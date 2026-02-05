import yfinance as yf
import pandas as pd
import numpy as np
import config
from utils import load_blacklist

# Expanded Ticker List for better opportunities
TICKER_MAPPING = {
    # --- ATX Prime (Österreich) ---
    "AT0000652011": "EBS.VI", "AT0000743059": "OMV.VI", "AT0000937503": "VOE.VI",
    "AT0000746409": "VER.VI", "AT0000606306": "RBI.VI", "AT0000831706": "WIE.VI",
    "AT0000730007": "ANDR.VI", "AT0000BAWAG2": "BG.VI",

    # --- US Tech & Growth (High Volatility) ---
    "US67066G1040": "NVDA",  "US88160R1014": "TSLA",  "US0231351067": "AMZN",
    "US0378331005": "AAPL",  "US5949181045": "MSFT",  "US0079031078": "AMD",
    "US30303M1027": "META",  "US22788C1053": "CRWD",  "US69608A1088": "PLTR",
    "US11135F1012": "AVGO",  "US5951121038": "MU",    "US02079K3059": "GOOGL",
    "US4581401001": "INTC",  "US70450Y1038": "PYPL",  "US64110L1061": "NFLX",
    "US1912161007": "KO",    "US0846707026": "BRK-B", "US92826C8394": "V",
    "US46625H1005": "JPM",   "US5801351017": "MCD",   "US2546871060": "DIS",
    "US60770K1079": "MRNA",  "US7170811035": "PFE",   "US8825081040": "TXN",
    "US7475251036": "QCOM",                           # Qualcomm
    "US90353T1007": "U",     # Unity Software
    "US09075V1026": "BNTX",  # Biontech
    
    # --- DAX 40 (Deutschland) ---
    "DE0007030009": "RHM.DE",  # Rheinmetall
    "DE0007164600": "SAP.DE",  
    "DE0007664039": "VOW3.DE", # VW
    "DE0007236101": "SIE.DE",  # Siemens
    "DE0008404005": "ALV.DE",  # Allianz
    "DE0007100000": "MBG.DE",  # Mercedes
    "DE0005557508": "DTE.DE",  # Telekom
    "DE0005190003": "BMW.DE",
    "DE000BASF111": "BAS.DE",  # BASF
    "DE000A1EWWW0": "ADS.DE",  # Adidas
    "DE0006231004": "IFX.DE",  # Infineon
    "DE000ENAG999": "EOAN.DE", # E.ON
    
    # --- Euro Stoxx 50 / Europa ---
    "NL0000388619": "UNA.AS", # Unilever (Amsterdam)
    "FR0000120271": "TTE.PA", # TotalEnergies (Paris)
    "NL0010273215": "ASML.AS",# ASML (Amsterdam)
    "FR0000121014": "MC.PA",  # LVMH (Paris)
    "FR0000052292": "RMS.PA", # Hermes (Paris)
}

# Fallback-Mapping: Wenn ISIN nicht gescannt wird, suche nach dem Namen
# Schlüsselwörter aus dem Aktiennamen -> ISIN
NAME_TO_ISIN_FALLBACK = {
    # US Tech
    "amazon": "US0231351067",
    "apple": "US0378331005",
    "nvidia": "US67066G1040",
    "microsoft": "US5949181045",
    "meta": "US30303M1027",
    "facebook": "US30303M1027",
    "alphabet": "US02079K3059",
    "google": "US02079K3059",
    "amd": "US0079031078",
    "advanced micro": "US0079031078",
    "tesla": "US88160R1014",
    "crowdstrike": "US22788C1053",
    "palantir": "US69608A1088",
    "broadcom": "US11135F1012",
    "micron": "US5951121038",
    "netflix": "US64110L1061",
    "paypal": "US70450Y1038",
    "intel": "US4581401001",
    "disney": "US2546871060",
    "coca-cola": "US1912161007",
    "coca cola": "US1912161007",
    "berkshire": "US0846707026",
    "visa": "US92826C8394",
    # ATX
    "erste group": "AT0000652011",
    "omv": "AT0000743059",
    "voestalpine": "AT0000937503",
    "verbund": "AT0000746409",
    "raiffeisen": "AT0000606306",
    "wienerberger": "AT0000831706",
    "andritz": "AT0000730007",
    "bawag": "AT0000BAWAG2",
    # DAX / Europa
    "rheinmetall": "DE0007030009",
    "sap": "DE0007164600",
    "volkswagen": "DE0007664039",
    "vw": "DE0007664039",
    "siemens": "DE0007236101",
    "allianz": "DE0008404005",
    "mercedes": "DE0007100000",
    "daimler": "DE0007100000",
    "telekom": "DE0005557508",
    "deutsche telekom": "DE0005557508",
    "bmw": "DE0005190003",
    "basf": "DE000BASF111",
    "adidas": "DE000A1EWWW0",
    "infineon": "DE0006231004",
    "e.on": "DE000ENAG999",
    "eon": "DE000ENAG999",
    "asml": "NL0010273215",
    "lvmh": "FR0000121014",
    "louis vuitton": "FR0000121014",
}

