"""
Слой хранения: SQLite со справочниками и плоскими строками расписания.

Расписание хранится «денормализованно»: одна поездка урока превращается
в несколько строк — по одной на каждую группу, преподавателя и аудиторию.
Это даёт мгновенные выборки по любому срезу.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from .config import settings
from .edupage import KIND_CLASS, KIND_ROOM, KIND_TEACHER, ParsedWeek, WeekRef

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS weeks (
    tt_num     TEXT PRIMARY KEY,
    text       TEXT,
    datefrom   TEXT,
    dateto     TEXT,
    year       INTEGER DEFAULT 0,
    is_default INTEGER DEFAULT 0,
    position   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS classes (
    id   TEXT PRIMARY KEY,
    name TEXT, short TEXT, color TEXT, bell TEXT
);

CREATE TABLE IF NOT EXISTS teachers (
    id   TEXT PRIMARY KEY,
    name TEXT, short TEXT, color TEXT
);

CREATE TABLE IF NOT EXISTS classrooms (
    id   TEXT PRIMARY KEY,
    name TEXT, short TEXT, color TEXT
);

CREATE TABLE IF NOT EXISTS subjects (
    id   TEXT PRIMARY KEY,
    name TEXT, short TEXT, color TEXT
);

CREATE TABLE IF NOT EXISTS periods (
    period INTEGER PRIMARY KEY,
    name   TEXT,
    start  TEXT,
    end    TEXT
);

CREATE TABLE IF NOT EXISTS lessons (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    week        TEXT NOT NULL,
    owner_kind  TEXT NOT NULL,
    owner_id    TEXT NOT NULL,
    day_idx     INTEGER NOT NULL,
    period      INTEGER NOT NULL,
    start       TEXT,
    end         TEXT,
    subject_id  TEXT,
    subject     TEXT,
    subject_short TEXT,
    color       TEXT,
    teachers    TEXT,
    rooms       TEXT,
    classes     TEXT,
    groups      TEXT,
    lesson_key  TEXT
);

CREATE INDEX IF NOT EXISTS idx_lessons_owner ON lessons(owner_kind, owner_id, week, day_idx, period);
CREATE INDEX IF NOT EXISTS idx_lessons_week  ON lessons(week);
"""

_ANIMALS_LOCK = threading.Lock()


