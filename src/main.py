import asyncio
import traceback
import subprocess
import sys
import time
import os
from bot import run_bot_cycle
from config import SUCCESS_WAIT_SECONDS, ERROR_WAIT_SECONDS
import remote_manager

# --- FIX FOR WINDOWS CONSOLE ENCODING ---
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
# ----------------------------------------

# ... (Previous code like smart_sleep and main_loop remains exactly the same) ...
# Copy the smart_sleep and main_loop functions from your original file here.
# I will show the critical change in the "if __name__" block below:

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
    
    # Calculate the absolute path to dashboard.py inside the src folder
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
                dashboard_script,  # <--- UPDATED PATH
                "--browser.gatherUsageStats", "false",
                "--server.headless", "true"
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