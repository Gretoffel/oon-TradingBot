import config
from datetime import datetime
from market_data import get_market_snapshot, get_isin_by_name, is_market_open, get_minutes_until_close
from utils import load_blacklist, calculate_fee


def analyze_portfolio_safety(depot_data, ai_defense_results, market_snapshot):
    """
    Phase 1: Defense.
    Combines AI 'Red Flags' with Technical Indicators and EOD logic.
    """
    sells = []
    pending_sell_isins = [o['isin'] for o in depot_data['open_orders'] if o['type'] == 'SELL']
    
    for stock in depot_data['stocks']:
        isin = stock.get('isin')
        name = stock['name']
        qty = stock.get('qty', 0)
        current_value_eur = stock.get('value_eur', 0.0)
        
        if isin in pending_sell_isins: continue
        
        # 1. AI RED FLAG CHECK
        ai_match = next((r for r in ai_defense_results if r.get('isin') == isin or (r.get('isin') and r.get('isin') in name)), None)
        if ai_match and ai_match.get('action') == 'EMERGENCY_SELL':
            sells.append({
                "aktion": "SELL", "name": name, "isin": isin,
                "grund": f"🚨 AI EMERGENCY: {ai_match.get('reason', 'Red Flag')}"
            })
            continue

        # 2. MATCH TECHNICAL DATA
        tech_data = market_snapshot.get(isin)
        if not tech_data:
            # Check by name matching if ISIN failed
            for t_isin, t_data in market_snapshot.items():
                if t_data['ticker'].split('.')[0].lower() in name.lower():
                    tech_data = t_data
                    break
        
        # --- PERFORMANCE PARSING ---
        perf_pct = 0.0
        try:
            raw_perf = stock.get("performance_since_buy", "0").replace("%", "").replace(",", ".").replace("+", "").strip()
            perf_pct = float(raw_perf)
        except: pass
        
        # Reconstruct Basis for Fee analysis
        # Fees: We estimate fees using the current value and a theoretical buy value
        fee_sell = calculate_fee(current_value_eur)
        net_perf_pct = perf_pct # Default to gross if we can't get better data
        
        # --- TECHNICAL SELL RULES ---
        if tech_data:
            price = tech_data['price']
            ema_fast = tech_data['ema_fast']
            rsi = tech_data['rsi']
            atr = tech_data.get('atr', 0)
            ticker = tech_data['ticker']

            # A. EOD PROTECTION
            mins_left = get_minutes_until_close(ticker)
            if mins_left <= config.MINUTES_BEFORE_CLOSE_TO_SELL:
                sells.append({
                    "aktion": "SELL", "name": name, "isin": isin,
                    "grund": f"🕒 EOD EXIT: Market closing in {mins_left} min."
                })
                continue

            # B. HARD STOP LOSS
            if perf_pct <= config.STOP_LOSS_HARD_PCT:
                sells.append({
                    "aktion": "SELL", "name": name, "isin": isin,
                    "grund": f"🛑 STOP LOSS: Position at {perf_pct:.1f}%"
                })
                continue

            # C. HARD TAKE PROFIT
            if perf_pct >= config.TAKE_PROFIT_HARD_PCT:
                sells.append({
                    "aktion": "SELL", "name": name, "isin": isin,
                    "grund": f"💰 TAKE PROFIT: Target reached ({perf_pct:.1f}%)"
                })
                continue

            # D. TRAILING STOP & OVERBOUGHT PROTECTION (Profit Protection)
            if net_perf_pct >= config.TRAILING_STOP_ACTIVATE_PCT:
                # 1. RSI exhaustion (immediate profit taking when over-extended)
                if rsi > 80:
                    sells.append({
                        "aktion": "SELL", "name": name, "isin": isin,
                        "grund": f"💰 TAKE PROFIT: RSI Exhaustion reached ({rsi:.0f}) at {net_perf_pct:+.1f}% profit."
                    })
                    continue
                    
                # 2. Trend Break while in profit
                if price < ema_fast:
                    sells.append({
                        "aktion": "SELL", "name": name, "isin": isin,
                        "grund": f"🔒 TRAILING STOP: Trend Break at {net_perf_pct:+.1f}% profit."
                    })
                    continue

                # 3. EMA21 Cross (Deeper trend break)
                if price < tech_data['ema_slow']:
                    sells.append({
                        "aktion": "SELL", "name": name, "isin": isin,
                        "grund": f"🔒 TRAILING STOP: Core Trend Lost (EMA21) at {net_perf_pct:+.1f}% profit."
                    })
                    continue

            # E. TREND BREAK (Sinking Ship prevention)
            # Exit if short term trend is lost even if it's a small loss
            if price < ema_fast and perf_pct > -1.5:
                # Only if we are not already deep in the hole (then we wait for hard stop)
                sells.append({
                    "aktion": "SELL", "name": name, "isin": isin,
                    "grund": f"📉 TREND BREAK: Price fell below EMA_FAST."
                })
                continue
                
    return sells

