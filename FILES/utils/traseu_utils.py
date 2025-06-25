from geopy.distance import geodesic


def elimina_coord_duplicate(lista):
    if not lista:
        return []
    rezultat = [lista[0]]
    for coord in lista[1:]:
        if coord != rezultat[-1]:
            rezultat.append(coord)
    return rezultat

def decide_traseu(start, oprire, destinatie, nod_familiar=None):
    traseu = [start]

    if nod_familiar and oprire:
        d_start_oprire = geodesic(start, oprire).meters
        d_start_nod = geodesic(start, nod_familiar).meters

        if d_start_oprire < d_start_nod:
            traseu += [oprire, nod_familiar]
        else:
            traseu += [nod_familiar, oprire]
    elif nod_familiar:
        traseu.append(nod_familiar)
    elif oprire:
        traseu.append(oprire)

    traseu.append(destinatie)
    return traseu



def insereaza_oprire_in_traseu(traseu, oprire_coord):
    dmin = float('inf')
    index_apropiat = -1
    for idx, punct in enumerate(traseu):
        dist = geodesic(punct, oprire_coord).meters
        if dist < dmin:
            dmin = dist
            index_apropiat = idx
    punct_apropiat = traseu[index_apropiat]
    traseu_modificat = (
        traseu[:index_apropiat+1] +
        [oprire_coord, punct_apropiat] +
        traseu[index_apropiat+1:]
    )
    return traseu_modificat
