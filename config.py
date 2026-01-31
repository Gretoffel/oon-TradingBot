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
SUCCESS_WAIT_SECONDS = 10 * 60    # 20 Minuten
ERROR_WAIT_SECONDS = 10           # 10 Sekunden

# --- TEST MODUS KONFIGURATION ---
TEST_MODE = False  

TEST_ORDERS = [
    {
        "aktion": "SELL",
        "name": "Microsoft",
        "isin": "US5949181045",
        "betrag_eur": 355,
        "grund": "Manueller Testlauf für selling"
    }
]