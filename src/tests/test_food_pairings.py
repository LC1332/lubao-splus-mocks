import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from food_pairings_logic import (dedup_key, enumerate_pairings, make_questions,
                                 validate_question)


def make_question(prices_a, prices_b, duplicate_group="b"):
    def group(prices, prefix):
        return {"category": prefix, "unit": "份", "items": [
            {"id": f"{prefix}{i}", "name": f"{prefix}{i}", "price": price}
            for i, price in enumerate(prices)]}
    return {"group_a": group(prices_a, "a"), "group_b": group(prices_b, "b"),
            "duplicate_group": duplicate_group}


class FoodPairingLogicTests(unittest.TestCase):
    def test_reference_example_has_eight_pairings_and_five_totals(self):
        pairs = enumerate_pairings(make_question([17, 12], [18, 23, 25, 18])["group_a"]["items"],
                                   make_question([17, 12], [18, 23, 25, 18])["group_b"]["items"])
        self.assertEqual(8, len(pairs))
        self.assertEqual([30, 35, 37, 40, 42], sorted({p["total"] for p in pairs}))

    def test_strict_example_has_twelve_pairings_and_seven_totals(self):
        q = make_question([12, 17, 22], [18, 23, 25, 18])
        report = validate_question(q)
        self.assertTrue(report["valid"], report["checks"])
        self.assertEqual(12, report["product_pairing_count"])
        self.assertEqual([30, 35, 37, 40, 42, 45, 47], report["distinct_totals"])
        self.assertEqual(7, report["answer"])
        self.assertEqual(2, len(report["duplicate_price_witness"]["item_ids"]))
        self.assertGreater(report["equal_difference_witness"]["difference"], 0)

    def test_ten_totals_is_accepted_and_eleven_is_rejected(self):
        ten = make_question([19, 31, 27, 15, 35], [15, 15, 31, 23, 19])
        eleven = make_question([38, 34, 35, 36, 31], [41, 41, 36, 38, 39])
        self.assertEqual(10, validate_question(ten)["answer"])
        self.assertTrue(validate_question(ten)["valid"])
        self.assertEqual(11, validate_question(eleven)["answer"])
        self.assertFalse(validate_question(eleven)["checks"]["distinct_total_count_range"])

    def test_invalid_group_sizes_and_missing_repeated_price_are_rejected(self):
        self.assertFalse(validate_question(make_question([12, 17, 22], [18, 18, 23]))["checks"]["group_sizes"])
        self.assertFalse(validate_question(make_question([12, 17], [18, 18, 23, 25]))["checks"]["group_sizes"])
        q = make_question([12, 17, 22], [18, 23, 25, 30])
        self.assertFalse(validate_question(q)["checks"]["duplicate_price_products"])

    def test_missing_distinct_other_prices_and_nonzero_equal_difference_are_rejected(self):
        q = make_question([12, 12, 12, 12], [18, 18, 23, 25])
        self.assertFalse(validate_question(q)["checks"]["other_group_has_distinct_prices"])
        q = make_question([11, 18, 27, 36], [20, 20, 22, 25])
        self.assertFalse(validate_question(q)["checks"]["nonzero_equal_difference"])

    def test_dedup_key_ignores_order_and_group_swap_but_preserves_repetition(self):
        self.assertEqual(dedup_key([12, 12, 17], [18, 23, 25]),
                         dedup_key([25, 18, 23], [17, 12, 12]))
        self.assertNotEqual(dedup_key([12, 17], [18, 23]),
                            dedup_key([12, 12, 17], [18, 23]))

    def test_seed_reproduces_twelve_questions_and_three_total_prompts(self):
        first = make_questions(12, 3, 20261014)
        second = make_questions(12, 3, 20261014)
        self.assertEqual(first, second)
        self.assertEqual(12, len(first))
        self.assertEqual(3, sum(q["question_type"] == "distinct_totals" for q in first))
        self.assertEqual([4, 8, 12], [q["number"] for q in first if q["question_type"] == "distinct_totals"])
        self.assertGreaterEqual(len({tuple(q["group_sizes"].values()) for q in first}), 2)
        self.assertEqual(12, len({tuple(tuple(x) for x in q["dedup_key"]) for q in first}))


if __name__ == "__main__":
    unittest.main()
