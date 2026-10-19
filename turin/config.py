"""
Конфигурация проекта TTPU Timetable.

Все настройки читаются из переменных окружения и/или файла .env
рядом с корнем проекта. Файл .env.example содержит полный список.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Минимальная загрузка .env без внешних зависимостей."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_dotenv(ROOT / ".env")


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    try:
        return int(_env(key) or default)
    except ValueError:
        return default


def _env_bool(key: str, default: bool = False) -> bool:
    value = _env(key).lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _env_path(key: str, default: str) -> Path:
    path = Path(_env(key) or default)
    return path if path.is_absolute() else ROOT / path


@dataclass(frozen=True)
class Settings:
    # ── источники данных ───────────────────────────────────────────────
    edupage_origin: str = _env("EDUPAGE_ORIGIN", "https://ttpu.edupage.org")
    school_name: str = _env("SCHOOL_NAME", "Turin Polytechnic University in Tashkent")
    school_short: str = _env("SCHOOL_SHORT", "TTPU")
    timezone: str = _env("TIMEZONE", "Asia/Tashkent")

    # ── сервер ─────────────────────────────────────────────────────────
    host: str = _env("HOST", "0.0.0.0")
    port: int = _env_int("PORT", 8000)
    base_url: str = _env("BASE_URL", "http://localhost:8000")
    secret_key: str = _env("SECRET_KEY", "ttpu-timetable-dev-secret")
    admin_token: str = _env("ADMIN_TOKEN", "")
    refresh_hours: int = _env_int("REFRESH_HOURS", 6)
    refresh_on_start: bool = _env_bool("REFRESH_ON_START", True)

    # ── telegram ───────────────────────────────────────────────────────
    bot_token: str = _env("BOT_TOKEN", "")
    bot_username: str = _env("BOT_USERNAME", "")
    run_bot: bool = _env_bool("RUN_BOT", True)
    daily_default_time: str = _env("DAILY_DEFAULT_TIME", "07:30")
    reminder_minutes: int = _env_int("REMINDER_MINUTES", 15)

    # ── файлы ──────────────────────────────────────────────────────────
    data_dir: Path = _env_path("DATA_DIR", "data")
    timetable_db: Path = _env_path("TIMETABLE_DB", "data/timetable.db")
    users_db: Path = _env_path("USERS_DB", "data/users.db")
    web_dir: Path = ROOT / "web"

    @property
    def api_base(self) -> str:
        return f"{self.edupage_origin.rstrip('/')}/timetable/server"

    @property
    def referer(self) -> str:
        return f"{self.edupage_origin.rstrip('/')}/"


settings = Settings()

__all__ = ["settings", "Settings", "ROOT"]
