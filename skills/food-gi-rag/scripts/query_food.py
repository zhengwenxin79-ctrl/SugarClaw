#!/usr/bin/env python3
"""
SugarClaw 食物 GI/GL 向量查询引擎
支持语义搜索（向量）+ 元数据过滤（结构化查询）

用法:
  python3 query_food.py "热干面"                    # 语义搜索
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
COLLECTION_NAME = "sugarclaw_food_gi"


def get_collection():
    import chromadb
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        return client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print("[ERROR] 数据库不存在，请先运行: python3 scripts/build_vectordb.py")
        sys.exit(1)


def semantic_search(query, max_results=3, where_filter=None):
    """语义向量搜索。"""
    collection = get_collection()
    kwargs = {
        "query_texts": [query],
        "n_results": max_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where_filter:
        kwargs["where"] = where_filter
    return collection.query(**kwargs)


def format_result(meta, doc, distance=None):
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
    return "\n".join(lines)


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

    # 构建元数据过滤器
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
        results = semantic_search(args.counter, max_results=1)
        if results["metadatas"] and results["metadatas"][0]:
            meta = results["metadatas"][0][0]
            print(f"[{meta['food_name']}] 对冲方案:")
            print(f"  GI={meta['gi_value']}({meta['gi_level']}) GL={meta['gl_per_serving']}")
            print(f"  策略: {meta['counter_strategy']}")
        else:
            print(f"未找到「{args.counter}」的对冲方案")
        return

    if not args.query:
        if args.high_gi or args.low_gi or args.region or args.category:
            # 无查询词但有过滤条件，用通配查询
            args.query = "食物"
        else:
            parser.print_help()
            return

    results = semantic_search(args.query, args.max, where_filter)

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
            output.append(entry)
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    print(f"[SugarClaw] 检索到 {len(results['metadatas'][0])} 种匹配食物:\n")
    for i, (meta, doc, dist) in enumerate(zip(
        results["metadatas"][0],
        results["documents"][0],
        results["distances"][0]
    )):
        print(f"{'─' * 50}")
        print(f"[{i+1}]")
        print(format_result(meta, doc, dist))
    print(f"{'─' * 50}")
    print("\n声明: 以上数据仅供参考，个体血糖反应因人而异。")


if __name__ == "__main__":
    main()