@contextmanager
def connect(path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    target = Path(path or settings.timetable_db)
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db(path: Path | str | None = None) -> None:
    with connect(path) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript(SCHEMA)


def is_ready(path: Path | str | None = None) -> bool:
    target = Path(path or settings.timetable_db)
    if not target.is_file():
        return False
    try:
        with connect(target) as connection:
            row = connection.execute("SELECT COUNT(*) AS n FROM lessons").fetchone()
        return bool(row and row["n"])
    except sqlite3.Error:
        return False


# ────────────────────────────────────────────────────────────────────────────
# Запись
# ────────────────────────────────────────────────────────────────────────────
def store(
    weeks: Sequence[WeekRef],
    parsed: Sequence[ParsedWeek],
    source: str = "",
    path: Path | str | None = None,
) -> dict[str, int]:
    """Полностью заменяет содержимое базы свежими данными (в одной транзакции)."""
    by_num = {week.tt_num: week for week in weeks}
    lessons_total = 0

    with connect(path) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript(SCHEMA)
        connection.execute("BEGIN IMMEDIATE")
        try:
            for table in ("lessons", "weeks", "classes", "teachers", "classrooms", "subjects", "periods"):
                connection.execute(f"DELETE FROM {table}")

            classes: dict[str, tuple] = {}
            teachers: dict[str, tuple] = {}
            classrooms: dict[str, tuple] = {}
            subjects: dict[str, tuple] = {}
            periods: dict[str, tuple] = {}

            for week in parsed:
                for row in week.classes:
                    classes[row["id"]] = (
                        row["id"], row.get("name", ""), row.get("short", ""),
                        row.get("color", ""), row.get("bell", "0"),
                    )
                for row in week.teachers:
                    teachers[row["id"]] = (row["id"], row.get("name", ""), row.get("short", ""), row.get("color", ""))
                for row in week.classrooms:
                    classrooms[row["id"]] = (row["id"], row.get("name", ""), row.get("short", ""), row.get("color", ""))
                for row in week.subjects:
                    subjects[row["id"]] = (row["id"], row.get("name", ""), row.get("short", ""), row.get("color", ""))
                for row in week.periods:
                    periods[str(row["period"])] = (int(row["period"]), row.get("name", ""), row.get("start", ""), row.get("end", ""))

            connection.executemany("INSERT OR REPLACE INTO classes    VALUES (?,?,?,?,?)", classes.values())
            connection.executemany("INSERT OR REPLACE INTO teachers   VALUES (?,?,?,?)", teachers.values())
            connection.executemany("INSERT OR REPLACE INTO classrooms VALUES (?,?,?,?)", classrooms.values())
            connection.executemany("INSERT OR REPLACE INTO subjects   VALUES (?,?,?,?)", subjects.values())
            connection.executemany("INSERT OR REPLACE INTO periods    VALUES (?,?,?,?)", periods.values())

            ordered = sorted(by_num.values(), key=lambda item: (item.datefrom or "", item.tt_num))
            for position, week in enumerate(ordered):
                week = by_num[week.tt_num]
                if not week.date_to:
                    week.datefrom = week.datefrom
                connection.execute(
                    "INSERT OR REPLACE INTO weeks (tt_num,text,datefrom,dateto,year,is_default,position) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (
                        week.tt_num, week.text,
                        week.datefrom, week.date_to,
                        week.year, 1 if week.is_default else 0, position,
                    ),
                )

            batch = []
            for week in parsed:
                for row in week.lessons:
                    batch.append((
                        row.week, row.owner_kind, row.owner_id, row.day_idx, row.period,
                        row.start, row.end, row.subject_id, row.subject, row.subject_short,
                        row.color,
                        json.dumps(row.teachers, ensure_ascii=False),
                        json.dumps(row.rooms, ensure_ascii=False),
                        json.dumps(row.classes, ensure_ascii=False),
                        json.dumps(row.groups, ensure_ascii=False),
                        row.lesson_key,
                    ))
                    lessons_total += 1
            connection.executemany(
                "INSERT INTO lessons (week,owner_kind,owner_id,day_idx,period,start,end,"
                "subject_id,subject,subject_short,color,teachers,rooms,classes,groups,lesson_key) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                batch,
            )

            now = datetime.now().isoformat(timespec="seconds")
            for key, value in {
                "updated_at": now,
                "source": source,
                "lessons": str(lessons_total),
                "weeks": str(len(parsed)),
                "classes": str(len(classes)),
                "teachers": str(len(teachers)),
                "classrooms": str(len(classrooms)),
            }.items():
                connection.execute("INSERT OR REPLACE INTO meta (key,value) VALUES (?,?)", (key, value))

            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise

    return {
        "lessons": lessons_total,
        "weeks": len(parsed),
        "classes": len(classes),
        "teachers": len(teachers),
        "classrooms": len(classrooms),
        "subjects": len(subjects),
    }


# ────────────────────────────────────────────────────────────────────────────
# Чтение
# ────────────────────────────────────────────────────────────────────────────
def _rows(connection: sqlite3.Connection, sql: str, params: Sequence[Any] = ()) -> list[dict]:
    return [dict(row) for row in connection.execute(sql, params).fetchall()]


def meta(path: Path | str | None = None) -> dict[str, str]:
    with connect(path) as connection:
        try:
            return {row["key"]: row["value"] for row in connection.execute("SELECT key,value FROM meta")}
        except sqlite3.Error:
            return {}


def weeks(path: Path | str | None = None) -> list[dict]:
    with connect(path) as connection:
        return _rows(connection, "SELECT * FROM weeks ORDER BY position, datefrom")


def current_week(day: date | None = None, path: Path | str | None = None) -> dict | None:
    """Неделя, в которую попадает дата (иначе — неделя по умолчанию)."""
    day = day or date.today()
    all_weeks = weeks(path)
    if not all_weeks:
        return None
    iso = day.isoformat()
    for week in all_weeks:
        end = week["dateto"] or _plus(week["datefrom"], 6)
        if week["datefrom"] and end and week["datefrom"] <= iso <= end:
            return week
    for week in all_weeks:
        if week["is_default"]:
            return week
    return all_weeks[0]


def week_by_number(tt_num: str, path: Path | str | None = None) -> dict | None:
    with connect(path) as connection:
        row = connection.execute("SELECT * FROM weeks WHERE tt_num=?", (str(tt_num),)).fetchone()
        return dict(row) if row else None


