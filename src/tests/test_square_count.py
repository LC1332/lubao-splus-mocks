"""Core regression checks for square-counting geometry."""
import unittest

from square_count_logic import (
    canonical_key, complete_matrix, connected, framed_squares,
    isolated_3x3_matrix, make_questions, squares, validate,
)


class SquareCountTests(unittest.TestCase):
    def test_complete_5_by_6_baseline(self):
        result = squares(complete_matrix())
        self.assertEqual([len(result[k]) for k in range(1, 6)], [30, 20, 12, 6, 2])
        self.assertEqual(sum(map(len, result.values())), 70)

    def test_isolated_3_by_3_baseline(self):
        result = squares(isolated_3x3_matrix())
        self.assertEqual([len(result[k]) for k in range(1, 6)], [9, 4, 1, 0, 0])
        self.assertEqual(sum(map(len, result.values())), 14)

    def test_one_missing_cell_removes_only_squares_that_cover_it(self):
        matrix = [list(row) for row in complete_matrix()]
        matrix[0][0] = 0
        result = squares(tuple(tuple(row) for row in matrix))
        self.assertEqual([len(result[k]) for k in range(1, 6)], [29, 19, 11, 5, 1])

    def test_four_neighbor_connectivity_rejects_diagonal_contact(self):
        self.assertFalse(connected(((1, 0, 0, 0, 0, 0), (0, 1, 0, 0, 0, 0),
                                    (0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0),
                                    (0, 0, 0, 0, 0, 0))))

    def test_missing_cell_can_leave_a_visible_phantom_frame(self):
        matrix = [list(row) for row in isolated_3x3_matrix()]
        matrix[2][2] = 0
        matrix = tuple(tuple(row) for row in matrix)
        self.assertNotEqual(squares(matrix), framed_squares(matrix))

    def test_generation_is_repeatable_and_unique_up_to_symmetry(self):
        first = make_questions(12, 20261014)
        second = make_questions(12, 20261014)
        self.assertEqual([q["matrix"] for q in first], [q["matrix"] for q in second])
        self.assertEqual(len({q["canonical_key"] for q in first}), 12)
        self.assertTrue(all(validate(tuple(tuple(row) for row in q["matrix"]))["valid"] for q in first))


if __name__ == "__main__":
    unittest.main()
