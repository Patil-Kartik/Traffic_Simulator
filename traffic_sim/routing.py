from __future__ import annotations

from typing import Dict, List, Tuple
import heapq


def shortest_path(nodes: Dict[str, Tuple[float, float]],
                  edges: Dict[Tuple[str, str], float],
                  source: str,
                  destination: str) -> List[str]:
    """Dijkstra shortest path over a directed graph.

    nodes: mapping of node id -> (x,y)
    edges: mapping of (u,v) -> weight
    returns list of node ids from source to destination inclusive.
    """
    if source == destination:
        return [source]

    adj: Dict[str, List[Tuple[float, str]]] = {}
    for (u, v), w in edges.items():
        adj.setdefault(u, []).append((w, v))

    pq = [(0.0, source)]
    dist = {source: 0.0}
    prev: Dict[str, str] = {}

    while pq:
        d, u = heapq.heappop(pq)
        if u == destination:
            break
        if d != dist.get(u, float('inf')):
            continue
        for w, v in adj.get(u, []):
            nd = d + w
            if nd < dist.get(v, float('inf')):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))

    if destination not in dist:
        raise ValueError(f"No route found from {source} to {destination}")

    path = [destination]
    while path[-1] != source:
        path.append(prev[path[-1]])
    path.reverse()
    return path
