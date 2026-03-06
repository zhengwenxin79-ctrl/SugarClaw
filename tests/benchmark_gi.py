#!/usr/bin/env python3
"""
SugarClaw GI 值准确性基准测试
将 SugarClaw 的 501 种中国食物 GI 值与 International Tables 2021 金标准进行交叉验证。

评估指标:
  - 命中率: SugarClaw 食物在金标准中能匹配到的比例
  - GI 等级一致率: Low/Medium/High 分级的一致性
  - 平均绝对偏差: |SugarClaw GI - 金标准 GI|
  - 分类别偏差分析

用法:
  python3 tests/benchmark_gi.py
"""
import json
import os
import re
import sys
from datetime import datetime

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUGARCLAW_FOODS = os.path.join(WORKSPACE, "skills", "food-gi-rag", "data", "foods_500.json")
GOLD_STANDARD = os.path.join(WORKSPACE, "tests", "benchmark_data", "gi_tables_2021.json")

# 中文食物名 → 英文关键词映射 (用于交叉匹配)
FOOD_MAPPING = {
    # 米饭类
    "白米饭": ["white rice", "rice, white", "jasmine rice"],
    "糙米饭": ["brown rice", "rice, brown"],
    "糯米饭": ["glutinous rice", "sticky rice"],
    "红米饭": ["red rice"],
    "黑米饭": ["black rice"],
    "小米粥": ["millet"],
    "燕麦粥": ["oat", "oatmeal", "porridge"],
    "白粥": ["rice porridge", "congee", "rice gruel"],
    "皮蛋瘦肉粥": ["rice porridge", "congee"],
    "八宝粥": ["mixed grain porridge"],
    # 面食
    "白面条": ["noodles", "wheat noodles"],
    "全麦面条": ["whole wheat noodles", "wholemeal noodles"],
    "荞麦面": ["buckwheat noodles", "soba"],
    "米粉": ["rice noodles", "rice vermicelli"],
    "意大利面": ["spaghetti", "pasta", "macaroni"],
    "通心粉": ["macaroni"],
    "乌冬面": ["udon"],
    "方便面": ["instant noodles"],
    # 面包
    "白面包": ["white bread", "bread, white"],
    "全麦面包": ["whole wheat bread", "wholemeal bread", "whole grain bread"],
    "黑麦面包": ["rye bread"],
    "法棍面包": ["baguette", "french bread"],
    "馒头": ["steamed bread", "mantou", "chinese steamed"],
    "花卷": ["steamed roll"],
    "包子": ["steamed bun", "baozi"],
    # 薯类
    "土豆": ["potato", "potatoes"],
    "红薯": ["sweet potato"],
    "紫薯": ["purple sweet potato"],
    "山药": ["yam", "chinese yam"],
    "芋头": ["taro"],
    # 豆类
    "红豆": ["red bean", "adzuki"],
    "绿豆": ["mung bean", "green bean"],
    "黄豆": ["soybean", "soy bean"],
    "黑豆": ["black bean", "black soybean"],
    "豆腐": ["tofu"],
    "豆浆": ["soy milk", "soymilk"],
    # 水果
    "苹果": ["apple"],
    "香蕉": ["banana"],
    "橙子": ["orange"],
    "葡萄": ["grape"],
    "西瓜": ["watermelon"],
    "芒果": ["mango"],
    "菠萝": ["pineapple"],
    "木瓜": ["papaya"],
    "草莓": ["strawberry"],
    "蓝莓": ["blueberry"],
    "猕猴桃": ["kiwi", "kiwifruit"],
    "柚子": ["grapefruit", "pomelo"],
    "荔枝": ["lychee", "litchi"],
    "龙眼": ["longan"],
    "柿子": ["persimmon"],
    "枣": ["date", "jujube"],
    "桃子": ["peach"],
    "梨": ["pear"],
    "樱桃": ["cherry"],
    "李子": ["plum"],
    # 蔬菜
    "胡萝卜": ["carrot"],
    "南瓜": ["pumpkin"],
    "玉米": ["corn", "maize", "sweet corn"],
    "豌豆": ["pea", "green peas"],
    # 甜品/零食
    "蜂蜜": ["honey"],
    "白砂糖": ["sugar", "sucrose", "table sugar"],
    "果糖": ["fructose"],
    "葡萄糖": ["glucose powder", "dextrose powder"],
    "巧克力": ["chocolate"],
    "冰淇淋": ["ice cream"],
    "饼干": ["biscuit", "cookie", "cracker"],
    "蛋糕": ["cake"],
    # 饮品
    "可乐": ["coca-cola", "cola", "pepsi"],
    "橙汁": ["orange juice"],
    "苹果汁": ["apple juice"],
    "牛奶": ["milk", "full-fat milk", "whole milk"],
    "酸奶": ["yogurt", "yoghurt"],
    # 坚果
    "花生": ["peanut"],
    "核桃": ["walnut"],
    "杏仁": ["almond"],
    "腰果": ["cashew"],
}


