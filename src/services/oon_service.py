import asyncio
import re
from core import config
from core.utils import clean_amount
from core import remote_manager
from services import market_data

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
        # Wir suchen alle Zeilen in der Tabelle
        rows = await page.locator("tbody tr[role='row']").all()
        
        for row in rows:
            try:
                row_text = await row.inner_text()
                
                # Filter: Überspringe Zeilen, die eigentlich offene Orders sind (manchmal in der gleichen Tabelle)
                if "Warten auf Ausführung" in row_text or "Bestens" in row_text or "Limit" in row_text:
                    continue 

                # 1. NAME und ISIN finden
                name_el = row.locator("a.tt-link").first
                name = "Unbekannt"
                isin = "N/A"

                if await name_el.count() > 0:
                    name = await name_el.inner_text()
                else:
                    # Fallback für den Namen
                    name_items = await row.locator("strong").all()
                    if name_items: 
                        name = await name_items[0].inner_text()

                # --- 1b. ISIN EXTRAKTION (Aggressiv) ---
                # A) In allen Links der Zeile suchen (HREFs)
                all_links = await row.locator("a").all()
                for link in all_links:
                    href = await link.get_attribute("href")
                    if href:
                        match = re.search(r'([A-Z]{2}[A-Z0-9]{9}\d)', href)
                        if match:
                            isin = match.group(1)
                            break
                
                # B) Im text_content suchen (vielleicht schon im DOM, aber hidden)
                if isin == "N/A":
                    tc = await row.text_content()
                    match = re.search(r'([A-Z]{2}[A-Z0-9]{9}\d)', tc)
                    if match:
                        isin = match.group(1)

                # C) Pfeil klicken (Detail-Ansicht), falls immer noch nix
                if isin == "N/A":
                    # Suche den Toggle-Button (Pfeil)
                    toggle = row.locator("button.toggle-btn").first
                    if await toggle.count() > 0:
                        try:
                            await toggle.click()
                            await asyncio.sleep(0.5) # Animation abwarten
                            tc_after = await row.text_content()
                            match = re.search(r'([A-Z]{2}[A-Z0-9]{9}\d)', tc_after)
                            if match:
                                isin = match.group(1)
                        except: pass

                # --- NEW: ISIN RESOLUTION FALLBACK ---
                if isin == "N/A" or not isin:
                    from services.market_data import TICKER_MAPPING, get_isin_by_name
                    # Try fuzzy matching by name
                    resolved_isin = get_isin_by_name(name)
                    if resolved_isin:
                        isin = resolved_isin
                    else:
                        # Try exact ticker match if name is just a ticker
                        for t_isin, t_ticker in TICKER_MAPPING.items():
                            if t_ticker.lower() in name.lower() or name.lower() in t_ticker.lower():
                                isin = t_isin
                                break

                # 2. MENGE (Stückzahl)
                qty_el = row.locator("[data-currency='STK']").first
                qty = clean_amount(await qty_el.inner_text()) if await qty_el.count() > 0 else 0
                
                # 3. WERT (in EUR)
                val_el = row.locator("[data-currency='EUR']").last
                val_eur = clean_amount(await val_el.inner_text()) if await val_el.count() > 0 else 0
                
                # 4. PERFORMANCE (%)
                perf_text = "N/A"
                try:
                    # Suche nach der Zelle mit % Zeichen
                    cells = await row.locator("td").all()
                    for cell in cells:
                        txt = await cell.inner_text()
                        if "%" in txt and ("+" in txt or "-" in txt):
                            perf_text = txt.replace("\n", "").strip()
                            break
                except: pass

                # Nur hinzufügen, wenn wir wirklich Aktien besitzen
                if qty > 0:
                    stock_entry = { 
                        "name": name.strip(), 
                        "isin": isin, 
                        "qty": qty, 
                        "value_eur": val_eur, 
                        "performance_since_buy": perf_text 
                    }
                    depot_data["stocks"].append(stock_entry)
                    print(f"   ✅ Besitz: {stock_entry['name']:<20} | ISIN: {stock_entry['isin']} | {stock_entry['qty']} Stk. | Perf: {stock_entry['performance_since_buy']}")
            
            except Exception as e:
                # Einzelne Zeilenfehler fangen, damit der Scan nicht abbricht
                # print(f"Debug Row Error: {e}") 
                continue

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
                
                # Betrag (EUR) für offene Aufträge erfassen
                betrag_eur = 0.0
                try:
                    # Suche nach EUR-Betrag in den Zellen
                    cells = await row.locator("td").all()
                    for cell in cells:
                        cell_text = await cell.inner_text()
                        # Suche nach EUR-Beträgen (z.B. "1.000,00 €" oder "500,00")
                        if "€" in cell_text or "EUR" in cell_text:
                            betrag_eur = clean_amount(cell_text)
                            if betrag_eur > 0:
                                break
                except: pass
                
                entry = { 
                    "name": name.strip(), 
                    "isin": isin, 
                    "type": order_type, 
                    "qty": qty, 
                    "betrag_eur": betrag_eur,
                    "status": status_text.strip() 
                }
                depot_data["open_orders"].append(entry)
                print(f"   ⏳ Offener Auftrag: {entry['type']} {entry['qty']}x {entry['name']} | Betrag: {betrag_eur:.2f} €")
            except: continue
    except Exception as e:
        print(f"⚠️ Scan Fehler (Offene Aufträge): {e}")

    return depot_data
