"""
Генерация иконок PWA (без внешних ассетов).

    python scripts/make_icons.py

Рисует минималистичный знак «расписание»: три строки, третья — акцентом.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "web" / "icons"

INK = (20, 19, 16, 255)
CREAM = (246, 243, 238, 255)
CLAY = (196, 100, 58, 255)
CANVAS = 1024


def mark(size: int, scale: float = 1.0, background: bool = True) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    if background:
        draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.235), fill=INK)

    unit = size * scale
    left = (size - unit) / 2
    top = (size - unit) / 2
    bar_height = unit * 0.115
    radius = bar_height / 2

    rows = [
        (0.10, 0.90, CREAM),
        (0.10, 0.62, CREAM),
        (0.10, 0.38, CLAY),
    ]
    for index, (start, width, color) in enumerate(rows):
        y = top + unit * (0.20 + index * 0.235)
        draw.rounded_rectangle(
            [left + unit * start, y, left + unit * (start + width), y + bar_height],
            radius=radius,
            fill=color,
        )
    return image


def save(image: Image.Image, name: str) -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    image.save(TARGET / name)
    print(f"  {name}: {image.size[0]}x{image.size[1]}")


def main() -> None:
    save(mark(512), "icon-512.png")
    save(mark(192), "icon-192.png")
    save(mark(512, scale=0.72), "maskable-512.png")
    save(mark(180), "apple-touch-icon.png")
    save(mark(64), "favicon.png")
    save(mark(32), "favicon-32.png")
    print("Готово:", TARGET)


if __name__ == "__main__":
    main()
