"""
TTPU Timetable Scraper — multi-week
Playwright захватывает первую неделю через браузер,
остальные недели тянутся напрямую через API с cookies сессии.
"""
import sys, asyncio, sqlite3, os, json
from datetime import datetime
from playwright.async_api import async_playwright
import httpx

# Windows UTF-8 fix
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

BASE_URL     = "https://ttpu.edupage.org/timetable/"
API_BASE     = "https://ttpu.edupage.org/timetable/server"
TIMETABLE_DB = os.getenv("TIMETABLE_DB", "data/timetable.db")

SLOTS = {
    "1":("09:00","10:20"), "2":("10:30","11:50"), "3":("12:00","13:20"),
    "4":("14:20","15:40"), "5":("15:50","17:10"), "6":("17:20","18:40"),
    "7":("18:50","20:10"), "8":("20:20","21:40"),
}
DAYS_MAP  = {"100000":0,"010000":1,"001000":2,"000100":3,"000010":4,"000001":5}
DAY_NAMES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
API_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": BASE_URL,
    "Origin": "https://ttpu.edupage.org",
}

# ── PARSER ────────────────────────────────────────────────────────────────
def parse_raw(raw: dict) -> dict:
    """Parse a regularttGetData response into structured data."""
    tables     = {t["id"]: t for t in raw.get("dbiAccessorRes", {}).get("tables", [])}
    def rows(tid): return tables.get(tid, {}).get("data_rows", [])

    subjects   = {r["id"]: r for r in rows("subjects")}
    teachers   = {r["id"]: r for r in rows("teachers")}
    classrooms = {r["id"]: r for r in rows("classrooms")}
    classes    = {r["id"]: r for r in rows("classes")}
    lessons    = {r["id"]: r for r in rows("lessons")}
    schedule   = {}

    for card in rows("cards"):
        days_str  = card.get("days", "")
        period    = str(card.get("period", ""))
        room_ids  = card.get("classroomids", [])
        lesson_id = card.get("lessonid", "")
        if not days_str or not period or not lesson_id:
            continue
        lesson = lessons.get(lesson_id)
        if not lesson:
            continue
        day_idx = DAYS_MAP.get(days_str)
        if day_idx is None:
            continue
        slot      = SLOTS.get(period, ("", ""))
        subj      = subjects.get(lesson.get("subjectid", ""), {})
        teach_ids = lesson.get("teacherids", [])
        class_ids = lesson.get("classids", [])
        teacher_name = ", ".join(
            teachers[tid].get("short", tid) for tid in teach_ids if tid in teachers
        )
        room_name = ", ".join(
            classrooms[rid].get("name", rid) for rid in room_ids if rid in classrooms
        )
        info = {
            "day": DAY_NAMES[day_idx], "day_idx": day_idx,
            "period": int(period), "time_start": slot[0], "time_end": slot[1],
            "subject": subj.get("name", ""), "subject_short": subj.get("short", ""),
            "teacher": teacher_name, "room": room_name,
            "subject_id":   lesson.get("subjectid", ""),
            "teacher_id":   teach_ids[0] if teach_ids else "",
            "classroom_id": room_ids[0]  if room_ids  else "",
        }
        for cid in class_ids:
            schedule.setdefault(cid, []).append(info)

    for cid in schedule:
        schedule[cid].sort(key=lambda x: (x["day_idx"], x["period"]))

    return {
        "classes": classes, "subjects": subjects,
        "teachers": teachers, "classrooms": classrooms,
        "schedule": schedule,
    }

# ── DIRECT API HELPERS ────────────────────────────────────────────────────
async def api_post(endpoint: str, args: list, cookies: dict) -> dict:
    payload = {"__args": json.dumps(args), "__gsh": "00000000"}
    async with httpx.AsyncClient(cookies=cookies, timeout=30, headers=API_HEADERS) as client:
        r = await client.post(f"{API_BASE}/{endpoint}", data=payload)
        r.raise_for_status()
        return r.json()

async def fetch_weeks(cookies: dict) -> tuple[list, str]:
    """
    Returns (weeks_list, default_tt_num).
    weeks_list = [{tt_num, week_text, datefrom, is_default}, ...]
    """
    data = await api_post("ttviewer.js?__func=getTTViewerData", [None, 2025], cookies)
    r = data.get("r", {})
    timetables  = r.get("regular", {}).get("timetables", [])
    default_num = r.get("regular", {}).get("default_num", "")
    weeks = []
    for t in timetables:
        if t.get("hidden"):
            continue
        weeks.append({
            "tt_num":    t["tt_num"],
            "week_text": t.get("text", ""),
            "datefrom":  t.get("datefrom", ""),
            "is_default": 1 if t["tt_num"] == default_num else 0,
        })
    return weeks, default_num

