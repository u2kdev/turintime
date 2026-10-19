"""
Фоновые уведомления бота:

* утренняя рассылка расписания в выбранное пользователем время;
* напоминание за N минут до начала пары.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

from .. import db, schedule
from . import storage
from . import texts as tx

log = logging.getLogger("turin.notify")

TICK_SECONDS = 25


def _today_lessons(group_id: str, moment: datetime) -> tuple[dict, list[dict]]:
    week = db.current_week(moment.date())
    days = schedule.day_grid("class", group_id, week)
    index = moment.weekday()
    if index > 5:
        return week or {}, []
    return week or {}, days[index]["lessons"]


async def _safe_send(bot: Bot, chat_id: int, text: str) -> bool:
    try:
        await bot.send_message(chat_id, text, disable_notification=False)
        return True
    except TelegramRetryAfter as exc:
        await asyncio.sleep(exc.retry_after)
        return False
    except TelegramForbiddenError:
        log.info("Пользователь %s заблокировал бота", chat_id)
        return False
    except Exception as exc:  # noqa: BLE001
        log.warning("Не удалось отправить сообщение %s: %s", chat_id, exc)
        return False


async def _digests(bot: Bot, moment: datetime) -> None:
    clock = moment.strftime("%H:%M")
    today = moment.date().isoformat()
    for user in storage.subscribers("digest"):
        if (user.get("notify_time") or "")[:5] != clock:
            continue
        if user.get("last_digest") == today:
            continue
        group_id = user["group_id"]
        week, lessons = _today_lessons(group_id, moment)
        up = schedule.up_next("class", group_id, moment, week=week).as_dict()
        day = schedule.day_meta(week, moment.weekday()) if moment.weekday() <= 5 else {
            **schedule.day_meta(week, 0), "date": today, "idx": moment.weekday()
        }
        text = tx.day_message(user.get("group_name") or group_id, day, lessons, up=up)
        if await _safe_send(bot, user["chat_id"] or user["user_id"], text):
            storage.update(user["user_id"], last_digest=today)


async def _reminders(bot: Bot, moment: datetime) -> None:
    now_minutes = moment.hour * 60 + moment.minute
    for user in storage.subscribers("remind"):
        group_id = user["group_id"]
        window = int(user.get("remind_minutes") or 15)
        week, lessons = _today_lessons(group_id, moment)
        for lesson in lessons:
            start = schedule.minutes(lesson["start"])
            if start is None:
                continue
            delta = start - now_minutes
            if not (0 <= delta <= window):
                continue
            marker = f"{moment.date().isoformat()}#{lesson['key']}"
            if user.get("last_reminder") == marker:
                continue
            rooms = ", ".join(room["name"] for room in lesson.get("rooms") or [])
            teachers = ", ".join(t["short"] or t["name"] for t in lesson.get("teachers") or [])
            text = (
                f"⏰ <b>Через {delta} {tx.plural(delta, 'минуту', 'минуты', 'минут')}</b>\n"
                f"{tx.LINE}\n"
                f"{tx.lesson_lines(lesson)}\n"
                f"{tx.LINE}\n"
                f"👥 {tx.esc(user.get('group_name') or group_id)}"
            )
            if rooms or teachers:
                text += f"\n<i>{tx.esc(teachers)}{' · ' if teachers and rooms else ''}{tx.esc(rooms)}</i>"
            if await _safe_send(bot, user["chat_id"] or user["user_id"], text):
                user["last_reminder"] = marker
                storage.update(user["user_id"], last_reminder=marker)
            break


async def notify_loop(bot: Bot) -> None:
    """Бесконечный цикл: раз в TICK_SECONDS проверяем расписание и рассылаем."""
    log.info("Рассылка уведомлений запущена")
    while True:
        try:
            moment = schedule.now_local()
            await _digests(bot, moment)
            await _reminders(bot, moment)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            log.exception("Ошибка цикла уведомлений")
        await asyncio.sleep(TICK_SECONDS)
