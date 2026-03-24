"""
TTPU Timetable Bot — aiogram 3.7+
"""
import sqlite3, asyncio, os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage

DB_PATH   = "data/timetable.db"
DAY_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
DAY_RU    = {
    "Monday":"Понедельник","Tuesday":"Вторник","Wednesday":"Среда",
    "Thursday":"Четверг","Friday":"Пятница","Saturday":"Суббота",
}

# ── TG USER PERSISTENCE ───────────────────────────────────────────────────
def save_tg_user(user_id: int, username: str, first_name: str, last_name: str,
                 group_id: str = "", group_name: str = ""):
    now  = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    exists = conn.execute("SELECT user_id FROM tg_users WHERE user_id=?", (user_id,)).fetchone()
    if exists:
        conn.execute("""UPDATE tg_users SET username=?,first_name=?,last_name=?,last_seen=?
                        WHERE user_id=?""", (username, first_name, last_name, now, user_id))
    else:
        conn.execute("""INSERT INTO tg_users
                        (user_id,username,first_name,last_name,group_id,group_name,created_at,last_seen)
                        VALUES (?,?,?,?,?,?,?,?)""",
                     (user_id, username, first_name, last_name, group_id, group_name, now, now))
    conn.commit(); conn.close()

def update_tg_group(user_id: int, group_id: str, group_name: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE tg_users SET group_id=?,group_name=?,last_seen=? WHERE user_id=?",
                 (group_id, group_name, datetime.now().isoformat(), user_id))
    conn.commit(); conn.close()

def load_tg_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM tg_users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(r) if r else None

# ── DB ────────────────────────────────────────────────────────────────────
def all_groups():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row
    rows = c.execute("SELECT id,name FROM groups ORDER BY name").fetchall()
    c.close(); return [dict(r) for r in rows]

def group_schedule(gid):
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row
    rows = c.execute("""
        SELECT day, period, time_start, time_end,
               subject_name, subject_short, teacher_name, room_name
        FROM lessons WHERE group_id=? ORDER BY day_idx, period
    """, (gid,)).fetchall()
    c.close()
    s = {}
    for r in rows: s.setdefault(r["day"], []).append(dict(r))
    return s

def db_meta():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row
    g = c.execute("SELECT COUNT(*) as n FROM groups").fetchone()["n"]
    u = c.execute("SELECT value FROM meta WHERE key='updated_at'").fetchone()
    c.close(); return g, (u["value"][:10] if u else "—")

def today_en():
    return DAY_ORDER[min(datetime.now().weekday(), 5)]

def current_period():
    t = datetime.now().hour * 60 + datetime.now().minute
    for s, e, n in [(540,620,1),(630,710,2),(720,800,3),(860,940,4),
                    (950,1030,5),(1040,1120,6),(1130,1210,7),(1220,1300,8)]:
        if s <= t <= e: return n
    return 0

# ── KEYBOARDS ─────────────────────────────────────────────────────────────
def kb_groups(groups, page=0):
    PER = 20
    chunk = groups[page*PER:(page+1)*PER]
    total = (len(groups)+PER-1)//PER
    rows = []
    for i in range(0, len(chunk), 2):
        pair = chunk[i:i+2]
        rows.append([InlineKeyboardButton(text=g["name"], callback_data=f"grp:{g['id']}") for g in pair])
    if total > 1:
        nav = []
        if page > 0: nav.append(InlineKeyboardButton(text="◀️", callback_data=f"page:{page-1}"))
        nav.append(InlineKeyboardButton(text=f"{page+1}/{total}", callback_data="noop"))
        if page < total-1: nav.append(InlineKeyboardButton(text="▶️", callback_data=f"page:{page+1}"))
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_home(gid):
    today = today_en()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Сегодня", callback_data=f"day:{gid}:{today}"),
         InlineKeyboardButton(text="📋 Все дни", callback_data=f"days:{gid}")],
        [InlineKeyboardButton(text="🔄 Сменить группу", callback_data="choose_group")],
    ])

def kb_days(gid, schedule):
    today = today_en()
    rows, row = [], []
    for day in DAY_ORDER:
        cnt = len(schedule.get(day, []))
        lbl = ("• " if day==today else "") + DAY_RU[day] + (" •" if day==today else "")
        lbl += f" ({cnt})" if cnt else " —"
        row.append(InlineKeyboardButton(text=lbl, callback_data=f"day:{gid}:{day}"))
        if len(row)==2: rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"home:{gid}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_day(gid, day):
    idx  = DAY_ORDER.index(day)
    prev = DAY_ORDER[idx-1] if idx>0 else None
    nxt  = DAY_ORDER[idx+1] if idx<5 else None
    nav  = []
    if prev: nav.append(InlineKeyboardButton(text=f"◀️ {DAY_RU[prev][:2]}", callback_data=f"day:{gid}:{prev}"))
    nav.append(InlineKeyboardButton(text="📋 Дни", callback_data=f"days:{gid}"))
    if nxt:  nav.append(InlineKeyboardButton(text=f"{DAY_RU[nxt][:2]} ▶️", callback_data=f"day:{gid}:{nxt}"))
    return InlineKeyboardMarkup(inline_keyboard=[
        nav,
        [InlineKeyboardButton(text="🏠 Главная", callback_data=f"home:{gid}")],
    ])

