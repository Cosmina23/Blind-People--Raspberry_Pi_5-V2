import json


async def receive_message_from_app(websocket):
    if websocket:
        message = await websocket.recv()
        print(f"Mesaj primit de la aplicație: {message}")
        return message

async def send_message(websocket, message):
    if websocket:
        await websocket.send(json.dumps({"message": message}))
        print(f"Trimis la aplicație: {message}")
    else:
        print("Nicio aplicație conectată")

