#!/usr/bin/env python3
"""Generate a reproducible 4x4 adjacent-number Sudoku worksheet and answer key."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from adjacent_sudoku_logic import make_questions, validate_question  # noqa: E402
from adjacent_sudoku_render import draw_board, make_docx  # noqa: E402


def build(count: int, seed: int, output_dir: Path) -> Path:
    output_dir = output_dir.expanduser().resolve()
    assets = output_dir / "4×4数独与相邻数素材"
    assets.mkdir(parents=True, exist_ok=True)
    questions = make_questions(count, seed)
    seen = set()
    for question in questions:
        if not validate_question(question):
            raise RuntimeError(f"第 {question['number']} 题最终复核失败。")
        if question["puzzle_key"] in seen:
            raise RuntimeError("发现重复题面，已停止输出。")
        seen.add(question["puzzle_key"])
        draw_board(question, assets / f"q{question['number']:02d}.png")
        draw_board(question, assets / f"q{question['number']:02d}_answer.png", answer=True)
        question["given"] = {"row": question["given"]["row"] + 1,
                              "column": question["given"]["column"] + 1,
                              "value": question["given"]["value"]}
        question["left_right_red"] = [list(row) for row in question["left_right_red"]]
        question["up_down_red"] = [list(row) for row in question["up_down_red"]]
        question["solution"] = [list(row) for row in question["solution"]]
        question["puzzle_key"] = {"left_right_red": question["left_right_red"],
                                  "up_down_red": question["up_down_red"],
                                  "given": question["given"]}
        question["unique_solution_verified"] = True
        question["question_image"] = f"q{question['number']:02d}.png"
        question["answer_image"] = f"q{question['number']:02d}_answer.png"
    payload = {"generation_version": "1.0", "seed": seed,
               "configuration": {"count": count, "board_size": "4x4", "symbols": [1, 2, 3, 4],
                                  "given_count": 1, "given_value": 2, "independent_category_probability": 0.5,
                                  "questions_per_page": 2},
               "questions": questions}
    (assets / "题目数据与答案.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    docx = output_dir / "大班数学4×4数独与相邻数练习.docx"
    make_docx(questions, assets, docx)
    return docx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=12, help="题目数量（1 至 12），默认 12")
    parser.add_argument("--seed", type=int, default=20261014, help="固定随机种子，默认 20261014")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "generated", help="输出目录")
    args = parser.parse_args()
    if not 1 <= args.count <= 12:
        parser.error("--count 必须为 1 至 12")
    try:
        result = build(args.count, args.seed, args.output_dir)
    except RuntimeError as exc:
        parser.error(str(exc))
    print(f"已生成：{result}")
    print(f"题目：{args.count} 道；随机种子：{args.seed}；每页 2 题；答案附于卷末。")


if __name__ == "__main__":
    main()
