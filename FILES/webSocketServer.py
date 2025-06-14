import websockets
import json
import asyncio
from geopy.distance import geodesic
from src.takeCredentials import autentificare, reset_credentials
from src.navigator_maps import obtine_ruta
from src.indicatioRoutes import comenzi_deplasare
from textToSpeech import speak_text
from voiceToText import recognize_speech
from src.indicatioRoutes import geocode_adresa
import osmnx as ox
from test_osmnx import gaseste_puncte_pe_traseu
from src.monitorizare_trecere import monitorizare_treceri
# import openrouteservice
from src.detectare_treceri_traseu import gaseste_treceri_fix_pe_traseu
from pyrosm import OSM


current_app = None
last_location = None
location_queue = asyncio.Queue()

ORS_API_KEY = "5b3ce3597851110001cf62483ed29d9e4b9b47a58f40e20891efb908"
# client = openrouteservice.Client(key=ORS_API_KEY)


def genereaza_treceri_din_traseu(coordonate_ruta):
    try:
        print("Generăm treceri de pietoni de pe traseu...")
        pbf_path = "/home/cosmina/Documente/Proiect1/timisoara.osm.pbf"
        osm = OSM(pbf_path)
        crossings = osm.get_pois(custom_filter={"highway": ["crossing"]})

        treceri = gaseste_treceri_fix_pe_traseu(coordonate_ruta, crossings)

        with open("treceri_pe_traseu.json", "w") as f:
            json.dump(treceri, f, indent=2)
        print(f"Treceri salvate: {len(treceri)}")
    except Exception as e:
        print(f"[Eroare treceri pietoni]: {e}")

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
                with open("/home/cosmina/Documente/Proiect1/vizite.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            # elif msg_type == "searchedLocation":
            #     print("[SEARCH] Locație căutată primită")
            #     await proceseaza_destinatie(data, websocket)

            else:
                print(f"[UNKNOWN TYPE] {data}")

        except json.JSONDecodeError:
            print("[EROARE] JSON invalid")
        except websockets.exceptions.ConnectionClosed:
            print("[WS] Conexiune închisă")
            break
        except Exception as e:
            print(f"[EROARE gravă în primeste_mesaje]: {e}")

#POI = PUNCTE DE INTERES DIN TRASEU     
async def cauta_poi(traseu_coord, categorie_poi):
    try:
        lat_min = min(p[0] for p in traseu_coord)
        lng_min = min(p[1] for p in traseu_coord)
        lat_max = max(p[0] for p in traseu_coord)
        lng_max = max(p[1] for p in traseu_coord)

        g = ox.graph_from_bbox(lat_max, lat_min, lng_max, lng_min, network_type='walk')
        pois = ox.features_from_bbox(lat_max, lat_min, lng_max, lng_min, tags={"amenity": categorie_poi})

        if pois.empty:
            return None 
        
        #gasire cel mai apropiat poi de traseu 
        ruta_points = [(lat,lng) for lat,lng in traseu_coord]
        min_dist = float("inf")
        clossest = None 

        for _, row in pois.iterrows():
            poi_point = (row.geometry.y, row.geometry.x)
            for coord in ruta_points:
                dist = ox.distance.great_circle_vec(coord[0], coord[1], poi_point[0], poi_point[1])
                if dist < min_dist:
                    min_dist = dist
                    clossest = poi_point
        return clossest
    
    except Exception as e:
        print(f'[POI] Eroare la cautare poi: {e}')
        return None 



def scor_familiaritate(coord, distanta, nr_vizite, distanta_maxima = 2000):
    if distanta > distanta_maxima:
        return 0
    scor = nr_vizite * (1 - (distanta / distanta_maxima))
    return max(scor, 0)


def gaseste_nod_familiar(source_coord, target_coord, vizite_json, prag_diferenta_metri=150):
    candidati = []

    for punct in vizite_json:
        coord = (punct["lat"], punct["lng"])
        nr_vizite = punct["nr_vizite"]
        nume_loc = punct.get("nume_loc", "Loc familiar necunoscut")

        dist_la_destinatie = geodesic(coord, target_coord).meters
        dist_la_start = geodesic(source_coord, coord).meters
        total_dist = dist_la_start + dist_la_destinatie

        candidati.append({
            "coord": coord,
            "nr_vizite": nr_vizite,
            "dist_final": dist_la_destinatie,
            "dist_total": total_dist,
            "nume_loc": nume_loc
        })

    if not candidati:
        return None, None

    print("[DEBUG] Noduri familiare candidate:")
    for c in candidati:
        print(f"- {c['nume_loc']}: coord={c['coord']}, vizite={c['nr_vizite']}, dist_dest={c['dist_final']:.1f} m")

    # Sortează după distanță la destinație
    candidati.sort(key=lambda x: x["dist_final"])

    nod_apropiat = candidati[0]

    for c in candidati[1:]:
        diferenta = abs(c["dist_final"] - nod_apropiat["dist_final"])
        if diferenta <= prag_diferenta_metri and c["nr_vizite"] > nod_apropiat["nr_vizite"]:
            print(f"[DEBUG] Aleg nod cu mai multe vizite: {c['nume_loc']} în loc de {nod_apropiat['nume_loc']}")
            nod_apropiat = c

    print(f"[SELECTAT] Nod familiar: {nod_apropiat['nume_loc']} ({nod_apropiat['coord']}), {nod_apropiat['dist_final']:.1f}m de destinație, {nod_apropiat['nr_vizite']} vizite")
    return nod_apropiat["coord"], nod_apropiat["nume_loc"]

def gaseste_nod_familiar_modificat(start, end, vizite_json):
    try:
        _,_, durata_directa = obtine_ruta(start,end)
        print(f'[NOD FAMILIAR] Durata direct: {durata_directa} min')
    except Exception as e:
        print(f'[NOD FAMILIAR] Eroare la ruta directa {e}')
        return None
    
    best_node = None 
    best_durata = float('inf')
    best_vizite = 1

    for punct in vizite_json:
        coord = (punct["lat"], punct["lng"])
        nr_vizite = punct["nr_vizite"]
        try:
            _,_,durata_nod = obtine_ruta(start, end, nod_familiar = coord)
            print(f'[NOD FAMILIAR] Ruta pt {coord} dureaza {durata_nod} min')

            if durata_nod <= durata_directa *1.3:
                if durata_nod < best_durata or (abs(durata_nod - best_durata) < 3 and nr_vizite > best_vizite):
                    best_nod = {
                        "lat" : coord[0],
                        "lng":coord[1],
                        "nume": punct.get("nume_loc", "nod necunoscut"),
                        "nr_vizite": nr_vizite
                    }
                    best_durata = durata_nod
                    best_vizite = nr_vizite

        except Exception as e:
            print(f'[NOD FAMILIAR] Eroare la ruta cu nodul {coord}: {e}')
            continue 

    return best_nod

def elimina_coord_duplicate(lista):
    if not lista:
        return []
    rezultat = [lista[0]]
    for coord in lista[1:]:
        if coord != rezultat[-1]:
            rezultat.append(coord)
    return rezultat

def decide_traseu(start, oprire, destinatie, nod_familiar=None):
    traseu = [start]

    if nod_familiar and oprire:
        d_start_oprire = geodesic(start, oprire).meters
        d_start_nod = geodesic(start, nod_familiar).meters

        if d_start_oprire < d_start_nod:
            traseu += [oprire, nod_familiar]
        else:
            traseu += [nod_familiar, oprire]
    elif nod_familiar:
        traseu.append(nod_familiar)
    elif oprire:
        traseu.append(oprire)

    traseu.append(destinatie)
    return traseu



def insereaza_oprire_in_traseu(traseu, oprire_coord):
    dmin = float('inf')
    index_apropiat = -1
    for idx, punct in enumerate(traseu):
        dist = geodesic(punct, oprire_coord).meters
        if dist < dmin:
            dmin = dist
            index_apropiat = idx
    punct_apropiat = traseu[index_apropiat]
    traseu_modificat = (
        traseu[:index_apropiat+1] +
        [oprire_coord, punct_apropiat] +
        traseu[index_apropiat+1:]
    )
    return traseu_modificat


fisier_vizite = "/home/cosmina/Documente/Proiect1/vizite.json"
with open(fisier_vizite, "r", encoding="utf-8") as f:
    vizite = json.load(f)

lista_vizite = vizite.get("locuri", [])

async def handle_connection(websocket, path=None):
    global current_app
    global last_location

    if current_app:
        await current_app.close()
        print("Conexiune curată / Aplicație anterioară deconectată")

    current_app = websocket
    print("Conexiune nouă stabilită")

    # try:
    #     print("Aștept comenzile utilizatorului...")
    #     await autentificare(websocket)

    #     while True:
    #         message = await websocket.recv()
    #         print(f"Mesaj primit: {message}")

    #         try:
    #             data = json.loads(message)

    #             if data.get("message") in ["logout", "user logout"]:
    #                 print("Utilizatorul s-a deconectat")
    #                 reset_credentials()
    #                 break

    #             msg_type = data.get("type")

    #             if msg_type == "location":
    #                 last_location = (data.get("lat"), data.get("lng"))
    #                 print(f"Ultima locație actualizată: {last_location}")
    #                 await location_queue.put(data)  

    #             elif msg_type == "searchedLocation":
    #                 if last_location:
    #                     start = last_location
    #                     # end = (data.get("lat"), data.get("lng"))
    #                     speak_text('Spuneti adresa unde doriti sa ajungeti')
    #                     destinatie = await recognize_speech()
    #                     print(f'DESTINATIE: {destinatie}')
    #                     opriri = []

    #                     # speak_text('Vreți să faceți opriri pe drum?')
    #                     # raspuns = await recognize_speech()
    #                     # print(f'OPRIRI? Raspusn primit: {raspuns}')

    #                     # if raspuns.lower() in ["da", "sigur", "ok", "vreau", "desigur"]:
    #                     #     speak_text('Cate opriri vreti sa faceti?')
    #                     #     nr_opriri = await recognize_speech()
    #                     #     try:
    #                     #         nr_opriri = int(''.join(filter(str.isdigit, nr_opriri_text)))
    #                     #     except ValueError:
    #                     #         speak_text("Nu am înțeles numărul de opriri. Vom continua fără opriri.")
    #                     #         nr_opriri = 0
                            

    #                     end = await geocode_adresa(destinatie)

    #                     #adauga buton cand apasa pe el sa fie ascultata locatia unde doreste sa ajunga 
    #                     if not end:
    #                         speak_text('Locatia nu a fost identificata')
    #                         return

    #                     print(f"Calculăm ruta de la start la finish...")

    #                     #indicatii, coordonate_ruta, durata = obtine_ruta_ors(start, end, ORS_API_KEY)

    #                     #speak_text(f'Traseul pana la destinatie dureaza {durata} minute')
    #                     # speak_text('Vrei sa faic opriri pe drum?')
    #                     # raspuns = await recognize_speech()

    #                     indicatii, coordonate_ruta, durata_traseu = obtine_ruta(start,end)
    #                     speak_text(f'Traseul pana la destinatie dureaza aproximativ {durata_traseu} minute')

    #                     with open("indicatii_ruta.txt", "w") as f:
    #                         for indicatie in indicatii:
    #                             f.write(indicatie + "\n")
    #                     # print("Indicatii salvate îi indicatii_ruta.txt")

    #                     #salvare coordonate
    #                     with open("coordonate_ruta.json", "w") as f:
    #                         json.dump(
    #                             [{"latitude": lat, "longitude": lng} for lat, lng in coordonate_ruta],
    #                             f,
    #                             indent=2
    #                         )
    #                     # print("Coordonatele salvate în coordonate_ruta.json")

    #                     # Obținem numele locației de start și final 
    #                     # try:
    #                     #     reverse_end = client.pelias_reverse(location=[end[1], end[0]])
    #                     #     nume_end = reverse_end['features'][0]['properties'].get('label', 'Locatie necunoscuta')
    #                     # except Exception as e:
    #                     #     print("Eroare la reverse geocoding:", e)
    #                     #     nume_end = "Locatie necunoscuta"


    #                     await websocket.send(json.dumps({
    #                         "type": "ruta",
    #                         "coordonate": [{"latitude": lat, "longitude": lng} for lat, lng in coordonate_ruta]
    #                     }))
    #                     print("Coordonatele au fost trimise către aplicație")

    #                     #date trimise pentru salvare in tabelul rute din baza de date
    #                     await websocket.send(json.dumps({
    #                         "type": "traseu_nou",
    #                         "locatie_start_lat": start[0],
    #                         "locatie_start_lng": start[1],
    #                         "locatie_end_lat": end[0],
    #                         "locatie_end_lng": end[1],
    #                         "opriri": [] 
    #                     }))
    #                     print("TRIMIS TRASEU NOU !!!!!!!!!!!!!!!")

                       
    #                     asyncio.create_task(comenzi_deplasare(location_queue))

    #             else:
    #                 print(f"Mesaj necunoscut: {data}")

    #         except json.JSONDecodeError:
    #             print("Mesaj JSON invalid")



    try:
        print("Aștept comenzile utilizatorului")
        await autentificare(websocket)

        asyncio.create_task(primeste_mesaje(websocket))

        # Continuă fluxul principal fără să blochezi aplicația
        while last_location is None:
            await asyncio.sleep(0.5)

        # while True:
        #     try:
        #         message = await websocket.recv()
        #         data = json.loads(message)

        #         if data.get("type") == "location":
        #             last_location = (data.get("lat"), data.get("lng"))
        #             await location_queue.put(data)
        #         elif data.get("type") == "locuri_vizitate":
        #             try:
        #                 with open("/home/cosmina/Documente/Proiect1/vizite.json", "w", encoding="utf-8") as f:
        #                     print(f'[WebSocket] vizite.json actualizat')
        #                     json.dump(data, f, indent=2, ensure_ascii=False)
        #             except Exception as e:
        #                 print(f'[Eroare salvare locuri_vizitate]: {e}')
        #         else:
        #             print(f"[WebSocket] Tip necunoscut: {data.get('type')}")

        #     except websockets.exceptions.ConnectionClosed:
        #         print("Conexiune WebSocket închisă de client.")
        #         break
        #     except Exception as e:
        #         print(f"[Eroare WebSocket]: {e}")
        #         continue

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
            # dacă avem opriri, ne pregătim să decidem traseul corect
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
    
            # nod_familiar se folosește doar o singură dată (între start și oprire, sau start și end dacă nu avem oprire)
            # fol_nod_fstart == last_location and (not opriri or p_end == opriri[0])):
            #         foamiliar = None
            # if nod_familiar:
            #     if (p_l_nod_familiar = nod_familiar  # îl folosim doar o dată și doar pe prima secțiune relevantă

            indicatii_partial, coordonate_partial, durata = obtine_ruta(
                p_start, p_end,
                fol_edge_for_poi=(p_end in opriri),
                nod_familiar=None
            )

            indicatii_totale.extend(indicatii_partial)
            coordonate_totale.extend(coordonate_partial if i == 0 else coordonate_partial[1:])
            durata_totala += durata

        if nod_familiar_coord:
            speak_text(f"Traseul include locația familiară salvată cu numele {nod_familiar_nume}.")

        speak_text(f"Traseul complet durează aproximativ {durata_totala} minute.")

        coordonate_totale = elimina_coord_duplicate(coordonate_totale)

        with open("indicatii_ruta.txt", "w") as f:
            for indicatie in indicatii_totale:
                f.write(indicatie + "\n")

        with open("coordonate_ruta.json", "w") as f:
            json.dump(
                [{"latitude": lat, "longitude": lng} for lat, lng in coordonate_totale],
                f,
                indent=2
            )
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
