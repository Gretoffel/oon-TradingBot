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

# --- DAY TRADING SPEED ---
# Increased frequency for better entry/exit
SUCCESS_WAIT_SECONDS = 20      
ERROR_WAIT_SECONDS = 10           

# --- RISK MANAGEMENT ---
MIN_TRADE_VOLUME = 6000.0  
MAX_INVEST_PER_STOCK = 10000.0 # Reduced slightly to allow diversification
MIN_CASH_FOR_NEW_TRADE = 6000.0 
MAX_NEW_POSITIONS_PER_CYCLE = 3  # <--- NEW: Don't over-diversify in one go

# --- STRATEGY SETTINGS ---
# Hard Limits (Safety Net)
TAKE_PROFIT_HARD_PCT = 3.0    # Absolute exit if it flies
STOP_LOSS_HARD_PCT = -1.5     # Absolute exit if it crashes

# Technical Indicators
RSI_PERIOD = 14
RSI_OVERBOUGHT = 75     # Sell zone
RSI_OVERSOLD = 30       # (Reference)
RSI_BUY_MIN = 50        # Momentum must be positive
RSI_BUY_MAX = 70        # Don't buy if already peaked

# --- TEST MODE ---
TEST_MODE = False  
TEST_ORDERS = []