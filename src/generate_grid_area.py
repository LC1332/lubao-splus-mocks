#!/usr/bin/env python3
"""Generate grid-area and unit-conversion questions, figures, data, and a Word worksheet."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from grid_area_logic import bbox, generate_questions, left_piece_vertices, validate_question
from grid_area_render import create_docx, draw_board


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=12, help="题目数量，默认 12")
    parser.add_argument("--seed", type=int, default=20261014, help="固定随机种子，默认 20261014")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "generated", help="输出目录，默认 generated")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count 必须大于 0")

    questions = generate_questions(args.count, args.seed)
    for q in questions:
        validate_question(q)
        left_parts = q["left"]["pieces"]
        left_vertices = [set(left_piece_vertices(p)) for p in left_parts]
        q["left"]["connections"] = [[i + 1, j + 1] for i in range(len(left_parts)) for j in range(i + 1, len(left_parts)) if left_vertices[i] & left_vertices[j]]
        right_tris = [tuple(map(tuple, tri)) for tri in q["right"]["triangles"]]
        q["right"]["triangle_bboxes"] = [list(bbox(tri)) for tri in right_tris]
        q["right"]["triangle_areas"] = [{"area2": a, "equivalent_cells": a / 2} for a in q["right"]["triangle_area2"]]
        q["right"]["connections"] = [[i + 1, j + 1] for i in range(len(right_tris)) for j in range(i + 1, len(right_tris)) if set(right_tris[i]) & set(right_tris[j])]
        q["validation"] = {"passed": True, "checks": ["piece_count", "exact_area", "unit_conversion", "connected", "no_overlap", "reserved_marker"]}
        q["left"]["colors"] = {"figure": "yellow", "unit_marker": "pink"}
        q["right"]["colors"] = {"triangles_1_to_4": "teal", "triangle_5": "orange", "unit_marker": "pink"}

    output_dir = args.output_dir.expanduser().resolve()
    assets_dir = output_dir / "方格面积与单位换算素材"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for q in questions:
        draw_board(q, "left", assets_dir / f"q{q['number']:02d}_left.png")
        draw_board(q, "right", assets_dir / f"q{q['number']:02d}_right.png")

    docx_path = output_dir / "大班数学方格面积与单位换算练习.docx"
    create_docx(questions, assets_dir, docx_path)
    units = {"left_1_right_2": sum(q["left_unit"] == 1 for q in questions),
             "left_2_right_1": sum(q["left_unit"] == 2 for q in questions)}
    data = {"generator_version": "1.0.0", "seed": args.seed, "created_utc": datetime.now(timezone.utc).isoformat(),
            "configuration": {"count": args.count, "left_board": [7, 7], "right_board": [8, 7], "unit_configuration_counts": units},
            "files": {"worksheet": docx_path.name, "assets_directory": assets_dir.name}, "questions": questions}
    data_path = assets_dir / "题目数据与答案.json"
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成 Word：{docx_path}")
    print(f"题目数：{len(questions)}；单位配置：左1右2 {units['left_1_right_2']} 道，左2右1 {units['left_2_right_1']} 道")
    print(f"题图与数据：{assets_dir}")


if __name__ == "__main__":
    main()
