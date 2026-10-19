"""Формирование текстов и клавиатур для Telegram-бота."""
from __future__ import annotations

import html
from typing import Any

MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]

DASH = "—"
LINE = "<i>──────────────────</i>"


def esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=False)


def plural(number: int, one: str, few: str, many: str) -> str:
    rest = number % 100
    if 11 <= rest <= 14:
        return many
    rest %= 10
    if rest == 1:
        return one
    if 2 <= rest <= 4:
        return few
    return many


def date_label(day: dict[str, Any]) -> str:
    """«пн, 19 октября»."""
    if not day.get("date"):
        return day.get("ru_short", "")
    month = MONTHS_RU[day.get("month", 0)] if day.get("month") else ""
    weekday = (day.get("ru") or "")[:2].lower()
    return f"{weekday}, {day.get('day')} {month}".strip()


def lesson_lines(lesson: dict[str, Any], marker: str = "", compact: bool = False) -> str:
    subject = esc(lesson.get("subject") or lesson.get("short") or DASH)
    short = esc(lesson.get("short") or "")
    time = f"{lesson.get('start','')}–{lesson.get('end','')}"
    rooms = ", ".join(esc(room["name"]) for room in lesson.get("rooms") or [])
    teachers = ", ".join(esc(t["short"] or t["name"]) for t in lesson.get("teachers") or [])
    groups = ", ".join(esc(name) for name in lesson.get("groups") or [])
    classes = ", ".join(esc(item["name"]) for item in lesson.get("classes") or [])

    head = f"{marker}<b>{lesson.get('period')}. {time}</b>"
    if compact:
        line = f"{head} · {subject}"
        if rooms:
            line += f" · {rooms}"
        return line

    out = [head, f"<b>{subject}</b>"]
    if short and short != subject:
        out.append(f"<i>{short}</i>")
    meta = []
    if teachers:
        meta.append(f"👤 {teachers}")
    if rooms:
        meta.append(f"🚪 {rooms}")
    if groups:
        meta.append(f"👥 {groups}")
    elif classes and lesson.get("hide_classes"):
        meta.append(f"👥 {classes}")
    if meta:
        out.append(" · ".join(meta))
    return "\n".join(out)


def day_message(entity_name: str, day: dict[str, Any], lessons: list[dict[str, Any]],
                up: dict[str, Any] | None = None, kind: str = "class") -> str:
    """Подробное расписание одного дня."""
    title_kind = {"class": "Группа", "teacher": "Преподаватель", "room": "Аудитория"}.get(kind, "")
    head = [
        f"📅 <b>{esc(entity_name)}</b>",
        f"<i>{title_kind}</i> · {esc(date_label(day))}",
    ]
    if not lessons:
        head.append(LINE)
        head.append("☕️ <b>Занятий нет</b>")
        return "\n".join(head)

    now_period = None
    if up and up.get("current") and up.get("current_day", {}).get("date") == day.get("date"):
        now_period = up["current"].get("period")

    head.append(LINE)
    now_marker, next_marker = "▶️ ", "⏭ "
    next_key = (up or {}).get("next", {}).get("key") if (up or {}).get("next") else None
    next_same_day = bool(next_key) and (up or {}).get("next_day", {}).get("date") == day.get("date")

    blocks = [f"{len(lessons)} {plural(len(lessons), 'пара', 'пары', 'пар')}"]
    for lesson in lessons:
        marker = ""
        if now_period is not None and lesson.get("period") == now_period:
            marker = now_marker
        elif next_same_day and lesson.get("key") == next_key:
            marker = next_marker
        blocks.append(lesson_lines(lesson, marker=marker))

    tail = ""
    if now_period is not None and up and up.get("current_left_minutes") is not None:
        left = up["current_left_minutes"]
        tail = f"\n{LINE}\n⏳ До конца пары <b>{left} {plural(left, 'минута', 'минуты', 'минут')}</b>"
    return "\n".join(head) + "\n\n" + "\n\n".join(blocks) + tail


