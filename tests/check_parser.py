"""Проверка парсера: сверяем FYL1-26 с тем, что показывает сайт EduPage."""
import asyncio
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from turin import db  # noqa: E402
from turin.config import settings  # noqa: E402
from turin.edupage import DAY_BITS, fetch_parsed_weeks  # noqa: E402
from turin import sync  # noqa: E402


async def main() -> None:
    result = await sync.refresh()
    print("SYNC:", result)

    target = None
    for item in db.directory()["classes"]:
        if item["name"] == "FYL1-26":
            target = item
    print("Класс:", target)

    week = db.current_week()
    print("Текущая неделя:", week)

    rows = db.schedule("class", target["id"], week["tt_num"])
    grid: dict[int, list] = defaultdict(list)
    for row in rows:
        grid[row["day_idx"]].append(db.lesson_payload(row))

    for idx, bits in enumerate(DAY_BITS):
        items = sorted(grid.get(idx, []), key=lambda x: x["period"])
        print(f"\n{bits} (day {idx}):")
        for lesson in items:
            teachers = ", ".join(t["short"] for t in lesson["teachers"])
            rooms = ", ".join(r["name"] for r in lesson["rooms"])
            groups = f" [{','.join(lesson['groups'])}]" if lesson["groups"] else ""
            print(f"   {lesson['period']}. {lesson['start']}-{lesson['end']} "
                  f"{lesson['short']}{groups} | {teachers} | {rooms}")

    print("\nВсего строк:", len(rows))
    # полнота: сколько строк по каждой аудитории/преподавателю
    info = db.directory()
    print("Групп:", len(info["classes"]), "преподавателей:", len(info["teachers"]),
          "аудиторий:", len(info["classrooms"]), "предметов:", len(info["subjects"]))
    print("Периоды:", info["periods"])
    print("Популярные группы:", [(c["name"], c["n"]) for c in db.popular_classes(6)])
    print("Поиск 'IT':", db.search("it1"))
    t = info["teachers"][0]
    print("Пример преподавателя:", t, "занятий:",
          len(db.schedule("teacher", t["id"], week["tt_num"])))
    r = info["classrooms"][0]
    print("Пример аудитории:", r, "занятий:",
          len(db.schedule("room", r["id"], week["tt_num"])))


asyncio.run(main())
