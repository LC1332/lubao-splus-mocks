"""Data generation and strict validation for food-pairing worksheets."""
from __future__ import annotations

from collections import Counter
import random


SCENARIOS = [
    ("下午茶", "饮料", "杯", "蛋糕", "块"),
    ("早餐", "饮品", "杯", "面包", "个"),
    ("野餐", "果汁", "瓶", "三明治", "份"),
    ("点心时间", "酸奶", "杯", "松饼", "个"),
    ("午餐", "主食", "份", "小菜", "碟"),
    ("运动后", "饮品", "瓶", "能量点心", "份"),
    ("生日聚会", "饮料", "杯", "甜点", "块"),
    ("郊游", "水果盒", "盒", "烘焙点心", "个"),
]

VARIANTS = {
    "饮料": ["橙汁", "苹果汁", "葡萄汁", "柠檬水", "草莓奶昔", "芒果奶昔"],
    "饮品": ["豆浆", "牛奶", "燕麦饮", "可可饮", "草莓酸奶", "蓝莓酸奶"],
    "果汁": ["橙子果汁", "葡萄果汁", "桃子果汁", "苹果果汁", "芒果果汁"],
    "酸奶": ["原味酸奶", "草莓酸奶", "蓝莓酸奶", "芒果酸奶", "桃子酸奶"],
    "主食": ["饭团", "鸡蛋饼", "玉米卷", "蔬菜卷", "芝士卷"],
    "小菜": ["玉米杯", "水果沙拉", "土豆泥", "蔬菜杯", "番茄沙拉"],
    "瓶": ["柠檬饮", "葡萄饮", "苹果饮", "桃子饮", "橙子饮"],
    "生日饮料": ["草莓饮", "橙子饮", "葡萄饮", "蓝莓饮", "蜜桃饮"],
    "甜点": ["巧克力蛋糕", "草莓蛋糕", "香草蛋糕", "柠檬蛋糕", "蓝莓蛋糕"],
    "蛋糕": ["草莓蛋糕", "巧克力蛋糕", "奶油蛋糕", "蓝莓蛋糕", "柠檬蛋糕", "香草蛋糕"],
    "面包": ["牛角包", "吐司卷", "豆沙包", "奶酪包", "全麦面包", "小餐包"],
    "三明治": ["鸡蛋三明治", "火腿三明治", "蔬菜三明治", "芝士三明治", "鸡肉三明治"],
    "松饼": ["蓝莓松饼", "香蕉松饼", "巧克力松饼", "原味松饼", "草莓松饼"],
    "能量点心": ["燕麦棒", "坚果饼", "芝麻卷", "谷物球", "果仁脆"],
    "烘焙点心": ["苹果派", "蛋挞", "蝴蝶酥", "小饼干", "莓果派"],
    "水果盒": ["苹果盒", "葡萄盒", "莓果盒", "橙子盒", "桃子盒"],
}


def enumerate_pairings(group_a: list[dict], group_b: list[dict]) -> list[dict]:
    """Keep product identity and multiplicity while enumerating every choice."""
    return [
        {"item_a_id": a["id"], "item_a": a["name"], "price_a": a["price"],
         "item_b_id": b["id"], "item_b": b["name"], "price_b": b["price"],
         "total": a["price"] + b["price"]}
        for a in group_a for b in group_b
    ]


def equal_difference_witness(group_a: list[dict], group_b: list[dict]) -> dict | None:
    for group_x, group_y, name_x, name_y in ((group_a, group_b, "a", "b"), (group_b, group_a, "b", "a")):
        unique_x = {x["price"]: x for x in group_x}
        unique_y = {x["price"]: x for x in group_y}
        for x0 in sorted(unique_x):
            for x1 in sorted(unique_x):
                if x0 >= x1:
                    continue
                for y0 in sorted(unique_y):
                    y1 = y0 + x1 - x0
                    if y1 in unique_y:
                        return {
                            "group_x": name_x, "group_y": name_y,
                            "x_low_id": unique_x[x0]["id"], "x_low_price": x0,
                            "x_high_id": unique_x[x1]["id"], "x_high_price": x1,
                            "y_low_id": unique_y[y0]["id"], "y_low_price": y0,
                            "y_high_id": unique_y[y1]["id"], "y_high_price": y1,
                            "difference": x1 - x0,
                            "equal_total": x1 + y0,
                        }
    return None


