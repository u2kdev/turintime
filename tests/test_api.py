"""Быстрая проверка HTTP-API (без запуска сервера)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from turin.api import create_app  # noqa: E402

app = create_app(with_bot=False)

with TestClient(app) as client:
    for path in ["/api/health", "/api/meta", "/api/weeks"]:
        response = client.get(path)
        print(f"\n{path} -> {response.status_code}")
        print(response.text[:400])

    directory = client.get("/api/directory").json()
    print("\nсправочник:", {key: len(value) for key, value in directory.items() if isinstance(value, list)})

    group = next(item for item in directory["classes"] if item["name"] == "FYL1-26")
    schedule = client.get(f"/api/schedule/class/{group['id']}").json()
    print("\nрасписание:", schedule["entity"]["name"], "| неделя:", schedule["week"]["title"])
    for day in schedule["days"]:
        print("  ", day["ru"], day["date"], "->", day["count"], "пар",
              [lesson["short"] for lesson in day["lessons"]])

    print("\nnow:", client.get(f"/api/now/class/{group['id']}").json())
    print("\nsearch 'IT1':", [item["name"] for item in client.get("/api/search?q=IT1").json()])

    teacher = directory["teachers"][0]
    t_schedule = client.get(f"/api/schedule/teacher/{teacher['id']}").json()
    print("\nпреподаватель:", teacher["name"], "->", sum(d["count"] for d in t_schedule["days"]), "пар")

    room = next(item for item in directory["classrooms"] if item["name"] == "C405")
    r_schedule = client.get(f"/api/schedule/room/{room['id']}").json()
    print("аудитория:", room["name"], "->", sum(d["count"] for d in r_schedule["days"]), "пар")

    offline = client.get(f"/api/offline/class/{group['id']}").json()
    print("\noffline bundle: недель", len(offline["weeks"]),
          "| размер", len(client.get(f"/api/offline/class/{group['id']}").content), "байт")

    missing = client.get("/api/schedule/class/несуществующая")
    print("\n404-тест:", missing.status_code, missing.text[:80])
