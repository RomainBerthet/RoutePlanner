import random

from route_planner.optimization import solve_open_route


def _route_cost(order, matrix):
    return sum(matrix[a][b] for a, b in zip(order, order[1:]))


def test_solve_open_route_exact_dp():
    matrix = [
        [0, 5, 1, 50],
        [5, 0, 10, 1],
        [1, 1, 0, 10],
        [50, 1, 10, 0],
    ]

    order, strategy = solve_open_route(matrix)

    assert order == [0, 2, 1, 3]
    assert strategy == "exact_dp"


def _euclidean_matrix(points):
    return [
        [((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 for bx, by in points]
        for ax, ay in points
    ]


def test_local_search_pins_endpoints_and_visits_all():
    random.seed(7)
    points = [(random.random(), random.random()) for _ in range(16)]
    matrix = _euclidean_matrix(points)

    order, strategy = solve_open_route(matrix)

    assert strategy == "nearest_neighbor_local_search"
    assert order[0] == 0 and order[-1] == len(points) - 1
    assert sorted(order) == list(range(len(points)))


def test_local_search_not_worse_than_nearest_neighbor():
    random.seed(11)
    points = [(random.random(), random.random()) for _ in range(18)]
    matrix = _euclidean_matrix(points)

    # Reproduce the raw nearest-neighbor construction the solver starts from.
    remaining = set(range(1, len(points) - 1))
    nn = [0]
    current = 0
    while remaining:
        nxt = min(remaining, key=lambda idx: matrix[current][idx])
        nn.append(nxt)
        remaining.remove(nxt)
        current = nxt
    nn.append(len(points) - 1)

    order, _ = solve_open_route(matrix)

    assert _route_cost(order, matrix) <= _route_cost(nn, matrix) + 1e-9
