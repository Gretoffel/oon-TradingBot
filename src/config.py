import os
from dotenv import load_dotenv

# --- PATH CONFIGURATION ---
# Get the directory where THIS file (config.py) is located (e.g., .../src)
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
# Go up one level to get the project root
PROJECT_ROOT = os.path.dirname(SRC_DIR)

# Load .env from Project Root
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Zugangsdaten
MY_USERNAME = os.getenv("BOERSEN_EMAIL")
MY_PASSWORD = os.getenv("BOERSEN_PASSWORD")

# URLs
OON_LOGIN_URL = "https://www.oon-boersespiel.at/de/start.html?login=open"
OON_DEPOT_URL = "https://www.oon-boersespiel.at/de/boersespiel.html#/personal/portfolio//detail/overview"
AI_STUDIO_URL = "https://aistudio.google.com/app/prompts/new_chat"

# Settings (Using Absolute Paths)
# These will now be created in the Project Root, not inside src
USER_DATA_DIR = os.path.join(PROJECT_ROOT, "google_session")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
JSON_DIR = os.path.join(PROJECT_ROOT, "json")

SUCCESS_WAIT_SECONDS = 15 * 60    # 5 Minuten
ERROR_WAIT_SECONDS = 10           # 10 Sekunden

# --- TEST MODUS KONFIGURATION ---
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