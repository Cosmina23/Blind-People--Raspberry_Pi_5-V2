import json

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
