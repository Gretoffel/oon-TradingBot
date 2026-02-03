import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright
import os

import config
import remote_manager
from utils import clean_amount, extract_json_list, print_analysis_summary, get_todays_log_content
from actions import execute_buy_order, execute_sell_order

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

async def run_bot_cycle():
    """Führt einen einzelnen Zyklus des Bots aus."""
    print("\n" + "="*40)
    print("🤖 TRADING BOT ZYKLUS STARTET")
    
    remote_manager.update_status("Start", "Initialisiere Browser...", balance=0.0)

    if config.TEST_MODE:
        print("⚠️  ACHTUNG: TEST-MODUS AKTIV (Keine KI)")
    print("="*40)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=config.USER_DATA_DIR,
            channel="chrome",  # <--- FORCE REAL CHROME
            headless=False, 
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu" 
            ]
        )
        context.set_default_timeout(15000)
        
        current_cash = 0.0

        try:
            page = context.pages[0] if context.pages else await context.new_page()
            
            # --- HIER SIND DIE NEUEN LISTENERS ---
            # Damit siehst du im Terminal, was der Browser denkt, kurz bevor er abstürzt.
            print("   🕵️  Aktiviere Browser-Diagnose...")
            
            # 1. Zeige Fehler aus der Browser-Konsole (rote Fehlermeldungen in F12)
            page.on("console", lambda msg: print(f"   [BROWSER CONSOLE] {msg.type}: {msg.text}") if msg.type == "error" else None)
            
            # 2. Zeige JavaScript Fehler auf der Seite
            page.on("pageerror", lambda exc: print(f"   [BROWSER PAGE ERROR] {exc}"))
            
            # 3. Melde sofort, wenn der Tab stirbt ("Aw Snap")
            page.on("crash", lambda: print("\n   🔴🔴🔴 ALARM: BROWSER TAB IST ABGESTÜRZT! (CRASH EVENT) 🔴🔴🔴\n"))

            # 1. LOGIN
            remote_manager.update_status("Login", "Logge bei OON ein...")
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
            remote_manager.update_status("Scan", "Lese Depot und Cash aus...")
            print("📊 Lese Depot-Daten...")
            
            await page.goto(config.OON_DEPOT_URL)
            try: await page.wait_for_selector("a.tt-link", timeout=15000)
            except: pass

            depot_data = { "cash": 0.0, "stocks": [], "open_orders": [] }

            # A) Cash
            try:
                spans = await page.locator("span[data-currency='EUR']").all()
                for span in spans:
                    if "Geldkonto" in await span.locator("xpath=..").inner_text():
                        depot_data["cash"] = clean_amount(await span.inner_text())
            except: pass
            
            current_cash = depot_data["cash"]
            print(f"💰 Verfügbares Cash (laut Anzeige): {current_cash} €")
            remote_manager.update_status("Scan", "Analysiere Positionen...", balance=current_cash)

            # B) Bestand
            try:
                rows = await page.locator("tbody tr[role='row']").all()
                for row in rows:
                    try:
                        row_text = await row.inner_text()
                        if "Warten auf Ausführung" in row_text or "Bestens" in row_text or "Limit" in row_text:
                            continue 
                        name_el = row.locator("a.tt-link").first
                        if await name_el.count() > 0: name = await name_el.inner_text()
                        else:
                            name_items = await row.locator("strong").all()
                            if name_items: name = await name_items[0].inner_text()
                            else: continue
                        qty_el = row.locator("[data-currency='STK']").first
                        qty = clean_amount(await qty_el.inner_text()) if await qty_el.count() > 0 else 0
                        val_el = row.locator("[data-currency='EUR']").last
                        val_eur = clean_amount(await val_el.inner_text()) if await val_el.count() > 0 else 0
                        
                        perf_text = "N/A"
                        try:
                            cells = await row.locator("td").all()
                            for cell in cells:
                                if "%" in await cell.inner_text():
                                    perf_text = (await cell.inner_text()).replace("\n", "").strip()
                                    break
                        except: pass

                        if qty > 0:
                            stock_entry = { "name": name.strip(), "qty": qty, "value_eur": val_eur, "performance_since_buy": perf_text }
                            depot_data["stocks"].append(stock_entry)
                            print(f"   ✅ Besitz: {stock_entry['name']} | {stock_entry['qty']} Stk. | Perf: {stock_entry['performance_since_buy']}")
                    except: continue
            except Exception as e:
                print(f"⚠️ Scan Fehler (Bestand): {e}")

            # C) Offene Aufträge
            try:
                open_order_rows = await page.locator("xpath=//h3[contains(text(), 'Offene Aufträge')]/following::tt-table[1]//tbody//tr").all()
                for row in open_order_rows:
                    try:
                        full_text = await row.inner_text()
                        if not full_text.strip(): continue
                        name = await row.locator("td").nth(0).locator("strong").inner_text()
                        isin_match = re.search(r'\b([A-Z]{2}[A-Z0-9]{9}\d)\b', full_text)
                        isin = isin_match.group(1) if isin_match else "Unbekannt"
                        type_text = await row.locator("td").nth(1).inner_text()
                        order_type = "BUY" if "Kauf" in type_text else "SELL" if "Verkauf" in type_text else "UNKNOWN"
                        qty = clean_amount(await row.locator("td").nth(2).inner_text())
                        status_text = await row.locator("td").nth(4).inner_text()
                        entry = { "name": name.strip(), "isin": isin, "type": order_type, "qty": qty, "status": status_text.strip() }
                        depot_data["open_orders"].append(entry)
                        print(f"   ⏳ Offener Auftrag: {entry['type']} {entry['qty']}x {entry['name']}")
                    except: continue
            except Exception as e:
                print(f"⚠️ Scan Fehler (Offene Aufträge): {e}")


            # 3. ENTSCHEIDUNG (KI ODER TEST)
            decisions = []
            
            # --- UPDATE: Send gathered data to dashboard ---
            remote_manager.update_status(
                "KI", 
                "Frage KI nach Strategie...", 
                balance=current_cash,
                portfolio=depot_data["stocks"],
                open_orders=depot_data["open_orders"]
            )
            # -----------------------------------------------

            if config.TEST_MODE:
                print("\n🧪 TEST-MODUS: Überspringe KI. Lade Test-Daten...")
                decisions = config.TEST_ORDERS
            else:
                print("\n🧠 Frage KI (Google Search)...")
                todays_logs = get_todays_log_content()
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Strategie-Datei lesen
                # FIX: Access PROJECT_ROOT via config module
                strategy_file = os.path.join(config.PROJECT_ROOT, "src", "strategy.txt")
                user_strategy = ""
                if os.path.exists(strategy_file):
                    try:
                        with open(strategy_file, "r", encoding="utf-8") as f:
                            content = f.read().strip()
                            if content:
                                user_strategy = f"\n\nUSER INSTRUCTIONS (VERY IMPORTANT):\n{content}\n"
                                print(f"   📜 Strategie-Update geladen: {content[:50]}...")
                    except Exception as e:
                        print(f"⚠️ Konnte Strategie nicht lesen: {e}")

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
                {user_strategy}
                AUFGABE:
                1. Analysiere mein Depot und offene Aufträge.
                2. Recherchiere ausführlich aktuelle News zu meinen besessenen Aktien. Soll ich sie HALTEN oder VERKAUFEN ("SELL")?
                3. Recherchiere ausführlich nach NEUEN Aktien mit hohem Potenzial ("BUY").
                4. Du musst nicht immer alles machen, wenn es nicht sicher vorteilhaft ist, kannst du auch buy oder sell aktionen weglassen und nur eins davon machen oder wenn alles gehalten werden soll, eine leere menge zurückgeben "[]"
                5. Du wirst in etwa 10-20 minuten erneut die chance haben die selbe Aufgabe mit dem neuen depot zu machen und so weiter, beachte das.
                6. Du musst nicht das ganze Budget investieren, dazu ist später immer noch Zeit.
                
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

                # --- KI INTERACTION LOOP ---
                max_ai_retries = 3
                ai_success = False

                for attempt in range(max_ai_retries):
                    print(f"   🔄 KI-Zyklus Versuch {attempt+1}/{max_ai_retries}...")
                    
                    try:
                        if page.is_closed():
                            print("   ♻️ Seite war geschlossen. Erstelle neu...")
                            page = await context.new_page()

                        if page.url != config.AI_STUDIO_URL:
                            await page.goto(config.AI_STUDIO_URL)
                            await asyncio.sleep(4)
                        
                        if await check_soft_crash(page):
                            print("   ⚠️ Crash beim Start erkannt -> Neustart des Versuchs.")
                            continue

                        # Check ob wir auf der Login-Seite sind
                        if "accounts.google.com" in page.url or "signin" in page.url:
                            print("\n🔑 Google Login erforderlich. Bitte manuell einloggen!")
                            print("   ⏳ Der Bot wartet nun BIS ZU 1 STUNDE, bis die Anmeldung abgeschlossen ist...")
                            # 59 Minuten und 59 Sekunden Timeout (3599000 ms)
                            # wait_for_selector kehrt zurück, sobald das Element da ist (Login fertig)
                            await page.wait_for_selector("div[contenteditable='true'], textarea", state="visible", timeout=3599000)
                            print("   ✅ Anmeldung erkannt! Fahre fort...")
                        else:
                            # Normaler kurzer Wait
                            await page.wait_for_selector("div[contenteditable='true'], textarea", state="visible", timeout=8000)
                        await page.fill("div[contenteditable='true'], textarea", prompt)
                        
                        run_btn = page.locator(".run-button-label", has_text="Run")
                        if await run_btn.count() > 0: await run_btn.click()
                        else: await page.keyboard.press("Control+Enter")

                        print("⏳ Recherche läuft...")

                        try:
                            chat_container = page.locator(".chat-session-content").last
                            if await chat_container.count() > 0:
                                await chat_container.hover()
                                await asyncio.sleep(0.5)
                                await page.mouse.wheel(0, 15000)
                                await chat_container.evaluate("el => el.scrollTop = el.scrollHeight")
                        except Exception as s_err:
                            print(f"   ⚠️ Scroll-Warnung: {s_err}")

                        found_answer = False
                        last_text_len = 0 
                        
                        for poll_tick in range(15): 
                            await asyncio.sleep(4) 
                            
                            if await check_soft_crash(page):
                                print("⚠️ Soft Crash beim Warten. Breche Polling ab und versuche neu...")
                                break 

                            error_locator = page.locator(".model-error")
                            if await error_locator.count() > 0 and await error_locator.last.is_visible():
                                print("\n⚠️ Google AI Error. Versuche Rerun...")
                                try:
                                    await error_locator.last.hover(force=True)
                                    rerun_btns = page.locator("button[aria-label='Rerun this turn']")
                                    if await rerun_btns.count() > 0:
                                        await rerun_btns.last.click()
                                        continue
                                    else:
                                        await page.reload()
                                        break 
                                except: 
                                    break 

                            ans_locator = page.locator('div[data-turn-role="Model"]').last
                            if await ans_locator.count() > 0:
                                current_text = await ans_locator.inner_text()
                                
                                if len(current_text) >= 2 and "]" in current_text:
                                    if len(current_text) == last_text_len:
                                        # --- NEW: PRINT RAW AI OUTPUT ---
                                        print("\n" + "-"*30)
                                        print("📝 EXACT AI OUTPUT RECEIVED:")
                                        print("-" * 30)
                                        print(current_text)
                                        print("-" * 30 + "\n")
                                        # --------------------------------
                                        
                                        parsed_json = extract_json_list(current_text)
                                        if parsed_json is not None:
                                            decisions = parsed_json
                                            found_answer = True
                                            ai_success = True
                                            print("   ✅ Antwort empfangen und validiert.")
                                            break 
                                    else: last_text_len = len(current_text)
                                else: last_text_len = len(current_text)
                        
                        if found_answer:
                            break 

                    except Exception as e:
                        error_msg = str(e).lower()
                        print(f"❌ Fehler im KI-Zyklus: {e}")
                        
                        if "crashed" in error_msg or "closed" in error_msg or "target" in error_msg:
                            print("\n🛑 FATALER BROWSER FEHLER (Target crashed).")
                            print("♻️  ERSTELLE NEUEN TAB UND STARTE NEU...\n")
                            try:
                                await page.close() 
                            except: pass
                            
                            page = await context.new_page()
                            await asyncio.sleep(2)
                        else:
                            await asyncio.sleep(5)
                
                if not ai_success:
                    print("❌ KI hat keine gültige Antwort geliefert.")
                    return 

            print_analysis_summary(decisions)

            # 4. EXECUTION
            if decisions:
                print("\n" + "⚡ EXECUTION PHASE".center(40, "="))
                remote_manager.update_status("Trading", f"Verarbeite {len(decisions)} Signale...", balance=current_cash)

                if page.is_closed(): page = await context.new_page()

                if page.url != config.OON_DEPOT_URL:
                    await page.goto(config.OON_DEPOT_URL)
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(5)

                for trade in decisions:
                    typ = trade.get("aktion")
                    name = trade.get("name")
                    isin = trade.get("isin", "N/A")
                    reason = trade.get("grund", "Kein Grund")
                    
                    remote_manager.update_status("Trading", f"{typ}: {name}", balance=current_cash)

                    if typ == "BUY":
                        already_ordered = any(o['name'] == name or o['isin'] == isin for o in depot_data['open_orders'] if o['type'] == "BUY")
                        if already_ordered:
                            print(f"⚠️ ÜBERSPRUNGEN: {name} ist bereits in offenen Aufträgen!")
                            continue
                        amt = trade.get("betrag_eur", 0)
                        search_term = isin if isin != "N/A" and isin else name
                        effective_cash = depot_data["cash"] * 0.9 
                        if amt > effective_cash: amt = effective_cash
                        if amt < 100: continue

                        await execute_buy_order(page, search_term, amt, real_name=name, isin=isin, reason=reason)
                        depot_data["cash"] -= amt
                        current_cash = depot_data["cash"]
                        await asyncio.sleep(3)
                    
                    elif typ == "SELL":
                        owned_stock = next((s for s in depot_data["stocks"] if name in s["name"] or s["name"] in name), None)
                        if owned_stock:
                            qty_to_sell = owned_stock["qty"]
                            print(f"🔴 Verkaufe {qty_to_sell} Stück von {name}...")                            
                            await execute_sell_order(page, owned_stock["name"], qty_to_sell, reason=reason)
                            depot_data["cash"] += owned_stock["value_eur"]
                            current_cash = depot_data["cash"] 
                        else:
                            print(f"⚠️ Kann {name} nicht verkaufen: Nicht im Depot gefunden.")

            remote_manager.update_status("Fertig", "Zyklus beendet.", balance=current_cash)
            print("\n✅ Zyklus abgeschlossen.")
            await asyncio.sleep(5)
            
        finally:
            await context.close()