from collections import Counter
import pytest

from a4_evac.algorithms import Network, min_cost
from a4_evac.baselines import baseline
from a4_evac.data import build_a4
from a4_evac.hazards import simulate_hazards, scenario_named
from a4_evac.runner import run


def test_cost_phase_counters_preserve_optimum():
    net = Network(4)
    net.add(0, 1, 2)
    net.add(1, 3, 2, 1)
    net.add(0, 2, 3)
    net.add(2, 3, 3, 4)
    stats = {}
    assert min_cost(net, 0, 3, 5, stats=stats) == (5, 14)
    assert stats['cost_phases'] == 2
    assert stats['augmentations'] == 2


def test_balanced_baseline_splits_upper_population_and_preserves_ground_exit():
    b = build_a4()
    data = run(b, scenario_named('safe', 900), {'R205': 10, 'R101': 4}, 'M1E')
    result, metrics, _, _, validation = data
    assert validation['valid'] and metrics['evacuated_count'] == 14
    throughput = Counter(j.exit_node for j in result.schedule)
    assert throughput['EXIT1'] == throughput['EXIT2'] == 5
    assert throughput['D101_1'] == 4


def test_m3_rejects_invalid_penalty():
    b = build_a4()
    hazards = simulate_hazards(b, scenario_named('safe', 120))
    with pytest.raises(ValueError, match='weight'):
        baseline(b, hazards, {'R101': 1}, 24, 'M3', m3_weight=float('nan'))
