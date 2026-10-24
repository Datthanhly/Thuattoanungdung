"""Measured runs, JSON/CSV snapshots and independent replay."""

from collections import Counter
from dataclasses import asdict
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time
import tracemalloc

from . import __version__
from .data import write_json, save_inputs
from .hazards import simulate_hazards
from .baselines import baseline
from .optimize import optimize
from .schedule import validate_schedule, simulation_trace, occupancy_valid


def make_occupancy(b, load=1.0, people=None, seed=2026):
    if not math.isfinite(load) or not 0 <= load <= 1:
        raise ValueError("load must be in [0,1]")
    if people is None:
        return {k: round(v * load) for k, v in b.full_occupancy.items() if round(v * load)}
    if isinstance(people, bool) or not isinstance(people, int) or not 0 <= people <= sum(b.full_occupancy.values()):
        raise ValueError("people must be an integer between 0 and 1360")
    rng, counts = random.Random(seed), Counter()
    available = sorted(b.full_occupancy)
    for _ in range(people):
        source = rng.choice(available)
        counts[source] += 1
        if counts[source] == b.full_occupancy[source]:
            available.remove(source)
    return dict(counts)


def run(b, scenario, occupancy, method="M4", memory=False, m3_weight=4.0):
    occupancy_valid(b, occupancy)
    hazards = simulate_hazards(b, scenario)
    horizon = int(scenario.duration_seconds // b.dt)
    if horizon < 0:
        raise ValueError("Negative horizon")
    if memory:
        tracemalloc.start()
    start = time.perf_counter()
    try:
        result = optimize(b, hazards, occupancy, horizon) if method == "M4" else baseline(b, hazards, occupancy, horizon, method, m3_weight=m3_weight)
        elapsed = time.perf_counter() - start
        peak = tracemalloc.get_traced_memory()[1] / 1024**2 if memory else None
    finally:
        if memory:
            tracemalloc.stop()
    validation = validate_schedule(b, hazards, result.schedule, occupancy, horizon)
    trace = simulation_trace(b, hazards, result.schedule, occupancy, horizon)
    complete = result.evacuated == result.total
    arrivals = [(j.exit_step * b.dt, j.count, j.exit_node) for j in result.schedule if j.exit_step is not None]
    total_exit = sum(t * c for t, c, _ in arrivals)
    throughput = Counter()
    for _, count, exit_node in arrivals:
        throughput[exit_node] += count
    payload = {"parameters": b.parameters, "rooms": b.rooms, "edges": [asdict(e) for e in b.edges],
               "occupancy": occupancy, "scenario": asdict(scenario), "source": "latest user diagram 2026-10-24"}
    metrics = {"method": method, "status": result.status, "completion_status": "COMPLETE" if complete else "INCOMPLETE",
               "software_version": __version__, "python_version": sys.version.split()[0],
               "building_id": b.building_id, "scenario_id": scenario.id, "seed": scenario.seed,
               "map_capacity": sum(b.full_occupancy.values()), "total_people": result.total,
               "evacuated_count": result.evacuated, "remaining_people": result.total - result.evacuated,
               "evacuation_rate": 100 * result.evacuated / result.total if result.total else 100.0,
               "makespan_seconds": max((t for t, _, _ in arrivals), default=0) if complete else None,
               "last_rescue_seconds": max((t for t, _, _ in arrivals), default=None),
               "avg_exit_time_seconds": total_exit / result.evacuated if result.evacuated else None,
               "total_exit_time_seconds": total_exit, "duration_seconds": horizon * b.dt,
               "time_step_seconds": b.dt, "runtime_seconds": elapsed, "peak_python_mb": peak,
               "time_expanded_nodes": result.network_nodes, "time_expanded_edges": result.network_edges,
               "capacity_violations": validation["capacity_violations"], "safety_violations": validation["safety_violations"],
               "structural_violations": validation["structural_violations"], "throughput_by_exit": dict(throughput),
               "exposed_unplanned_at_horizon": trace[-1]["exposed_unplanned_total"],
               "input_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
               "safety_metric_scope": "recorded actions; unrescued exposure is reported separately", **result.details}
    return result, metrics, trace, hazards, validation


def csv_file(path, rows, fields=None):
    rows = list(rows)
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})


def export(directory, b, scenario, occupancy, data):
    result, metrics, trace, hazards, validation = data
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    save_inputs(b, root)
    write_json(root / "scenario.json", asdict(scenario))
    write_json(root / "occupancy.json", occupancy)
    write_json(root / "metrics.json", metrics)
    write_json(root / "schedule.json", [asdict(j) for j in result.schedule])
    write_json(root / "validation.json", validation)
    write_json(root / "simulation_trace.json", trace)
    csv_file(root / "simulation_trace.csv", trace)
    csv_file(root / "rooms.csv", b.rooms)
    rows = []
    for j in result.schedule:
        for a in j.actions:
            rows.append({"journey_id": j.id, "people": j.count, "source_room": j.source, **asdict(a),
                         "depart_seconds": a.depart * b.dt, "arrive_seconds": a.arrive * b.dt})
        if j.exit_step is not None:
            rows.append({"journey_id": j.id, "people": j.count, "source_room": j.source, "kind": "EXIT",
                         "source": j.exit_node, "target": "OUTSIDE", "depart_seconds": j.exit_step * b.dt,
                         "arrive_seconds": j.exit_step * b.dt})
    csv_file(root / "schedule.csv", rows, ["journey_id", "people", "source_room", "kind", "source", "target", "edge_id", "depart_seconds", "arrive_seconds"])
    csv_file(root / "hazards.csv", ({"node_id": n.id, "fire_seconds": hazards.fire[n.id] if math.isfinite(hazards.fire[n.id]) else None,
                                     "smoke_seconds": hazards.smoke[n.id] if math.isfinite(hazards.smoke[n.id]) else None,
                                     "unsafe_seconds": hazards.nodes[n.id] if math.isfinite(hazards.nodes[n.id]) else None} for n in b.nodes))
    csv_file(root / "queue_lengths.csv", ({"time_seconds": r["time_seconds"], "node_id": node, "queue_length": count}
                                          for r in trace for node, count in r["queues"].items()))
    return root
