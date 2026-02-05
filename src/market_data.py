import yfinance as yf
import pandas as pd
import numpy as np
import config
from utils import load_blacklist

# AGGRESSIVE TICKER LIST (High Beta / Momentum / Hype)
TICKER_MAPPING = {
    # --- US HIGH BETA & CRYPTO PROXIES (Volatility is King) ---
    "US5949721065": "MSTR",  # MicroStrategy (Bitcoin Proxy)
    "US19260Q1076": "COIN",  # Coinbase
    "US5657881067": "MARA",  # Marathon Digital
    "US7672921050": "RIOT",  # Riot Platforms
    "US15135B1017": "CLSK",  # CleanSpark
    "US83406F1021": "SOFI",  # SoFi Technologies
    "US67066G1040": "NVDA",  # Nvidia (Muss bleiben)
    "US88160R1014": "TSLA",  # Tesla (Muss bleiben)
    "US0378331005": "AAPL",  # Apple
    "US5949181045": "MSFT",  # Microsoft
    "US0079031078": "AMD",   # AMD
    "US69608A1088": "PLTR",  # Palantir (AI Hype)
    "US89400J1079": "TPL",   # Tesla Proxy / Tech
    "US09075V1026": "BNTX",  # BioNTech (Volatil)
    "US60770K1079": "MRNA",  # Moderna
    "US72919P2020": "PLUG",  # Plug Power (Wasserstoff Hype)
    "US29355A1079": "ENPH",  # Enphase Energy

    # --- US Big Tech ---
    "US0231351067": "AMZN",
    "US30303M1027": "META",
    "US02079K3059": "GOOGL",
    "US22788C1053": "CRWD",
    "US11135F1012": "AVGO",
    "US64110L1061": "NFLX",

    # --- ATX Prime (Österreich - Pflichtprogramm, aber selektiv) ---
    "AT0000652011": "EBS.VI", 
    "AT0000743059": "OMV.VI", 
    "AT0000937503": "VOE.VI",
    "AT0000746409": "VER.VI", 
    "AT0000606306": "RBI.VI", 
    "AT0000730007": "ANDR.VI", 
    "AT0000BAWAG2": "BG.VI",

    # --- DAX 40 (Momentum Picks) ---
    "DE0007030009": "RHM.DE",  # Rheinmetall (Defense Hype)
    "DE0007164600": "SAP.DE",  
    "DE0007236101": "SIE.DE",  # Siemens
    "DE0006231004": "IFX.DE",  # Infineon
}

# Fallback-Mapping: Wenn ISIN nicht gescannt wird, suche nach dem Namen
NAME_TO_ISIN_FALLBACK = {
    "microstrategy": "US5949721065",
    "coinbase": "US19260Q1076",
    "marathon": "US5657881067",
    "riot": "US7672921050",
    "nvidia": "US67066G1040",
    "tesla": "US88160R1014",
    "palantir": "US69608A1088",
    "plug power": "US72919P2020",
    "rheinmetall": "DE0007030009",
    "amazon": "US0231351067",
    "apple": "US0378331005",
    "microsoft": "US5949181045",
    "meta": "US30303M1027",
    "google": "US02079K3059",
    "amd": "US0079031078",
    "erste group": "AT0000652011",
    "omv": "AT0000743059",
    "voestalpine": "AT0000937503",
    "verbund": "AT0000746409",
    "raiffeisen": "AT0000606306",
}

def get_isin_by_name(name: str) -> str | None:
    name_lower = name.lower()
    for keyword, isin in NAME_TO_ISIN_FALLBACK.items():
        if keyword in name_lower:
            return isin
    return None

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def calculate_vwap(df):
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    volume = df['Volume']
    temp_df = pd.DataFrame({'tp': typical_price, 'vol': volume})
    temp_df['vol_price'] = temp_df['tp'] * temp_df['vol']
    try:
        grouped = temp_df.groupby(temp_df.index.date)
        vwap = grouped['vol_price'].cumsum() / grouped['vol'].cumsum()
        return vwap
    except:
        return typical_price

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def is_market_open(ticker):
    from datetime import datetime
    now = datetime.now()
    if now.weekday() >= 5: return False 
    
    minutes = now.hour * 60 + now.minute
    
    if any(ticker.endswith(ext) for ext in [".VI", ".DE", ".AS", ".PA"]):
        return 540 <= minutes <= 1055 
    if "." not in ticker or ticker.endswith(".US"):
        return 930 <= minutes <= 1320
    return True

def get_minutes_until_close(ticker):
    from datetime import datetime
    now = datetime.now()
    minutes_now = now.hour * 60 + now.minute
    
    if any(ticker.endswith(ext) for ext in [".VI", ".DE", ".AS", ".PA"]):
        close_mins = config.MARKET_CLOSE_HOUR_EU * 60 + config.MARKET_CLOSE_MINUTE_EU
    else:
        close_mins = config.MARKET_CLOSE_HOUR_US * 60 + config.MARKET_CLOSE_MINUTE_US
        
    remaining = close_mins - minutes_now
    return remaining

