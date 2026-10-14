"""Coordinate model and exact checks for block matching questions."""
from __future__ import annotations

from collections import deque
from typing import Iterable

Matrix = tuple[tuple[int, ...], ...]  # rows are y=0 (front) to back; columns are x


def blocks(matrix: Matrix) -> list[tuple[int, int, int]]:
    return [(x, y, z) for y, row in enumerate(matrix) for x, h in enumerate(row) for z in range(h)]


def floor_cells(matrix: Matrix) -> frozenset[tuple[int, int]]:
    return frozenset((x, y) for y, row in enumerate(matrix) for x, h in enumerate(row) if h > 0)


def wall_projection(matrix: Matrix) -> frozenset[tuple[int, int]]:
    return frozenset((x, z) for x in range(max(map(len, matrix)))
                     for z in range(max((row[x] if x < len(row) else 0) for row in matrix)))


def connected(matrix: Matrix) -> bool:
    cells = set(floor_cells(matrix))
    if not cells:
        return False
    seen = {next(iter(cells))}
    todo = deque(seen)
    while todo:
        x, y = todo.popleft()
        for nxt in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if nxt in cells and nxt not in seen:
                seen.add(nxt)
                todo.append(nxt)
    return len(seen) == len(cells)


def valid_structure(matrix: Matrix, min_cubes: int = 1, max_cubes: int = 99, max_height: int = 3) -> bool:
    vals = [v for row in matrix for v in row]
    return bool(vals) and all(0 <= v <= max_height for v in vals) and min_cubes <= sum(vals) <= max_cubes and connected(matrix)


def judge(matrix: Matrix, target_floor: frozenset[tuple[int, int]],
          target_wall: frozenset[tuple[int, int]], target_count: int = 6,
          wall_rule: str = "pass") -> dict:
    count_ok = len(blocks(matrix)) == target_count
    floor_ok = floor_cells(matrix) == target_floor
    projection = wall_projection(matrix)
    wall_ok = projection == target_wall if wall_rule == "exact" else projection <= target_wall
    return {"count_ok": count_ok, "floor_ok": floor_ok, "wall_ok": wall_ok,
            "truth": "".join("1" if b else "0" for b in (count_ok, floor_ok, wall_ok)),
            "cube_count": len(blocks(matrix)),
            "floor_cells": sorted([list(p) for p in floor_cells(matrix)]),
            "wall_projection": sorted([list(p) for p in projection])}


def matrix_from_heights(rows: Iterable[Iterable[int]]) -> Matrix:
    return tuple(tuple(int(x) for x in row) for row in rows)
