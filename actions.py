import asyncio
import math
import re
from utils import clean_amount, log_success
from config import OON_DEPOT_URL

async def click_cancel_button(page):
    """Hilfsfunktion: Versucht, den Abbrechen-Button zu drücken."""
    try:
        cancel_btn = page.locator("button, a").filter(has_text=re.compile("Abbrechen", re.IGNORECASE))
        if await cancel_btn.count() > 0 and await cancel_btn.first.is_visible():
            print("   ⚠️ Fehler-Behandlung: Drücke 'Abbrechen' Button...")
            await cancel_btn.first.click()
            await asyncio.sleep(1)
            return True
        
        close_icon = page.locator(".icon-close, .modal-close, button.close")
        if await close_icon.count() > 0 and await close_icon.first.is_visible():
             await close_icon.first.click()
             return True
    except Exception as e:
        print(f"   ⚠️ Konnte nicht abbrechen: {e}")
    return False

# --- BUY ORDER ---
# Parameter 'isin' und 'reason' hinzugefügt für das Logging
async def execute_buy_order(page, search_term, budget_eur, real_name="Unbekannt", isin="N/A", reason="-"):
    print(f"\n🛒 KAUF-START: {real_name} (Budget: {budget_eur} €)")
    
    try:
        # 1. BUTTON "Neues Wertpapier"
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

        # 2. SUCHE
        search_input_sel = "#live_search"
        try:
            await page.wait_for_selector(search_input_sel, state="visible", timeout=6000)
        except:
            await new_paper_btn.first.click(force=True)
            await page.wait_for_selector(search_input_sel, state="visible", timeout=6000)

        print(f"   -> Tippe '{search_term}'...")
        await page.click(search_input_sel)
        await page.fill(search_input_sel, "") 
        await page.type(search_input_sel, search_term, delay=150) 
        await asyncio.sleep(2.5)
        
        await page.keyboard.press("ArrowDown")
        await asyncio.sleep(0.3)
        await page.keyboard.press("ArrowDown")
        await asyncio.sleep(0.3)
        await page.keyboard.press("Enter")
        
        # 3. DATEN
        qty_selector = "input[formcontrolname='numOfShares']"
        try:
            await page.wait_for_selector(qty_selector, state="visible", timeout=8000)
            await asyncio.sleep(2.0) 

            modal_text = await page.locator("ngb-modal-window").inner_text()

            # CHECK 1: Handelbar?
            if re.search(r'maximal\s*[:.]?\s*-', modal_text, re.IGNORECASE):
                print("❌ Aktie ist NICHT handelbar (Limit: -).")
                await click_cancel_button(page)
                return

            # CHECK 2: Preis ermitteln
            price_selector = "input[formcontrolname='price']"
            price_str = await page.input_value(price_selector)
            current_price = clean_amount(price_str)
            
            if current_price > 0:
                qty = math.floor(budget_eur / current_price)
            else:
                qty = 1 

            # CHECK 3: Limit
            limit_match = re.search(r'maximal\s*[:.]?\s*(\d+)', modal_text, re.IGNORECASE)
            max_limit = float('inf')
            
            if limit_match:
                max_limit = int(limit_match.group(1))
                print(f"   ✅ Limit vom Spiel erkannt: {max_limit} Stück")
                
                if max_limit == 0:
                    print("❌ Limit ist 0.")
                    await click_cancel_button(page)
                    return

                if qty > max_limit:
                    qty = max_limit
                if qty >= max_limit * 0.9:
                    qty = max_limit
            else:
                print("   ℹ️ Kein Limit gefunden. Nutze Budget-Berechnung.")

            if qty < 1:
                print(f"⚠️ Berechnete Menge ist 0.")
                await click_cancel_button(page)
                return
                
            print(f"   -> Kaufe Menge: {qty}")

            # 4. ORDER
            await page.fill(qty_selector, str(int(qty)))
            await asyncio.sleep(1)
            
            buy_btn = page.locator("button[type='submit']").filter(has_text="Kaufen")
            if await buy_btn.is_disabled():
                print("❌ Kaufen-Button ist inaktiv!")
                await click_cancel_button(page)
                return

            if await buy_btn.count() > 0:
                await buy_btn.first.click()
            else:
                await page.locator("button:has-text('Kaufen')").first.click()
            
            # 5. CONFIRM
            await asyncio.sleep(2)
            pre_confirm = page.locator("button:has-text('Kostenpflichtig'), button:has-text('Order ausführen')")
            if await pre_confirm.count() > 0 and await pre_confirm.first.is_visible():
                 print("   -> Bestätige Kosten...")
                 await pre_confirm.first.click()
                 await asyncio.sleep(2)

            # 6. SUCCESS
            success_btn = page.locator("button:has-text('Zum Spieldepot'), button:has-text('Zum Musterdepot')")
            try:
                await success_btn.wait_for(state="visible", timeout=10000)
                print("✅ KAUF ERFOLGREICH.")
                
                # --- LOGGING ---
                log_success("BUY", real_name, isin, qty, current_price, reason)
                # ---------------
                
                await success_btn.first.click()
            except:
                print("⚠️ Kein Erfolgs-Button erschienen.")
                await page.goto(OON_DEPOT_URL)

            await asyncio.sleep(3)

        except Exception as e:
            print(f"❌ Fehler während Eingabe: {e}")
            await click_cancel_button(page)
            return

    except Exception as e:
        print(f"❌ ERROR BUY {real_name}: {e}")
        await click_cancel_button(page)

