"""Собирает галерею скриншотов для README из «сырых» PNG.

Сырые кадры снимает `tests/shoot_web.py` (PNG, device_scale_factor 1.5–2),
они тяжёлые. Здесь они уменьшаются, конвертируются в прогрессивный JPEG
и раскладываются по `docs/screenshots/` под говорящими именами.

    python tests/shoot_web.py      # сначала снять кадры
    python scripts/export_screenshots.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\HP\AppData\Local\Temp\opencode\shots")
DST = ROOT / "docs" / "screenshots"

# сырое имя -> (имя в репозитории, целевая ширина, качество)
MAPPING: dict[str, tuple[str, int, int]] = {
    # десктоп
    "01-home.png": ("desktop-home.jpg", 1280, 84),
    "04-week.png": ("desktop-week.jpg", 1280, 84),
    "05-day.png": ("desktop-day.jpg", 1280, 84),
    "02-browse.png": ("desktop-browse.jpg", 1280, 84),
    "08-search.png": ("desktop-search.jpg", 1100, 84),
    "06-home-dark.png": ("desktop-home-dark.jpg", 1280, 84),
    "07-week-dark.png": ("desktop-week-dark.jpg", 1280, 84),
    # телефон
    "10-m-home.png": ("mobile-home.jpg", 430, 86),
    "11-m-week.png": ("mobile-week.jpg", 430, 86),
    "12-m-day.png": ("mobile-day.jpg", 430, 86),
    "13-m-menu.png": ("mobile-menu.jpg", 430, 86),
    "15-m-browse.png": ("mobile-browse.jpg", 430, 86),
    "16-m-home-dark.png": ("mobile-home-dark.jpg", 430, 86),
    "17-m-week-dark.png": ("mobile-week-dark.jpg", 430, 86),
    "14-m-offline.png": ("mobile-offline.jpg", 430, 86),
}


def export() -> int:
    if not SRC.is_dir():
        print(f"нет каталога со скриншотами: {SRC}")
        return 1
    DST.mkdir(parents=True, exist_ok=True)

    done = 0
    missing: list[str] = []
    for raw, (target, width, quality) in MAPPING.items():
        source = SRC / raw
        if not source.is_file():
            missing.append(raw)
            continue
        with Image.open(source) as image:
            image = image.convert("RGB")
            if image.width > width:
                height = round(image.height * width / image.width)
                image = image.resize((width, height), Image.LANCZOS)
            out = DST / target
            image.save(out, "JPEG", quality=quality, optimize=True, progressive=True)
        done += 1
        print(f"  {raw:24} -> {target:26} {out.stat().st_size // 1024:>4} КБ")

    if missing:
        print("\nне найдены:", ", ".join(missing))
        print("сначала запустите: python tests/shoot_web.py")
    print(f"\nготово: {done} из {len(MAPPING)}")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(export())
