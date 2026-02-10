import asyncio
from playwright.async_api import async_playwright
import config
import remote_manager
from utils import print_analysis_summary
from actions import execute_buy_order, execute_sell_order
from browser_utils import create_browser_context
from oon_service import login, scan_depot
from algo_service import calculate_algo_decisions

from market_data import get_market_snapshot, TICKER_MAPPING, is_market_open
from ai_service import check_portfolio_safety, analyze_candidates_deep_dive
from algo_service import analyze_portfolio_safety, synthesize_decisions

async def run_bot_cycle(full_analysis=False):
    """
    Führt einen Zyklus durch.
    full_analysis=False: Nur Preis-Check & Verkäufe (Safety Loop) - Schnell
    full_analysis=True:  Komplettes Programm mit KI & Käufen (Strategy Loop) - Langsam
    """
    mode_text = "FULL STRATEGY (KI & BUY)" if full_analysis else "QUICK CHECK (SAFETY ONLY)"
    print("\n" + "="*40)
    print(f"⚡ BOT ZYKLUS STARTET | MODUS: {mode_text}")
    remote_manager.update_status("Start", f"Modus: {mode_text}", balance=0.0)
    print("="*40)

    async with async_playwright() as p:
        context = await create_browser_context(p)
        
        try:
            page = context.pages[0] if context.pages else await context.new_page()

            # --- PHASE 0: LOGGING & SCANNING (Immer notwendig) ---
            await login(page)
            depot_data = await scan_depot(page)
            current_cash = depot_data["cash"]
            
            # Update Dashboard Data
            remote_manager.update_status(
                "Active", 
                f"Modus: {mode_text}", 
                balance=current_cash, 
                portfolio=depot_data.get('stocks', []),
                open_orders=depot_data.get('open_orders', [])
            )
            
            # --- PHASE 2 (TECH SCAN) ---
            # Wir holen immer Marktdaten, um Stops zu prüfen
            portfolio_isins = [s.get('isin') for s in depot_data['stocks'] if s.get('isin') and s.get('isin') != 'N/A']
            
            status_msg = "Analysiere Portfolio (Safety)..." if not full_analysis else "Analysiere Markt & Portfolio..."
            remote_manager.update_status("Tech Scan", status_msg, balance=current_cash)
            
            # Fetch data (Schnell genug für 1-Minuten Takt)
            tech_snapshot = get_market_snapshot(portfolio_isins=portfolio_isins) 
            
            # --- PHASE 1 (DEFENSE) ---
            # KI Defense nur im Full Mode (kostet Zeit/Quota), sonst rein technisch
            ai_defense_results = []
            if full_analysis:
                tradeable_stocks = []
                for s in depot_data['stocks']:
                    isin = s.get('isin', 'N/A')
                    ticker = next((t_ticker for t_isin, t_ticker in TICKER_MAPPING.items() if t_isin == isin), None)
                    if (ticker and is_market_open(ticker)) or not ticker:
                        tradeable_stocks.append(s)

                if tradeable_stocks:
                    remote_manager.update_status("Defense", f"KI Defense Check...", balance=current_cash)
                    ai_defense_results = await check_portfolio_safety(page, context, tradeable_stocks)
            
            # Analysiere Safety (Stop-Loss, Break-Even, EMA Trend)
            # Das passiert JEDES MAL (auch im Quick Check)
            # (Die Ergebnistabelle wird direkt in analyze_portfolio_safety ausgegeben)
            emergency_sells = analyze_portfolio_safety(depot_data, ai_defense_results, tech_snapshot)
            
            # Update Dashboard Data (Peak% wurde in analyze_portfolio_safety hinzugefügt)
            remote_manager.update_status(
                "Active", 
                f"Modus: {mode_text}", 
                balance=current_cash, 
                portfolio=depot_data.get('stocks', []),
                open_orders=depot_data.get('open_orders', [])
            )

            # EXECUTE SELLS (Sofort!)
            if emergency_sells:
                if page.is_closed(): page = await context.new_page()
                if page.url != config.OON_DEPOT_URL: await page.goto(config.OON_DEPOT_URL)
                
                for trade in emergency_sells:
                    name = trade["name"]
                    remote_manager.update_status("Trading", f"SELL: {name}", balance=current_cash)
                    owned = next((s for s in depot_data["stocks"] if s["name"] in name or name in s["name"]), None)
                    if owned:
                        await execute_sell_order(page, owned["name"], owned["qty"], reason=trade["grund"])
                        await asyncio.sleep(3)
                
                # Re-scan nach Verkauf
                depot_data = await scan_depot(page)
                current_cash = depot_data["cash"]

            # --- PHASE 3 (SYNTHESIS & BUY) ---
            # Nur im FULL ANALYSIS Modus!
            if full_analysis:
                pending_buy_amount = sum(o.get('betrag_eur', 0) for o in depot_data['open_orders'] if o['type'] == 'BUY')
                available_cash = current_cash - pending_buy_amount
                current_slots = len(depot_data['stocks'])
                slots_left = config.PORTFOLIO_DIVERSITY - current_slots
                
                ai_matrix = []
                if available_cash < config.MIN_CASH_FOR_NEW_TRADE:
                    print(f"   💰 Budget zu gering für Käufe ({available_cash:.2f} €). Skip KI.")
                elif slots_left <= 0:
                    print(f"   📁 Portfolio voll. Skip KI.")
                else:
                    # Top Candidates for AI
                    top_candidates = list(tech_snapshot.values())[:config.MAX_AI_CANDIDATES]
                    print(f"   📊 Passing top {len(top_candidates)} candidates to AI...")
                    remote_manager.update_status("Synthesis", "KI Deep-Dive (Buying)...", balance=current_cash)
                    ai_matrix = await analyze_candidates_deep_dive(page, context, top_candidates)
                
                final_buys = synthesize_decisions(depot_data, tech_snapshot, ai_matrix)
                
                if final_buys:
                    print(f"🚀 EXECUTING {len(final_buys)} BUY ORDERS...")
                    if page.is_closed(): page = await context.new_page()
                    if page.url != config.OON_DEPOT_URL: await page.goto(config.OON_DEPOT_URL)
                    
                    for trade in final_buys:
                        name = trade["name"]
                        isin = trade["isin"]
                        amt = trade["betrag_eur"]
                        reason = trade["grund"]
                        if amt > (current_cash + 10): continue
                        
                        remote_manager.update_status("Trading", f"BUY: {name}", balance=current_cash)
                        search_term = isin if isin and isin != "N/A" else name
                        result = await execute_buy_order(page, search_term, amt, real_name=name, isin=isin, reason=reason)
                        if result == "SUCCESS":
                            current_cash -= amt
                            await asyncio.sleep(3)

            remote_manager.update_status("Fertig", "Zyklus beendet.", balance=current_cash)
            
        except Exception as e:
            print(f"❌ ERROR IN BOT CYCLE: {e}")
            import traceback
            traceback.print_exc()
            remote_manager.update_status("Fehler", str(e), balance=current_cash)
            
        finally:
            await context.close()