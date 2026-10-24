"""Time-expanded max evacuation, earliest horizon and minimum sum exit times."""

from collections import defaultdict
from dataclasses import dataclass, field
from math import inf
import heapq
from time import perf_counter

from .algorithms import Network, dinic, min_cost
from .schedule import Action, Journey, occupancy_valid, validate_schedule


@dataclass
class Result:
    method: str
    status: str
    schedule: list
    evacuated: int
    total: int
    max_steps: int
    optimal_steps: int | None = None
    network_nodes: int = 0
    network_edges: int = 0
    details: dict = field(default_factory=dict)


def exit_lower_bounds(b):
    reverse = defaultdict(list)
    for e in b.edges:
        if e.entry_capacity:
            reverse[e.target].append((e.source, e.steps(b.dt)))
    distance, heap = {n.id: inf for n in b.nodes}, []
    for n in b.exits:
        distance[n] = 0
        heapq.heappush(heap, (0, n))
    while heap:
        d, u = heapq.heappop(heap)
        if d != distance[u]:
            continue
        for v, cost in reverse[u]:
            if d + cost < distance[v]:
                distance[v] = d + cost
                heapq.heappush(heap, (d + cost, v))
    return distance


def time_network(b, hazards, occupancy, horizon, lower=None):
    net, states = Network(2), {}
    lower = exit_lower_bounds(b) if lower is None else lower
    # Pruning by free-flow distance is valid even with queues: a person cannot
    # reach the exit faster than this lower bound on remaining travel time.
    for k in range(horizon + 1):
        for n in b.nodes:
            if k + lower[n.id] <= horizon and hazards.safe_node(n.id, k * b.dt):
                a, z = net.node(), net.node()
                states[n.id, k] = a, z
                net.add(a, z, n.storage_capacity)
                if n.kind == "EXIT":
                    net.add(z, 1, n.exit_capacity, k, ("exit", n.id, k))
    for source, count in occupancy.items():
        if (source, 0) in states:
            net.add(0, states[source, 0][0], count, meta=("source", source))
    for (node, k), (_, z) in states.items():
        n = b.node_by_id[node]
        if n.kind == "EXIT":
            continue
        if n.can_wait and (node, k + 1) in states:
            net.add(z, states[node, k + 1][0], n.storage_capacity, meta=("wait", node, k, k + 1))
        for e in b.outgoing[node]:
            arrival = k + e.steps(b.dt)
            if (e.target, arrival) in states and e.entry_capacity and hazards.safe_move(e, k * b.dt, arrival * b.dt):
                net.add(z, states[e.target, arrival][0], e.entry_capacity, meta=("move", e.id, k, arrival))
    return net


def decompose(net, b):
    positive, pointers = [[] for _ in net.adj], [0] * len(net.adj)
    flow = {}
    for u, i in net.forward:
        e = net.adj[u][i]
        value = e.initial - e.cap
        if value:
            positive[u].append(i)
            flow[u, i] = value
    schedule = []
    while any(flow[0, i] for i in positive[0]):
        path, u = [], 0
        while u != 1:
            while pointers[u] < len(positive[u]) and not flow[u, positive[u][pointers[u]]]:
                pointers[u] += 1
            if pointers[u] == len(positive[u]):
                raise RuntimeError("Flow conservation/decomposition error")
            i = positive[u][pointers[u]]
            path.append((u, i))
            u = net.adj[u][i].to
        count = min(flow[p] for p in path)
        source, actions, exit_node, exit_step = None, [], None, None
        for u, i in path:
            flow[u, i] -= count
            meta = net.adj[u][i].meta
            if meta is None:
                continue
            if meta[0] == "source":
                source = meta[1]
            elif meta[0] == "wait":
                _, node, start, end = meta
                actions.append(Action("WAIT", node, node, start, end))
            elif meta[0] == "move":
                _, eid, start, end = meta
                e = b.edge_by_id[eid]
                actions.append(Action("MOVE", e.source, e.target, start, end, eid))
            else:
                _, exit_node, exit_step = meta
        schedule.append(Journey(f"G{len(schedule)+1:05}", source, count, actions, exit_node, exit_step))
    return schedule


def optimize(b, hazards, occupancy, horizon):
    occupancy_valid(b, occupancy)
    if not isinstance(horizon, int) or horizon < 0:
        raise ValueError("Invalid horizon")
    total, lower, probes = sum(occupancy.values()), exit_lower_bounds(b), {}
    phase_times = {'build': 0.0, 'max_flow': 0.0, 'min_cost': 0.0, 'decompose_validate': 0.0}
    probe_stats, cost_stats = {}, {}

    def rescued(k):
        started = perf_counter()
        net = time_network(b, hazards, occupancy, k, lower)
        phase_times['build'] += perf_counter() - started
        started = perf_counter()
        value = dinic(net, 0, 1, total, stats=probe_stats)
        phase_times['max_flow'] += perf_counter() - started
        probes[k] = value
        return value

    maximum = rescued(horizon)
    lo, hi = 0, horizon
    while lo < hi:
        mid = (lo + hi) // 2
        if rescued(mid) >= maximum:
            hi = mid
        else:
            lo = mid + 1
    started = perf_counter()
    net = time_network(b, hazards, occupancy, lo, lower)
    phase_times['build'] += perf_counter() - started
    started = perf_counter()
    flow, cost = min_cost(net, 0, 1, maximum, stats=cost_stats)
    phase_times['min_cost'] += perf_counter() - started
    if flow != maximum:
        raise RuntimeError("Max flow / min-cost inconsistency")
    started = perf_counter()
    schedule = decompose(net, b)
    report = validate_schedule(b, hazards, schedule, occupancy, horizon)
    if not report["valid"]:
        raise RuntimeError("Independent validation failed: " + "; ".join(report["errors"][:5]))
    phase_times['decompose_validate'] = perf_counter() - started
    return Result("M4", "OPTIMAL_FOR_MODEL" if flow == total else "INFEASIBLE_WITHIN_HORIZON",
                  schedule, flow, total, horizon, lo if flow == total else None,
                  len(net.adj), len(net.forward), {"max_flow_probes": probes, "total_exit_steps": cost,
                                                   "last_rescue_step": lo if flow else None,
                                                   "phase_seconds": phase_times,
                                                   "probe_stats": probe_stats, "cost_stats": cost_stats})
