import asyncio
import os
import re
import json
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

# --- HILFSFUNKTIONEN ---

def clean_amount(text):
    if not text: return 0.0
    # Entfernt alles außer Zahlen, Minus, Komma, Punkt
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
        text = re.sub(r'\[\d+\]', '', text) # Quellen [1] entfernen
        text = text.replace('[]', '') 
        start = text.find('[')
        end = text.rfind(']')
        if start == -1 or end == -1: return None
        return json.loads(text[start : end + 1])
    except: return None

async def run_bot():
    async with async_playwright() as p:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🤖 Bot startet...")
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context.set_default_timeout(10000) 
        page = context.pages[0] if context.pages else await context.new_page()

        # --- 1. DATEN AUSLESEN ---
        print("🚀 Lese Depot-Daten...")
        await page.goto(OON_LOGIN_URL)
        
        try:
            await page.click("#onetrust-reject-all-handler", timeout=2000)
        except: pass

        if await page.is_visible("#usernameid"):
            await page.fill("#usernameid", MY_USERNAME)
            await page.fill("#passwordid", MY_PASSWORD)
            await page.keyboard.press("Enter")
            await asyncio.sleep(5)

        await page.goto(OON_DEPOT_URL)
        try:
            print("⏳ Warte auf Tabellen-Daten...")
            await page.wait_for_selector("a.tt-link", timeout=15000)
        except:
            print("⚠️ Zeitüberschreitung beim Laden der Tabelle. Versuche weiterzumachen.")

        depot_data = {"cash": 0.0, "stocks": []}

        # A) Cash auslesen
        try:
            spans = await page.locator("span[data-currency='EUR']").all()
            for span in spans:
                val = await span.inner_text()
                parent_text = await span.locator("xpath=..").inner_text()
                if "Geldkonto" in parent_text:
                    depot_data["cash"] = clean_amount(val)
                    print(f"💰 Geldkonto erkannt: {val}")
        except Exception as e:
            print(f"⚠️ Cash Fehler: {e}")

        # B) Aktien filtern & lesen
        print("📊 Analysiere Aktienliste...")
        try:
            rows = await page.locator("tbody tr[role='row']").all()
            print(f"ℹ️ {len(rows)} Tabellen-Zeilen gefunden (inkl. möglicher Leerzeilen).")

            for i, row in enumerate(rows):
                try:
                    # 1. NAME
                    name_el = row.locator("a.tt-link").first
                    if await name_el.count() > 0:
                        name = await name_el.inner_text()
                    else:
                        name = await row.locator("strong").first.inner_text()

                    # 2. MENGE
                    qty_el = row.locator("[data-currency='STK']").first
                    qty_text = await qty_el.inner_text() if await qty_el.count() > 0 else "0"
                    qty = clean_amount(qty_text)

                    # 3. WERT
                    val_el = row.locator("[data-currency='EUR']").last
                    val_text = await val_el.inner_text() if await val_el.count() > 0 else "0"
                    
                    # --- DER NEUE FILTER ---
                    if qty > 0:
                        stock_entry = {
                            "name": name.strip(),
                            "qty": qty,
                            "value_eur": clean_amount(val_text)
                        }
                        depot_data["stocks"].append(stock_entry)
                        print(f"   ✅ Gefunden: {stock_entry['name']} ({stock_entry['qty']} Stk.)")
                    else:
                        # Debug-Ausgabe für ignorierte Zeilen (kannst du später auskommentieren)
                        # print(f"   👻 Ignoriere Zeile '{name}' wegen Menge 0.")
                        pass

                except Exception as row_e:
                    # Leise Fehlerbehandlung bei leeren Zeilen
                    continue

        except Exception as e:
            print(f"⚠️ Tabellen-Fehler: {e}")

        print(f"📊 FINALER STATUS: {len(depot_data['stocks'])} aktive Positionen.")

        # --- 2. KI PLAYGROUND ---
        print("🧠 Befrage Gemini...")
        await page.goto(AI_STUDIO_URL)
        await asyncio.sleep(4)

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt = f"""
        Zeit: {current_time} CET. Trading Bot für OÖN-Spiel.
        STATUS: Cash {depot_data['cash']} EUR, Aktien: {json.dumps(depot_data['stocks'])}
        
        AUFGABE:
        1. Google Search Live-Daten (ATX, Tech-Aktien, DAX).
        2. Strategie entwickeln (Kaufen/Verkaufen).
        3. Budget beachten!
        
        ANTWORT FORMAT (JSON-Liste Only, KEINE Quellenangaben!):
        [
          {{ "aktion": "BUY", "name": "Name", "betrag_eur": 5000, "grund": "Info" }},
          {{ "aktion": "SELL", "name": "Name", "menge": "ALL", "grund": "Info" }}
        ]
        """

        try:
            input_sel = "div[contenteditable='true'], textarea"
            await page.wait_for_selector(input_sel, timeout=10000)
            await page.fill(input_sel, prompt)
            
            await page.locator(".run-button-label", has_text="Run").click()
            print("⏳ Recherche läuft (40s)...")
            await asyncio.sleep(40)

            last_ans = await page.locator('div[data-turn-role="Model"]').last.inner_text()
            decisions = extract_json_list(last_ans)

            print("\n" + "="*40)
            print("   🤖 KI STRATEGIE")
            print("="*40)

            if decisions:
                for d in decisions:
                    typ = d.get('aktion')
                    name = d.get('name')
                    val = d.get('betrag_eur', d.get('menge'))
                    
                    if typ == "BUY":
                        print(f"🟢 BUY  : {name} ({val} €)")
                    elif typ == "SELL":
                        print(f"🔴 SELL : {name} ({val})")
                    print(f"   Grund: {d.get('grund')}")
                    print("-" * 20)
            else:
                print("❌ Keine lesbare JSON-Strategie erhalten.")

        except Exception as e:
            print(f"❌ KI Fehler: {e}")

        await page.screenshot(path="bot_result.png")
        await asyncio.sleep(5)
        await context.close()

if __name__ == "__main__":
    asyncio.run(run_bot())