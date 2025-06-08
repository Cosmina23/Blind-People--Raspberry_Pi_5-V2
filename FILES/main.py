import asyncio
print("START MAIN")
import os
import sys
import traceback

try:
    open("treceri_pe_traseu.json", "w").close()
    print("[INIT] Fișierul treceri_pe_traseu.json a fost golit.")
except Exception as e:
    print(f"[EROARE] Nu pot șterge fișierul: {e}")

try:
    from webSocketServer import start_websocket_server
except Exception as e:
    print("EROARE LA IMPORT:")
    traceback.print_exc(file=sys.stdout)
    raise e  # OBLIGĂ afișarea completă și oprește programul


async def main():
    print("Serverul Websocket porneste...")

    # Trimitere mesaj de conectare
    # await send_message("Program RSP_PI deschis")
    # await send_message(f"User: username, Pass: password")

    try:
        await start_websocket_server()
    except asyncio.CancelledError:
        print("Serverul WebSocket a fost oprit.")
    except KeyboardInterrupt:
        print("Serverul WebSocket a fost întrerupt de utilizator.")
    finally:
        print("Aplicația s-a închis.")

if __name__ == "__main__":
    print('RUN MAIN')
    asyncio.run(main())
