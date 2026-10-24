"""Reconstructed schematic and data-driven animation; no invented trajectories."""

from collections import Counter
from functools import lru_cache
from bisect import bisect_right
from pathlib import Path
import json
import math

from PIL import Image, ImageDraw, ImageFont

from .data import load_building, write_json
from .hazards import Scenario, simulate_hazards
from .schedule import Action, Journey, validate_schedule


@lru_cache(maxsize=30)
def font(size, bold=False):
    path = Path("C:/Windows/Fonts") / ("arialbd.ttf" if bold else "arial.ttf")
    if not path.is_file():
        import matplotlib
        path = Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"
    return ImageFont.truetype(str(path), size)


def text(draw, xy, value, size=16, color="#203957", bold=False, anchor=None):
    draw.text(xy, str(value), font=font(size, bold), fill=color, anchor=anchor)


def frame(b, seconds=None, state=None, hazards=None, report_mode=False):
    width, band, top, scale, left = 1680, 180, 160, 19.5, 190
    height = top + 7 * band + 110
    image = Image.new("RGB", (width, height), "#f7faff")
    draw = ImageDraw.Draw(image)
    text(draw, (40, 24), "A4 - PHENIKAA | MÔ HÌNH SƠ TÁN THEO THỜI GIAN", 28, bold=True)
    total = sum(b.full_occupancy.values())
    open_ground = "OPEN-GROUND" in b.building_id
    text(draw, (42, 66), "7 tầng · 27 khu phòng · tối đa 1.360 người · hành lang 2 m · bỏ khu WC gần cầu thang 2", 19)
    text(draw, (42, 98), "Tầng 1: hành lang hở, qua cửa phòng là ra ngoài. Bề rộng cửa/thang và tốc độ vẫn là tham số giả định." if open_ground else "Cửa ra ngoài tầng 1, chiều rộng thông hành và thời gian đi là giả định; không suy ra từ bản vẽ kiểm định.", 16, "#6b7e94")
    positions = {}
    for floor in range(7, 0, -1):
        y = top + (7 - floor) * band
        floor_max = sum(r["max_people"] for r in b.rooms if r["floor"] == floor)
        draw.rounded_rectangle((25, y + 5, 165, y + 130), radius=9, fill="#e5f1fc", outline="#c4ddf3", width=2)
        text(draw, (95, y + 27), f"TẦNG {floor}", 21, bold=True, anchor="mt")
        text(draw, (95, y + 66), f"{floor_max} người", 17, "#14765d", True, "mt")
        blocks = b.layout[str(floor)]["blocks"]
        for block in blocks:
            x0, w = left + block["x0"] * scale, block["width_m"] * scale
            x1 = x0 + w
            fill = "#fff0d7" if block["kind"] == "room" else "#e5eaf0"
            if hazards and block["kind"] == "room" and not hazards.safe_node(block["node_id"], seconds):
                fill = "#ffd6d6"
            draw.rectangle((x0, y, x1, y + 99), fill=fill, outline="#3d5879", width=2)
            if block["kind"] == "room":
                labelsize = 24 if report_mode else (18 if w > 100 else 14)
                text(draw, ((x0+x1)/2, y+16), block["label"], labelsize, bold=True, anchor="mt")
                text(draw, ((x0+x1)/2, y+42), f"{block['width_m']:g} × 8,8 m", (18 if w > 100 else 14) if report_mode else (13 if w > 100 else 10), anchor="mt")
                text(draw, ((x0+x1)/2, y+65), f"Max {block['max_people']}", (22 if w > 100 else 17) if report_mode else (14 if w > 100 else 11), "#ae352b", True, "mt")
                for dx in block["door_x"]:
                    px = left + dx * scale
                    draw.line((px - 10, y + 99, px + 10, y + 99), fill="#d7ecfd", width=5)
                    draw.line((px - 10, y + 99, px - 10, y + 80), fill="#3d5879", width=2)
                    draw.arc((px - 29, y + 80, px + 9, y + 118), 270, 360, fill="#3d5879", width=1)
            else:
                core_width = 5 * scale
                sx = x0 + (w - core_width) / 2
                draw.rectangle((sx, y + 4, sx + core_width, y + 49), fill="#c4dfed", outline="#63839b")
                for yy in range(y + 8, y + 49, 5):
                    draw.line((sx, yy, sx + core_width, yy), fill="#789bb5")
                text(draw, ((x0+x1)/2, y + 53), f"THANG {block['label']}" if report_mode else f"CẦU THANG {block['label']}", 20 if report_mode else 14, bold=True, anchor="mt")
                text(draw, ((x0+x1)/2, y + 77), f"Sảnh {block['width_m']:g} m" if report_mode else f"Sảnh {block['width_m']:g} m / lõi 5 m", 18 if report_mode else 11, "#6b7e94", anchor="mt")
        end = left + b.layout[str(floor)]["length_m"] * scale
        draw.rectangle((left, y + 99, end, y + 126), fill="#d9f4e6" if floor == 1 and open_ground else "#d4eafb", outline="#3d5879", width=2)
        if state is None and not (floor == 1 and open_ground):
            text(draw, ((left+end)/2, y + 102), "HÀNH LANG RỘNG 2 m", 14, bold=True)
        draw.line((left, y + 144, end, y + 144), fill="#a4b3c3")
        text(draw, ((left+end)/2, y + 149), f"Chiều dài mặt bằng mô hình: {b.layout[str(floor)]['length_m']:g} m", 12, "#6b7e94", anchor="mt")
        for n in b.nodes:
            if n.floor != floor:
                continue
            if n.kind == "ROOM":
                py = y + 45
            elif n.kind == "DOOR":
                py = y + 96
            elif n.kind == "CORRIDOR":
                py = y + 112
            elif n.kind == "LOBBY":
                py = y + 85
            elif n.kind == "STAIR":
                py = y + 28
            elif n.kind == "EXIT" and open_ground:
                py = y + (99 if n.id.startswith("D") else 112)
            else:
                py = y + 160
            positions[n.id] = (left + n.x * scale, py)
            if n.kind == "EXIT":
                px, py = positions[n.id]
                if open_ground:
                    draw.line((px, py + 2, px, y + 123), fill="#138865", width=3)
                    draw.polygon([(px - 5, y + 119), (px + 5, y + 119), (px, y + 126)], fill="#138865")
                    label = "Thoát" if n.id.startswith("D") else f"Từ thang {n.id[-1]}"
                    text(draw, (px, y + 129), label, 11, "#14765d", anchor="mt")
                else:
                    draw.line((px, y + 128, px, py), fill="#138865", width=4)
                    text(draw, (px + 8, py - 6), f"{n.id} (giả định)", 12, "#14765d")
    if state:
        nodes, moves, escaped, exposed = state
        for node, count in nodes.items():
            if not count:
                continue
            px, py = positions[node]
            unsafe = hazards and not hazards.safe_node(node, seconds)
            color = "#dc2626" if unsafe else "#ffffff"
            draw.rounded_rectangle((px - 16, py - 11, px + 16, py + 11), radius=5,
                                   fill=color, outline="#a73428" if unsafe else "#314f74", width=1)
            text(draw, (px, py - 1), count, 12, "white" if unsafe else "#203957", True, "mm")
        for (eid, start, end), count in moves.items():
            e = b.edge_by_id[eid]
            a, z = positions[e.source], positions[e.target]
            progress = (seconds / b.dt - start) / (end - start)
            # Inter-floor interpolation is schematic: each floor has local
            # coordinates, so a marker links the two corresponding stair cores.
            points = [a, z]
            lengths = [math.dist(u, v) for u, v in zip(points, points[1:])]
            distance = progress * sum(lengths)
            px, py = z
            for u, v, length in zip(points, points[1:], lengths):
                if distance <= length:
                    ratio = distance / length if length else 0
                    px, py = u[0] + ratio * (v[0]-u[0]), u[1] + ratio * (v[1]-u[1])
                    break
                distance -= length
            draw.ellipse((px - 10, py - 10, px + 10, py + 10), fill="#2563eb", outline="white", width=1)
            text(draw, (px, py - 1), count, 10, "white", True, "mm")
        text(draw, (1180, 33), f"t={seconds:06.1f}s | Thoát {escaped}", 21, "#14765d", True)
        text(draw, (1120, 72), f"Trong nhà: {sum(nodes.values())+sum(moves.values())} | Vùng nguy hiểm: {exposed}", 16)
        text(draw, (42, 126), "Chấm xanh: nhóm đang đi (số người). Ô trắng: đang ở nút. Liên kết giữa tầng là sơ đồ.", 16, "#526b86")
    bottom = height - 52
    text(draw, (40, bottom), "Dữ liệu: sơ đồ mặt bằng A4. Mô hình giữ sảnh và hai cụm thang; khu WC nằm ngoài phạm vi tính toán.", 15, "#6b7e94")
    text(draw, (40, bottom + 25), "Mô phỏng thuật toán; chưa kiểm định PCCC. Tọa độ từng tầng là tọa độ cục bộ, không phải khảo sát 3D.", 14, "#9a4e4e")
    return image


