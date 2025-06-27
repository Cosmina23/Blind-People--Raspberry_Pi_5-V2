from geopy.distance import geodesic


def elimina_coord_duplicate(lista):
    if not lista:
        return []
    rezultat = [lista[0]]
    for coord in lista[1:]:
        if coord != rezultat[-1]:
            rezultat.append(coord)
    return rezultat


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
