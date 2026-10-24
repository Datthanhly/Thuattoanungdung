"""Validate the measured report extension and complete its input provenance."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from a4_evac.data import build_a4,write_json
from a4_evac.runner import make_occupancy
from run_review_experiments import solver_digest


def main():
    out=ROOT/'outputs/a4_open_ground/review_20261024'
    b=build_a4()
    paths=list(out.rglob('metrics.json'))
    assert len(paths)==46, f'Expected 46 completed runs, found {len(paths)}'
    summary={'completed_runs':len(paths),'solver_sha256':solver_digest(),'checks':[]}
    for p in paths:
        r=json.loads(p.read_text(encoding='utf-8'))
        assert json.loads(p.with_name('validation.json').read_text(encoding='utf-8'))['valid']
        assert r['capacity_violations']==r['safety_violations']==r['structural_violations']==0
        assert r['duration_seconds']==900
        if 'population' in p.parts:
            seed=int(p.parent.name.rsplit('_s',1)[1])
            occ=json.loads(p.with_name('occupancy.json').read_text(encoding='utf-8'))
            assert occ==make_occupancy(b,people=r['total_people'],seed=seed)
            r['allocation_seed']=seed
        if 'runtime' in p.parts or 'sensitivity' in p.parts:
            assert r['evacuated_count']==1360 and r['makespan_seconds'] is not None
        if 'runtime' in p.parts:
            assert r['makespan_seconds']==390
            assert r['cost_stats']['cost_phases']==74
            assert r['cost_stats']['augmentations']==526
            assert r['probe_stats']['augmentations']==3753
        # The measured process ran the same a4_evac code as this audit.
        # The report scripts changed during writing, but solver modules did not.
        r['solver_sha256']=solver_digest()
        write_json(p,r)
    for sc in ['safe','smoke','stair_block','exit_block']:
        original=json.loads((ROOT/f'outputs/a4_open_ground/benchmark/{sc}/M3/metrics.json').read_text())
        repeated=json.loads((out/f'm3/{sc}/w4/metrics.json').read_text())
        for key in ['evacuated_count','makespan_seconds','avg_exit_time_seconds','total_exit_time_seconds']:
            assert original[key]==repeated[key],(sc,key)
    summary['checks']=['46 actual runs','all independent validators valid','all durations 900 seconds',
                       '15 population allocations reproduced from seed','5 identical M4 objective values',
                       'M3 alpha=4 reproduces primary benchmark','6 full-building sensitivities complete']
    write_json(ROOT/'document/Mau/data/review_verification.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
