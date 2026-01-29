import asyncio
import os
import re
import json
import math
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# --- SETUP ---
load_dotenv()
MY_USERNAME = os.getenv("BOERSEN_EMAIL")
MY_PASSWORD = os.getenv("BOERSEN_PASSWORD")

OON_LOGIN_URL = "https://www.oon-boersespiel.at/de/start.html?login=open"
OON_DEPOT_URL = "https://www.oon-boersespiel.at/de/boersespiel.html#/personal/portfolio//detail/overview"
AI_STUDIO_URL = "https://aistudio.google.com/app/prompts/new_chat"
USER_DATA_DIR = "./google_session"

# --- TEST TRADES ---
TEST_TRADES = [
    {
        "aktion": "BUY",
        "name": "Apple Inc.", 
        "betrag_eur": 3000,
        "grund": "Testlauf"
    }
]

# --- EXECUTION FUNKTION ---

# here should be run-oon.py be started

# --- MAIN ---

async def run_bot():
    print("\n" + "="*40)
    print("🤖 TRADING BOT")
    print("="*40)
    print("1: KI-Modus")
    print("2: Test-Modus")
    mode = input("Wahl: ").strip()

    async with async_playwright() as p:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Browser startet...")
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context.set_default_timeout(15000)
        page = context.pages[0] if context.pages else await context.new_page()

        # 1. LOGIN
        print("🚀 Login...")
        await page.goto(OON_LOGIN_URL)
        try: await page.click("#onetrust-reject-all-handler", timeout=2000)
        except: pass

        if await page.is_visible("#usernameid"):
            await page.fill("#usernameid", MY_USERNAME)
            await page.fill("#passwordid", MY_PASSWORD)
            await page.keyboard.press("Enter")
            await asyncio.sleep(5)

        # 2. DEPOT DATEN HOLEN
        print("📊 Lese Depot-Daten...")
        await page.goto(OON_DEPOT_URL)
        try: await page.wait_for_selector("a.tt-link", timeout=15000)
        except: pass

        depot_data = {"cash": 0.0, "stocks": []}
        try:
            spans = await page.locator("span[data-currency='EUR']").all()
            for span in spans:
                if "Geldkonto" in await span.locator("xpath=..").inner_text():
                    depot_data["cash"] = clean_amount(await span.inner_text())
        except: pass
        
        print(f"💰 Cash: {depot_data['cash']} €")

        # 3. ENTSCHEIDUNG FINDEN
        decisions = []
        if mode == "2":
            decisions = TEST_TRADES
        else:
            print("🧠 Frage KI (Google Search)...")
            await page.goto(AI_STUDIO_URL)
            await asyncio.sleep(4)
            
            # Prompt
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            prompt = f"""
            Zeit: {current_time} CET. 
            Status: Cash {depot_data['cash']} EUR.
            Aufgabe: Du bist ein Trading Experte und deine Aufgabe ist es, so viel Profit wie möglich zu machen. Recherchiere was die besten Aktien sind und wie es gerade um die bereits besessenen steht. Du kannst neue kaufen und bereits Besessene verkaufen, wenn dies Vorteilhaft erscheint. Wenn nichts an der aktuellen Lage zu verbessern ist, gib eine Leere Menge [] zurück.
            Entscheidung: Kaufliste erstellen.
            Format JSON Beispiel: 
            [
                {{ "aktion": "BUY", "name": "Aktienname", "betrag_eur": 2000, "grund": "..." }},
                {{ "aktion": "SELL", "name": "Aktienname", "betrag_eur": 2000, "grund": "..." }}
            ]
            """
            try:
                await page.fill("div[contenteditable='true'], textarea", prompt)
                await page.locator(".run-button-label", has_text="Run").click()
                print("⏳ Recherche läuft (40s)...")
                await asyncio.sleep(40)
                ans = await page.locator('div[data-turn-role="Model"]').last.inner_text()
                decisions = extract_json_list(ans)
            except Exception as e:
                print(f"❌ KI Fehler: {e}")

        # 4. EXECUTION PHASE (HIER IST DER FIX!)
        if decisions:
            print("\n" + "⚡ EXECUTION PHASE".center(40, "="))
            
            # FIX: Wir müssen ZWINGEND zurück zum Depot navigieren!
            if page.url != OON_DEPOT_URL:
                print(f"🔙 Navigiere zurück zum Depot: {OON_DEPOT_URL}")
                await page.goto(OON_DEPOT_URL)
                print("⏳ Warte auf Angular...")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(5) # Sicherstellen, dass Buttons geladen sind

            for trade in decisions:
                if trade["aktion"] == "BUY":
                    amt = trade["betrag_eur"]
                    if amt > depot_data["cash"]: amt = depot_data["cash"] * 0.95
                    await execute_buy_order(page, trade["name"], amt)
                    # Kurze Pause nach jedem Trade
                    await asyncio.sleep(4)
                
                elif trade["aktion"] == "SELL":
                    print(f"🔴 SELL {trade['name']} (Logik folgt später).")

        print("\n✅ Fertig.")
        await asyncio.sleep(5)
        await context.close()

if __name__ == "__main__":
    asyncio.run(run_bot())