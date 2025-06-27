import websockets
import json
import asyncio
import RPi.GPIO as GPIO  # <-- GPIO aici
from src.takeCredentials import autentificare, get_input
from routing.rutare_principal import obtine_ruta_segment, incarca_graf
from src.indicatiiRutare import comenzi_deplasare, genereaza_indicatii_din_coordonate, geocode_adresa
from voice_interface.textToSpeech import speak_text
from voice_interface.voiceToText import recognize_speech
from routing.pois import gaseste_puncte_pe_traseu
from src.monitorizare_trecere import monitorizare_treceri
from routing.detectare_treceri_traseu import genereaza_treceri_din_traseu
from routing.noduri_familiare import gaseste_nod_familiar_modificat
from utils.traseu_utils import elimina_coord_duplicate
from src.manager_file import incarca_vizite, salveaza_vizite, actualizeaza_vizite
from routing.my_dijkstra import bidirectional_dijkstra_modificat
from src.manager_file import salveaza_ruta

# --- Config GPIO ---
BUTTON_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

current_app = None
last_location = None
location_queue = asyncio.Queue()
task_deplasare = None
task_treceri = None

button_pressed_event = asyncio.Event() 


FISIER_VIZITE = "/home/cosmina/Documente/Proiect1/vizite.json"
lista_vizite = incarca_vizite(FISIER_VIZITE)
INDICATII_PATH = "indicatii_ruta.json"
COORD_PATH = "coordonate_ruta.json"

async def primeste_mesaje(websocket):
    global last_location
    while True:
        try:
            message = await websocket.recv()
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "location":
                print(f"[LOCATIE] Primit: {data}")
                last_location = (data.get("lat"), data.get("lng"))
                await location_queue.put(data)

            elif msg_type == "locuri_vizitate":
                print("[VIZITE] Actualizare locuri vizitate")
                salveaza_vizite(data, FISIER_VIZITE)

            else:
                print(f"[UNKNOWN TYPE] {data}")

        except Exception as e:
            print(f"[EROARE primeste_mesaje]: {e}")
            break
def buton_apasat(channel):
    print("[BUTON] Apăsat - semnal pentru rută nouă")
    button_pressed_event.set()

def setup_buton_listener():
    GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=buton_apasat, bouncetime=1500)

# --- Rutina de rutare (nicio schimbare aici, doar asigurăm că e async și o apelăm din context corect) ---
async def proceseaza_ruta_noua(websocket):
    global task_deplasare, task_treceri, last_location

    if task_deplasare:
        task_deplasare.cancel()
        try: await task_deplasare
        except: pass

    if task_treceri:
        task_treceri.cancel()
        try: await task_treceri
        except: pass

    while last_location is None:
        print("[AȘTEPTARE] Aștept locația de start...")
        await asyncio.sleep(0.5)

    destinatie = await get_input("Spuneți adresa unde doriți să ajungeți.")
    end = await geocode_adresa(destinatie)
    if not end:
        speak_text("Locația nu a fost identificată.")
        return

    _, coordonate_ruta, durata_traseu = obtine_ruta_segment(last_location, end)
    speak_text(f"Traseul durează aproximativ {durata_traseu} minute")

    opriri = []
    raspuns = await get_input("Doriți să faceți opriri pe drum?")
    if any(cuv in raspuns.lower() for cuv in ["farmacie", "magazin", "cafenea", "restaurant", "benzinărie", "benzinarie"]):
        categorie = None
        if "farmacie" in raspuns.lower(): categorie = "pharmacy"
        elif "magazin" in raspuns.lower(): categorie = "supermarket"
        elif "cafenea" in raspuns.lower(): categorie = "cafe"
        elif "benzinarie" in raspuns.lower() or "benzinărie" in raspuns.lower(): categorie = "fuel"
        elif "restaurant" in raspuns.lower(): categorie = "restaurant"

        try:
            pbf_path = "/home/cosmina/Documente/Proiect1/timisoara.osm.pbf"
            poi_coord = gaseste_puncte_pe_traseu(last_location, end, pbf_path, categorie, 1, coordonate_ruta)
            if poi_coord:
                speak_text(f"Am găsit un {categorie} pe traseu. Îl adăugăm?")
                confirmare = await recognize_speech()
                if "da" in confirmare.lower():
                    opriri.append(poi_coord[0])
        except Exception as e:
            print(f"[POI] Eroare: {e}")

    nod_familiar = gaseste_nod_familiar_modificat(last_location, end, lista_vizite)
    nod_familiar_coord = (nod_familiar["lat"], nod_familiar["lng"]) if nod_familiar else None
    nod_familiar_nume = nod_familiar["nume"] if nod_familiar else None

    graf = incarca_graf()
    ruta_noduri, durata_totala = bidirectional_dijkstra_modificat(
        G=graf, start=last_location, end=end,
        oprire=opriri[0] if opriri else None,
        nod_familiar=nod_familiar_coord
    )

    coordonate_totale = [(graf.nodes[n]['y'], graf.nodes[n]['x']) for n in ruta_noduri]
    coordonate_totale = elimina_coord_duplicate(coordonate_totale)

    coordonate_dict = [{"latitude": lat, "longitude": lng} for lat, lng in coordonate_totale]
    indicatii_totale = genereaza_indicatii_din_coordonate(coordonate_dict)

    salveaza_ruta(coordonate_totale, INDICATII_PATH, COORD_PATH, indicatii_totale)
    if nod_familiar_coord:
        speak_text(f"Traseul include locația {nod_familiar_nume}.")
    speak_text(f"Durata estimată este {durata_totala} minute.")

    genereaza_treceri_din_traseu(coordonate_totale)
    await websocket.send(json.dumps({
        "type": "ruta",
        "coordonate": coordonate_dict,
        "opriri": [{"latitude": lat, "longitude": lng} for lat, lng in opriri]
    }))

    await websocket.send(json.dumps({
        "type": "traseu_actualizat",
        "locatie_start_lat": last_location[0],
        "locatie_start_lng": last_location[1],
        "locatie_end_lat": end[0],
        "locatie_end_lng": end[1],
        "destinatie_nume": destinatie,
        "opriri": [{"latitude": lat, "longitude": lng} for lat, lng in opriri],
        "nod_familiar": {
            "lat": nod_familiar_coord[0],
            "lng": nod_familiar_coord[1],
            "nume": nod_familiar_nume
        } if nod_familiar_coord else None
    }))

    actualizeaza_vizite(end, FISIER_VIZITE, nume_nou=destinatie)
    task_deplasare = asyncio.create_task(comenzi_deplasare(location_queue))
    task_treceri = asyncio.create_task(monitorizare_treceri(lambda: last_location))

# --- WebSocket ---
async def handle_connection(websocket, path=None):
    global current_app
    if current_app:
        await current_app.close()
    current_app = websocket
    print("Nouă conexiune websocket")
    await autentificare(websocket)
    asyncio.create_task(primeste_mesaje(websocket))
    await proceseaza_ruta_noua(websocket)

    # buclă care așteaptă apăsarea butonului
    while True:
        await button_pressed_event.wait()
        button_pressed_event.clear()
        print("[EVENIMENT] Buton apăsat - încep recalculare...")
        await proceseaza_ruta_noua(websocket)

# --- Start server ---
async def start_websocket_server():
    try:
        print("Pornim serverul WebSocket...")
        setup_buton_listener()
        await websockets.serve(handle_connection, "0.0.0.0", 8765)
        await asyncio.Future()
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    asyncio.run(start_websocket_server())