# ── FORMATTER ─────────────────────────────────────────────────────────────
def fmt_day(gname, day, lessons):
    now  = current_period() if day == today_en() else 0
    text = f"📅 <b>{gname}</b> · <b>{DAY_RU[day]}</b>\n\n"
    if not lessons:
        return text + "<i>Пар нет</i>"
    parts = []
    for l in lessons:
        p     = l["period"]
        time  = f"{l['time_start']}–{l['time_end']}"
        subj  = l["subject_name"] or l["subject_short"] or "—"
        mark  = "▶️" if p==now else f"<b>{p}.</b>"
        line  = f"{mark} <b>{subj}</b>  <code>{time}</code>"
        if l["subject_short"] and l["subject_short"] != subj:
            line += f"\n    <i>{l['subject_short']}</i>"
        if l["room_name"]:    line += f"\n    🚪 {l['room_name']}"
        if l["teacher_name"]: line += f"\n    👤 {l['teacher_name']}"
        parts.append(line)
    return text + "\n\n".join(parts)

# ── GLOBALS ───────────────────────────────────────────────────────────────
_groups_cache = []
_user_page    = {}

def get_groups():
    global _groups_cache
    if not _groups_cache: _groups_cache = all_groups()
    return _groups_cache

def find_group(gid): return next((g for g in get_groups() if g["id"]==gid), None)

# ── DISPATCHER ────────────────────────────────────────────────────────────
def build_dp():
    dp = Dispatcher(storage=MemoryStorage())

    async def show_groups(target, uid, page=0, edit=False):
        groups = get_groups()
        total, upd = db_meta()
        text = (f"🏫 <b>TTPU Расписание</b>\n"
                f"Групп: <b>{total}</b>  ·  обновлено {upd}\n\n"
                f"👇 Выбери свою группу:")
        _user_page[uid] = page
        kb = kb_groups(groups, page)
        if edit: await target.edit_text(text, reply_markup=kb)
        else:    await target.answer(text, reply_markup=kb)

    async def show_home(target, uid, gid, gname, tg_user=None, edit=False):
        update_tg_group(uid, gid, gname)
        schedule = group_schedule(gid)
        today_n  = len(schedule.get(today_en(), []))
        total_n  = sum(len(v) for v in schedule.values())
        text = (f"✅ <b>{gname}</b>\n"
                f"Пар всего: <b>{total_n}</b>  ·  Сегодня: <b>{today_n}</b>\n\n"
                f"Выбери действие:")
        if edit: await target.edit_text(text, reply_markup=kb_home(gid))
        else:    await target.answer(text, reply_markup=kb_home(gid))

    @dp.message(CommandStart())
    async def cmd_start(msg: Message):
        u = msg.from_user
        save_tg_user(u.id, u.username or "", u.first_name or "", u.last_name or "")
        if not os.path.exists(DB_PATH):
            await msg.answer("⚠️ База не найдена.\n<code>python debug.py</code>"); return
        saved = load_tg_user(u.id)
        if saved and saved.get("group_id"):
            await msg.answer(f"👋 Привет, <b>{u.first_name}</b>!\nГруппа: <b>{saved['group_name']}</b>")
            await show_home(msg, u.id, saved["group_id"], saved["group_name"])
        else:
            await msg.answer(f"👋 Привет, <b>{u.first_name}</b>! Выбери группу:")
            await show_groups(msg, u.id)

    @dp.callback_query(F.data.startswith("page:"))
    async def cb_page(call: CallbackQuery):
        page = int(call.data.split(":")[1])
        await show_groups(call.message, call.from_user.id, page=page, edit=True)
        await call.answer()

    @dp.callback_query(F.data.startswith("grp:"))
    async def cb_grp(call: CallbackQuery):
        gid = call.data.split(":",1)[1]
        g   = find_group(gid)
        if not g: await call.answer("Группа не найдена", show_alert=True); return
        await show_home(call.message, call.from_user.id, g["id"], g["name"], edit=True)
        await call.answer()

    @dp.callback_query(F.data.startswith("home:"))
    async def cb_home(call: CallbackQuery):
        gid = call.data.split(":",1)[1]
        g   = find_group(gid)
        gname = g["name"] if g else gid
        await show_home(call.message, call.from_user.id, gid, gname, edit=True)
        await call.answer()

    @dp.callback_query(F.data.startswith("days:"))
    async def cb_days(call: CallbackQuery):
        gid = call.data.split(":",1)[1]
        g   = find_group(gid)
        gname = g["name"] if g else gid
        await call.message.edit_text(f"📚 <b>{gname}</b> — выбери день:",
                                     reply_markup=kb_days(gid, group_schedule(gid)))
        await call.answer()

    @dp.callback_query(F.data.startswith("day:"))
    async def cb_day(call: CallbackQuery):
        _, gid, day = call.data.split(":",2)
        g     = find_group(gid)
        gname = g["name"] if g else gid
        lessons = group_schedule(gid).get(day, [])
        await call.message.edit_text(fmt_day(gname, day, lessons), reply_markup=kb_day(gid, day))
        await call.answer()

    @dp.callback_query(F.data == "choose_group")
    async def cb_choose(call: CallbackQuery):
        page = _user_page.get(call.from_user.id, 0)
        await show_groups(call.message, call.from_user.id, page=page, edit=True)
        await call.answer()

    @dp.callback_query(F.data == "noop")
    async def cb_noop(call: CallbackQuery): await call.answer()

    @dp.message()
    async def fallback(msg: Message): await msg.answer("Нажми /start 📅")

    return dp

# ── TOKEN ─────────────────────────────────────────────────────────────────
def load_token():
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token and os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            if line.startswith("BOT_TOKEN="):
                token = line.split("=",1)[1].strip(); break
    return token

async def run_bot():
    token = load_token()
    if not token:
        print("❌ BOT_TOKEN не найден"); return

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    dp  = build_dp()
    g, upd = db_meta()
    print(f"✓ Бот запущен · {g} групп · обновлено {upd}")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(run_bot())