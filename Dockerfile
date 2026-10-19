# ── Образ приложения TTPU Timetable ────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Сначала зависимости — слой кэшируется, пока не менялся requirements.txt
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY turin ./turin
COPY web ./web

# Каталог для SQLite (расписание + пользователи бота). Монтируется томом.
RUN mkdir -p /app/data
VOLUME ["/app/data"]

ENV HOST=0.0.0.0 \
    PORT=8000 \
    DATA_DIR=/app/data \
    TIMETABLE_DB=/app/data/timetable.db \
    USERS_DB=/app/data/users.db

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

CMD ["python", "main.py"]
