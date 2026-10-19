"""Инлайн-клавиатуры Telegram-бота."""
from __future__ import annotations

from typing import Any, Sequence

from aiogram.types import InlineKeyboardButton as Btn
from aiogram.types import InlineKeyboardMarkup as Kb

PER_PAGE = 12
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]


def _grid(items: Sequence[Any], columns: int, make: Any) -> list[list[Btn]]:
    rows: list[list[Btn]] = []
    row: list[Btn] = []
    for item in items:
        row.append(make(item))
        if len(row) == columns:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


def _pager(scope: str, page: int, pages: int, extra: list[Btn] | None = None) -> list[Btn]:
    row: list[Btn] = []
    if page > 0:
        row.append(Btn(text="◀️", callback_data=f"page:{scope}:{page - 1}"))
    row.append(Btn(text=f"{page + 1} / {max(pages, 1)}", callback_data="noop"))
    if page < pages - 1:
        row.append(Btn(text="▶️", callback_data=f"page:{scope}:{page + 1}"))
    if extra:
        row.extend(extra)
    return row


def entity_picker(kind: str, items: Sequence[dict], page: int = 0,
                  search: bool = True, back: str | None = None) -> Kb:
    """Список групп / преподавателей / аудиторий с постраничной навигацией."""
    pages = max(1, (len(items) + PER_PAGE - 1) // PER_PAGE)
    page = max(0, min(page, pages - 1))
    chunk = items[page * PER_PAGE:(page + 1) * PER_PAGE]
    rows = _grid(
        chunk, 2,
        lambda item: Btn(
            text=(item.get("name") or item.get("short") or "?")[:32],
            callback_data=f"pick:{kind}:{item['id']}",
        ),
    )
    extra = [Btn(text="🔍 Поиск", callback_data=f"search:{kind}")] if search else []
    if pages > 1 or extra:
        rows.append(_pager(kind, page, pages, extra))
    elif extra:
        rows.append(extra)
    if back:
        rows.append([Btn(text="◀️ Назад", callback_data=back)])
    return Kb(inline_keyboard=rows)


def home_kb(kind: str, entity_id: str, has_group: bool = True) -> Kb:
    rows = [
        [Btn(text="📅 Сегодня", callback_data=f"day:{kind}:{entity_id}:today"),
         Btn(text="⏭ Завтра", callback_data=f"day:{kind}:{entity_id}:tomorrow")],
        [Btn(text="🗓 Неделя", callback_data=f"week:{kind}:{entity_id}"),
         Btn(text="⏱ Ближайшая", callback_data=f"next:{kind}:{entity_id}")],
        [Btn(text="👤 Преподаватель", callback_data="choose:teacher"),
         Btn(text="🚪 Аудитория", callback_data="choose:room")],
        [Btn(text="⚙️ Настройки", callback_data="settings"),
         Btn(text="🔄 Сменить группу", callback_data="choose:class")],
    ]
    if not has_group:
        rows = rows[2:]
    return Kb(inline_keyboard=rows)


def schedule_kb(kind: str, entity_id: str, day_idx: int | None = None) -> Kb:
    rows: list[list[Btn]] = []
    if day_idx is not None:
        nav: list[Btn] = []
        if day_idx > 0:
            nav.append(Btn(text=f"◀️ {WEEKDAYS[day_idx - 1]}", callback_data=f"day:{kind}:{entity_id}:{day_idx - 1}"))
        if day_idx < 5:
            nav.append(Btn(text=f"{WEEKDAYS[day_idx + 1]} ▶️", callback_data=f"day:{kind}:{entity_id}:{day_idx + 1}"))
        if nav:
            rows.append(nav)
    rows.append([Btn(text="🗓 Вся неделя", callback_data=f"week:{kind}:{entity_id}"),
                 Btn(text="🏠 Меню", callback_data=f"home:{kind}:{entity_id}")])
    return Kb(inline_keyboard=rows)


def week_kb(kind: str, entity_id: str, days: Sequence[dict]) -> Kb:
    rows = _grid(
        [day for day in days if day.get("lessons")],
        3,
        lambda day: Btn(
            text=f"{WEEKDAYS[day['idx']]} · {day['count']}",
            callback_data=f"day:{kind}:{entity_id}:{day['idx']}",
        ),
    )
    rows.append([Btn(text="🏠 Меню", callback_data=f"home:{kind}:{entity_id}")])
    return Kb(inline_keyboard=rows)


def settings_kb(user: dict[str, Any]) -> Kb:
    notify = "✅" if user.get("notify") else "❌"
    remind = "✅" if user.get("remind") else "❌"
    times = ["07:00", "07:30", "08:00", "08:30", "09:00"]
    rows = [
        [Btn(text=f"🌅 Утренняя рассылка {notify}", callback_data="set:notify")],
        _grid(times, 5, lambda value: Btn(
            text=("• " if user.get("notify_time") == value else "") + value,
            callback_data=f"set:time:{value}",
        ))[0],
        [Btn(text=f"⏰ Напоминание перед парой {remind}", callback_data="set:remind")],
        [Btn(text="🔄 Сменить группу", callback_data="choose:class"),
         Btn(text="🏠 Меню", callback_data="home_any")],
    ]
    return Kb(inline_keyboard=rows)


def back_home_kb(entity_id: str = "") -> Kb:
    return Kb(inline_keyboard=[[Btn(text="🏠 Меню", callback_data="home_any")]])
