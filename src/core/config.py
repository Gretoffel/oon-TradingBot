import os
import json
import yaml
from dotenv import load_dotenv

# --- PATH CONFIGURATION ---
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(SRC_DIR)

# Load .env
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Credentials (from .env)
MY_USERNAME = os.getenv("BOERSEN_EMAIL")
MY_PASSWORD = os.getenv("BOERSEN_PASSWORD")

# Directories
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
JSON_DIR = os.path.join(PROJECT_ROOT, "json")
USER_DATA_DIR = os.path.join(PROJECT_ROOT, "google_session")
SESSION_LOG_FILE = os.path.join(LOG_DIR, "session_live.log")
BLACKLIST_FILE = os.path.join(JSON_DIR, "blacklist_stocks.json")
AI_CONFIG_FILE = os.path.join(CONFIG_DIR, "ai_config.json")

# --- Load YAML config ---
_config_path = os.path.join(CONFIG_DIR, "config.yml")
with open(_config_path, "r", encoding="utf-8") as _f:
    _cfg = yaml.safe_load(_f)

# --- URLs ---
OON_LOGIN_URL = _cfg["urls"]["login"]
OON_DEPOT_URL = _cfg["urls"]["depot"]

# --- Market Timing ---
MARKET_CLOSE_HOUR_EU = _cfg["market_timing"]["close_hour_eu"]
MARKET_CLOSE_MINUTE_EU = _cfg["market_timing"]["close_minute_eu"]
MARKET_CLOSE_HOUR_US = _cfg["market_timing"]["close_hour_us"]
MARKET_CLOSE_MINUTE_US = _cfg["market_timing"]["close_minute_us"]
MINUTES_BEFORE_CLOSE_TO_SELL = _cfg["market_timing"]["minutes_before_close_to_sell"]
MINUTES_BEFORE_CLOSE_NO_BUY = _cfg["market_timing"]["minutes_before_close_no_buy"]

# --- Transaction Fees ---
TRANSACTION_FEE_BUY = _cfg["fees"]["buy"]
TRANSACTION_FEE_SELL = _cfg["fees"]["sell"]

# --- Cycle Timing ---
AI_CYCLE_INTERVAL_SECONDS = _cfg["cycle_timing"]["ai_cycle_interval_seconds"]
CHECK_INTERVAL_SECONDS = _cfg["cycle_timing"]["check_interval_seconds"]
ERROR_WAIT_SECONDS = _cfg["cycle_timing"]["error_wait_seconds"]

# --- Risk Management ---
MIN_TRADE_VOLUME = _cfg["risk_management"]["min_trade_volume"]
MAX_INVEST_PER_STOCK = _cfg["risk_management"]["max_invest_per_stock"]
MIN_CASH_FOR_NEW_TRADE = _cfg["risk_management"]["min_cash_for_new_trade"]
MAX_NEW_POSITIONS_PER_CYCLE = _cfg["risk_management"]["max_new_positions_per_cycle"]

# --- 3-Phase-Loop Strategy ---
MAX_AI_CANDIDATES = _cfg["strategy"]["max_ai_candidates"]
MIN_FINAL_SCORE = _cfg["strategy"]["min_final_score"]
AI_WEIGHT = _cfg["strategy"]["ai_weight"]
TECH_WEIGHT = _cfg["strategy"]["tech_weight"]
PORTFOLIO_DIVERSITY = _cfg["strategy"]["portfolio_diversity"]
EARNINGS_DAYS_THRESHOLD = _cfg["strategy"]["earnings_days_threshold"]

# --- Take Profit / Stop Loss ---
TAKE_PROFIT_HARD_PCT = _cfg["profit_loss"]["take_profit_hard_pct"]
STOP_LOSS_HARD_PCT = _cfg["profit_loss"]["stop_loss_hard_pct"]

# --- High Water Mark ---
HWM_TRIGGER_PCT = _cfg["high_water_mark"]["trigger_pct"]
HWM_DROP_THRESHOLD = _cfg["high_water_mark"]["drop_threshold"]

# --- ATR ---
ATR_STOP_LOSS_MULTIPLIER = _cfg["atr"]["stop_loss_multiplier"]
ATR_TAKE_PROFIT_MULTIPLIER = _cfg["atr"]["take_profit_multiplier"]

# --- Trailing Stop ---
TRAILING_STOP_ACTIVATE_PCT = _cfg["trailing_stop"]["activate_pct"]
TRAILING_STOP_LOCK_IN_PCT = _cfg["trailing_stop"]["lock_in_pct"]

# --- Technical Indicators ---
RSI_PERIOD = _cfg["technical_indicators"]["rsi_period"]
RSI_OVERBOUGHT = _cfg["technical_indicators"]["rsi_overbought"]
RSI_OVERSOLD = _cfg["technical_indicators"]["rsi_oversold"]
EMA_FAST = _cfg["technical_indicators"]["ema_fast"]
EMA_SLOW = _cfg["technical_indicators"]["ema_slow"]
RSI_SWEET_SPOT_MIN = _cfg["technical_indicators"]["rsi_sweet_spot_min"]
RSI_SWEET_SPOT_MAX = _cfg["technical_indicators"]["rsi_sweet_spot_max"]
MIN_VOLUME_RATIO = _cfg["technical_indicators"]["min_volume_ratio"]

# --- Browser ---
_browser_yml = _cfg["browser"]["show"]
BROWSER_SHOW = os.getenv("BROWSER_SHOW", str(_browser_yml)).lower() == "true"

# --- Test Mode ---
TEST_MODE = _cfg["test_mode"]["enabled"]
TEST_ORDERS = []

# --- Web Config ---
def _load_web_config():
    cfg_file = os.path.join(CONFIG_DIR, "ai_config.json")
    try:
        with open(cfg_file, "r", encoding="utf-8") as file:
            return json.load(file).get("web_config", False)
    except Exception:
        return False

WEB_CONFIG = _load_web_config()
