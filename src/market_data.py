import yfinance as yf
import pandas as pd
import numpy as np
import config

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
    """Calculates Volume Weighted Average Price - wichtig für Day-Trading."""
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
    return vwap

def calculate_atr(df, period=14):
    """Calculates Average True Range - Volatilitätsindikator für dynamisches Risikomanagement."""
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def get_market_snapshot():
    tickers = list(TICKER_MAPPING.values())
    isin_map = {v: k for k, v in TICKER_MAPPING.items()}
    results = {}
    
    try:
        # Request 5 days of 2-minute interval data
        data = yf.download(tickers, period="5d", interval="2m", progress=False, group_by='ticker')
        
        for ticker in tickers:
            try:
                # Handle single vs multi-index dataframe structure
                df = data[ticker] if len(tickers) > 1 else data
                df = df.dropna(how='all').ffill()
                
                if df.empty or len(df) < 20: 
                    continue
                
                prices = df['Close']
                current_price = float(prices.iloc[-1])
                prev_price = float(prices.iloc[-2])
                
                # Indicators
                rsi_series = calculate_rsi(prices, config.RSI_PERIOD)
                current_rsi = float(rsi_series.iloc[-1])
                
                ema_short = calculate_ema(prices, 9)
                ema_long = calculate_ema(prices, 20)
                
                current_ema_short = float(ema_short.iloc[-1])
                current_ema_long = float(ema_long.iloc[-1])
                
                # NEU: VWAP berechnen
                vwap_series = calculate_vwap(df)
                current_vwap = float(vwap_series.iloc[-1]) if not np.isnan(vwap_series.iloc[-1]) else current_price
                
                # NEU: ATR berechnen
                atr_series = calculate_atr(df, 14)
                current_atr = float(atr_series.iloc[-1]) if not np.isnan(atr_series.iloc[-1]) else 0.0
                
                # NEU: Volume Ratio (aktuelles Volumen / 20-Perioden-Durchschnitt)
                volume_avg = df['Volume'].rolling(20).mean().iloc[-1]
                current_volume = df['Volume'].iloc[-1]
                volume_ratio = float(current_volume / volume_avg) if volume_avg > 0 else 1.0
                
                momentum_pct = ((current_price - prev_price) / prev_price) * 100
                isin = isin_map.get(ticker)
                
                # Trend Logic
                trend = "NEUTRAL"
                if current_price > current_ema_long: trend = "UP"
                elif current_price < current_ema_long: trend = "DOWN"

                if isin and not np.isnan(current_price):
                    results[isin] = {
                        "ticker": ticker,
                        "isin": isin,
                        "price": current_price,
                        "rsi": current_rsi if not np.isnan(current_rsi) else 50,
                        "ema_9": current_ema_short,
                        "ema_20": current_ema_long,
                        "vwap": current_vwap,           # NEU
                        "atr": current_atr,             # NEU
                        "volume_ratio": volume_ratio,   # NEU
                        "momentum": momentum_pct,
                        "trend": trend
                    }
            except Exception:
                continue
                
    except Exception as e:
        print(f"⚠️ Yahoo API Critical Error: {e}")
        
    return results