def load_sugarclaw():
    with open(SUGARCLAW_FOODS, "r", encoding="utf-8") as f:
        return json.load(f)


def load_gold_standard():
    with open(GOLD_STANDARD, "r", encoding="utf-8") as f:
        return json.load(f)


def find_match(chinese_name, aliases, gold_foods):
    """Find the best matching food in gold standard."""
    # Get English keywords for this food
    keywords = []
    for cn_key, en_keys in FOOD_MAPPING.items():
        if cn_key in chinese_name or any(cn_key in a for a in aliases):
            keywords.extend(en_keys)

    if not keywords:
        return None

    best_match = None
    best_score = 0

    for gold in gold_foods:
        gold_name = gold["food_name"].lower()
        for kw in keywords:
            kw_lower = kw.lower()
            # Exact substring match
            if kw_lower in gold_name:
                score = len(kw_lower) / len(gold_name)  # prefer closer matches
                if score > best_score:
                    best_score = score
                    best_match = gold

    return best_match


def gi_level(gi):
    if gi <= 55:
        return "Low"
    elif gi <= 69:
        return "Medium"
    else:
        return "High"


def normalize_level(level_str):
    """Normalize GI level to English: Low/Medium/High."""
    mapping = {"低": "Low", "中": "Medium", "高": "High"}
    return mapping.get(level_str, level_str)