# --- SELL ORDER ---
# Parameter 'reason' hinzugefügt für das Logging
async def execute_sell_order(page, stock_name, quantity, reason="-"):
    print(f"\n📉 VERKAUF-START: {stock_name} (Menge: {quantity})")
    
    try:
        row = page.locator("tr[role='row']").filter(has_text=stock_name).first
        if await row.count() == 0:
            print(f"❌ Aktie '{stock_name}' nicht gefunden!")
            return

        print("   -> Zeile gefunden. Öffne Menü...")
        menu_btn = row.locator("button.dropdown-toggle")
        await menu_btn.scroll_into_view_if_needed()
        await menu_btn.click()
        await asyncio.sleep(1)

        sell_option = page.locator("a").filter(has_text="Aus Spieldepot verkaufen")
        if await sell_option.count() == 0:
             print("❌ Option nicht sichtbar.")
             try: await menu_btn.click()
             except: pass
             return
        
        await sell_option.first.click()
        
        print("   -> Warte auf Popup...")
        qty_input_sel = "input[formcontrolname='numOfShares']"
        try:
            await page.wait_for_selector(qty_input_sel, state="visible", timeout=5000)
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

        await asyncio.sleep(2)
        pre_confirm = page.locator("button:has-text('Kostenpflichtig'), button:has-text('Order ausführen')")
        if await pre_confirm.count() > 0 and await pre_confirm.first.is_visible():
             print("   -> Bestätige Ausführung...")
             await pre_confirm.first.click()
             await asyncio.sleep(2)

        success_btn = page.locator("button:has-text('Zum Spieldepot'), button:has-text('Zum Musterdepot')")
        try:
            await success_btn.wait_for(state="visible", timeout=10000)
            print("✅ VERKAUF ERFOLGREICH.")
            
            # --- LOGGING ---
            # ISIN haben wir beim Verkauf evtl. nicht parat, daher "N/A" oder man müsste sie vorher scrapen
            log_success("SELL", stock_name, "N/A", quantity, 0, reason)
            # ---------------

            await success_btn.first.click()
        except:
            print("⚠️ Kein Erfolgs-Button. Navigiere manuell.")
            await page.goto(OON_DEPOT_URL)

        await asyncio.sleep(3)

    except Exception as e:
        print(f"❌ ERROR SELL {stock_name}: {e}")
        await click_cancel_button(page)