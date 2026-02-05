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

async def run_bot_cycle():
    print("\n" + "="*40)
    print("⚡ 3-PHASE-LOOP BOT ZYKLUS STARTET")
    remote_manager.update_status("Start", "Initialisiere 3-Phasen-Loop...", balance=0.0)
    print("="*40)

    async with async_playwright() as p:
        context = await create_browser_context(p)
        
        try:
            page = context.pages[0] if context.pages else await context.new_page()

            # --- PHASE 0: LOGGING & SCANNING ---
            await login(page)
            depot_data = await scan_depot(page)
            current_cash = depot_data["cash"]
            
            # --- PHASE 2 (UPGRADED): TECHNICAL SCAN (Market + Portfolio) ---
            # Fetch technical data for everything we track AND everything we own
            portfolio_isins = [s.get('isin') for s in depot_data['stocks'] if s.get('isin') and s.get('isin') != 'N/A']
            remote_manager.update_status("Tech Scan", "Analysiere Markt-Technik & Portfolio...", balance=current_cash)
            tech_snapshot = get_market_snapshot(portfolio_isins=portfolio_isins) 
            
            # --- PHASE 1 (DEFENSE): AI + TECH PORTFOLIO CHECK ---
            # 1. Prepare AI Defense
            tradeable_stocks = []
            for s in depot_data['stocks']:
                isin = s.get('isin', 'N/A')
                ticker = next((t_ticker for t_isin, t_ticker in TICKER_MAPPING.items() if t_isin == isin), None)
                if (ticker and is_market_open(ticker)) or not ticker:
                    tradeable_stocks.append(s)

            if tradeable_stocks:
                remote_manager.update_status("Defense", f"KI & Technik prüfen {len(tradeable_stocks)} Aktien...", balance=current_cash)
                ai_defense_results = await check_portfolio_safety(page, context, tradeable_stocks)
                # Combine AI findings with Technical StopLoss/TakeProfit/EOD in algo_service
                emergency_sells = analyze_portfolio_safety(depot_data, ai_defense_results, tech_snapshot)
            else:
                emergency_sells = []
            
            # 2. Console Summary for Defense
            print("\n" + "─"*50)
            print(f"🛡️ PORTFOLIO DEFENSE RESULTS ({len(depot_data['stocks'])} held)")
            if emergency_sells:
                for s in emergency_sells:
                    print(f"   🚨 SELL TRIGGERED: {s['name']} - {s['grund']}")
            else:
                print("   ✅ All owned positions passed safety & technical checks.")
            print("─"*50 + "\n")
            
            if emergency_sells:
                print(f"🚀 EXECUTING {len(emergency_sells)} SELL ORDERS...")
                if page.is_closed(): page = await context.new_page()
                if page.url != config.OON_DEPOT_URL: await page.goto(config.OON_DEPOT_URL)
                
                for trade in emergency_sells:
                    name = trade["name"]
                    remote_manager.update_status("Trading", f"SELL: {name}", balance=current_cash)
                    owned = next((s for s in depot_data["stocks"] if s["name"] in name or name in s["name"]), None)
                    if owned:
                        await execute_sell_order(page, owned["name"], owned["qty"], reason=trade["grund"])
                        await asyncio.sleep(3)
                
                # Re-scan after sells to update cash/depot
                depot_data = await scan_depot(page)
                current_cash = depot_data["cash"]

            # --- PHASE 3 (SYNTHESIS): AI DEEP DIVE & BUY OPS ---
            # Get Top candidates from the snapshot we already have
            top_candidates = list(tech_snapshot.values())[:config.MAX_AI_CANDIDATES]
            print(f"   📊 FUNNEL: Passing top {len(top_candidates)} tech candidates to AI Deep-Dive...")
            
            remote_manager.update_status("Synthesis", "KI führt Deep-Dive durch...", balance=current_cash)
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

            remote_manager.update_status("Fertig", "Loop erfolgreich beendet.", balance=current_cash)
            
        except Exception as e:
            print(f"❌ KRITISCHER FEHLER IM BOT-ZYKLUS: {e}")
            import traceback
            traceback.print_exc()
            remote_manager.update_status("Fehler", str(e), balance=current_cash)
            
        finally:
            await context.close()
