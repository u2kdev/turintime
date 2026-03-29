"""
TTPU Timetable Scraper
pip install playwright && playwright install chromium
"""
import sys
import asyncio, sqlite3, os
from datetime import datetime
from playwright.async_api import async_playwright

# Fix Unicode encoding on Windows (cp1251 doesn't support checkmarks etc.)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_URL     = "https://ttpu.edupage.org/timetable/"
TIMETABLE_DB = os.getenv("TIMETABLE_DB", "data/timetable.db")

SLOTS = {
    "1":("09:00","10:20"), "2":("10:30","11:50"), "3":("12:00","13:20"),
    "4":("14:20","15:40"), "5":("15:50","17:10"), "6":("17:20","18:40"),
    "7":("18:50","20:10"), "8":("20:20","21:40"),
}
DAYS_MAP  = {"100000":0,"010000":1,"001000":2,"000100":3,"000010":4,"000001":5}
DAY_NAMES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]

def parse_all(raw: dict) -> dict:
    tables     = {t["id"]: t for t in raw.get("dbiAccessorRes",{}).get("tables",[])}
    def rows(tid): return tables.get(tid,{}).get("data_rows",[])

    subjects   = {r["id"]: r for r in rows("subjects")}
    teachers   = {r["id"]: r for r in rows("teachers")}
    classrooms = {r["id"]: r for r in rows("classrooms")}
    classes    = {r["id"]: r for r in rows("classes")}
    lessons    = {r["id"]: r for r in rows("lessons")}
    schedule   = {}

    for card in rows("cards"):
        days_str  = card.get("days","")
        period    = str(card.get("period",""))
        room_ids  = card.get("classroomids",[])
        lesson_id = card.get("lessonid","")
        if not days_str or not period or not lesson_id: continue
        lesson = lessons.get(lesson_id)
        if not lesson: continue
        slot    = SLOTS.get(period,("",""))
        day_idx = DAYS_MAP.get(days_str)
        if day_idx is None: continue
        subj      = subjects.get(lesson.get("subjectid",""),{})
        teach_ids = lesson.get("teacherids",[])
        class_ids = lesson.get("classids",[])
        teacher_name = ", ".join(teachers[tid].get("short",tid) for tid in teach_ids if tid in teachers)
        room_name    = ", ".join(classrooms[rid].get("name",rid) for rid in room_ids if rid in classrooms)
        info = {
            "day": DAY_NAMES[day_idx], "day_idx": day_idx,
            "period": int(period), "time_start": slot[0], "time_end": slot[1],
            "subject": subj.get("name",""), "subject_short": subj.get("short",""),
            "teacher": teacher_name, "room": room_name,
            "subject_id": lesson.get("subjectid",""),
            "teacher_id": teach_ids[0] if teach_ids else "",
            "classroom_id": room_ids[0] if room_ids else "",
        }
        for cid in class_ids:
            schedule.setdefault(cid,[]).append(info)
    for cid in schedule:
        schedule[cid].sort(key=lambda x:(x["day_idx"],x["period"]))
    return {"classes":classes,"subjects":subjects,
            "teachers":teachers,"classrooms":classrooms,"schedule":schedule}

async def scrape() -> dict:
    captured = {}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page    = await browser.new_page()
        async def on_response(r):
            if "regularttGetData" in r.url:
                try:
                    data = await r.json()
                    if not data.get("reload"):
                        captured["raw"] = data.get("r") or data
                        print("[OK] Data captured!")
                except: pass
        page.on("response", on_response)
        print("[BROWSER] Loading TTPU timetable page...")
        await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        await browser.close()
    if not captured.get("raw"):
        print("[ERROR] No data received"); return {}
    print("[PARSE] Parsing data...")
    return parse_all(captured["raw"])

def init_timetable_db():
    os.makedirs(os.path.dirname(TIMETABLE_DB) or ".", exist_ok=True)
    conn = sqlite3.connect(TIMETABLE_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS groups    (id TEXT PRIMARY KEY, name TEXT, short TEXT, color TEXT);
        CREATE TABLE IF NOT EXISTS subjects  (id TEXT PRIMARY KEY, name TEXT, short TEXT, color TEXT);
        CREATE TABLE IF NOT EXISTS teachers  (id TEXT PRIMARY KEY, name TEXT, short TEXT, color TEXT);
        CREATE TABLE IF NOT EXISTS classrooms(id TEXT PRIMARY KEY, name TEXT, short TEXT);
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id TEXT, subject_id TEXT, teacher_id TEXT, classroom_id TEXT,
            subject_name TEXT, subject_short TEXT, teacher_name TEXT, room_name TEXT,
            day TEXT, day_idx INTEGER, period INTEGER, time_start TEXT, time_end TEXT
        );
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE INDEX IF NOT EXISTS idx_group ON lessons(group_id);
        CREATE INDEX IF NOT EXISTS idx_day   ON lessons(day_idx, period);
    """)
    conn.commit()
    return conn

def save_to_db(conn, data: dict):
    c = conn.cursor()
    c.executescript("DELETE FROM lessons; DELETE FROM groups; DELETE FROM subjects; DELETE FROM teachers; DELETE FROM classrooms;")
    for r in data["classes"].values():
        c.execute("INSERT OR REPLACE INTO groups VALUES (?,?,?,?)",
                  (r["id"],r.get("name",""),r.get("short",""),r.get("color","")))
    for r in data["subjects"].values():
        c.execute("INSERT OR REPLACE INTO subjects VALUES (?,?,?,?)",
                  (r["id"],r.get("name",""),r.get("short",""),r.get("color","")))
    for r in data["teachers"].values():
        c.execute("INSERT OR REPLACE INTO teachers VALUES (?,?,?,?)",
                  (r["id"],r.get("name",""),r.get("short",""),r.get("color","")))
    for r in data["classrooms"].values():
        c.execute("INSERT OR REPLACE INTO classrooms VALUES (?,?,?)",
                  (r["id"],r.get("name",""),r.get("short","")))
    for group_id, lessons in data["schedule"].items():
        for l in lessons:
            c.execute("""INSERT INTO lessons
                (group_id,subject_id,teacher_id,classroom_id,
                 subject_name,subject_short,teacher_name,room_name,
                 day,day_idx,period,time_start,time_end)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (group_id,l["subject_id"],l["teacher_id"],l["classroom_id"],
                 l["subject"],l["subject_short"],l["teacher"],l["room"],
                 l["day"],l["day_idx"],l["period"],l["time_start"],l["time_end"]))
    c.execute("INSERT OR REPLACE INTO meta VALUES ('updated_at',?)",
              (datetime.now().isoformat(),))
    conn.commit()

async def main():
    print("="*50)
    print("  TTPU Timetable Scraper")
    print(f"  DB: {TIMETABLE_DB}")
    print("="*50+"\n")
    data = await scrape()
    if not data: return
    print(f"\n  Groups:    {len(data['classes'])}")
    print(f"  Subjects:  {len(data['subjects'])}")
    total = sum(len(v) for v in data["schedule"].values())
    print(f"  Lessons:   {total}")
    print(f"\n[DB] Saving to {TIMETABLE_DB}...")
    conn = init_timetable_db()
    save_to_db(conn, data)
    g = conn.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
    l = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
    print(f"\n  Done! Groups: {g} | Lessons: {l}")
    print(f"  Run: python app.py\n")

if __name__ == "__main__":
    asyncio.run(main())