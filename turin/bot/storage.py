"""Telegram-бот: хранилище пользователей и их настроек."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

from ..config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS tg_users (
    user_id      INTEGER PRIMARY KEY,
    chat_id      INTEGER,
    username     TEXT DEFAULT '',
    first_name   TEXT DEFAULT '',
    last_name    TEXT DEFAULT '',
    group_id     TEXT DEFAULT '',
    group_name   TEXT DEFAULT '',
    notify       INTEGER DEFAULT 0,
    notify_time  TEXT DEFAULT '07:30',
    remind       INTEGER DEFAULT 0,
    remind_minutes INTEGER DEFAULT 15,
    lang         TEXT DEFAULT 'ru',
    created_at   TEXT,
    last_seen    TEXT,
    last_digest  TEXT DEFAULT '',
    last_reminder TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS bot_events (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    kind    TEXT,
    created_at TEXT
);
"""


@contextmanager
def connect(path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    target = Path(path or settings.users_db)
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
        connection.executescript(SCHEMA)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def upsert_user(user_id: int, chat_id: int | None = None, username: str = "",
                first_name: str = "", last_name: str = "") -> dict[str, Any]:
    init_db()
    with connect() as connection:
        row = connection.execute("SELECT * FROM tg_users WHERE user_id=?", (user_id,)).fetchone()
        if row is None:
            connection.execute(
                "INSERT INTO tg_users (user_id,chat_id,username,first_name,last_name,"
                "notify_time,created_at,last_seen) VALUES (?,?,?,?,?,?,?,?)",
                (user_id, chat_id, username, first_name, last_name,
                 settings.daily_default_time, _now(), _now()),
            )
        else:
            connection.execute(
                "UPDATE tg_users SET chat_id=COALESCE(?,chat_id), username=?, first_name=?, "
                "last_name=?, last_seen=? WHERE user_id=?",
                (chat_id, username, first_name, last_name, _now(), user_id),
            )
        row = connection.execute("SELECT * FROM tg_users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row)


def get_user(user_id: int) -> dict[str, Any] | None:
    init_db()
    with connect() as connection:
        row = connection.execute("SELECT * FROM tg_users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def update(user_id: int, **fields: Any) -> None:
    allowed = {
        "group_id", "group_name", "notify", "notify_time", "remind",
        "remind_minutes", "lang", "last_digest", "last_reminder",
    }
    pairs = {key: value for key, value in fields.items() if key in allowed}
    if not pairs:
        return
    init_db()
    columns = ", ".join(f"{key}=?" for key in pairs)
    with connect() as connection:
        connection.execute(
            f"UPDATE tg_users SET {columns}, last_seen=? WHERE user_id=?",
            (*pairs.values(), _now(), user_id),
        )


def subscribers(kind: str) -> list[dict[str, Any]]:
    """Пользователи с включёнными уведомлениями (notify) или напоминаниями (remind)."""
    init_db()
    column = "notify" if kind == "digest" else "remind"
    with connect() as connection:
        rows = connection.execute(
            f"SELECT * FROM tg_users WHERE {column}=1 AND group_id!='' ORDER BY user_id"
        ).fetchall()
        return [dict(row) for row in rows]


def stats() -> dict[str, Any]:
    init_db()
    with connect() as connection:
        total = connection.execute("SELECT COUNT(*) AS n FROM tg_users").fetchone()["n"]
        with_group = connection.execute(
            "SELECT COUNT(*) AS n FROM tg_users WHERE group_id!=''"
        ).fetchone()["n"]
        today = date.today().isoformat()
        active = connection.execute(
            "SELECT COUNT(*) AS n FROM tg_users WHERE last_seen LIKE ?", (f"{today}%",)
        ).fetchone()["n"]
        groups = [
            dict(row)
            for row in connection.execute(
                "SELECT group_name, COUNT(*) AS n FROM tg_users WHERE group_name!='' "
                "GROUP BY group_name ORDER BY n DESC LIMIT 8"
            ).fetchall()
        ]
        return {"total": total, "with_group": with_group, "active_today": active, "top_groups": groups}
