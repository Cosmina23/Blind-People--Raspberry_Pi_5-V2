import os
import json
import osmnx as ox
import openrouteservice
from shapely.geometry import Point
from geopy.distance import geodesic
from osmnx.distance import nearest_edges
from networkx.algorithms.shortest_paths.weighted import bidirectional_dijkstra as nx_bidirectional_dijkstra

from src.indicatiiRutare import calculeaza_unghi, genereaza_indicatie
from routing.my_dijkstra import bidirectional_dijkstra_modificat
from src.manager_file import incarca_vizite


# --- Configurare globală ---
FISIER_VIZITE = "/home/cosmina/Documente/Proiect1/vizite.json"
GRAFML_FILE = "timisoara.graphml"


def incarca_graf():
    if not os.path.exists(GRAFML_FILE):
        graf = ox.graph_from_place("Timișoara, Romania", network_type="walk")
        ox.save_graphml(graf, GRAFML_FILE)
    else:
        graf = ox.load_graphml(GRAFML_FILE)

    for node in graf.nodes:
        nod = graf.nodes[node]
        nod['coord'] = (nod['y'], nod['x'])

    return graf


def nearest_node(graf, coord):
    return ox.distance.nearest_nodes(graf, X=coord[1], Y=coord[0])


def nearest_point_on_edge(graf, point):
    u, v, key = nearest_edges(graf, point[1], point[0])
    lat_u, lon_u = graf.nodes[u]['y'], graf.nodes[u]['x']
    lat_v, lon_v = graf.nodes[v]['y'], graf.nodes[v]['x']

    point_geom = Point(point[1], point[0])
    line = Point(lon_u, lat_u).buffer(0.0001).union(Point(lon_v, lat_v).buffer(0.0001)).convex_hull
    if not line.contains(point_geom):
        return u if geodesic((lat_u, lon_u), point).meters < geodesic((lat_v, lon_v), point).meters else v
    return u


def obtine_ruta_segment(start, end):
    graf = incarca_graf()

    ruta, durata = bidirectional_dijkstra_modificat(
        G=graf,
        start=start,
        end=end,
        oprire=None,
         nod_familiar=None
    )


    indicatii = []
    for i in range(len(ruta) - 2):
        u, v, w = ruta[i], ruta[i + 1], ruta[i + 2]
        lat1, lon1 = graf.nodes[u]['y'], graf.nodes[u]['x']
        lat2, lon2 = graf.nodes[v]['y'], graf.nodes[v]['x']
        lat3, lon3 = graf.nodes[w]['y'], graf.nodes[w]['x']

        angle = calculeaza_unghi((lat1, lon1), (lat2, lon2), (lat3, lon3))
        directie = genereaza_indicatie(angle)

        anticipare = f"In cativa pasi, {directie.lower()}."
        final = f"Acum, {directie.lower()}."

        indicatii.append({"lat": lat2, "lng": lon2, "text": {"lat": lat3, "lng": lon3, "text": anticipare}, "anuntata": False})
        indicatii.append({"lat": lat3, "lng": lon3, "text": {"lat": lat3, "lng": lon3, "text": final}, "anuntata": False})

    coordonate_ruta = [(graf.nodes[n]['y'], graf.nodes[n]['x']) for n in ruta]
    distanta = sum(geodesic(coordonate_ruta[i], coordonate_ruta[i + 1]).meters for i in range(len(coordonate_ruta) - 1))
    # durata = int(distanta / (5000 / 60))

    return indicatii, coordonate_ruta, durata

def obtine_ruta(start, end, nod_familiar=None, noduri_intermediare=None):
    graf = incarca_graf()
    oprire = noduri_intermediare[0] if noduri_intermediare else None

    ruta_noduri, durata_totala = bidirectional_dijkstra_modificat(
        G=graf,
        start=start,
        end=end,
        oprire=oprire,
        nod_familiar=nod_familiar
    )

    coordonate_ruta = [(graf.nodes[n]['y'], graf.nodes[n]['x']) for n in ruta_noduri]
    indicatii = []
    for i in range(len(ruta_noduri) - 2):
        u, v, w = ruta_noduri[i], ruta_noduri[i + 1], ruta_noduri[i + 2]
        lat1, lon1 = graf.nodes[u]['y'], graf.nodes[u]['x']
        lat2, lon2 = graf.nodes[v]['y'], graf.nodes[v]['x']
        lat3, lon3 = graf.nodes[w]['y'], graf.nodes[w]['x']

        angle = calculeaza_unghi((lat1, lon1), (lat2, lon2), (lat3, lon3))
        directie = genereaza_indicatie(angle)

        anticipare = f"In cativa pasi, {directie.lower()}."
        final = f"Acum, {directie.lower()}."

        indicatii.append({"lat": lat2, "lng": lon2, "text": {"lat": lat3, "lng": lon3, "text": anticipare}, "anuntata": False})
        indicatii.append({"lat": lat3, "lng": lon3, "text": {"lat": lat3, "lng": lon3, "text": final}, "anuntata": False})

    return indicatii, coordonate_ruta, durata_totala
