import re
import json
import os
import pandas as pd # Needed for DataFrame
from datetime import datetime
import config 

def clean_amount(text):
    """Wandelt Text wie '1.200,50' in float um."""
    if not text: return 0.0
    cleaned = re.sub(r'[^\d,.-]', '', text)
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace('.', '')
    cleaned = cleaned.replace(',', '.')
    try: return float(cleaned)
    except: return 0.0

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

def log_success(action, name, isin, amount, price, reason):
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
            f"QTY: {amount:<5} | "
            f"PRICE_EST: {price:<8} | "
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

def get_todays_log_dataframe():
    """Liest das Logfile und wandelt es in ein Pandas DataFrame um (für Dashboard)."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    filename = os.path.join(config.LOG_DIR, f"log_{today_str}.txt")
    
    if not os.path.exists(filename):
        return pd.DataFrame()

    data = []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                # Parse using regex matching the format in log_success
                # Format: [Time] ACTION: ... | NAME: ... | ...
                try:
                    # Simple string splitting is more robust if separators are unique
                    parts = line.split("|")
                    
                    # Extract Time and Action from first part
                    first_part = parts[0].strip()
                    time_val = first_part[1:9] # Extract HH:MM:SS
                    action_val = first_part.split("ACTION:")[1].strip()
                    
                    name_val = parts[1].split("NAME:")[1].strip()
                    isin_val = parts[2].split("ISIN:")[1].strip()
                    qty_val = parts[3].split("QTY:")[1].strip()
                    price_val = parts[4].split("PRICE_EST:")[1].strip()
                    reason_val = parts[5].split("REASON:")[1].strip()
                    
                    data.append({
                        "Uhrzeit": time_val,
                        "Aktion": action_val,
                        "Name": name_val,
                        "ISIN": isin_val,
                        "Menge": qty_val,
                        "Kurs (ca.)": price_val,
                        "Grund": reason_val
                    })
                except:
                    continue # Skip malformed lines
                    
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error parsing log to DF: {e}")
        return pd.DataFrame()