import asyncio
import config

async def check_soft_crash(page):
    """
    Prüft auf 'Aw, Snap!' Fehler.
    Gibt True zurück, wenn ein Crash erkannt und ein Reload angestoßen wurde.
    """
    try:
        title = await page.title()
        if "Aw, Snap!" in title:
            print("🚨 SOFT CRASH DETECTED (Title). Versuche Reload...")
            await page.reload()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(4)
            return True

        try:
            crash_header = page.locator("h1").filter(has_text="Aw, Snap!")
            if await crash_header.count() > 0 and await crash_header.first.is_visible():
                print("🚨 SOFT CRASH DETECTED (Header). Versuche Reload...")
                await page.reload()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(4)
                return True
        except:
            pass 
            
    except Exception as e:
        raise e 
            
    return False

async def create_browser_context(playwright):
    """
    Erstellt einen persistenten Browser-Kontext mit den notwendigen Einstellungen.
    """
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=config.USER_DATA_DIR,
        channel="chrome",  # <--- FORCE REAL CHROME
        headless=False, 
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox"
        ]
    )
    context.set_default_timeout(15000)
    return context