def get_isin_by_name(name: str) -> str | None:
    """Findet ISIN anhand des Aktiennamens (Fuzzy-Match)."""
    name_lower = name.lower()
    for keyword, isin in NAME_TO_ISIN_FALLBACK.items():
        if keyword in name_lower:
            return isin
    return None

def calculate_rsi(series, period=14):
    """Calculates Relative Strength Index."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_ema(series, span):
    """Calculates Exponential Moving Average."""
    return series.ewm(span=span, adjust=False).mean()

def calculate_vwap(df):
    """Calculates Volume Weighted Average Price - Resets Daily."""
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    volume = df['Volume']
    
    # Helper DataFrame for calculation
    temp_df = pd.DataFrame({'tp': typical_price, 'vol': volume})
    temp_df['vol_price'] = temp_df['tp'] * temp_df['vol']
    
    # Group by Day (Index Date) and calc cumulative sum per day
    # Assuming df.index is DatetimeIndex
    try:
        grouped = temp_df.groupby(temp_df.index.date)
        vwap = grouped['vol_price'].cumsum() / grouped['vol'].cumsum()
        return vwap
    except Exception as e:
        # Fallback if index isn't datetime or other error
        print(f"VWAP Error: {e}")
        return typical_price # Fallback to typical price

def calculate_atr(df, period=14):
    """Calculates Average True Range - Volatilitätsindikator für dynamisches Risikomanagement."""
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def is_market_open(ticker):
    """Checks market hours (CET)."""
    from datetime import datetime
    now = datetime.now()
    if now.weekday() >= 5: return False # Weekend
    
    minutes = now.hour * 60 + now.minute
    
    # EU Markets (DAX, ATX, Amsterdam, Paris) (09:00 - 17:35 CET)
    if any(ticker.endswith(ext) for ext in [".VI", ".DE", ".AS", ".PA"]):
        return 540 <= minutes <= 1055 
        
    # US Market (15:30 - 22:00 CET)
    if "." not in ticker or ticker.endswith(".US"):
        return 930 <= minutes <= 1320
        
    return True

def get_minutes_until_close(ticker):
    """Returns minutes remaining until market close (EU or US)."""
    from datetime import datetime
    now = datetime.now()
    minutes_now = now.hour * 60 + now.minute
    
    # Determine Market
    if any(ticker.endswith(ext) for ext in [".VI", ".DE", ".AS", ".PA"]):
        # EU Market Close
        close_mins = config.MARKET_CLOSE_HOUR_EU * 60 + config.MARKET_CLOSE_MINUTE_EU
    else:
        # US Market Close
        close_mins = config.MARKET_CLOSE_HOUR_US * 60 + config.MARKET_CLOSE_MINUTE_US
        
    remaining = close_mins - minutes_now
    return remaining

def calculate_technical_score(data):
    """
    Calculates a technical score from 0 to 100 based on RSI, Trend, and Volume.
    Logic:
    - RSI Sweet Spot (40-60): 30 points
    - Trend (Price > EMA21): 40 points
    - Momentum (Price > EMA9): 20 points
    - Volume (> 120% Avg): 10 points
    """
    score = 0
    rsi = data.get('rsi', 50)
    price = data.get('price', 0)
    ema_fast = data.get('ema_fast', 0)
    ema_slow = data.get('ema_slow', 0)
    vol_ratio = data.get('volume_ratio', 1.0)

    # 1. RSI Score
    if config.RSI_SWEET_SPOT_MIN <= rsi <= config.RSI_SWEET_SPOT_MAX:
        score += 30
    elif rsi < config.RSI_SWEET_SPOT_MIN:
        score += 15 # Oversold is okay, but not "sweet spot"
    
    # 2. Trend Score (EMA Slow)
    if price > ema_slow:
        score += 40
    
    # 3. Momentum Score (EMA Fast)
    if price > ema_fast:
        score += 20
        
    # 4. Volume Score
    if vol_ratio >= config.MIN_VOLUME_RATIO:
        score += 10
        
    return score

def get_market_snapshot(portfolio_isins=None):
    # Combine fixed list with portfolio stocks that might not be in our default list
    all_isins = set(TICKER_MAPPING.keys())
    if portfolio_isins:
        all_isins.update(portfolio_isins)
        
    tickers = []
    isin_map = {}
    for isin in all_isins:
        ticker = TICKER_MAPPING.get(isin)
        if not ticker:
            # Try to resolve by ISIN directly if not in mapping?
            # Actually, yfinance works better with tickers. 
            # We already have NAME_TO_ISIN_FALLBACK, but here we need ISIN -> Ticker.
            # If it's a known ISIN from portfolio scan, it might have been resolved before.
            continue
        tickers.append(ticker)
        isin_map[ticker] = isin
    
    results = {}
    
    # Load Blacklist
    blacklist = load_blacklist()
    blacklisted_ids = set()
    for e in blacklist:
        if 'id' in e: blacklisted_ids.add(e['id'])
        if 'name' in e: blacklisted_ids.add(e['name'])
    
    try:
        # Request 10 days of 5-minute interval data
        data = yf.download(tickers, period="10d", interval="5m", progress=False, group_by='ticker')
        
        for ticker in tickers:
            isin = isin_map.get(ticker)
            
            # --- FILTERING ---
            # 1. Blacklist Check
            if isin in blacklisted_ids or ticker in blacklisted_ids:
                continue
            
            # 2. Market Hours Check
            if not is_market_open(ticker):
                continue
            
            # 3. EOD Buy/Sell Protection (Don't scan if close too close)
            mins_left = get_minutes_until_close(ticker)
            if mins_left <= config.MINUTES_BEFORE_CLOSE_NO_BUY:
                # We still might want to scan if we OWN it for emergency sells, 
                # but Phase 1 AI defense usually handles that.
                # For Phase 2 FUNNEL, we definitely don't want it.
                continue

            try:
                # Handle single vs multi-index dataframe structure
                df = data[ticker] if len(tickers) > 1 else data
                df = df.dropna(how='all').ffill()
                
                if df.empty or len(df) < 30: 
                    continue
                
                prices = df['Close']
                current_price = float(prices.iloc[-1])
                prev_price = float(prices.iloc[-2])
                
                # Indicators
                rsi_series = calculate_rsi(prices, config.RSI_PERIOD)
                current_rsi = float(rsi_series.iloc[-1])
                
                ema_fast = calculate_ema(prices, config.EMA_FAST)
                ema_slow = calculate_ema(prices, config.EMA_SLOW)
                
                current_ema_fast = float(ema_fast.iloc[-1])
                current_ema_slow = float(ema_slow.iloc[-1])
                
                # VWAP
                vwap_series = calculate_vwap(df)
                current_vwap = float(vwap_series.iloc[-1]) if not np.isnan(vwap_series.iloc[-1]) else current_price
                
                # ATR
                atr_series = calculate_atr(df, 14)
                current_atr = float(atr_series.iloc[-1]) if not np.isnan(atr_series.iloc[-1]) else 0.0
                
                # Volume Ratio
                volume_avg = df['Volume'].rolling(20).mean().iloc[-1]
                current_volume = df['Volume'].iloc[-1]
                volume_ratio = float(current_volume / volume_avg) if volume_avg > 0 else 1.0
                
                momentum_pct = ((current_price - prev_price) / prev_price) * 100
                isin = isin_map.get(ticker)
                
                # Trend Logic
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
                    # Calculate Technical Score
                    stock_data["tech_score"] = calculate_technical_score(stock_data)
                    results[isin] = stock_data
                    
            except Exception:
                continue
                
    except Exception as e:
        print(f"⚠️ Yahoo API Critical Error: {e}")
        
    # Sort results by tech_score descending
    sorted_results = dict(sorted(results.items(), key=lambda item: item[1]['tech_score'], reverse=True))
    
    # --- NEW: CONSOLE SUMMARY ---
    if sorted_results:
        print("\n" + "="*80)
        print(f"🔭 MARKET SCAN SUMMARY | {len(sorted_results)} Stocks tracked")
        print(f"{'TICKER':<10} | {'PRICE':<8} | {'RSI':<5} | {'SCORE':<5} | {'TREND':<7} | {'STATUS'}")
        print("-" * 80)
        for isin, data in list(sorted_results.items())[:15]: # Show top 15
            ticker = data['ticker']
            price = data['price']
            rsi = data['rsi']
            score = data['tech_score']
            trend = data['trend']
            status = "✅ POTENTIAL" if score >= 80 else "⏳ WATCH"
            print(f"{ticker:<10} | {price:<8.2f} | {rsi:<5.1f} | {score:<5} | {trend:<7} | {status}")
        print("="*80 + "\n")
    else:
        print("⚠️ No valid market data found in scan.")
        
    return sorted_results
