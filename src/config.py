import os
from dotenv import load_dotenv

# --- PATH CONFIGURATION ---
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SRC_DIR)

# Load .env
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Credentials
MY_USERNAME = os.getenv("BOERSEN_EMAIL")
MY_PASSWORD = os.getenv("BOERSEN_PASSWORD")

# URLs
OON_LOGIN_URL = "https://www.oon-boersespiel.at/de/start.html?login=open"
OON_DEPOT_URL = "https://www.oon-boersespiel.at/de/boersespiel.html#/personal/portfolio//detail/overview"

# --- MARKET TIMING ---
# Closing Times (Local Time CET)
MARKET_CLOSE_HOUR_EU = 17
MARKET_CLOSE_MINUTE_EU = 30
MARKET_CLOSE_HOUR_US = 22
MARKET_CLOSE_MINUTE_US = 0

# SWING TRADING UPDATE:
# Wir verkaufen NICHT mehr automatisch vor Börsenschluss.
# Setze auf 0 oder -1, um EOD-Verkauf zu deaktivieren.
MINUTES_BEFORE_CLOSE_TO_SELL = 0 

# Don't buy new stocks right before close, but holding is fine
MINUTES_BEFORE_CLOSE_NO_BUY = 15 

# Settings
USER_DATA_DIR = os.path.join(PROJECT_ROOT, "google_session")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
JSON_DIR = os.path.join(PROJECT_ROOT, "json")
SESSION_LOG_FILE = os.path.join(LOG_DIR, "session_live.log")
BLACKLIST_FILE = os.path.join(JSON_DIR, "blacklist_stocks.json")

# Transaction Fees
TRANSACTION_FEE_BUY = 20.0 
TRANSACTION_FEE_SELL = 20.0

# --- DAY TRADING SPEED ---
SUCCESS_WAIT_SECONDS = 15 * 60
ERROR_WAIT_SECONDS = 5           

# --- RISK MANAGEMENT ---
MIN_TRADE_VOLUME = 6000.0  
MAX_INVEST_PER_STOCK = 11500.0 # Leicht erhöht, um aggressiver zu investieren
MIN_CASH_FOR_NEW_TRADE = 6000.0 
MAX_NEW_POSITIONS_PER_CYCLE = 3  

# --- 3-PHASE-LOOP STRATEGY ---
MAX_AI_CANDIDATES = 15         
MIN_FINAL_SCORE = 78           # Etwas toleranter für High-Risk Aktien
AI_WEIGHT = 0.5                # Balance zwischen Tech (Momentum) und AI
TECH_WEIGHT = 0.5              
PORTFOLIO_DIVERSITY = 5        # Weniger Aktien, dafür größere Positionen (Konzentration)
EARNINGS_DAYS_THRESHOLD = 1    # Nur warnen, wenn Earnings morgen sind (Risikoakzeptanz)

# --- STRATEGY SETTINGS (SWING MODE) ---
# Hard Limits - Gewinne laufen lassen!
TAKE_PROFIT_HARD_PCT = 50.0    # "The Sky is the Limit" - Kein früher Verkauf
STOP_LOSS_HARD_PCT = -5.0      # Mehr Luft zum Atmen bei Volatilität

# ATR-basiertes Risikomanagement
ATR_STOP_LOSS_MULTIPLIER = 2.0    # Weiterer Stop
ATR_TAKE_PROFIT_MULTIPLIER = 4.0  # Weiteres Ziel

# Trailing Stop Einstellungen
# Wir aktivieren den Trailing Stop erst später, um nicht bei Rauschen rauszufliegen
TRAILING_STOP_ACTIVATE_PCT = 2.5   # Erst ab 2.5% Gewinn absichern
TRAILING_STOP_LOCK_IN_PCT = 1.0    # 1% Gewinn sichern, Rest Raum geben

# Technical Indicators
RSI_PERIOD = 14                
RSI_OVERBOUGHT = 85            # Erst bei extremer Überhitzung warnen
RSI_OVERSOLD = 30       
EMA_FAST = 9                   
EMA_SLOW = 21                  

# Scoring Zones (Aggressive Momentum)
# Wir suchen Aktien, die bereits laufen (RSI > 50 ist gut!)
RSI_SWEET_SPOT_MIN = 45
RSI_SWEET_SPOT_MAX = 80 # Momentum erlauben!

# Volumen-Filter
MIN_VOLUME_RATIO = 1.1  

# AI Studio URL
AI_STUDIO_URL = "https://aistudio.google.com/app/prompts/new_chat"

# --- TEST MODE ---
TEST_MODE = False  
TEST_ORDERS = []