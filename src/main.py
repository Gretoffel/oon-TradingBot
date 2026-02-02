import asyncio
import traceback
import subprocess
import sys
import time
import os
from bot import run_bot_cycle
from config import SUCCESS_WAIT_SECONDS, ERROR_WAIT_SECONDS, SESSION_LOG_FILE, LOG_DIR
import remote_manager

# --- LOGGER SETUP ---
class DualLogger:
    """
    Schreibt stdout/stderr sowohl in das Terminal als auch in eine Datei,
    damit das Dashboard die 'print'-Ausgaben live mitlesen kann.
    """
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.filename = filename
        # Datei leeren beim Start
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write(f"--- LOG START: {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")

    def write(self, message):
        try:
            self.terminal.write(message)
            with open(self.filename, "a", encoding="utf-8") as log:
                log.write(message)
        except Exception:
            pass # Fallback, falls Logging crasht

    def flush(self):
        self.terminal.flush()

# Redirect Output
sys.stdout = DualLogger(SESSION_LOG_FILE)
sys.stderr = sys.stdout 
# --------------------

async def smart_sleep(seconds):
    """
    Schläft für die angegebene Zeit, prüft aber jede Sekunde, 
    ob ein STOP-Befehl vom Dashboard vorliegt.
    """
    for i in range(seconds):
        cmd = remote_manager.get_command()
        if cmd == "stop":
            remote_manager.update_status("Pausiert", "Benutzer hat gestoppt (Wartezeit abgebrochen)")
            print("\n🛑 PAUSE DURCH BENUTZER ERKANNT.")
            return False 
        
        remaining = seconds - i
        if i % 10 == 0: 
            remote_manager.update_status("Warten", f"Nächster Zyklus in {int(remaining/60)} min")
            
        await asyncio.sleep(1)
    return True 

async def main_loop():
    print("🚀 SUPERVISOR GESTARTET")
    print("Drücke STRG+C zum Beenden (Dashboard wird mit beendet).")
    
    while True:
        try:
            cmd = remote_manager.get_command()
            if cmd == "stop":
                print("💤 Bot ist pausiert (Warte auf 'Start' via Dashboard)...")
                remote_manager.update_status("Pausiert", "Warte auf Start-Befehl...")
                await asyncio.sleep(5)
                continue

            remote_manager.update_status("Aktiv", "Zyklus startet...")
            await run_bot_cycle()
            
            print(f"💤 Alles glatt gelaufen. Schlafe {SUCCESS_WAIT_SECONDS/60} Minuten...")
            completed = await smart_sleep(SUCCESS_WAIT_SECONDS)
            
            if not completed:
                continue
            
        except KeyboardInterrupt:
            print("\n🛑 Programm vom Benutzer beendet.")
            break
            
        except Exception as e:
            print("\n" + "!"*40)
            print(f"❌ KRITISCHER ABSTURZ: {e}")
            print("Traceback:")
            traceback.print_exc()
            print("!"*40)
            
            remote_manager.update_status("Fehler", f"Absturz: {str(e)}")
            print(f"🔄 Starte neu in {ERROR_WAIT_SECONDS} Sekunden...")
            await asyncio.sleep(ERROR_WAIT_SECONDS)

if __name__ == "__main__":
    dashboard_process = None
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dashboard_script = os.path.join(current_dir, "dashboard.py")
    
    try:
        print("🖥️ Starte Dashboard im Hintergrund...")
        # Startet Streamlit als separaten Prozess
        dashboard_process = subprocess.Popen(
            [
                sys.executable, 
                "-m", 
                "streamlit", 
                "run", 
                dashboard_script, 
                "--browser.gatherUsageStats", "false",
                "--server.headless", "true",
                "--theme.base", "dark" 
            ]
        )
        
        time.sleep(3)
        asyncio.run(main_loop())

    except KeyboardInterrupt:
        print("\n👋 Beende Hauptprogramm...")
    finally:
        if dashboard_process:
            print("🛑 Beende Dashboard-Prozess...")
            dashboard_process.terminate()
            try:
                dashboard_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                dashboard_process.kill()
            print("✅ Alles beendet.")