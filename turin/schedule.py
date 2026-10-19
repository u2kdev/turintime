"""
Логика «что идёт сейчас / что дальше» и сборка срезов расписания.

Используется и веб-API, и Telegram-ботом, и рассылкой уведомлений.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from . import db
from .config import settings
from .edupage import DAY_LABELS_EN, DAY_LABELS_RU, DAY_SHORT_EN, DAY_SHORT_RU, DAY_SLUGS

WEEKDAY_INDEX = {slug: index for index, slug in enumerate(DAY_SLUGS)}


def tz() -> ZoneInfo:
    try:
        return ZoneInfo(settings.timezone)
    except Exception:  # noqa: BLE001 — нет tzdata, работаем в локальной зоне
        return ZoneInfo("UTC")


def now_local() -> datetime:
    return datetime.now(tz())


def parse_hhmm(value: str) -> tuple[int, int] | None:
    try:
        hour, minute = value.strip().split(":")
        return int(hour), int(minute)
    except (ValueError, AttributeError):
        return None


def minutes(value: str) -> int | None:
    parsed = parse_hhmm(value)
    return parsed[0] * 60 + parsed[1] if parsed else None


def monday_of(week: dict | None) -> date | None:
    if not week or not week.get("datefrom"):
        return None
    try:
        start = datetime.strptime(week["datefrom"], "%Y-%m-%d").date()
    except ValueError:
        return None
    return start + timedelta(days=1)


def day_meta(week: dict | None, index: int) -> dict[str, Any]:
    """
    Метаданные учебного дня: дата, названия на двух языках.

    `datefrom` учебной недели — воскресенье, поэтому:
      * индексы 0..5 — понедельник..суббота (учебные дни);
      * индекс 6 — воскресенье, которое открывает эту же неделю.
    """
    start = monday_of(week)
    day: date | None = None
    if start:
        day = start + timedelta(days=index) if index <= 5 else start - timedelta(days=1)
    return {
        "idx": index,
        "slug": DAY_SLUGS[index] if 0 <= index < len(DAY_SLUGS) else "day",
        "date": day.isoformat() if day else "",
        "day": day.day if day else 0,
        "month": day.month if day else 0,
        "ru": DAY_LABELS_RU[index] if index < len(DAY_LABELS_RU) else "",
        "en": DAY_LABELS_EN[index] if index < len(DAY_LABELS_EN) else "",
        "ru_short": DAY_SHORT_RU[index] if index < len(DAY_SHORT_RU) else "",
        "en_short": DAY_SHORT_EN[index] if index < len(DAY_SHORT_EN) else "",
    }


def week_number(text: str | None) -> int | None:
    """Достаёт номер недели из заголовка EduPage вида «week 10 / 1.1_26_27 (…)»."""
    match = re.search(r"week\s*(\d+)", text or "", re.IGNORECASE)
    return int(match.group(1)) if match else None


def week_label(week: dict | None) -> str:
    """Человекочитаемый заголовок недели вместо служебной строки EduPage."""
    if not week:
        return ""
    number = week_number(week.get("text"))
    return f"Неделя {number}" if number else (week.get("text") or "")


def week_payload(week: dict | None) -> dict[str, Any] | None:
    if not week:
        return None
    monday = monday_of(week)
    return {
        "tt_num": week.get("tt_num", ""),
        "title": week_label(week),
        "raw_title": week.get("text", ""),
        "number": week_number(week.get("text")),
        "datefrom": week.get("datefrom", ""),
        "dateto": week.get("dateto", ""),
        "monday": monday.isoformat() if monday else "",
        "year": week.get("year", 0),
        "is_default": bool(week.get("is_default")),
    }


def day_grid(kind: str, entity_id: str, week: dict | None) -> list[dict[str, Any]]:
    """Полная сетка недели: 6 дней, в каждом — отсортированные уроки."""
    tt_num = (week or {}).get("tt_num")
    rows = db.schedule(kind, entity_id, tt_num) if tt_num else db.schedule(kind, entity_id)
    buckets: dict[int, list[dict]] = {}
    for row in rows:
        buckets.setdefault(int(row["day_idx"]), []).append(db.lesson_payload(row))
    days = []
    for index in range(6):
        lessons = sorted(buckets.get(index, []), key=lambda item: (item["period"], item["short"]))
        day = day_meta(week, index)
        day["lessons"] = lessons
        day["count"] = len(lessons)
        day["first_start"] = lessons[0]["start"] if lessons else ""
        day["last_end"] = lessons[-1]["end"] if lessons else ""
        days.append(day)
    return days


@dataclass
class UpNext:
    """Ближайшая пара и текущая пара для сущности."""

    moment: datetime
    today: dict[str, Any]
    current: dict[str, Any] | None
    current_day: dict[str, Any] | None
    next: dict[str, Any] | None
    next_day: dict[str, Any] | None
    next_in_minutes: int | None
    current_left_minutes: int | None
    progress: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "now": self.moment.isoformat(timespec="seconds"),
            "today": self.today,
            "current": self.current,
            "current_day": self.current_day,
            "next": self.next,
            "next_day": self.next_day,
            "next_in_minutes": self.next_in_minutes,
            "current_left_minutes": self.current_left_minutes,
            "progress": round(self.progress, 4),
        }


def up_next(kind: str, entity_id: str, moment: datetime | None = None,
            week: dict | None = None) -> UpNext:
    """
    Определяет текущую и ближайшую пару по реальным датам и времени.

    Работает и в воскресенье (когда пар нет), и когда ближайшая пара
    находится в следующей учебной неделе.
    """
    moment = moment or now_local()
    week = week if week is not None else db.current_week(moment.date())
    today_iso = moment.date().isoformat()
    today_index = moment.weekday()

    days = day_grid(kind, entity_id, week)
    today_meta = day_meta(week, today_index)

    todays: list[dict[str, Any]] = []
    for day in days:
        if day["date"] == today_iso:
            todays = day["lessons"]
            today_meta = {**day, "lessons": day["lessons"]}
            break
    else:
        today_meta = {**today_meta, "lessons": []}

    def bounds(day: dict[str, Any], lesson: dict[str, Any]) -> tuple[datetime, datetime] | None:
        if not day.get("date"):
            return None
        try:
            target = datetime.strptime(day["date"], "%Y-%m-%d").date()
        except ValueError:
            return None
        start, end = parse_hhmm(lesson.get("start")), parse_hhmm(lesson.get("end"))
        if not start or not end:
            return None
        zone = moment.tzinfo
        begin = datetime(target.year, target.month, target.day, start[0], start[1], tzinfo=zone)
        finish = datetime(target.year, target.month, target.day, end[0], end[1], tzinfo=zone)
        return begin, finish

    current: dict[str, Any] | None = None
    current_day: dict[str, Any] | None = None
    current_left: int | None = None
    progress = 0.0
    for lesson in sorted(todays, key=lambda item: item.get("period") or 0):
        span = bounds(today_meta, lesson)
        if not span:
            continue
        begin, finish = span
        if begin <= moment < finish:
            current, current_day = lesson, today_meta
            current_left = max(0, int((finish - moment).total_seconds() // 60))
            progress = (moment - begin).total_seconds() / max(1.0, (finish - begin).total_seconds())
            break

    # Ближайшая пара: сначала сегодня, затем — в следующие учебные дни
    nxt: dict[str, Any] | None = None
    nxt_day: dict[str, Any] | None = None
    nxt_in: int | None = None
    upcoming: list[tuple[datetime, dict[str, Any], dict[str, Any]]] = []

    weeks_to_scan = [week] + [
        item for item in db.weeks() if item["tt_num"] != (week or {}).get("tt_num")
    ]

    for index, candidate_week in enumerate(weeks_to_scan):
        grid = days if index == 0 else day_grid(kind, entity_id, candidate_week)
        for day in grid:
            for lesson in day["lessons"]:
                span = bounds(day, lesson)
                if not span:
                    continue
                if span[0] > moment:
                    upcoming.append((span[0], day, lesson))
        if upcoming:
            break

    if upcoming:
        upcoming.sort(key=lambda item: item[0])
        begin, nxt_day, nxt = upcoming[0]
        if nxt_day.get("date") == today_iso:
            nxt_in = max(1, int((begin - moment).total_seconds() // 60))
        else:
            nxt_in = None

    return UpNext(
        moment=moment,
        today={key: value for key, value in today_meta.items() if key != "lessons"},
        current=current,
        current_day=current_day,
        next=nxt,
        next_day=nxt_day,
        next_in_minutes=nxt_in,
        current_left_minutes=current_left,
        progress=progress,
    )


def human_next(up: UpNext, lang: str = "ru") -> str:
    """«Сейчас · EAP» / «Через 25 мин · DELS (lec)» / «Завтра · MUS (lec)»."""
    ru = lang == "ru"
    if up.current:
        left = f" · ещё {up.current_left_minutes} мин" if up.current_left_minutes is not None else ""
        return (f"Сейчас: {up.current['short'] or up.current['subject']}{left}")
    if up.next is None:
        return "Занятий впереди нет" if ru else "No upcoming classes"
    title = up.next["short"] or up.next["subject"]
    if up.next_in_minutes is not None:
        if up.next_in_minutes <= 60:
            return (f"Через {up.next_in_minutes} мин: {title}" if ru
                    else f"In {up.next_in_minutes} min: {title}")
        hours = up.next_in_minutes // 60
        return (f"Через {hours} ч: {title}" if ru else f"In {hours}h: {title}")
    day = up.next_day or {}
    label = day.get("ru" if ru else "en", "")
    tomorrow = up.moment.date() + timedelta(days=1)
    if day.get("date") == tomorrow.isoformat():
        label = "Завтра" if ru else "Tomorrow"
    return f"{label}: {title}"


def offline_bundle(kind: str, entity_id: str) -> dict[str, Any]:
    """Компактный пакет для офлайн-режима: все недели сразу."""
    all_weeks = db.weeks()
    week_map: dict[str, dict[str, Any]] = {}
    for week in all_weeks:
        days = day_grid(kind, entity_id, week)
        payload = week_payload(week)
        payload["days"] = days
        week_map[week["tt_num"]] = payload
    return {
        "kind": kind,
        "entity": db.entity(kind, entity_id),
        "generated_at": now_local().isoformat(timespec="seconds"),
        "updated_at": db.meta().get("updated_at", ""),
        "weeks": week_map,
    }
