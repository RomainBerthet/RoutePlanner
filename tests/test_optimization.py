from route_planner.optimization import solve_open_route


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
