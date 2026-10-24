"""M1 static, M2 hazard-aware rerouting, M3 capacity-aware greedy routing."""

from collections import Counter
import math
from .algorithms import shortest_path
from .hazards import safe_path
from .optimize import Result
from .schedule import Action, Journey, validate_schedule


def baseline(b, hazards, occupancy, horizon, method, m3_weight=4.0):
    if method not in {"M1", "M1E", "M2", "M3"}:
        raise ValueError("Unknown baseline")
    if not math.isfinite(m3_weight) or m3_weight < 0:
        raise ValueError('M3 weight must be finite and nonnegative')
    graph = {n.id: [] for n in b.nodes}
    for e in b.edges:
        if e.entry_capacity and hazards.safe_move(e, 0, 0):
            graph[e.source].append((e.target, e.steps(b.dt), e.id))
    fixed = {n: shortest_path(graph, n, b.exits)[1] for n in occupancy}
    split_routes = {(n, core): shortest_path(graph, n, {f'EXIT{core}'})[1]
                    for n in occupancy if b.node_by_id[n].floor > 1 for core in (1, 2)} if method == 'M1E' else {}
    split_index = 0
    storage, entries, exits, cache = Counter(), Counter(), Counter(), {}
    people, schedule = [], []
    for source, count in sorted(occupancy.items()):
        for k in range(horizon + 1):
            if hazards.safe_node(source, k * b.dt):
                storage[source, k] += count
        if not hazards.safe_node(source, 0):
            continue
        for _ in range(count):
            j = Journey(f"P{len(schedule)+1:05}", source, 1)
            schedule.append(j)
            route = fixed[source]
            if method == 'M1E' and b.node_by_id[source].floor > 1:
                route = split_routes[source, 1 + split_index % 2]
                split_index += 1
            people.append({"j": j, "node": source, "ready": 0, "index": 0, "stopped": False, 'route': route})

    def path(node, k):
        if (node, k) not in cache:
            cache[node, k] = safe_path(b, hazards, node, k)
        return cache[node, k]

    def fits(e, k):
        arrival = k + e.steps(b.dt)
        if arrival > horizon or entries[e.id, k] >= e.entry_capacity or not hazards.safe_move(e, k * b.dt, arrival * b.dt):
            return False
        n = b.node_by_id[e.target]
        if n.kind == "EXIT":
            return exits[n.id, arrival] < n.exit_capacity and storage[n.id, arrival] < n.storage_capacity
        return all(storage[n.id, t] < n.storage_capacity for t in range(arrival, horizon + 1)
                   if hazards.safe_node(n.id, t * b.dt))

    for k in range(horizon):
        for person in people:
            j, node = person["j"], person["node"]
            if j.exit_step is not None or person["stopped"] or person["ready"] > k:
                continue
            candidates = []
            if method in {"M1", "M1E"}:
                route = person['route']
                if person["index"] < len(route):
                    candidates = [b.edge_by_id[route[person["index"]]]]
            elif method == "M2":
                route = path(node, k)[1]
                if route:
                    candidates = [b.edge_by_id[route[0]]]
            else:
                scored = []
                for e in b.outgoing[node]:
                    if not fits(e, k):
                        continue
                    arrival = k + e.steps(b.dt)
                    remaining, route = path(e.target, arrival)
                    if remaining == float("inf"):
                        continue
                    score = e.steps(b.dt) + remaining + m3_weight * entries[e.id, k] / max(1, e.entry_capacity)
                    score += m3_weight * storage[e.target, arrival] / max(1, b.node_by_id[e.target].storage_capacity)
                    scored.append((score, e.id, e))
                candidates = [v[2] for v in sorted(scored)]
            e = next((e for e in candidates if fits(e, k)), None)
            if e is not None:
                arrival = k + e.steps(b.dt)
                entries[e.id, k] += 1
                for t in range(k + 1, horizon + 1):
                    if hazards.safe_node(node, t * b.dt):
                        storage[node, t] -= 1
                n = b.node_by_id[e.target]
                if n.kind == "EXIT":
                    exits[n.id, arrival] += 1
                    storage[n.id, arrival] += 1
                    j.exit_node, j.exit_step = n.id, arrival
                else:
                    for t in range(arrival, horizon + 1):
                        if hazards.safe_node(n.id, t * b.dt):
                            storage[n.id, t] += 1
                j.actions.append(Action("MOVE", node, n.id, k, arrival, e.id))
                person["node"], person["ready"] = n.id, arrival
                person["index"] += 1
            elif b.node_by_id[node].can_wait and hazards.safe_node(node, (k + 1) * b.dt):
                j.actions.append(Action("WAIT", node, node, k, k + 1))
            else:
                person["stopped"] = True
    report = validate_schedule(b, hazards, schedule, occupancy, horizon)
    if not report["valid"]:
        raise RuntimeError("Baseline validation failed: " + "; ".join(report["errors"][:5]))
    count = sum(j.count for j in schedule if j.exit_step is not None)
    return Result(method, "COMPLETE" if count == sum(occupancy.values()) else "INCOMPLETE",
                  schedule, count, sum(occupancy.values()), horizon,
                  details={"tie_breaking": "source/person ID", "reservations": "hold node until committed departure",
                           "m3_weight": m3_weight if method == 'M3' else None,
                           "equal_stair_split": method == 'M1E'})
