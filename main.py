import requests
import json
from datetime import datetime, timedelta

BASE = "https://ttpu.edupage.org/timetable/server"
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://ttpu.edupage.org/timetable/",
    "Origin": "https://ttpu.edupage.org",
}

DAYS = {0: "Понедельник", 1: "Вторник", 2: "Среда",
        3: "Четверг", 4: "Пятница", 5: "Суббота"}

SLOTS = {
    1: "09:00-10:20", 2: "10:30-11:50", 3: "12:00-13:20",
    4: "14:20-15:40", 5: "15:50-17:10", 6: "17:20-18:40",
    7: "18:50-20:10", 8: "20:20-21:40"
}

def post(endpoint, args):
    payload = {
        "__args": json.dumps(args),
        "__gsh": "00000000"
    }
    r = requests.post(f"{BASE}/{endpoint}", data=payload, headers=HEADERS)
    r.raise_for_status()
    return r.json()


def get_all_groups():
    """Возвращает словарь {name: id} всех групп"""
    data = post("ttviewer.js?__func=getTTViewerData", [None, 2025])
    classes = data["r"]["classes"]
    return {c["name"]: c["id"] for c in classes}


def get_timetable_raw(group_id):
    """Сырые данные расписания по ID группы"""
    data = post("regulartt.js?__func=regularttGetData", [None, str(group_id)])
    return data["r"]


def parse_timetable(raw, group_name):
    """Парсит сырые данные в читаемый вид"""
    cards = raw.get("cards", [])
    subjects = {s["id"]: s["name"] for s in raw.get("subjects", [])}
    teachers = {t["id"]: f"{t.get('firstname','').strip()} {t.get('lastname','').strip()}".strip()
                for t in raw.get("teachers", [])}
    classrooms = {c["id"]: c["name"] for c in raw.get("classrooms", [])}

    schedule = {}
    for card in cards:
        day = int(card.get("days", "0"), 2)
        day_idx = day.bit_length() - 1 if day else None
        if day_idx is None or day_idx > 5:
            continue

        period = int(card.get("period", 0))
        subj_id = card.get("subjectid", "")
        teacher_ids = card.get("teacherids", [])
        room_ids = card.get("classroomids", [])

        lesson = {
            "subject": subjects.get(subj_id, subj_id),
            "teacher": ", ".join(teachers.get(tid, tid) for tid in teacher_ids),
            "room": ", ".join(classrooms.get(rid, rid) for rid in room_ids),
            "time": SLOTS.get(period, f"Слот {period}"),
            "period": period,
        }

        if day_idx not in schedule:
            schedule[day_idx] = []
        schedule[day_idx].append(lesson)

    for day_idx in schedule:
        schedule[day_idx].sort(key=lambda x: x["period"])

    return schedule


def print_timetable(schedule, group_name):
    print(f"\n{'='*50}")
    print(f"  Расписание группы: {group_name}")
    print(f"{'='*50}")

    for day_idx in sorted(schedule.keys()):
        print(f"\n{DAYS[day_idx]}:")
        print("-" * 40)
        for lesson in schedule[day_idx]:
            print(f"  {lesson['period']}. {lesson['time']}")
            print(f"     {lesson['subject']}")
            if lesson['teacher']:
                print(f"     Преп: {lesson['teacher']}")
            if lesson['room']:
                print(f"     Ауд:  {lesson['room']}")
    print()


def main():
    print("Загружаем список групп...")
    groups = get_all_groups()

    target = "FY1-25"
    if target not in groups:
        print(f"Группа {target} не найдена!")
        print("Доступные группы:", list(groups.keys()))
        return

    group_id = groups[target]
    print(f"Найдена группа {target} с ID={group_id}")
    print("Загружаем расписание...")

    raw = get_timetable_raw(group_id)
    schedule = parse_timetable(raw, target)
    print_timetable(schedule, target)

    # Сохраняем в JSON
    with open("fy1_25_timetable.json", "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)
    print("Расписание сохранено в fy1_25_timetable.json")


if __name__ == "__main__":
    main()