print("CEVA1")
from heapq import heappop, heappush
from itertools import count
import networkx as nx
print("CEVA1")
def _dijkstra_multisource(
    G, sources, weight, pred=None, paths=None, cutoff=None, target=None
):
    G_succ = G._adj  # Works for both directed and undirected graphs
    dist = {}
    seen = {}
    c = count()
    fringe = []

    for source in sources:
        seen[source] = 0
        heappush(fringe, (0, next(c), source))

    while fringe:
        (d, _, v) = heappop(fringe)
        if v in dist:
            continue
        dist[v] = d
        if v == target:
            break
        for u, e in G_succ[v].items():
            cost = weight(v, u, e)
            if cost is None:
                continue
            vu_dist = dist[v] + cost
            if cutoff is not None and vu_dist > cutoff:
                continue
            if u in dist:
                u_dist = dist[u]
                if vu_dist < u_dist:
                    raise ValueError("Contradictory paths found:", "negative weights?")
                elif pred is not None and vu_dist == u_dist:
                    pred[u].append(v)
            elif u not in seen or vu_dist < seen[u]:
                seen[u] = vu_dist
                heappush(fringe, (vu_dist, next(c), u))
                if paths is not None:
                    paths[u] = paths[v] + [u]
                if pred is not None:
                    pred[u] = [v]
            elif vu_dist == seen[u]:
                if pred is not None:
                    pred[u].append(v)

    return dist

print("CEVA1")
def my_shortest_path_dijkstra(G, source, target, weight="length"):
    def weight_func(u, v, d):
        return d.get(weight, 1)

    paths = {source: [source]}
    dist = _dijkstra_multisource(G, [source], weight_func, paths=paths, target=target)

    if target not in paths:
        raise nx.NetworkXNoPath(f"No path between {source} and {target}.")

    return paths[target]
