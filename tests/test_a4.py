from dataclasses import replace
from collections import Counter
import pytest

from a4_evac.data import build_a4, save_inputs, load_building
from a4_evac.hazards import Scenario, scenario_named, simulate_hazards
from a4_evac.runner import make_occupancy, run, export
from a4_evac.optimize import time_network
from a4_evac.algorithms import dinic
from a4_evac.schedule import validate_schedule
from a4_evac.cli import main


def test_latest_image_transcription_and_wc_exclusion(tmp_path):
    b = build_a4()
    assert len(b.rooms) == 27 and sum(b.full_occupancy.values()) == 1360
    assert b.full_occupancy["R705"] == 40
    assert {f: sum(r["max_people"] for r in b.rooms if r["floor"] == f) for f in range(1, 8)} == {
        1: 180, 2: 180, 3: 200, 4: 200, 5: 200, 6: 240, 7: 160}
    assert [b.layout[str(f)]["length_m"] for f in range(1, 8)] == [66.4, 69.6, 69.6, 68.8, 65.2, 60.8, 52.0]
    assert all("WC" not in n.id for n in b.nodes)
    assert sum(n.kind == "LOBBY" for n in b.nodes) == 14
    assert sum(n.kind == "STAIR" for n in b.nodes) == 14
    assert sum(r["door_count"] for r in b.rooms) == 50
    assert [x["label"] for x in b.layout["6"]["blocks"]] == ["1", "606-607-608", "603-604-605", "2", "601-602"]
    save_inputs(b, tmp_path)
    assert load_building(tmp_path / "building.json").rooms == b.rooms


def test_cohort_transit_bound_and_stair_topology():
    b = build_a4()
    for e in b.edges:
        assert e.in_transit_capacity == e.steps(b.dt) * e.entry_capacity
        a, z = b.node_by_id[e.source], b.node_by_id[e.target]
        if a.floor != z.floor:
            assert a.kind == z.kind == "STAIR" and a.floor == z.floor + 1
            assert a.id.split("_")[-1] == z.id.split("_")[-1]


def test_ground_room_doors_are_immediate_absorbing_exits():
    b = build_a4()
    assert len(b.exits) == 9  # Seven room doors and two open stair discharge areas.
    assert "assumed_outside_exit_width_m" not in b.parameters
    assert not any(e.kind == "ASSUMED_OUTSIDE_EXIT" for e in b.edges)
    for room in (r for r in b.rooms if r["floor"] == 1):
        routes = b.outgoing[room["node_id"]]
        assert len(routes) == room["door_count"]
        for e in routes:
            assert e.kind == "ROOM_DOOR" and e.target in b.exits
            assert not b.outgoing[e.target]


@pytest.mark.parametrize("method", ["M1", "M2", "M3", "M4"])
def test_ground_evacuation_keeps_door_bottleneck_without_extra_gate(method):
    b = build_a4()
    result, metrics, *_ = run(b, scenario_named("safe", 60), {"R101": 20}, method)
    assert metrics["makespan_seconds"] == 15  # Door flow 7+7+6 at t=5,10,15.
    for journey in result.schedule:
        moves = [a for a in journey.actions if a.kind == "MOVE"]
        assert len(moves) == 1 and moves[0].target == "D101_1"
        assert journey.exit_step == moves[0].arrive


def test_ground_rooms_do_not_depend_on_stair_discharge_areas():
    b = build_a4()
    scenario = Scenario("both_stair_areas_blocked", 100, node_closures={"EXIT1": 0, "EXIT2": 0})
    occupancy = {r["node_id"]: r["max_people"] for r in b.rooms if r["floor"] == 1}
    result, metrics, *_ = run(b, scenario, occupancy)
    assert result.evacuated == 180
    assert metrics["makespan_seconds"] == 35
    assert set(metrics["throughput_by_exit"]).isdisjoint({"EXIT1", "EXIT2"})


def test_upper_rooms_discharge_via_open_ground_corridor():
    b = build_a4()
    result, metrics, *_ = run(b, scenario_named("safe", 200), {"R205": 5})
    assert result.evacuated == 5
    for journey in result.schedule:
        assert journey.exit_node in {"EXIT1", "EXIT2"}
        assert journey.actions[-1].source in {"L1_1", "L1_2"}
        assert journey.actions[-1].target == journey.exit_node


@pytest.mark.parametrize("method", ["M1", "M2", "M3", "M4"])
def test_end_to_end_and_population_conservation(tmp_path, method):
    b = build_a4()
    s = scenario_named("safe", 400)
    occ = make_occupancy(b, people=20)
    data = run(b, s, occ, method)
    assert data[0].evacuated == 20
    assert data[4]["valid"]
    for row in data[2]:
        assert sum(row["node_occupancy"].values()) + sum(row["active_moves"].values()) + row["evacuated_total"] + row["exposed_unplanned_total"] == 20
    export(tmp_path / method, b, s, occ, data)
    assert main(["replay", str(tmp_path / method)]) == 0


def test_hazard_boundaries_and_monotone_horizon():
    b = build_a4()
    s = scenario_named("exit_block", 120)
    h = simulate_hazards(b, s)
    assert h.safe_node("EXIT1", 119.999) and not h.safe_node("EXIT1", 120)
    occ = {"R101": 5}
    values = []
    for k in (0, 2, 5, 10, 20):
        values.append(dinic(time_network(b, h, occ, k), 0, 1))
    assert values == sorted(values)


def test_validator_detects_altered_counts_and_times():
    b = build_a4()
    s = scenario_named("safe", 300)
    occ = {"R101": 5}
    result, metrics, trace, h, validation = run(b, s, occ)
    first = result.schedule[0]
    altered = [replace(first, count=100)]
    assert not validate_schedule(b, h, altered, occ, 60)["valid"]
    wrong = replace(first, actions=[replace(first.actions[0], arrive=999), *first.actions[1:]])
    assert not validate_schedule(b, h, [wrong], occ, 60)["valid"]


def test_incomplete_and_empty_population():
    b = build_a4()
    result, metrics, *_ = run(b, scenario_named("safe", 5), {"R705": 10})
    assert result.evacuated == 0 and metrics["makespan_seconds"] is None
    assert metrics["completion_status"] == "INCOMPLETE"
    result, metrics, *_ = run(b, scenario_named("safe", 0), {})
    assert result.evacuated == 0 and metrics["makespan_seconds"] == 0


def test_resume_rejects_changed_topology_with_same_parameters(tmp_path):
    b = build_a4()
    occupancy = make_occupancy(b, people=4)
    scenario = scenario_named("safe", 200)
    export(tmp_path / "cached" / "M4", b, scenario, occupancy, run(b, scenario, occupancy))
    args = ["run", "--people", "4", "--duration", "200", "--output", str(tmp_path / "cached"), "--resume"]
    assert main(args) == 0
    changed_edges = [replace(b.edges[0], length_m=b.edges[0].length_m + 1), *b.edges[1:]]
    changed = replace(b, edges=changed_edges)
    save_inputs(changed, tmp_path / "edited")
    assert main([*args, "--building", str(tmp_path / "edited" / "building.json")]) == 2
