import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

import config
import remote_manager  # <--- NEU: Für Status-Updates an das Dashboard
from utils import clean_amount, extract_json_list, print_analysis_summary, get_todays_log_content
from actions import execute_buy_order, execute_sell_order

async def run_bot_cycle():
    """Führt einen einzelnen Zyklus des Bots aus."""
    print("\n" + "="*40)
    print("🤖 TRADING BOT ZYKLUS STARTET")
    
    # --- STATUS UPDATE: START ---
    remote_manager.update_status("Start", "Initialisiere Browser...", balance=0.0)
    # ----------------------------

    if config.TEST_MODE:
        print("⚠️  ACHTUNG: TEST-MODUS AKTIV (Keine KI)")
    print("="*40)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=config.USER_DATA_DIR,
            headless=False, # Setze auf True, wenn der Browser unsichtbar sein soll
            args=["--disable-blink-features=AutomationControlled"]
        )
        context.set_default_timeout(15000)
        
        # Variable für Cash-Tracking im Dashboard
        current_cash = 0.0

        try:
            page = context.pages[0] if context.pages else await context.new_page()

            # 1. LOGIN
            # --- STATUS UPDATE: LOGIN ---
            remote_manager.update_status("Login", "Logge bei OON ein...")
            # ----------------------------
            print("🚀 Login...")
            try:
                await page.goto(config.OON_LOGIN_URL)
                try: await page.click("#onetrust-reject-all-handler", timeout=2000)
                except: pass

                if await page.is_visible("#usernameid"):
                    await page.fill("#usernameid", config.MY_USERNAME)
                    await page.fill("#passwordid", config.MY_PASSWORD)
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(5)
            except Exception as e:
                print(f"⚠️ Login-Check übersprungen oder Fehler: {e}")

            # 2. SCANNING
            # --- STATUS UPDATE: SCAN ---
            remote_manager.update_status("Scan", "Lese Depot und Cash aus...")
            # ---------------------------
            print("📊 Lese Depot-Daten...")
            await page.goto(config.OON_DEPOT_URL)
            try:
                print("⏳ Warte auf Tabellen-Daten...")
                await page.wait_for_selector("a.tt-link", timeout=15000)
            except: pass

            depot_data = {
                "cash": 0.0, 
                "stocks": [],
                "open_orders": [] 
            }

            # --- A) CASH AUSLESEN ---
            try:
                spans = await page.locator("span[data-currency='EUR']").all()
                for span in spans:
                    if "Geldkonto" in await span.locator("xpath=..").inner_text():
                        depot_data["cash"] = clean_amount(await span.inner_text())
            except: pass
            
            # Update Cash Variable & Status
            current_cash = depot_data["cash"]
            print(f"💰 Verfügbares Cash (laut Anzeige): {current_cash} €")
            remote_manager.update_status("Scan", "Analysiere Positionen...", balance=current_cash)

            # --- B) BESTAND AUSLESEN ---
            try:
                rows = await page.locator("tbody tr[role='row']").all()
                for row in rows:
                    try:
                        row_text = await row.inner_text()
                        if "Warten auf Ausführung" in row_text or "Bestens" in row_text or "Limit" in row_text:
                            continue 

                        name_el = row.locator("a.tt-link").first
                        if await name_el.count() > 0:
                            name = await name_el.inner_text()
                        else:
                            name_items = await row.locator("strong").all()
                            if name_items: name = await name_items[0].inner_text()
                            else: continue

                        qty_el = row.locator("[data-currency='STK']").first
                        qty_text = await qty_el.inner_text() if await qty_el.count() > 0 else "0"
                        
                        val_el = row.locator("[data-currency='EUR']").last
                        val_text = await val_el.inner_text() if await val_el.count() > 0 else "0"
                        
                        perf_text = "N/A"
                        try:
                            cells = await row.locator("td").all()
                            for cell in cells:
                                cell_txt = await cell.inner_text()
                                if "%" in cell_txt:
                                    perf_text = cell_txt.replace("\n", "").strip()
                                    break
                        except: pass

                        qty = clean_amount(qty_text)
                        if qty > 0:
                            stock_entry = {
                                "name": name.strip(),
                                "qty": qty,
                                "value_eur": clean_amount(val_text),
                                "performance_since_buy": perf_text 
                            }
                            depot_data["stocks"].append(stock_entry)
                            print(f"   ✅ Besitz: {stock_entry['name']} | {stock_entry['qty']} Stk. | Perf: {stock_entry['performance_since_buy']}")
                    except: continue
            except Exception as e:
                print(f"⚠️ Scan Fehler (Bestand): {e}")

            # --- C) OFFENE AUFTRÄGE AUSLESEN ---
            print("🔍 Prüfe auf offene Aufträge...")
            try:
                open_order_rows = await page.locator("xpath=//h3[contains(text(), 'Offene Aufträge')]/following::tt-table[1]//tbody//tr").all()
                for row in open_order_rows:
                    try:
                        full_text = await row.inner_text()
                        if not full_text.strip(): continue

                        cell_1 = row.locator("td").nth(0)
                        name = await cell_1.locator("strong").inner_text()
                        
                        isin_match = re.search(r'\b([A-Z]{2}[A-Z0-9]{9}\d)\b', full_text)
                        isin = isin_match.group(1) if isin_match else "Unbekannt"

                        type_text = await row.locator("td").nth(1).inner_text()
                        order_type = "BUY" if "Kauf" in type_text else "SELL" if "Verkauf" in type_text else "UNKNOWN"

                        qty_text = await row.locator("td").nth(2).inner_text()
                        qty = clean_amount(qty_text)

                        status_text = await row.locator("td").nth(4).inner_text()

                        entry = {
                            "name": name.strip(),
                            "isin": isin,
                            "type": order_type,
                            "qty": qty,
                            "status": status_text.strip()
                        }
                        depot_data["open_orders"].append(entry)
                        print(f"   ⏳ Offener Auftrag: {entry['type']} {entry['qty']}x {entry['name']}")
                    except Exception as e:
                        continue
            except Exception as e:
                print(f"⚠️ Scan Fehler (Offene Aufträge): {e}")


            # ---------------------------------------------------------
            # 3. ENTSCHEIDUNG (KI ODER TEST)
            # ---------------------------------------------------------
            decisions = []
            
            # --- STATUS UPDATE: KI ---
            remote_manager.update_status("KI", "Frage KI nach Strategie...", balance=current_cash)
            # -------------------------

            if config.TEST_MODE:
                print("\n🧪 TEST-MODUS: Überspringe KI. Lade Test-Daten...")
                decisions = config.TEST_ORDERS
            else:
                print("\n🧠 Frage KI (Google Search)...")
                
                todays_logs = get_todays_log_content()

                await page.goto(config.AI_STUDIO_URL)
                await asyncio.sleep(4)

                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                prompt = f"""
                Zeit: {current_time} CET. 
                
                MEIN FINANZ-STATUS:
                - Verfügbares Cash (Anzeige): {depot_data['cash']} EUR.
                
                BEREITS HEUTE DURCHGEFÜHRTE TRANSAKTIONEN (Log):
                {todays_logs}
                
                MEIN AKTUELLES DEPOT (Besitz): 
                {json.dumps(depot_data['stocks'])}
                
                MEINE OFFENEN AUFTRÄGE (Warten auf Ausführung):
                {json.dumps(depot_data['open_orders'])}
                
                AUFGABE:
                1. Analysiere mein Depot und offene Aufträge.
                2. Ziehe vom Cash gedanklich ab, was für die offenen "BUY"-Aufträge nötig ist (Schätze den Betrag).
                3. Schlage "SELL" vor für schlechte Aktien im Besitz.
                4. Schlage "BUY" vor für neue Chancen.
                5. Du musst nicht immer alles machen, wenn es nicht sicher vorteilhaft ist, kannst du auch buy oder sell aktionen weglassen und nur eins davon machen oder wenn alles gehalten werden soll, eine leere menge zurückgeben "[]"
                6. Du wirst in etwa 10-20 minuten erneut die chance haben die selbe Aufgabe mit dem neuen depot zu machen und so weiter, beachte das.
                7. Du musst nicht das ganze Budget investieren, dazu ist später immer noch Zeit.
                
                REGELN:
                - Beim Kaufen fallen Gebühren an (meißt etwa 5 - 20€), führe also nur Kaufaktionen durch die wirklich etwas bringen. Du erhältst die selbe investing Aufgabe in 20 Minuten wieder, wenn du jedes Mal viel verkaufst und neu kaufst, könnten die Gebühren sich deutlich aufsummieren, entscheide sinnvoll.
                - Kaufe KEINE Aktie, die bereits in "MEINE OFFENEN AUFTRÄGE" als BUY steht (Vermeidung von Doppelkauf), außer es ist sinnvoll, mehr davon zu kaufen.
                - Kaufe KEINE Aktie, die ich bereits besitze (außer Nachkauf ist sinnvoll).
                - Gib bei BUY unbedingt die ISIN an.
                - Wenn das (bereinigte) Budget knapp ist, oder keine Aktion nötig ist, gib einfach eine leere Liste zurück "[]".
                - Anmerkung: BUY und SELL aktionen sind optional, du musst sie nicht durchführen.
                - Lass vieleicht ein wenig Geld für zukünftige, eventuell bessere, Investitionen übrig.

                ANTWORT FORMAT (JSON LISTE):
                [
                  {{ "aktion": "BUY", "name": "Name", "isin": "ISIN", "betrag_eur": 1000, "grund": "News..." }},
                  {{ "aktion": "SELL", "name": "Name", "isin": "ISIN", "betrag_eur": 1000, "grund": "Gewinnmitnahme..." }}
                ]
                Gib nur das JSON zurück.
                """

                try:
                    await page.fill("div[contenteditable='true'], textarea", prompt)
                    
                    # Run Button
                    await page.locator(".run-button-label", has_text="Run").click()
                    print("⏳ Recherche läuft...")

                    max_retries = 3
                    
                    # Äußerer Loop: Versuche den gesamten Turn neu, falls es crasht
                    for attempt in range(max_retries):
                        print(f"   ... Warte auf Antwort (Versuch {attempt + 1})...")
                        
                        found_answer = False
                        last_text_len = 0 # Zum Prüfen, ob noch getippt wird
                        
                        # --- NEU: SMART POLLING MIT STABILITÄTS-CHECK ---
                        # Wir warten maximal 15x 4 Sekunden = 60 Sekunden pro Versuch
                        for poll_tick in range(15): 
                            await asyncio.sleep(4) 
                            
                            # 1. ERROR CHECK (Sofort prüfen)
                            error_locator = page.locator(".model-error")
                            if await error_locator.count() > 0 and await error_locator.last.is_visible():
                                print("\n⚠️ ACHTUNG: Google AI Fehler erkannt! (model-error)")
                                try:
                                    # Fix: Maus-Trick anwenden, um Button sichtbar zu machen
                                    error_element = error_locator.last
                                    await error_element.scroll_into_view_if_needed()
                                    
                                    box = await error_element.bounding_box()
                                    if box:
                                        # Maus zur Mitte bewegen
                                        await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                                        await asyncio.sleep(0.5)
                                    else:
                                        await error_element.hover(force=True)
                                    
                                    await asyncio.sleep(1)

                                    rerun_btns = page.locator("button[aria-label='Rerun this turn']")
                                    if await rerun_btns.count() > 0:
                                        print("🔄 Rerun-Button gefunden. Klicke (JS)...")
                                        await rerun_btns.last.evaluate("node => node.click()")
                                        # Wir brechen den Polling-Loop ab, damit der äußere Loop (attempt) neu wartet
                                        break 
                                    else:
                                        print("❌ Rerun-Button trotz Hover nicht im DOM gefunden.")
                                        break
                                except Exception as click_err:
                                    print(f"❌ Fehler beim Rerun-Klick: {click_err}")
                                    break
                            
                            # 2. ANTWORT CHECK (Mit Stabilitäts-Prüfung)
                            # Wir prüfen nur, wenn kein Fehler da war
                            ans_locator = page.locator('div[data-turn-role="Model"]').last
                            if await ans_locator.count() > 0:
                                current_text = await ans_locator.inner_text()
                                current_len = len(current_text)
                                
                                # A) Ist Text da und sieht er grob nach JSON aus?
                                if current_len > 20 and "]" in current_text:
                                    
                                    # B) STABILITÄTS-CHECK: Hat sich der Text seit dem letzten Loop verändert?
                                    if current_len == last_text_len:
                                        # Text-Länge ist gleich geblieben -> KI hat aufgehört zu tippen.
                                        
                                        # C) Validierung: Ist es wirklich valides JSON?
                                        parsed_json = extract_json_list(current_text)
                                        if parsed_json is not None:
                                            decisions = parsed_json
                                            found_answer = True
                                            print("   ✅ Antwort ist vollständig und stabil.")
                                            break
                                        else:
                                            # Es könnte sein, dass noch Müll drumherum steht oder JSON kaputt ist
                                            # Wir warten einfach weiter im nächsten Tick
                                            pass
                                    else:
                                        # Text wird noch länger -> KI tippt gerade noch
                                        last_text_len = current_len
                                        # Optional: print(f"   ... schreibt noch ({current_len})...")
                                else:
                                    # Noch kein schließendes ']' oder zu kurz -> Speicher Länge trotzdem
                                    last_text_len = current_len

                        if found_answer:
                            break # Raus aus der Retry-Schleife (attempt)

                except Exception as e:
                    print(f"❌ KI Fehler (Generell): {e}")
            
            print_analysis_summary(decisions)

            # 4. EXECUTION
            if decisions:
                print("\n" + "⚡ EXECUTION PHASE".center(40, "="))
                
                # --- STATUS UPDATE: TRADING ---
                remote_manager.update_status("Trading", f"Verarbeite {len(decisions)} Signale...", balance=current_cash)
                # ------------------------------

                if page.url != config.OON_DEPOT_URL:
                    await page.goto(config.OON_DEPOT_URL)
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(5)

                for trade in decisions:
                    typ = trade.get("aktion")
                    name = trade.get("name")
                    isin = trade.get("isin", "N/A")
                    reason = trade.get("grund", "Kein Grund")
                    
                    # --- STATUS UPDATE: AKTUELLE AKTION ---
                    remote_manager.update_status("Trading", f"{typ}: {name}", balance=current_cash)
                    # --------------------------------------

                    if typ == "BUY":
                        already_ordered = any(o['name'] == name or o['isin'] == isin for o in depot_data['open_orders'] if o['type'] == "BUY")
                        if already_ordered:
                            print(f"⚠️ ÜBERSPRUNGEN: {name} ist bereits in offenen Aufträgen!")
                            continue

                        amt = trade.get("betrag_eur", 0)
                        search_term = isin if isin != "N/A" and isin else name
                        
                        effective_cash = depot_data["cash"] * 0.9 
                        
                        if amt > effective_cash: 
                            amt = effective_cash
                        
                        if amt < 100:
                            continue

                        await execute_buy_order(page, search_term, amt, real_name=name, isin=isin, reason=reason)
                        
                        # Cash lokal anpassen, damit Status stimmt
                        depot_data["cash"] -= amt
                        current_cash = depot_data["cash"]
                        await asyncio.sleep(3)
                    
                    elif typ == "SELL":
                        owned_stock = next((s for s in depot_data["stocks"] if name in s["name"] or s["name"] in name), None)
                        if owned_stock:
                            qty_to_sell = owned_stock["qty"]
                            print(f"🔴 Verkaufe {qty_to_sell} Stück von {name} (Perf: {owned_stock['performance_since_buy']})...")                            
                            await execute_sell_order(page, owned_stock["name"], qty_to_sell, reason=reason)
                            
                            # Cash lokal anpassen (Schätzung)
                            depot_data["cash"] += owned_stock["value_eur"]
                            current_cash = depot_data["cash"] 
                        else:
                            print(f"⚠️ Kann {name} nicht verkaufen: Nicht im Depot gefunden.")

            # --- STATUS UPDATE: FERTIG ---
            remote_manager.update_status("Fertig", "Zyklus beendet.", balance=current_cash)
            # -----------------------------
            
            print("\n✅ Zyklus abgeschlossen.")
            await asyncio.sleep(5)
            
        finally:
            await context.close()