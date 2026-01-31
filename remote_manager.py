# remote_manager.py
import json
import os
import time

STATE_FILE = "bot_state.json"
CONTROL_FILE = "bot_control.json"

def update_status(phase, details="", balance=0.0):
    """Schreibt den aktuellen Status des Bots in eine Datei."""
    data = {
        "timestamp": time.time(),
        "phase": phase,          # z.B. "Login", "Analysiere", "Schlafe"
        "details": details,      # z.B. "Kaufe Apple", "Warte 10min"
        "balance": balance,
        "is_alive": True
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"⚠️ Remote Fehler (Write): {e}")

def get_command():
    """Liest Befehle vom Dashboard (run/stop)."""
    if not os.path.exists(CONTROL_FILE):
        return "run"
    try:
        with open(CONTROL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("command", "run")
    except:
        return "run"

def set_command(command):
    """Wird vom Dashboard genutzt, um Befehle zu senden."""
    with open(CONTROL_FILE, "w", encoding="utf-8") as f:
        json.dump({"command": command}, f)

def get_state():
    """Wird vom Dashboard genutzt, um den Status zu lesen."""
    if not os.path.exists(STATE_FILE):
        return {"phase": "Offline", "details": "Keine Daten", "balance": 0, "timestamp": 0}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"phase": "Fehler", "details": "Lesefehler", "balance": 0}