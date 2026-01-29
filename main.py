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

def print_analysis_summary(decisions):
    """Gibt eine strukturierte Übersicht der KI-Entscheidungen auf der Konsole aus."""
    print("\n" + "="*40)
    print("📋 ZUSAMMENFASSUNG DER KI-ANALYSE")
    print("="*40)

    if not decisions:
        print("🤷‍♂️ Die KI hat keine Aktionen empfohlen (HOLD Strategie).")
        return

    print(f"💡 Es wurden {len(decisions)} Aktionen vorgeschlagen:\n")

    for i, trade in enumerate(decisions, 1):
        action = trade.get("aktion", "UNKNOWN").upper()
        name = trade.get("name", "Unbekannt")
        reason = trade.get("grund", "Keine Begründung angegeben.")
        
        if action == "BUY":
            isin = trade.get("isin", "N/A")
            amount = trade.get("betrag_eur", 0)
            print(f"{i}. 🟢 KAUFEN: {name}")
            print(f"    ├─ ISIN:   {isin}")
            print(f"    ├─ Budget: {amount} €")
            print(f"    └─ Grund:  {reason}")
            
        elif action == "SELL":
            print(f"{i}. 🔴 VERKAUFEN: {name}")
            print(f"    └─ Grund:  {reason}")
        
        else:
            print(f"{i}. ⚪ {action}: {name} ({reason})")
            
        print("-" * 40)

# --- KAUF LOGIK (Original) ---

async def execute_buy_order(page, stock_name, budget_eur):
    print(f"\n🛒 KAUF-START: {stock_name} (Budget: {budget_eur} €)")
    
    try:
        # 1. BUTTON KLICKEN
        new_paper_btn = page.locator("button:has-text('Neues Wertpapier')")
        if await new_paper_btn.count() == 0:
            await page.wait_for_selector("button:has-text('Neues Wertpapier')", timeout=5000)
        
        if not await new_paper_btn.first.is_visible():
            await new_paper_btn.first.scroll_into_view_if_needed()
        await new_paper_btn.first.click()

        # 2. SUCHE
        search_input_sel = "#live_search"
        try:
            await page.wait_for_selector(search_input_sel, state="visible", timeout=6000)
        except:
            await new_paper_btn.first.click(force=True)
            await page.wait_for_selector(search_input_sel, state="visible", timeout=6000)

        print(f"   -> Tippe '{stock_name}'...")
        await page.click(search_input_sel)
        await page.fill(search_input_sel, "") 
        await page.type(search_input_sel, stock_name, delay=150) 
        await asyncio.sleep(2.5)
        
        await page.keyboard.press("ArrowDown")
        await asyncio.sleep(0.3)
        await page.keyboard.press("ArrowDown")
        await asyncio.sleep(0.3)
        await page.keyboard.press("Enter")
        
        # 3. PREIS
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
        if current_price <= 0: return

        qty = math.floor(budget_eur / current_price)
        if qty < 1:
            print(f"⚠️ Budget zu klein.")
            return
        print(f"   -> Menge: {qty} Stück")

        # 4. ORDER
        await page.fill("input[formcontrolname='numOfShares']", str(qty))
        await asyncio.sleep(1)
        
        buy_btn = page.locator("button[type='submit']").filter(has_text="Kaufen")
        if await buy_btn.count() > 0:
            await buy_btn.first.click()
        else:
            await page.locator("button:has-text('Kaufen')").first.click()
        
        # 5. BESTÄTIGUNG
        await asyncio.sleep(2)
        pre_confirm = page.locator("button:has-text('Kostenpflichtig'), button:has-text('Order ausführen')")
        if await pre_confirm.count() > 0 and await pre_confirm.first.is_visible():
             await pre_confirm.first.click()
             await asyncio.sleep(2)

        success_btn = page.locator("button:has-text('Zum Musterdepot')")
        try:
            await success_btn.wait_for(state="visible", timeout=10000)
            print("✅ KAUF ERFOLGREICH.")
            await success_btn.click()
        except:
            await page.goto(OON_DEPOT_URL)

        await asyncio.sleep(3)

    except Exception as e:
        print(f"❌ ERROR BUY {stock_name}: {e}")

# --- VERKAUF LOGIK (NEU) ---

