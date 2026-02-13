import json
import os
import time
from collections import deque
from core.config import JSON_DIR, SESSION_LOG_FILE

STATE_FILE = os.path.join(JSON_DIR, "bot_state.json")
CONTROL_FILE = os.path.join(JSON_DIR, "bot_control.json")


def _ensure_json_dir():
    """Create the JSON directory if it does not exist."""
    if not os.path.exists(JSON_DIR):
        os.makedirs(JSON_DIR)


def _read_state_file():
    """Read and parse the state file. Returns empty dict on any failure."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_state_file(data):
    """Write data to the state file as JSON."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Warning: Failed to write state file: {e}")


def update_status(phase, details="", balance=0.0, portfolio=None, open_orders=None, high_water_marks=None):
    """Write the current bot status to disk, merging with previously persisted state."""
    _ensure_json_dir()

    current_data = _read_state_file()

    data = {
        "timestamp": time.time(),
        "phase": phase,
        "details": details,
        "balance": balance,
        "is_alive": True,
        "portfolio": portfolio if portfolio is not None else current_data.get("portfolio", []),
        "open_orders": open_orders if open_orders is not None else current_data.get("open_orders", []),
        "high_water_marks": high_water_marks if high_water_marks is not None else current_data.get("high_water_marks", {}),
    }

    _write_state_file(data)


def get_high_water_marks():
    """Load the persisted high water marks from state."""
    state = get_state()
    return state.get("high_water_marks", {})


def save_high_water_marks(hwms):
    """Update high water marks without overwriting the rest of the state."""
    _ensure_json_dir()
    current_data = get_state()
    current_data["high_water_marks"] = hwms
    _write_state_file(current_data)


def get_command():
    """Read the current control command. Defaults to 'run' if missing or corrupt."""
    if not os.path.exists(CONTROL_FILE):
        return "run"
    try:
        with open(CONTROL_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("command", "run")
    except Exception:
        return "run"


def set_command(command):
    """Write a control command to disk."""
    _ensure_json_dir()
    with open(CONTROL_FILE, "w", encoding="utf-8") as f:
        json.dump({"command": command}, f)


def get_state():
    """Read the full bot state from disk. Returns a safe default if missing or corrupt."""
    if not os.path.exists(STATE_FILE):
        return {"phase": "Offline", "details": "Waiting...", "balance": 0, "portfolio": [], "high_water_marks": {}}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"phase": "Error", "balance": 0, "portfolio": [], "high_water_marks": {}}


def get_live_logs(lines=50):
    """Read the last N lines from the session log file."""
    if not os.path.exists(SESSION_LOG_FILE):
        return "Waiting for log data..."
    try:
        with open(SESSION_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            last_lines = deque(f, maxlen=lines)
        return "".join(last_lines)
    except Exception as e:
        return f"Error: {e}"
