"""Обновление расписания: загрузка из EduPage и запись в SQLite."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from . import db
from .config import settings
from .edupage import EduPageClient, EduPageError, fetch_parsed_weeks

log = logging.getLogger("turin.sync")


@dataclass
class SyncState:
    running: bool = False
    last_result: str = ""
    last_run: str = ""
    last_error: str = ""
    last_stats: dict[str, Any] | None = None


state = SyncState()
_lock = asyncio.Lock()


async def refresh(force: bool = False) -> dict[str, Any]:
    """Скачивает расписание и полностью перезаписывает базу."""
    if _lock.locked() and not force:
        return {"ok": False, "error": "Обновление уже выполняется"}
    async with _lock:
        state.running = True
        state.last_error = ""
        try:
            db.init_db()
            client = EduPageClient()
            weeks, parsed = await fetch_parsed_weeks(client)
            stats = await asyncio.to_thread(db.store, weeks, parsed, client.api)
            state.last_stats = stats
            state.last_run = datetime.now().isoformat(timespec="seconds")
            state.last_result = (
                f"Недель: {stats['weeks']} · занятий: {stats['lessons']} · "
                f"групп: {stats['classes']}"
            )
            log.info("Расписание обновлено: %s", state.last_result)
            return {"ok": True, "message": state.last_result, "stats": stats}
        except EduPageError as exc:
            state.last_error = str(exc)
            log.error("Обновление не удалось: %s", exc)
            if db.is_ready():
                return {"ok": False, "error": str(exc), "stale": True}
            return {"ok": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            state.last_error = repr(exc)
            log.exception("Неожиданная ошибка обновления")
            return {"ok": False, "error": repr(exc)}
        finally:
            state.running = False


async def refresh_if_stale(max_age_hours: int | None = None) -> dict[str, Any]:
    """Обновляет базу только если данные устарели или отсутствуют."""
    max_age = settings.refresh_hours if max_age_hours is None else max_age_hours
    if not db.is_ready():
        return await refresh()
    info = db.meta()
    updated = info.get("updated_at", "")
    try:
        when = datetime.fromisoformat(updated)
    except ValueError:
        return await refresh()
    if datetime.now() - when > timedelta(hours=max_age):
        log.info("Данные устарели (%s), обновляем", updated)
        return await refresh()
    return {"ok": True, "message": f"Данные актуальны ({updated})", "skipped": True}


async def scheduler_loop(stop: asyncio.Event | None = None) -> None:
    """Фоновое обновление раз в REFRESH_HOURS часов."""
    interval = max(1, settings.refresh_hours) * 3600
    while stop is None or not stop.is_set():
        try:
            await refresh()
        except Exception:  # noqa: BLE001
            log.exception("Ошибка фонового обновления")
        try:
            if stop is None:
                await asyncio.sleep(interval)
            else:
                await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue


def summary() -> dict[str, Any]:
    info = db.meta()
    return {
        "updated_at": info.get("updated_at", ""),
        "source": info.get("source", ""),
        "lessons": int(info.get("lessons") or 0),
        "weeks": int(info.get("weeks") or 0),
        "classes": int(info.get("classes") or 0),
        "teachers": int(info.get("teachers") or 0),
        "classrooms": int(info.get("classrooms") or 0),
        "running": state.running,
        "last_result": state.last_result,
        "last_error": state.last_error,
        "ready": db.is_ready(),
    }
