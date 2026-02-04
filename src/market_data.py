import yfinance as yf
import pandas as pd
import time

# Mapping: ISIN -> Yahoo Ticker
# Fokus auf ATX (Minütliche Ausführung) + Volatile US Techs
TICKER_MAPPING = {
    # ATX (Priorität 1)
    "AT0000652011": "EBS.VI",  # Erste Group
    "AT0000743059": "OMV.VI",  # OMV
    "AT0000937503": "VOE.VI",  # Voestalpine
    "AT0000746409": "VER.VI",  # Verbund
    "AT0000606306": "RBI.VI",  # Raiffeisen
    "AT0000831706": "WIE.VI",  # Wienerberger
    "AT0000730007": "ANDR.VI", # Andritz
    "AT0000BAWAG2": "BG.VI",   # BAWAG
    
    # US Tech / International (Nur handeln wenn starker Trend, da 15min Delay im Display)
    "US67066G1040": "NVDA",    # Nvidia
    "US88160R1014": "TSLA",    # Tesla
    "US0231351067": "AMZN",    # Amazon
    "DE0007030009": "RHM.DE",  # Rheinmetall
}

def get_market_snapshot():
    """
    Holt Live-Daten aller Ticker gleichzeitig.
    Gibt ein Dictionary zurück: {'ISIN': {'price': 100.0, 'change_5m_pct': 0.5}}
    """
    tickers = list(TICKER_MAPPING.values())
    isin_map = {v: k for k, v in TICKER_MAPPING.items()}
    
    results = {}
    
    try:
        # Download der letzten 5 Minuten (Interval 1m)
        # Wir brauchen genug Daten um die Veränderung zu berechnen
        data = yf.download(tickers, period="1d", interval="1m", progress=False, group_by='ticker')
        
        for ticker in tickers:
            try:
                # Extrahiere DataFrame für einzelnen Ticker
                df = data[ticker] if len(tickers) > 1 else data
                
                if df.empty or len(df) < 2:
                    continue
                
                # Letzter Preis (Live)
                current_price = float(df['Close'].iloc[-1])
                
                # Preis vor 5 Minuten (oder so weit zurück wie möglich)
                lookback = 5 if len(df) >= 6 else len(df) - 1
                old_price = float(df['Close'].iloc[-lookback])
                
                # Momentum berechnen
                momentum_pct = ((current_price - old_price) / old_price) * 100
                
                isin = isin_map.get(ticker)
                if isin:
                    results[isin] = {
                        "ticker": ticker,
                        "current_price": current_price,
                        "momentum_5m": momentum_pct
                    }
            except Exception as e:
                pass # Einzelner Ticker Fehler ignorieren

    except Exception as e:
        print(f"⚠️ Fehler beim Bulk-Download Yahoo: {e}")
        return {}

    return results

def get_name_by_isin(isin):
    # Einfache Rückgabe für Logging, falls Yahoo Name fehlt
    return TICKER_MAPPING.get(isin, isin)