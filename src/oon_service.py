import asyncio
import re
import config
from utils import clean_amount
import remote_manager

async def login(page):
    """Führt den Login bei OON durch."""
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

async def scan_depot(page):
    """Liest Cash, Bestand und offene Aufträge aus."""
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

    return depot_data
