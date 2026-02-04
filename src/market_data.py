import yfinance as yf
import pandas as pd
import numpy as np
import config

# Expanded Ticker List for better opportunities
TICKER_MAPPING = {
    # ATX Prime (Liquid)
    "AT0000652011": "EBS.VI", "AT0000743059": "OMV.VI", "AT0000937503": "VOE.VI",
    "AT0000746409": "VER.VI", "AT0000606306": "RBI.VI", "AT0000831706": "WIE.VI",
    "AT0000730007": "ANDR.VI", "AT0000BAWAG2": "BG.VI",
    # US Tech (High Volatility)
    "US67066G1040": "NVDA", "US88160R1014": "TSLA", "US0231351067": "AMZN",
    "US0378331005": "AAPL", "US5949181045": "MSFT", "US0079031078": "AMD",
    "US30303M1027": "META", 
    # DAX movers
    "DE0007030009": "RHM.DE", "DE0007164600": "SAP.DE", "DE0007664039": "VOW3.DE"
}

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
                
                momentum_pct = ((current_price - prev_price) / prev_price) * 100
                isin = isin_map.get(ticker)
                
                # Trend Logic
                trend = "NEUTRAL"
                if current_price > current_ema_long: trend = "UP"
                elif current_price < current_ema_long: trend = "DOWN"

                if isin and not np.isnan(current_price):
                    results[isin] = {
                        "ticker": ticker,
                        "isin": isin, # <--- CRITICAL: passed back for execution
                        "price": current_price,
                        "rsi": current_rsi if not np.isnan(current_rsi) else 50,
                        "ema_9": current_ema_short,
                        "ema_20": current_ema_long,
                        "momentum": momentum_pct,
                        "trend": trend
                    }
            except Exception:
                continue
                
    except Exception as e:
        print(f"⚠️ Yahoo API Critical Error: {e}")
        
    return results