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


def genereaza_indicatii_din_coordonate(coordonate):
    indicatii = []
    for i in range(len(coordonate) - 2):
        p1 = (coordonate[i]["latitude"], coordonate[i]["longitude"])
        p2 = (coordonate[i+1]["latitude"], coordonate[i+1]["longitude"])
        p3 = (coordonate[i+2]["latitude"], coordonate[i+2]["longitude"])

        unghi = calculeaza_unghi(p1, p2, p3)
        directie = genereaza_indicatie(unghi)

        anticipare = f"In cativa pasi, {directie.lower()}."
        final = f"Acum, {directie.lower()}."

        indicatii.append({"lat": p2[0], "lng": p2[1], "text": {"lat": p3[0], "lng": p3[1], "text": anticipare}, "anuntata": False})
        indicatii.append({"lat": p3[0], "lng": p3[1], "text": {"lat": p3[0], "lng": p3[1], "text": final}, "anuntata": False})
    
    return indicatii


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

def get_indicatii_ruta():
    try:
        with open("indicatii_ruta.json", "r") as f:
            indicatii = json.load(f)
        return indicatii
    except Exception as e:
        print(f"[Indicatii] Eroare la citire JSON: {e}")
        return []


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
    indicatii = get_indicatii_ruta()

    # Poți include și coordonatele pentru alte verificări
    coordonate = [{"latitude": i["lat"], "longitude": i["lng"]} for i in indicatii]

    while True:
        try:
            data = await location_queue.get()
            lat_user = data.get("lat")
            lng_user = data.get("lng")

            actualizat = False  # flag ca să știm dacă salvăm fișierul

            for instructiune in indicatii:
                if instructiune.get("anuntata"):
                    continue

                lat_ind = instructiune["lat"]
                lng_ind = instructiune["lng"]

                dist = calculate_distance(lat_user, lng_user, lat_ind, lng_ind) * 1000  # în metri

                if dist <= 4:
                    mesaj = instructiune.get("text", {}).get("text")
                    if mesaj:
                        print(f"[Asistent] Redau instrucțiune: {mesaj}")
                        speak_text(mesaj)
                        instructiune["anuntata"] = True
                        actualizat = True

                        
            if actualizat:
                with open("indicatii_ruta.json", "w") as f:
                    json.dump(indicatii, f, indent=2)


        except Exception as e:
            print(f"[Asistent] Eroare la procesarea instrucțiunilor: {e}")
            break
