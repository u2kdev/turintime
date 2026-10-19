"""Точка входа: запуск веб-сервера (и Telegram-бота вместе с ним).

    python main.py            # сервер + бот
    python main.py update     # только обновить расписание и выйти
"""
from __future__ import annotations

import sys

from turin.api import create_app
from turin.config import settings

app = create_app()


def _configure_stdio() -> None:
    """Windows-консоль по умолчанию в cp1251 и падает на «→». Печатаем UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_configure_stdio()


def _update_only() -> int:
    import asyncio
    from turin import sync

    result = asyncio.run(sync.refresh())
    print(result.get("message") or result.get("error"))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in {"update", "sync", "scrape"}:
        raise SystemExit(_update_only())

    import uvicorn

    print(f"  {settings.school_name}")
    print(f"  Веб-приложение → {settings.base_url}")
    print(f"  База данных    → {settings.timetable_db}")
    if settings.bot_token:
        print("  Telegram-бот   → включён")
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=False, log_level="info")
