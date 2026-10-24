"""Additional measured experiments for the scientific report review.

Sequential solver execution avoids contention between timed solver runs.
Existing primary benchmark files are never overwritten.
"""
from pathlib import Path
from dataclasses import asdict
import gzip
import hashlib
import json
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from a4_evac.data import build_a4, write_json
from a4_evac.runner import run, make_occupancy
from a4_evac.hazards import scenario_named

OUT = ROOT/'outputs/a4_open_ground/review_20261024'


def solver_digest():
    digest=hashlib.sha256()
    for p in sorted((ROOT/'a4_evac').glob('*.py')):
        digest.update(p.name.encode())
        digest.update(p.read_bytes())
    return digest.hexdigest()


def measured(key, b, occupancy, scenario='safe', method='M4', weight=4):
    directory = OUT/key
    target = directory/'metrics.json'
    if target.exists():
        saved=json.loads(target.read_text(encoding='utf-8'))
        if (json.loads((directory/'parameters.json').read_text(encoding='utf-8')) != b.parameters
                or json.loads((directory/'occupancy.json').read_text(encoding='utf-8')) != occupancy
                or saved['method'] != method or saved['scenario_id'] != scenario
                or (method=='M3' and saved.get('m3_weight') != weight)
                or saved.get('solver_sha256') != solver_digest()):
            raise ValueError(f'Cached experiment differs from current inputs or solver: {key}')
        print('Cached', key, flush=True)
        return saved
    print('Running', key, flush=True)
    sc = scenario_named(scenario, 900)
    data = run(b, sc, occupancy, method, m3_weight=weight)
    result, metrics, _, _, validation = data
    metrics['solver_sha256'] = solver_digest()
    if key.startswith('population/'):
        metrics['allocation_seed'] = int(key.rsplit('_s', 1)[1])
    assert validation['valid']
    directory.mkdir(parents=True, exist_ok=True)
    write_json(directory/'occupancy.json', occupancy)
    write_json(directory/'parameters.json', b.parameters)
    write_json(directory/'validation.json', validation)
    if not key.startswith('runtime/'):
        with gzip.open(directory/'schedule.json.gz', 'wt', encoding='utf-8') as f:
            json.dump([asdict(j) for j in result.schedule], f, ensure_ascii=False)
    write_json(target, metrics)
    print('Done', key, metrics['evacuated_count'], metrics['makespan_seconds'],
          round(metrics['runtime_seconds'], 2), flush=True)
    return metrics


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    hardware = {'platform': platform.platform(), 'python': sys.version,
                'timing_scope': 'runner.run solver interval; sequential runs; no tracemalloc',
                'repetitions': 5, 'seeds': [2026, 2027, 2028, 2029, 2030]}
    try:
        hardware['hardware_powershell'] = subprocess.check_output(
            ['powershell', '-NoProfile', '-Command',
             "Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json -Compress"],
            text=True).strip()
        hardware['memory_bytes'] = int(subprocess.check_output(
            ['powershell', '-NoProfile', '-Command',
             '(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory'], text=True).strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        hardware['hardware_unavailable'] = True
    write_json(OUT/'environment.json', hardware)
    b = build_a4()
    full = b.full_occupancy
    # Controlled baseline ablation on all four scenarios.
    for scenario in ['safe', 'smoke', 'stair_block', 'exit_block']:
        measured(f'balanced/{scenario}', b, full, scenario, 'M1E')
        for weight in [1, 2, 4, 8]:
            measured(f'm3/{scenario}/w{weight}', b, full, scenario, 'M3', weight)
    # Five fresh repeats on identical inputs, including stage instrumentation.
    for repetition in range(1, 6):
        measured(f'runtime/r{repetition}', b, full)
    # Seed affects allocation, with an exact total fixed at each load level.
    for load in [.3, .5, .7]:
        for seed in range(2026, 2031):
            occupancy = make_occupancy(b, people=round(1360*load), seed=seed)
            measured(f'population/p{round(100*load)}_s{seed}', b, occupancy)
    # One-factor-at-a-time whole-building sensitivity, not ground-only.
    variants = [('width12', {'assumed_stair_usable_width_m': 1.2}),
                ('width18', {'assumed_stair_usable_width_m': 1.8}),
                ('speed05', {'stair_speed_m_s': .5}),
                ('speed09', {'stair_speed_m_s': .9}),
                ('dt10', {'time_step_seconds': 10}),
                ('dt2', {'time_step_seconds': 2})]
    for key, overrides in variants:
        changed = build_a4(overrides)
        measured(f'sensitivity/{key}', changed, changed.full_occupancy)
    write_json(OUT/'complete.json', {'complete': True, 'runs': 46})


if __name__ == '__main__':
    main()
