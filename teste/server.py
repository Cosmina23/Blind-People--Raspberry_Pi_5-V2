import asyncio
import websockets
import json
from textToSpeech import speak_text
from voiceToText import recognize_speech

current_app = None

async def handle_connection(websocket, path=None):
    global current_app
    
    print("Conexiune nouă stabilită!")
    
    if current_app:
        await current_app.close()
        print("Aplicație anterioară deconectată")

    current_app = websocket
    print("Conexiune activă cu aplicația.")

    try:
        print("Încep procesul de autentificare...")

        # Vorbim cu utilizatorul
        speak_text("Buna! Ai deja un cont?")
        cont = await recognize_speech()
        print(f"Ai cont? : {cont}")
        if not cont:
            print("Nu am înțeles răspunsul")
            await send_message("Eroare: Nu am înțeles răspunsul")
            return
        await send_message(f"Cont existent: {cont}")

        # Continuăm cu numele utilizatorului
        speak_text("Te rog să îmi spui numele de utilizator.")
        name = await recognize_speech()
        print(f"Nume preluat: {name}")
        if not name:
            print("Nu am recunoscut numele.")
            await send_message("Eroare: Nu am recunoscut numele.")
            return
        await send_message(f'Nume: "{name}"')

        # Continuăm cu codul de autentificare
        speak_text("Te rog să îmi spui codul de autentificare.")
        code = await recognize_speech()
        print(f"Cod preluat: {code}")
        if not code:
            print("Nu am recunoscut codul.")
            await send_message("Eroare: Nu am recunoscut codul.")
            return
        await send_message(f'Cod: "{code}"')

        # Verificăm conectarea
        speak_text(f"Vrei să te conectezi cu numele {name}?")
        conectare_ok = await recognize_speech()
        print(f"Răspuns: {conectare_ok}")
        if conectare_ok.lower() == "da":
            await send_message("Conectare cu succes!")
            speak_text("Te rog să aștepți câteva secunde.")
        else:
            speak_text("Te rog să reintroduci credentialele.")
        
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Conexiune închisă din cauza unei erori: {e}")
    except Exception as e:
        print(f"A apărut o eroare necunoscută: {e}")
    finally:
        current_app = None

async def send_message(message):
    if current_app:
        await current_app.send(json.dumps({"message": message}))
        print(f"Trimis la aplicație: {message}")
    else:
        print("Nu există aplicație conectată.")

async def start_websocket_server():
    print("Începem serverul WebSocket...")
    server = await websockets.serve(handle_connection, "0.0.0.0", 8765)
    print("Server WebSocket pornit pe portul 8765")
    
    try:
        # Ține serverul activ la nesfârșit
        await asyncio.Future()  # Serverul WebSocket rămâne activ
    except asyncio.CancelledError:
        print("Serverul WebSocket a fost oprit.")
        server.close()
        await server.wait_closed()
    except Exception as e:
        print(f"Eroare: {e}")

async def main():
    print("Serverul WebSocket pornește...")
    await start_websocket_server()

if __name__ == "__main__":
    print("Înainte de asyncio.run()")
    asyncio.run(main())  # Rulează funcția main
    print("Serverul WebSocket 2...")  # Acesta va fi afisat dupa ce main se termina