def _plus(iso: str, days: int) -> str:
    try:
        return (datetime.strptime(iso, "%Y-%m-%d").date() + timedelta(days=days)).isoformat()
    except (ValueError, TypeError):
        return ""


def directory(path: Path | str | None = None) -> dict[str, list[dict]]:
    with connect(path) as connection:
        return {
            "classes": _rows(connection, "SELECT id,name,short,color FROM classes"),
            "teachers": _rows(connection, "SELECT id,name,short,color FROM teachers"),
            "classrooms": _rows(connection, "SELECT id,name,short,color FROM classrooms"),
            "subjects": _rows(connection, "SELECT id,name,short,color FROM subjects"),
            "periods": _rows(connection, "SELECT period,name,start,end FROM periods ORDER BY period"),
        }


def entity(kind: str, entity_id: str, path: Path | str | None = None) -> dict | None:
    table = {"class": "classes", "teacher": "teachers", "room": "classrooms"}.get(kind)
    if not table:
        return None
    with connect(path) as connection:
        row = connection.execute(
            f"SELECT id,name,short,color FROM {table} WHERE id=?", (entity_id,)
        ).fetchone()
        return dict(row) if row else None


def schedule(
    kind: str,
    entity_id: str,
    week: str | None = None,
    path: Path | str | None = None,
) -> list[dict]:
    sql = (
        "SELECT * FROM lessons WHERE owner_kind=? AND owner_id=?"
        + (" AND week=?" if week else "")
        + " ORDER BY day_idx, period, subject"
    )
    params: list[Any] = [kind, entity_id]
    if week:
        params.append(str(week))
    with connect(path) as connection:
        return _rows(connection, sql, params)


def search(query: str, limit: int = 24, path: Path | str | None = None) -> list[dict]:
    needle = f"%{query.strip().lower()}%"
    if len(needle) < 3:
        return []
    results: list[dict] = []
    with connect(path) as connection:
        for table, kind in (("classes", KIND_CLASS), ("teachers", KIND_TEACHER), ("classrooms", KIND_ROOM)):
            rows = connection.execute(
                f"SELECT id,name,short,color FROM {table} "
                "WHERE lower(name) LIKE ? OR lower(short) LIKE ? ORDER BY name LIMIT ?",
                (needle, needle, limit),
            ).fetchall()
            for row in rows:
                results.append({"kind": kind, "id": row["id"], "name": row["name"],
                                "short": row["short"], "color": row["color"]})
    return results


def popular_classes(limit: int = 12, path: Path | str | None = None) -> list[dict]:
    """Группы с наибольшим числом занятий — для быстрого доступа."""
    with connect(path) as connection:
        return _rows(
            connection,
            "SELECT c.id, c.name, c.short, c.color, COUNT(l.id) AS n "
            "FROM classes c LEFT JOIN lessons l "
            "  ON l.owner_kind='class' AND l.owner_id=c.id "
            "GROUP BY c.id ORDER BY n DESC, c.name LIMIT ?",
            (limit,),
        )


def load_map(week: str | None = None, path: Path | str | None = None) -> dict[str, int]:
    """Сколько занятий у каждой группы/преподавателя/аудитории за неделю."""
    sql = "SELECT owner_kind, owner_id, COUNT(*) AS n FROM lessons"
    params: list[Any] = []
    if week:
        sql += " WHERE week=?"
        params.append(str(week))
    sql += " GROUP BY owner_kind, owner_id"
    with connect(path) as connection:
        rows = connection.execute(sql, params).fetchall()
    return {f"{row['owner_kind']}:{row['owner_id']}": int(row["n"]) for row in rows}


def lesson_payload(row: dict) -> dict:
    """Компактное представление строки урока для API/бота."""
    return {
        "key": row.get("lesson_key") or "",
        "period": row.get("period"),
        "start": row.get("start") or "",
        "end": row.get("end") or "",
        "subject": row.get("subject") or "",
        "short": row.get("subject_short") or row.get("subject") or "",
        "color": row.get("color") or "",
        "teachers": json.loads(row.get("teachers") or "[]"),
        "rooms": json.loads(row.get("rooms") or "[]"),
        "classes": json.loads(row.get("classes") or "[]"),
        "groups": json.loads(row.get("groups") or "[]"),
    }


def day_of_lessons(rows: Iterable[dict]) -> dict[int, list[dict]]:
    result: dict[int, list[dict]] = {}
    for row in rows:
        result.setdefault(int(row["day_idx"]), []).append(lesson_payload(row))
    return result
