import json
from geopy.distance import geodesic

def incarca_vizite(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("locuri", [])

def salveaza_vizite(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def salveaza_ruta(coordonate, ind_path, coord_path, indicatii=None):
    # Salvează coordonatele
    with open(coord_path, "w") as f:
        json.dump(
            [{"latitude": lat, "longitude": lng} for lat, lng in coordonate],
            f,
            indent=2
        )

    # Salvează indicațiile ca JSON complet
    if indicatii is not None:
        with open(ind_path, "w") as f:
            json.dump(indicatii, f, indent=2)


def actualizeaza_vizite(destinatie_coord, path="vizite.json", nume_nou="destinatie noua", prag_metri=10):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        locuri = data.get("locuri", [])
        gasit = False

        for loc in locuri:
            dist = geodesic((loc["lat"], loc["lng"]), destinatie_coord).meters
            if dist <= prag_metri:
                loc["nr_vizite"] += 1
                gasit = True
                break

        if not gasit:
            locuri.append({
                "lat": destinatie_coord[0],
                "lng": destinatie_coord[1],
                "nr_vizite": 1,
                "nume_loc": nume_nou
            })

        data["locuri"] = locuri

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[VIZITE] Vizitele au fost actualizate pentru destinație.")

    except Exception as e:
        print(f"[VIZITE] Eroare la actualizarea vizitelor: {e}")
