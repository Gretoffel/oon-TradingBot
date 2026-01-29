import re
import json
import os
from datetime import datetime
import config # Import config für LOG_DIR

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
        text = text.replace('[]', '') 
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
        # Ordner erstellen, falls nicht existiert
        if not os.path.exists(config.LOG_DIR):
            os.makedirs(config.LOG_DIR)
        
        # Dateiname: log_2026-01-29.txt
        today_str = datetime.now().strftime("%Y-%m-%d")
        filename = os.path.join(config.LOG_DIR, f"log_{today_str}.txt")
        
        # Zeitstempel für den Eintrag
        time_str = datetime.now().strftime("%H:%M:%S")
        
        # Formatierung der Zeile
        # Zeit | Action | Name | ISIN | Menge/Betrag | Kurs | Grund
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