"""
TTPU Timetable Web App
pip install fastapi uvicorn authlib httpx itsdangerous python-multipart starlette aiogram
"""
import sqlite3, os, asyncio
from datetime import datetime, date, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth

# ── ДВЕ БАЗЫ ДАННЫХ ──────────────────────────────────────────────────────
USERS_DB     = os.getenv("USERS_DB",     "data/users.db")      # пользователи
TIMETABLE_DB = os.getenv("TIMETABLE_DB", "data/timetable.db")  # расписание

# ── ENV ───────────────────────────────────────────────────────────────────
def load_env():
    cfg = {}
    if os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    cfg.update({k: v for k, v in os.environ.items() if k not in cfg})
    return cfg

ENV           = load_env()
SECRET_KEY    = ENV.get("SECRET_KEY",          "ttpu-secret-change-me")
GOOGLE_ID     = ENV.get("GOOGLE_CLIENT_ID",    "")
GOOGLE_SECRET = ENV.get("GOOGLE_CLIENT_SECRET","")
ADMIN_USER    = ENV.get("ADMIN_USERNAME",      "admin")
ADMIN_PASS    = ENV.get("ADMIN_PASSWORD",      "admin123")
BASE_URL      = ENV.get("BASE_URL",            "http://localhost:8000")
AUTHOR_NAME   = ENV.get("AUTHOR_NAME",         "")
AUTHOR_SUR    = ENV.get("AUTHOR_SURNAME",      "")
AUTHOR_TG     = ENV.get("AUTHOR_TG",           "")
AUTHOR_LABEL  = ENV.get("AUTHOR_TG_LABEL",     "")
ORG_NAME      = ENV.get("ORG_NAME",            "")
ORG_DESC      = ENV.get("ORG_DESC",            "")

# ── DB CONNECTIONS ────────────────────────────────────────────────────────
def users_db():
    c = sqlite3.connect(USERS_DB)
    c.row_factory = sqlite3.Row
    return c

def tt_db():
    c = sqlite3.connect(TIMETABLE_DB)
    c.row_factory = sqlite3.Row
    return c

# ── INIT USERS.DB ─────────────────────────────────────────────────────────
def init_users_db():
    os.makedirs(os.path.dirname(USERS_DB) or ".", exist_ok=True)
    c = sqlite3.connect(USERS_DB)
    c.executescript("""
        CREATE TABLE IF NOT EXISTS web_users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            google_id  TEXT UNIQUE,
            email      TEXT,
            name       TEXT,
            picture    TEXT,
            group_id   TEXT DEFAULT '',
            group_name TEXT DEFAULT '',
            is_guest   INTEGER DEFAULT 0,
            created_at TEXT,
            last_seen  TEXT
        );
        CREATE TABLE IF NOT EXISTS web_visits (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date    TEXT
        );
        CREATE TABLE IF NOT EXISTS page_views (
            date  TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tg_users (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            last_name  TEXT DEFAULT '',
            group_id   TEXT DEFAULT '',
            group_name TEXT DEFAULT '',
            created_at TEXT,
            last_seen  TEXT
        );
    """)
    c.commit(); c.close()

# ── USER HELPERS (users.db) ───────────────────────────────────────────────
def upsert_web_user(google_id, email, name, picture) -> dict:
    c   = users_db()
    now = datetime.now().isoformat()
    today = date.today().isoformat()
    row = c.execute("SELECT * FROM web_users WHERE google_id=?", (google_id,)).fetchone()
    if row:
        c.execute("UPDATE web_users SET name=?,picture=?,last_seen=?,is_guest=0 WHERE google_id=?",
                  (name, picture, now, google_id))
        c.commit()
        user = dict(c.execute("SELECT * FROM web_users WHERE google_id=?", (google_id,)).fetchone())
    else:
        c.execute("""INSERT INTO web_users
                     (google_id,email,name,picture,is_guest,created_at,last_seen)
                     VALUES (?,?,?,?,0,?,?)""",
                  (google_id, email, name, picture, now, now))
        c.commit()
        user = dict(c.execute("SELECT * FROM web_users WHERE google_id=?", (google_id,)).fetchone())
    if not c.execute("SELECT id FROM web_visits WHERE user_id=? AND date=?",
                     (user["id"], today)).fetchone():
        c.execute("INSERT INTO web_visits (user_id,date) VALUES (?,?)", (user["id"], today))
    c.execute("INSERT OR IGNORE INTO page_views (date,count) VALUES (?,0)", (today,))
    c.execute("UPDATE page_views SET count=count+1 WHERE date=?", (today,))
    c.commit(); c.close()
    return user

