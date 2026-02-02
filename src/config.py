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
AI_STUDIO_URL = "https://aistudio.google.com/app/prompts/new_chat"

# Settings
USER_DATA_DIR = os.path.join(PROJECT_ROOT, "google_session")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
JSON_DIR = os.path.join(PROJECT_ROOT, "json")

# NEW: File to store live console output for the dashboard
SESSION_LOG_FILE = os.path.join(LOG_DIR, "session_live.log")

SUCCESS_WAIT_SECONDS = 15 * 60    
ERROR_WAIT_SECONDS = 10           

# --- TEST MODE ---
TEST_MODE = False  

TEST_ORDERS = [
    {
        "aktion": "SELL",
        "name": "Palantir Technologies Inc",
        "isin": "US69608A1088",
        "betrag_eur": 985,
        "grund": "Manueller Testlauf für selling"
    }
]