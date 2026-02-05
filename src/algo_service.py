import config
from datetime import datetime
from market_data import get_market_snapshot, get_isin_by_name, is_market_open, get_minutes_until_close
from utils import load_blacklist, calculate_fee


def analyze_portfolio_safety(depot_data, ai_defense_results, market_snapshot):
    """
    Phase 1: Defense.
    Adjusted for SWING TRADING: Holds positions overnight unless emergency.
    """
    sells = []
    pending_sell_isins = [o['isin'] for o in depot_data['open_orders'] if o['type'] == 'SELL']
    
    for stock in depot_data['stocks']:
        isin = stock.get('isin')
        name = stock['name']
        qty = stock.get('qty', 0)
        current_value_eur = stock.get('value_eur', 0.0)
        
        if isin in pending_sell_isins: continue
        
        # 1. AI RED FLAG CHECK (Still critical for Swing Trading)
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
        
        # --- TECHNICAL SELL RULES ---
        if tech_data:
            price = tech_data['price']
            ema_fast = tech_data['ema_fast']
            rsi = tech_data['rsi']
            ticker = tech_data['ticker']

            # A. EOD PROTECTION (ONLY IF ENABLED IN CONFIG)
            # For Swing Trading, config.MINUTES_BEFORE_CLOSE_TO_SELL should be 0 or -1
            if config.MINUTES_BEFORE_CLOSE_TO_SELL > 0:
                mins_left = get_minutes_until_close(ticker)
                if mins_left <= config.MINUTES_BEFORE_CLOSE_TO_SELL:
                    sells.append({
                        "aktion": "SELL", "name": name, "isin": isin,
                        "grund": f"🕒 EOD EXIT: Market closing in {mins_left} min."
                    })
                    continue

            # B. HARD STOP LOSS (Emergency Brake)
            if perf_pct <= config.STOP_LOSS_HARD_PCT:
                sells.append({
                    "aktion": "SELL", "name": name, "isin": isin,
                    "grund": f"🛑 STOP LOSS: Position at {perf_pct:.1f}%"
                })
                continue

            # C. HARD TAKE PROFIT (Optional, usually high for Swing)
            if perf_pct >= config.TAKE_PROFIT_HARD_PCT:
                sells.append({
                    "aktion": "SELL", "name": name, "isin": isin,
                    "grund": f"💰 TAKE PROFIT: Target reached ({perf_pct:.1f}%)"
                })
                continue

            # D. TRAILING STOP & OVERBOUGHT PROTECTION
            # We allow higher RSI in Swing Trading (Momentum)
            if perf_pct >= config.TRAILING_STOP_ACTIVATE_PCT:
                
                # 1. RSI exhaustion - relaxed for Swing
                if rsi > config.RSI_OVERBOUGHT: # e.g. > 85
                    sells.append({
                        "aktion": "SELL", "name": name, "isin": isin,
                        "grund": f"💰 TAKE PROFIT: RSI Extreme ({rsi:.0f}) at {perf_pct:+.1f}% profit."
                    })
                    continue
                    
                # 2. Trend Break - We use EMA Slow for Swing, not EMA Fast
                # EMA Fast break is just noise in swing trading.
                if price < tech_data['ema_slow']:
                    sells.append({
                        "aktion": "SELL", "name": name, "isin": isin,
                        "grund": f"🔒 TRAILING STOP: Trend Change (EMA21) at {perf_pct:+.1f}% profit."
                    })
                    continue

            # E. TREND BREAK (Sinking Ship prevention)
            # Only sell if we are losing AND trend is definitely broken
            if price < tech_data['ema_slow'] and perf_pct < -2.0:
                sells.append({
                    "aktion": "SELL", "name": name, "isin": isin,
                    "grund": f"📉 TREND BREAK: Price fell below EMA21 & Negative Perf."
                })
                continue
                
    return sells

def synthesize_decisions(depot_data, tech_candidates, ai_matrix):
    """
    Phase 3: Synthesis.
    Combines Tech Score and AI Matrix to generate final BUY decisions.
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
        if isin in pending_buy_isins or isin in owned_isins: continue
        
        ai_data = next((item for item in ai_matrix if item.get('isin') == isin), None)
        if not ai_data: continue 
        
        analyst_rating = float(ai_data.get('analyst_rating', 3.0)) 
        sentiment = float(ai_data.get('news_sentiment', 3.0)) 
        
        ai_score = ((analyst_rating + sentiment) / 2 - 1) / 4 * 100
        
        tech_score = tech_data['tech_score']
        final_score = (tech_score * config.TECH_WEIGHT) + (ai_score * config.AI_WEIGHT)
        
        # Earnings Block - Relaxed for Swing
        earnings_date_str = ai_data.get('earnings_date', '0')
        earnings_danger = False
        if earnings_date_str and earnings_date_str != '0':
            try:
                ed = datetime.strptime(earnings_date_str, "%Y-%m-%d")
                days_to_earnings = (ed - datetime.now()).days
                if 0 <= days_to_earnings <= config.EARNINGS_DAYS_THRESHOLD:
                    earnings_danger = True
            except: pass
            
        print(f"   📊 {tech_data['ticker']}: Tech {tech_score:.0f} | AI {ai_score:.0f} | FINAL {final_score:.1f}")
        
        if final_score >= config.MIN_FINAL_SCORE and not earnings_danger:
            tech_data['final_score'] = final_score
            tech_data['ai_context'] = ai_data.get('brief_summary', '')
            scored_candidates.append(tech_data)

    # 3. Allocation
    if not scored_candidates: return []
    
    scored_candidates.sort(key=lambda x: x['final_score'], reverse=True)
    
    num_to_buy = min(len(scored_candidates), config.MAX_NEW_POSITIONS_PER_CYCLE)
    current_slots = len(depot_data['stocks'])
    slots_left = config.PORTFOLIO_DIVERSITY - current_slots
    num_to_buy = min(num_to_buy, max(0, slots_left))
    
    if num_to_buy <= 0:
        print(f"   ⚠️ Portfolio at diversity limit ({current_slots}/{config.PORTFOLIO_DIVERSITY}).")
        return []

    # Swing Strategy: Go big or go home (Higher allocation per stock)
    budget_per_stock = cash / num_to_buy
    actual_invest = max(config.MIN_TRADE_VOLUME, min(budget_per_stock, config.MAX_INVEST_PER_STOCK))
    
    temp_cash = cash
    for i in range(num_to_buy):
        c = scored_candidates[i]
        if temp_cash >= config.MIN_TRADE_VOLUME:
            amt = min(actual_invest, temp_cash)
            if (temp_cash - amt) < config.MIN_TRADE_VOLUME:
                amt = temp_cash

            final_decisions.append({
                "aktion": "BUY",
                "isin": c['isin'],
                "name": c['ticker'],
                "betrag_eur": amt,
                "grund": f"Score {c['final_score']:.0f} | Momentum Swing | {c['ai_context']}"
            })
            temp_cash -= amt
            
    if final_decisions:
        print("\n" + "─"*50)
        print(f"💰 FINAL SWING TRADES ({len(final_decisions)})")
        print("─"*50)
        for d in final_decisions:
            print(f"   🚀 BUY: {d['name']} | Amount: {d['betrag_eur']:.2f} €")
        print("─"*50 + "\n")
    else:
        print("\n🤷‍♂️ No SWING opportunities found.")

    return final_decisions

def calculate_algo_decisions(depot_data):
    return []