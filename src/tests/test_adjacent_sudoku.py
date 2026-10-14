import sys
import unittest
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adjacent_sudoku_logic import (  # noqa: E402
    all_latin_solutions, candidate_pools, count_solutions, edge_pattern,
    edge_rule_is_valid, has_ordered_line, is_valid_solution, make_questions,
    validate_question,
)


class AdjacentSudokuLogicTests(unittest.TestCase):
    def test_all_edges_are_bidirectional(self):
        grid = ((1, 2, 4, 3), (3, 4, 2, 1), (2, 1, 3, 4), (4, 3, 1, 2))
        lr, ud = edge_pattern(grid)
        self.assertTrue(edge_rule_is_valid(grid, lr, ud))
        broken = [list(row) for row in lr]
        broken[0][0] = False  # red edge whose values differ by one
        self.assertFalse(edge_rule_is_valid(grid, broken, ud))
        broken = [list(row) for row in lr]
        broken[0][1] = True  # unmarked edge whose values differ by two
        self.assertFalse(edge_rule_is_valid(grid, broken, ud))
        broken_ud = [list(row) for row in ud]
        broken_ud[0][0] = not broken_ud[0][0]
        self.assertFalse(edge_rule_is_valid(grid, lr, broken_ud))
        one_four = next((g, r, c) for g in all_latin_solutions() for r in range(4) for c in range(3)
                        if {g[r][c], g[r][c + 1]} == {1, 4})
        g, r, c = one_four
        self.assertFalse(edge_pattern(g)[0][r][c])

    def test_latin_solution_has_no_box_or_diagonal_rule(self):
        grid = next(g for g in all_latin_solutions()
                    if len({g[0][0], g[0][1], g[1][0], g[1][1]}) < 4)
        self.assertTrue(is_valid_solution(grid))
        diagonal_repeat = next(g for g in all_latin_solutions()
                               if len({g[i][i] for i in range(4)}) < 4)
        self.assertTrue(is_valid_solution(diagonal_repeat))

    def test_ordered_line_directions_and_nonmatches(self):
        self.assertTrue(has_ordered_line(((1, 2, 3, 4), (3, 4, 1, 2), (2, 1, 4, 3), (4, 3, 2, 1))))
        self.assertTrue(has_ordered_line(((4, 3, 2, 1), (3, 4, 1, 2), (2, 1, 4, 3), (1, 2, 3, 4))))
        self.assertTrue(has_ordered_line(((1, 2, 4, 3), (2, 1, 3, 4), (3, 4, 1, 2), (4, 3, 2, 1))))
        self.assertTrue(has_ordered_line(((4, 2, 3, 1), (3, 1, 4, 2), (2, 4, 1, 3), (1, 3, 2, 4))))
        self.assertFalse(has_ordered_line(((2, 3, 4, 1),) * 4))

    def test_solver_distinguishes_unique_and_multiple(self):
        unique = next(item for pool in candidate_pools() for item in pool)
        lr, ud, given = unique["key"]
        self.assertEqual(count_solutions(given, lr, ud), 1)
        self.assertGreater(count_solutions(None, lr, ud), 1)
        self.assertEqual(count_solutions(None, ((False,) * 3,) * 4, ((False,) * 4,) * 3), 0)

    def test_generation_reproducible_and_independent_class_draw(self):
        first = make_questions(12, 20261014)
        again = make_questions(12, 20261014)
        signature = lambda qs: [(q["puzzle_key"], q["target_category"]) for q in qs]
        self.assertEqual(signature(first), signature(again))
        self.assertNotEqual(signature(first), signature(make_questions(12, 20261015)))
        self.assertEqual(len({q["puzzle_key"] for q in first}), 12)
        self.assertTrue(all(validate_question(q) for q in first))
        self.assertGreaterEqual(min(len(p) for p in candidate_pools()), 12)

    def test_category_probability_and_extreme_pool_capacity(self):
        rng = random.Random(20261014)
        hits = sum(rng.getrandbits(1) for _ in range(10_000))
        self.assertTrue(4_800 <= hits <= 5_200, hits)
        for pool in candidate_pools():
            self.assertGreaterEqual(len(pool), 12)
            sample = pool[:12]
            self.assertEqual(len({item["key"] for item in sample}), 12)
            self.assertTrue(all(item["actual_category"] == bool(pool is candidate_pools()[1])
                                for item in sample))


if __name__ == "__main__":
    unittest.main()
