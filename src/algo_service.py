import config
from datetime import datetime
from market_data import get_market_snapshot, get_isin_by_name
from utils import load_blacklist

def is_market_open(ticker):
    """Checks market hours (CET)."""
    now = datetime.now()
    if now.weekday() >= 5: return False # Weekend
    
    minutes = now.hour * 60 + now.minute
    
    # DAX / ATX (09:00 - 17:40)
    if ticker.endswith(".VI") or ticker.endswith(".DE"):
        return 540 <= minutes <= 1060 
        
    # US Market (15:30 - 22:00)
    if "." not in ticker or "US" in ticker:
        return 930 <= minutes <= 1320
        
    return True

def calculate_algo_decisions(depot_data):
    print("\n" + "="*80)
    print(f"🧠 STRATEGY ENGINE | {datetime.now().strftime('%H:%M:%S')} | Trend-Following & Momentum")
    print("="*80)
    
    decisions = []
    market_data = get_market_snapshot()
    
    if not market_data:
        print("❌ CRITICAL: No Market Data received from Yahoo Finance.")
        return []

    # --- 1. PORTFOLIO ANALYSIS ---
    print(f"{'NAME':<20} | {'STATUS':<10} | {'GROSS %':<7} | {'NET P/L':<9} | {'RSI':<5} | {'TREND':<7} | {'ACTION / REASON'}")
    print("-" * 100)

    pending_sell_names = [o['name'] for o in depot_data['open_orders'] if o['type'] == 'SELL']
    
    for stock in depot_data['stocks']:
        name = stock["name"]
        isin = stock.get("isin", "N/A") 
        qty = stock.get("qty", 0)
        current_value_eur = stock.get("value_eur", 0.0)
        
        # 1. CHECK LOCKS
        is_locked = any(p in name or name in p for p in pending_sell_names)
        if is_locked:
            print(f"{name[:19]:<20} | 🔒 LOCKED | {stock.get('performance_since_buy', 'N/A'):<7} | {'-':<9} | {'-':<5} | {'-':<7} | Pending Sell Order")
            continue

        # 2. MATCH DATA
        ticker_data = None
        resolved_isin = isin
        
        # Match methods (ISIN -> Name -> Fuzzy)
        if isin != "N/A" and isin in market_data:
            ticker_data = market_data[isin]
        
        if not ticker_data:
            fallback_isin = get_isin_by_name(name)
            if fallback_isin and fallback_isin in market_data:
                ticker_data = market_data[fallback_isin]
                resolved_isin = fallback_isin
        
        if not ticker_data:
            name_lower = name.lower()
            for m_isin, data in market_data.items():
                ticker = data['ticker']
                if ticker.split(".")[0].lower() in name_lower:
                    ticker_data = data
                    resolved_isin = m_isin
                    break

        # 3. GET PERFORMANCE (GROSS)
        gross_perf_pct = 0.0
        try:
            raw_perf = stock.get("performance_since_buy", "0").replace("%", "").replace(",", ".").replace("+", "").strip()
            gross_perf_pct = float(raw_perf)
        except: pass

        # 4. CALCULATE NET RETURNS (Including Fees)
        # Reconstruct Invested Amount: Invested = Current / (1 + GrossPct/100)
        # Note: This assumes broker's "Performance" is based on raw price change or pure invest amount without fees.
        # If broker includes fees, this might be slightly off, but safer to assume we must subtract fees manually just in case.
        if gross_perf_pct != -100:
            invested_basis = current_value_eur / (1 + gross_perf_pct / 100.0)
        else:
            invested_basis = current_value_eur # Avoiding div by zero if something is weird

        # Fees: 20€ Buy + 0€ Sell (as per user/config)
        total_fees = config.TRANSACTION_FEE_BUY + config.TRANSACTION_FEE_SELL
        
        gross_profit_eur = current_value_eur - invested_basis
        net_profit_eur = gross_profit_eur - total_fees
        
        # Net Percent based on original invested amount
        net_perf_pct = (net_profit_eur / invested_basis * 100) if invested_basis > 0 else 0.0
        
        # Formatted Net String
        net_str = f"{net_profit_eur:+.1f}€ ({net_perf_pct:+.1f}%)"


        # 5. ANALYZE
        if not ticker_data:
            # Fallback Logic (Data Missing)
            action = "HOLD"
            reason = "No Live Data"
            
            # Use NET pct for safety checks if possible, or Fallback to Gross if big crash
            if gross_perf_pct <= config.STOP_LOSS_HARD_PCT:
                action = "SELL"
                reason = "Emergency Stop Loss (Blind)"
            
            print(f"{name[:19]:<20} | ⚠️ BLIND  | {gross_perf_pct:+.2f}%  | {net_str:<9} | {'?':<5} | {'?':<7} | {action}: {reason}")
            if action == "SELL":
                decisions.append({"aktion": "SELL", "name": name, "grund": reason})
            continue

        # Valid Data Found
        price = ticker_data['price']
        rsi = ticker_data['rsi']
        ema9 = ticker_data['ema_9']
        trend = ticker_data['trend'] # UP / DOWN / NEUTRAL
        
        action = "HOLD"
        reason = "Strategy fits"

        # --- VERBESSERTE EXIT-LOGIK (FEE AWARE) ---
        
        # A. Stop Loss (Respect Hard Limit on GROSS or NET?)
        # Usage of NET is safer for the wallet, but GROSS is technically cleaner for chart analysis.
        # We'll use GROSS for "Structure Break" (Stop Loss) but check NET for "Take Profit".
        # However, if Net Loss is huge due to fees on small position, we must be careful.
        
        if gross_perf_pct <= config.STOP_LOSS_HARD_PCT:
            action = "SELL"
            reason = f"🛑 Stop Loss Hit (Gross {gross_perf_pct:.1f}%)"
        
        # B. Hard Take Profit (Goal reached) - CHECK NET PROFIT!
        elif net_perf_pct >= config.TAKE_PROFIT_HARD_PCT:
            action = "SELL"
            reason = f"💰 Take Profit Hit (Net {net_perf_pct:.1f}%)"
        
        # C. Trailing Stop - Only activate if we are NET POSITIVE!
        elif net_perf_pct >= config.TRAILING_STOP_ACTIVATE_PCT:
            # Trailing Stop mechanism
            # If momentum breaks (Price < EMA9) OR RSI Overbought reversal
            if price < ema9:
                action = "SELL"
                reason = f"🔒 Trailing Stop (Net {net_perf_pct:.1f}% | EMA9 Break)"
            elif rsi > config.RSI_OVERBOUGHT and trend != "UP":
                action = "SELL"
                reason = f"🔒 Trailing Stop (Net {net_perf_pct:.1f}% | RSI {rsi:.0f})"
            else:
                reason = f"Holding (Net {net_perf_pct:.1f}% > {config.TRAILING_STOP_LOCK_IN_PCT}%)"
            
        # D. Technical Exit (Weakness without profit)
        # If we are slightly red but indicators scream SELL, do we sell?
        # Yes, better small loss than big loss.
        elif rsi > config.RSI_OVERBOUGHT:
            # Overbought but price confusing? Sell if not losing too much.
            if net_perf_pct > -1.0: 
                action = "SELL"
                reason = f"Overbought RSI ({rsi:.0f}) & Stagnant"
        
        # Trend Broken Check (The "Sinking Ship" Fix)
        # If Price drops below EMA9, the short-term trend is dead.
        # SELL immediately, even if it's a small loss, to avoid riding it down to -2%.
        elif price < ema9:
             # Safety: Only sell if we are NOT deep in the hole yet (e.g. better than -1.5%).
             # If we are already -1.8%, might as well wait for the hard stop.
             # But if we are -0.2%, GET OUT!
             if gross_perf_pct > -1.2:
                 action = "SELL"
                 reason = "Trend Broken (Price < EMA9) - Early Exit"
             else:
                 reason = "Trend Broken but Deep Dive (Hold for Bounce/Stop)"

        # Output Row
        print(f"{name[:19]:<20} | ✅ LIVE   | {gross_perf_pct:+.2f}%  | {net_str:<9} | {rsi:<5.1f} | {trend:<7} | {action}: {reason}")
        
        if action == "SELL":
             decisions.append({"aktion": "SELL", "name": name, "grund": reason})


    # --- 2. MARKET SCAN ---
    print("\n" + "-"*100)
    
    # Berechne das tatsächlich verfügbare Cash
    displayed_cash = depot_data['cash']
    pending_buy_amount = sum(
        order.get('betrag_eur', 0) 
        for order in depot_data['open_orders'] 
        if order['type'] == 'BUY'
    )
    cash = displayed_cash - pending_buy_amount
    
    print(f"🔭 MARKET SCAN")
    print(f"   💰 Angezeigtes Cash:      {displayed_cash:.2f} €")
    if pending_buy_amount > 0:
        print(f"   📋 Offene Kaufaufträge:  -{pending_buy_amount:.2f} €")
    print(f"   ➡️  Verfügbares Budget:   {cash:.2f} €")
    
    if cash < config.MIN_CASH_FOR_NEW_TRADE:
        print("   ⚠️ Insufficient Cash to trade.")
    else:
        candidates = []
        pending_buy_isins = [o['isin'] for o in depot_data['open_orders'] if o['type'] == 'BUY']
        
        # Load Blacklist
        blacklist_entries = load_blacklist()
        blacklist_ids = set(e['id'] for e in blacklist_entries)
        
        print(f"{'TICKER':<10} | {'PRICE':<8} | {'RSI':<5} | {'TREND':<7} | {'B.E. %':<6} | {'STATUS'}")
        
        for isin, data in market_data.items():
            # Blacklist Check
            if isin in blacklist_ids: continue
            ticker = data['ticker']
            simple_ticker = ticker.split(".")[0]
            if ticker in blacklist_ids or simple_ticker in blacklist_ids: continue
            
            # Skip closed / owned
            if not is_market_open(ticker): continue
            already_owned = any(simple_ticker in s['name'] for s in depot_data['stocks'])
            if already_owned or isin in pending_buy_isins: continue

            # Strategy Check
            score = 0
            rsi = data['rsi']
            price = data['price']
            ema20 = data['ema_20']
            vwap = data.get('vwap', price)
            volume_ratio = data.get('volume_ratio', 1.0)
            
            # Calculate Break-Even % for this potential trade
            # Assume we invest max possible per stock
            target_invest = min(cash, config.MAX_INVEST_PER_STOCK)
            if target_invest < config.MIN_TRADE_VOLUME:
                # Can't trade this anyway
                continue
                
            fee_impact_pct = (config.TRANSACTION_FEE_BUY / target_invest) * 100
            
            # Status
            status_parts = []
            
            # 1. Trend Filter
            if price > ema20: score += 1
            
            # 2. RSI Filter (Uses NEW optimized config)
            if config.RSI_BUY_MIN <= rsi <= config.RSI_BUY_MAX: score += 1
            
            # 3. Volume Filter
            if volume_ratio >= config.MIN_VOLUME_RATIO: score += 1
            
            # 4. VWAP
            if price > vwap: score += 1

            # Entscheidung: Strict Score
            if score >= 3:
                # Extra Check: Is Fee Impact too high? (> 0.5% starts to hurt day trading)
                if fee_impact_pct > 0.6:
                    status_msg = f"Wait (Fees {fee_impact_pct:.1f}%)"
                else:
                    status_msg = f"✅ BUY (Score {score}/4)"
                    candidates.append(data)
            else:
                status_msg = f"Wait ({score}/4)"
                
            print(f"{ticker:<10} | {price:<8.2f} | {rsi:<5.1f} | {data['trend']:<7} | {fee_impact_pct:<6.2f} | {status_msg}")

        if candidates:
            candidates.sort(key=lambda x: x['rsi'])
            num_candidates = len(candidates)
            target_count = min(num_candidates, config.MAX_NEW_POSITIONS_PER_CYCLE)
            ideal_budget_per_stock = cash / target_count
            actual_budget = max(config.MIN_TRADE_VOLUME, min(ideal_budget_per_stock, config.MAX_INVEST_PER_STOCK))
            
            print(f"\n⚖️ ALLOCATION: Found {num_candidates} signals. Buying top {target_count}.")
    
            current_temp_cash = cash
            for i in range(target_count):
                best = candidates[i]
                if current_temp_cash >= config.MIN_TRADE_VOLUME:
                    invest_amount = min(actual_budget, current_temp_cash)
                    if (current_temp_cash - invest_amount) < config.MIN_TRADE_VOLUME:
                        invest_amount = current_temp_cash
    
                    decisions.append({
                        "aktion": "BUY",
                        "isin": best['isin'],
                        "name": best['ticker'],
                        "betrag_eur": invest_amount,
                        "grund": f"Score 3+/4 (RSI {best['rsi']:.0f}, Vol {best.get('volume_ratio', 1.0):.1f}x)"
                    })
                    print(f"   ✅ Added to execution: {best['ticker']} ({invest_amount:.2f} €)")
                    current_temp_cash -= invest_amount
                else:
                    print(f"   ⚠️ Skipping {best['ticker']}: Insufficient cash")
    
    return decisions