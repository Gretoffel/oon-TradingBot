import asyncio
import traceback
import subprocess
import sys
import time
from bot import run_bot_cycle
from config import SUCCESS_WAIT_SECONDS, ERROR_WAIT_SECONDS
import remote_manager

async def smart_sleep(seconds):
    """
    Schläft für die angegebene Zeit, prüft aber jede Sekunde, 
    ob ein STOP-Befehl vom Dashboard vorliegt.
    """
    for i in range(seconds):
        # 1. Prüfe Command
        cmd = remote_manager.get_command()
        if cmd == "stop":
            remote_manager.update_status("Pausiert", "Benutzer hat gestoppt (Wartezeit abgebrochen)")
            print("\n🛑 PAUSE DURCH BENUTZER ERKANNT.")
            return False # Sleep abgebrochen
        
        # 2. Status Update (Countdown)
        # Wir aktualisieren den Status nur alle 10 Sekunden, um die Festplatte zu schonen
        remaining = seconds - i
        if i % 10 == 0: 
            remote_manager.update_status("Warten", f"Nächster Zyklus in {int(remaining/60)} min")
            
        await asyncio.sleep(1)
    
    return True # Sleep regulär beendet

async def main_loop():
    print("🚀 SUPERVISOR GESTARTET")
    print("Drücke STRG+C zum Beenden (Dashboard wird mit beendet).")
    
    while True:
        try:
            # --- SCHRITT A: PRÜFE OB GESTOPPT ---
            cmd = remote_manager.get_command()
            if cmd == "stop":
                print("💤 Bot ist pausiert (Warte auf 'Start' via Dashboard)...")
                remote_manager.update_status("Pausiert", "Warte auf Start-Befehl...")
                await asyncio.sleep(5)
                continue

            # --- SCHRITT B: STARTE BOT ZYKLUS ---
            # Status wird innerhalb von bot.py noch detaillierter gesetzt
            remote_manager.update_status("Aktiv", "Zyklus startet...")
            
            await run_bot_cycle()
            
            # --- SCHRITT C: WARTEZEIT (SMART SLEEP) ---
            print(f"💤 Alles glatt gelaufen. Schlafe {SUCCESS_WAIT_SECONDS/60} Minuten...")
            
            # Nutze Smart Sleep statt normalem sleep
            completed = await smart_sleep(SUCCESS_WAIT_SECONDS)
            
            if not completed:
                # Wenn smart_sleep False zurückgibt, wurde gestoppt -> Schleife neu starten
                continue
            
        except KeyboardInterrupt:
            print("\n🛑 Programm vom Benutzer beendet.")
            break
            
        except Exception as e:
            # Bei Crash (beliebiger Fehler)
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
    
    try:
        print("🖥️ Starte Dashboard im Hintergrund...")
        # Startet Streamlit als separaten Prozess
        # sys.executable garantiert, dass das gleiche Python (venv) genutzt wird
        dashboard_process = subprocess.Popen(
    [
        sys.executable, 
        "-m", 
        "streamlit", 
        "run", 
        "dashboard.py", 
        "--browser.gatherUsageStats", "false",  # Überspringt die E-Mail/Statistik Abfrage
        "--server.headless", "true"             # Verhindert, dass automatisch ein Browser am PC aufgeht
    ]
)
        
        # Kurze Wartezeit, damit Streamlit hochfahren kann
        time.sleep(3)
        
        # Starte den Haupt-Loop
        asyncio.run(main_loop())

    except KeyboardInterrupt:
        print("\n👋 Beende Hauptprogramm...")
    finally:
        # Aufräumen: Dashboard-Prozess beenden, wenn main.py beendet wird
        if dashboard_process:
            print("🛑 Beende Dashboard-Prozess...")
            dashboard_process.terminate()
            try:
                dashboard_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                dashboard_process.kill()
            print("✅ Alles beendet.")