def get_web_user(uid):
    r = users_db().execute("SELECT * FROM web_users WHERE id=?", (uid,)).fetchone()
    return dict(r) if r else None

def track_view():
    today = date.today().isoformat()
    c = users_db()
    c.execute("INSERT OR IGNORE INTO page_views (date,count) VALUES (?,0)", (today,))
    c.execute("UPDATE page_views SET count=count+1 WHERE date=?", (today,))
    c.commit(); c.close()

# ── SCHEDULE HELPERS (timetable.db) ───────────────────────────────────────
def all_groups():
    if not os.path.exists(TIMETABLE_DB):
        return []
    return [dict(r) for r in
            tt_db().execute("SELECT id,name FROM groups ORDER BY name").fetchall()]

def group_schedule(gid):
    rows = tt_db().execute("""
        SELECT day, day_idx, period, time_start, time_end,
               subject_name, subject_short, teacher_name, room_name
        FROM lessons WHERE group_id=? ORDER BY day_idx, period
    """, (gid,)).fetchall()
    s = {}
    for r in rows: s.setdefault(r["day"], []).append(dict(r))
    return s

def tt_meta():
    if not os.path.exists(TIMETABLE_DB):
        return 0, "—"
    c = tt_db()
    g = c.execute("SELECT COUNT(*) as n FROM groups").fetchone()["n"]
    u = c.execute("SELECT value FROM meta WHERE key='updated_at'").fetchone()
    return g, (u["value"][:10] if u else "—")

# ── ADMIN STATS ────────────────────────────────────────────────────────────
def admin_stats():
    c = users_db(); today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    tv = c.execute("SELECT count FROM page_views WHERE date=?", (today,)).fetchone()
    g, upd = tt_meta()
    result = {
        "total_web":      c.execute("SELECT COUNT(*) as n FROM web_users WHERE is_guest=0").fetchone()["n"],
        "total_tg":       c.execute("SELECT COUNT(*) as n FROM tg_users").fetchone()["n"],
        "today_visits":   c.execute("SELECT COUNT(DISTINCT user_id) as n FROM web_visits WHERE date=?", (today,)).fetchone()["n"],
        "week_visits":    c.execute("SELECT COUNT(DISTINCT user_id) as n FROM web_visits WHERE date>=?", (week_ago,)).fetchone()["n"],
        "today_views":    tv["count"] if tv else 0,
        "visits_chart":   [dict(r) for r in c.execute("SELECT date, COUNT(DISTINCT user_id) as n FROM web_visits WHERE date >= date('now','-14 days') GROUP BY date ORDER BY date").fetchall()],
        "views_chart":    [dict(r) for r in c.execute("SELECT date, count FROM page_views WHERE date >= date('now','-14 days') ORDER BY date").fetchall()],
        "recent_web":     [dict(r) for r in c.execute("SELECT name,email,picture,group_name,created_at,last_seen,is_guest FROM web_users ORDER BY last_seen DESC LIMIT 20").fetchall()],
        "tg_users":       [dict(r) for r in c.execute("SELECT user_id,username,first_name,last_name,group_name,created_at,last_seen FROM tg_users ORDER BY last_seen DESC LIMIT 30").fetchall()],
        "popular_groups": [dict(r) for r in c.execute("SELECT group_name, COUNT(*) as n FROM web_users WHERE group_name!='' GROUP BY group_name ORDER BY n DESC LIMIT 10").fetchall()],
        "timetable_groups": g,
        "timetable_updated": upd,
    }
    c.close(); return result

# ── SCRAPER ────────────────────────────────────────────────────────────────
scraper_status = {"running": False, "last_result": None, "last_run": None}

