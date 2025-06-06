import networkx as nx
from heapq import heappop, heappush
from itertools import count 
from geopy.distance import geodesic
import osmnx as ox

def _weight_function(G, weight):
    if callable(weight):
        return weight
    # If the weight keyword argument is not callable, we assume it is a
    # string representing the edge attribute containing the weight of
    # the edge.
    if G.is_multigraph():
        return lambda u, v, d: min(attr.get(weight, 1) for attr in d.values())
    return lambda u, v, data: data.get(weight, 1)

def bidirectional_dijkstra(G, source, target, weight="weight"):
    if source not in G:
        raise nx.NodeNotFound(f"Source {source} is not in G")

    if target not in G:
        raise nx.NodeNotFound(f"Target {target} is not in G")

    if source == target:
        return (0, [source])

    weight = _weight_function(G, weight)
    # Init:  [Forward, Backward]
    dists = [{}, {}]  # dictionary of final distances
    paths = [{source: [source]}, {target: [target]}]  # dictionary of paths
    fringe = [[], []]  # heap of (distance, node) for choosing node to expand
    seen = [{source: 0}, {target: 0}]  # dict of distances to seen nodes
    c = count()
    # initialize fringe heap
    heappush(fringe[0], (0, next(c), source))
    heappush(fringe[1], (0, next(c), target))
    # neighs for extracting correct neighbor information
    if G.is_directed():
        neighs = [G._succ, G._pred]
    else:
        neighs = [G._adj, G._adj]
    # variables to hold shortest discovered path
    # finaldist = 1e30000
    finaldist = float('inf')
    finalpath = []
    dir = 1
    while fringe[0] and fringe[1]:
        # choose direction
        # dir == 0 is forward direction and dir == 1 is back
        dir = 1 - dir
        # extract closest to expand
        (dist, _, v) = heappop(fringe[dir])
        if v in dists[dir]:
            # Shortest path to v has already been found
            continue
        # update distance
        dists[dir][v] = dist  # equal to seen[dir][v]
        if v in dists[1 - dir]:
            # if we have scanned v in both directions we are done
            # we have now discovered the shortest path
            return (finaldist, finalpath)

        for w, d in neighs[dir][v].items():
            # weight(v, w, d) for forward and weight(w, v, d) for back direction
            cost = weight(v, w, d) if dir == 0 else weight(w, v, d)
            if cost is None:
                continue
            vwLength = dists[dir][v] + cost
            if w in dists[dir]:
                if vwLength < dists[dir][w]:
                    raise ValueError("Contradictory paths found: negative weights?")
            elif w not in seen[dir] or vwLength < seen[dir][w]:
                # relaxing
                seen[dir][w] = vwLength
                heappush(fringe[dir], (vwLength, next(c), w))
                paths[dir][w] = paths[dir][v] + [w]
                if w in seen[0] and w in seen[1]:
                    # see if this path is better than the already
                    # discovered shortest path
                    totaldist = seen[0][w] + seen[1][w]
                    if finalpath == [] or finaldist > totaldist:
                        finaldist = totaldist
                        revpath = paths[1][w][:]
                        revpath.reverse()
                        finalpath = paths[0][w] + revpath[1:]
    raise nx.NetworkXNoPath(f"No path between {source} and {target}.")


def scor_familiaritate(coord, distanta, nr_vizite, distanta_maxima = 2000):
    if distanta > distanta_maxima:
        return 0
    scor = nr_vizite * (1 - (distanta / distanta_maxima))
    return max(scor, 0)



def gaseste_nod_familiar(source_coord, target_coord, vizite_json):
    best_nod = None
    best_scor = -1
    dist_directa = geodesic(source_coord, target_coord).meters

    for punct in vizite_json:
        coord = (punct["lat"], punct["lng"])
        nr_vizite = punct["nr_vizite"]

        dist_la_start = geodesic(source_coord, coord).meters
        dist_la_final = geodesic(coord, target_coord).meters
        total_dist = dist_la_start + dist_la_final

        scor = scor_familiaritate(coord, total_dist, nr_vizite)
        print(f"[DEBUG] Candidat: {coord} | Total dist: {total_dist:.1f}m | Scor: {scor:.2f}")

        if scor > best_scor:
            best_scor = scor
            best_nod = coord

    return best_nod


def bidirectional_dijkstra_modificat(G, source, target, vizite_json):
    # Pasul 1: extrage coordonatele din graf
    raw_coord_map = nx.get_node_attributes(G, 'coord')
    if not raw_coord_map:
        raise ValueError("Graful nu conține atributele coord pentru noduri")

    # Pasul 2: normalizează (rotunjește) la 6 zecimale
    coord_map = {k: (round(v[0], 6), round(v[1], 6)) for k, v in raw_coord_map.items()}
    inv_coord_map = {v: k for k, v in coord_map.items()}

    if source not in coord_map or target not in coord_map:
        print(f'[EROARE] coord_map nu conține nodurile {source} sau {target}')
        raise ValueError("Nodurile nu au coordonate")

    source_coord = coord_map[source]
    target_coord = coord_map[target]

    # Găsește nod familiar (intermediar)
    nod_intermediar_coord = gaseste_nod_familiar(source_coord, target_coord, vizite_json)
    print(f"[DEBUG] Nod familiar ales: {nod_intermediar_coord}")

    if nod_intermediar_coord:
        if nod_intermediar_coord in inv_coord_map:
            intermediar = inv_coord_map[nod_intermediar_coord]
            print(f"[DEBUG] Nod familiar găsit exact în graf: {intermediar}")
        else:
            # fallback: căutăm cel mai apropiat nod din graf de coordonata familiară
            try:
                intermediar = ox.distance.nearest_nodes(
                    G,
                    X=nod_intermediar_coord[1],  # lng
                    Y=nod_intermediar_coord[0]   # lat
                )
                print(f"[DEBUG] Fallback: cel mai apropiat nod de coordonata familiară: {intermediar}")
            except Exception as e:
                print(f"[WARN] Eroare la fallback nearest_nodes: {e}")
                intermediar = None
    else:
        intermediar = None

    # Dacă avem nod intermediar (din coordonata exactă sau fallback), îl includem în traseu
    if intermediar:
        dist1, path1 = bidirectional_dijkstra(G, source, intermediar)
        dist2, path2 = bidirectional_dijkstra(G, intermediar, target)
        return dist1 + dist2, path1[:-1] + path2
    else:
        print("[DEBUG] Nu a fost găsit niciun nod familiar. Continuăm direct.")
        return bidirectional_dijkstra(G, source, target)