async def execute_sell_order(page, stock_name, quantity):
    print(f"\n📉 VERKAUF-START: {stock_name} (Menge: {quantity})")
    
    try:
        # 1. ZEILE IN DER TABELLE FINDEN
        # Wir suchen die Zeile, die den Namen der Aktie als Text enthält
        row = page.locator("tr[role='row']").filter(has_text=stock_name).first
        
        if await row.count() == 0:
            print(f"❌ Aktie '{stock_name}' nicht in der Tabelle gefunden!")
            return

        print("   -> Zeile gefunden. Öffne Menü (3 Punkte)...")
        
        # 2. MENÜ ÖFFNEN
        # Der Button mit den 3 Punkten (icon-points_navigation)
        menu_btn = row.locator("button.dropdown-toggle")
        await menu_btn.scroll_into_view_if_needed()
        await menu_btn.click()
        await asyncio.sleep(1)

        # 3. "AUS MUSTERDEPOT VERKAUFEN" KLICKEN
        # Das Dropdown öffnet sich meist im Body, nicht in der Row -> Page Locator nutzen
        sell_option = page.locator("a").filter(has_text="Aus Musterdepot verkaufen")
        if await sell_option.count() == 0:
             print("❌ Option 'Aus Musterdepot verkaufen' nicht sichtbar.")
             # Versuch: Menü nochmal klicken (manchmal schließt es sich)
             await menu_btn.click()
             await asyncio.sleep(1)
        
        await sell_option.first.click()
        
        # 4. FORMULAR AUSFÜLLEN
        print("   -> Warte auf Verkaufs-Popup...")
        qty_input_sel = "input[formcontrolname='numOfShares']"
        try:
            await page.wait_for_selector(qty_input_sel, state="visible", timeout=5000)
        except:
            print("❌ Popup nicht aufgegangen.")
            return
            
        await asyncio.sleep(1)
        print(f"   -> Trage Menge ein: {quantity}")
        await page.fill(qty_input_sel, str(quantity))
        await asyncio.sleep(1)

        # 5. BESTÄTIGEN (Button heißt hier meist "Verkaufen")
        submit_btn = page.locator("button[type='submit']").filter(has_text="Verkaufen")
        if await submit_btn.count() > 0:
            await submit_btn.first.click()
        else:
            # Fallback
            await page.locator("button:has-text('Verkaufen')").click()

        # 6. KOSTEN BESTÄTIGEN / ABSCHLUSS
        await asyncio.sleep(2)
        pre_confirm = page.locator("button:has-text('Kostenpflichtig'), button:has-text('Order ausführen')")
        if await pre_confirm.count() > 0 and await pre_confirm.first.is_visible():
             print("   -> Bestätige Ausführung...")
             await pre_confirm.first.click()
             await asyncio.sleep(2)

        # 7. ZURÜCK ZUM DEPOT
        success_btn = page.locator("button:has-text('Zum Musterdepot')")
        try:
            await success_btn.wait_for(state="visible", timeout=10000)
            print("✅ VERKAUF ERFOLGREICH.")
            await success_btn.click()
        except:
            print("⚠️ Kein Erfolgs-Button. Navigiere manuell.")
            await page.goto(OON_DEPOT_URL)

        await asyncio.sleep(3)
        safe_name = "".join([c for c in stock_name if c.isalnum()])
        await page.screenshot(path=f"success_sell_{safe_name}.png")

    except Exception as e:
        print(f"❌ ERROR SELL {stock_name}: {e}")
        await page.screenshot(path=f"error_sell.png")

# --- MAIN ---

