import re
import json
import os
import glob # <--- NEU
import pandas as pd
from datetime import datetime
import config 

def clean_amount(text):
    """Wandelt Text wie '1.200,50' in float um."""
    if not text: return 0.0
    cleaned = re.sub(r'[^\d,.-]', '', str(text)) # str() cast für Sicherheit
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
            f"QTY: {str(amount):<5} | "
            f"PRICE_EST: {str(price):<8} | "
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

    # Alle log_YYYY-MM-DD.txt Dateien finden, neueste zuerst
    files = sorted(glob.glob(os.path.join(config.LOG_DIR, "log_*.txt")), reverse=True)

    for filepath in files:
        try:
            filename = os.path.basename(filepath)
            # Datum aus Dateiname extrahieren (log_2024-05-20.txt -> 2024-05-20)
            date_part = filename.replace("log_", "").replace(".txt", "")
            
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Zeilen rückwärts lesen (Neueste Aktion oben)
            for line in reversed(lines):
                if "ACTION:" not in line: continue
                
                parts = line.split("|")
                if not parts: continue

                # Teil 0: "[12:00:00] ACTION: BUY"
                part0 = parts[0].strip()
                time_match = re.search(r'\[(.*?)\]', part0)
                time_str = time_match.group(1) if time_match else "00:00:00"
                
                action = "UNKNOWN"
                if "ACTION:" in part0:
                    action = part0.split("ACTION:")[1].strip()
                
                entry = {
                    "Datum": date_part,
                    "Zeit": time_str,
                    "Aktion": action,
                    "Name": "N/A",
                    "ISIN": "N/A",
                    "Menge": 0,
                    "Preis": 0.0,
                    "Grund": ""
                }

                # Restliche Teile parsen
                for p in parts[1:]:
                    p = p.strip()
                    if p.startswith("NAME:"): entry["Name"] = p.replace("NAME:", "").strip()
                    elif p.startswith("ISIN:"): entry["ISIN"] = p.replace("ISIN:", "").strip()
                    elif p.startswith("QTY:"): entry["Menge"] = clean_amount(p.replace("QTY:", ""))
                    elif p.startswith("PRICE_EST:"): entry["Preis"] = clean_amount(p.replace("PRICE_EST:", ""))
                    elif p.startswith("REASON:"): entry["Grund"] = p.replace("REASON:", "").strip()
                
                history.append(entry)

        except Exception as e:
            print(f"Fehler beim Parsen von {filepath}: {e}")
            continue
            
    return history