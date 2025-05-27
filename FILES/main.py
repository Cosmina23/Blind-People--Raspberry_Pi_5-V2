import asyncio

from webSocketServer import start_websocket_server

print("START MAIN")

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
