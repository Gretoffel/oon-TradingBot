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
# NEU: Das ist der große KI-Zyklus (Kaufen)
AI_CYCLE_INTERVAL_SECONDS = 15 * 60 
# NEU: Das ist der schnelle Sicherheits-Check (Verkaufen / Stop-Loss)
CHECK_INTERVAL_SECONDS = 60      

ERROR_WAIT_SECONDS = 5

# --- RISK MANAGEMENT ---
MIN_TRADE_VOLUME = 6000.0  
MAX_INVEST_PER_STOCK = 11500.0
MIN_CASH_FOR_NEW_TRADE = 6000.0 
MAX_NEW_POSITIONS_PER_CYCLE = 3  

# --- 3-PHASE-LOOP STRATEGY ---
MAX_AI_CANDIDATES = 15         
MIN_FINAL_SCORE = 78           
AI_WEIGHT = 0.5                
TECH_WEIGHT = 0.5              
PORTFOLIO_DIVERSITY = 5        
EARNINGS_DAYS_THRESHOLD = 1    

# --- STRATEGY SETTINGS (SWING MODE) ---
TAKE_PROFIT_HARD_PCT = 20.0    # Angepasst: Realistischeres Ziel
STOP_LOSS_HARD_PCT = -2.5      # Angepasst: Engerer Stop Loss für Sicherheit

# Break-Even Trigger (ab wann wird der Gewinn gesichert?)
BREAK_EVEN_TRIGGER_PCT = 4.0   # Wenn wir über 4% sind...
BREAK_EVEN_LOCK_PCT = 0.5      # ...darf es nicht mehr unter 0.5% fallen.

# ATR-basiertes Risikomanagement
ATR_STOP_LOSS_MULTIPLIER = 2.0    
ATR_TAKE_PROFIT_MULTIPLIER = 4.0  

# Trailing Stop Einstellungen
TRAILING_STOP_ACTIVATE_PCT = 1.0   # Früher aktivieren (schon ab 1% Gewinn)
TRAILING_STOP_LOCK_IN_PCT = 0.5    

# Technical Indicators
RSI_PERIOD = 14                
RSI_OVERBOUGHT = 85            
RSI_OVERSOLD = 30       
EMA_FAST = 9                   
EMA_SLOW = 21                  

# Scoring Zones
RSI_SWEET_SPOT_MIN = 45
RSI_SWEET_SPOT_MAX = 80 

# Volumen-Filter
MIN_VOLUME_RATIO = 1.1  

# AI Studio URL
AI_STUDIO_URL = "https://aistudio.google.com/app/prompts/new_chat"

# --- TEST MODE ---
TEST_MODE = False  
TEST_ORDERS = []