def week_message(entity_name: str, days: list[dict[str, Any]], week: dict[str, Any] | None,
                 kind: str = "class") -> str:
    lines = [f"🗓 <b>{esc(entity_name)}</b>"]
    if week:
        lines.append(f"<i>{esc(week.get('title',''))}</i>")
    lines.append(LINE)
    empty = True
    for day in days:
        lessons = day.get("lessons") or []
        if not lessons:
            continue
        empty = False
        lines.append(f"\n<b>{esc(date_label(day)).upper()}</b>")
        for lesson in lessons:
            rooms = ", ".join(esc(room["name"]) for room in lesson.get("rooms") or [])
            short = esc(lesson.get("short") or lesson.get("subject") or DASH)
            row = f"  <b>{lesson.get('period')}</b> {lesson.get('start','')} · {short}"
            if rooms:
                row += f" · <i>{rooms}</i>"
            lines.append(row)
    if empty:
        lines.append("\n☕️ На этой неделе занятий нет")
    return "\n".join(lines)


def entity_list_message(title: str, kind: str, page: int, pages: int, total: int) -> str:
    return (f"<b>{esc(title)}</b>\n"
            f"<i>Найдено: {total} · страница {page + 1} из {pages}</i>\n{LINE}\n"
            "Выберите из списка или отправьте текст для поиска 🔍")


def home_message(user: dict[str, Any], up: dict[str, Any] | None, week_title: str) -> str:
    name = esc(user.get("first_name") or "студент")
    group = esc(user.get("group_name") or "не выбрана")
    lines = [
        f"👋 <b>{name}</b>, ваша группа: <b>{group}</b>",
    ]
    if week_title:
        lines.append(f"<i>{esc(week_title)}</i>")
    lines.append(LINE)
    if up:
        moment = up.get("now", "")[11:16]
        lines.append(f"🕐 Сейчас {moment}")
        if up.get("current"):
            lesson = up["current"]
            rooms = ", ".join(esc(room["name"]) for room in lesson.get("rooms") or [])
            left = up.get("current_left_minutes")
            lines.append(f"▶️ <b>{esc(lesson['short'] or lesson['subject'])}</b>"
                         + (f" · 🚪 {rooms}" if rooms else ""))
            if left is not None:
                lines.append(f"⏳ осталось {left} {plural(left, 'минута', 'минуты', 'минут')}")
        elif up.get("next"):
            lesson = up["next"]
            rooms = ", ".join(esc(room["name"]) for room in lesson.get("rooms") or [])
            in_min = up.get("next_in_minutes")
            when = (f"через {in_min} {plural(in_min, 'минуту', 'минуты', 'минут')}"
                    if in_min is not None else "в следующий учебный день")
            lines.append(f"⏭ {esc(lesson['short'] or lesson['subject'])}{f' · 🚪 {rooms}' if rooms else ''}")
            lines.append(f"<i>{when}</i>")
        else:
            lines.append("☕️ Пар впереди нет")
    return "\n".join(lines)


def settings_message(user: dict[str, Any]) -> str:
    notify = "включена ✅" if user.get("notify") else "выключена ❌"
    remind = "включены ✅" if user.get("remind") else "выключены ❌"
    return (
        "⚙️ <b>Настройки</b>\n"
        f"{LINE}\n"
        f"👥 Группа: <b>{esc(user.get('group_name') or '—')}</b>\n"
        f"🌅 Утренняя рассылка: <b>{notify}</b>"
        + (f" в <b>{esc(user.get('notify_time'))}</b>" if user.get("notify") else "") + "\n"
        f"⏰ Напоминание перед парой: <b>{remind}</b>"
        + (f" за {user.get('remind_minutes')} мин" if user.get("remind") else "") + "\n"
        f"{LINE}\n"
        "Уведомления приходят в этот чат."
    )


HELP_TEXT = (
    "🤖 <b>Расписание TTPU</b>\n"
    f"{LINE}\n"
    "/start — главное меню\n"
    "/today — пары на сегодня\n"
    "/tomorrow — пары на завтра\n"
    "/week — вся неделя\n"
    "/next — ближайшая пара\n"
    "/group — сменить группу\n"
    "/teacher — расписание преподавателя\n"
    "/room — расписание аудитории\n"
    "/settings — уведомления\n"
    "/help — эта справка\n"
    f"{LINE}\n"
    "Просто отправьте название группы, преподавателя или аудитории — я найду."
)
