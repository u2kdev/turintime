"""HTTP API и отдача веб-приложения."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import db, schedule, sync
from .config import ROOT, settings
from .edupage import KINDS

log = logging.getLogger("turin.api")

api = APIRouter(prefix="/api")


def _ensure_ready() -> None:
    if not db.is_ready():
        raise HTTPException(status_code=503, detail="Расписание ещё не загружено")


def _validate_kind(kind: str) -> str:
    if kind not in KINDS:
        raise HTTPException(status_code=404, detail="Неизвестный тип расписания")
    return kind


# ── служебное ───────────────────────────────────────────────────────────────
@api.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "ready": db.is_ready(), "time": schedule.now_local().isoformat(timespec="seconds")}


@api.get("/meta")
def meta() -> dict[str, Any]:
    summary = sync.summary()
    week = db.current_week()
    moment = schedule.now_local()
    return {
        "school": settings.school_name,
        "school_short": settings.school_short,
        "timezone": settings.timezone,
        "now": moment.isoformat(timespec="seconds"),
        "today": {"idx": moment.weekday(), "date": moment.date().isoformat()},
        "bot_username": settings.bot_username,
        "bot_url": f"https://t.me/{settings.bot_username}" if settings.bot_username else "",
        **summary,
        "current_week": schedule.week_payload(week),
    }


@api.get("/weeks")
def weeks() -> list[dict[str, Any]]:
    _ensure_ready()
    return [schedule.week_payload(week) for week in db.weeks()]


@api.get("/directory")
def directory() -> dict[str, Any]:
    _ensure_ready()
    data = db.directory()
    data["popular"] = db.popular_classes(14)
    week = db.current_week()
    data["week"] = schedule.week_payload(week)
    data["load"] = db.load_map((week or {}).get("tt_num"))
    data["updated_at"] = db.meta().get("updated_at", "")
    return data


@api.get("/search")
def search(q: str = Query("", min_length=1, max_length=64)) -> list[dict[str, Any]]:
    _ensure_ready()
    return db.search(q)


# ── расписание ──────────────────────────────────────────────────────────────
def _resolve_week(week: str | None, day: str | None) -> dict | None:
    if day:
        try:
            target = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Дата в формате ГГГГ-ММ-ДД")
        return db.current_week(target)
    if week:
        found = db.week_by_number(week)
        if not found:
            raise HTTPException(status_code=404, detail="Неделя не найдена")
        return found
    return db.current_week()


@api.get("/schedule/{kind}/{entity_id:path}")
def get_schedule(
    kind: str,
    entity_id: str,
    week: str | None = Query(None, description="Номер учебной недели"),
    day: str | None = Query(None, description="Дата ГГГГ-ММ-ДД"),
) -> dict[str, Any]:
    _ensure_ready()
    _validate_kind(kind)
    entity = db.entity(kind, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Группа, преподаватель или аудитория не найдены")
    resolved = _resolve_week(week, day)
    return {
        "kind": kind,
        "entity": entity,
        "week": schedule.week_payload(resolved),
        "weeks": [schedule.week_payload(item) for item in db.weeks()],
        "days": schedule.day_grid(kind, entity_id, resolved),
        "updated_at": db.meta().get("updated_at", ""),
        "generated_at": schedule.now_local().isoformat(timespec="seconds"),
    }


@api.get("/now/{kind}/{entity_id:path}")
def get_now(kind: str, entity_id: str) -> dict[str, Any]:
    _ensure_ready()
    _validate_kind(kind)
    if not db.entity(kind, entity_id):
        raise HTTPException(status_code=404, detail="Не найдено")
    return schedule.up_next(kind, entity_id).as_dict()


@api.get("/offline/{kind}/{entity_id:path}")
def get_offline(kind: str, entity_id: str) -> dict[str, Any]:
    """Всё расписание сущности по всем неделям — для офлайн-кэша на телефоне."""
    _ensure_ready()
    _validate_kind(kind)
    if not db.entity(kind, entity_id):
        raise HTTPException(status_code=404, detail="Не найдено")
    return schedule.offline_bundle(kind, entity_id)


# ── обновление ──────────────────────────────────────────────────────────────
def _is_admin(request: Request) -> bool:
    token = settings.admin_token
    provided = request.headers.get("x-admin-token") or request.query_params.get("token", "")
    if token:
        return provided == token
    host = (request.client.host if request.client else "") or ""
    return host in {"127.0.0.1", "::1", "localhost", "testclient"}


@api.post("/refresh")
async def post_refresh(request: Request) -> dict[str, Any]:
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Нужен административный токен")
    return await sync.refresh()


@api.get("/refresh/status")
def refresh_status(request: Request) -> dict[str, Any]:
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Нужен административный токен")
    return sync.summary()


# ── приложение ──────────────────────────────────────────────────────────────
def create_app(with_bot: bool = True) -> FastAPI:
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s  %(levelname)-7s %(name)s  %(message)s",
            datefmt="%H:%M:%S",
        )
        db.init_db()
        tasks: list[asyncio.Task] = []
        stop = asyncio.Event()

        if settings.refresh_on_start:
            tasks.append(asyncio.create_task(_warmup()))
        tasks.append(asyncio.create_task(sync.scheduler_loop(stop)))

        if with_bot and settings.run_bot and settings.bot_token:
            try:
                from .bot.runner import start_bot

                tasks.append(asyncio.create_task(start_bot(stop)))
            except Exception as exc:  # noqa: BLE001
                log.error("Telegram-бот не запущен: %s", exc)
        elif with_bot and settings.run_bot:
            log.info("BOT_TOKEN не задан — Telegram-бот выключен")

        try:
            yield
        finally:
            stop.set()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(
        title="TTPU Timetable API",
        description="Расписание Турниского политехнического университета в Ташкенте",
        version=os.environ.get("APP_VERSION", "2.0.0"),
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(GZipMiddleware, minimum_size=700)
    app.include_router(api)

    web_dir = settings.web_dir
    assets = web_dir / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")
    icons = web_dir / "icons"
    if icons.is_dir():
        app.mount("/icons", StaticFiles(directory=icons), name="icons")

    @app.get("/sw.js", include_in_schema=False)
    def service_worker() -> FileResponse:
        return FileResponse(web_dir / "sw.js", media_type="application/javascript",
                            headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest() -> FileResponse:
        return FileResponse(web_dir / "manifest.webmanifest",
                            media_type="application/manifest+json")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        icon = web_dir / "icons" / "favicon.png"
        if icon.is_file():
            return FileResponse(icon, media_type="image/png")
        return Response(status_code=204)

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> HTMLResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Не найдено")
        candidate = (web_dir / path).resolve()
        if path and web_dir.resolve() in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        index = web_dir / "index.html"
        if not index.is_file():
            return HTMLResponse("<h1>TTPU Timetable</h1><p>web/index.html не найден</p>", status_code=500)
        return HTMLResponse(index.read_text(encoding="utf-8"),
                            headers={"Cache-Control": "no-cache"})

    return app


async def _warmup() -> None:
    await asyncio.sleep(0.5)
    try:
        await sync.refresh_if_stale()
    except Exception:  # noqa: BLE001
        log.exception("Стартовое обновление не удалось")