async def fetch_week_data(tt_num: str, cookies: dict) -> dict | None:
    """Fetch regularttGetData for a specific tt_num."""
    try:
        data = await api_post(
            "regulartt.js?__func=regularttGetData", [None, tt_num], cookies
        )
        raw = data.get("r") or data
        if not raw or raw.get("reload"):
            return None
        return raw
    except Exception as e:
        print(f"  [warn] tt_num={tt_num}: {e}")
        return None

# ── MAIN SCRAPER ──────────────────────────────────────────────────────────
async def scrape() -> dict | None:
    """
    Returns {
        "weeks":   [{tt_num, week_text, datefrom, is_default}, ...],
        "data":    {tt_num: parsed_data, ...}
    }
    or None on fatal error.
    """
    captured_raw = None
    cookies      = {}

    # Step 1 — Open browser, capture first regularttGetData + session cookies
    print("[1/3] Opening browser...")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page    = await browser.new_page()

        async def on_response(resp):
            nonlocal captured_raw
            if "regularttGetData" in resp.url and captured_raw is None:
                try:
                    d = await resp.json()
                    if not d.get("reload"):
                        captured_raw = d.get("r") or d
                        print("      Browser captured default week data!")
                except Exception:
                    pass

        page.on("response", on_response)
        await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)

        raw_cookies = await page.context.cookies()
        cookies = {c["name"]: c["value"] for c in raw_cookies}
        print(f"      Session cookies: {len(cookies)} entries")
        await browser.close()

    if not captured_raw:
        print("[ERROR] Browser did not capture any schedule data.")
        print("        Check network connectivity to ttpu.edupage.org")
        return None

    # Step 2 — Get list of available weeks
    print("[2/3] Fetching weeks list...")
    try:
        weeks, default_num = await fetch_weeks(cookies)
        print(f"      Found {len(weeks)} week(s)")
        for w in weeks:
            mark = " (default)" if w["is_default"] else ""
            print(f"      - {w['week_text']}{mark}")
    except Exception as e:
        print(f"      [warn] Could not fetch weeks list: {e}")
        print("      Saving single captured week as fallback")
        weeks      = [{"tt_num":"default","week_text":"Current","datefrom":"","is_default":1}]
        default_num = "default"

    # Step 3 — Parse default week from browser capture, fetch others via API
    print("[3/3] Fetching remaining weeks...")
    default_week = next((w for w in weeks if w["is_default"]), weeks[0] if weeks else None)
    if not default_week:
        default_week = {"tt_num": "default", "week_text": "Current", "datefrom": "", "is_default": 1}

    all_data = {default_week["tt_num"]: parse_raw(captured_raw)}
    g_count  = len(all_data[default_week["tt_num"]]["classes"])
    print(f"      {default_week['week_text']}: {g_count} groups (from browser)")

    for w in weeks:
        if w["tt_num"] == default_week["tt_num"]:
            continue
        raw = await fetch_week_data(w["tt_num"], cookies)
        if raw:
            all_data[w["tt_num"]] = parse_raw(raw)
            gc = len(all_data[w["tt_num"]]["classes"])
            print(f"      {w['week_text']}: {gc} groups")
        else:
            print(f"      {w['week_text']}: skipped (no data)")

    return {"weeks": weeks, "data": all_data}

