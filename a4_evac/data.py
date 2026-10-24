"""Transcription of the LAST image supplied on 2026-10-24.

Earlier pictures in the conversation disagree. This file intentionally follows
the latest picture (705=40, total=1360), including its room/core ordering.
No toilets are represented. Lobby strips remain traversable schematic areas.
"""

from dataclasses import dataclass, field, asdict
from collections import defaultdict
import json
import math
from pathlib import Path


# Left to right: (type, label, longitudinal width, maximum occupancy).
FLOORS = {
    1: [("core", "1", 7.2, 0), ("room", "104-105", 18.4, 80), ("room", "103", 13.6, 40),
        ("core", "2", 13.6, 0), ("room", "102", 8.8, 40), ("room", "101", 4.8, 20)],
    2: [("core", "1", 7.2, 0), ("room", "205", 12.0, 40), ("room", "204", 4.8, 20),
        ("room", "203", 13.6, 40), ("core", "2", 13.6, 0), ("room", "201-202", 18.4, 80)],
    3: [("core", "1", 7.2, 0), ("room", "305", 12.0, 40), ("room", "304", 8.8, 40),
        ("room", "303", 9.6, 40), ("core", "2", 13.6, 0), ("room", "301-302", 18.4, 80)],
    4: [("core", "1", 7.2, 0), ("room", "405", 11.2, 40), ("room", "404", 9.6, 40),
        ("room", "403", 9.6, 40), ("core", "2", 13.6, 0), ("room", "401-402", 17.6, 80)],
    5: [("core", "1", 7.2, 0), ("room", "505", 11.2, 40), ("room", "504", 8.8, 40),
        ("room", "503", 10.4, 40), ("core", "2", 13.6, 0), ("room", "501-502", 14.0, 80)],
    6: [("core", "1", 7.2, 0), ("room", "606-607-608", 16.8, 80),
        ("room", "603-604-605", 13.6, 80), ("core", "2", 13.6, 0), ("room", "601-602", 9.6, 80)],
    7: [("core", "1", 7.2, 0), ("room", "705", 9.6, 40), ("room", "704", 4.0, 20),
        ("room", "702-703", 13.6, 80), ("core", "2", 13.6, 0), ("room", "701", 4.0, 20)],
}


DEFAULTS = {
    "time_step_seconds": 5,
    "walking_speed_m_s": 1.2,
    "stair_speed_m_s": 0.7,
    "interfloor_path_m": 12.0,
    "specific_flow_people_m_s": 1.3,
    "assumed_room_door_width_m": 1.2,
    "assumed_stair_usable_width_m": 1.5,
    "corridor_width_m": 2.0,
    "corridor_lane_width_m": 1.0,
    "room_depth_m": 8.8,
    "stair_footprint_width_m_from_image": 5.0,
    "corridor_node_storage": 24,
    "lobby_node_storage": 30,
    "stair_node_storage": 36,
    "fire_propagation_m_s": 0.03,
    "smoke_propagation_m_s": 0.15,
    "smoke_upstairs_seconds": 25.0,
    "smoke_downstairs_seconds": 45.0,
    "duration_seconds": 900,
    "seed": 2026,
}


@dataclass(frozen=True)
class Node:
    id: str
    floor: int
    x: float
    y: float
    kind: str
    storage_capacity: int
    can_wait: bool = True
    exit_capacity: int = 0


@dataclass(frozen=True)
class Edge:
    id: str
    source: str
    target: str
    length_m: float
    travel_seconds: float
    entry_capacity: int
    in_transit_capacity: int
    kind: str

    def steps(self, dt):
        return max(1, math.ceil(self.travel_seconds / dt))


