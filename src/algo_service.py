import config
from datetime import datetime
from market_data import get_market_snapshot, get_isin_by_name, is_market_open, get_minutes_until_close
from utils import load_blacklist, calculate_fee
import remote_manager  # <--- NEU: Für High Water Mark Speicher

def analyze_portfolio_safety(depot_data, ai_defense_results, market_snapshot):
    """
    Phase 1: Defense.
    Checkt Stop-Loss, High-Water-Mark (Smart Trailing) und EMA-Trend.
    """
    sells = []
    health_reports = []
    pending_sell_isins = [o['isin'] for o in depot_data['open_orders'] if o['type'] == 'SELL']
    
    # --- NEU: High Water Marks laden ---
    high_water_marks = remote_manager.get_high_water_marks()
    hwm_updated = False 

    for stock in depot_data['stocks']:
        isin = stock.get('isin')
        name = stock['name']
        qty = stock.get('qty', 0)
        
        if isin in pending_sell_isins: continue
        
        # Default report data
        report = {
            "name": name[:15],
            "isin": isin,
            "price": 0.0,
            "perf": 0.0,
            "peak": 0.0,
            "rsi": 0.0,
            "trend": "N/A",
            "signal": "HOLD",
            "reason": "OK"
        }

        # --- PERFORMANCE PARSING ---
        perf_pct = 0.0
        try:
            raw_perf = stock.get("performance_since_buy", "0").replace("%", "").replace(",", ".").replace("+", "").strip()
            perf_pct = float(raw_perf)
        except: pass
        report["perf"] = perf_pct

        # --- NEU: HWM UPDATE LOGIK ---
        current_hwm = high_water_marks.get(isin, 0.0)
        
        # 1. Reset bei Verlust: Wenn Position rot ist, HWM vergessen
        if perf_pct < 0:
            if current_hwm != 0:
                high_water_marks[isin] = 0.0
                hwm_updated = True
        # 2. Update bei neuem Hoch
        elif perf_pct > current_hwm:
            high_water_marks[isin] = perf_pct
            current_hwm = perf_pct
            hwm_updated = True
            # Optional: Logge signifikante neue Hochs
            if perf_pct > config.HWM_TRIGGER_PCT:
                print(f"   📈 New Peak für {name}: {perf_pct:.2f}%")

        report["peak"] = current_hwm

        # 1. AI RED FLAG CHECK
        if ai_defense_results:
            ai_match = next((r for r in ai_defense_results if r.get('isin') == isin or (r.get('isin') and r.get('isin') in name)), None)
            if ai_match and ai_match.get('action') == 'EMERGENCY_SELL':
                reason = f"🚨 AI: {ai_match.get('reason', 'Red Flag')}"
                report["signal"] = "SELL"
                report["reason"] = reason
                sells.append({"aktion": "SELL", "name": name, "isin": isin, "grund": reason})
                health_reports.append(report)
                continue

        # 2. MATCH TECHNICAL DATA
        tech_data = market_snapshot.get(isin)
        if not tech_data:
            for t_isin, t_data in market_snapshot.items():
                if t_data['ticker'].split('.')[0].lower() in name.lower():
                    tech_data = t_data
                    break
        
        if tech_data:
            price = tech_data['price']
            rsi = tech_data['rsi']
            ticker = tech_data['ticker']
            report["name"] = ticker
            report["price"] = price
            report["rsi"] = rsi
            report["trend"] = tech_data['trend']

            # --- MARKET OPEN CHECK ---
            if not is_market_open(ticker):
                report["trend"] = "OFF"
                report["signal"] = "WAIT"
                report["reason"] = "Market Closed"
                health_reports.append(report)
                continue

            # A. EOD PROTECTION
            if config.MINUTES_BEFORE_CLOSE_TO_SELL > 0:
                mins_left = get_minutes_until_close(ticker)
                if mins_left <= config.MINUTES_BEFORE_CLOSE_TO_SELL:
                    reason = f"🕒 EOD: {mins_left}m left"
                    report["signal"] = "SELL"
                    report["reason"] = reason
                    sells.append({"aktion": "SELL", "name": name, "isin": isin, "grund": reason})
                    health_reports.append(report)
                    continue

            # --- NEU: B. HIGH WATER MARK (SMART TRAILING STOP) ---
            # Ersetzt den alten Break-Even Code komplett.
            # Wir prüfen nur, wenn wir über dem Trigger (z.B. 4%) sind.
            if current_hwm >= config.HWM_TRIGGER_PCT:
                drawdown = current_hwm - perf_pct
                if drawdown >= config.HWM_DROP_THRESHOLD:
                    reason = f"📉 HWM-EXIT: Peak {current_hwm:.1f}% -> Now {perf_pct:.1f}%"
                    report["signal"] = "SELL"
                    report["reason"] = reason
                    sells.append({"aktion": "SELL", "name": name, "isin": isin, "grund": reason})
                    
                    # Reset nach Signal, damit er nicht looped
                    high_water_marks[isin] = 0.0
                    hwm_updated = True
                    
                    health_reports.append(report)
                    continue

            # C. HARD STOP LOSS
            if perf_pct <= config.STOP_LOSS_HARD_PCT:
                reason = f"🛑 STOP-LOSS: {perf_pct:.2f}%"
                report["signal"] = "SELL"
                report["reason"] = reason
                sells.append({"aktion": "SELL", "name": name, "isin": isin, "grund": reason})
                health_reports.append(report)
                continue

            # D. HARD TAKE PROFIT
            if perf_pct >= config.TAKE_PROFIT_HARD_PCT:
                reason = f"💰 PROFIT: {perf_pct:.2f}%"
                report["signal"] = "SELL"
                report["reason"] = reason
                sells.append({"aktion": "SELL", "name": name, "isin": isin, "grund": reason})
                health_reports.append(report)
                continue

            # E. TRAILING STOP & OVERBOUGHT (Legacy / RSI)
            if perf_pct >= config.TRAILING_STOP_ACTIVATE_PCT:
                if rsi > config.RSI_OVERBOUGHT: 
                    reason = f"🔥 OVERBOUGHT: RSI {rsi:.0f}"
                    report["signal"] = "SELL"
                    report["reason"] = reason
                    sells.append({"aktion": "SELL", "name": name, "isin": isin, "grund": reason})
                    health_reports.append(report)
                    continue
                # EMA Trend Check nur, wenn wir noch nicht vom HWM gefangen wurden
                if price < tech_data['ema_slow']:
                    reason = f"🔒 T-STOP: EMA21 Break"
                    report["signal"] = "SELL"
                    report["reason"] = reason
                    sells.append({"aktion": "SELL", "name": name, "isin": isin, "grund": reason})
                    health_reports.append(report)
                    continue

            # F. TREND BREAK (Sinking Ship)
            if price < tech_data['ema_slow'] and perf_pct < -1.0:
                reason = f"📉 TREND: EMA21 Break & Neg"
                report["signal"] = "SELL"
                report["reason"] = reason
                sells.append({"aktion": "SELL", "name": name, "isin": isin, "grund": reason})
                health_reports.append(report)
                continue
                
        health_reports.append(report)

    # --- NEU: Speichern der HWMs ---
    if hwm_updated:
        remote_manager.save_high_water_marks(high_water_marks)

    # --- PRINT PORTFOLIO HEALTH TABLE ---
    if health_reports:
        print("\n" + "─"*80)
        print(f"🛡️ PORTFOLIO HEALTH CHECK | {len(health_reports)} Positions held")
        # Tabelle um PEAK% erweitert
        print(f"{'TICKER':<10} | {'PERF%':<7} | {'PEAK%':<6} | {'RSI':<5} | {'SIGNAL':<7} | {'REASON'}")
        print("-" * 80)
        for h in health_reports:
            sig_icon = "🔴 SELL" if h['signal'] == "SELL" else "🟡 WAIT" if h['signal'] == "WAIT" else "🟢 HOLD"
            perf_str = f"{h['perf']:+.2f}%"
            
            peak_val = h.get('peak', 0.0)
            peak_str = f"{peak_val:.1f}%" if peak_val > 0 else "-"

            print(f"{h['name']:<10} | {perf_str:<7} | {peak_str:<6} | {h['rsi']:<5.1f} | {sig_icon:<7} | {h['reason']}")
        print("─"*80 + "\n")
        
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