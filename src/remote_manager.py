import json
import os
import time
from collections import deque
from config import JSON_DIR, SESSION_LOG_FILE

# Define paths inside the json folder
STATE_FILE = os.path.join(JSON_DIR, "bot_state.json")
CONTROL_FILE = os.path.join(JSON_DIR, "bot_control.json")

def _ensure_json_dir():
    if not os.path.exists(JSON_DIR):
        os.makedirs(JSON_DIR)

def update_status(phase, details="", balance=0.0):
    """Schreibt den aktuellen Status des Bots in eine Datei."""
    _ensure_json_dir()
    data = {
        "timestamp": time.time(),
        "phase": phase,
        "details": details,
        "balance": balance,
        "is_alive": True
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"⚠️ Remote Fehler (Write): {e}")

def get_command():
    if not os.path.exists(CONTROL_FILE):
        return "run"
    try:
        with open(CONTROL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("command", "run")
    except:
        return "run"

def set_command(command):
    _ensure_json_dir()
    with open(CONTROL_FILE, "w", encoding="utf-8") as f:
        json.dump({"command": command}, f)

def get_state():
    if not os.path.exists(STATE_FILE):
        return {"phase": "Offline", "details": "Warte auf Start...", "balance": 0, "timestamp": 0}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"phase": "Fehler", "details": "Lesefehler", "balance": 0}

def get_live_logs(lines=50):
    """Liest die letzten N Zeilen des Live-Logs effizient aus."""
    if not os.path.exists(SESSION_LOG_FILE):
        return "Warte auf Log-Daten..."
    
    try:
        # deque mit maxlen behält nur die letzten N Elemente
        with open(SESSION_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            last_lines = deque(f, maxlen=lines)
        return "".join(last_lines)
    except Exception as e:
        return f"Fehler beim Lesen des Logs: {e}"