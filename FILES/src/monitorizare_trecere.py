import json
import time
import asyncio
import subprocess
from geopy.distance import geodesic
from src.detectie_semafor import analizeaza_semafor_din_imagine
import os

PROXIMITATE_METRI = 10

def get_user_location():
    # o coordonată apropiată de o trecere cunoscută din treceri_pe_traseu.json
    return (45.72500991821289, 21.25615692138672)


async def monitorizare_treceri(get_user_location_func):
    try:
        with open("treceri_pe_traseu.json", "r") as f:
            treceri = json.load(f)
    except Exception as e:
        print(f"[Monitorizare] Nu pot încărca trecerile: {e}")
        return

    treceri_detectate = set()

    while True:
        user_coord = get_user_location()
        if not user_coord:
            await asyncio.sleep(2)
            continue

        lat_user, lon_user = user_coord

        for zebra in treceri:
            lat, lon = zebra["latitude"], zebra["longitude"]
            dist = geodesic((lat_user, lon_user), (lat, lon)).meters

            if dist < PROXIMITATE_METRI and (lat, lon) not in treceri_detectate:
                print(f"Aproape de trecere la ({lat:.5f}, {lon:.5f}), distanță: {dist:.1f} m")

                img_path = f"zebra_{int(time.time())}.jpg"
                subprocess.run(["libcamera-still", "-o", img_path, "--width", "640", "--height", "480", "--nopreview"])
                rezultat = analizeaza_semafor_din_imagine(img_path, "imagini_rezultate")

                print(f"Trecere cu semafor: {rezultat}" if rezultat != "fara semafor" else "Trecere fără semafor")
                treceri_detectate.add((lat, lon))

                from textToSpeech import speak_text

                if rezultat != "fara semafor":
                    speak_text(f"Semafor detectat. Culoare: {rezultat}")
                else:
                    speak_text("Trecere fără semafor.")
                    try:
                        os.remove(img_path)  # Șterge imaginea după procesare
                    except:
                        pass


        await asyncio.sleep(5)

# if __name__ == "__main__":
#     asyncio.run(monitorizare_treceri(get_user_location))
