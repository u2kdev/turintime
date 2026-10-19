"""Обработчики Telegram-бота."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .. import db, schedule
from . import keyboards as kb
from . import storage
from . import texts as tx

log = logging.getLogger("turin.bot")
router = Router(name="turin")

KIND_TITLES = {"class": "группы", "teacher": "преподаватели", "room": "аудитории"}
KIND_ONE = {"class": "Группа", "teacher": "Преподаватель", "room": "Аудитория"}


class Search(StatesGroup):
    waiting = State()


# ── справочники ─────────────────────────────────────────────────────────────
_cache: dict[str, list[dict]] = {}


def natural_key(value: str) -> list:
    import re

    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", value or "")]


def catalog(kind: str) -> list[dict]:
    """Справочники кэшируются и сбрасываются при обновлении расписания."""
    stamp = db.meta().get("updated_at", "")
    if _cache.get("_stamp") != stamp:
        data = db.directory()
        _cache.clear()
        _cache["_stamp"] = stamp
        _cache["class"] = sorted(data["classes"], key=lambda item: natural_key(item["name"]))
        _cache["teacher"] = sorted(data["teachers"], key=lambda item: item["short"] or item["name"])
        _cache["room"] = sorted(data["classrooms"], key=lambda item: natural_key(item["name"]))
    return _cache.get(kind) or []


def find_entity(kind: str, entity_id: str) -> dict | None:
    for item in catalog(kind):
        if item["id"] == entity_id:
            return item
    return db.entity(kind, entity_id)


def entity_name(kind: str, entity_id: str) -> str:
    item = find_entity(kind, entity_id)
    if not item:
        return entity_id
    return item.get("name") or item.get("short") or entity_id


def search_catalog(kind: str, query: str, limit: int = 30) -> list[dict]:
    needle = query.strip().lower()
    if not needle:
        return []
    items = catalog(kind)
    exact = [item for item in items if (item.get("name") or "").lower() == needle
             or (item.get("short") or "").lower() == needle]
    starts = [item for item in items if needle in (item.get("name") or "").lower()
              or needle in (item.get("short") or "").lower()]
    ordered: list[dict] = []
    for item in exact + starts:
        if item not in ordered:
            ordered.append(item)
    if len(ordered) < limit:
        for item in db.search(query, limit=limit):
            if item["kind"] == kind and item not in ordered:
                ordered.append(item)
    return ordered[:limit]


# ── отправка расписания ─────────────────────────────────────────────────────
def _day_index(mode: str, now: datetime) -> int | None:
    if mode == "today":
        return now.weekday()
    if mode == "tomorrow":
        return (now + timedelta(days=1)).weekday()
    try:
        return int(mode)
    except (TypeError, ValueError):
        return None


async def send_day(target: Message, kind: str, entity_id: str, mode: str, edit: bool = False) -> None:
    now = schedule.now_local()
    target_date = now.date() + timedelta(days=1 if mode == "tomorrow" else 0)
    index = _day_index(mode, now)
    week = db.current_week(target_date)
    days = schedule.day_grid(kind, entity_id, week)
    name = entity_name(kind, entity_id)

    if index is None or index > 5:
        text = (f"📅 <b>{tx.esc(name)}</b>\n{tx.LINE}\n"
                "В воскресенье занятий нет 🙂")
        up = None
    else:
        up = schedule.up_next(kind, entity_id, week=week).as_dict()
        text = tx.day_message(name, days[index], days[index]["lessons"], up=up, kind=kind)

    markup = kb.schedule_kb(kind, entity_id, index if index is not None and index <= 5 else None)
    if edit:
        await target.edit_text(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)


async def send_week(target: Message, kind: str, entity_id: str, edit: bool = False) -> None:
    week = db.current_week()
    days = schedule.day_grid(kind, entity_id, week)
    text = tx.week_message(entity_name(kind, entity_id), days, schedule.week_payload(week), kind)
    markup = kb.week_kb(kind, entity_id, days)
    if edit:
        await target.edit_text(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)


async def send_next(target: Message, kind: str, entity_id: str, edit: bool = False) -> None:
    up = schedule.up_next(kind, entity_id)
    payload = up.as_dict()
    name = entity_name(kind, entity_id)
    lines = [f"⏱ <b>{tx.esc(name)}</b>", tx.LINE]
    lesson = payload.get("current") or payload.get("next")
    if lesson:
        head = "▶️ <b>Идёт сейчас</b>" if payload.get("current") else "⏭ <b>Ближайшая пара</b>"
        lines.append(head)
        if payload.get("next_day") and not payload.get("current"):
            lines.append(f"<i>{tx.date_label(payload['next_day'])}</i>")
        if not payload.get("current") and payload.get("next_day", {}).get("date") != payload["today"].get("date"):
            pass
        lines.append("")
        lines.append(tx.lesson_lines(lesson))
        left = payload.get("current_left_minutes")
        in_min = payload.get("next_in_minutes")
        if left is not None:
            lines.append(f"\n⏳ Осталось {left} {tx.plural(left, 'минута', 'минуты', 'минут')}")
        elif in_min is not None:
            lines.append(f"\n⏳ Начало через {in_min} {tx.plural(in_min, 'минуту', 'минуты', 'минут')}")
        elif payload.get("next_day"):
            lines.append(f"\n<i>День: {tx.date_label(payload['next_day'])}</i>")
    else:
        lines.append("☕️ Пар впереди нет")
    text = "\n".join(lines)
    markup = kb.schedule_kb(kind, entity_id, payload.get("next_day", {}).get("idx") if payload.get("next_day") else None)
    if edit:
        await target.edit_text(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)


async def send_home(target: Message, user_id: int, edit: bool = False) -> None:
    user = storage.get_user(user_id)
    if not user:
        return
    if not user.get("group_id"):
        await send_group_picker(target, 0, edit=edit)
        return
    up = schedule.up_next("class", user["group_id"]).as_dict()
    week = db.current_week()
    text = tx.home_message(user, up, (schedule.week_payload(week) or {}).get("title", ""))
    markup = kb.home_kb("class", user["group_id"], has_group=True)
    if edit:
        try:
            await target.edit_text(text, reply_markup=markup)
        except Exception:  # noqa: BLE001 — сообщение могло не измениться
            pass
    else:
        await target.answer(text, reply_markup=markup)


async def send_group_picker(target: Message, page: int = 0, edit: bool = False,
                            query: str = "", kind: str = "class") -> None:
    items = search_catalog(kind, query) if query else catalog(kind)
    if not items:
        text = f"😕 Ничего не найдено по запросу «{tx.esc(query)}»"
        markup = kb.entity_picker(kind, [], 0, back="home_any")
    else:
        total = len(items)
        text = tx.entity_list_message(f"Выберите {'группу' if kind == 'class' else KIND_ONE[kind].lower()}",
                                      kind, page, max(1, (total + kb.PER_PAGE - 1) // kb.PER_PAGE), total)
        if query:
            text = f"🔍 «{tx.esc(query)}»\n" + text
        markup = kb.entity_picker(kind, items[:60], page)
    if edit:
        await target.edit_text(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)


# ── команды ─────────────────────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    storage.upsert_user(
        user.id,
        chat_id=message.chat.id,
        username=user.username or "",
        first_name=user.first_name or "",
        last_name=user.last_name or "",
    )
    saved = storage.get_user(user.id)
    if saved and saved.get("group_id"):
        await message.answer(f"👋 С возвращением, <b>{tx.esc(saved.get('group_name'))}</b>!")
        await send_home(message, user.id)
    else:
        await message.answer(
            "👋 <b>Привет!</b> Я показываю расписание TTPU.\n\n"
            "Для начала выберите свою группу — можно отправить её название "
            "текстом (например, <code>IT1-26</code>) или выбрать из списка."
        )
        await send_group_picker(message, 0)


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(tx.HELP_TEXT)


@router.message(Command("group"))
async def cmd_group(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_group_picker(message, 0)


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = storage.get_user(message.from_user.id) or {}
    await message.answer(tx.settings_message(user), reply_markup=kb.settings_kb(user))


@router.message(Command("today"))
async def cmd_today(message: Message, state: FSMContext) -> None:
    await _simple_day(message, state, "today")


@router.message(Command("tomorrow"))
async def cmd_tomorrow(message: Message, state: FSMContext) -> None:
    await _simple_day(message, state, "tomorrow")


async def _simple_day(message: Message, state: FSMContext, mode: str) -> None:
    await state.clear()
    user = storage.get_user(message.from_user.id) or {}
    if not user.get("group_id"):
        await message.answer("Сначала выберите группу 🙂")
        await send_group_picker(message, 0)
        return
    await send_day(message, "class", user["group_id"], mode)


@router.message(Command("week"))
async def cmd_week(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = storage.get_user(message.from_user.id) or {}
    if not user.get("group_id"):
        await message.answer("Сначала выберите группу 🙂")
        await send_group_picker(message, 0)
        return
    await send_week(message, "class", user["group_id"])


@router.message(Command("next"))
async def cmd_next(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = storage.get_user(message.from_user.id) or {}
    if not user.get("group_id"):
        await message.answer("Сначала выберите группу 🙂")
        await send_group_picker(message, 0)
        return
    await send_next(message, "class", user["group_id"])


@router.message(Command("teacher"))
async def cmd_teacher(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_group_picker(message, 0, kind="teacher")


@router.message(Command("room"))
async def cmd_room(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_group_picker(message, 0, kind="room")


# ── кнопки ──────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery) -> None:
    await call.answer()


@router.callback_query(F.data == "home_any")
async def cb_home_any(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await send_home(call.message, call.from_user.id, edit=True)
    await call.answer()


@router.callback_query(F.data.startswith("home:"))
async def cb_home(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await send_home(call.message, call.from_user.id, edit=True)
    await call.answer()


@router.callback_query(F.data.startswith("choose:"))
async def cb_choose(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    kind = call.data.split(":", 1)[1]
    await send_group_picker(call.message, 0, edit=True, kind=kind)
    await call.answer()


@router.callback_query(F.data.startswith("page:"))
async def cb_page(call: CallbackQuery, state: FSMContext) -> None:
    _, kind, page = call.data.split(":")
    data = await state.get_data()
    await send_group_picker(call.message, int(page), edit=True,
                            query=data.get("query", ""), kind=kind)
    await call.answer()


@router.callback_query(F.data.startswith("search:"))
async def cb_search(call: CallbackQuery, state: FSMContext) -> None:
    kind = call.data.split(":", 1)[1]
    await state.set_state(Search.waiting)
    await state.update_data(kind=kind, query="")
    title = KIND_TITLES.get(kind, "группы")
    await call.message.edit_text(
        f"🔍 Отправьте название или часть названия — найду {title}.\n\n"
        "Например: <code>IT1</code>, <code>FAYZIYEVA</code> или <code>C405</code>",
        reply_markup=kb.back_home_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("pick:"))
async def cb_pick(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    _, kind, entity_id = call.data.split(":", 2)
    user_id = call.from_user.id
    if kind == "class":
        name = entity_name("class", entity_id)
        storage.update(user_id, group_id=entity_id, group_name=name)
        await send_home(call.message, user_id, edit=True)
    else:
        await send_day(call.message, kind, entity_id, "today", edit=True)
    await call.answer()


@router.callback_query(F.data.startswith("day:"))
async def cb_day(call: CallbackQuery) -> None:
    _, kind, entity_id, mode = call.data.split(":", 3)
    await send_day(call.message, kind, entity_id, mode, edit=True)
    await call.answer()


@router.callback_query(F.data.startswith("week:"))
async def cb_week(call: CallbackQuery) -> None:
    _, kind, entity_id = call.data.split(":", 2)
    await send_week(call.message, kind, entity_id, edit=True)
    await call.answer()


@router.callback_query(F.data.startswith("next:"))
async def cb_next(call: CallbackQuery) -> None:
    _, kind, entity_id = call.data.split(":", 2)
    await send_next(call.message, kind, entity_id, edit=True)
    await call.answer()


@router.callback_query(F.data == "settings")
async def cb_settings(call: CallbackQuery) -> None:
    user = storage.get_user(call.from_user.id) or {}
    await call.message.edit_text(tx.settings_message(user), reply_markup=kb.settings_kb(user))
    await call.answer()


@router.callback_query(F.data.startswith("set:"))
async def cb_set(call: CallbackQuery) -> None:
    parts = call.data.split(":")
    user_id = call.from_user.id
    if len(parts) == 2 and parts[1] == "notify":
        user = storage.get_user(user_id) or {}
        storage.update(user_id, notify=0 if user.get("notify") else 1)
    elif len(parts) == 2 and parts[1] == "remind":
        user = storage.get_user(user_id) or {}
        storage.update(user_id, remind=0 if user.get("remind") else 1)
    elif len(parts) == 3 and parts[1] == "time":
        storage.update(user_id, notify_time=parts[2], notify=1)
    user = storage.get_user(user_id) or {}
    await call.message.edit_text(tx.settings_message(user), reply_markup=kb.settings_kb(user))
    await call.answer("Готово")


# ── свободный текст: поиск и умное распознавание ─────────────────────────────
@router.message(Search.waiting)
async def on_search_query(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    kind = data.get("kind", "class")
    query = (message.text or "").strip()
    await state.update_data(query=query)
    results = search_catalog(kind, query)
    if not results:
        await message.answer(
            f"😕 По запросу «{tx.esc(query)}» ничего не нашлось.\n"
            "Попробуйте другое написание или /help",
            reply_markup=kb.back_home_kb(),
        )
        return
    if kind == "class" and len(results) == 1:
        entity = results[0]
        storage.update(message.from_user.id, group_id=entity["id"],
                       group_name=entity.get("name") or entity["id"])
        await state.clear()
        await send_home(message, message.from_user.id)
        return
    await state.set_state(None)
    await send_group_picker(message, 0, query=query, kind=kind)


@router.message(F.text)
async def on_text(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = (message.text or "").strip()
    if not text:
        return
    user = storage.get_user(message.from_user.id) or {}
    found = search_catalog("class", text, limit=8)
    if len(found) == 1 or (found and found[0]["name"].lower() == text.lower()):
        entity = found[0]
        storage.update(message.from_user.id, group_id=entity["id"],
                       group_name=entity.get("name") or entity["id"])
        await send_home(message, message.from_user.id)
        return
    if found:
        await message.answer(f"🔍 Нашёл {len(found)} групп(ы) по «{tx.esc(text)}»:", reply_markup=kb.back_home_kb())
        await send_group_picker(message, 0, query=text)
        return
    if user.get("group_id"):
        await message.answer(
            f"Не понял «{tx.esc(text)}» 🤔\n"
            "Воспользуйтесь кнопками или /help",
            reply_markup=kb.home_kb("class", user["group_id"]),
        )
    else:
        await message.answer(
            "Не нашёл такую группу 😕\nОтправьте название иначе или /help",
            reply_markup=kb.back_home_kb(),
        )


def build_router() -> Router:
    return router
