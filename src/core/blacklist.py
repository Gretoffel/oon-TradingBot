import json
import os
from datetime import datetime
from core import config


def load_blacklist():
    """Load the list of blocked stocks (ticker/ISIN) from JSON."""
    if not os.path.exists(config.BLACKLIST_FILE):
        return []

    try:
        with open(config.BLACKLIST_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        print(f"Warning: Failed to load blacklist: {e}")
        return []


def save_blacklist(data):
    """Persist the blacklist to disk."""
    try:
        if not os.path.exists(config.JSON_DIR):
            os.makedirs(config.JSON_DIR)

        with open(config.BLACKLIST_FILE, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        print(f"Warning: Failed to save blacklist: {e}")


def add_to_blacklist(identifier, reason="Not Tradeable"):
    """Add a stock (ticker or ISIN) to the blacklist if not already present."""
    if not identifier or identifier == "N/A":
        return

    current_list = load_blacklist()

    already_exists = any(item['id'] == identifier for item in current_list)
    if already_exists:
        print(f"Info: {identifier} is already on the blacklist.")
        return

    entry = {
        "id": identifier,
        "reason": reason,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    current_list.append(entry)
    save_blacklist(current_list)
    print(f"BLACKLIST: {identifier} added ({reason}).")
