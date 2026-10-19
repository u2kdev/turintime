"""
Скачивает шрифты с Google Fonts и кладёт их локально в web/assets/fonts.

Нужно для офлайн-режима: приложение должно открываться без интернета,
значит шрифты не могут подгружаться с fonts.googleapis.com.

    python scripts/fetch_fonts.py
"""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "web" / "assets" / "fonts"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# Семейства: имя файла -> параметры Google Fonts.
# Оставляем только нужные подмножества: latin, latin-ext (узбекские ʻ / ʼ) и cyrillic.
FAMILIES = {
    "manrope": "Manrope:wght@400..800",
    "literata": "Literata:wght@400..700",
    "jetbrains-mono": "JetBrains+Mono:wght@400..600",
}
KEEP_SUBSETS = {"latin", "latin-ext", "cyrillic"}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    css_out: list[str] = [
        "/* Локальные шрифты для офлайн-режима. Скачано scripts/fetch_fonts.py. */",
    ]

    for name, spec in FAMILIES.items():
        url = f"https://fonts.googleapis.com/css2?family={spec}&display=swap"
        css = fetch(url).decode("utf-8")
        blocks = re.findall(r"/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{.*?\})", css, re.S)
        if not blocks:
            blocks = [("latin", block) for block in re.findall(r"(@font-face\s*\{.*?\})", css, re.S)]
        kept = 0
        for subset, block in blocks:
            if subset not in KEEP_SUBSETS:
                continue
            match = re.search(r"url\((https://[^)]+)\)", block)
            if not match:
                continue
            source = match.group(1)
            filename = f"{name}-{subset}.woff2"
            (TARGET / filename).write_bytes(fetch(source))
            block = block.replace(source, f"./{filename}")
            block = re.sub(r"\s+", " ", block).strip()
            css_out.append(f"/* {name} · {subset} */\n{block}")
            kept += 1
        print(f"  {name}: {kept} файла(ов)")
        if kept == 0:
            raise SystemExit(f"Не удалось скачать шрифт {name}")

    (TARGET / "fonts.css").write_text("\n".join(css_out) + "\n", encoding="utf-8")
    total = sum(item.stat().st_size for item in TARGET.glob("*.woff2"))
    print(f"Готово: {TARGET} — {total / 1024:.0f} КБ")


if __name__ == "__main__":
    main()