def calculate_technical_score(data):
    """
    Calculates a technical score tailored for SWING/MOMENTUM trading.
    High RSI is now rewarded (Strong Trend) instead of punished, 
    unless it's extremely overbought (>85).
    """
    score = 0
    rsi = data.get('rsi', 50)
    price = data.get('price', 0)
    ema_fast = data.get('ema_fast', 0)
    ema_slow = data.get('ema_slow', 0)
    vol_ratio = data.get('volume_ratio', 1.0)

    # 1. RSI Score - MOMENTUM Logic
    # 50-70 is the sweet spot for entry in strong trends
    # 70-80 is still good momentum
    # > 85 is danger zone
    if 50 <= rsi <= 80:
        score += 40
    elif 40 <= rsi < 50:
        score += 20 # Recovery zone
    elif rsi > 80:
        score += 10 # Caution, but strong momentum
    
    # 2. Trend Score (Price vs EMAs)
    if price > ema_slow:
        score += 30
    if price > ema_fast:
        score += 10
    
    # 3. EMA Cross (Golden Cross Logic approx)
    if ema_fast > ema_slow:
        score += 10
        
    # 4. Volume Score
    if vol_ratio >= config.MIN_VOLUME_RATIO:
        score += 10
        
    return score

def get_market_snapshot(portfolio_isins=None):
    all_isins = set(TICKER_MAPPING.keys())
    if portfolio_isins:
        all_isins.update(portfolio_isins)
        
    tickers = []
    isin_map = {}
    for isin in all_isins:
        ticker = TICKER_MAPPING.get(isin)
        if not ticker: continue
        tickers.append(ticker)
        isin_map[ticker] = isin
    
    results = {}
    blacklist = load_blacklist()
    blacklisted_ids = set()
    for e in blacklist:
        if 'id' in e: blacklisted_ids.add(e['id'])
        if 'name' in e: blacklisted_ids.add(e['name'])
    
    try:
        # Request 10 days data
        data = yf.download(tickers, period="10d", interval="5m", progress=False, group_by='ticker')
        
        for ticker in tickers:
            isin = isin_map.get(ticker)
            
            if isin in blacklisted_ids or ticker in blacklisted_ids: continue
            if not is_market_open(ticker): continue
            
            # EOD Buy Protection - still relevant for buying, but we removed forced selling
            mins_left = get_minutes_until_close(ticker)
            if mins_left <= config.MINUTES_BEFORE_CLOSE_NO_BUY:
                continue

            try:
                df = data[ticker] if len(tickers) > 1 else data
                df = df.dropna(how='all').ffill()
                if df.empty or len(df) < 30: continue
                
                prices = df['Close']
                current_price = float(prices.iloc[-1])
                prev_price = float(prices.iloc[-2])
                
                rsi_series = calculate_rsi(prices, config.RSI_PERIOD)
                current_rsi = float(rsi_series.iloc[-1])
                
                ema_fast = calculate_ema(prices, config.EMA_FAST)
                ema_slow = calculate_ema(prices, config.EMA_SLOW)
                current_ema_fast = float(ema_fast.iloc[-1])
                current_ema_slow = float(ema_slow.iloc[-1])
                
                vwap_series = calculate_vwap(df)
                current_vwap = float(vwap_series.iloc[-1]) if not np.isnan(vwap_series.iloc[-1]) else current_price
                
                atr_series = calculate_atr(df, 14)
                current_atr = float(atr_series.iloc[-1]) if not np.isnan(atr_series.iloc[-1]) else 0.0
                
                volume_avg = df['Volume'].rolling(20).mean().iloc[-1]
                current_volume = df['Volume'].iloc[-1]
                volume_ratio = float(current_volume / volume_avg) if volume_avg > 0 else 1.0
                
                momentum_pct = ((current_price - prev_price) / prev_price) * 100
                
                trend = "NEUTRAL"
                if current_price > current_ema_slow: trend = "UP"
                elif current_price < current_ema_slow: trend = "DOWN"

                if isin and not np.isnan(current_price):
                    stock_data = {
                        "ticker": ticker,
                        "isin": isin,
                        "price": current_price,
                        "rsi": current_rsi if not np.isnan(current_rsi) else 50,
                        "ema_fast": current_ema_fast,
                        "ema_slow": current_ema_slow,
                        "vwap": current_vwap,
                        "atr": current_atr,
                        "volume_ratio": volume_ratio,
                        "momentum": momentum_pct,
                        "trend": trend
                    }
                    stock_data["tech_score"] = calculate_technical_score(stock_data)
                    results[isin] = stock_data
                    
            except Exception: continue
                
    except Exception as e:
        print(f"⚠️ Yahoo API Error: {e}")
        
    sorted_results = dict(sorted(results.items(), key=lambda item: item[1]['tech_score'], reverse=True))
    
    if sorted_results:
        print("\n" + "="*80)
        print(f"🔭 MARKET SCAN (SWING MODE) | {len(sorted_results)} Stocks tracked")
        print(f"{'TICKER':<10} | {'PRICE':<8} | {'RSI':<5} | {'SCORE':<5} | {'TREND':<7} | {'STATUS'}")
        print("-" * 80)
        for isin, data in list(sorted_results.items())[:15]: 
            ticker = data['ticker']
            price = data['price']
            rsi = data['rsi']
            score = data['tech_score']
            trend = data['trend']
            status = "🚀 MOMENTUM" if score >= 80 else "⏳ WATCH"
            print(f"{ticker:<10} | {price:<8.2f} | {rsi:<5.1f} | {score:<5} | {trend:<7} | {status}")
        print("="*80 + "\n")
    else:
        print("⚠️ No valid market data found in scan.")
        
    return sorted_results