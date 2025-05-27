from textToSpeech import speak_text
from voiceToText import recognize_speech
from sendMessage import send_message, receive_message_from_app

async def get_input(text):
    while True:
        speak_text(text)
        value = await recognize_speech()
        if value: 
            print(f"Recunnoscut: {value}")
            return value
        speak_text("Nu am inteles, te rog repeta")

async def autentificare(websocket):
    speak_text("Buna! Vrei sa te conectezi vocal sau manual?")
    metoda = await recognize_speech()

    if any(cuv in metoda.lower() for cuv in ["manual", "scris", "vreau manual", "nu vreau vocal"]):
        speak_text("Am inteles, autentificarea se va face manual")
        await send_message(websocket, "autentiicare manuala")
        return
    else: 
        speak_text("Conectarea o sa fie vocala")

    cont = await get_input("Ai deja cont?")
    await send_message(websocket, f'Cont existent: {cont}')

    user_name = await get_input("Te rog sa imi spui numele de utilizator")
    await send_message(websocket, f'Nume: {user_name}')

    code = await get_input("te rog sa imi spui codul pentru autentificare format doar din cifre")
    await send_message(websocket, f'Cod: {code}')

    conectare_ok = await get_input(f"Vrei sa te conectezi cu numele {user_name} ?")
    if conectare_ok.lower() == 'da':
        await send_message(websocket, f"Credentiale bune: {conectare_ok}")
        speak_text(f"Te rog sa astepti cateva secunde")
        response = await receive_message_from_app(websocket)
    else:
        speak_text("reintrodu credentialele de conectare")

def reset_credentials():
    global user_name, code
    user_name = ""
    code = ""
