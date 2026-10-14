"""Logic, exhaustive candidate construction, and reproducible sampling for 4x4 puzzles."""
from __future__ import annotations

from functools import lru_cache
from itertools import permutations, product
import random
from typing import Iterator, Sequence

Grid = tuple[tuple[int, ...], ...]
RedLR = tuple[tuple[bool, ...], ...]  # cells joined left-to-right; drawn on a vertical edge
RedUD = tuple[tuple[bool, ...], ...]  # cells joined top-to-bottom; drawn on a horizontal edge
PuzzleKey = tuple[RedLR, RedUD, tuple[int, int, int]]
SYMBOLS = (1, 2, 3, 4)
ROWS = tuple(permutations(SYMBOLS))


def is_valid_solution(grid: Sequence[Sequence[int]]) -> bool:
    if len(grid) != 4 or any(len(row) != 4 for row in grid):
        return False
    expected = set(SYMBOLS)
    return all(set(row) == expected for row in grid) and all(
        {grid[r][c] for r in range(4)} == expected for c in range(4)
    )


def has_ordered_line(grid: Sequence[Sequence[int]]) -> bool:
    forward, backward = SYMBOLS, SYMBOLS[::-1]
    return any(tuple(row) in (forward, backward) for row in grid) or any(
        tuple(grid[r][c] for r in range(4)) in (forward, backward) for c in range(4)
    )


def edge_pattern(grid: Sequence[Sequence[int]]) -> tuple[RedLR, RedUD]:
    lr = tuple(tuple(abs(grid[r][c] - grid[r][c + 1]) == 1 for c in range(3)) for r in range(4))
    ud = tuple(tuple(abs(grid[r][c] - grid[r + 1][c]) == 1 for c in range(4)) for r in range(3))
    return lr, ud


def edge_rule_is_valid(grid: Sequence[Sequence[int]], lr: Sequence[Sequence[bool]],
                       ud: Sequence[Sequence[bool]]) -> bool:
    if len(lr) != 4 or any(len(row) != 3 for row in lr) or len(ud) != 3 or any(len(row) != 4 for row in ud):
        return False
    got_lr, got_ud = edge_pattern(grid)
    return got_lr == tuple(tuple(row) for row in lr) and got_ud == tuple(tuple(row) for row in ud)


def puzzle_key(grid: Sequence[Sequence[int]], given: tuple[int, int, int]) -> PuzzleKey:
    lr, ud = edge_pattern(grid)
    return lr, ud, given


def _matches_key(grid: Grid, key: PuzzleKey) -> bool:
    lr, ud, (gr, gc, value) = key
    return grid[gr][gc] == value and edge_pattern(grid) == (lr, ud)


def iter_solutions(given: tuple[int, int, int] | None, lr: Sequence[Sequence[bool]],
                   ud: Sequence[Sequence[bool]], limit: int | None = None) -> Iterator[Grid]:
    """Enumerate visible-clue solutions; stop after ``limit`` if requested."""
    if len(lr) != 4 or any(len(row) != 3 for row in lr) or len(ud) != 3 or any(len(row) != 4 for row in ud):
        return
    if given is not None:
        gr, gc, value = given
        if not (0 <= gr < 4 and 0 <= gc < 4 and value in SYMBOLS):
            return
    found = 0

    def visit(rows: list[tuple[int, ...]]) -> Iterator[Grid]:
        nonlocal found
        r = len(rows)
        if r == 4:
            result = tuple(rows)
            found += 1
            yield result
            return
        for row in ROWS:
            if given is not None and r == gr and row[gc] != value:
                continue
            if any(row[c] in {prev[c] for prev in rows} for c in range(4)):
                continue
            if any((abs(rows[r - 1][c] - row[c]) == 1) != ud[r - 1][c] for c in range(4)) if r else False:
                continue
            if any((abs(row[c] - row[c + 1]) == 1) != lr[r][c] for c in range(3)):
                continue
            yield from visit(rows + [row])
            if limit is not None and found >= limit:
                return

    yield from visit([])


def count_solutions(given: tuple[int, int, int] | None, lr: Sequence[Sequence[bool]],
                    ud: Sequence[Sequence[bool]], limit: int = 2) -> int:
    return sum(1 for _ in iter_solutions(given, lr, ud, limit=limit))


@lru_cache(maxsize=1)
def all_latin_solutions() -> tuple[Grid, ...]:
    return tuple(rows for rows in product(ROWS, repeat=4)
                 if all(len({rows[r][c] for r in range(4)}) == 4 for c in range(4)))


@lru_cache(maxsize=1)
def candidate_pools() -> tuple[tuple[dict, ...], tuple[dict, ...]]:
    """Return pools indexed by ordered-line false/true, in stable puzzle-key order."""
    solutions = all_latin_solutions()
    by_pattern: dict[tuple[RedLR, RedUD], list[Grid]] = {}
    for grid in solutions:
        by_pattern.setdefault(edge_pattern(grid), []).append(grid)
    unique: list[dict] = []
    for grid in solutions:
        pattern = edge_pattern(grid)
        for r in range(4):
            for c in range(4):
                if grid[r][c] != 2:
                    continue
                given = (r, c, 2)
                matches = [other for other in by_pattern[pattern] if other[r][c] == 2]
                if len(matches) == 1 and matches[0] == grid:
                    unique.append({"key": (pattern[0], pattern[1], given), "solution": grid,
                                   "actual_category": has_ordered_line(grid)})
    unique.sort(key=lambda item: item["key"])
    buckets: dict[bool, dict[PuzzleKey, dict]] = {False: {}, True: {}}
    for candidate in unique:
        buckets[candidate["actual_category"]].setdefault(candidate["key"], candidate)
    return tuple(tuple(buckets[k].values()) for k in (False, True))  # type: ignore[return-value]


def make_questions(count: int = 12, seed: int = 20261014) -> list[dict]:
    if count < 1:
        raise ValueError("题目数量必须至少为 1")
    pools = candidate_pools()
    for category, pool in zip((False, True), pools):
        if len(pool) < 12:
            name = "无顺序行列" if not category else "含顺序行列"
            raise RuntimeError(f"{name}候选池只有 {len(pool)} 道不同唯一解题，少于 12 道；未降低出题要求。")
    rng = random.Random(seed)
    chosen: dict[bool, set[PuzzleKey]] = {False: set(), True: set()}
    questions = []
    for number in range(1, count + 1):
        target = bool(rng.getrandbits(1))
        available = [candidate for candidate in pools[target] if candidate["key"] not in chosen[target]]
        if not available:
            raise RuntimeError(f"第 {number} 题所抽类别候选已用尽；未自动更换类别。")
        candidate = rng.choice(available)
        chosen[target].add(candidate["key"])
        lr, ud, given = candidate["key"]
        questions.append({"number": number, "given": {"row": given[0], "column": given[1], "value": given[2]},
                          "left_right_red": lr, "up_down_red": ud, "solution": candidate["solution"],
                          "target_category": target, "actual_category": candidate["actual_category"],
                          "puzzle_key": candidate["key"]})
    return questions


def validate_question(question: dict) -> bool:
    grid = question["solution"]
    given_obj = question["given"]
    given = (given_obj["row"], given_obj["column"], given_obj["value"])
    if not is_valid_solution(grid) or given[2] != 2 or grid[given[0]][given[1]] != 2:
        return False
    if not edge_rule_is_valid(grid, question["left_right_red"], question["up_down_red"]):
        return False
    return (question["target_category"] == has_ordered_line(grid)
            and count_solutions(given, question["left_right_red"], question["up_down_red"]) == 1)