# ── DATABASE ──────────────────────────────────────────────────────────────
def init_db():
    os.makedirs(os.path.dirname(TIMETABLE_DB) or ".", exist_ok=True)
    conn = sqlite3.connect(TIMETABLE_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS groups    (id TEXT PRIMARY KEY, name TEXT, short TEXT, color TEXT);
        CREATE TABLE IF NOT EXISTS subjects  (id TEXT PRIMARY KEY, name TEXT, short TEXT, color TEXT);
        CREATE TABLE IF NOT EXISTS teachers  (id TEXT PRIMARY KEY, name TEXT, short TEXT, color TEXT);
        CREATE TABLE IF NOT EXISTS classrooms(id TEXT PRIMARY KEY, name TEXT, short TEXT);
        CREATE TABLE IF NOT EXISTS weeks (
            tt_num     TEXT PRIMARY KEY,
            week_text  TEXT,
            datefrom   TEXT,
            is_default INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS lessons (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            tt_num       TEXT    DEFAULT '',
            group_id     TEXT, subject_id TEXT, teacher_id TEXT, classroom_id TEXT,
            subject_name TEXT, subject_short TEXT, teacher_name TEXT, room_name TEXT,
            day TEXT, day_idx INTEGER, period INTEGER, time_start TEXT, time_end TEXT
        );
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE INDEX IF NOT EXISTS idx_group ON lessons(group_id);
        CREATE INDEX IF NOT EXISTS idx_week  ON lessons(tt_num);
        CREATE INDEX IF NOT EXISTS idx_day   ON lessons(day_idx, period);
    """)
    # Migration for old DBs without tt_num column
    try:
        conn.execute("ALTER TABLE lessons ADD COLUMN tt_num TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    conn.commit()
    return conn

def save_to_db(conn, result: dict) -> int:
    weeks    = result["weeks"]
    all_data = result["data"]
    c = conn.cursor()

    # Clear everything and rebuild
    c.executescript("""
        DELETE FROM lessons; DELETE FROM groups; DELETE FROM subjects;
        DELETE FROM teachers; DELETE FROM classrooms; DELETE FROM weeks;
    """)

    # Reference tables from first parsed week
    first = next(iter(all_data.values()), {})
    for r in first.get("classes",    {}).values():
        c.execute("INSERT OR REPLACE INTO groups     VALUES (?,?,?,?)",
                  (r["id"], r.get("name",""), r.get("short",""), r.get("color","")))
    for r in first.get("subjects",   {}).values():
        c.execute("INSERT OR REPLACE INTO subjects   VALUES (?,?,?,?)",
                  (r["id"], r.get("name",""), r.get("short",""), r.get("color","")))
    for r in first.get("teachers",   {}).values():
        c.execute("INSERT OR REPLACE INTO teachers   VALUES (?,?,?,?)",
                  (r["id"], r.get("name",""), r.get("short",""), r.get("color","")))
    for r in first.get("classrooms", {}).values():
        c.execute("INSERT OR REPLACE INTO classrooms VALUES (?,?,?)",
                  (r["id"], r.get("name",""), r.get("short","")))

    # Weeks
    for w in weeks:
        c.execute("INSERT OR REPLACE INTO weeks VALUES (?,?,?,?)",
                  (w["tt_num"], w["week_text"], w["datefrom"], w["is_default"]))

    # Lessons per week
    total = 0
    for tt_num, data in all_data.items():
        for group_id, lesson_list in data.get("schedule", {}).items():
            for l in lesson_list:
                c.execute("""
                    INSERT INTO lessons
                        (tt_num, group_id, subject_id, teacher_id, classroom_id,
                         subject_name, subject_short, teacher_name, room_name,
                         day, day_idx, period, time_start, time_end)
                    VALUES (?,?,?,?,?, ?,?,?,?, ?,?,?,?,?)
                """, (
                    tt_num, group_id, l["subject_id"], l["teacher_id"], l["classroom_id"],
                    l["subject"], l["subject_short"], l["teacher"], l["room"],
                    l["day"], l["day_idx"], l["period"], l["time_start"], l["time_end"],
                ))
                total += 1

    c.execute("INSERT OR REPLACE INTO meta VALUES ('updated_at', ?)",
              (datetime.now().isoformat(),))
    conn.commit()
    return total

# ── ENTRY POINT ───────────────────────────────────────────────────────────
async def main():
    print("=" * 50)
    print("  TTPU Timetable Scraper (multi-week)")
    print(f"  DB: {TIMETABLE_DB}")
    print("=" * 50 + "\n")

    result = await scrape()
    if not result:
        sys.exit(1)

    weeks    = result["weeks"]
    all_data = result["data"]

    total_lessons = sum(
        len(v) for d in all_data.values() for v in d.get("schedule", {}).values()
    )
    print(f"\nResults:")
    print(f"  Weeks with data : {len(all_data)}")
    print(f"  Groups          : {len(next(iter(all_data.values()))['classes'])}")
    print(f"  Total lessons   : {total_lessons}")

    print(f"\nSaving to {TIMETABLE_DB}...")
    conn  = init_db()
    total = save_to_db(conn, result)

    g  = conn.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
    wc = conn.execute("SELECT COUNT(*) FROM weeks").fetchone()[0]
    l  = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
    print(f"  Done! Groups: {g} | Weeks: {wc} | Lessons: {l}")
    print(f"\nStart server: python app.py\n")

if __name__ == "__main__":
    asyncio.run(main())