def draw_floorplan(b, path, report_mode=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame(b, report_mode=report_mode).save(path)


def plot_curves(traces, total, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {"M1": "#dc2626", "M2": "#d97706", "M3": "#2563eb", "M4": "#059669"}
    fig, ax = plt.subplots(figsize=(10, 4.5), constrained_layout=True)
    for method, rows in traces.items():
        ax.step([r["time_seconds"] for r in rows], [r["evacuated_total"] for r in rows], where="post",
                label=method, color=colors[method], linewidth=2)
    ax.set(xlabel="Simulation time (s)", ylabel="Evacuated people", ylim=(0, max(1, total)*1.05))
    ax.grid(alpha=0.2)
    ax.legend(ncol=4)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def animate_result(directory, output=None, frame_ms=600, end_hold_ms=3000):
    for name, value in (("frame_ms", frame_ms), ("end_hold_ms", end_hold_ms)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 10 or value % 10:
            raise ValueError(f"{name} must be a positive multiple of 10 milliseconds")
    root = Path(directory)
    b = load_building(root / "building.json")
    scenario = Scenario(**json.loads((root / "scenario.json").read_text(encoding="utf-8")))
    occupancy = json.loads((root / "occupancy.json").read_text(encoding="utf-8"))
    journeys = [Journey(**{**j, "actions": [Action(**a) for a in j["actions"]]})
                for j in json.loads((root / "schedule.json").read_text(encoding="utf-8"))]
    metrics = json.loads((root / "metrics.json").read_text(encoding="utf-8"))
    hazards = simulate_hazards(b, scenario)
    report = validate_schedule(b, hazards, journeys, occupancy, scenario.duration_seconds // b.dt)
    if not report["valid"]:
        raise ValueError("Cannot animate invalid schedule")
    assigned = Counter()
    starts = []
    for j in journeys:
        assigned[j.source] += j.count
        starts.append([a.depart * b.dt for a in j.actions])
    unassigned = {n: count - assigned[n] for n, count in occupancy.items() if count > assigned[n]}

    def state(t):
        nodes, moves, escaped = Counter(unassigned), Counter(), 0
        for j, times in zip(journeys, starts):
            if j.exit_step is not None and j.exit_step * b.dt <= t:
                escaped += j.count
                continue
            index = bisect_right(times, t) - 1
            if index < 0:
                nodes[j.source] += j.count
            else:
                a = j.actions[index]
                if a.kind == "MOVE" and t < a.arrive * b.dt:
                    moves[a.edge_id, a.depart, a.arrive] += j.count
                else:
                    nodes[a.target] += j.count
        exposed = sum(c for n, c in nodes.items() if not hazards.safe_node(n, t))
        assert sum(nodes.values()) + sum(moves.values()) + escaped == sum(occupancy.values())
        return nodes, moves, escaped, exposed

    end = metrics["makespan_seconds"] if metrics["makespan_seconds"] is not None else metrics["duration_seconds"]
    interval = b.dt  # A bounded-memory 1000px GIF, one frame per simulation step.
    count = round(end / interval) + 1
    target = Path(output) if output else root / "evacuation.gif"
    target.parent.mkdir(parents=True, exist_ok=True)
    def render(t):
        im = frame(b, t, state(t), hazards)
        return im.resize((1008, round(im.height * 0.6)), Image.Resampling.LANCZOS)
    sample = render(end / 2)
    sample.save(target.with_name(target.stem + "_preview.png"))
    palette = sample.quantize(colors=256)
    def frames():
        for k in range(count):
            yield render(k * interval).quantize(palette=palette, dither=Image.Dither.NONE)
    sequence = frames()
    first = next(sequence)
    first.save(target, save_all=True, append_images=sequence, loop=0, optimize=False,
               duration=[frame_ms]*(count-1)+[end_hold_ms] if count > 1 else end_hold_ms)
    write_json(target.with_suffix(".playback.json"), {
        "frame_ms": frame_ms, "end_hold_ms": end_hold_ms,
        "simulation_step_seconds": interval, "simulation_end_seconds": end,
        "frame_count": count, "playback_duration_ms": frame_ms*(count-1)+end_hold_ms,
        "source_result": str(root.resolve()), "input_sha256": metrics.get("input_sha256"),
    })
    return target.resolve()