async def run_scraper_task():
    if scraper_status["running"]:
        return {"ok": False, "error": "Скрапер уже запущен"}
    scraper_status["running"] = True
    scraper_status["last_result"] = None
    try:
        script = "debug.py"
        if not os.path.exists(script):
            scraper_status["last_result"] = "❌ debug.py не найден"
            return {"ok": False, "error": "debug.py не найден"}
        proc = await asyncio.create_subprocess_exec(
            "python", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "TIMETABLE_DB": TIMETABLE_DB},
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode("utf-8", errors="replace")
        if proc.returncode == 0:
            g, upd = tt_meta()
            msg = f"✓ Обновлено: {g} групп · {upd}"
            scraper_status["last_result"] = msg
            scraper_status["last_run"]    = datetime.now().isoformat()
            print(f"[scraper] {msg}")
            return {"ok": True, "message": msg}
        else:
            err = f"❌ Ошибка (код {proc.returncode})"
            scraper_status["last_result"] = err
            print(f"[scraper] {err}\n{output[-300:]}")
            return {"ok": False, "error": err}
    except asyncio.TimeoutError:
        scraper_status["last_result"] = "❌ Таймаут (>120с)"
        return {"ok": False, "error": "Таймаут"}
    except Exception as e:
        scraper_status["last_result"] = f"❌ {e}"
        return {"ok": False, "error": str(e)}
    finally:
        scraper_status["running"] = False

async def auto_update_loop():
    print("[auto-update] Запущено. Обновление каждые 24 часа.")
    while True:
        await asyncio.sleep(24 * 60 * 60)
        print(f"[auto-update] {datetime.now().strftime('%Y-%m-%d %H:%M')} — обновляем расписание...")
        result = await run_scraper_task()
        print(f"[auto-update] {result.get('message') or result.get('error')}")

# ── OAUTH ──────────────────────────────────────────────────────────────────
oauth = OAuth()
if GOOGLE_ID:
    oauth.register(
        name="google", client_id=GOOGLE_ID, client_secret=GOOGLE_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

def current_user(request: Request):
    if request.session.get("is_guest"):
        return {"id": None, "name": "Гость", "email": "", "picture": "",
                "group_id":   request.session.get("guest_group_id",   ""),
                "group_name": request.session.get("guest_group_name", ""),
                "is_guest": True}
    uid = request.session.get("user_id")
    return get_web_user(uid) if uid else None

def is_admin(request: Request):
    return bool(request.session.get("is_admin"))

# ── APP ────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_users_db()
    tasks = []

    # Telegram bot
    try:
        from bot import run_bot, load_token
        if load_token():
            print("✓ Запускаем Telegram бота...")
            tasks.append(asyncio.create_task(run_bot()))
            await asyncio.sleep(0.3)
        else:
            print("⚠️  BOT_TOKEN не задан — бот не запущен")
    except Exception as e:
        print(f"⚠️  Бот: {e}")
        import traceback; traceback.print_exc()

    # Auto-update
    tasks.append(asyncio.create_task(auto_update_loop()))

    yield

    for t in tasks:
        if t and not t.done():
            t.cancel()
            try: await t
            except asyncio.CancelledError: pass

app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=60*60*24*30)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── PAGES ──────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def page_index(request: Request):
    track_view()
    return HTMLResponse(open("index.html", encoding="utf-8").read())

@app.get("/timetable", response_class=HTMLResponse)
async def page_timetable(request: Request):
    if not current_user(request):
        return RedirectResponse("/?auth=1")
    return HTMLResponse(open("timetable.html", encoding="utf-8").read())

@app.get("/admin", response_class=HTMLResponse)
async def page_admin(request: Request):
    if not is_admin(request):
        return RedirectResponse("/?auth=1")
    return HTMLResponse(open("admin.html", encoding="utf-8").read())

@app.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.pop("is_admin", None)
    return RedirectResponse("/")

# ── AUTH ───────────────────────────────────────────────────────────────────
@app.post("/api/login")
async def api_login(request: Request):
    body = await request.json()
    if body.get("username","").strip() == ADMIN_USER and \
       body.get("password","").strip() == ADMIN_PASS:
        request.session["is_admin"] = True
        return JSONResponse({"ok": True, "redirect": "/admin"})
    return JSONResponse({"ok": False, "error": "Неверные данные"}, status_code=401)

@app.post("/api/guest")
async def api_guest(request: Request):
    request.session["is_guest"] = True
    request.session.pop("user_id", None)
    return JSONResponse({"ok": True, "redirect": "/timetable"})

@app.get("/login")
async def login(request: Request):
    if not GOOGLE_ID:
        return JSONResponse({"error": "GOOGLE_CLIENT_ID not configured"}, 400)
    return await oauth.google.authorize_redirect(request, f"{BASE_URL}/auth/callback")

