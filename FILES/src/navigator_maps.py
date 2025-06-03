import osmnx as ox 
import networkx as nx 
from geopy.distance import geodesic
from gtts import gTTS
import os 
import math 
import folium
import openrouteservice
import json
from shapely.geometry import Point
from osmnx.distance import nearest_edges

print("CEVA")
from my_dijkstra import my_shortest_path_dijkstra
print("CEVAs")

def nearest_point_on_edge(g, point):
    u, v, key = nearest_edges(g, point[1], point[0])
    edge_data = g[u][v][key]
    #coordonatele nodurilor u și v
    lat_u, lon_u = g.nodes[u]['y'], g.nodes[u]['x']
    lat_v, lon_v = g.nodes[v]['y'], g.nodes[v]['x']

    # proiecte pt punctului pe segmentul [u,v] (interpolare)
    point_geom = Point(point[1], point[0])
    line = Point(lon_u, lat_u).buffer(0.0001).union(Point(lon_v, lat_v).buffer(0.0001)).convex_hull
    if not line.contains(point_geom):
        #daca punctul nu e intre u-v, alegem nodul cel mai apropiat
        return u if geodesic((lat_u, lon_u), point).meters < geodesic((lat_v, lon_v), point).meters else v
    return u


def calculeaza_unghi(p1, p2, p3):
    v1 = (p2[0] - p1[0], p2[1] - p1[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])
    prod = v1[0]*v2[0] + v1[1]*v2[1]
    norm_u = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
    norm_v = math.sqrt(v2[0] ** 2 + v2[1] ** 2)
    if norm_u*norm_v == 0:
        return 0

    cos_angle = prod / (norm_u * norm_v)
    cos_angle = max(-1, min(1, cos_angle))
    angle = math.degrees(math.acos(cos_angle))

    determinant = v1[0]*v2[1] - v1[1]*v2[0]
    return angle if determinant > 0 else -angle


def nearest_node(graf, coord):
    return ox.distance.nearest_nodes(graf, X=coord[1], Y=coord[0])


def genereaza_indicatie(angle):
    prag_dreapta = 20
    prag_stanga = -20
    if angle > prag_dreapta:
        return "La dreapta"
    elif angle < prag_stanga:
        return "La stanga"
    return "Inainte"


def salveaza_harta(graf, ruta, extra_points=None):
    noduri = [(graf.nodes[n]['y'], graf.nodes[n]['x']) for n in ruta]
    m = folium.Map(location=noduri[0], zoom_start=15)
    folium.PolyLine(noduri, color='blue', weight=5).add_to(m)
    folium.Marker(noduri[0], tooltip='Start').add_to(m)
    folium.Marker(noduri[-1], tooltip='Finish').add_to(m)
    if extra_points:
        for idx, pt in enumerate(extra_points):
            folium.Marker(pt, tooltip=f'Oprire {idx+1}', icon=folium.Icon(color='green')).add_to(m)
    m.save('maps.html')


def obtine_ruta(start, end, fol_edge_for_poi=False):
    if not os.path.exists("timisoara.graphml"):
        timisoara_g = ox.graph_from_place("Timișoara, Romania", network_type="walk")
        ox.save_graphml(timisoara_g, "timisoara.graphml")
    else:
        timisoara_g = ox.load_graphml("timisoara.graphml")

    start_node = nearest_node(timisoara_g, start)
    if fol_edge_for_poi:
        end_node = nearest_point_on_edge(timisoara_g, end)
    else:
        end_node = nearest_node(timisoara_g, end)

    ruta =  my_shortest_path_dijkstra(timisoara_g, start_node, end_node, weight='length')

    indicatii = []
    for i in range(len(ruta) - 2):
        u, v, w = ruta[i], ruta[i + 1], ruta[i + 2]
        lat1, lon1 = timisoara_g.nodes[u]['y'], timisoara_g.nodes[u]['x']
        lat2, lon2 = timisoara_g.nodes[v]['y'], timisoara_g.nodes[v]['x']
        lat3, lon3 = timisoara_g.nodes[w]['y'], timisoara_g.nodes[w]['x']

        distanta = geodesic((lat1, lon1), (lat2, lon2)).meters
        angle = calculeaza_unghi((lat1, lon1), (lat2, lon2), (lat3, lon3))
        indicatie_directie = genereaza_indicatie(angle)
        mesaj = f"Mergi aproximativ {distanta:.1f} metri, apoi {indicatie_directie}"
        indicatii.append(mesaj)

    total_distance = sum(
        geodesic(
            (timisoara_g.nodes[ruta[i]]['y'], timisoara_g.nodes[ruta[i]]['x']),
            (timisoara_g.nodes[ruta[i + 1]]['y'], timisoara_g.nodes[ruta[i + 1]]['x'])
        ).meters for i in range(len(ruta) - 1)
    )
    duration_min = int(total_distance / (5000 / 60))

    coordonate_ruta = [(timisoara_g.nodes[n]['y'], timisoara_g.nodes[n]['x']) for n in ruta]

    extra_points = []
    if fol_edge_for_poi:
        coordonate_ruta.append(end)
        extra_points.append(end)

    salveaza_harta(timisoara_g, ruta, extra_points=extra_points)
    return indicatii, coordonate_ruta, duration_min


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
        coordonate_ruta = []

        steps = result['features'][0]['properties']['segments'][0]['steps']
        geometry = result['features'][0]['geometry']['coordinates']
        duration_sec = result['features'][0]['properties']['segments'][0]['duration']
        duration_min = int(duration_sec // 60)

        for step in steps:
            dist = step['distance']
            instructiune = step['instruction']

            if "Direcția {" in instructiune or "direction {" in instructiune:
                continue

            instructiune_formatata = f"{instructiune}. Dupa care mergeti: {dist:.0f} metri."
            indicatii.append(instructiune_formatata)

        coordonate_ruta = [(lat, lon) for lon, lat in geometry]

        return indicatii, coordonate_ruta, duration_min

    except Exception as e:
        print("Eroare ORS:", e)
        return [], []


# start = (45.72787, 21.23604) #Kaufland martirilor
# end = (45.73559, 21.25672) #altex stand vidrighin
# indicatii = obtine_ruta(start,end)
# for indicatie in indicatii:
#     print(indicatie)

#pentru a apela din main, comenteaza liniile 87-91 si decomenteaza 94-97
# def calcul_traseu(start,end):
#     indicatii = obtine_ruta(start,end)
#     for indicatie in indicatii:
#         print(indicatie)