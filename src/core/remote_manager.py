import json
import os
import time
from collections import deque
from core.config import JSON_DIR, SESSION_LOG_FILE

STATE_FILE = os.path.join(JSON_DIR, "bot_state.json")
CONTROL_FILE = os.path.join(JSON_DIR, "bot_control.json")

def _ensure_json_dir():
    if not os.path.exists(JSON_DIR):
        os.makedirs(JSON_DIR)

def update_status(phase, details="", balance=0.0, portfolio=None, open_orders=None, high_water_marks=None):
    """Schreibt den aktuellen Status des Bots in eine Datei."""
    _ensure_json_dir()
    
    current_data = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                current_data = json.load(f)
        except: pass

    data = {
        "timestamp": time.time(),
        "phase": phase,
        "details": details,
        "balance": balance,
        "is_alive": True,
        "portfolio": portfolio if portfolio is not None else current_data.get("portfolio", []),
        "open_orders": open_orders if open_orders is not None else current_data.get("open_orders", []),
        # HWM behalten oder aktualisieren
        "high_water_marks": high_water_marks if high_water_marks is not None else current_data.get("high_water_marks", {})
    }
    
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"⚠️ Remote Fehler (Write): {e}")

# --- NEUE FUNKTIONEN FÜR HIGH WATER MARK ---

def get_high_water_marks():
    """Lädt nur die gespeicherten Höchststände."""
    state = get_state()
    return state.get("high_water_marks", {})

def save_high_water_marks(hwms):
    """Speichert aktualisierte Höchststände, ohne den Rest zu überschreiben."""
    _ensure_json_dir()
    current_data = get_state()
    current_data["high_water_marks"] = hwms
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(current_data, f, indent=4)
    except Exception as e:
        print(f"⚠️ Fehler beim Speichern der HWMs: {e}")

# --- Bestehende Funktionen bleiben gleich ---

def get_command():
    if not os.path.exists(CONTROL_FILE): return "run"
    try:
        with open(CONTROL_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("command", "run")
    except: return "run"

def set_command(command):
    _ensure_json_dir()
    with open(CONTROL_FILE, "w", encoding="utf-8") as f:
        json.dump({"command": command}, f)

def get_state():
    if not os.path.exists(STATE_FILE):
        return {"phase": "Offline", "details": "Warte...", "balance": 0, "portfolio": [], "high_water_marks": {}}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"phase": "Fehler", "balance": 0, "portfolio": [], "high_water_marks": {}}

def get_live_logs(lines=50):
    if not os.path.exists(SESSION_LOG_FILE): return "Warte auf Log-Daten..."
    try:
        with open(SESSION_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            last_lines = deque(f, maxlen=lines)
        return "".join(last_lines)
    except Exception as e: return f"Fehler: {e}"