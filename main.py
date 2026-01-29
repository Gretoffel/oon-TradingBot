#
# Copyright (C) 2026 Gretoffel
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

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

# --- HILFSFUNKTIONEN ---

def clean_amount(text):
    if not text: return 0.0
    cleaned = re.sub(r'[^\d,.-]', '', text)
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace('.', '')
    cleaned = cleaned.replace(',', '.')
    try: return float(cleaned)
    except: return 0.0

def extract_json_list(text):
    if not text: return None
    try:
        text = text.replace('```json', '').replace('```', '')
        text = re.sub(r'\[\d+\]', '', text) 
        text = text.replace('[]', '') 
        start = text.find('[')
        end = text.rfind(']')
        if start == -1 or end == -1: return None
        return json.loads(text[start : end + 1])
    except: return None

# --- EXECUTION FUNKTION ---

async def execute_buy_order(page, stock_name, budget_eur):
    print(f"\n🛒 KAUF-START: {stock_name} (Budget: {budget_eur} €)")
    
    try:
        # 1. BUTTON KLICKEN
        print("   -> Suche Button 'Neues Wertpapier'...")
        new_paper_btn = page.locator("button:has-text('Neues Wertpapier')")
        
        # Falls Button nicht sofort da ist, kurz warten/scrollen
        if await new_paper_btn.count() == 0:
            await page.wait_for_selector("button:has-text('Neues Wertpapier')", timeout=5000)
        
        if not await new_paper_btn.first.is_visible():
            await new_paper_btn.first.scroll_into_view_if_needed()
        
        await new_paper_btn.first.click()

        # 2. SUCHE & AUSWAHL
        search_input_sel = "#live_search"
        print("   -> Warte auf Suchfeld...")
        try:
            await page.wait_for_selector(search_input_sel, state="visible", timeout=6000)
        except:
            print("⚠️ Klicke Button erneut (Angular Glitch)...")
            await new_paper_btn.first.click(force=True)
            await page.wait_for_selector(search_input_sel, state="visible", timeout=6000)

        print(f"   -> Tippe '{stock_name}'...")
        await page.click(search_input_sel)
        await page.fill(search_input_sel, "") 
        await page.type(search_input_sel, stock_name, delay=150) 
        
        print("   -> Wähle Ergebnis (2x Pfeil Runter)...")
        await asyncio.sleep(2.5)
        
        await page.keyboard.press("ArrowDown")
        await asyncio.sleep(0.3)
        await page.keyboard.press("ArrowDown")
        await asyncio.sleep(0.3)
        await page.keyboard.press("Enter")
        
        # 3. PREIS & MENGE
        print("   -> Warte auf Preis...")
        price_selector = "input[formcontrolname='price']"
        try:
            await page.wait_for_selector(price_selector, state="visible", timeout=10000)
        except:
            print("❌ Timeout: Kauf-Fenster ging nicht auf.")
            return

        await asyncio.sleep(2)
        price_str = await page.input_value(price_selector)
        
        if not price_str:
             await page.click(price_selector)
             await asyncio.sleep(1)
             price_str = await page.input_value(price_selector)

        current_price = clean_amount(price_str)
        print(f"   -> Kurs: {current_price} €")
        
        if current_price <= 0:
            print("❌ Ungültiger Preis.")
            return

        qty = math.floor(budget_eur / current_price)
        if qty < 1:
            print(f"⚠️ Budget zu klein für 1 Aktie.")
            return
        print(f"   -> Menge: {qty} Stück")

        # 4. ORDER ABSETZEN
        await page.fill("input[formcontrolname='numOfShares']", str(qty))
        await asyncio.sleep(1)
        
        print("   -> Klicke 'Kaufen'...")
        buy_btn = page.locator("button[type='submit']").filter(has_text="Kaufen")
        if await buy_btn.count() > 0:
            await buy_btn.first.click()
        else:
            await page.locator("button:has-text('Kaufen')").first.click()
        
        # 5. BESTÄTIGUNG & ABSCHLUSS
        await asyncio.sleep(2)
        
        # Check auf Kostenpflichtig/Bestätigen
        pre_confirm = page.locator("button:has-text('Kostenpflichtig'), button:has-text('Order ausführen')")
        if await pre_confirm.count() > 0 and await pre_confirm.first.is_visible():
             print("   -> Bestätige Kosten...")
             await pre_confirm.first.click()
             await asyncio.sleep(2)

        # Check auf 'Zum Musterdepot' (Erfolg)
        print("   -> Warte auf Abschluss...")
        success_btn = page.locator("button:has-text('Zum Musterdepot')")
        try:
            await success_btn.wait_for(state="visible", timeout=10000)
            print("✅ ERFOLG! Zurück zum Depot.")
            await success_btn.click()
        except:
            print("⚠️ Kein Erfolgs-Button. Klicke in den Hintergrund zum Schließen.")
            # Fallback: Seite neu laden oder navigieren, um Overlay loszuwerden
            await page.goto(OON_DEPOT_URL)

        await asyncio.sleep(3)
        await page.screenshot(path=f"success_{stock_name}.png")

    except Exception as e:
        print(f"❌ ERROR BEI {stock_name}: {e}")
        await page.screenshot(path=f"error_{stock_name}.png")


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