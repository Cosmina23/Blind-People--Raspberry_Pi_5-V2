import asyncio
import json
from voice_interface.textToSpeech import speak_text
from geopy.distance import geodesic as GD
from geopy.geocoders import Nominatim
from geopy.geocoders import Nominatim
# from detectie_semafor import analizeaza_semafor_din_imagine
# import subprocess, time

import math 

PROXIMITY_METERS = 15
geolocator = Nominatim(user_agent="asistent_navigatie")



def calculeaza_unghi(p1, p2, p3):
    v1 = (p2[0] - p1[0], p2[1] - p1[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])
    prod = v1[0]*v2[0] + v1[1]*v2[1]
    norm_u = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
    norm_v = math.sqrt(v2[0] ** 2 + v2[1] ** 2)
    if norm_u*norm_v == 0:
        return 0

    cos_angle = prod / (norm_u * norm_v)
    cos_angle = max(-1, min(1, cos_angle))
    angle = math.degrees(math.acos(cos_angle))

    determinant = v1[0]*v2[1] - v1[1]*v2[0]
    return angle if determinant > 0 else -angle



def genereaza_indicatie(angle):
    prag_dreapta = 20
    prag_stanga = -20
    if angle > prag_dreapta:
        return "La dreapta"
    elif angle < prag_stanga:
        return "La stanga"
    return "Inainte"

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
