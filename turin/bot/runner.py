"""Запуск Telegram-бота: polling + фоновые уведомления."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from .. import db
from ..config import settings
from . import storage
from .handlers import build_router
from .notifier import notify_loop

log = logging.getLogger("turin.bot")

COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="today", description="Пары на сегодня"),
    BotCommand(command="tomorrow", description="Пары на завтра"),
    BotCommand(command="week", description="Расписание на неделю"),
    BotCommand(command="next", description="Ближайшая пара"),
    BotCommand(command="group", description="Сменить группу"),
    BotCommand(command="teacher", description="Расписание преподавателя"),
    BotCommand(command="room", description="Расписание аудитории"),
    BotCommand(command="settings", description="Уведомления"),
    BotCommand(command="help", description="Помощь"),
]


def build_bot() -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(build_router())
    return dispatcher


async def run_polling(bot: Bot, dispatcher: Dispatcher) -> None:
    me = await bot.get_me()
    await bot.set_my_commands(COMMANDS, scope=BotCommandScopeDefault())
    log.info("Бот @%s запущен", me.username)
    try:
        await dispatcher.start_polling(bot, handle_signals=False, drop_pending_updates=True)
    finally:
        log.info("Polling остановлен")


async def start_bot(stop: asyncio.Event | None = None) -> None:
    """Поднимает бота внутри текущего процесса (вызывается из lifespan)."""
    storage.init_db()
    if not db.is_ready():
        log.warning("Расписание ещё не загружено — бот ответит, когда данные появятся")

    bot = build_bot()
    dispatcher = build_dispatcher()
    tasks = [
        asyncio.create_task(run_polling(bot, dispatcher)),
        asyncio.create_task(notify_loop(bot)),
    ]
    if stop is not None:
        await stop.wait()
    else:
        await asyncio.gather(*tasks)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await bot.session.close()


async def main() -> None:
    """Автономный запуск: python -m turin.bot"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    db.init_db()
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN не задан — добавьте его в .env")
    await start_bot()


if __name__ == "__main__":
    asyncio.run(main())
