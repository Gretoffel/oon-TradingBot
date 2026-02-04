import asyncio
import math
import re
from utils import clean_amount, log_success, add_to_blacklist
from config import OON_DEPOT_URL, MIN_TRADE_VOLUME, MAX_INVEST_PER_STOCK

async def click_cancel_button(page):
    """Hilfsfunktion: Versucht, den Abbrechen-Button zu drücken."""
    try:
        # Versuch 1: Button mit Text "Abbrechen"
        cancel_btn = page.locator("button, a").filter(has_text=re.compile("Abbrechen", re.IGNORECASE))
        if await cancel_btn.count() > 0 and await cancel_btn.first.is_visible():
            print("   ⚠️ Fehler-Behandlung: Drücke 'Abbrechen' Button...")
            await cancel_btn.first.click()
            await asyncio.sleep(1)
            return True
        
        # Versuch 2: X-Icon oder Close-Button
        close_icon = page.locator(".icon-close, .modal-close, button.close")
        if await close_icon.count() > 0 and await close_icon.first.is_visible():
             await close_icon.first.click()
             return True
    except Exception as e:
        print(f"   ⚠️ Konnte nicht abbrechen: {e}")
    return False

# --- BUY ORDER ---
# Rückgabewerte:
#   "SUCCESS" - Kauf erfolgreich
#   "CANCELLED_LIMIT_TOO_LOW" - Website-Limit macht Kauf unrentabel
#   "CANCELLED_OTHER" - Anderer Abbruchgrund (nicht handelbar, etc.)
async def execute_buy_order(page, search_term, budget_eur, real_name="Unbekannt", isin="N/A", reason="-"):
    # 1. SICHERHEITS-CHECK: GEBÜHREN
    if budget_eur < MIN_TRADE_VOLUME:
        print(f"🛑 STOP: Kauf von {real_name} abgebrochen.")
        print(f"   Grund: Budget {budget_eur:.2f} € ist unter Minimum {MIN_TRADE_VOLUME} € (Gebührenfalle!).")
        return "CANCELLED_OTHER"

    # 2. SICHERHEITS-CHECK: MAX INVEST
    if budget_eur > MAX_INVEST_PER_STOCK:
        print(f"   ℹ️ Budget von {budget_eur:.2f} € auf Limit {MAX_INVEST_PER_STOCK} € begrenzt.")
        budget_eur = MAX_INVEST_PER_STOCK

    print(f"\n🛒 KAUF-START: {real_name} (ISIN: {search_term}) | Budget: {budget_eur:.2f} €")
    
    try:
        # A. BUTTON "Neues Wertpapier"
        new_paper_btn = page.locator("button:has-text('Neues Wertpapier')")
        try:
            await page.wait_for_selector("button:has-text('Neues Wertpapier')", timeout=5000)
        except:
            print("❌ Start-Button 'Neues Wertpapier' nicht gefunden.")
            return

        if not await new_paper_btn.first.is_visible():
            await new_paper_btn.first.scroll_into_view_if_needed()
        
        try:
            await new_paper_btn.first.click()
        except:
            print("   ⚠️ Klick blockiert? Versuche Reset via Abbrechen...")
            await click_cancel_button(page)
            await asyncio.sleep(1)
            await new_paper_btn.first.click()

        # B. SUCHE
        search_input_sel = "#live_search"
        try:
            await page.wait_for_selector(search_input_sel, state="visible", timeout=6000)
        except:
            await new_paper_btn.first.click(force=True)
            await page.wait_for_selector(search_input_sel, state="visible", timeout=6000)

        print(f"   -> Suche nach '{search_term}'...")
        await page.click(search_input_sel)
        await page.fill(search_input_sel, "") 
        await page.type(search_input_sel, search_term, delay=100) 
        await asyncio.sleep(2.5)
        
        # Erster Treffer auswählen
        await page.keyboard.press("ArrowDown")
        await asyncio.sleep(0.3)
        await page.keyboard.press("ArrowDown") # Sichergehen dass wir in der Liste sind
        await asyncio.sleep(0.3)
        await page.keyboard.press("Enter")
        
        # C. DATEN EINGABE
        qty_selector = "input[formcontrolname='numOfShares']"
        try:
            await page.wait_for_selector(qty_selector, state="visible", timeout=8000)
            await asyncio.sleep(1.5) 

            modal_text = await page.locator("ngb-modal-window").inner_text()

            # Check 1: "Kann nicht gehandelt werden" (Fehlermeldung)
            if "nicht gehandelt werden" in modal_text or "not tradeable" in modal_text.lower():
                print("⛔ Aktie ist gesperrt/nicht handelbar (Blacklist!).")
                add_to_blacklist(search_term, f"Kann nicht gehandelt werden ({real_name})")
                await click_cancel_button(page)
                return "CANCELLED_OTHER"

            # Check 2: Limit ist "-"
            if re.search(r'maximal\s*[:.]?\s*-', modal_text, re.IGNORECASE):
                print("⛔ Aktie hat Limit '-' (Blacklist!).")
                add_to_blacklist(search_term, f"Limit ist - ({real_name})")
                await click_cancel_button(page)
                return "CANCELLED_OTHER"

            # Check 3: Limit ist 0
            limit_match_zero = re.search(r'maximal\s*[:.]?\s*0\b', modal_text, re.IGNORECASE)
            if limit_match_zero:
                print("⛔ Aktie hat Limit 0 (Blacklist!).")
                add_to_blacklist(search_term, f"Limit ist 0 ({real_name})")
                await click_cancel_button(page)
                return "CANCELLED_OTHER"

            # Preis ermitteln für Mengenberechnung
            price_selector = "input[formcontrolname='price']"
            price_str = await page.input_value(price_selector)
            current_price = clean_amount(price_str)
            
            qty = 0
            if current_price > 0:
                qty = math.floor(budget_eur / current_price)
            else:
                qty = 0 

            # Limit vom Spiel beachten (z.B. max 20% Regel)
            limit_match = re.search(r'maximal\s*[:.]?\s*(\d+)', modal_text, re.IGNORECASE)
            
            website_limit_applied = False
            if limit_match:
                max_limit = int(limit_match.group(1))
                # 0 wurde schon oben abgefangen
                if qty > max_limit:
                    print(f"   ⚠️ Website-Limit greift: Berechnete Menge {qty} → Website-Maximum {max_limit}")
                    qty = max_limit
                    website_limit_applied = True

            if qty < 1:
                print(f"⚠️ Berechnete Menge ist 0 (Preis: {current_price}, Budget: {budget_eur}).")
                await click_cancel_button(page)
                return "CANCELLED_OTHER"
            
            # NEU: Prüfen ob der Kauf mit Website-Limit noch rentabel ist
            if website_limit_applied:
                actual_invest_amount = qty * current_price
                if actual_invest_amount < MIN_TRADE_VOLUME:
                    print(f"❌ ABBRUCH: Website-Limit macht Kauf unrentabel!")
                    print(f"   Kaufbetrag wäre nur {actual_invest_amount:.2f} € (Minimum: {MIN_TRADE_VOLUME} €)")
                    print(f"   → Breche ab und versuche nächstbessere Aktie...")
                    await click_cancel_button(page)
                    return "CANCELLED_LIMIT_TOO_LOW"
                
            print(f"   -> Kaufe Menge: {qty} zu je {current_price:.2f} €")

            # Menge eintragen
            await page.fill(qty_selector, str(int(qty)))
            await asyncio.sleep(1)
            
            # Kaufen Button
            buy_btn = page.locator("button[type='submit']").filter(has_text="Kaufen")
            if await buy_btn.count() > 0:
                await buy_btn.first.click()
            else:
                await page.locator("button:has-text('Kaufen')").first.click()
            
            # D. BESTÄTIGUNG
            await asyncio.sleep(2)
            pre_confirm = page.locator("button:has-text('Kostenpflichtig'), button:has-text('Order ausführen')")
            if await pre_confirm.count() > 0 and await pre_confirm.first.is_visible():
                 print("   -> Bestätige Kosten...")
                 await pre_confirm.first.click()
                 await asyncio.sleep(2)

            # E. ERFOLG
            success_btn = page.locator("button:has-text('Zum Spieldepot'), button:has-text('Zum Musterdepot')")
            try:
                await success_btn.wait_for(state="visible", timeout=10000)
                print("✅ KAUF ERFOLGREICH.")
                
                # Loggen
                log_success("BUY", real_name, isin, qty, current_price, reason)
                
                await success_btn.first.click()
                await asyncio.sleep(3)
                return "SUCCESS"
            except:
                print("⚠️ Kein Erfolgs-Button erschienen. Navigiere manuell.")
                await page.goto(OON_DEPOT_URL)
                return "SUCCESS"  # Vermutlich trotzdem erfolgreich

        except Exception as e:
            err_msg = str(e)
            print(f"❌ Fehler während Eingabe im Modal: {err_msg}")
            
            # Check for hidden input timeout (Blacklist candidate)
            # "waiting for locator(...) to be visible" -> Timeout
            if "Timeout" in err_msg and "numOfShares" in err_msg:
                print("⛔ Input-Feld Timeout -> Vermutlich gesperrt/hidden (Blacklist).")
                add_to_blacklist(search_term, f"Input Timeout / Not Tradeable ({real_name})")

            await click_cancel_button(page)
            return "CANCELLED_OTHER"

    except Exception as e:
        print(f"❌ ERROR BUY {real_name}: {e}")
        await click_cancel_button(page)
        return "CANCELLED_OTHER"

