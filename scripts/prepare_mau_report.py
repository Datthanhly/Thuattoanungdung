"""Prepare auditable tables and figures for the user's standard report template."""
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from a4_evac.data import build_a4, write_json
from a4_evac.runner import run, export
from a4_evac.hazards import scenario_named
from a4_evac.visuals import draw_floorplan


def table(path, cols, headers, rows):
    lines = [r"\begin{center}\small", r"\begin{tabular}{"+cols+"}", r"\toprule",
             " & ".join(headers)+r"\\\midrule"]
    def cell(value):
        s=str(value)
        return s.replace('_',r'\_') if r'\_' not in s else s
    lines += [" & ".join(cell(v) for v in row)+r"\\" for row in rows]
    lines += [r"\bottomrule\end{tabular}\end{center}"]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    target = ROOT / "document/Mau"
    for folder in ("figures", "tables", "data", "extracts", "build"):
        (target/folder).mkdir(exist_ok=True)
    src = ROOT / "outputs/a4_open_ground/benchmark"
    rows = json.loads((src/"comparison.json").read_text(encoding="utf-8"))
    b = build_a4()
    assert len(rows)==16 and all(r["building_id"]==b.building_id for r in rows)
    for name in ("comparison.json", "comparison.csv"):
        shutil.copy2(src/name, target/"data"/name)
    assumptions=json.loads((ROOT/'data/a4/assumptions.json').read_text(encoding='utf-8'))
    assumptions['source']='Sơ đồ mặt bằng bảy tầng tòa nhà A4; các tham số thông hành chưa được hiệu chỉnh bằng khảo sát hiện trường.'
    assumptions['boundary_conditions']=assumptions.pop('confirmed_by_user',[])
    write_json(target/'data/assumptions.json',assumptions)
    shutil.copy2(ROOT/"data/a4/model_parameters.json", target/"data/model_parameters.json")
    draw_floorplan(b, target/"figures/a4_floorplan.png", report_mode=True)
    im = Image.open(target/"figures/a4_floorplan.png")
    im.crop((150,1210,1550,1430)).save(target/"figures/ground_floor.png")
    for scenario in ("safe", "smoke", "stair_block", "exit_block"):
        fig,ax=plt.subplots(figsize=(7.2,2.65),layout='constrained')
        for method,color in zip(('M1','M2','M3','M4'),('#c85555','#d99c3e','#4478b8','#22896b')):
            trace=json.loads((src/scenario/method/'simulation_trace.json').read_text())
            ax.step([r['time_seconds'] for r in trace],[r['evacuated_total'] for r in trace],
                    where='post',label=method,color=color,linewidth=1.8)
        ax.set_xlabel('Simulation time (s)',fontsize=12)
        ax.set_ylabel('Evacuated people',fontsize=12)
        ax.tick_params(labelsize=11)
        ax.set_ylim(0,1420);ax.grid(alpha=.2)
        ax.legend(ncol=4,fontsize=10,loc='lower left',bbox_to_anchor=(0,1.01),frameon=False)
        fig.savefig(target/'figures'/f'{scenario}_comparison.png',dpi=220);plt.close(fig)
        selected = [r for r in rows if r["scenario_id"]==scenario]
        table(target/"tables"/f"{scenario}.tex", "lrrrr", ["PP", "Thoát", "Hoàn tất (s)", "TB (s)", "Giải (s)"],
              [[r['method'],r['evacuated_count'],"--" if r['makespan_seconds'] is None else r['makespan_seconds'],
                f"{r['avg_exit_time_seconds']:.2f}",f"{r['runtime_seconds']:.3f}"] for r in selected])
    table(target/"tables/floors.tex", "crrr", ["Tầng", "Chiều dài (m)", "Số khu phòng", "Sức chứa"],
          [[f,f"{b.layout[str(f)]['length_m']:.1f}",sum(r['floor']==f for r in b.rooms),sum(r['max_people'] for r in b.rooms if r['floor']==f)] for f in range(1,8)])
    table(target/"tables/nodes.tex", "lr", ["Loại nút", "Số lượng"], sorted(Counter(n.kind for n in b.nodes).items()))
    table(target/"tables/edges.tex", "lr", ["Loại cạnh có hướng", "Số lượng"], sorted(Counter(e.kind for e in b.edges).items()))
    table(target/"tables/rooms.tex", "clrrr", ["Tầng", "Khu phòng", "Dài (m)", "Tối đa", "Số cửa"],
          [[r['floor'],r['label'],f"{r['width_m']:g}",r['max_people'],r['door_count']] for r in b.rooms])
    table(target/"tables/ten.tex", "lrrr", ["Kịch bản", "Nút TEN", "Cạnh thuận", "Cứu cuối (s)"],
          [[r['scenario_id'].replace('_',r'\_'),r['time_expanded_nodes'],r['time_expanded_edges'],r['last_rescue_seconds']] for r in rows if r['method']=='M4'])
    table(target/"tables/throughput.tex", "lrrr", ["Kịch bản M4", "Cửa phòng T1", "Thang 1", "Thang 2"],
          [[r['scenario_id'].replace('_',r'\_'),sum(v for k,v in r['throughput_by_exit'].items() if k.startswith('D')),
            r['throughput_by_exit'].get('EXIT1',0),r['throughput_by_exit'].get('EXIT2',0)] for r in rows if r['method']=='M4'])
    table(target/'tables/hashes.tex','ll',['Kịch bản','SHA-256 (12 ký tự đầu)'],
          [[r['scenario_id'].replace('_',r'\_'),r['input_sha256'][:12]] for r in rows if r['method']=='M4'])
    schedule=json.loads((src/'safe/M4/schedule.json').read_text())
    example=next(j for j in schedule if j['source']=='R101' and not any(a['kind']=='WAIT' for a in j['actions']))
    (target/'data/journey_example.json').write_text(json.dumps(example,ensure_ascii=False,
        separators=(', ',': ')).replace('"actions": [','\n "actions": [').replace('"exit_node":','\n "exit_node":')+'\n',encoding='utf-8')
    safe = next(r for r in rows if r['scenario_id']=='safe' and r['method']=='M4')
    table(target/"tables/probes.tex", "rr", ["Horizon (bước)", "Max flow (người)"],
          sorted((int(k),v) for k,v in safe['max_flow_probes'].items()))
    sensitivity=[]
    for dt,width in ((2,1.2),(5,1.2),(10,1.2),(5,0.9),(5,1.5)):
        building=build_a4({'time_step_seconds':dt,'assumed_room_door_width_m':width})
        occupancy={r['node_id']:r['max_people'] for r in building.rooms if r['floor']==1}
        out=ROOT/f"outputs/a4_open_ground/report_sensitivity/dt{dt}_door{width:g}"
        if (out/'metrics.json').exists():
            metrics=json.loads((out/'metrics.json').read_text())
        else:
            data=run(building,scenario_named('safe',120),occupancy,'M4')
            export(out,building,scenario_named('safe',120),occupancy,data)
            metrics=data[1]
        sensitivity.append({'dt':dt,'door_width_m':width,**metrics})
    write_json(target/'data/sensitivity.json',sensitivity)
    table(target/'tables/sensitivity.tex','rrrrr',[r'$\Delta t$ (s)','Cửa (m)','Thoát','Hoàn tất (s)','TB (s)'],
          [[r['dt'],r['door_width_m'],r['evacuated_count'],r['makespan_seconds'],f"{r['avg_exit_time_seconds']:.2f}"] for r in sensitivity])
    scenarios=['safe','smoke','stair_block','exit_block']
    methods=['M1','M2','M3','M4']
    colors=['#c85555','#d99c3e','#4478b8','#22896b']
    fig,axes=plt.subplots(1,2,figsize=(7.2,3.0),layout='constrained')
    for i,method in enumerate(methods):
        vals=[next(r for r in rows if r['scenario_id']==s and r['method']==method) for s in scenarios]
        x=[j+(i-1.5)*0.19 for j in range(4)]
        axes[0].bar(x,[r['evacuation_rate'] for r in vals],width=.18,label=method,color=colors[i])
        axes[1].bar(x,[r['runtime_seconds'] for r in vals],width=.18,label=method,color=colors[i])
    for ax in axes:
        ax.set_xticks(range(4),['S0','S1','S2','S3'])
        ax.tick_params(labelsize=11);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    axes[0].set_ylabel('Evacuated (%)',fontsize=12);axes[0].set_ylim(0,105)
    axes[1].set_ylabel('Solver runtime (s)',fontsize=12)
    axes[0].legend(ncol=4,fontsize=9,loc='lower left',bbox_to_anchor=(0,1.01),frameon=False)
    fig.savefig(target/'figures/aggregate.png',dpi=200);plt.close(fig)
    for relative, first, last in [('algorithms.py',9,31),('optimize.py',120,149),('schedule.py',145,164)]:
        lines=(ROOT/'a4_evac'/relative).read_text(encoding='utf-8').splitlines()
        (target/'extracts'/relative).write_text('\n'.join(lines[first-1:last])+'\n',encoding='utf-8')
    preview=ROOT/'outputs/a4_open_ground/a4_evacuation_preview.png'
    shutil.copy2(preview,target/'figures/animation_preview.png')
    ground=json.loads((ROOT/'outputs/a4_open_ground/ground_floor_demo/M4/metrics.json').read_text())
    write_json(target/'data/ground_floor_metrics.json',ground)
    import platform
    from importlib.metadata import version
    write_json(target/'data/environment.json',{'python':platform.python_version(),'system':platform.system(),
        'machine':platform.machine(),'Pillow':version('Pillow'),'matplotlib':version('matplotlib'),
        'networkx':version('networkx'),'pytest':version('pytest')})
    (target/'data/source_manifest.json').write_text(json.dumps({'model':b.building_id,'version':safe['software_version'],
        'benchmark':'outputs/a4_open_ground/benchmark','rows':16,'nodes':len(b.nodes),'edges':len(b.edges),
        'rooms':len(b.rooms),'population':1360,'ground_floor_population':180},indent=2),encoding='utf-8')
    from prepare_review_assets import main as prepare_review
    prepare_review()
    print('Prepared tables, measured sensitivity and figures:',target)


if __name__=='__main__':
    main()
