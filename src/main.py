import asyncio
import traceback
import subprocess
import sys
import time
import os
from bot import run_bot_cycle
from config import CHECK_INTERVAL_SECONDS, AI_CYCLE_INTERVAL_SECONDS, SESSION_LOG_FILE, LOG_DIR, ERROR_WAIT_SECONDS
import remote_manager

# --- LOGGER SETUP ---
class DualLogger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.filename = filename
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
            pass 

    def flush(self):
        self.terminal.flush()

sys.stdout = DualLogger(SESSION_LOG_FILE)
sys.stderr = sys.stdout 
# --------------------

async def smart_sleep(seconds):
    """
    Schläft X Sekunden, prüft aber auf Stop-Befehl.
    """
    for i in range(seconds):
        cmd = remote_manager.get_command()
        if cmd == "stop":
            remote_manager.update_status("Pausiert", "Benutzer hat gestoppt.")
            print("\n🛑 PAUSE DURCH BENUTZER.")
            return False 
        
        # Nur alle 10 Sek Log update, sonst Spam
        if i % 10 == 0: 
            remote_manager.update_status("Warten", f"Nächster Check in {seconds - i}s")
            
        await asyncio.sleep(1)
    return True 

async def main_loop():
    print("🚀 SUPERVISOR GESTARTET (SMART INTERVAL)")
    print(f"   ⏱️ Quick Check (Sell): Alle {CHECK_INTERVAL_SECONDS} Sek.")
    print(f"   🧠 Full Check (Buy):   Alle {AI_CYCLE_INTERVAL_SECONDS/60:.0f} Min.")
    
    last_ai_run = 0
    
    while True:
        try:
            cmd = remote_manager.get_command()
            if cmd == "stop":
                print("💤 Bot ist pausiert...")
                remote_manager.update_status("Pausiert", "Warte auf Start...")
                await asyncio.sleep(5)
                continue

            # Entscheiden ob Full Run oder Quick Run
            now = time.time()
            is_full_run = (now - last_ai_run) >= AI_CYCLE_INTERVAL_SECONDS
            
            # Bot starten
            await run_bot_cycle(full_analysis=is_full_run)
            
            # Timer updaten wenn Full Run war
            if is_full_run:
                last_ai_run = time.time()
                print(f"💤 Full Cycle fertig. Schlafe {CHECK_INTERVAL_SECONDS}s bis Quick Check...")
            else:
                print(f"💤 Quick Check fertig. Schlafe {CHECK_INTERVAL_SECONDS}s...")

            # Kurze Pause (Default 60s)
            completed = await smart_sleep(CHECK_INTERVAL_SECONDS)
            if not completed: continue
            
        except KeyboardInterrupt:
            print("\n🛑 Beendet.")
            break
            
        except Exception as e:
            print(f"\n❌ KRITISCHER ABSTURZ: {e}")
            traceback.print_exc()
            remote_manager.update_status("Fehler", f"Absturz: {str(e)}")
            print(f"🔄 Starte neu in {ERROR_WAIT_SECONDS} Sekunden...")
            await asyncio.sleep(ERROR_WAIT_SECONDS)

if __name__ == "__main__":
    dashboard_process = None
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dashboard_script = os.path.join(current_dir, "dashboard.py")
    
    try:
        print("🖥️ Starte Dashboard...")
        dashboard_process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", dashboard_script, "--browser.gatherUsageStats", "false", "--server.headless", "true", "--theme.base", "dark"]
        )
        time.sleep(3)
        asyncio.run(main_loop())

    except KeyboardInterrupt:
        print("\n👋 Beende Hauptprogramm...")
    finally:
        if dashboard_process:
            dashboard_process.terminate()
            try: dashboard_process.wait(timeout=3)
            except: dashboard_process.kill()