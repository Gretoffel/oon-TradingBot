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
SUCCESS_WAIT_SECONDS = 60      # Jede Minute prüfen!
ERROR_WAIT_SECONDS = 10           

# --- RISK MANAGEMENT ---
# Regel: Nie unter 5k handeln wegen Gebühren (~20€). Zielgröße: 10k.
MIN_TRADE_VOLUME = 800.0  
MAX_INVEST_PER_STOCK = 10000.0
MIN_CASH_FOR_NEW_TRADE = 800.0 

# Take Profit / Stop Loss (in Prozent)
TAKE_PROFIT_PCT = 1.5   # Bei +1.5% Gewinn sofort raus
STOP_LOSS_PCT = -0.8    # Bei -0.8% Verlust Notbremse

# --- TEST MODE ---
TEST_MODE = False  
TEST_ORDERS = []