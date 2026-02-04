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

# Settings
USER_DATA_DIR = os.path.join(PROJECT_ROOT, "google_session")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
JSON_DIR = os.path.join(PROJECT_ROOT, "json")
SESSION_LOG_FILE = os.path.join(LOG_DIR, "session_live.log")
BLACKLIST_FILE = os.path.join(JSON_DIR, "blacklist_stocks.json")

# Transaction Fees
TRANSACTION_FEE_BUY = 20.0
TRANSACTION_FEE_SELL = 0.0

# --- DAY TRADING SPEED ---
# Increased frequency for better entry/exit
SUCCESS_WAIT_SECONDS = 15      
ERROR_WAIT_SECONDS = 5           

# --- RISK MANAGEMENT ---
MIN_TRADE_VOLUME = 6000.0  
MAX_INVEST_PER_STOCK = 10000.0 # Reduced slightly to allow diversification
MIN_CASH_FOR_NEW_TRADE = 6000.0 
MAX_NEW_POSITIONS_PER_CYCLE = 3  # <--- NEW: Don't over-diversify in one go

# --- STRATEGY SETTINGS ---
# Hard Limits (Safety Net - Fallback wenn keine ATR-Daten)
TAKE_PROFIT_HARD_PCT = 2.5    # Absolute exit if it flies (Targeting smaller, quicker moves)
STOP_LOSS_HARD_PCT = -2.0     # Tighter stop loss to prevent big losses

# ATR-basiertes Risikomanagement
ATR_STOP_LOSS_MULTIPLIER = 1.5    # Stop-Loss = Entry - (ATR × 1.5)
ATR_TAKE_PROFIT_MULTIPLIER = 2.5  # Take-Profit = Entry + (ATR × 2.5)

# Trailing Stop Einstellungen
TRAILING_STOP_ACTIVATE_PCT = 0.8   # Aktiviere Trailing Stop früher (ab +0.8%)
TRAILING_STOP_LOCK_IN_PCT = 0.3    # Lock-in 0.3% unter aktuellem Gewinn

# Technical Indicators
RSI_PERIOD = 14
RSI_OVERBOUGHT = 75     # Sell zone
RSI_OVERSOLD = 30       # (Reference)
RSI_BUY_MIN = 45        # Catch trends earlier (was 50)
RSI_BUY_MAX = 70        # Don't buy if already peaked

# Volumen-Filter
MIN_VOLUME_RATIO = 1.2  # Kaufe nur wenn Volumen >= 120% des Durchschnitts

# --- TEST MODE ---
TEST_MODE = False  
TEST_ORDERS = []