"""Exact grid geometry, construction, validation, and answers for grid-area worksheets."""
from __future__ import annotations

from collections import deque
from itertools import combinations
import random

LEFT_SIZE = (7, 7)
RIGHT_SIZE = (8, 7)
MARK_CELL = (0, 0)


def cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def triangle_area2(vertices):
    return abs(cross(*vertices))


def bbox(vertices):
    xs, ys = [p[0] for p in vertices], [p[1] for p in vertices]
    return min(xs), min(ys), max(xs), max(ys)


def polygon_area(poly):
    if len(poly) < 3:
        return 0.0
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly))) / 2)


def _clip(subject, clipper):
    """Sutherland-Hodgman clipping of convex polygons; returns their intersection."""
    result = [(float(x), float(y)) for x, y in subject]
    clipper = [(float(x), float(y)) for x, y in clipper]
    signed = sum(clipper[i][0] * clipper[(i + 1) % len(clipper)][1] - clipper[(i + 1) % len(clipper)][0] * clipper[i][1]
                 for i in range(len(clipper)))
    orient = 1 if signed >= 0 else -1
    for i, a in enumerate(clipper):
        b = clipper[(i + 1) % len(clipper)]
        inp, result = result, []
        if not inp:
            break
        def side(p):
            return orient * ((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]))
        prev = inp[-1]
        for cur in inp:
            sp, sc = side(prev), side(cur)
            if sc >= -1e-9:
                if sp < -1e-9:
                    t = sp / (sp - sc)
                    result.append((prev[0] + t * (cur[0] - prev[0]), prev[1] + t * (cur[1] - prev[1])))
                result.append(cur)
            elif sp >= -1e-9:
                t = sp / (sp - sc)
                result.append((prev[0] + t * (cur[0] - prev[0]), prev[1] + t * (cur[1] - prev[1])))
            prev = cur
    return result


def triangles_overlap(a, b):
    return polygon_area(_clip(a, b)) > 1e-8


def triangle_template_ok(v):
    if len(set(v)) != 3 or triangle_area2(v) == 0:
        return False
    x0, y0, x1, y1 = bbox(v)
    w, h = x1 - x0, y1 - y0
    if (w, h) not in {(3, 3), (3, 2), (2, 3), (2, 2)}:
        return False
    corners = {(x0, y0), (x1, y0), (x0, y1), (x1, y1)}
    corner_count = sum(p in corners for p in v)
    edge_interior = any((p[0] in (x0, x1) or p[1] in (y0, y1)) and p not in corners for p in v)
    return 1 <= corner_count <= 2 and edge_interior


def triangle_fits_board(v, width=8, height=7):
    if not triangle_template_ok(v):
        return False
    x0, y0, x1, y1 = bbox(v)
    if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
        return False
    # The pink unit-value cell is fully reserved.
    return polygon_area(_clip(v, [(0, 0), (1, 0), (1, 1), (0, 1)])) < 1e-8


def is_non_rectangular_half_integer(v):
    x0, y0, x1, y1 = bbox(v)
    return triangle_area2(v) % 2 == 1 and triangle_area2(v) != (x1 - x0) * (y1 - y0)


def triangle_candidates(width=8, height=7):
    out = []
    points = [(x, y) for y in range(height + 1) for x in range(width + 1)]
    for tri in combinations(points, 3):
        if triangle_fits_board(tri, width, height):
            out.append(tuple(sorted(tri)))
    return out


def _connected_by_vertices(parts):
    if not parts:
        return False
    seen, todo = {0}, [0]
    while todo:
        i = todo.pop()
        for j, p in enumerate(parts):
            if j not in seen and set(parts[i]["vertices"]) & set(p["vertices"]):
                seen.add(j)
                todo.append(j)
    return len(seen) == len(parts)


def left_area2(parts):
    return sum(2 if p["kind"] == "square" else 1 for p in parts)


def validate_left(parts):
    squares = [p for p in parts if p["kind"] == "square"]
    halves = [p for p in parts if p["kind"] == "half"]
    if not 3 <= len(squares) <= 9 or not 6 <= len(halves) <= 14:
        return False
    occupied = {}
    for p in parts:
        x, y = p["cell"]
        if not (0 <= x < 7 and 0 <= y < 7) or (x, y) == MARK_CELL:
            return False
        if p["kind"] == "half" and p["orientation"] not in range(4):
            return False
        # Every half-cell atom owns its own square cell. Two complementary halves
        # would be one complete square and may not be represented as two pieces.
        if (x, y) in occupied:
            return False
        occupied[(x, y)] = p["kind"]
    if left_area2(parts) % 2:
        return False
    return _connected_by_vertices(parts)


def left_piece_vertices(piece):
    x, y = piece["cell"]
    tl, tr, br, bl = (x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)
    if piece["kind"] == "square":
        return (tl, tr, br, bl)
    return ((tl, tr, br), (tl, tr, bl), (tl, br, bl), (tr, br, bl))[piece["orientation"]]