@dataclass
class Building:
    nodes: list[Node]
    edges: list[Edge]
    rooms: list[dict]
    layout: dict
    parameters: dict
    building_id: str = "PHENIKAA-A4-OPEN-GROUND-20261024"
    node_by_id: dict = field(init=False, repr=False)
    edge_by_id: dict = field(init=False, repr=False)
    outgoing: dict = field(init=False, repr=False)

    def __post_init__(self):
        self.node_by_id = {n.id: n for n in self.nodes}
        self.edge_by_id = {e.id: e for e in self.edges}
        self.outgoing = defaultdict(list)
        for e in self.edges:
            self.outgoing[e.source].append(e)
        self.validate()

    @property
    def exits(self):
        return {n.id for n in self.nodes if n.kind == "EXIT"}

    @property
    def full_occupancy(self):
        return {r["node_id"]: r["max_people"] for r in self.rooms}

    @property
    def dt(self):
        return self.parameters["time_step_seconds"]

    def validate(self):
        if len(self.node_by_id) != len(self.nodes) or len(self.edge_by_id) != len(self.edges):
            raise ValueError("Duplicate node or edge IDs")
        if not self.exits:
            raise ValueError("No exit")
        for n in self.nodes:
            if not isinstance(n.floor, int) or isinstance(n.floor, bool) or n.floor not in FLOORS or not all(math.isfinite(v) for v in (n.x, n.y)):
                raise ValueError(f"Invalid node {n.id}")
            if not isinstance(n.storage_capacity, int) or isinstance(n.storage_capacity, bool) or n.storage_capacity < 0:
                raise ValueError("Storage must be nonnegative integer")
            if not isinstance(n.exit_capacity, int) or n.exit_capacity < 0:
                raise ValueError("Invalid exit capacity")
        for e in self.edges:
            if e.source not in self.node_by_id or e.target not in self.node_by_id:
                raise ValueError(f"Unknown endpoint {e.id}")
            if not math.isfinite(e.travel_seconds) or not math.isfinite(e.length_m) or e.travel_seconds <= 0 or e.length_m <= 0:
                raise ValueError(f"Invalid edge duration/length {e.id}")
            if not isinstance(e.entry_capacity, int) or isinstance(e.entry_capacity, bool) or e.entry_capacity < 0:
                raise ValueError("Entry capacity must be nonnegative integer")
            # Deliberate cohort/cell model: at most d entry cohorts overlap.
            if e.in_transit_capacity < e.steps(self.dt) * e.entry_capacity:
                raise ValueError("Transit capacity requires extra resource constraints; this building uses d cohorts")
            a, b = self.node_by_id[e.source], self.node_by_id[e.target]
            if a.floor != b.floor and (a.kind != "STAIR" or b.kind != "STAIR"):
                raise ValueError("Only stairs may connect different floors")
            if a.kind == "EXIT":
                raise ValueError("Exits are absorbing")


def build_a4(overrides=None):
    p = {**DEFAULTS, **(overrides or {})}
    unknown = set(p) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"Unknown assumptions: {sorted(unknown)}")
    for key, value in p.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or (value < 0 if key == "seed" else value <= 0):
            raise ValueError(f"Invalid positive parameter {key}")
    for key in ("room_depth_m", "corridor_width_m", "stair_footprint_width_m_from_image"):
        if p[key] != DEFAULTS[key]:
            raise ValueError(f"{key} comes from the source image and is not a free simulation assumption")
    for key in ("time_step_seconds", "corridor_node_storage", "lobby_node_storage", "stair_node_storage", "seed"):
        if not isinstance(p[key], int):
            raise ValueError(f"{key} must be an integer")
    if p["corridor_lane_width_m"] * 2 > p["corridor_width_m"]:
        raise ValueError("Directional corridor lanes exceed the available width")
    nodes, edges, rooms, layout = [], [], [], {}
    dt, rate = p["time_step_seconds"], p["specific_flow_people_m_s"]

    def add_edge(a, b, width, kind, length=None, speed=None):
        lookup = {n.id: n for n in nodes}
        u, v = lookup[a], lookup[b]
        length = math.hypot(u.x - v.x, u.y - v.y) if length is None else length
        seconds = length / (speed or p["walking_speed_m_s"])
        capacity = math.floor(width * rate * dt)
        edges.append(Edge(f"{a}__{b}", a, b, length, seconds, capacity,
                          capacity * max(1, math.ceil(seconds / dt)), kind))

    for floor, blocks in FLOORS.items():
        x, waypoints, floor_layout = 0.0, [], []
        for kind, label, width, maximum in blocks:
            mid = x + width / 2
            block = {"kind": kind, "label": label, "x0": x, "width_m": width, "depth_m": p["room_depth_m"]}
            if kind == "room":
                rid = "R" + label
                doors = 2 if "-" in label or width >= 8 else 1
                fractions = (0.2, 0.8) if doors == 2 else (0.5,)
                block.update({"node_id": rid, "max_people": maximum, "door_x": [x + f * width for f in fractions]})
                rooms.append({"floor": floor, "label": label, "node_id": rid,
                              "width_m": width, "depth_m": p["room_depth_m"], "max_people": maximum,
                              "door_count": doors, "door_location_source": "approximate positions from image convention"})
                nodes.append(Node(rid, floor, mid, 4.4, "ROOM", maximum))
                door_cap = math.floor(p["assumed_room_door_width_m"] * rate * dt)
                for index, dx in enumerate(block["door_x"], 1):
                    did, cid = f"D{label}_{index}", f"C{floor}_{len(waypoints):02}"
                    # User confirms the ground corridor opens directly outside.
                    # Arrival at a ground-room door is the exit event itself:
                    # no extra outdoor door, travel edge or time step is added.
                    nodes.append(Node(did, floor, dx, 8.8,
                                      "EXIT" if floor == 1 else "DOOR", door_cap,
                                      floor != 1, door_cap if floor == 1 else 0))
                    add_edge(rid, did, p["assumed_room_door_width_m"], "ROOM_DOOR")
                    if floor > 1:
                        nodes.append(Node(cid, floor, dx, 9.8, "CORRIDOR", p["corridor_node_storage"]))
                        add_edge(did, cid, p["assumed_room_door_width_m"], "DOOR_CORRIDOR")
                        waypoints.append((dx, cid))
            else:
                lobby, stair, corridor = f"L{floor}_{label}", f"S{floor}_{label}", f"C{floor}_{len(waypoints):02}"
                if floor == 1:
                    corridor = "EXIT" + label
                nodes.extend([Node(lobby, floor, mid, 7.5, "LOBBY", p["lobby_node_storage"]),
                              Node(stair, floor, mid, 4.4, "STAIR", p["stair_node_storage"]),
                              Node(corridor, floor, mid, 9.8, "EXIT" if floor == 1 else "CORRIDOR",
                                   1360 if floor == 1 else p["corridor_node_storage"],
                                   floor != 1, 1360 if floor == 1 else 0)])
                for a, b in ((corridor, lobby), (lobby, stair)):
                    if a != corridor or floor > 1:
                        add_edge(a, b, p["assumed_stair_usable_width_m"], "CORE_ACCESS")
                    add_edge(b, a, p["assumed_stair_usable_width_m"], "CORE_ACCESS")
                block.update({"lobby_node": lobby, "stair_node": stair, "corridor_node": corridor})
                waypoints.append((mid, corridor))
            floor_layout.append(block)
            x += width
        layout[str(floor)] = {"length_m": round(x, 5), "blocks": floor_layout}
        waypoints.sort()
        for (_, a), (_, b) in zip(waypoints, waypoints[1:]) if floor > 1 else []:
            add_edge(a, b, p["corridor_lane_width_m"], "CORRIDOR_LANE")
            add_edge(b, a, p["corridor_lane_width_m"], "CORRIDOR_LANE")
    for floor in range(2, 8):
        for core in (1, 2):
            add_edge(f"S{floor}_{core}", f"S{floor-1}_{core}", p["assumed_stair_usable_width_m"],
                     "STAIR_DOWN", p["interfloor_path_m"], p["stair_speed_m_s"])
    return Building(nodes, edges, rooms, layout, p)