def main():
    print("=" * 60)
    print("  SugarClaw GI Accuracy Benchmark")
    print("  Gold Standard: International Tables of GI/GL 2021")
    print("  (Atkinson et al., Am J Clin Nutr, 2021)")
    print("=" * 60)

    sc_foods = load_sugarclaw()
    gold_foods = load_gold_standard()

    print(f"\n  SugarClaw foods: {len(sc_foods)}")
    print(f"  Gold standard foods: {len(gold_foods)}")

    # Cross-match
    matched = []
    unmatched = []

    for food in sc_foods:
        name = food["food_name"]
        aliases = food.get("aliases", [])
        gold = find_match(name, aliases, gold_foods)

        if gold:
            matched.append({
                "sc_name": name,
                "sc_gi": food["gi_value"],
                "sc_level": normalize_level(food.get("gi_level", gi_level(food["gi_value"]))),
                "gold_name": gold["food_name"],
                "gold_gi": gold["gi_value"],
                "gold_level": gold["gi_level"],
                "gold_country": gold.get("country", "N/A"),
                "abs_diff": abs(food["gi_value"] - gold["gi_value"]),
                "category": food.get("food_category", "N/A"),
            })
        else:
            unmatched.append(name)

    print(f"\n  Matched: {len(matched)} / {len(sc_foods)} ({len(matched)/len(sc_foods)*100:.1f}%)")
    print(f"  Unmatched: {len(unmatched)}")

    if not matched:
        print("  [ERROR] No matches found. Check food mapping.")
        sys.exit(1)

    # Metrics
    total_diff = sum(m["abs_diff"] for m in matched)
    avg_diff = total_diff / len(matched)
    max_diff = max(m["abs_diff"] for m in matched)

    level_match = sum(1 for m in matched if m["sc_level"] == m["gold_level"])
    level_accuracy = level_match / len(matched) * 100

    within_5 = sum(1 for m in matched if m["abs_diff"] <= 5)
    within_10 = sum(1 for m in matched if m["abs_diff"] <= 10)
    within_15 = sum(1 for m in matched if m["abs_diff"] <= 15)

    print(f"\n  --- GI Value Accuracy ---")
    print(f"  Mean absolute difference: {avg_diff:.1f} GI points")
    print(f"  Max absolute difference:  {max_diff} GI points")
    print(f"  Within ±5 GI points:  {within_5}/{len(matched)} ({within_5/len(matched)*100:.1f}%)")
    print(f"  Within ±10 GI points: {within_10}/{len(matched)} ({within_10/len(matched)*100:.1f}%)")
    print(f"  Within ±15 GI points: {within_15}/{len(matched)} ({within_15/len(matched)*100:.1f}%)")

    print(f"\n  --- GI Level Accuracy (Low/Medium/High) ---")
    print(f"  Level match: {level_match}/{len(matched)} ({level_accuracy:.1f}%)")

    # Confusion matrix
    levels = ["Low", "Medium", "High"]
    header_label = "SugarClaw \\ Gold"
    print(f"\n  {header_label:<18} {'Low':>8} {'Medium':>8} {'High':>8}")
    print(f"  {'-'*18} {'-'*8} {'-'*8} {'-'*8}")
    for sc_lev in levels:
        row = []
        for g_lev in levels:
            count = sum(1 for m in matched if m["sc_level"] == sc_lev and m["gold_level"] == g_lev)
            row.append(count)
        cn_level = {"Low": "低", "Medium": "中", "High": "高"}[sc_lev]
        print(f"  {sc_lev} ({cn_level}GI){' '*(12-len(sc_lev))} {row[0]:>8} {row[1]:>8} {row[2]:>8}")

    # Per-category analysis
    cat_stats = {}
    for m in matched:
        cat = m["category"]
        if cat not in cat_stats:
            cat_stats[cat] = {"diffs": [], "level_matches": 0, "count": 0}
        cat_stats[cat]["diffs"].append(m["abs_diff"])
        cat_stats[cat]["count"] += 1
        if m["sc_level"] == m["gold_level"]:
            cat_stats[cat]["level_matches"] += 1

    print(f"\n  --- Per-Category Analysis ---")
    print(f"  {'Category':<15} {'N':>4} {'Avg Diff':>10} {'Level Match':>12}")
    print(f"  {'-'*15} {'-'*4} {'-'*10} {'-'*12}")
    for cat, stats in sorted(cat_stats.items(), key=lambda x: -x[1]["count"]):
        avg = sum(stats["diffs"]) / len(stats["diffs"])
        lm = stats["level_matches"] / stats["count"] * 100
        print(f"  {cat:<15} {stats['count']:>4} {avg:>10.1f} {lm:>11.1f}%")

    # Show largest discrepancies
    matched.sort(key=lambda x: -x["abs_diff"])
    print(f"\n  --- Top 10 Largest Discrepancies ---")
    print(f"  {'SugarClaw Food':<20} {'SC GI':>6} {'Gold Food':<30} {'Gold GI':>8} {'Diff':>6}")
    for m in matched[:10]:
        print(f"  {m['sc_name'][:20]:<20} {m['sc_gi']:>6} {m['gold_name'][:30]:<30} {m['gold_gi']:>8} {m['abs_diff']:>6}")

    # Save results
    output_path = os.path.join(WORKSPACE, "tests", "benchmark_data", "gi_benchmark_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "sugarclaw_foods": len(sc_foods),
            "gold_standard_foods": len(gold_foods),
            "matched": len(matched),
            "metrics": {
                "mean_abs_diff": round(avg_diff, 1),
                "max_abs_diff": max_diff,
                "within_5": within_5,
                "within_10": within_10,
                "within_15": within_15,
                "level_accuracy_pct": round(level_accuracy, 1),
            },
            "details": matched,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  Results saved to {output_path}")


if __name__ == "__main__":
    main()
