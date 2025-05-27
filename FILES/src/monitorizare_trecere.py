import time
import json
import subprocess
from geopy.distance import geodesic
from detectie_semafor import analizeaza_semafor_din_imagine

PROXIMITATE_METRI = 10

with open("treceri_pe_traseu.json", "r") as f:
    treceri = json.load(f)

#functie de simualre, se inlocuieste cu coordonatele reale
def get_user_location():
    return (45.748, 21.23)

treceri_detectate = set()

while True:
    lat_user, lon_user = get_user_location()

    for zebra in treceri:
        lat, lon = zebra["latitude"], zebra["longitude"]
        dist = geodesic((lat_user, lon_user), (lat, lon)).meters

        if dist < PROXIMITATE_METRI and (lat, lon) not in treceri_detectate:
            print(f"👣 Aproape de trecere la ({lat:.5f}, {lon:.5f}), distanță: {dist:.1f} m")

            img_path = f"zebra_{int(time.time())}.jpg"
            subprocess.run(["libcamera-still", "-o", img_path, "--width", "640", "--height", "480", "--nopreview"])
            rezultat = analizeaza_semafor_din_imagine(img_path)

            print(f"Trecere cu semafor: {rezultat}" if rezultat != "fara semafor" else "Trecere fără semafor")
            treceri_detectate.add((lat, lon))

    time.sleep(5)
