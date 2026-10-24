import random
import pytest

from a4_evac.algorithms import Network, dinic, min_cost, shortest_path, multi_source


def test_shortest_paths_zero_weights_and_astar():
    graph = {"s": [("a", 0, "sa"), ("b", 8, "sb")], "a": [("b", 2, "ab")], "b": []}
    assert shortest_path(graph, "s", {"b"})[:2] == (2, ["sa", "ab"])
    assert shortest_path(graph, "s", {"b"}, lambda n: {"s": 2, "a": 2, "b": 0}[n])[0] == 2
    assert shortest_path(graph, "b", {"s"})[0] == float("inf")
    assert multi_source({"a": [("b", 10)], "b": [("c", 5)], "c": []}, [("a", 20), ("b", 7)])["c"] == 12


def test_residual_rerouting_and_insufficient_flow():
    net = Network(6)
    for u, v, cost in [(0, 1, 0), (0, 2, 0), (1, 3, 0), (1, 4, 1), (2, 3, 0), (3, 5, 0), (4, 5, 0)]:
        net.add(u, v, 1, cost)
    assert min_cost(net, 0, 5, 2) == (2, 1)
    net = Network(2)
    net.add(0, 1, 2, 3)
    assert min_cost(net, 0, 1, 3) == (2, 6)


def test_iterative_dinic_deep_graph():
    net = Network(2101)
    for i in range(2100):
        net.add(i, i+1, 3)
    assert dinic(net, 0, 2100) == 3


@pytest.mark.parametrize("seed", range(25))
def test_random_flow_against_networkx(seed):
    nx = pytest.importorskip("networkx")
    rng, oracle, flow_net, cost_net = random.Random(seed), nx.DiGraph(), Network(8), Network(8)
    oracle.add_nodes_from(range(8))
    for u in range(8):
        for v in range(8):
            if u != v and rng.random() < 0.25:
                cap, cost = rng.randrange(6), rng.randrange(5)
                oracle.add_edge(u, v, capacity=cap, weight=cost)
                flow_net.add(u, v, cap, cost)
                cost_net.add(u, v, cap, cost)
    expected = nx.maximum_flow_value(oracle, 0, 7)
    assert dinic(flow_net, 0, 7) == expected
    flow, cost = min_cost(cost_net, 0, 7, expected)
    assert flow == expected
    assert cost == nx.cost_of_flow(oracle, nx.max_flow_min_cost(oracle, 0, 7))
