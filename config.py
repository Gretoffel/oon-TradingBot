import os
from dotenv import load_dotenv

# Environment Variablen laden
load_dotenv()

# Zugangsdaten
MY_USERNAME = os.getenv("BOERSEN_EMAIL")
MY_PASSWORD = os.getenv("BOERSEN_PASSWORD")

# URLs
OON_LOGIN_URL = "https://www.oon-boersespiel.at/de/start.html?login=open"
OON_DEPOT_URL = "https://www.oon-boersespiel.at/de/boersespiel.html#/personal/portfolio//detail/overview"
AI_STUDIO_URL = "https://aistudio.google.com/app/prompts/new_chat"

# Settings
USER_DATA_DIR = "./google_session"
LOG_DIR = "./logs"                # <--- NEU: Ordner für Logfiles
SUCCESS_WAIT_SECONDS = 5 * 60    # 10 Minuten
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