# --- SELL ORDER ---
async def execute_sell_order(page, stock_name, quantity, reason="-"):
    print(f"\n📉 VERKAUF-START: {stock_name} (Menge: {quantity})")
    
    try:
        # Zeile suchen
        row = page.locator("tr[role='row']").filter(has_text=stock_name).first
        if await row.count() == 0:
            print(f"❌ Aktie '{stock_name}' nicht im Depot gefunden!")
            return

        print("   -> Zeile gefunden. Öffne Menü...")
        menu_btn = row.locator("button.dropdown-toggle")
        
        # Scrollen falls nötig
        if not await menu_btn.is_visible():
             await menu_btn.scroll_into_view_if_needed()
             
        await menu_btn.click()
        await asyncio.sleep(1)

        # "Verkaufen" Option wählen
        sell_option = page.locator("a").filter(has_text="Aus Spieldepot verkaufen")
        if await sell_option.count() == 0:
             print("❌ 'Verkaufen'-Option nicht sichtbar.")
             # Menü schließen versuch
             try: await menu_btn.click()
             except: pass
             return
        
        await sell_option.first.click()
        
        # Popup Handling
        print("   -> Warte auf Popup...")
        qty_input_sel = "input[formcontrolname='numOfShares']"
        try:
            await page.wait_for_selector(qty_input_sel, state="visible", timeout=6000)
        except:
            print("❌ Popup nicht aufgegangen.")
            return
            
        await asyncio.sleep(1)
        await page.fill(qty_input_sel, str(int(quantity)))
        await asyncio.sleep(1)

        submit_btn = page.locator("button[type='submit']").filter(has_text="Verkaufen")
        if await submit_btn.count() > 0:
            await submit_btn.first.click()
        else:
            await page.locator("button:has-text('Verkaufen')").click()

        # Bestätigung
        await asyncio.sleep(2)
        pre_confirm = page.locator("button:has-text('Kostenpflichtig'), button:has-text('Order ausführen')")
        if await pre_confirm.count() > 0 and await pre_confirm.first.is_visible():
             print("   -> Bestätige Ausführung...")
             await pre_confirm.first.click()
             await asyncio.sleep(2)

        # Erfolg
        success_btn = page.locator("button:has-text('Zum Spieldepot'), button:has-text('Zum Musterdepot')")
        try:
            await success_btn.wait_for(state="visible", timeout=10000)
            print("✅ VERKAUF ERFOLGREICH.")
            
            log_success("SELL", stock_name, "N/A", quantity, 0, reason)

            await success_btn.first.click()
        except:
            print("⚠️ Kein Erfolgs-Button. Navigiere manuell.")
            await page.goto(OON_DEPOT_URL)

        await asyncio.sleep(3)

    except Exception as e:
        print(f"❌ ERROR SELL {stock_name}: {e}")
        await click_cancel_button(page)