"""Deterministic generation of unique, validated four-option questions."""
from __future__ import annotations

from functools import lru_cache
from itertools import product
import random

from block_matching_geometry import Matrix, floor_cells, judge, valid_structure, wall_projection

TWO_TRUE = ("110", "101", "011")
ONE_TRUE = ("100", "010", "001")


@lru_cache(maxsize=1)
def candidate_pool() -> tuple[Matrix, ...]:
    result: list[Matrix] = []
    for width in range(2, 5):
        for flat in product(range(4), repeat=width * 2):
            mat = (tuple(flat[:width]), tuple(flat[width:]))
            n = sum(flat)
            if 5 <= n <= 7 and mat[0].count(0) < width and mat[1].count(0) < width and valid_structure(mat, 5, 7):
                result.append(mat)
    return tuple(result)


def make_questions(count: int, seed: int, wall_rule: str = "pass") -> list[dict]:
    rng = random.Random(seed)
    pool = candidate_pool()
    possible = list(pool)
    rng.shuffle(possible)
    seen_targets: set[tuple] = set()
    questions: list[dict] = []
    answer_slots = list("AAABBBCCCDDD")
    rng.shuffle(answer_slots)

    for qidx in range(count):
        needed_two = (TWO_TRUE[qidx % 3], TWO_TRUE[(qidx + 1) % 3])
        needed_one = ONE_TRUE[qidx % 3]
        found = None
        for correct in possible:
            if sum(map(sum, correct)) != 6 or not (3 <= len(floor_cells(correct)) <= 5):
                continue
            target_floor = floor_cells(correct)
            target_wall = wall_projection(correct)
            target_key = (tuple(sorted(target_floor)), tuple(sorted(target_wall)))
            if target_key in seen_targets:
                continue
            buckets = {pattern: [] for pattern in (*needed_two, needed_one)}
            for candidate in pool:
                if candidate == correct:
                    continue
                verdict = judge(candidate, target_floor, target_wall, wall_rule=wall_rule)
                if verdict["truth"] in buckets:
                    buckets[verdict["truth"]].append(candidate)
            if all(buckets[k] for k in buckets):
                chosen = [rng.choice(buckets[k]) for k in (*needed_two, needed_one)]
                if len(set(chosen)) == 3:
                    found = (correct, chosen, target_floor, target_wall, target_key)
                    break
        if found is None:
            raise RuntimeError(f"无法生成第 {qidx + 1} 题：候选结构不足，未降低判题要求。")

        correct, distractors, target_floor, target_wall, target_key = found
        seen_targets.add(target_key)
        options = [{"matrix": correct, "role": "correct"}]
        for matrix, pattern in zip(distractors, (*needed_two, needed_one)):
            options.append({"matrix": matrix, "role": "distractor", "distractor_type": pattern})
        for option in options:
            option["cube_colors"] = {tuple(block): rng.choice(("红", "黄", "蓝"))
                                      for block in [(x, y, z) for y, row in enumerate(option["matrix"])
                                                    for x, height in enumerate(row) for z in range(height)]}
        rng.shuffle(options)
        answer_letter = answer_slots[qidx]
        for idx, option in enumerate(options):
            option["letter"] = "ABCD"[idx]
            checks = judge(option["matrix"], target_floor, target_wall, wall_rule=wall_rule)
            option.update(checks)
            option["blocks"] = [[x, y, z] for y, row in enumerate(option["matrix"])
                                 for x, height in enumerate(row) for z in range(height)]
            option["is_answer"] = option["role"] == "correct"
            if option["is_answer"]:
                option["distractor_type"] = None
        # Rearrange so the correct answer letters follow the exact 3-per-letter plan.
        correct_option = next(o for o in options if o["is_answer"])
        options.remove(correct_option)
        options.insert("ABCD".index(answer_letter), correct_option)
        for idx, option in enumerate(options):
            option["letter"] = "ABCD"[idx]
        questions.append({"number": qidx + 1, "target_count": 6,
                          "target_floor": [list(p) for p in sorted(target_floor)],
                          "target_wall": [list(p) for p in sorted(target_wall)],
                          "options": options, "answer": answer_letter,
                          "floor_image": f"q{qidx + 1:02d}_floor.png",
                          "wall_image": f"q{qidx + 1:02d}_wall.png",
                          "two_true_types": list(needed_two), "one_true_type": needed_one})
    return questions
