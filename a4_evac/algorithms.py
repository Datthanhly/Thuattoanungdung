"""Self-written graph algorithms; NetworkX is used ONLY by tests."""

from collections import deque
from dataclasses import dataclass
import heapq
from math import inf


def shortest_path(graph, source, exits, heuristic=None):
    h = heuristic or (lambda _: 0)
    distance, parent, heap, expanded = {source: 0}, {}, [(h(source), 0, source)], 0
    while heap:
        _, cost, u = heapq.heappop(heap)
        if cost != distance[u]:
            continue
        expanded += 1
        if u in exits:
            path = []
            while u != source:
                u, edge = parent[u]
                path.append(edge)
            return cost, path[::-1], expanded
        for v, weight, eid in graph.get(u, []):
            if weight < 0:
                raise ValueError("Nonnegative weights required")
            if cost + weight < distance.get(v, inf):
                distance[v], parent[v] = cost + weight, (u, eid)
                heapq.heappush(heap, (cost + weight + h(v), cost + weight, v))
    return inf, [], expanded


def multi_source(graph, sources):
    distance = {v: inf for v in graph}
    heap = []
    for node, start in sources:
        if start < distance.get(node, inf):
            distance[node] = start
            heapq.heappush(heap, (start, node))
    while heap:
        t, u = heapq.heappop(heap)
        if t != distance[u]:
            continue
        for v, weight in graph.get(u, []):
            if weight < 0:
                raise ValueError("Negative propagation time")
            if t + weight < distance.get(v, inf):
                distance[v] = t + weight
                heapq.heappush(heap, (t + weight, v))
    return distance


@dataclass(slots=True)
class Arc:
    to: int
    rev: int
    cap: int
    cost: int
    initial: int
    meta: tuple | None


class Network:
    def __init__(self, size=0):
        self.adj = [[] for _ in range(size)]
        self.forward = []

    def node(self):
        self.adj.append([])
        return len(self.adj) - 1

    def add(self, u, v, capacity, cost=0, meta=None):
        if not isinstance(capacity, int) or capacity < 0 or u == v:
            raise ValueError("Invalid capacity or self-loop")
        self.forward.append((u, len(self.adj[u])))
        self.adj[u].append(Arc(v, len(self.adj[v]), capacity, cost, capacity, meta))
        self.adj[v].append(Arc(u, len(self.adj[u]) - 1, 0, -cost, 0, None))

    def push(self, u, i, amount):
        e = self.adj[u][i]
        e.cap -= amount
        self.adj[e.to][e.rev].cap += amount


def dinic(net, source, sink, limit=None, admissible=None, stats=None):
    if source == sink:
        raise ValueError("Identical terminals")
    limit = sum(e.cap for e in net.adj[source]) if limit is None else limit
    flow = 0
    while flow < limit:
        level = [-1] * len(net.adj)
        level[source] = 0
        queue = deque([source])
        while queue:
            u = queue.popleft()
            for e in net.adj[u]:
                if e.cap and level[e.to] < 0 and (admissible is None or admissible(u, e)):
                    level[e.to] = level[u] + 1
                    queue.append(e.to)
        if level[sink] < 0:
            break
        if stats is not None:
            stats['level_phases'] = stats.get('level_phases', 0) + 1
        pointer = [0] * len(level)
        while flow < limit:
            stack, path = [source], []
            while stack and stack[-1] != sink:
                u = stack[-1]
                while pointer[u] < len(net.adj[u]):
                    e = net.adj[u][pointer[u]]
                    if e.cap and level[e.to] == level[u] + 1 and (admissible is None or admissible(u, e)):
                        break
                    pointer[u] += 1
                if pointer[u] == len(net.adj[u]):
                    level[u] = -1
                    stack.pop()
                    if path:
                        parent, _ = path.pop()
                        pointer[parent] += 1
                else:
                    path.append((u, pointer[u]))
                    stack.append(net.adj[u][pointer[u]].to)
            if not stack:
                break
            amount = min(limit - flow, min(net.adj[u][i].cap for u, i in path))
            for u, i in path:
                net.push(u, i, amount)
            flow += amount
            if stats is not None:
                stats['augmentations'] = stats.get('augmentations', 0) + 1
    return flow


def min_cost(net, source, sink, required, stats=None):
    """SSAP + potentials. Forward costs must initially be nonnegative."""
    if any(net.adj[u][i].cost < 0 for u, i in net.forward):
        raise ValueError("This implementation requires nonnegative initial forward costs")
    n, potential, flow, cost = len(net.adj), [0] * len(net.adj), 0, 0
    while flow < required:
        distance, parent = [inf] * n, [None] * n
        distance[source] = 0
        heap = [(0, source)]
        while heap:
            d, u = heapq.heappop(heap)
            if d != distance[u]:
                continue
            for i, e in enumerate(net.adj[u]):
                if not e.cap:
                    continue
                reduced = e.cost + potential[u] - potential[e.to]
                if d + reduced < distance[e.to]:
                    distance[e.to] = d + reduced
                    parent[e.to] = u, i
                    heapq.heappush(heap, (distance[e.to], e.to))
        if distance[sink] == inf:
            break
        if stats is not None:
            stats['cost_phases'] = stats.get('cost_phases', 0) + 1
        for v, d in enumerate(distance):
            if d != inf:
                potential[v] += d
        # Every zero-reduced-cost source/sink path has the same original
        # cost p[t]-p[s]. Push a complete blocking flow through these paths
        # rather than running a full heap search for each small group.
        delta = dinic(net, source, sink, required - flow,
                      lambda u, e: e.cost + potential[u] - potential[e.to] == 0, stats=stats)
        if not delta:
            raise RuntimeError("No admissible shortest path after potential update")
        cost += delta * (potential[sink] - potential[source])
        flow += delta
    return flow, cost
