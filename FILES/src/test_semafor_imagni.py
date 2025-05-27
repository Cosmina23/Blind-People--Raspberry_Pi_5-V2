import os
import cv2
from detectie_semafor import analizeaza_semafor_din_imagine


FOLDER_IMAGINI = "imagini_semafor_test"
FOLDER_REZULTATE = "imagini_semafor_test_rezult"
os.makedirs(FOLDER_REZULTATE, exist_ok=True)

extensii_permise = [".jpg", ".jpeg", ".png"]
imagini = [f for f in os.listdir(FOLDER_IMAGINI) if os.path.splitext(f)[-1].lower() in extensii_permise]

print(f"\n📷 Găsite {len(imagini)} imagini pentru test...\n")

for nume in imagini:
    cale = os.path.join(FOLDER_IMAGINI, nume)

    print(f"🔎 Procesăm {nume}...")
    rezultat = analizeaza_semafor_din_imagine(cale, FOLDER_REZULTATE)

    if rezultat == "fara semafor":
        print(f"⚠️  {nume}: Nu a fost identificat niciun semafor valid.")
    else:
        print(f"✅ {nume}: Semafor detectat — culoare: {rezultat}")
