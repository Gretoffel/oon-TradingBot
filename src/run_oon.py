import asyncio
import math
from helping_func import clean_amount

OON_DEPOT_URL = "https://www.oon-boersespiel.at/de/boersespiel.html#/personal/portfolio//detail/overview"

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