def validate_question(q: dict) -> dict:
    a, b = q["group_a"]["items"], q["group_b"]["items"]
    duplicate_group = q["duplicate_group"]
    duplicated = a if duplicate_group == "a" else b
    other = b if duplicate_group == "a" else a
    pairs = enumerate_pairings(a, b)
    totals = sorted({p["total"] for p in pairs})
    prices_dup, prices_other = Counter(x["price"] for x in duplicated), Counter(x["price"] for x in other)
    diff_witness = equal_difference_witness(a, b)
    dup_ids = next((ids for price in prices_dup for ids in [[x["id"] for x in duplicated if x["price"] == price]] if len(ids) >= 2), [])
    checks = {
        "exactly_two_groups": len((q["group_a"], q["group_b"])) == 2,
        "group_sizes": len(duplicated) >= 4 and len(other) >= 3,
        "duplicate_price_products": bool(dup_ids) and len({i for i in dup_ids}) >= 2,
        "other_group_has_distinct_prices": len(prices_other) >= 2,
        "all_prices_two_digit_integers": all(type(x["price"]) is int and 10 <= x["price"] <= 49 for x in a + b),
        "totals_two_digits": all(10 <= t <= 98 for t in totals),
        "nonzero_equal_difference": bool(diff_witness and diff_witness["difference"] > 0),
        "distinct_total_count_range": 1 <= len(totals) <= 10,
        "all_pairings_enumerated": len(pairs) == len(a) * len(b),
    }
    return {"valid": all(checks.values()), "checks": checks, "pairings": pairs,
            "distinct_totals": totals, "answer": len(totals),
            "duplicate_price_witness": ({"group": duplicate_group, "price": next(p for p, n in prices_dup.items() if n >= 2),
                                         "item_ids": dup_ids[:2]} if dup_ids else None),
            "equal_difference_witness": diff_witness,
            "product_pairing_count": len(pairs),
            "distinct_unit_price_pair_count": len(set(x["price"] for x in a)) * len(set(x["price"] for x in b))}


def dedup_key(prices_a: list[int], prices_b: list[int]) -> tuple:
    x, y = tuple(sorted(prices_a)), tuple(sorted(prices_b))
    return tuple(sorted((x, y)))


def _candidate(rng: random.Random, number: int) -> dict:
    # Vary both size combinations and which food category carries the repeated price.
    size_a, size_b = rng.choice([(4, 3), (5, 3), (4, 4), (5, 4)])
    duplicate_group = rng.choice(("a", "b"))
    required_size = size_a if duplicate_group == "a" else size_b
    other_size = size_b if duplicate_group == "a" else size_a
    repeated = rng.randint(10, 39)
    dup_prices = [repeated, repeated]
    while len(dup_prices) < required_size:
        price = rng.randint(10, 49)
        if price not in dup_prices:
            dup_prices.append(price)
    other_prices = rng.sample(range(10, 50), other_size)
    if duplicate_group == "a":
        prices_a, prices_b = dup_prices, other_prices
    else:
        prices_a, prices_b = other_prices, dup_prices

    def group(items, prices, prefix):
        return {"category": items[0], "unit": items[1],
                "items": [{"id": f"q{number:02d}_{prefix}{i+1}", "name": name, "price": price,
                           "asset_id": f"food_{i % 8}"}
                          for i, (name, price) in enumerate(zip(items[2], prices))]}

    scenario = rng.choice(SCENARIOS)
    ca, ua, cb, ub = scenario[1:]
    names_a = rng.sample(VARIANTS.get(ca, [ca + "A", ca + "B", ca + "C", ca + "D", ca + "E"]), size_a)
    names_b = rng.sample(VARIANTS.get(cb, [cb + "A", cb + "B", cb + "C", cb + "D", cb + "E"]), size_b)
    q = {"scenario": scenario[0], "group_a": group((ca, ua, names_a), prices_a, "a"),
         "group_b": group((cb, ub, names_b), prices_b, "b"), "duplicate_group": duplicate_group}
    report = validate_question(q)
    if not report["valid"]:
        return q
    q.update(report)
    q["dedup_key"] = dedup_key(prices_a, prices_b)
    return q


def make_questions(count: int = 12, total_price_count: int = 3, seed: int = 20261014) -> list[dict]:
    if count != 12 or total_price_count != 3:
        raise ValueError("本练习卷固定为 12 题，其中 3 题询问不同总价。")
    rng = random.Random(seed)
    found: dict[tuple, dict] = {}
    for _ in range(250_000):
        q = _candidate(rng, len(found) + 1)
        if q.get("valid"):
            found.setdefault(q["dedup_key"], q)
            if len(found) == count:
                break
    if len(found) != count:
        raise RuntimeError(f"达到 250000 次尝试，仅生成 {len(found)} 道不同合格题；未输出不完整练习卷。")
    questions = list(found.values())
    rng.shuffle(questions)
    total_prompt_numbers = {4, 8, 12}
    for i, q in enumerate(questions, 1):
        q["number"] = i
        for group_key in ("group_a", "group_b"):
            for j, item in enumerate(q[group_key]["items"], 1):
                item["id"] = f"q{i:02d}_{group_key[-1]}{j}"
                item["asset_id"] = f"q{i:02d}_{group_key[-1]}{j}_illustration"
        report = validate_question(q)
        if not report["valid"]:
            raise RuntimeError(f"第 {i} 题在最终编号后校验失败。")
        q.update(report)
        q["question_type"] = "distinct_totals" if i in total_prompt_numbers else "priced_pairings"
        ga, gb = q["group_a"], q["group_b"]
        if q["question_type"] == "distinct_totals":
            ending = "一共有多少种不同的总价？"
        else:
            ending = "有多少种不同价格的搭配方法呢？"
        q["prompt"] = (f"请你搭配{q['scenario']}，每次选一{ga['unit']}{ga['category']}搭配一{gb['unit']}{gb['category']}，"
                       f"{ending}把答案填在括号里。")
        # Candidate identity is independent of names, image identities, order, and wording.
        q["dedup_key"] = [list(q["dedup_key"][0]), list(q["dedup_key"][1])]
        q["group_sizes"] = {"a": len(ga["items"]), "b": len(gb["items"])}
    return questions
