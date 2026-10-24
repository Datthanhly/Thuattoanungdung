"""Integral journeys and an independent capacity/safety validator."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Action:
    kind: str
    source: str
    target: str
    depart: int
    arrive: int
    edge_id: str | None = None


@dataclass
class Journey:
    id: str
    source: str
    count: int
    actions: list[Action] = field(default_factory=list)
    exit_node: str | None = None
    exit_step: int | None = None


def occupancy_valid(b, occupancy):
    for node, amount in occupancy.items():
        if node not in b.full_occupancy or isinstance(amount, bool) or not isinstance(amount, int) or not 0 <= amount <= b.full_occupancy[node]:
            raise ValueError(f"Occupancy outside room capacity: {node}")


def usages(schedule):
    nodes, entries, transit, exits, queues = Counter(), Counter(), Counter(), Counter(), Counter()
    for j in schedule:
        visits = {(j.source, 0)}
        for a in j.actions:
            if a.kind == "WAIT":
                visits.update((a.source, k) for k in range(a.depart, a.arrive + 1))
                for k in range(a.depart, a.arrive):
                    queues[a.source, k] += j.count
            else:
                visits.update(((a.source, a.depart), (a.target, a.arrive)))
                entries[a.edge_id, a.depart] += j.count
                for k in range(a.depart, a.arrive):
                    transit[a.edge_id, k] += j.count
        for v, k in visits:
            nodes[v, k] += j.count
        if j.exit_step is not None:
            exits[j.exit_node, j.exit_step] += j.count
    return nodes, entries, transit, exits, queues


def validate_schedule(b, hazards, schedule, occupancy, horizon):
    occupancy_valid(b, occupancy)
    errors, safety, capacity = [], [], []
    assigned, ids = Counter(), set()
    for j in schedule:
        if j.id in ids or j.source not in occupancy or not isinstance(j.count, int) or isinstance(j.count, bool) or j.count <= 0:
            errors.append(f"Invalid source/count/duplicate journey {j.id}")
            continue
        ids.add(j.id)
        assigned[j.source] += j.count
        node, step = j.source, 0
        for a in j.actions:
            if (a.source != node or a.depart != step or not isinstance(a.depart, int) or isinstance(a.depart, bool)
                    or not isinstance(a.arrive, int) or isinstance(a.arrive, bool) or a.arrive <= step):
                errors.append(f"Discontinuous journey {j.id}")
                continue
            if a.kind == "WAIT":
                if a.target != node or not b.node_by_id[node].can_wait or a.edge_id is not None:
                    errors.append(f"Illegal wait {j.id}")
                for k in range(a.depart, a.arrive + 1):
                    if not hazards.safe_node(node, k * b.dt):
                        safety.append(f"Unsafe wait {j.id}@{k}")
            elif a.kind == "MOVE":
                e = b.edge_by_id.get(a.edge_id)
                if e is None or (e.source, e.target) != (a.source, a.target) or a.arrive - a.depart != e.steps(b.dt):
                    errors.append(f"Invalid edge/duration {j.id}")
                elif not hazards.safe_move(e, a.depart * b.dt, a.arrive * b.dt):
                    safety.append(f"Unsafe movement {j.id}/{e.id}")
            else:
                errors.append(f"Unknown action {j.id}")
            node, step = a.target, a.arrive
        if step > horizon:
            errors.append(f"Horizon exceeded {j.id}")
        if j.exit_step is not None and (node not in b.exits or node != j.exit_node or step != j.exit_step):
            errors.append(f"Invalid exit {j.id}")
        if j.exit_step is None and (node in b.exits or j.exit_node is not None):
            errors.append(f"Missing exit event {j.id}")
    if errors:
        return {"valid": False, "errors": errors, "capacity_violations": 0, "safety_violations": len(safety), "structural_violations": len(errors)}
    nodes, entries, transit, exits, _ = usages(schedule)
    for source, count in occupancy.items():
        if assigned[source] > count:
            errors.append(f"Supply exceeded at {source}")
        for k in range(horizon + 1):
            if hazards.safe_node(source, k * b.dt):
                nodes[source, k] += max(0, count - assigned[source])
    for j in schedule:
        if j.exit_step is None:
            node = j.actions[-1].target if j.actions else j.source
            step = j.actions[-1].arrive if j.actions else 0
            for k in range(step + 1, horizon + 1):
                if hazards.safe_node(node, k * b.dt):
                    nodes[node, k] += j.count
    for (node, k), count in nodes.items():
        if count > b.node_by_id[node].storage_capacity:
            capacity.append(f"Storage {node}@{k}: {count}")
        if not hazards.safe_node(node, k * b.dt):
            safety.append(f"Unsafe node {node}@{k}")
    for (eid, k), count in entries.items():
        if count > b.edge_by_id[eid].entry_capacity:
            capacity.append(f"Entry {eid}@{k}")
    for (eid, k), count in transit.items():
        if count > b.edge_by_id[eid].in_transit_capacity:
            capacity.append(f"Transit {eid}@{k}")
    for (node, k), count in exits.items():
        if count > b.node_by_id[node].exit_capacity:
            capacity.append(f"Exit {node}@{k}")
    return {"valid": not errors and not safety and not capacity, "errors": errors + safety + capacity,
            "capacity_violations": len(capacity), "safety_violations": len(safety), "structural_violations": len(errors)}


def simulation_trace(b, hazards, schedule, occupancy, horizon):
    nodes, entries, transit, exits, queues = usages(schedule)
    departures = Counter()
    for j in schedule:
        for a in j.actions:
            if a.kind == "MOVE":
                departures[a.source, a.depart] += j.count
    assigned = Counter()
    stopped = []
    for j in schedule:
        assigned[j.source] += j.count
        if j.exit_step is None:
            stopped.append((j.actions[-1].target if j.actions else j.source,
                            j.actions[-1].arrive if j.actions else 0, j.count))
    for source, count in occupancy.items():
        if count > assigned[source]:
            stopped.append((source, -1, count - assigned[source]))
    trace, escaped = [], 0
    for k in range(horizon + 1):
        exposed = 0
        for node, last, count in stopped:
            if k > last:
                if hazards.safe_node(node, k * b.dt):
                    nodes[node, k] += count
                    queues[node, k] += count
                else:
                    exposed += count
        escaped += sum(exits[e, k] for e in b.exits)
        after = {n.id: nodes[n.id, k] - departures[n.id, k] - exits[n.id, k] for n in b.nodes
                 if nodes[n.id, k] - departures[n.id, k] - exits[n.id, k]}
        active = {e.id: transit[e.id, k] for e in b.edges if transit[e.id, k]}
        if sum(after.values()) + sum(active.values()) + escaped + exposed != sum(occupancy.values()):
            raise RuntimeError("Replay population conservation failed")
        trace.append({"time_seconds": k * b.dt, "evacuated_total": escaped,
                      "remaining_total": sum(occupancy.values()) - escaped, "exposed_unplanned_total": exposed,
                      "node_occupancy_before_departure": {n.id: nodes[n.id, k] for n in b.nodes if nodes[n.id, k]},
                      "node_occupancy": after, "active_moves": active,
                      "edge_entries": {e.id: entries[e.id, k] for e in b.edges if entries[e.id, k]},
                      "queues": {n.id: queues[n.id, k] for n in b.nodes if queues[n.id, k]},
                      "unsafe_nodes": [n.id for n in b.nodes if not hazards.safe_node(n.id, k * b.dt)]})
    return trace
