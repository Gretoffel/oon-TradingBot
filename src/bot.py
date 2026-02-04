import asyncio
from playwright.async_api import async_playwright
import config
import remote_manager
from utils import print_analysis_summary
from actions import execute_buy_order, execute_sell_order
from browser_utils import create_browser_context
from oon_service import login, scan_depot
from algo_service import calculate_algo_decisions

async def run_bot_cycle():
    print("\n" + "="*40)
    print("⚡ DAY TRADING BOT ZYKLUS STARTET")
    remote_manager.update_status("Start", "Initialisiere...", balance=0.0)
    print("="*40)

    async with async_playwright() as p:
        context = await create_browser_context(p)
        
        try:
            page = context.pages[0] if context.pages else await context.new_page()

            # 1. LOGIN
            await login(page)

            # 2. SCANNING
            depot_data = await scan_depot(page)
            current_cash = depot_data["cash"]
            
            # Status Update for Dashboard
            remote_manager.update_status(
                "Analyse", 
                "Führe Portfolio-Strategie aus...", 
                balance=current_cash,
                portfolio=depot_data["stocks"],
                open_orders=depot_data["open_orders"]
            )

            # 3. STRATEGY CALCULATION
            # This now returns a list of multiple diversified trades
            decisions = calculate_algo_decisions(depot_data)
            
            # Show what we plan to do in the console
            print_analysis_summary(decisions)

            # 4. EXECUTION LOOP
            if decisions:
                print(f"🚀 STARTE AUSFÜHRUNG VON {len(decisions)} AKTIONEN...")
                
                if page.is_closed(): page = await context.new_page()
                if page.url != config.OON_DEPOT_URL:
                    await page.goto(config.OON_DEPOT_URL)
                    await asyncio.sleep(2)

                # Trennen in SELL und BUY Entscheidungen
                sell_decisions = [d for d in decisions if d.get("aktion") == "SELL"]
                buy_decisions = [d for d in decisions if d.get("aktion") == "BUY"]
                
                # SELL-Entscheidungen zuerst ausführen (um Cash freizumachen)
                for trade in sell_decisions:
                    name = trade.get("name")
                    reason = trade.get("grund", "")
                    
                    remote_manager.update_status("Trading", f"SELL: {name}", balance=current_cash)
                    
                    owned = next((s for s in depot_data["stocks"] if s["name"] in name or name in s["name"]), None)
                    if owned:
                        await execute_sell_order(page, owned["name"], owned["qty"], reason=reason)
                        await asyncio.sleep(3)
                    else:
                        print(f"⚠️ Verkaufs-Signal für {name}, aber Aktie nicht im Bestand gefunden.")
                
                # BUY-Entscheidungen: Bei Limit-Abbruch nächstbessere probieren
                buy_index = 0
                while buy_index < len(buy_decisions) and current_cash >= config.MIN_TRADE_VOLUME:
                    trade = buy_decisions[buy_index]
                    name = trade.get("name")
                    isin = trade.get("isin", "N/A")
                    reason = trade.get("grund", "")
                    amt = trade.get("betrag_eur", 0)
                    
                    remote_manager.update_status("Trading", f"BUY: {name}", balance=current_cash)
                    
                    # Final Safety Check: Do we have enough cash left?
                    if amt > (current_cash + 10):
                        print(f"⚠️ Überspringe Kauf von {name}: Nicht genügend Cash ({current_cash:.2f} €)")
                        buy_index += 1
                        continue

                    search_term = isin if isin != "N/A" else name
                    result = await execute_buy_order(page, search_term, amt, real_name=name, isin=isin, reason=reason)
                    
                    if result == "SUCCESS":
                        # Kauf erfolgreich - Cash abziehen und weiter
                        current_cash -= amt
                        await asyncio.sleep(3)
                        buy_index += 1
                    elif result == "CANCELLED_LIMIT_TOO_LOW":
                        # Website-Limit macht Kauf unrentabel - nächste Aktie probieren
                        print(f"   ➡️ Probiere nächstbessere Aktie (falls vorhanden)...")
                        buy_index += 1
                        # Kein Cash abziehen, da Kauf abgebrochen
                    else:
                        # Anderer Abbruch (nicht handelbar, etc.) - überspringen
                        buy_index += 1

            remote_manager.update_status("Fertig", "Zyklus erfolgreich beendet.", balance=current_cash)
            
        except Exception as e:
            print(f"❌ KRITISCHER FEHLER IM BOT-ZYKLUS: {e}")
            remote_manager.update_status("Fehler", str(e), balance=current_cash)
            
        finally:
            await context.close()