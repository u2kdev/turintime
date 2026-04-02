# Официальный образ Playwright с Python — Chromium уже внутри
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Копируем зависимости и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем браузер Chromium для Python-библиотеки playwright
RUN playwright install chromium

# Создаём папку для баз данных
RUN mkdir -p /app/data

# Копируем весь проект
COPY . .

# Открываем порт
EXPOSE 8000

# Запускаем приложение
CMD ["python", "app.py"]
