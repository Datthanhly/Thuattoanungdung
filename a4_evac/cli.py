import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .data import build_a4, save_inputs, load_building, write_json
from .hazards import scenario_named, Scenario, simulate_hazards
from .runner import make_occupancy, run, export, csv_file
from .schedule import Action, Journey, validate_schedule


def main(argv=None):
    parser = argparse.ArgumentParser(description="A4 evacuation on the latest user-provided 1360-person map")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "compare", "benchmark"):
        p = commands.add_parser(name)
        p.add_argument("--scenario", choices=["safe", "smoke", "stair_block", "exit_block"], default="safe")
        p.add_argument("--duration", type=int, help="Seconds; defaults to the configured horizon")
        p.add_argument("--load", type=float, default=1.0, help="Fraction of image maximum occupancy, not actual attendance")
        p.add_argument("--people", type=int)
        p.add_argument("--seed", type=int, help="Defaults to the configured seed")
        p.add_argument("--assumptions", help="JSON object overriding simulation assumptions")
        p.add_argument("--building", help="Load an edited A4 building JSON instead of regenerating")
        p.add_argument("--output", default="outputs/a4_open_ground/benchmark" if name == "benchmark" else "outputs/a4_open_ground/demo")
        p.add_argument("--method", choices=["M1", "M2", "M3", "M4"], default="M4")
        p.add_argument("--memory", action="store_true", help="Enable tracemalloc; slower")
        p.add_argument("--gif", action="store_true")
        p.add_argument("--frame-ms", type=int, default=600, help="GIF frame delay in ms, positive multiple of 10 (default: 600)")
        p.add_argument("--end-hold-ms", type=int, default=3000, help="GIF final frame duration in ms (default: 3000)")
        p.add_argument("--resume", action="store_true", help="Reuse matching validated exported runs")
    p = commands.add_parser("generate-data")
    p.add_argument("--output", default="data/a4")
    p = commands.add_parser("replay")
    p.add_argument("result")
    p = commands.add_parser("gif")
    p.add_argument("result", default="outputs/a4_open_ground/benchmark/safe/M4", nargs="?")
    p.add_argument("--output")
    p.add_argument("--frame-ms", type=int, default=600, help="GIF frame delay in ms, positive multiple of 10 (default: 600)")
    p.add_argument("--end-hold-ms", type=int, default=3000, help="GIF final frame duration in ms (default: 3000)")
    p = commands.add_parser("report")
    p.add_argument("--results", default="outputs/a4_open_ground/benchmark")
    p.add_argument("--output", default="document")
    args = parser.parse_args(argv)
    try:
        if args.command == "generate-data":
            save_inputs(build_a4(), args.output)
            return 0
        if args.command == "replay":
            root = Path(args.result)
            b = load_building(root / "building.json")
            s = Scenario(**json.loads((root / "scenario.json").read_text(encoding="utf-8")))
            occ = json.loads((root / "occupancy.json").read_text(encoding="utf-8"))
            schedule = [Journey(**{**j, "actions": [Action(**a) for a in j["actions"]]})
                        for j in json.loads((root / "schedule.json").read_text(encoding="utf-8"))]
            report = validate_schedule(b, simulate_hazards(b, s), schedule, occ, s.duration_seconds // b.dt)
            print(json.dumps(report, indent=2))
            return 0 if report["valid"] else 1
        if args.command == "gif":
            from .visuals import animate_result
            print(animate_result(args.result, args.output, args.frame_ms, args.end_hold_ms))
            return 0
        if args.command == "report":
            from .latex import create_report
            create_report(args.results, args.output)
            return 0
        overrides = json.loads(Path(args.assumptions).read_text(encoding="utf-8")) if args.assumptions else None
        if args.building and overrides:
            raise ValueError("Choose either --building or --assumptions")
        b = load_building(args.building) if args.building else build_a4(overrides)
        args.duration = b.parameters["duration_seconds"] if args.duration is None else args.duration
        args.seed = b.parameters["seed"] if args.seed is None else args.seed
        if args.duration < 0:
            raise ValueError("duration must be nonnegative")
        occupancy = make_occupancy(b, args.load, args.people, args.seed)
        root, rows, traces = Path(args.output), [], {}
        root.mkdir(parents=True, exist_ok=True)
        names = ["safe", "smoke", "stair_block", "exit_block"] if args.command == "benchmark" else [args.scenario]
        methods = ["M1", "M2", "M3", "M4"] if args.command != "run" else [args.method]
        print(f"A4 latest map: 7 floors, 27 room zones, capacity 1360; scenario population={sum(occupancy.values())} (assumed)", flush=True)
        for name in names:
            scenario = scenario_named(name, args.duration, args.seed)
            for method in methods:
                directory = root / name / method if args.command == "benchmark" else root / method
                if args.resume and (directory / "metrics.json").is_file():
                    saved_b = load_building(directory / "building.json")
                    saved_s = json.loads((directory / "scenario.json").read_text(encoding="utf-8"))
                    saved_o = json.loads((directory / "occupancy.json").read_text(encoding="utf-8"))
                    if (saved_b != b or saved_o != occupancy
                            or saved_s != json.loads(json.dumps(asdict(scenario)))):
                        raise ValueError(f"Cannot resume different inputs at {directory}")
                    if main(["replay", str(directory)]) != 0:
                        raise ValueError("Invalid cached schedule")
                    metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
                    rows.append(metrics)
                    traces[name, method] = json.loads((directory / "simulation_trace.json").read_text(encoding="utf-8"))
                    print(f"Reused {name}/{method}", flush=True)
                    continue
                print(f"Running {name}/{method}...", flush=True)
                data = run(b, scenario, occupancy, method, args.memory)
                export(directory, b, scenario, occupancy, data)
                rows.append(data[1])
                traces[name, method] = data[2]
                write_json(root / "comparison.json", rows)
                csv_file(root / "comparison.csv", rows)
                print(f"  {method}: {data[1]['evacuated_count']}/{sum(occupancy.values())}; makespan={data[1]['makespan_seconds']}; runtime={data[1]['runtime_seconds']:.3f}s", flush=True)
        write_json(root / "comparison.json", rows)
        csv_file(root / "comparison.csv", rows)
        from .visuals import draw_floorplan, plot_curves
        draw_floorplan(b, root / "a4_floorplan.png")
        for name in names:
            plot_curves({m: traces[name, m] for m in methods}, sum(occupancy.values()), root / f"{name}_comparison.png")
        if args.gif:
            from .visuals import animate_result
            directory = root / names[-1] / methods[-1] if args.command == "benchmark" else root / methods[-1]
            animate_result(directory, frame_ms=args.frame_ms, end_hold_ms=args.end_hold_ms)
        print(f"Results: {root.resolve()}")
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Input error: {exc}")
        return 2
