#!/usr/bin/env python3
"""Generate a 12-question food pairing worksheet with distinct-total answers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from food_pairings_logic import make_questions, validate_question
from food_pairings_render import draw_question, make_docx


def build(count: int = 12, total_price_count: int = 3, seed: int = 20261014,
          output_dir: Path = ROOT / "generated") -> tuple[Path, Path]:
    output_dir = output_dir.expanduser().resolve()
    assets = output_dir / "食物搭配素材"
    questions = make_questions(count, total_price_count, seed)
    summaries = [validate_question(q) for q in questions]
    if len(questions) != 12 or sum(q["question_type"] == "distinct_totals" for q in questions) != 3:
        raise RuntimeError("整卷题数或问法配额校验失败。")
    if len({tuple(tuple(s) for s in q["dedup_key"]) for q in questions}) != 12:
        raise RuntimeError("发现重复的数学题目数据。")
    if len({(q["group_sizes"]["a"], q["group_sizes"]["b"]) for q in questions}) < 2:
        raise RuntimeError("题目数量组合变化不足。")
    if not all(s["valid"] and s["answer"] == q["answer"] for s, q in zip(summaries, questions)):
        raise RuntimeError("最终数据独立复算未通过。")
    all_sums = [p["total"] for q in questions for p in q["pairings"]]
    carries = any((p["price_a"] % 10) + (p["price_b"] % 10) >= 10 for q in questions for p in q["pairings"])
    noncarries = any((p["price_a"] % 10) + (p["price_b"] % 10) < 10 for q in questions for p in q["pairings"])
    if not (carries and noncarries):
        raise RuntimeError("整卷需同时覆盖进位与不进位加法。")

    for q in questions:
        draw_question(q, assets / f"q{q['number']:02d}.png")
    payload = {
        "generation_version": "1.0",
        "seed": seed,
        "configuration": {"count": count, "total_price_count": total_price_count,
                          "questions_per_page": 2, "max_attempts": 250000,
                          "price_range": [10, 49], "distinct_total_limit": 10,
                          "carry_coverage": {"carry": carries, "no_carry": noncarries}},
        "asset_manifest": [
            {"asset_id": item["asset_id"], "image_file": f"q{q['number']:02d}.png",
             "group": group_key, "position": index + 1}
            for q in questions
            for group_key in ("group_a", "group_b")
            for index, item in enumerate(q[group_key]["items"])
        ],
        "questions": questions,
        "verification": {"valid": True, "all_answers_independently_recomputed": True,
                         "question_count": 12, "distinct_total_questions": 3,
                         "distinct_size_combinations": len({(q['group_sizes']['a'], q['group_sizes']['b']) for q in questions}),
                         "min_distinct_totals": min(q["answer"] for q in questions),
                         "max_distinct_totals": max(q["answer"] for q in questions),
                         "all_pairings_count": sum(len(q["pairings"]) for q in questions),
                         "all_sum_values_two_digit": all(10 <= s <= 98 for s in all_sums)},
    }
    data_path = assets / "题目数据与答案.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    docx_path = output_dir / "大班数学食物搭配练习.docx"
    make_docx(questions, assets, docx_path)
    return docx_path, data_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=12, help="固定为 12 题")
    parser.add_argument("--total-price-count", type=int, default=3, help="明确询问不同总价的题数，固定为 3")
    parser.add_argument("--seed", type=int, default=20261014, help="复现随机种子")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "generated", help="输出目录")
    args = parser.parse_args()
    try:
        docx, data = build(args.count, args.total_price_count, args.seed, args.output_dir)
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print(f"已生成：{docx}")
    print(f"题目数据：{data}")
    print(f"题数：12；明确询问不同总价：3；随机种子：{args.seed}")


if __name__ == "__main__":
    main()
