import asyncio
import json
from textToSpeech import speak_text
from geopy.distance import geodesic as GD
from geopy.geocoders import Nominatim
from geopy.geocoders import Nominatim
# from detectie_semafor import analizeaza_semafor_din_imagine
# import subprocess, time

PROXIMITY_METERS = 15
geolocator = Nominatim(user_agent="asistent_navigatie")

async def geocode_adresa(adresa):
    try:
        if "timișoara" not in adresa.lower():
            adresa += ", Timișoara"

        locatie = geolocator.geocode(adresa)
        if locatie:
            print(f'[GEOCODARE]: {adresa} => {locatie.latitude}, {locatie.longitude}')
            return (locatie.latitude, locatie.longitude)
        else:
            print(f'[GEOCODARE]: Nu am gasit locatia pentru: {adresa}')
            return None
    except Exception as e:
        print(f'[GEOCODARE]: Eroare: {e}')
        return None

def calculate_distance(lat_s, lng_s, lat_e, lng_e):
    return GD((lat_s, lng_s), (lat_e, lng_e)).km

def get_indicatii():
    with open("indicatii_ruta.txt", "r") as f:
        indicatii = [linie.strip() for linie in f.readlines()]

    with open("coordonate_ruta.json", "r") as f:
        coordonate = json.load(f)

    return indicatii, coordonate

def get_opriri():
    try:
        with open("coordonate_ruta.json", "r") as f:
            coordonate = json.load(f)
        with open("coordonate_opriri.json", "r") as f:
            opriri = json.load(f)
        return coordonate, opriri
    except:
        return [], []
    
def incarca_locatii_vizitate(user_name="Cosmina"):
    try:
        with open("vizite.json", "r") as f:
            data = json.load(f)
            if data.get("user") == user_name:
                return data.get("locuri", [])
    except Exception as e:
        print(f"[VIZITE] Eroare la citire vizite.json: {e}")
    return []


async def comenzi_deplasare(location_queue):
    print("[Asistent] Modulul de ghidare vocală a început.")
    indicatii, coordonate = get_indicatii()

    # with open("treceri_pe_traseu.json","r") as f:
    #     treceri_pe_traseu = json.load(f)
    

    _, opriri = get_opriri()

    pas_curent = 0
    opriri_efectuate = set()

    # 1. Incarca locatiile vizitate (noduri familiare)
    locatii_vizitate = incarca_locatii_vizitate(user_name=data.get("user", "Cosmina"))
    locatii_familiare = []

    for loc_viz in locatii_vizitate:
        for idx, punct in enumerate(coordonate):
            dist = calculate_distance(punct["latitude"], punct["longitude"], loc_viz["lat"], loc_viz["lng"]) * 1000
            if dist <= PROXIMITY_METERS:
                locatii_familiare.append({
                    "nume": loc_viz.get("nume_loc", "loc cunoscut"),
                    "index": idx
                })

    if locatii_familiare:
        loc_familiar = sorted(locatii_familiare, key=lambda x: x["index"])[0]  # cel mai apropiat în ordine
        msg_intro = f"Traseul include locația cunoscută salvată cu numele {loc_familiar['nume']}."

        # Verificăm dacă există opriri înainte de acea locație
        opriri_inainte = []
        for oprire in opriri:
            for i in range(0, loc_familiar["index"]):
                punct = coordonate[i]
                dist = calculate_distance(punct["latitude"], punct["longitude"], oprire["latitude"], oprire["longitude"]) * 1000
                if dist <= PROXIMITY_METERS:
                    opriri_inainte.append(oprire)

        if opriri_inainte:
            msg_intro += f" Dar mai întâi ajungem la oprirea intermediară."

        print("[Asistent] Mesaj introductiv:", msg_intro)
        speak_text(msg_intro)

    while pas_curent < len(coordonate):
        try:
            data = await location_queue.get()
            lat_user = data.get("lat")
            lng_user = data.get("lng")
            lat_end = coordonate[pas_curent]["latitude"]
            lng_end = coordonate[pas_curent]["longitude"]

            # for zebra in treceri_pe_traseu:
            #     z_lat = zebra["latitude"]
            #     z_lng = zebra["longitude"]
            #     d = calculate_distance(lat_user, lng_user, z_lat, z_lng) * 1000

            #     if d <= PROXIMITY_METERS and (z_lat, z_lng) not in opriri_efectuate:
            #         print(f"[Semafor] Aproape de trecere la {z_lat}, {z_lng} (d={d:.1f} m)")

            #         img_path = f"zebra_{int(time.time())}.jpg"
            #         subprocess.run([
            #             "libcamera-still", "-o", img_path,
            #             "--width", "640", "--height", "480", "--nopreview"
            #         ])

            #         rezultat = analizeaza_semafor_din_imagine(img_path)
            #         print(f"[Semafor] Rezultat: {rezultat}")
            #         speak_text(f"Trecere de pietoni cu semafor: {rezultat}" if rezultat != "fara semafor" else "Trecere de pietoni fara semafor")
            #         opriri_efectuate.add((z_lat, z_lng))


            dist = calculate_distance(lat_user, lng_user, lat_end, lng_end) * 1000  # in metri
            print(f"[Asistent] Distanță până la pasul {pas_curent + 1}: {dist:.1f} m")

            if 1.5 <= dist <= 3:
                instructiune = indicatii[pas_curent]
                mesaj = f"În câțiva pași, {instructiune.lower()}."
                print(f"[Asistent] Instrucțiune anticipată: {mesaj}")
                speak_text(mesaj)

            elif dist < 1.5:
                instructiune = indicatii[pas_curent]
                mesaj = f"Acum, {instructiune.lower()}."
                print(f"[Asistent] Instrucțiune finală: {mesaj}")
                speak_text(mesaj)
                pas_curent += 1


            for oprire in opriri:
                o_lat = oprire["latitude"]
                o_lng = oprire["longitude"]
                d_oprire = calculate_distance(lat_user, lng_user, o_lat, o_lng) * 1000
                if d_oprire <= PROXIMITY_METERS and (o_lat, o_lng) not in opriri_efectuate:
                    speak_text("Ați ajuns la oprirea intermediară.")
                    print("[Asistent] Utilizatorul a ajuns la o oprire.")
                    opriri_efectuate.add((o_lat, o_lng))

            if pas_curent == len(coordonate):
                await asyncio.sleep(1)
                speak_text("Ați ajuns la destinație.")
                break

        except Exception as e:
            print(f"[Asistent] Eroare la procesarea instrucțiunilor: {e}")
            break
