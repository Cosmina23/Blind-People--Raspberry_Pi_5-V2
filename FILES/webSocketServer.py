import websockets
import json
import asyncio
from src.takeCredentials import autentificare
from routing.rutare_principal import obtine_ruta, obtine_ruta_standard
from src.indicatiiRutare import comenzi_deplasare
from voice_interface.textToSpeech import speak_text
from voice_interface.voiceToText import recognize_speech
from src.indicatiiRutare import geocode_adresa
from routing.pois import gaseste_puncte_pe_traseu
from src.monitorizare_trecere import monitorizare_treceri
from routing.detectare_treceri_traseu import genereaza_treceri_din_traseu
from routing.noduri_familiare import gaseste_nod_familiar_modificat
from utils.traseu_utils import elimina_coord_duplicate, decide_traseu
from src.manager_file import incarca_vizite, salveaza_vizite, salveaza_ruta
# import openrouteservice


current_app = None
last_location = None
location_queue = asyncio.Queue()

ORS_API_KEY = "5b3ce3597851110001cf62483ed29d9e4b9b47a58f40e20891efb908"
# client = openrouteservice.Client(key=ORS_API_KEY)
FISIER_VIZITE = "/home/cosmina/Documente/Proiect1/vizite.json"
lista_vizite = incarca_vizite(FISIER_VIZITE)
INDICATII_PATH = "indicatii_ruta.txt"
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

        except json.JSONDecodeError:
            print("[EROARE] JSON invalid")
        except websockets.exceptions.ConnectionClosed:
            print("[WS] Conexiune închisă")
            break
        except Exception as e:
            print(f"[EROARE gravă în primeste_mesaje]: {e}")


async def handle_connection(websocket, path=None):
    global current_app
    global last_location

    if current_app:
        await current_app.close()
        print("Conexiune curată / Aplicație anterioară deconectată")

    current_app = websocket
    print("Conexiune nouă stabilită")

    try:
        print("Aștept comenzile utilizatorului")
        await autentificare(websocket)

        asyncio.create_task(primeste_mesaje(websocket))

        while last_location is None:
            await asyncio.sleep(0.5)

        speak_text("Spuneți adresa unde doriți să ajungeți.")
        destinatie = await recognize_speech()
        print(f"[Asistent] Destinație rostită: {destinatie}")

        end = await geocode_adresa(destinatie)

        if not end:
            speak_text("Locația nu a fost identificată. Încercați din nou mai târziu.")
            return

        indicatii, coordonate_ruta, durata_traseu = obtine_ruta(last_location, end)
        speak_text(f"Traseul până la destinație durează aproximativ {durata_traseu} minute")

        opriri = []
        speak_text("Doriți să faceți opriri pe drum? De exemplu, să căutăm un magazin?")
        raspuns = await recognize_speech()

        if any(cuv in raspuns.lower() for cuv in ["farmacie", "magazin", "cafenea", "restaurant", "benzinărie", "benzinarie"]):
            categorie = None
            if "farmacie" in raspuns.lower(): categorie = "pharmacy"
            elif "magazin" or "profi" in raspuns.lower(): categorie = "supermarket"
            elif "cafenea" in raspuns.lower(): categorie = "cafe"
            elif "benzinarie" in raspuns.lower() or "benzinărie" in raspuns.lower(): categorie = "fuel"
            elif "restaurant" in raspuns.lower(): categorie = "restaurant"

            if categorie:
                try:
                    pbf_path = "/home/cosmina/Documente/Proiect1/timisoara.osm.pbf"
                    poi_coord = gaseste_puncte_pe_traseu(
                        start=last_location,
                        end=end,
                        nume_pbf=pbf_path,
                        categorie=categorie,
                        max_rezultate=1,
                        coordonate_traseu = coordonate_ruta
                    )

                    if poi_coord:
                        speak_text(f"Am găsit un {categorie} pe traseu.")
                        speak_text("Doriți să adăugăm această oprire?")
                        confirmare = await recognize_speech()
                        if any(cuv in confirmare.lower() for cuv in ["da", "sigur", "ok", "vreau"]):
                            opriri.append(poi_coord[0])

                except Exception as e:
                    print(f"[POI] Eroare la căutarea POI: {e}")
                    speak_text("A apărut o eroare la căutarea punctului de interes.")

        

        nod_familiar = gaseste_nod_familiar_modificat(last_location, end, lista_vizite)
        nod_familiar_coord = (nod_familiar["lat"], nod_familiar["lng"]) if nod_familiar else None
        nod_familiar_nume = nod_familiar["nume"] if nod_familiar else None

        if opriri:
            traseu_logical = []
            traseu_logical = decide_traseu(last_location, opriri[0], end, nod_familiar_coord)
        elif nod_familiar_coord:
            traseu_logical = [last_location, nod_familiar_coord, end]
        else:
            traseu_logical = [last_location, end]


        indicatii_totale = []
        coordonate_totale = []
        durata_totala = 0


        for i in range(len(traseu_logical) - 1):
            p_start = traseu_logical[i]
            p_end = traseu_logical[i + 1]

            print(f"[DEBUG] Calculez segment: {p_start} -> {p_end}")
    
            try:
                coordonate_partial, durata = obtine_ruta_standard(p_start, p_end)
                indicatii_partial = [] 
            except Exception as e:
                print(f"[EROARE] Segmentul {p_start} -> {p_end}: {e}")
                continue

            indicatii_totale.extend(indicatii_partial)
            coordonate_totale.extend(coordonate_partial if i == 0 else coordonate_partial[1:])
            durata_totala += durata


        if nod_familiar_coord:
            speak_text(f"Traseul include locația familiară salvată cu numele {nod_familiar_nume}.")

        speak_text(f"Traseul complet durează aproximativ {durata_totala} minute.")

        coordonate_totale = elimina_coord_duplicate(coordonate_totale)

        salveaza_ruta(coordonate_totale, INDICATII_PATH, COORD_PATH, indicatii_totale)
        genereaza_treceri_din_traseu(coordonate_totale)


        await websocket.send(json.dumps({
            "type": "ruta",
            "coordonate": [{"latitude": lat, "longitude": lng} for lat, lng in coordonate_totale],
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
            "nod_familiar":{
                "lat": nod_familiar_coord[0],
                "lng": nod_familiar_coord[1],
                "nume": nod_familiar_nume
            } if nod_familiar_coord else None
        }))

        print("Traseu trimis. Începem ghidarea vocală...")

        asyncio.create_task(comenzi_deplasare(location_queue))
        asyncio.create_task(monitorizare_treceri(lambda: last_location))

        await asyncio.Future()

    except websockets.exceptions.ConnectionClosed as e:
        print(f"Conexiune închisă: {e}")

    except Exception as e:
        print(f"Eroare necunoscută: {e}")

    finally:
        current_app = None


async def start_websocket_server():
    print("Pornim serverul WebSocket...")
    server = await websockets.serve(handle_connection, "0.0.0.0", 8765)
    print("Server WebSocket pornit pe portul 8765")
    await asyncio.Future()
