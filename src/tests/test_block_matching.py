import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from block_matching_geometry import judge, matrix_from_heights, valid_structure
from block_matching_generator import make_questions


class GeometryTests(unittest.TestCase):
    def test_reference_example_and_back_row_projection(self):
        correct = matrix_from_heights(((1, 0, 1), (1, 1, 2)))
        target_floor = frozenset({(0, 0), (2, 0), (0, 1), (1, 1), (2, 1)})
        target_wall = frozenset({(0, 0), (1, 0), (2, 0), (2, 1)})
        self.assertEqual(judge(correct, target_floor, target_wall)["truth"], "111")
        high_back = matrix_from_heights(((1, 0, 1), (2, 1, 1)))
        self.assertEqual(judge(high_back, target_floor, target_wall)["truth"], "110")

    def test_floor_requires_exact_cells_and_wall_pass_allows_lower(self):
        floor = frozenset({(0, 0), (1, 0)})
        wall = frozenset({(0, 0), (1, 0), (1, 1)})
        lower = matrix_from_heights(((1, 1), (0, 0)))
        self.assertTrue(judge(lower, floor, wall, wall_rule="pass")["wall_ok"])
        self.assertFalse(judge(lower, floor, wall, wall_rule="exact")["wall_ok"])
        shifted = matrix_from_heights(((0, 1, 1), (0, 0, 0)))
        self.assertFalse(judge(shifted, floor, wall)["floor_ok"])

    def test_rotated_floor_is_not_normalized_to_match(self):
        target = frozenset({(0, 0), (2, 0), (0, 1), (1, 1), (2, 1)})
        turned = matrix_from_heights(((1, 1), (0, 1), (1, 1)))
        self.assertNotEqual(frozenset({(x, y) for y, row in enumerate(turned)
                                       for x, h in enumerate(row) if h}), target)

    def test_connected_supported_structures(self):
        self.assertTrue(valid_structure(matrix_from_heights(((1, 2), (1, 0))), 1, 6))
        self.assertFalse(valid_structure(matrix_from_heights(((1, 0, 1), (0, 0, 0))), 1, 6))


class GeneratedSetTests(unittest.TestCase):
    def test_five_fixed_seeds_make_twelve_unique_valid_questions(self):
        for seed in (20261014, 42, 7, 1234, 8675309):
            questions = make_questions(12, seed)
            self.assertEqual(len(questions), 12)
            self.assertEqual({q["answer"]: sum(x["answer"] == q["answer"] for x in questions)
                              for q in questions}, {"A": 3, "B": 3, "C": 3, "D": 3})
            self.assertEqual(len({(tuple(map(tuple, q["target_floor"])), tuple(map(tuple, q["target_wall"])))
                                  for q in questions}), 12)
            self.assertEqual({typ for q in questions for typ in q["two_true_types"]}, {"110", "101", "011"})
            self.assertEqual({q["one_true_type"] for q in questions}, {"100", "010", "001"})
            for q in questions:
                self.assertEqual(len(q["options"]), 4)
                self.assertEqual(sum(o["is_answer"] for o in q["options"]), 1)
                self.assertEqual(sum(o["truth"] == "111" for o in q["options"]), 1)
                self.assertTrue(all(o["truth"].count("1") in (1, 2) for o in q["options"] if not o["is_answer"]))
                self.assertEqual({o["letter"] for o in q["options"]}, set("ABCD"))


if __name__ == "__main__":
    unittest.main()
