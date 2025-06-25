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
    lista_vizite = incarca_vizite(FISIER_VIZITE)

    start_node = nearest_node(graf, start)
    end_node = nearest_node(graf, end)

    _, ruta = bidirectional_dijkstra_modificat(
        graf, start_node, end_node, lista_vizite, nod_intermediar=None
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
    durata = int(distanta / (5000 / 60))

    return indicatii, coordonate_ruta, durata


def obtine_ruta(start, end, nod_familiar=None, noduri_intermediare=None):
    traseu = [start] + (noduri_intermediare or [])
    if nod_familiar:
        traseu.append(nod_familiar)
    traseu.append(end)

    toate_indicatiile, toate_coord, durata_totala = [], [], 0

    for i in range(len(traseu) - 1):
        ind, coord, durata = obtine_ruta_segment(traseu[i], traseu[i + 1])
        toate_indicatiile.extend(ind)
        toate_coord.extend(coord if i == 0 else coord[1:])
        durata_totala += durata

    return toate_indicatiile, toate_coord, durata_totala


def obtine_ruta_standard(start, end):
    graf = incarca_graf()
    start_node = nearest_node(graf, start)
    end_node = nearest_node(graf, end)

    _, ruta = nx_bidirectional_dijkstra(graf, start_node, end_node, weight='length')
    coordonate = [(graf.nodes[n]['y'], graf.nodes[n]['x']) for n in ruta]

    distanta = sum(geodesic(coordonate[i], coordonate[i + 1]).meters for i in range(len(coordonate) - 1))
    durata = int(distanta / (5000 / 60))
    return coordonate, durata


def obtine_ruta_ors(start, end, api_key):
    client = openrouteservice.Client(key=api_key)
    coords = [(start[1], start[0]), (end[1], end[0])]

    try:
        result = client.directions(
            coordinates=coords,
            profile='foot-walking',
            format='geojson',
            language='ro',
            instructions=True
        )

        indicatii = []
        geometry = result['features'][0]['geometry']['coordinates']
        durata_sec = result['features'][0]['properties']['segments'][0]['duration']
        durata_min = int(durata_sec // 60)

        for step in result['features'][0]['properties']['segments'][0]['steps']:
            instructiune = step['instruction']
            if "Direcția {" in instructiune or "direction {" in instructiune:
                continue
            dist = step['distance']
            indicatii.append(f"{instructiune}. Dupa care mergeti: {dist:.0f} metri.")

        coordonate = [(lat, lon) for lon, lat in geometry]
        return indicatii, coordonate, durata_min

    except Exception as e:
        print("Eroare ORS:", e)
        return [], []