@app.get("/auth/callback")
async def auth_callback(request: Request):
    try:
        token    = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo") or await oauth.google.userinfo(token=token)
        user     = upsert_web_user(userinfo["sub"], userinfo.get("email",""),
                                   userinfo.get("name",""), userinfo.get("picture",""))
        request.session["user_id"] = user["id"]
        request.session.pop("is_guest", None)
        return RedirectResponse("/timetable")
    except Exception as e:
        print(f"OAuth error: {e}")
        return RedirectResponse("/?error=oauth")

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")

# ── API: USER ──────────────────────────────────────────────────────────────
@app.get("/api/me")
async def api_me(request: Request):
    user = current_user(request)
    if not user:
        return JSONResponse({"authenticated": False, "is_admin": is_admin(request)})
    return JSONResponse({
        "authenticated": True,
        "is_admin":   is_admin(request),
        "is_guest":   bool(user.get("is_guest")),
        "name":       user["name"],
        "email":      user.get("email", ""),
        "picture":    user.get("picture", ""),
        "group_id":   user.get("group_id", ""),
        "group_name": user.get("group_name", ""),
    })

@app.post("/api/me/group")
async def api_set_group(request: Request):
    user = current_user(request)
    if not user: raise HTTPException(401)
    body  = await request.json()
    gid   = body.get("group_id",   "")
    gname = body.get("group_name", "")
    if user.get("is_guest"):
        request.session["guest_group_id"]   = gid
        request.session["guest_group_name"] = gname
    else:
        c = users_db()
        c.execute("UPDATE web_users SET group_id=?,group_name=? WHERE id=?",
                  (gid, gname, user["id"]))
        c.commit(); c.close()
    return {"ok": True}

# ── API: SCHEDULE ──────────────────────────────────────────────────────────
@app.get("/api/groups")
async def api_groups(): return all_groups()

@app.get("/api/timetable/{group_id:path}")
async def api_timetable(group_id: str, request: Request):
    if not current_user(request): raise HTTPException(401)
    if not os.path.exists(TIMETABLE_DB): raise HTTPException(503, "Расписание ещё не загружено")
    c = tt_db()
    g = c.execute("SELECT * FROM groups WHERE id=?", (group_id,)).fetchone()
    if not g: raise HTTPException(404)
    meta = c.execute("SELECT value FROM meta WHERE key='updated_at'").fetchone()
    return {"group_id": group_id, "group_name": g["name"],
            "updated_at": meta["value"] if meta else "",
            "schedule": group_schedule(group_id)}

@app.get("/api/meta")
async def api_meta():
    g, upd = tt_meta(); return {"total_groups": g, "updated_at": upd}

@app.get("/api/config")
async def api_config():
    return {
        "google_enabled": bool(GOOGLE_ID),
        "author_name":  f"{AUTHOR_NAME} {AUTHOR_SUR}".strip(),
        "author_tg":    AUTHOR_TG,
        "author_label": AUTHOR_LABEL,
        "org_name":     ORG_NAME,
        "org_desc":     ORG_DESC,
    }

# ── API: ADMIN ─────────────────────────────────────────────────────────────
@app.get("/api/admin/stats")
async def api_admin_stats(request: Request):
    if not is_admin(request): raise HTTPException(403)
    return admin_stats()

@app.post("/api/admin/scrape")
async def api_admin_scrape(request: Request):
    if not is_admin(request): raise HTTPException(403)
    if scraper_status["running"]:
        return JSONResponse({"ok": False, "error": "Скрапер уже запущен"})
    asyncio.create_task(run_scraper_task())
    return JSONResponse({"ok": True, "message": "Обновление запущено..."})

@app.get("/api/admin/scrape/status")
async def api_scrape_status(request: Request):
    if not is_admin(request): raise HTTPException(403)
    return JSONResponse(scraper_status)

# ── MAIN ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    os.makedirs(os.path.dirname(USERS_DB)     or ".", exist_ok=True)
    os.makedirs(os.path.dirname(TIMETABLE_DB) or ".", exist_ok=True)
    if not os.path.exists(TIMETABLE_DB):
        print(f"⚠️  Расписание не найдено ({TIMETABLE_DB})")
        print("   Запусти: python debug.py  — чтобы загрузить расписание")
    g, upd = tt_meta()
    print(f"✓ Расписание: {g} групп · {upd}")
    print(f"✓ Пользователи: {USERS_DB}")
    print(f"✓ Сервер → {BASE_URL}")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)