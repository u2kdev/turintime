"""Визуальная проверка веб-приложения: скриншоты основных экранов."""
import asyncio
import sys

from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8000"
OUT = "C:/Users/HP/AppData/Local/Temp/opencode/shots"
TARGET = sys.argv[1] if len(sys.argv) > 1 else "all"


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        desktop = await browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1.5)
        page = await desktop.new_page()
        errors = []
        page.on("console", lambda msg: errors.append(f"{msg.type}: {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))

        await page.goto(BASE, wait_until="networkidle")
        await page.wait_for_timeout(1400)
        await page.screenshot(path=f"{OUT}/01-home.png", full_page=True)

        await page.goto(BASE + "/browse/class", wait_until="networkidle")
        await page.wait_for_timeout(700)
        await page.screenshot(path=f"{OUT}/02-browse.png", full_page=True)

        # выбираем группу через поиск
        await page.fill("#browse-input", "IT1-26")
        await page.wait_for_timeout(500)
        await page.screenshot(path=f"{OUT}/03-browse-filter.png")
        await page.click(".catalog__items a")
        await page.wait_for_timeout(1600)
        await page.screenshot(path=f"{OUT}/04-week.png", full_page=True)

        await page.click('#view-switch button[data-view="day"]')
        await page.wait_for_timeout(900)
        await page.screenshot(path=f"{OUT}/05-day.png", full_page=True)

        # тёмная тема
        await page.goto(BASE, wait_until="networkidle")
        await page.wait_for_timeout(900)
        await page.click("#btn-theme")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{OUT}/06-home-dark.png", full_page=True)
        await page.goto(BASE + "/class/*98", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{OUT}/07-week-dark.png", full_page=True)
        await page.click("#btn-theme")

        # поиск
        await page.goto(BASE, wait_until="networkidle")
        await page.click("#btn-search")
        await page.fill("#search-input", "FAYZI")
        await page.wait_for_timeout(900)
        await page.screenshot(path=f"{OUT}/08-search.png")

        # мобильные экраны
        mobile = await browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                                           is_mobile=True, has_touch=True)
        m = await mobile.new_page()
        m.on("pageerror", lambda exc: errors.append(f"mobile pageerror: {exc}"))
        await m.goto(BASE, wait_until="networkidle")
        await m.wait_for_timeout(1300)
        await m.screenshot(path=f"{OUT}/10-m-home.png", full_page=True)
        await m.goto(BASE + "/class/*98", wait_until="networkidle")
        await m.wait_for_timeout(1500)
        await m.screenshot(path=f"{OUT}/11-m-week.png", full_page=True)
        await m.click('#view-switch button[data-view="day"]')
        await m.wait_for_timeout(800)
        await m.screenshot(path=f"{OUT}/12-m-day.png", full_page=True)
        await m.click("#btn-menu")
        await m.wait_for_timeout(600)
        await m.screenshot(path=f"{OUT}/13-m-menu.png")
        await m.click("#menu-close")

        # полноценный офлайн: отключаем сеть и перезагружаем
        await m.goto(BASE + "/class/*98", wait_until="networkidle")
        await m.wait_for_timeout(1200)
        await mobile.set_offline(True)
        await m.reload(wait_until="domcontentloaded")
        await m.wait_for_timeout(1500)
        await m.screenshot(path=f"{OUT}/14-m-offline.png", full_page=True)

        await browser.close()
        print("Ошибки консоли:" if errors else "Ошибок консоли нет")
        for error in errors[:20]:
            print("  ", error)


asyncio.run(main())
