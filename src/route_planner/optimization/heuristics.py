from __future__ import annotations

from math import inf
from typing import List, Sequence, Tuple


def optimize_open_route(matrix: Sequence[Sequence[float]]) -> List[int]:
    order, _ = solve_open_route(matrix)
    return order


def solve_open_route(matrix: Sequence[Sequence[float]]) -> Tuple[List[int], str]:
    size = len(matrix)
    if size <= 2:
        return list(range(size)), "trivial"

    middle_count = size - 2
    if middle_count <= 10:
        return _exact_open_route(matrix), "exact_dp"

    remaining = set(range(1, size - 1))
    order = [0]
    current = 0

    while remaining:
        next_index = min(
            remaining,
            key=lambda idx: matrix[current][idx] if matrix[current][idx] is not None else inf,
        )
        order.append(next_index)
        remaining.remove(next_index)
        current = next_index

    order.append(size - 1)
    order = _two_opt_open(order, matrix)
    return order, "nearest_neighbor_2opt"


def _exact_open_route(matrix: Sequence[Sequence[float]]) -> List[int]:
    size = len(matrix)
    middle_nodes = list(range(1, size - 1))
    count = len(middle_nodes)
    if count == 0:
        return [0, size - 1]

    dp = {}

    for idx, node in enumerate(middle_nodes):
        mask = 1 << idx
        dp[(mask, node)] = (_edge_cost(matrix, 0, node), (0, node))

    for mask in range(1, 1 << count):
        for idx, node in enumerate(middle_nodes):
            bit = 1 << idx
            if not mask & bit:
                continue
            state = (mask, node)
            if state not in dp:
                continue
            current_cost, current_path = dp[state]
            for next_idx, next_node in enumerate(middle_nodes):
                next_bit = 1 << next_idx
                if mask & next_bit:
                    continue
                next_mask = mask | next_bit
                candidate_cost = current_cost + _edge_cost(matrix, node, next_node)
                candidate_state = (next_mask, next_node)
                candidate_path = current_path + (next_node,)
                existing = dp.get(candidate_state)
                if existing is None or candidate_cost < existing[0]:
                    dp[candidate_state] = (candidate_cost, candidate_path)

    full_mask = (1 << count) - 1
    best_path = None
    best_cost = inf
    for node in middle_nodes:
        state = (full_mask, node)
        entry = dp.get(state)
        if entry is None:
            continue
        route_cost = entry[0] + _edge_cost(matrix, node, size - 1)
        if route_cost < best_cost:
            best_cost = route_cost
            best_path = entry[1]

    if best_path is None:
        return list(range(size))

    return list(best_path) + [size - 1]


def _two_opt_open(order: List[int], matrix: Sequence[Sequence[float]]) -> List[int]:
    best = order[:]
    best_cost = _route_cost(best, matrix)
    improved = True

    while improved:
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                candidate = best[:i] + list(reversed(best[i : j + 1])) + best[j + 1 :]
                candidate_cost = _route_cost(candidate, matrix)
                if candidate_cost < best_cost:
                    best = candidate
                    best_cost = candidate_cost
                    improved = True
        # Re-run until no better swap is found.

    return best


def _route_cost(order: Sequence[int], matrix: Sequence[Sequence[float]]) -> float:
    total = 0.0
    for left, right in zip(order, order[1:]):
        value = matrix[left][right]
        if value is None:
            return inf
        total += value
    return total


def _edge_cost(matrix: Sequence[Sequence[float]], left: int, right: int) -> float:
    value = matrix[left][right]
    if value is None:
        return inf
    return value
