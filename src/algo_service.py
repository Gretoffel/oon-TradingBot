import config
from datetime import datetime
from market_data import get_market_snapshot, get_isin_by_name

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
    print(f"{'NAME':<20} | {'STATUS':<10} | {'P/L %':<7} | {'RSI':<5} | {'TREND':<7} | {'ACTION / REASON'}")
    print("-" * 80)

    pending_sell_names = [o['name'] for o in depot_data['open_orders'] if o['type'] == 'SELL']
    
    for stock in depot_data['stocks']:
        name = stock["name"]
        isin = stock.get("isin", "N/A") # Ensure your oon_service extracts ISINs for stocks too!
        
        # 1. CHECK LOCKS
        # Looser matching for pending orders
        is_locked = any(p in name or name in p for p in pending_sell_names)
        if is_locked:
            print(f"{name[:19]:<20} | 🔒 LOCKED | {stock.get('performance_since_buy', 'N/A'):<7} | {'-':<5} | {'-':<7} | Pending Sell Order")
            continue

        # 2. MATCH DATA (Try multiple methods)
        ticker_data = None
        resolved_isin = isin
        
        # Method A: ISIN Match (Best - wenn ISIN korrekt gescannt wurde)
        if isin != "N/A" and isin in market_data:
            ticker_data = market_data[isin]
        
        # Method B: Name-to-ISIN Fallback (wenn ISIN "N/A" oder nicht gefunden)
        if not ticker_data:
            fallback_isin = get_isin_by_name(name)
            if fallback_isin and fallback_isin in market_data:
                ticker_data = market_data[fallback_isin]
                resolved_isin = fallback_isin
        
        # Method C: Fuzzy Name/Ticker Match (Letzte Chance)
        if not ticker_data:
            name_lower = name.lower()
            for m_isin, data in market_data.items():
                ticker = data['ticker']
                simple_ticker = ticker.split(".")[0].lower()
                # Prüfe ob Ticker im Namen vorkommt
                if simple_ticker in name_lower or name_lower in simple_ticker:
                    ticker_data = data
                    resolved_isin = m_isin
                    break

        # 3. GET PERFORMANCE
        game_perf_pct = 0.0
        try:
            raw_perf = stock.get("performance_since_buy", "0").replace("%", "").replace(",", ".").replace("+", "").strip()
            game_perf_pct = float(raw_perf)
        except: pass

        # 4. ANALYZE
        if not ticker_data:
            # Fallback Logic (Data Missing)
            action = "HOLD"
            reason = "No Live Data"
            
            # Hard Safety Net even without live data
            if game_perf_pct <= config.STOP_LOSS_HARD_PCT:
                action = "SELL"
                reason = "Emergency Stop Loss (Blind)"
            
            print(f"{name[:19]:<20} | ⚠️ BLIND  | {game_perf_pct:+.2f}%  | {'?':<5} | {'?':<7} | {action}: {reason}")
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

        # --- LOGIC ---
        
        # A. Stop Loss (Prioritize Safety)
        if game_perf_pct <= config.STOP_LOSS_HARD_PCT:
            action = "SELL"
            reason = f"🛑 Stop Loss Hit ({game_perf_pct}%)"
            
        # B. Take Profit (Greed)
        elif game_perf_pct >= config.TAKE_PROFIT_HARD_PCT:
            action = "SELL"
            reason = f"💰 Take Profit Hit ({game_perf_pct}%)"
            
        # C. Technical Exit (Weakness)
        elif rsi > config.RSI_OVERBOUGHT:
            action = "SELL"
            reason = f"Overbought RSI ({rsi:.0f})"
        
        elif game_perf_pct > 0.5 and price < ema9:
            action = "SELL"
            reason = "Trend Broken (Price < EMA9)"

        # Output Row
        print(f"{name[:19]:<20} | ✅ LIVE   | {game_perf_pct:+.2f}%  | {rsi:<5.1f} | {trend:<7} | {action}: {reason}")
        
        if action == "SELL":
             decisions.append({"aktion": "SELL", "name": name, "grund": reason})


    # --- 2. MARKET SCAN ---
    print("\n" + "-"*80)
    
    # Berechne das tatsächlich verfügbare Cash:
    # Angezeigte Cash MINUS Betrag der offenen Kaufaufträge
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
        
        print(f"{'TICKER':<10} | {'PRICE':<8} | {'RSI':<5} | {'TREND':<7} | {'STATUS'}")

        for isin, data in market_data.items():
            ticker = data['ticker']
            
            # Skip if market closed
            if not is_market_open(ticker): 
                # Don't spam log with closed markets, maybe just 1-2 lines or skip
                continue

            # Skip if owned
            simple_ticker = ticker.split(".")[0]
            already_owned = any(simple_ticker in s['name'] for s in depot_data['stocks'])
            if already_owned or isin in pending_buy_isins:
                continue

            # Strategy Check
            score = 0
            rsi = data['rsi']
            price = data['price']
            ema20 = data['ema_20']
            
            status_msg = "Wait"

            # 1. Trend Filter
            if price > ema20: score += 1
            else: status_msg = "Downtrend"
            
            # 2. RSI Filter
            if 50 <= rsi <= 70: score += 2
            elif rsi > 70: status_msg = "Overbought"
            elif rsi < 50: status_msg = "Weak Mom."

            if score >= 3:
                status_msg = "✅ BUY SIGNAL"
                candidates.append(data)
                
            print(f"{ticker:<10} | {price:<8.2f} | {rsi:<5.1f} | {data['trend']:<7} | {status_msg}")

        if candidates:
            # 1. Rank by RSI (Lower is better within our 50-70 range)
            candidates.sort(key=lambda x: x['rsi'])
            
            # 2. Determine how many we can afford / want to buy
            num_candidates = len(candidates)
            target_count = min(num_candidates, config.MAX_NEW_POSITIONS_PER_CYCLE)
            
            # 3. Calculate Budget per Stock
            # We try to split cash equally, but cap it at MAX_INVEST_PER_STOCK
            ideal_budget_per_stock = cash / target_count
            
            # Clamp the budget between our Min and Max rules
            actual_budget = max(config.MIN_TRADE_VOLUME, min(ideal_budget_per_stock, config.MAX_INVEST_PER_STOCK))
            
            print(f"\n⚖️ ALLOCATION: Found {num_candidates} signals. Attempting to buy top {target_count}.")
            print(f"   Target Budget per Stock: {actual_budget:.2f} €")
    
            current_temp_cash = cash
            for i in range(target_count):
                best = candidates[i]
                
                # Final check: Can we still afford this?
                if current_temp_cash >= config.MIN_TRADE_VOLUME:
                    invest_amount = min(actual_budget, current_temp_cash)
                    
                    # Double check to not leave a "tiny" amount of cash behind 
                    # (e.g., if 850€ is left, just invest it all instead of trying to save 50€)
                    if (current_temp_cash - invest_amount) < config.MIN_TRADE_VOLUME:
                        invest_amount = current_temp_cash
    
                    decisions.append({
                        "aktion": "BUY",
                        "isin": best['isin'], # Make sure isin is passed into the dict in the loop
                        "name": best['ticker'],
                        "betrag_eur": invest_amount,
                        "grund": f"Trend UP + RSI {best['rsi']:.1f} (Rank {i+1})"
                    })
                    
                    print(f"   ✅ Added to execution: {best['ticker']} ({invest_amount:.2f} €)")
                    current_temp_cash -= invest_amount
                else:
                    print(f"   ⚠️ Skipping {best['ticker']}: Insufficient remaining cash ({current_temp_cash:.2f} €)")
    
    # WICHTIG: Decisions IMMER zurückgeben (enthält SELL-Aktionen aus Portfolio-Analyse)
    return decisions