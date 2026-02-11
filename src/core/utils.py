import re
import json
import os
import glob # <--- NEU
import pandas as pd
from datetime import datetime
from core import config

def clean_amount(text):
    """Wandelt Text wie '1.200,50' in float um."""
    if not text: return 0.0
    cleaned = re.sub(r'[^\d,.-]', '', str(text)) # str() cast für Sicherheit
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace('.', '')
    cleaned = cleaned.replace(',', '.')
    try: return float(cleaned)
    except: return 0.0

def calculate_fee(amount_eur):
    """
    Berechnet die Transaktionsgebühren nach OÖN-Börsespiel-Regeln:
    - 0,25 % vom Transaktionswert
    - Mindestspesen: 17 Euro
    - Zusätzlich 3 Euro pro Order
    """
    if amount_eur <= 0: return 0.0
    
    base_fee = max(17.0, amount_eur * 0.0025)
    total_fee = base_fee + 3.0
    return total_fee

def extract_json_list(text):
    """Extrahiert eine JSON-Liste aus einem Textblock."""
    if not text: return None
    try:
        text = text.replace('```json', '').replace('```', '')
        text = re.sub(r'\[\d+\]', '', text) 
        start = text.find('[')
        end = text.rfind(']')
        if start == -1 or end == -1: return None
        return json.loads(text[start : end + 1])
    except: return None

def print_analysis_summary(decisions):
    """Gibt eine Zusammenfassung der KI-Entscheidungen aus."""
    print("\n" + "="*40)
    print("📋 ZUSAMMENFASSUNG DER KI-ANALYSE")
    print("="*40)

    if not decisions:
        print("🤷‍♂️ Die KI hat keine Aktionen empfohlen (HOLD Strategie).")
        return

    print(f"💡 Es wurden {len(decisions)} Aktionen vorgeschlagen:\n")

    for i, trade in enumerate(decisions, 1):
        action = trade.get("aktion", "UNKNOWN").upper()
        name = trade.get("name", "Unbekannt")
        reason = trade.get("grund", "Keine Begründung angegeben.")
        
        if action == "BUY":
            isin = trade.get("isin", "N/A")
            amount = trade.get("betrag_eur", 0)
            print(f"{i}. 🟢 KAUFEN: {name}")
            print(f"    ├─ ISIN:   {isin}")
            print(f"    ├─ Budget: {amount} €")
            print(f"    └─ Grund:  {reason}")
            
        elif action == "SELL":
            print(f"{i}. 🔴 VERKAUFEN: {name}")
            print(f"    └─ Grund:  {reason}")
        
        else:
            print(f"{i}. ⚪ {action}: {name} ({reason})")
            
        print("-" * 40)

def log_success(action, name, isin, amount, price, reason, profit=None):
    """Schreibt erfolgreiche Aktionen in eine Tages-Logdatei."""
    try:
        if not os.path.exists(config.LOG_DIR):
            os.makedirs(config.LOG_DIR)
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        filename = os.path.join(config.LOG_DIR, f"log_{today_str}.txt")
        time_str = datetime.now().strftime("%H:%M:%S")
        
        # Consistent separator for easy parsing
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
            
        print(f"   📝 Log-Eintrag gespeichert in {filename}")
        
    except Exception as e:
        print(f"   ⚠️ Fehler beim Schreiben des Logs: {e}")

def get_todays_log_content():
    """Liest den reinen Text-Inhalt des heutigen Logfiles (für KI)."""
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        filename = os.path.join(config.LOG_DIR, f"log_{today_str}.txt")
        
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            return content if content else "Keine Transaktionen heute."
        return "Keine Transaktionen heute."
    except Exception as e:
        return f"Fehler beim Lesen des Logs: {e}"

# --- NEU: HISTORY PARSER ---


def get_transaction_history():
    """Liest alle Log-Dateien und parst die Transaktionen in eine Liste."""
    history = []
    
    if not os.path.exists(config.LOG_DIR):
        return history

    files = sorted(glob.glob(os.path.join(config.LOG_DIR, "log_*.txt")), reverse=True)

    for filepath in files:
        try:
            filename = os.path.basename(filepath)
            date_part = filename.replace("log_", "").replace(".txt", "")
            
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            for line in reversed(lines):
                if "ACTION:" not in line: continue
                
                parts = line.split("|")
                # More robust splitting
                entry = {
                    "Datum": date_part,
                    "Zeit": "00:00",
                    "Aktion": "UNKNOWN",
                    "Name": "N/A",
                    "ISIN": "N/A",
                    "Menge": 0,
                    "Preis": 0.0,
                    "Profit": "N/A",
                    "Grund": ""
                }
                
                try:
                    # Safe parsing
                    entry["Zeit"] = parts[0].split("]")[0].replace("[", "").strip()
                    entry["Aktion"] = parts[0].split("ACTION:")[1].strip()
                    
                    for p in parts[1:]:
                        if "NAME:" in p: entry["Name"] = p.split("NAME:")[1].strip()
                        elif "ISIN:" in p: entry["ISIN"] = p.split("ISIN:")[1].strip()
                        elif "QTY:" in p: entry["Menge"] = clean_amount(p.split("QTY:")[1])
                        elif "PRICE_EST:" in p: entry["Preis"] = clean_amount(p.split("PRICE_EST:")[1])
                        elif "PROFIT:" in p: 
                            raw_profit = p.split("PROFIT:")[1].strip()
                            if raw_profit != "N/A":
                                entry["Profit"] = f"{float(raw_profit):+.2f} €"
                            else:
                                entry["Profit"] = "-"
                        elif "REASON:" in p: entry["Grund"] = p.split("REASON:")[1].strip()
                    
                    history.append(entry)
                except:
                    continue # Skip broken lines

        except Exception as e:
            continue
            
            
    return history

# --- BLACKLIST MANAGER ---

def load_blacklist():
    """Lädt die Liste der blockierten Aktien (Ticker/ISIN)."""
    if not os.path.exists(config.BLACKLIST_FILE):
        return []
    
    try:
        with open(config.BLACKLIST_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Falls es ein Dict ist (altes Format?), Liste extrahieren oder leer
            if isinstance(data, list): return data
            return []
    except Exception as e:
        print(f"⚠️ Fehler beim Laden der Blacklist: {e}")
        return []

def save_blacklist(data):
    """Speichert die Blacklist."""
    try:
        if not os.path.exists(config.JSON_DIR):
            os.makedirs(config.JSON_DIR)
            
        with open(config.BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"⚠️ Fehler beim Speichern der Blacklist: {e}")

def add_to_blacklist(identifier, reason="Not Tradeable"):
    """Fügt eine Aktie (Ticker oder ISIN) der Blacklist hinzu."""
    if not identifier or identifier == "N/A": return
    
    current_list = load_blacklist()
    
    # Check if already exists (by identifier)
    exists = any(item['id'] == identifier for item in current_list)
    
    if not exists:
        entry = {
            "id": identifier,
            "reason": reason,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        current_list.append(entry)
        save_blacklist(current_list)
        print(f"🚫 BLACKLIST: {identifier} wurde hinzugefügt ({reason}).")
    else:
        print(f"ℹ️ {identifier} ist bereits auf der Blacklist.")