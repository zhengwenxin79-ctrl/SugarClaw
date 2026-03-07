#!/usr/bin/env python3
"""
SugarClaw 食物 GI/GL 向量查询引擎
支持精确名称匹配 + 语义搜索（向量）+ 元数据过滤（结构化查询）
地域感知对冲推荐：根据食物/用户地域推荐当地低GI替代食物

用法:
  python3 query_food.py "热干面"                    # 精确+语义搜索
  python3 query_food.py "旺仔牛奶"                  # 精确名称匹配
  python3 query_food.py "过早吃了个面"               # 模糊语义匹配
  python3 query_food.py "低GI水果" --max 5          # 多结果
  python3 query_food.py "广东早茶" --region 广东     # 地域过滤
  python3 query_food.py --high-gi --max 10          # 列出高GI食物
  python3 query_food.py --counter "肠粉"            # 直接获取对冲方案
  python3 query_food.py "面条" --json               # JSON输出
"""

import argparse
import json
import os
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(SKILL_DIR, "data", "chromadb")
FOODS_PATH = os.path.join(SKILL_DIR, "data", "foods_500.json")
COLLECTION_NAME = "sugarclaw_food_gi"

# 向量搜索距离阈值：超过此值视为不相关
DISTANCE_THRESHOLD = 1.2