def _grow_left(rng, square_count, half_count, attempts=1500):
    candidates = [(x, y) for y in range(7) for x in range(7) if (x, y) != MARK_CELL]
    for _ in range(attempts):
        target = square_count + half_count
        first_kind = "square" if rng.random() < square_count / target else "half"
        parts = []
        counts = {"square": 0, "half": 0}
        while len(parts) < target:
            options = []
            for cell in candidates:
                for kind in ("square", "half"):
                    if counts[kind] >= {"square": square_count, "half": half_count}[kind]:
                        continue
                    for ori in (range(1) if kind == "square" else range(4)):
                        cand = {"kind": kind, "cell": cell, "orientation": ori}
                        if any(p["cell"] == cell and p["kind"] == "square" for p in parts):
                            continue
                        if kind == "square" and any(p["cell"] == cell for p in parts):
                            continue
                        if any(p["cell"] == cell for p in parts):
                            continue
                        cand["vertices"] = left_piece_vertices(cand)
                        if not parts or any(set(p["vertices"]) & set(cand["vertices"]) for p in parts):
                            options.append(cand)
            if not options:
                break
            # Favor the type with more remaining pieces while retaining shape variety.
            remaining = {k: lim - counts[k] for k, lim in (("square", square_count), ("half", half_count))}
            weighted = [o for o in options for _ in range(max(1, remaining[o["kind"]]))]
            picked = rng.choice(weighted)
            parts.append(picked)
            counts[picked["kind"]] += 1
        if len(parts) == target and validate_left(parts):
            for p in parts:
                p.pop("vertices", None)
            return parts
    return None


def _grow_right(rng, candidates, attempts=600):
    by_vertex = {}
    for tri in candidates:
        for v in tri:
            by_vertex.setdefault(v, []).append(tri)
    for _ in range(attempts):
        anchor = rng.choice(candidates)
        parts = [anchor]
        while len(parts) < 5:
            opts = []
            vertices = set(v for t in parts for v in t)
            for v in vertices:
                for tri in by_vertex.get(v, ()):
                    if tri in parts or any(triangles_overlap(tri, other) for other in parts):
                        continue
                    opts.append(tri)
            if not opts:
                break
            rng.shuffle(opts)
            parts.append(opts[0])
        if (len(parts) == 5 and sum(triangle_area2(t) for t in parts) % 2 == 0
                and any(is_non_rectangular_half_integer(t) for t in parts)):
            return parts
    return None


def make_question(number, left_unit, rng, right_candidates):
    left = None
    for _ in range(100):
        s, h = rng.randint(3, 9), rng.choice((6, 8, 10, 12, 14))
        left = _grow_left(rng, s, h)
        if left:
            break
    if not left:
        raise RuntimeError("无法构造满足约束的左图")
    right = _grow_right(rng, right_candidates)
    if not right:
        raise RuntimeError("无法构造满足约束的右图")
    left_sum2 = left_area2(left)
    right_sum2 = sum(triangle_area2(t) for t in right)
    return {
        "number": number,
        "prompt": "下面的方格有的一个格子代表1，有的一个格子代表2，根据格子代表的数，请你想一想下面的图案表示几？把答案填在对应的括号里。",
        "left_unit": left_unit, "right_unit": 3 - left_unit,
        "left_board": {"columns": 7, "rows": 7}, "right_board": {"columns": 8, "rows": 7},
        "left": {"pieces": left, "squares": sum(p["kind"] == "square" for p in left),
                 "half_triangles": sum(p["kind"] == "half" for p in left), "area2": left_sum2,
                 "equivalent_cells": left_sum2 / 2, "answer": left_sum2 // 2 * left_unit},
        "right": {"triangles": [list(t) for t in right], "triangle_area2": [triangle_area2(t) for t in right],
                  "area2": right_sum2, "equivalent_cells": right_sum2 / 2, "answer": right_sum2 // 2 * (3 - left_unit)},
    }


def generate_questions(count=12, seed=20261014):
    rng = random.Random(seed)
    configs = [1] * ((count + 1) // 2) + [2] * (count // 2)
    rng.shuffle(configs)
    candidates = triangle_candidates()
    questions, seen = [], set()
    tries = 0
    while len(questions) < count and tries < count * 500:
        tries += 1
        q = make_question(len(questions) + 1, configs[len(questions)], rng, candidates)
        # Compare geometry up to translation, rotation, and reflection; left/right roles stay fixed.
        key = (normalized_signature([left_piece_vertices(p) for p in q["left"]["pieces"]]),
               normalized_signature([tuple(map(tuple, t)) for t in q["right"]["triangles"]]))
        if key in seen:
            continue
        seen.add(key)
        questions.append(q)
    if len(questions) != count:
        raise RuntimeError(f"尝试 {tries} 次后仅生成 {len(questions)}/{count} 道合格题")
    return questions


def normalized_signature(polygons):
    transforms = (lambda x, y: (x, y), lambda x, y: (-y, x), lambda x, y: (-x, -y),
                  lambda x, y: (y, -x), lambda x, y: (-x, y), lambda x, y: (x, -y),
                  lambda x, y: (y, x), lambda x, y: (-y, -x))
    choices = []
    for transform in transforms:
        transformed = [[transform(*v) for v in poly] for poly in polygons]
        minx = min(v[0] for p in transformed for v in p)
        miny = min(v[1] for p in transformed for v in p)
        choices.append(tuple(sorted(tuple(sorted((x - minx, y - miny) for x, y in p)) for p in transformed)))
    return min(choices)


def validate_question(q):
    left = q["left"]
    assert validate_left([{**p, "vertices": left_piece_vertices(p)} for p in left["pieces"]])
    assert left["area2"] == left_area2(left["pieces"])
    assert left["answer"] * 2 == left["area2"] * q["left_unit"]
    tris = [tuple(map(tuple, t)) for t in q["right"]["triangles"]]
    assert len(tris) == 5 and all(triangle_fits_board(t) for t in tris)
    assert all(not triangles_overlap(a, b) for a, b in combinations(tris, 2))
    assert sum(triangle_area2(t) for t in tris) % 2 == 0
    assert any(is_non_rectangular_half_integer(t) for t in tris)
    parts = [{"vertices": t} for t in tris]
    assert _connected_by_vertices(parts)
    right = q["right"]
    assert right["area2"] == sum(map(triangle_area2, tris))
    assert right["answer"] * 2 == right["area2"] * q["right_unit"]
    assert q["left_unit"] + q["right_unit"] == 3
    return True
