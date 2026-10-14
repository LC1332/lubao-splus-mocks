import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from grid_area_logic import (generate_questions, triangle_area2, triangle_template_ok,
                             triangles_overlap, validate_question, left_area2, validate_left)


class GridAreaTests(unittest.TestCase):
    def test_left_area_and_unit_conversion(self):
        parts = ([{"kind": "square", "cell": (i + 1, 0), "orientation": 0} for i in range(6)] +
                 [{"kind": "half", "cell": (i, 2), "orientation": 0} for i in range(10)])
        self.assertEqual(left_area2(parts), 22)
        self.assertEqual((left_area2(parts) // 2) * 1, 11)
        self.assertEqual((left_area2(parts) // 2) * 2, 22)
        self.assertFalse(validate_left([{"kind": "half", "cell": (2, 2), "orientation": 0},
                                        {"kind": "half", "cell": (2, 2), "orientation": 2}] + parts[:3] + parts[6:12]))

    def test_triangle_reference_areas_and_half_integer(self):
        four_cells = ((0, 2), (2, 0), (3, 3))
        two_and_half = ((0, 1), (2, 2), (3, 0))
        self.assertTrue(triangle_template_ok(four_cells))
        self.assertTrue(triangle_template_ok(two_and_half))
        self.assertEqual(triangle_area2(four_cells), 8)
        self.assertEqual(triangle_area2(two_and_half), 5)

    def test_overlap_distinguishes_shared_edge_from_positive_area(self):
        a = ((1, 1), (3, 1), (1, 3))
        shares_edge = ((3, 1), (1, 3), (3, 3))
        overlaps = ((2, 1), (4, 1), (2, 3))
        self.assertFalse(triangles_overlap(a, shares_edge))
        self.assertTrue(triangles_overlap(a, overlaps))

    def test_seeded_batch_meets_constraints_and_is_reproducible(self):
        first = generate_questions(12, 20261014)
        second = generate_questions(12, 20261014)
        self.assertEqual(first, second)
        self.assertEqual([1] * 6, sorted(q["left_unit"] for q in first)[:6])
        self.assertEqual([2] * 6, sorted(q["left_unit"] for q in first)[6:])
        for question in first:
            self.assertTrue(validate_question(question))
            self.assertEqual(5, len(question["right"]["triangles"]))
            self.assertEqual(0, question["left"]["half_triangles"] % 2)
            self.assertTrue(any(area % 2 for area in question["right"]["triangle_area2"]))


if __name__ == "__main__":
    unittest.main()
