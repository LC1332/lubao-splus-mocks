"""Generation and exact validation for irregular square-counting grids."""
from __future__ import annotations

from collections import deque
from itertools import product
import random

ROWS, COLS = 5, 6
Matrix = tuple[tuple[int, ...], ...]


def squares(matrix: Matrix) -> dict[int, list[tuple[int, int, int]]]:
    """Return every fully retained k-by-k region as (row, column, k)."""
    result: dict[int, list[tuple[int, int, int]]] = {k: [] for k in range(1, min(ROWS, COLS) + 1)}
    for k in result:
        for r in range(ROWS - k + 1):
            for c in range(COLS - k + 1):
                if all(matrix[y][x] for y in range(r, r + k) for x in range(c, c + k)):
                    result[k].append((r, c, k))
    return result


def visible_edges(matrix: Matrix) -> set[tuple[tuple[int, int], tuple[int, int]]]:
    """Unit segments visible in the rendered cell-union outline and grid."""
    edges = set()
    for r, row in enumerate(matrix):
        for c, kept in enumerate(row):
            if not kept:
                continue
            edges.update({((r, c), (r, c + 1)), ((r + 1, c), (r + 1, c + 1)),
                          ((r, c), (r + 1, c)), ((r, c + 1), (r + 1, c + 1))})
    return edges


def framed_squares(matrix: Matrix) -> dict[int, list[tuple[int, int, int]]]:
    """Enumerate all square outlines whose four sides are visibly complete."""
    edges = visible_edges(matrix)
    result: dict[int, list[tuple[int, int, int]]] = {k: [] for k in range(1, ROWS + 1)}
    for k in result:
        for r in range(ROWS - k + 1):
            for c in range(COLS - k + 1):
                perimeter = (
                    [((r, x), (r, x + 1)) for x in range(c, c + k)]
                    + [((r + k, x), (r + k, x + 1)) for x in range(c, c + k)]
                    + [((y, c), (y + 1, c)) for y in range(r, r + k)]
                    + [((y, c + k), (y + 1, c + k)) for y in range(r, r + k)]
                )
                if all(edge in edges for edge in perimeter):
                    result[k].append((r, c, k))
    return result


def connected(matrix: Matrix) -> bool:
    cells = {(r, c) for r in range(ROWS) for c in range(COLS) if matrix[r][c]}
    if not cells:
        return False
    seen = {next(iter(cells))}
    queue = deque(seen)
    while queue:
        r, c = queue.popleft()
        for nxt in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if nxt in cells and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen == cells


def has_bbox_gap(matrix: Matrix) -> bool:
    """Whether the retained shape's bounding rectangle contains a missing cell."""
    cells = {(r, c) for r in range(ROWS) for c in range(COLS) if matrix[r][c]}
    if not cells:
        return False
    r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
    c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
    missing = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)} - cells
    return bool(missing)


def has_enclosed_hole(matrix: Matrix) -> bool:
    """Whether any missing cells form a 4-connected void enclosed by retained cells."""
    cells = {(r, c) for r in range(ROWS) for c in range(COLS) if matrix[r][c]}
    if not cells:
        return False
    r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
    c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
    missing = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)} - cells
    exterior = {p for p in missing if p[0] in (r0, r1) or p[1] in (c0, c1)}
    queue = deque(exterior)
    while queue:
        r, c = queue.popleft()
        for nxt in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if nxt in missing and nxt not in exterior:
                exterior.add(nxt)
                queue.append(nxt)
    return bool(missing - exterior)


def canonical_key(matrix: Matrix) -> str:
    """Canonical normalized shape key under translations, rotations and reflections."""
    points = [(r, c) for r in range(ROWS) for c in range(COLS) if matrix[r][c]]
    variants = []
    for flip in (1, -1):
        for rotation in range(4):
            transformed = []
            for r, c in points:
                x, y = r, flip * c
                for _ in range(rotation):
                    x, y = y, -x
                transformed.append((x, y))
            min_x = min(x for x, _ in transformed)
            min_y = min(y for _, y in transformed)
            normalized = tuple(sorted((x - min_x, y - min_y) for x, y in transformed))
            variants.append(normalized)
    return repr(min(variants))


def validate(matrix: Matrix) -> dict:
    retained = sum(map(sum, matrix))
    region = squares(matrix)
    framed = framed_squares(matrix)
    checks = {
        "dimensions": len(matrix) == ROWS and all(len(row) == COLS for row in matrix),
        "deletes_cells": 0 < retained < ROWS * COLS,
        "connected": connected(matrix),
        "contains_3x3": bool(region[3]),
        "irregular_outline": has_bbox_gap(matrix),
        "no_enclosed_holes": not has_enclosed_hole(matrix),
        "visible_matches_regions": region == framed,
    }
    return {"valid": all(checks.values()), "checks": checks,
            "retained_cells": retained, "counts": {str(k): len(v) for k, v in region.items()},
            "total": sum(map(len, region.values())), "square_positions": {
                str(k): [list(square) for square in values] for k, values in region.items()},
            "framed_square_positions": {str(k): [list(square) for square in values]
                                        for k, values in framed.items()}}


def make_questions(count: int = 12, seed: int = 20261014, max_attempts: int = 200_000) -> list[dict]:
    """Generate distinct valid shapes deterministically; fail without relaxing constraints."""
    rng = random.Random(seed)
    found: dict[str, Matrix] = {}
    attempts = 0
    # A protected 3x3 makes the instructional requirement likely; all other
    # cells are sampled independently, then every property is checked afresh.
    while len(found) < count and attempts < max_attempts:
        attempts += 1
        anchor_r = rng.randrange(ROWS - 2)
        anchor_c = rng.randrange(COLS - 2)
        density = rng.uniform(0.28, 0.68)
        protected = {(r, c) for r in range(anchor_r, anchor_r + 3)
                     for c in range(anchor_c, anchor_c + 3)}
        cells = [[int((r, c) in protected or rng.random() < density)
                  for c in range(COLS)] for r in range(ROWS)]
        matrix: Matrix = tuple(tuple(row) for row in cells)
        report = validate(matrix)
        if not report["valid"]:
            continue
        key = canonical_key(matrix)
        if key in found:
            continue
        found[key] = matrix
    if len(found) != count:
        raise RuntimeError(f"最多尝试 {max_attempts} 次后仅得到 {len(found)}/{count} 道合格且不重复的题目；未放宽条件。")
    questions = []
    for number, (key, matrix) in enumerate(found.items(), 1):
        report = validate(matrix)
        questions.append({"number": number, "matrix": [list(row) for row in matrix],
                          "retained_cells": report["retained_cells"], "counts": report["counts"],
                          "total": report["total"], "square_positions": report["square_positions"],
                          "canonical_key": key, "checks": report["checks"]})
    return questions


def complete_matrix() -> Matrix:
    return tuple(tuple(1 for _ in range(COLS)) for _ in range(ROWS))


def isolated_3x3_matrix() -> Matrix:
    return tuple(tuple(int(1 <= r <= 3 and 1 <= c <= 3) for c in range(COLS)) for r in range(ROWS))
