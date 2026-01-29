import asyncio
import traceback
from bot import run_bot_cycle
from config import SUCCESS_WAIT_SECONDS, ERROR_WAIT_SECONDS

async def main_loop():
    print("🚀 SUPERVISOR GESTARTET")
    print("Drücke STRG+C zum Beenden.")
    
    while True:
        try:
            # Starte den Bot
            await run_bot_cycle()
            
            # Wenn erfolgreich (kein Crash), warte 20 Minuten
            print(f"💤 Alles glatt gelaufen. Schlafe {SUCCESS_WAIT_SECONDS/60} Minuten...")
            await asyncio.sleep(SUCCESS_WAIT_SECONDS)
            
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
            
            print(f"🔄 Starte neu in {ERROR_WAIT_SECONDS} Sekunden...")
            await asyncio.sleep(ERROR_WAIT_SECONDS)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass