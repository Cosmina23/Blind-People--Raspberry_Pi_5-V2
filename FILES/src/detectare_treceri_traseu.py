import json
from pyrosm import OSM
from geopy.distance import geodesic

#preia coordonate traseu
with open("coordonate_ruta.json", "r") as f:
    coordonate_ruta = [(pt["latitude"], pt["longitude"]) for pt in json.load(f)]


osm = OSM("timisoara.osm.pbf")
crossings = osm.get_pois(custom_filter={"highway": ["crossing"]})

def gaseste_treceri_fix_pe_traseu(coordonate_ruta, toate_trecerile, prag_metri=3):
    rezultate = []
    for _, row in toate_trecerile.iterrows():
        punct_zebra = (row["lat"], row["lon"])
        if any(geodesic(punct_zebra, coord).meters <= prag_metri for coord in coordonate_ruta):
            rezultate.append({"latitude": punct_zebra[0], "longitude": punct_zebra[1]})
    return rezultate

treceri_pe_traseu = gaseste_treceri_fix_pe_traseu(coordonate_ruta, crossings)

#lista cu treceri salvata in fisier
with open("../treceri_pe_traseu.json", "w") as f:
    json.dump(treceri_pe_traseu, f, indent=2)

print(f"{len(treceri_pe_traseu)} treceri de pietoni detectate pe traseu.")
