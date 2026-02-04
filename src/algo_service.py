import config
from datetime import datetime
from market_data import get_market_snapshot, TICKER_MAPPING

def is_market_open(ticker):
    """
    Prüft anhand der Uhrzeit (Systemzeit CET), 
    ob die entsprechende Börse geöffnet ist.
    """
    now = datetime.now()
    minutes_since_midnight = now.hour * 60 + now.minute
    
    # 1. WIEN (.VI) & DEUTSCHLAND (.DE) -> 09:00 (540) bis 17:30 (1050)
    if ticker.endswith(".VI") or ticker.endswith(".DE"):
        return 540 <= minutes_since_midnight <= 1050
        
    # 2. USA (ohne Suffix) -> 15:30 (930) bis 22:00 (1320)
    if "." not in ticker:
        return 930 <= minutes_since_midnight <= 1320
        
    return True

def calculate_algo_decisions(depot_data):
    """
    Analysiert das Depot und Marktdaten.
    Berechnet die ECHTE Performance basierend auf Yahoo-Live-Daten,
    um die 15min Verzögerung des Spiels zu umgehen.
    """
    print("\n🧮 Starte algorithmische Analyse (Real-Time PnL)...")
    
    decisions = []
    market_data = get_market_snapshot() # Live Daten von Yahoo
    
    if not market_data:
        print("⚠️ Keine Marktdaten. Abbruch.")
        return []

    # ----------------------------------------------------
    # A. VERKAUFS-LOGIK (Stop Loss & Take Profit mit LIVE DATEN)
    # ----------------------------------------------------
    
    pending_sell_names = [o['name'] for o in depot_data['open_orders'] if o['type'] == 'SELL']
    
    # Mapping umkehren: Name/Ticker -> ISIN finden für Depot-Abgleich
    # Wir brauchen einen Weg, vom Depot-Eintrag zum Yahoo-Ticker zu kommen
    # Da das Spiel oft keine ISIN im Bestand anzeigt, matchen wir über den Namen/Ticker-Teil
    
    for stock in depot_data['stocks']:
        stock_name = stock["name"]
        qty = stock["qty"]
        current_value_game = stock["value_eur"] # Verzögerter Wert aus dem Spiel
        
        # Check: Läuft schon Verkauf?
        is_already_selling = any(p_name in stock_name or stock_name in p_name for p_name in pending_sell_names)
        if is_already_selling:
            continue
            
        # 1. Kaufpreis rekonstruieren (Reverse Engineering aus Spiel-Daten)
        # Formel: BuyPrice = CurrentValue / (1 + Perf/100) / Qty
        buy_price_per_share = 0.0
        try:
            raw_perf = stock.get("performance_since_buy", "0")
            game_perf_pct = float(raw_perf.replace("%", "").replace(",", ".").replace("+", "").strip())
            
            if qty > 0 and current_value_game > 0:
                total_buy_cost = current_value_game / (1 + (game_perf_pct / 100.0))
                buy_price_per_share = total_buy_cost / qty
        except:
            pass # Fallback, falls Berechnung scheitert

        # 2. Live Kurs finden
        live_price = 0.0
        ticker_symbol = "Unknown"
        
        # Wir suchen im market_data dictionary nach einem passenden Ticker
        # Wir matchen: Ist der Ticker-Name (z.B. "VOE") im Spiel-Namen enthalten?
        matched_isin = None
        for isin, data in market_data.items():
            simple_ticker = data['ticker'].split(".")[0] # "VOE.VI" -> "VOE"
            if simple_ticker in stock_name or stock_name in data['ticker']:
                live_price = data['current_price']
                ticker_symbol = data['ticker']
                matched_isin = isin
                break
        
        # 3. Echte Performance berechnen
        real_perf_pct = 0.0
        used_source = "GAME (Delayed)" # Default
        
        if live_price > 0 and buy_price_per_share > 0:
            # Wir haben Live Daten!
            real_perf_pct = ((live_price - buy_price_per_share) / buy_price_per_share) * 100.0
            used_source = "YAHOO (Live)"
        else:
            # Fallback auf Spiel-Daten
            real_perf_pct = game_perf_pct
        
        print(f"   📊 {stock_name:<15} | Buy: {buy_price_per_share:.2f}€ | Live: {live_price:.2f}€ | PnL: {real_perf_pct:+.2f}% [{used_source}]")

        # 4. Signale generieren
        
        # Prüfen ob Markt offen ist für diesen Ticker (nur wenn wir Ticker kennen)
        if ticker_symbol != "Unknown" and not is_market_open(ticker_symbol):
             # print(f"      Markt geschlossen für {stock_name}")
             continue

        # TAKE PROFIT
        if real_perf_pct >= config.TAKE_PROFIT_PCT:
            decisions.append({
                "aktion": "SELL",
                "name": stock_name,
                "grund": f"Take Profit ({used_source}): {real_perf_pct:.2f}% >= {config.TAKE_PROFIT_PCT}%"
            })
            continue
            
        # STOP LOSS
        if real_perf_pct <= config.STOP_LOSS_PCT:
            decisions.append({
                "aktion": "SELL",
                "name": stock_name,
                "grund": f"Stop Loss ({used_source}): {real_perf_pct:.2f}% <= {config.STOP_LOSS_PCT}%"
            })
            continue

    # ----------------------------------------------------
    # B. KAUF-LOGIK (Bleibt gleich: Momentum)
    # ----------------------------------------------------
    cash = depot_data['cash']
    pending_buy_isins = [o['isin'] for o in depot_data['open_orders'] if o['type'] == 'BUY']
    
    if cash >= config.MIN_CASH_FOR_NEW_TRADE:
        best_stock_isin = None
        best_momentum = -999.0
        
        for isin, data in market_data.items():
            ticker_name = data['ticker']
            
            if not is_market_open(ticker_name): continue
            
            mom_5m = data['momentum_5m']
            
            # Besitz-Check
            simple_ticker = ticker_name.split(".")[0]
            already_owned = any(simple_ticker in s['name'] for s in depot_data['stocks'])
            
            if already_owned or isin in pending_buy_isins: continue

            # Momentum Filter (0.3% - 3.0%)
            if 0.3 <= mom_5m <= 3.0:
                print(f"      👀 Kandidat: {ticker_name} (Momentum 5m: {mom_5m:.2f}%)")
                if mom_5m > best_momentum:
                    best_momentum = mom_5m
                    best_stock_isin = isin
        
        if best_stock_isin:
            invest_amount = min(cash, config.MAX_INVEST_PER_STOCK)
            if invest_amount >= config.MIN_TRADE_VOLUME:
                decisions.append({
                    "aktion": "BUY",
                    "isin": best_stock_isin,
                    "name": market_data[best_stock_isin]['ticker'],
                    "betrag_eur": invest_amount,
                    "grund": f"Starkes Momentum ({best_momentum:.2f}% in 5min)"
                })
    
    return decisions