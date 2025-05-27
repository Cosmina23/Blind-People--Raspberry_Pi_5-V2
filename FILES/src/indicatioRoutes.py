import asyncio
import json
from textToSpeech import speak_text
from geopy.distance import geodesic as GD
from geopy.geocoders import Nominatim
from geopy.geocoders import Nominatim

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

async def comenzi_deplasare(location_queue):
    print("[Asistent] Modulul de ghidare vocală a început.")
    indicatii, coordonate = get_indicatii()
    _, opriri = get_opriri()

    pas_curent = 0
    opriri_efectuate = set()

    while pas_curent < len(coordonate):
        try:
            data = await location_queue.get()
            lat_user = data.get("lat")
            lng_user = data.get("lng")
            lat_end = coordonate[pas_curent]["latitude"]
            lng_end = coordonate[pas_curent]["longitude"]

            dist = calculate_distance(lat_user, lng_user, lat_end, lng_end) * 1000  # in metri
            print(f"[Asistent] Distanță până la pasul {pas_curent + 1}: {dist:.1f} m")

            if 5 <= dist <= PROXIMITY_METERS:
                instructiune = indicatii[pas_curent]
                mesaj = f"In aproximativ 5 metri, {instructiune.lower()}."
                print(f"[Asistent] Instrucțiune: {mesaj}")
                speak_text(mesaj)
            elif dist < 5:
                instructiune = indicatii[pas_curent]
                mesaj = f"Acum, {instructiune.lower()}"
                print(f"[Asistent] Instrucțiune: {mesaj}")
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