def load_foods():
    """加载本地食物数据库用于精确匹配。"""
    with open(FOODS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def exact_match(query, foods, max_results=3):
    """精确名称/别名匹配，返回匹配的食物列表。
    优先级: 完全匹配 > food_name包含查询 > 查询包含food_name(严格) > 别名匹配
    严格匹配规则：
    - 查询词和核心名长度比 >= 0.5 才算匹配（防止"旺仔牛奶"匹配"牛奶"）
    - 查询词比核心名多出的部分不超过2个字（防止品牌名误匹配）
    """
    query_lower = query.lower().strip()
    query_len = len(query_lower)
    scored = []

    for food in foods:
        name = food["food_name"]
        name_lower = name.lower()
        aliases = [a.lower() for a in food.get("aliases", [])]

        # 完全匹配 food_name
        if query_lower == name_lower:
            scored.append((0, food))
            continue

        # 完全匹配某个别名
        if query_lower in aliases:
            scored.append((1, food))
            continue

        # food_name 包含查询词 (如查询"牛奶"匹配"牛奶(全脂)")
        # 查询词必须足够长(>=2字符)才做子串匹配
        if len(query_lower) >= 2 and query_lower in name_lower:
            scored.append((2, food))
            continue

        # 查询词包含 food_name 核心词（严格模式）
        # 例如"红烧牛肉面"包含"牛肉面" → OK (多2字)
        # 但"旺仔牛奶"包含"牛奶" → 拒绝 (多2字但核心名太短，比例不够)
        core_name = name.split("(")[0].split("（")[0].strip().lower()
        if len(core_name) >= 2 and core_name in query_lower:
            extra_chars = query_len - len(core_name)
            ratio = len(core_name) / query_len
            # 核心名占查询词的比例 >= 60%，且多出部分 <= 3字符
            if ratio >= 0.6 and extra_chars <= 3:
                scored.append((3, food))
                continue

        # 别名匹配（同样要求严格）
        for alias in food.get("aliases", []):
            alias_lower = alias.lower()
            if len(alias_lower) < 2:
                continue
            # 查询词精确包含别名，或别名精确包含查询词
            if query_lower == alias_lower:
                scored.append((1, food))
                break
            if alias_lower in query_lower:
                ratio = len(alias_lower) / query_len
                if ratio >= 0.6:
                    scored.append((4, food))
                    break
            if query_lower in alias_lower:
                ratio = query_len / len(alias_lower)
                if ratio >= 0.6:
                    scored.append((4, food))
                    break

    scored.sort(key=lambda x: x[0])
    return [item[1] for item in scored[:max_results]]


def get_collection():
    import chromadb
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        return client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print("[ERROR] 数据库不存在，请先运行: python3 scripts/build_vectordb.py")
        sys.exit(1)


def semantic_search(query, max_results=3, where_filter=None):
    """语义向量搜索，带距离阈值过滤。"""
    collection = get_collection()
    # 多取一些结果，后面按阈值过滤
    fetch_n = max(max_results * 2, 10)
    kwargs = {
        "query_texts": [query],
        "n_results": fetch_n,
        "include": ["documents", "metadatas", "distances"],
    }
    if where_filter:
        kwargs["where"] = where_filter
    results = collection.query(**kwargs)

    if not results["metadatas"] or not results["metadatas"][0]:
        return results

    # 过滤掉距离超过阈值的结果
    filtered_metas = []
    filtered_docs = []
    filtered_dists = []
    for meta, doc, dist in zip(
        results["metadatas"][0],
        results["documents"][0],
        results["distances"][0]
    ):
        if dist <= DISTANCE_THRESHOLD:
            filtered_metas.append(meta)
            filtered_docs.append(doc)
            filtered_dists.append(dist)
        if len(filtered_metas) >= max_results:
            break

    results["metadatas"] = [filtered_metas]
    results["documents"] = [filtered_docs]
    results["distances"] = [filtered_dists]
    return results


def food_to_meta(food):
    """将 foods_500.json 条目转换为与 ChromaDB metadata 兼容的 dict。"""
    macro = food.get("macro", {})
    return {
        "food_name": food["food_name"],
        "gi_value": food["gi_value"],
        "gi_level": food["gi_level"],
        "gl_per_serving": food["gl_per_serving"],
        "serving_size_g": food["serving_size_g"],
        "carb_g": macro.get("carb_g", 0),
        "protein_g": macro.get("protein_g", 0),
        "fat_g": macro.get("fat_g", 0),
        "fiber_g": macro.get("fiber_g", 0),
        "regional_tag": food["regional_tag"],
        "food_category": food["food_category"],
        "counter_strategy": food["counter_strategy"],
        "data_source": food["data_source"],
    }


def get_regional_counters(food_region, food_category, foods, max_suggestions=3):
    """根据食物地域推荐同地域/同分类的低GI对冲食物。
    优先级: 同地域+同分类低GI > 同地域低GI > 相近地域低GI > 全国低GI
    """
    # 地域亲和映射：某些地域间文化饮食相近
    region_affinity = {
        "武汉": ["湖北", "湖南", "江西"],
        "湖北": ["武汉", "湖南", "江西"],
        "湖南": ["湖北", "武汉", "贵州", "江西"],
        "广东": ["广西", "华南", "福建", "海南"],
        "广西": ["广东", "华南", "云南"],
        "福建": ["广东", "华南", "江浙"],
        "四川": ["重庆", "贵州", "云南", "西南"],
        "重庆": ["四川", "贵州", "西南"],
        "贵州": ["四川", "云南", "湖南", "西南"],
        "云南": ["四川", "贵州", "广西", "西南"],
        "江浙": ["上海", "杭州", "浙江", "安徽", "南方"],
        "上海": ["江浙", "杭州", "浙江"],
        "杭州": ["江浙", "上海", "浙江"],
        "浙江": ["江浙", "上海", "杭州"],
        "北京": ["北方", "天津", "河北"],
        "天津": ["北京", "北方", "河北"],
        "东北": ["北方", "内蒙古"],
        "北方": ["北京", "东北", "天津", "河北", "山西"],
        "山西": ["北方", "陕西", "河南"],
        "陕西": ["山西", "甘肃", "西北", "河南"],
        "河南": ["山西", "陕西", "北方", "湖北"],
        "甘肃": ["陕西", "西北", "宁夏", "新疆"],
        "西北": ["陕西", "甘肃", "新疆", "宁夏"],
        "新疆": ["西北", "甘肃"],
        "海南": ["广东", "热带", "华南"],
        "热带": ["海南", "广东", "广西"],
    }

    low_gi_foods = [f for f in foods if f["gi_value"] <= 55]

    candidates = []

    # 1. 同地域+同分类
    for f in low_gi_foods:
        if f["regional_tag"] == food_region and f["food_category"] == food_category:
            candidates.append(("same_region_cat", f))

    # 2. 同地域不同分类
    for f in low_gi_foods:
        if f["regional_tag"] == food_region and f["food_category"] != food_category:
            candidates.append(("same_region", f))

    # 3. 亲和地域
    affinity_regions = region_affinity.get(food_region, [])
    for f in low_gi_foods:
        if f["regional_tag"] in affinity_regions:
            candidates.append(("affinity_region", f))

    # 4. 全国通用 (只在前面不够时补充)
    for f in low_gi_foods:
        if f["regional_tag"] == "全国":
            candidates.append(("national", f))

    # 去重，保持优先级顺序（核心名相同的视为重复，如"臭豆腐"和"臭豆腐(长沙)"）
    seen_cores = set()
    unique = []
    for priority, f in candidates:
        core = f["food_name"].split("(")[0].split("（")[0].strip()
        if core not in seen_cores:
            seen_cores.add(core)
            unique.append((priority, f))

    return unique[:max_suggestions]


def format_result(meta, doc=None, distance=None, regional_counters=None):
    """格式化单条结果。"""
    lines = []
    gi_bar = "█" * (meta["gi_value"] // 10) + "░" * (10 - meta["gi_value"] // 10)
    lines.append(f"  食物: {meta['food_name']}  [{meta['regional_tag']}·{meta['food_category']}]")
    lines.append(f"  GI: {meta['gi_value']} ({meta['gi_level']}GI) {gi_bar}")
    lines.append(f"  GL: {meta['gl_per_serving']} (每份 {meta['serving_size_g']}g)")
    lines.append(
        f"  营养: 碳水{meta['carb_g']}g | 蛋白{meta['protein_g']}g | "
        f"脂肪{meta['fat_g']}g | 纤维{meta['fiber_g']}g"
    )
    lines.append(f"  对冲: {meta['counter_strategy']}")
    lines.append(f"  来源: {meta['data_source']}")
    if distance is not None:
        lines.append(f"  匹配度: {1 - distance:.2%}")

    # 地域感知对冲推荐
    if regional_counters and meta["gi_value"] > 55:
        lines.append(f"  ── 地域对冲推荐 ({meta['regional_tag']}周边低GI替代) ──")
        for priority, counter_food in regional_counters:
            region_label = counter_food["regional_tag"]
            lines.append(
                f"    → {counter_food['food_name']} "
                f"[{region_label}] "
                f"GI={counter_food['gi_value']}({counter_food['gi_level']}) "
                f"GL={counter_food['gl_per_serving']}"
            )

    return "\n".join(lines)


def smart_search(query, max_results=3, where_filter=None):
    """智能搜索: 精确匹配优先，向量搜索兜底。"""
    foods = load_foods()

    # 第一步：精确名称/别名匹配
    exact_results = exact_match(query, foods, max_results)
    if exact_results:
        # 精确命中，构造与 semantic_search 兼容的结果格式
        metas = [food_to_meta(f) for f in exact_results]
        docs = [""] * len(exact_results)
        dists = [0.0] * len(exact_results)
        return {
            "metadatas": [metas],
            "documents": [docs],
            "distances": [dists],
            "_match_type": "exact",
        }

    # 第二步：向量语义搜索（带距离阈值）
    results = semantic_search(query, max_results, where_filter)
    results["_match_type"] = "semantic"
    return results


def main():
    parser = argparse.ArgumentParser(
        description="SugarClaw 食物 GI/GL 向量查询"
    )
    parser.add_argument("query", nargs="?", default=None, help="搜索关键词（支持模糊语义）")
    parser.add_argument("--max", type=int, default=3, help="最大返回条数")
    parser.add_argument("--region", default=None, help="按地域过滤 (如: 广东, 武汉, 北方)")
    parser.add_argument("--category", default=None, help="按分类过滤 (如: 面食, 米制品, 水果)")
    parser.add_argument("--high-gi", action="store_true", help="仅显示高GI食物")
    parser.add_argument("--low-gi", action="store_true", help="仅显示低GI食物")
    parser.add_argument("--counter", default=None, help="直接获取指定食物的对冲方案")
    parser.add_argument("--json", action="store_true", dest="json_out", help="JSON输出")
    args = parser.parse_args()

    foods = load_foods()

    # 构建元数据过滤器(仅用于向量搜索)
    where_filter = None
    conditions = []
    if args.region:
        conditions.append({"regional_tag": args.region})
    if args.category:
        conditions.append({"food_category": args.category})
    if args.high_gi:
        conditions.append({"gi_level": "高"})
    if args.low_gi:
        conditions.append({"gi_level": "低"})

    if len(conditions) == 1:
        where_filter = conditions[0]
    elif len(conditions) > 1:
        where_filter = {"$and": conditions}

    # 对冲方案快查
    if args.counter:
        exact_results = exact_match(args.counter, foods, max_results=1)
        if not exact_results:
            # 回退到向量搜索
            results = semantic_search(args.counter, max_results=1)
            if results["metadatas"] and results["metadatas"][0]:
                meta = results["metadatas"][0][0]
                exact_results = [meta]  # use meta directly
            else:
                print(f"未找到「{args.counter}」的对冲方案")
                return

        if exact_results:
            food = exact_results[0]
            if isinstance(food, dict) and "macro" in food:
                meta = food_to_meta(food)
            else:
                meta = food
            print(f"[{meta['food_name']}] 对冲方案:")
            print(f"  GI={meta['gi_value']}({meta['gi_level']}) GL={meta['gl_per_serving']}")
            print(f"  策略: {meta['counter_strategy']}")

            # 地域对冲推荐
            if meta["gi_value"] > 55:
                counters = get_regional_counters(
                    meta["regional_tag"], meta["food_category"], foods
                )
                if counters:
                    print(f"  ── 地域对冲推荐 ({meta['regional_tag']}周边低GI替代) ──")
                    for priority, cf in counters:
                        print(f"    → {cf['food_name']} [{cf['regional_tag']}] "
                              f"GI={cf['gi_value']} GL={cf['gl_per_serving']}")
        return

    if not args.query:
        if args.high_gi or args.low_gi or args.region or args.category:
            args.query = "食物"
        else:
            parser.print_help()
            return

    results = smart_search(args.query, args.max, where_filter)

    if not results["metadatas"] or not results["metadatas"][0]:
        print(f"未检索到与「{args.query}」匹配的食物。")
        print("建议: 尝试使用常见食物名称或地域标签重新查询。")
        return

    if args.json_out:
        output = []
        for i, meta in enumerate(results["metadatas"][0]):
            entry = dict(meta)
            entry["distance"] = results["distances"][0][i]
            entry["match_score"] = round(1 - results["distances"][0][i], 4)
            entry["match_type"] = results.get("_match_type", "unknown")
            # 附加地域对冲推荐
            if meta["gi_value"] > 55:
                counters = get_regional_counters(
                    meta["regional_tag"], meta["food_category"], foods
                )
                entry["regional_counters"] = [
                    {"food_name": cf["food_name"],
                     "regional_tag": cf["regional_tag"],
                     "gi_value": cf["gi_value"],
                     "gl_per_serving": cf["gl_per_serving"],
                     "food_category": cf["food_category"]}
                    for _, cf in counters
                ]
            output.append(entry)
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    match_type = results.get("_match_type", "semantic")
    type_label = "精确匹配" if match_type == "exact" else "语义搜索"
    print(f"[SugarClaw] 检索到 {len(results['metadatas'][0])} 种匹配食物 ({type_label}):\n")

    for i, (meta, doc, dist) in enumerate(zip(
        results["metadatas"][0],
        results["documents"][0],
        results["distances"][0]
    )):
        # 获取地域对冲推荐
        regional_counters = None
        if meta["gi_value"] > 55:
            regional_counters = get_regional_counters(
                meta["regional_tag"], meta["food_category"], foods
            )

        print(f"{'─' * 50}")
        print(f"[{i+1}]")
        print(format_result(meta, doc, dist if match_type == "semantic" else None,
                            regional_counters))
    print(f"{'─' * 50}")
    print("\n声明: 以上数据仅供参考，个体血糖反应因人而异。")


if __name__ == "__main__":
    main()