def save_inputs(building, directory):
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    data = {"building_id": building.building_id, "nodes": [asdict(n) for n in building.nodes],
            "edges": [asdict(e) for e in building.edges], "rooms": building.rooms,
            "layout": building.layout, "parameters": building.parameters}
    write_json(root / "building.json", data)
    write_json(root / "model_parameters.json", building.parameters)
    write_json(root / "assumptions.json", {"parameters": building.parameters,
        "source": "Latest user-provided diagram, 2026-10-24; not independently surveyed",
        "excluded": ["toilets near core 2; no nodes, occupancy or extra pass-through routes"],
        "retained": ["schematic lobby areas of both stair cores"],
        "confirmed_by_user": ["Ground-floor corridor has no protective barrier and opens outdoors; crossing any ground-room door is immediate evacuation.",
                              "Upper-floor occupants evacuate when they reach the open ground corridor from either stair lobby; EXIT1/EXIT2 label those areas, not extra doors."],
        "from_image": ["room ordering", "room widths", "8.8m depth", "occupancy maxima", "2m corridor", "5m core footprint", "door count convention"],
        "not_measured": ["exact room door coordinates/clear widths", "usable stair width", "inter-floor travel distance", "actual attendance", "walking/flow/hazard speeds", "node holding capacities"],
        "ground_exit_model": "Seven ground-room doors are absorbing exits with the room-door capacity. Two stair discharge areas are absorbing exits with nonbinding capacity 1360; actual discharge is bounded by the stair/lobby access edge. No extra outside gate, gate width or exit travel delay.",
        "coordinate_system": "Each floor uses local x from the left edge; unequal lengths and core offsets in the schematic are not a surveyed 3D alignment.",
        "flow_model": "Two fixed 1m directional corridor lanes; descending-only stairs. Transit stores at most d departure cohorts. Not a certified building evacuation plan.",
        "maximum_people": sum(building.full_occupancy.values())})


def load_building(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return Building([Node(**n) for n in raw["nodes"]], [Edge(**e) for e in raw["edges"]],
                    raw["rooms"], raw["layout"], raw["parameters"], raw["building_id"])


def write_json(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