async def run_bot():
    print("\n" + "="*40)
    print("🤖 TRADING BOT (BUY & SELL IMPLEMENTED)")
    print("="*40)

    async with async_playwright() as p:
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

        # 2. SCANNING
        print("📊 Lese Depot-Daten...")
        await page.goto(OON_DEPOT_URL)
        try:
            print("⏳ Warte auf Tabellen-Daten...")
            await page.wait_for_selector("a.tt-link", timeout=15000)
        except: pass

        depot_data = {"cash": 0.0, "stocks": []}

        # Cash
        try:
            spans = await page.locator("span[data-currency='EUR']").all()
            for span in spans:
                if "Geldkonto" in await span.locator("xpath=..").inner_text():
                    depot_data["cash"] = clean_amount(await span.inner_text())
        except: pass
        print(f"💰 Cash: {depot_data['cash']} €")

        # Stocks
        try:
            rows = await page.locator("tbody tr[role='row']").all()
            for row in rows:
                try:
                    name_el = row.locator("a.tt-link").first
                    if await name_el.count() > 0:
                        name = await name_el.inner_text()
                    else:
                        name = await row.locator("strong").first.inner_text()

                    qty_el = row.locator("[data-currency='STK']").first
                    qty_text = await qty_el.inner_text() if await qty_el.count() > 0 else "0"
                    qty = clean_amount(qty_text)
                    
                    val_el = row.locator("[data-currency='EUR']").last
                    val_text = await val_el.inner_text() if await val_el.count() > 0 else "0"
                    
                    if qty > 0:
                        stock_entry = {
                            "name": name.strip(),
                            "qty": qty,
                            "value_eur": clean_amount(val_text)
                        }
                        depot_data["stocks"].append(stock_entry)
                        print(f"   ✅ Besitz: {stock_entry['name']} ({stock_entry['qty']} Stk.)")
                except: continue
        except Exception as e:
            print(f"⚠️ Scan Fehler: {e}")

        # 3. KI RECHERCHE
        print("\n🧠 Frage KI (Google Search)...")
        await page.goto(AI_STUDIO_URL)
        await asyncio.sleep(4)

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt = f"""
        Zeit: {current_time} CET. 
        MEIN STATUS: Cash {depot_data['cash']} EUR.
        MEIN AKTUELLES DEPOT: {json.dumps(depot_data['stocks'])}
        
        AUFGABE:
        1. Recherchiere ausführlich aktuelle News zu meinen besessenen Aktien. Soll ich sie HALTEN oder VERKAUFEN ("SELL","HOLD")?
        2. Recherchiere ausführlich nach NEUEN Aktien mit hohem Potenzial ("BUY").
        3. WICHTIG: Gib bei BUY unbedingt die ISIN an, damit ich die richtige Aktie finde.
        4. Du musst nicht immer alles machen, wenn es nicht sicher vorteilhaft ist, kannst du auch buy oder sell aktionen weglassen und nur eins davon machen oder wenn alles gehalten werden soll, eine leere menge zurückgeben "[]"
        5. Du wirst in etwa einer Stunde erneut die chance haben die selbe Aufgabe mit dem neuen depot zu machen und so weiter, beachte das.
        6. Du musst nicht das ganze Budget investieren, dazu ist später immer noch Zeit.

        ANTWORT FORMAT (JSON LISTE):
        [
          {{ "aktion": "BUY", "name": "AktienName", "isin": "isin", "betrag_eur": betrag_eur, "grund": "News..." }},
          {{ "aktion": "SELL", "name": "MeineSchlechteAktie", "isin": "isin", "betrag_eur": betrag_eur, "grund": "Verlust..." }}
        ]
        Gib nur das JSON zurück.
        """

        try:
            await page.fill("div[contenteditable='true'], textarea", prompt)
            await page.locator(".run-button-label", has_text="Run").click()
            print("⏳ Recherche läuft (ca. 45s)...")
            await asyncio.sleep(60)
            ans = await page.locator('div[data-turn-role="Model"]').last.inner_text()
            decisions = extract_json_list(ans)
        except Exception as e:
            print(f"❌ KI Fehler: {e}")
            decisions = []
        
        # --- ZUSAMMENFASSUNG ANZEIGEN ---
        print_analysis_summary(decisions)

        # 4. EXECUTION
        if decisions:
            print("\n" + "⚡ EXECUTION PHASE".center(40, "="))
            
            if page.url != OON_DEPOT_URL:
                await page.goto(OON_DEPOT_URL)
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(5)

            for trade in decisions:
                typ = trade.get("aktion")
                name = trade.get("name")
                
                if typ == "BUY":
                    # Kauf-Logik: Nutze ISIN als Suchbegriff wenn da, sonst Name
                    amt = trade.get("betrag_eur", 0)
                    search_term = trade.get("isin") if trade.get("isin") else name
                    
                    if amt > depot_data["cash"]: amt = depot_data["cash"] * 0.95
                    
                    await execute_buy_order(page, search_term, amt)
                    depot_data["cash"] -= amt
                    await asyncio.sleep(3)
                
                elif typ == "SELL":
                    # Verkauf-Logik: Menge aus den gescannten Daten holen
                    owned_stock = next((s for s in depot_data["stocks"] if name in s["name"] or s["name"] in name), None)
                    
                    if owned_stock:
                        qty_to_sell = owned_stock["qty"] # Wir verkaufen alles
                        print(f"🔴 Verkaufe {qty_to_sell} Stück von {name}...")
                        await execute_sell_order(page, owned_stock["name"], qty_to_sell)
                        
                        # Depot Daten simulieren update
                        depot_data["cash"] += owned_stock["value_eur"] # Grobe Schätzung
                    else:
                        print(f"⚠️ Kann {name} nicht verkaufen: Nicht im Depot gefunden (Scan-Name beachten!).")

        print("\n✅ Fertig.")
        await asyncio.sleep(5)
        await context.close()

if __name__ == "__main__":
    asyncio.run(run_bot())