def synthesize_decisions(depot_data, tech_candidates, ai_matrix):
    """
    Phase 3: Synthesis.
    Combines Tech Score and AI Matrix to generate final BUY decisions.
    
    Formula: Final_Score = (Tech_Score * 0.4) + (AI_Score * 0.6)
    """
    final_decisions = []
    
    # 1. Budget Calculation
    displayed_cash = depot_data['cash']
    pending_buy_amount = sum(o.get('betrag_eur', 0) for o in depot_data['open_orders'] if o['type'] == 'BUY')
    cash = displayed_cash - pending_buy_amount
    
    if cash < config.MIN_CASH_FOR_NEW_TRADE:
        print("   ⚠️ Insufficient budget for new trades.")
        return []

    # 2. Score & Filter
    scored_candidates = []
    pending_buy_isins = [o['isin'] for o in depot_data['open_orders'] if o['type'] == 'BUY']
    owned_isins = [s.get('isin') for s in depot_data['stocks']]
    
    for isin, tech_data in tech_candidates.items():
        # Safety filters
        if isin in pending_buy_isins or isin in owned_isins: continue
        
        # Match with AI Matrix
        ai_data = next((item for item in ai_matrix if item.get('isin') == isin), None)
        if not ai_data: continue # We need AI validation
        
        # Calculate AI Score (0-100)
        # Ratings and Sentiment are 1-5
        analyst_rating = float(ai_data.get('analyst_rating', 3.0)) # Default neutral
        sentiment = float(ai_data.get('news_sentiment', 3.0)) # Default neutral
        
        # Scale 1-5 to 0-100: (val - 1) / 4 * 100
        ai_score = ((analyst_rating + sentiment) / 2 - 1) / 4 * 100
        
        # Final Score
        tech_score = tech_data['tech_score']
        final_score = (tech_score * config.TECH_WEIGHT) + (ai_score * config.AI_WEIGHT)
        
        # Earnings Block
        earnings_date_str = ai_data.get('earnings_date', '0')
        earnings_danger = False
        if earnings_date_str and earnings_date_str != '0':
            try:
                ed = datetime.strptime(earnings_date_str, "%Y-%m-%d")
                days_to_earnings = (ed - datetime.now()).days
                if 0 <= days_to_earnings <= config.EARNINGS_DAYS_THRESHOLD:
                    earnings_danger = True
            except: pass
            
        print(f"   📊 {tech_data['ticker']}: Tech {tech_score:.0f} | AI {ai_score:.0f} | FINAL {final_score:.1f} {'⚠️ EARNINGS' if earnings_danger else ''}")
        
        if final_score >= config.MIN_FINAL_SCORE and not earnings_danger:
            tech_data['final_score'] = final_score
            tech_data['ai_context'] = ai_data.get('brief_summary', '')
            scored_candidates.append(tech_data)

    # 3. Allocation
    if not scored_candidates: return []
    
    # Sort by Final Score
    scored_candidates.sort(key=lambda x: x['final_score'], reverse=True)
    
    num_to_buy = min(len(scored_candidates), config.MAX_NEW_POSITIONS_PER_CYCLE)
    # Check if we are approaching diversity limit
    current_slots = len(depot_data['stocks'])
    slots_left = config.PORTFOLIO_DIVERSITY - current_slots
    num_to_buy = min(num_to_buy, max(0, slots_left))
    
    if num_to_buy <= 0:
        print(f"   ⚠️ Portfolio at diversity limit ({current_slots}/{config.PORTFOLIO_DIVERSITY}).")
        return []

    budget_per_stock = cash / num_to_buy
    actual_invest = max(config.MIN_TRADE_VOLUME, min(budget_per_stock, config.MAX_INVEST_PER_STOCK))
    
    temp_cash = cash
    for i in range(num_to_buy):
        c = scored_candidates[i]
        if temp_cash >= config.MIN_TRADE_VOLUME:
            amt = min(actual_invest, temp_cash)
            # Ensure we don't buy less than min volume if it's the last bit of cash
            if (temp_cash - amt) < config.MIN_TRADE_VOLUME:
                amt = temp_cash

            final_decisions.append({
                "aktion": "BUY",
                "isin": c['isin'],
                "name": c['ticker'],
                "betrag_eur": amt,
                "grund": f"Score {c['final_score']:.0f} | {c['ai_context']}"
            })
            temp_cash -= amt
            
    # 4. Final Summary for Console
    if final_decisions:
        print("\n" + "─"*50)
        print(f"💰 FINAL BUY DECISIONS ({len(final_decisions)})")
        print("─"*50)
        for d in final_decisions:
            print(f"   🚀 BUY: {d['name']} | Amount: {d['betrag_eur']:.2f} €")
            print(f"      Reason: {d['grund']}")
        print("─"*50 + "\n")
    else:
        print("\n🤷‍♂️ No BUY opportunities met the criteria this cycle.")

    return final_decisions

def calculate_algo_decisions(depot_data):
    """Legacy entry point - Now partially bypassed by bot.py flow."""
    # This remains for backward compatibility but bot.py will use the new functions
    # However, we can keep EOD logic here as a fallback
    return [] # bot.py will handle the new flow
