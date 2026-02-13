import os
import glob
from datetime import datetime
from core import config
from core.parsing import clean_amount


def log_success(action, name, isin, amount, price, reason, profit=None):
    """Append a successful trade to today's log file."""
    try:
        if not os.path.exists(config.LOG_DIR):
            os.makedirs(config.LOG_DIR)

        today_str = datetime.now().strftime("%Y-%m-%d")
        filename = os.path.join(config.LOG_DIR, f"log_{today_str}.txt")
        time_str = datetime.now().strftime("%H:%M:%S")

        log_line = (
            f"[{time_str}] "
            f"ACTION: {action:<4} | "
            f"NAME: {name:<20} | "
            f"ISIN: {isin:<12} | "
            f"QTY: {str(amount):<5} | "
            f"PRICE_EST: {str(price):<8} | "
            f"PROFIT: {profit if profit is not None else 'N/A'} | "
            f"REASON: {reason}\n"
        )

        with open(filename, "a", encoding="utf-8") as f:
            f.write(log_line)

        print(f"   Log entry saved to {filename}")

    except Exception as e:
        print(f"   Warning: Failed to write log: {e}")


def get_todays_log_content():
    """Read today's log file content as plain text (for AI context)."""
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        filename = os.path.join(config.LOG_DIR, f"log_{today_str}.txt")

        if not os.path.exists(filename):
            return "No transactions today."

        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()

        return content if content else "No transactions today."
    except Exception as e:
        return f"Error reading log: {e}"


def _find_log_files():
    """Return log file paths sorted by date (newest first)."""
    if not os.path.exists(config.LOG_DIR):
        return []
    return sorted(glob.glob(os.path.join(config.LOG_DIR, "log_*.txt")), reverse=True)


def _parse_log_line(line):
    """Parse a single structured log line into a dict. Returns None on failure."""
    if "ACTION:" not in line:
        return None

    parts = line.split("|")

    entry = {
        "date": "0000-00-00",
        "time": "00:00",
        "action": "UNKNOWN",
        "name": "N/A",
        "isin": "N/A",
        "quantity": 0,
        "price": 0.0,
        "profit": "N/A",
        "reason": "",
    }

    try:
        entry["time"] = parts[0].split("]")[0].replace("[", "").strip()
        entry["action"] = parts[0].split("ACTION:")[1].strip()

        for part in parts[1:]:
            if "NAME:" in part:
                entry["name"] = part.split("NAME:")[1].strip()
            elif "ISIN:" in part:
                entry["isin"] = part.split("ISIN:")[1].strip()
            elif "QTY:" in part:
                entry["quantity"] = clean_amount(part.split("QTY:")[1])
            elif "PRICE_EST:" in part:
                entry["price"] = clean_amount(part.split("PRICE_EST:")[1])
            elif "PROFIT:" in part:
                raw_profit = part.split("PROFIT:")[1].strip()
                entry["profit"] = f"{float(raw_profit):+.2f} \u20ac" if raw_profit != "N/A" else "-"
            elif "REASON:" in part:
                entry["reason"] = part.split("REASON:")[1].strip()

        return entry
    except Exception:
        return None


def get_transaction_history():
    """Read all log files and parse transactions into a list of dicts."""
    history = []

    for filepath in _find_log_files():
        date_part = os.path.basename(filepath).replace("log_", "").replace(".txt", "")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            continue

        for line in reversed(lines):
            entry = _parse_log_line(line)
            if entry is None:
                continue
            entry["date"] = date_part
            history.append(entry)

    return history


def print_analysis_summary(decisions):
    """Print a formatted summary of AI trading decisions to stdout."""
    print("\n" + "=" * 40)
    print("AI ANALYSIS SUMMARY")
    print("=" * 40)

    if not decisions:
        print("No actions recommended (HOLD strategy).")
        return

    print(f"{len(decisions)} action(s) proposed:\n")

    for i, trade in enumerate(decisions, 1):
        action = trade.get("aktion", "UNKNOWN").upper()
        name = trade.get("name", "Unknown")
        reason = trade.get("grund", "No reason given.")

        if action == "BUY":
            isin = trade.get("isin", "N/A")
            amount = trade.get("betrag_eur", 0)
            print(f"{i}. BUY: {name}")
            print(f"    ISIN:   {isin}")
            print(f"    Budget: {amount} EUR")
            print(f"    Reason: {reason}")

        elif action == "SELL":
            print(f"{i}. SELL: {name}")
            print(f"    Reason: {reason}")

        else:
            print(f"{i}. {action}: {name} ({reason})")

        print("-" * 40)
