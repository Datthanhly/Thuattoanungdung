"""Simple monotone hazard schedule; source times are assumptions, not forecasts."""

from dataclasses import dataclass, field, asdict
import heapq
from math import inf, isfinite
from .algorithms import multi_source


@dataclass
class Scenario:
    id: str = "safe"
    duration_seconds: int = 900
    seed: int = 2026
    fire_sources: list = field(default_factory=list)
    smoke_sources: list = field(default_factory=list)
    node_closures: dict = field(default_factory=dict)
    edge_closures: dict = field(default_factory=dict)
    description: str = "Full capacity is an assumed attendance scenario."


def scenario_named(name, duration=900, seed=2026):
    if name == "safe":
        return Scenario(name, duration, seed)
    if name == "smoke":
        return Scenario(name, duration, seed, [("R403", 180)], [("R403", 120)],
                        description="Assumed fire/smoke in room 403")
    if name == "stair_block":
        return Scenario(name, duration, seed, smoke_sources=[("S4_1", 90)],
                        description="Assumed smoke reaches stair core 1, floor 4, at 90s")
    if name == "exit_block":
        return Scenario(name, duration, seed, node_closures={"EXIT1": 120},
                        description="Assumed stair-1 discharge area on the open ground corridor becomes inaccessible at 120s; ground-room doors remain exits")
    raise ValueError(f"Unknown scenario {name}")


@dataclass
class Hazards:
    fire: dict
    smoke: dict
    nodes: dict
    edges: dict

    def safe_node(self, node, seconds):
        return seconds < self.nodes[node]

    def safe_move(self, edge, depart, arrive):
        return self.safe_node(edge.source, depart) and self.safe_node(edge.target, arrive) and arrive < self.edges[edge.id]


def simulate_hazards(b, scenario):
    graph_fire, graph_smoke = {n.id: [] for n in b.nodes}, {n.id: [] for n in b.nodes}
    p = b.parameters
    for e in b.edges:
        graph_fire[e.source].append((e.target, e.length_m / p["fire_propagation_m_s"]))
        smoke = e.length_m / p["smoke_propagation_m_s"]
        if e.kind == "STAIR_DOWN":
            smoke = p["smoke_downstairs_seconds"]
            graph_smoke[e.target].append((e.source, p["smoke_upstairs_seconds"]))
            graph_fire[e.target].append((e.source, e.length_m / p["fire_propagation_m_s"]))
        graph_smoke[e.source].append((e.target, smoke))
        if e.kind in {"ROOM_DOOR", "DOOR_CORRIDOR"}:
            graph_fire[e.target].append((e.source, e.length_m / p["fire_propagation_m_s"]))
            graph_smoke[e.target].append((e.source, e.length_m / p["smoke_propagation_m_s"]))
    for sources in (scenario.fire_sources, scenario.smoke_sources):
        for node, t in sources:
            if node not in b.node_by_id or not isinstance(t, (int, float)) or not isfinite(t) or t < 0:
                raise ValueError("Invalid hazard source")
    for name, closures, ids in (("node", scenario.node_closures, b.node_by_id), ("edge", scenario.edge_closures, b.edge_by_id)):
        for key, t in closures.items():
            if key not in ids or not isinstance(t, (int, float)) or not isfinite(t) or t < 0:
                raise ValueError(f"Invalid {name} closure")
    fire, smoke = multi_source(graph_fire, scenario.fire_sources), multi_source(graph_smoke, scenario.smoke_sources)
    nodes = {n.id: min(fire[n.id], smoke[n.id], scenario.node_closures.get(n.id, inf)) for n in b.nodes}
    edges = {e.id: min(nodes[e.source], nodes[e.target], scenario.edge_closures.get(e.id, inf)) for e in b.edges}
    return Hazards(fire, smoke, nodes, edges)


def safe_path(b, hazards, source, step=0):
    if not hazards.safe_node(source, step * b.dt):
        return inf, []
    distance, parent, heap = {source: step}, {}, [(step, source)]
    while heap:
        k, u = heapq.heappop(heap)
        if k != distance[u]:
            continue
        if u in b.exits:
            path = []
            while u != source:
                u, eid = parent[u]
                path.append(eid)
            return k - step, path[::-1]
        for e in b.outgoing[u]:
            arrival = k + e.steps(b.dt)
            if e.entry_capacity and hazards.safe_move(e, k * b.dt, arrival * b.dt) and arrival < distance.get(e.target, inf):
                distance[e.target], parent[e.target] = arrival, (u, e.id)
                heapq.heappush(heap, (arrival, e.target))
    return inf, []
