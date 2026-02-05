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
# AT/DE: 17:30 Continuous Trading Ends -> 17:35 Auction Ends. We set 17:30 as reference check.
# US: 22:00 Close
MARKET_CLOSE_HOUR_EU = 17
MARKET_CLOSE_MINUTE_EU = 30
MARKET_CLOSE_HOUR_US = 22
MARKET_CLOSE_MINUTE_US = 0

# Sell everything 15 mins before close to avoid auction uncertainty & stuck funds
MINUTES_BEFORE_CLOSE_TO_SELL = 15
# Don't buy new stocks if less than 20 mins to close
MINUTES_BEFORE_CLOSE_NO_BUY = 25 

# Settings
USER_DATA_DIR = os.path.join(PROJECT_ROOT, "google_session")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
JSON_DIR = os.path.join(PROJECT_ROOT, "json")
SESSION_LOG_FILE = os.path.join(LOG_DIR, "session_live.log")
BLACKLIST_FILE = os.path.join(JSON_DIR, "blacklist_stocks.json")

# Transaction Fees (deprecated, use utils.calculate_fee)
TRANSACTION_FEE_BUY = 0.0 
TRANSACTION_FEE_SELL = 0.0

# --- DAY TRADING SPEED ---
# Increased frequency for better entry/exit
SUCCESS_WAIT_SECONDS = 15 * 60
ERROR_WAIT_SECONDS = 5           

# --- RISK MANAGEMENT ---
MIN_TRADE_VOLUME = 6000.0  # High min volume needed due to ~20€+ fees
MAX_INVEST_PER_STOCK = 10000.0 # Reduced slightly to allow diversification
MIN_CASH_FOR_NEW_TRADE = 6000.0 
MAX_NEW_POSITIONS_PER_CYCLE = 3  

# --- 3-PHASE-LOOP STRATEGY ---
MAX_AI_CANDIDATES = 10         # Number of top tech stocks sent to AI
MIN_FINAL_SCORE = 75           # Threshold for BUY execution
AI_WEIGHT = 0.6                # Importance of AI Matrix
TECH_WEIGHT = 0.4              # Importance of Technical Score
PORTFOLIO_DIVERSITY = 7        # Target number of stocks in depot
EARNINGS_DAYS_THRESHOLD = 3    # Don't buy if earnings within 3 days

# --- STRATEGY SETTINGS ---
# Hard Limits (Safety Net - Fallback wenn keine ATR-Daten)
TAKE_PROFIT_HARD_PCT = 8.0    # Increased to let winners run (was 2.5)
STOP_LOSS_HARD_PCT = -2.0     # Tighter stop loss to prevent big losses

# ATR-basiertes Risikomanagement
ATR_STOP_LOSS_MULTIPLIER = 1.5    # Stop-Loss = Entry - (ATR × 1.5)
ATR_TAKE_PROFIT_MULTIPLIER = 2.5  # Take-Profit = Entry + (ATR × 2.5)

# Trailing Stop Einstellungen
TRAILING_STOP_ACTIVATE_PCT = 0.8   # Activate earlier (was 0.8), but high enough to cover fees
TRAILING_STOP_LOCK_IN_PCT = 0.3    # Lock-in 0.3% unter aktuellem Gewinn

# Technical Indicators (Refined for 5m intervals)
RSI_PERIOD = 14                # Standard Period
RSI_OVERBOUGHT = 70            # Standard Overbought
RSI_OVERSOLD = 30       
EMA_FAST = 9                   # Fast Trend
EMA_SLOW = 21                  # Slow Trend (Noise reduction)

# Scoring Neutral Zones
RSI_SWEET_SPOT_MIN = 40
RSI_SWEET_SPOT_MAX = 60

# Volumen-Filter
MIN_VOLUME_RATIO = 1.2  

# AI Studio URL
AI_STUDIO_URL = "https://aistudio.google.com/app/prompts/new_chat"

# --- TEST MODE ---
TEST_MODE = False  
TEST_ORDERS = []