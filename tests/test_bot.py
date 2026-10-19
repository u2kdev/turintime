"""Проверка бота без Telegram: импорт, клавиатуры, тексты, логика уведомлений."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from turin import db, schedule  # noqa: E402
from turin.bot import keyboards as kb  # noqa: E402
from turin.bot import texts as tx  # noqa: E402
from turin.bot.runner import build_dispatcher  # noqa: E402
from turin.bot import storage  # noqa: E402

print("Логи:")
dispatcher = build_dispatcher()
print("  dispatcher OK, observers:", len(dispatcher.observers))

directory = db.directory()
group = next(item for item in directory["classes"] if item["name"] == "IT1-26")
week = db.current_week()

print("\nКлавиатуры:")
print("  групп:", len(kb.entity_picker("class", directory["classes"][:40]).inline_keyboard), "рядов")
print("  меню:", len(kb.home_kb("class", group["id"]).inline_keyboard), "рядов")
print("  настройки:", len(kb.settings_kb({"notify": 1, "notify_time": "07:30"}).inline_keyboard), "рядов")
days = schedule.day_grid("class", group["id"], week)
print("  дней с парами:", sum(1 for d in days if d["count"]))

print("\nСообщение дня (среда):")
wednesday = days[2]
print(tx.day_message(group["name"], wednesday, wednesday["lessons"], kind="class"))

print("\nСообщение недели:")
print(tx.week_message(group["name"], days, schedule.week_payload(week)))

print("\n«Сейчас/дальше» в разные моменты:")
for label, moment in [
    ("воскресенье 23:00", datetime(2026, 10, 18, 23, 0, tzinfo=schedule.tz())),
    ("понедельник 12:30 (идёт пара)", datetime(2026, 10, 19, 12, 30, tzinfo=schedule.tz())),
    ("понедельник 11:55 (перед парой)", datetime(2026, 10, 19, 11, 55, tzinfo=schedule.tz())),
    ("суббота 09:30", datetime(2026, 10, 24, 9, 30, tzinfo=schedule.tz())),
    ("суббота 22:00 (дальше — след. неделя)", datetime(2026, 10, 24, 22, 0, tzinfo=schedule.tz())),
]:
    up = schedule.up_next("class", group["id"], moment)
    print(f"  {label}: {schedule.human_next(up)}")
    data = up.as_dict()
    if data["current"]:
        print(f"      идёт: {data['current']['short']} прогресс {data['progress']:.0%}, "
              f"осталось {data['current_left_minutes']} мин")
    if data["next"] and data["next_day"]:
        print(f"      дальше: {data['next']['short']} · {data['next_day']['ru']} "
              f"{data['next_day']['date']} · через {data['next_in_minutes']}")

print("\nХранилище:")
storage.init_db()
user = storage.upsert_user(123456, chat_id=123456, username="tester", first_name="Тест", last_name="Тестов")
print("  пользователь:", {k: user[k] for k in ("user_id", "group_name", "notify", "notify_time")})
storage.update(123456, group_id=group["id"], group_name=group["name"], notify=1, notify_time="07:30")
print("  после обновления:", storage.get_user(123456)["group_name"])
print("  статистика:", storage.stats())
print("  подписчиков на рассылку:", len(storage.subscribers("digest")))

up = schedule.up_next("class", group["id"], datetime(2026, 10, 19, 11, 55, tzinfo=schedule.tz()))
print("\nГлавное меню:")
print(tx.home_message(storage.get_user(123456), up.as_dict(), (schedule.week_payload(week) or {})["title"]))
print("\nНастройки:")
print(tx.settings_message(storage.get_user(123456)))
