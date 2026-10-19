"""
Клиент и парсер расписания aSc EduPage (ttpu.edupage.org).

Публичный API EduPage принимает POST-запросы с JSON-телом:

    POST {origin}/timetable/server/regulartt.js?__func=regularttGetData
    Content-Type: application/json
    {"__args": [null, "463"], "__gsh": "00000000"}

Ответ содержит «таблицы» (classes, teachers, classrooms, subjects,
periods, bells, lessons, cards, ...), из которых собирается расписание.
Никакого браузера (Playwright/Selenium) для этого не требуется.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable, Sequence

import httpx

from .config import settings

log = logging.getLogger("turin.edupage")

# Индекс дня недели -> aSc-битовая строка (понедельник первым)
DAY_BITS = ["100000", "010000", "001000", "000100", "000010", "000001"]
DAY_SLUGS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_LABELS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
DAY_LABELS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_SHORT_RU = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
DAY_SHORT_EN = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

KIND_CLASS = "class"
KIND_TEACHER = "teacher"
KIND_ROOM = "room"
KINDS = (KIND_CLASS, KIND_TEACHER, KIND_ROOM)


class EduPageError(RuntimeError):
    pass


# ────────────────────────────────────────────────────────────────────────────
# Модели
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class WeekRef:
    tt_num: str
    text: str = ""
    datefrom: str = ""
    year: int = 0
    is_default: bool = False

    @property
    def title(self) -> str:
        """«week 10 / 1.1_26_27 (18/10 - 25/10/2026)» -> человекочитаемо."""
        raw = self.text or ""
        match = re.search(r"\(([^)]*)\)", raw)
        span = match.group(1).strip() if match else ""
        if span:
            span = span.replace("/", ".").replace(" - ", " — ").replace("-", "—")
            span = re.sub(r"\s+", " ", span)
        label = raw.split("/")[0].strip().title() if raw else ""
        if label and span:
            return f"{label} · {span}"
        return label or span or f"Неделя {self.tt_num}"

    @property
    def date_to(self) -> str:
        """Суббота учебной недели (datefrom — воскресенье)."""
        return _shift(self.datefrom, 6)

    @property
    def monday(self) -> str:
        """Дата первого учебного дня недели."""
        return _shift(self.datefrom, 1)


def _shift(iso: str, days: int) -> str:
    try:
        start = datetime.strptime(iso, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return ""
    return date.fromordinal(start.toordinal() + days).isoformat()


@dataclass
class LessonRow:
    week: str
    owner_kind: str
    owner_id: str
    day_idx: int
    period: int
    start: str
    end: str
    subject_id: str
    subject: str
    subject_short: str
    color: str
    teachers: list[dict[str, str]] = field(default_factory=list)
    rooms: list[dict[str, str]] = field(default_factory=list)
    classes: list[dict[str, str]] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    lesson_key: str = ""


@dataclass
class ParsedWeek:
    week: WeekRef
    classes: list[dict[str, str]] = field(default_factory=list)
    teachers: list[dict[str, str]] = field(default_factory=list)
    classrooms: list[dict[str, str]] = field(default_factory=list)
    subjects: list[dict[str, str]] = field(default_factory=list)
    periods: list[dict[str, str]] = field(default_factory=list)
    lessons: list[LessonRow] = field(default_factory=list)


# ────────────────────────────────────────────────────────────────────────────
# Клиент
# ────────────────────────────────────────────────────────────────────────────
class EduPageClient:
    """Асинхронный клиент публичного JSON-API расписания."""

    def __init__(self, origin: str | None = None, timeout: float = 45.0) -> None:
        self.origin = (origin or settings.edupage_origin).rstrip("/")
        self.api = f"{self.origin}/timetable/server"
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": f"{self.origin}/",
            "Origin": self.origin,
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        }

    async def _post(self, endpoint: str, args: Sequence[Any], tries: int = 3) -> dict:
        payload = {"__args": list(args), "__gsh": "00000000"}
        last: Exception | None = None
        for attempt in range(1, tries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout, headers=self.headers, follow_redirects=True
                ) as client:
                    response = await client.post(f"{self.api}/{endpoint}", json=payload)
                    response.raise_for_status()
                    data = response.json()
                if isinstance(data, dict) and data.get("reload"):
                    raise EduPageError("EduPage вернул reload=true (неактуальный запрос)")
                return data
            except Exception as exc:  # noqa: BLE001 — нужен ретрай на любые сетевые сбои
                last = exc
                log.warning("EduPage %s: попытка %s/%s не удалась: %s", endpoint, attempt, tries, exc)
                if attempt < tries:
                    await asyncio.sleep(1.5 * attempt)
        raise EduPageError(f"Не удалось получить {endpoint}: {last}")

    # ── API ────────────────────────────────────────────────────────────────
    async def fetch_weeks(self, years: Iterable[int] | None = None) -> tuple[list[WeekRef], str]:
        """Список учебных недель и номер недели по умолчанию."""
        candidates = list(years) if years else school_year_candidates()
        for year in candidates:
            try:
                data = await self._post("ttviewer.js?__func=getTTViewerData", [None, year])
            except EduPageError as exc:
                log.warning("getTTViewerData(%s): %s", year, exc)
                continue
            regular = ((data or {}).get("r") or {}).get("regular") or {}
            items = regular.get("timetables") or []
            weeks = [
                WeekRef(
                    tt_num=str(item.get("tt_num")),
                    text=item.get("text") or "",
                    datefrom=item.get("datefrom") or "",
                    year=int(item.get("year") or year),
                    is_default=str(item.get("tt_num")) == str(regular.get("default_num")),
                )
                for item in items
                if item.get("tt_num") and not item.get("hidden")
            ]
            if weeks:
                return weeks, str(regular.get("default_num") or "")
        raise EduPageError("EduPage не вернул список недель ни для одного года")

    async def fetch_tables(self, tt_num: str) -> dict[str, Any]:
        """Сырые таблицы одной учебной недели."""
        data = await self._post("regulartt.js?__func=regularttGetData", [None, str(tt_num)])
        root = data.get("r") or {}
        accessor = root.get("dbiAccessorRes") or {}
        tables = accessor.get("tables")
        if not tables:
            raise EduPageError(f"Пустой ответ расписания для недели {tt_num}")
        return {table.get("id"): table.get("data_rows") or [] for table in tables}


def school_year_candidates(today: date | None = None) -> list[int]:
    """
    EduPage нумерует данные годом начала учебного года (август-июль),
    поэтому в сентябре-декабре это текущий год, а в январе-июле — прошлый.
    """
    today = today or date.today()
    primary = today.year if today.month >= 8 else today.year - 1
    return [primary, today.year, primary + 1, primary - 1]


# ────────────────────────────────────────────────────────────────────────────
# Парсер
# ────────────────────────────────────────────────────────────────────────────
def _txt(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _person(row: dict) -> dict[str, str]:
    return {
        "id": _txt(row.get("id")),
        "name": _txt(row.get("name")),
        "short": _txt(row.get("short")) or _txt(row.get("name")),
        "color": _txt(row.get("color")),
    }


def _place(row: dict) -> dict[str, str]:
    return {
        "id": _txt(row.get("id")),
        "name": _txt(row.get("name")),
        "short": _txt(row.get("short")) or _txt(row.get("name")),
        "color": _txt(row.get("color")),
    }


def day_index(bits: str) -> int | None:
    """'000010' -> 4 (пятница). Пустая строка/без единиц -> None."""
    bits = _txt(bits)
    if not bits or "1" not in bits:
        return None
    position = bits.index("1")
    if len(bits) == 6:
        return position
    # На случай 7-битной маски (вс..сб) — сдвигаем на день назад
    return max(0, position - (len(bits) - 6))


def parse_week(tables: dict[str, list[dict]], week: WeekRef) -> ParsedWeek:
    """Преобразует сырые таблицы EduPage в плоские строки расписания."""
    parsed = ParsedWeek(week=week)

    classes = {_txt(row.get("id")): row for row in tables.get("classes", [])}
    teachers = {_txt(row.get("id")): row for row in tables.get("teachers", [])}
    classrooms = {_txt(row.get("id")): row for row in tables.get("classrooms", [])}
    subjects = {_txt(row.get("id")): row for row in tables.get("subjects", [])}
    lessons = {_txt(row.get("id")): row for row in tables.get("lessons", [])}
    groups = {_txt(row.get("id")): row for row in tables.get("groups", [])}
    periods = {_txt(row.get("id")) or _txt(row.get("period")): row for row in tables.get("periods", [])}
    bells = {_txt(row.get("id")): row for row in tables.get("bells", [])}

    # ── справочники ────────────────────────────────────────────────────
    parsed.subjects = [
        {
            "id": _txt(row.get("id")),
            "name": _txt(row.get("name")),
            "short": _txt(row.get("short")) or _txt(row.get("name")),
            "color": _txt(row.get("color")),
        }
        for row in tables.get("subjects", [])
        if _txt(row.get("id"))
    ]
    parsed.teachers = [_person(row) for row in tables.get("teachers", []) if _txt(row.get("id"))]
    parsed.classrooms = [
        {**_place(row), "short": _place(row)["short"]}
        for row in tables.get("classrooms", [])
        if _txt(row.get("id"))
    ]
    parsed.classes = []
    for row in tables.get("classes", []):
        cid = _txt(row.get("id"))
        if not cid:
            continue
        parsed.classes.append(
            {
                **_place(row),
                "bell": _txt(row.get("bell")) or "0",
            }
        )

    default_times: dict[int, tuple[str, str]] = {}
    for period_id, row in periods.items():
        try:
            number = int(row.get("period") or period_id)
        except (TypeError, ValueError):
            continue
        default_times[number] = (_txt(row.get("starttime")), _txt(row.get("endtime")))
        parsed.periods.append(
            {
                "period": str(number),
                "name": _txt(row.get("name")) or f"{number}.",
                "start": _txt(row.get("starttime")),
                "end": _txt(row.get("endtime")),
            }
        )
    parsed.periods.sort(key=lambda item: int(item["period"]))

    def times_for(period: int, bell_id: str) -> tuple[str, str]:
        bell = bells.get(_txt(bell_id))
        if bell:
            override = (bell.get("perioddata") or {}).get(str(period)) or {}
            start, end = _txt(override.get("starttime")), _txt(override.get("endtime"))
            if start or end:
                return start, end
        return default_times.get(period, ("", ""))

    # ── уроки ──────────────────────────────────────────────────────────
    rows: list[LessonRow] = []
    for card in tables.get("cards", []):
        days = _txt(card.get("days"))
        period_raw = _txt(card.get("period"))
        lesson = lessons.get(_txt(card.get("lessonid")))
        if not days or not period_raw or not lesson:
            continue
        idx = day_index(days)
        if idx is None or idx > 5:
            continue
        try:
            period = int(period_raw)
        except ValueError:
            continue

        subject = subjects.get(_txt(lesson.get("subjectid")), {})
        room_ids = [_txt(rid) for rid in (card.get("classroomids") or []) if _txt(rid)]
        teacher_ids = [_txt(tid) for tid in (lesson.get("teacherids") or []) if _txt(tid)]
        class_ids = [_txt(cid) for cid in (lesson.get("classids") or []) if _txt(cid)]
        if not class_ids:
            class_ids = sorted(
                {
                    _txt(groups.get(gid, {}).get("classid"))
                    for gid in (lesson.get("groupids") or [])
                    if _txt(groups.get(gid, {}).get("classid"))
                }
            )

        row_teachers = [
            {
                "id": tid,
                "name": _txt(teachers.get(tid, {}).get("name")) or tid,
                "short": _txt(teachers.get(tid, {}).get("short")) or _txt(teachers.get(tid, {}).get("name")) or tid,
            }
            for tid in teacher_ids
        ]
        row_rooms = [
            {
                "id": rid,
                "name": _txt(classrooms.get(rid, {}).get("name")) or rid,
                "short": _txt(classrooms.get(rid, {}).get("short")) or _txt(classrooms.get(rid, {}).get("name")) or rid,
            }
            for rid in room_ids
        ]
        row_classes = [
            {
                "id": cid,
                "name": _txt(classes.get(cid, {}).get("name")) or cid,
                "short": _txt(classes.get(cid, {}).get("short")) or _txt(classes.get(cid, {}).get("name")) or cid,
                "color": _txt(classes.get(cid, {}).get("color")),
            }
            for cid in class_ids
        ]

        # Подгруппы («Group 1», «Boys» и т.п.) — если урок идёт не для всей группы
        group_labels: list[str] = []
        classdata = lesson.get("classdata") or {}
        for cid in class_ids:
            info = classdata.get(cid) or {}
            for gid in (info.get("groupids") or []):
                label = _txt(groups.get(_txt(gid), {}).get("name"))
                if label and label.lower() not in {"entire class", "весь класс"} and label not in group_labels:
                    group_labels.append(label)
        if not group_labels:
            referenced = [_txt(gid) for gid in (lesson.get("groupids") or []) if _txt(gid)]
            if len(referenced) == 1:
                label = _txt(groups.get(referenced[0], {}).get("name"))
                if label and label.lower() not in {"entire class", "весь класс"}:
                    group_labels = [label]

        base = dict(
            week=week.tt_num,
            day_idx=idx,
            period=period,
            subject_id=_txt(lesson.get("subjectid")),
            subject=_txt(subject.get("name")),
            subject_short=_txt(subject.get("short")) or _txt(subject.get("name")),
            color=_txt(subject.get("color")),
            teachers=row_teachers,
            rooms=row_rooms,
            classes=row_classes,
            groups=group_labels,
            lesson_key=_txt(lesson.get("id")) or _txt(card.get("id")),
        )

        owners: list[tuple[str, str, str]] = []
        for cid in class_ids:
            owners.append((KIND_CLASS, cid, _txt(classes.get(cid, {}).get("bell")) or "0"))
        for tid in teacher_ids:
            owners.append((KIND_TEACHER, tid, "0"))
        for rid in room_ids:
            owners.append((KIND_ROOM, rid, "0"))

        seen_owner: set[tuple[str, str]] = set()
        for kind, owner_id, bell_id in owners:
            if not owner_id or (kind, owner_id) in seen_owner:
                continue
            seen_owner.add((kind, owner_id))
            start, end = times_for(period, bell_id)
            rows.append(
                LessonRow(
                    owner_kind=kind,
                    owner_id=owner_id,
                    start=start,
                    end=end,
                    **base,
                )
            )

    rows.sort(key=lambda item: (item.owner_kind, item.owner_id, item.day_idx, item.period))
    parsed.lessons = rows
    return parsed


async def fetch_parsed_weeks(client: EduPageClient | None = None) -> tuple[list[WeekRef], list[ParsedWeek]]:
    """Скачивает и разбирает все доступные учебные недели."""
    client = client or EduPageClient()
    weeks, _default = await client.fetch_weeks()
    parsed: list[ParsedWeek] = []
    for week in weeks:
        try:
            tables = await client.fetch_tables(week.tt_num)
        except EduPageError as exc:
            log.error("Неделя %s: %s", week.tt_num, exc)
            continue
        parsed.append(parse_week(tables, week))
    if not parsed:
        raise EduPageError("Ни одну неделю не удалось загрузить")
    return weeks, parsed
