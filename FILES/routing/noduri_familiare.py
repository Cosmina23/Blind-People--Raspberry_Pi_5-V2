from routing.rutare_principal import obtine_ruta
from geopy.distance import geodesic


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
