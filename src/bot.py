import asyncio
from playwright.async_api import async_playwright
import config
import remote_manager
from utils import print_analysis_summary
from actions import execute_buy_order, execute_sell_order
from browser_utils import create_browser_context
from oon_service import login, scan_depot

# NEU: Algo Service statt AI
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
            
            # Status Update
            remote_manager.update_status(
                "Analyse", 
                "Berechne Algo-Signale...", 
                balance=current_cash,
                portfolio=depot_data["stocks"],
                open_orders=depot_data["open_orders"]
            )

            # 3. ENTSCHEIDUNG (ALGO)
            if config.TEST_MODE:
                decisions = config.TEST_ORDERS
            else:
                # Hier der Aufruf an den mathematischen Algo
                decisions = calculate_algo_decisions(depot_data)

            print_analysis_summary(decisions)

            # 4. EXECUTION
            if decisions:
                print("\n" + "🚀 EXECUTION PHASE".center(40, "="))
                remote_manager.update_status("Trading", f"Verarbeite {len(decisions)} Signale...", balance=current_cash)

                if page.is_closed(): page = await context.new_page()
                if page.url != config.OON_DEPOT_URL:
                    await page.goto(config.OON_DEPOT_URL)
                    await asyncio.sleep(3)

                for trade in decisions:
                    typ = trade.get("aktion")
                    name = trade.get("name")
                    isin = trade.get("isin", "N/A")
                    reason = trade.get("grund", "")
                    
                    remote_manager.update_status("Trading", f"{typ}: {name}", balance=current_cash)

                    if typ == "BUY":
                        amt = trade.get("betrag_eur", 0)
                        # ISIN ist extrem wichtig für die Suche!
                        search_term = isin if isin != "N/A" else name
                        await execute_buy_order(page, search_term, amt, real_name=name, isin=isin, reason=reason)
                        
                        # Simuliertes Update für den nächsten Loop im selben Zyklus
                        depot_data["cash"] -= amt
                        current_cash = depot_data["cash"]
                        await asyncio.sleep(2)
                    
                    elif typ == "SELL":
                        # Wir suchen die Aktie im Depot Namen
                        owned = next((s for s in depot_data["stocks"] if s["name"] in name or name in s["name"]), None)
                        if owned:
                            await execute_sell_order(page, owned["name"], owned["qty"], reason=reason)
                            await asyncio.sleep(2)
                        else:
                            print(f"⚠️ Sell fehlgeschlagen: {name} nicht im Depot gefunden.")

            remote_manager.update_status("Fertig", "Zyklus beendet.", balance=current_cash)
            
        finally:
            await context.close()