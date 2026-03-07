#!/usr/bin/env python3
"""
SugarClaw GI/GL 向量数据库构建器
将 seed_foods.json 导入 ChromaDB，使用 ChromaDB 内置 Embedding。
数据库持久化到 ~/.openclaw/workspace/skills/food-gi-rag/data/chromadb/

用法:
  python3 build_vectordb.py                    # 构建/重建数据库
  python3 build_vectordb.py --append extra.json # 追加新数据
  python3 build_vectordb.py --stats            # 查看数据库统计
"""

import argparse
import json
import os
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(SKILL_DIR, "data", "chromadb")
SEED_PATH = os.path.join(SKILL_DIR, "data", "seed_foods.json")
COLLECTION_NAME = "sugarclaw_food_gi"


def get_client():
    import chromadb
    return chromadb.PersistentClient(path=DB_PATH)


def food_to_document(food):
    """将食物条目转换为适合向量检索的文本文档。"""
    aliases = " / ".join(food.get("aliases", []))
    macro = food.get("macro", {})
    return (
        f"食物名称: {food['food_name']} ({aliases})\n"
        f"GI值: {food['gi_value']} ({food['gi_level']}GI)\n"
        f"GL值: {food['gl_per_serving']} (每份{food['serving_size_g']}g)\n"
        f"营养成分(每份): 碳水{macro.get('carb_g', 0)}g, "
        f"蛋白质{macro.get('protein_g', 0)}g, "
        f"脂肪{macro.get('fat_g', 0)}g, "
        f"纤维{macro.get('fiber_g', 0)}g\n"
        f"地域: {food['regional_tag']}\n"
        f"分类: {food['food_category']}\n"
        f"对冲策略: {food['counter_strategy']}\n"
        f"数据来源: {food['data_source']}"
    )


def food_to_metadata(food):
    """提取结构化元数据，用于过滤查询。"""
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


def build_db(foods, replace=True):
    """构建或重建向量数据库。"""
    client = get_client()

    if replace:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"[INFO] 已删除旧 collection: {COLLECTION_NAME}")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "SugarClaw 中国食物 GI/GL 向量库"}
    )

    documents = []
    metadatas = []
    ids = []

    for food in foods:
        doc = food_to_document(food)
        meta = food_to_metadata(food)
        food_id = food["food_name"].replace(" ", "_")

        documents.append(doc)
        metadatas.append(meta)
        ids.append(food_id)

    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    print(f"[OK] 成功导入 {len(documents)} 条食物数据到 {DB_PATH}")
    print(f"     Collection: {COLLECTION_NAME}")
    return collection


def append_db(extra_path):
    """追加新数据到现有数据库。"""
    with open(extra_path, "r", encoding="utf-8") as f:
        foods = json.load(f)

    client = get_client()
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    documents = []
    metadatas = []
    ids = []

    for food in foods:
        doc = food_to_document(food)
        meta = food_to_metadata(food)
        food_id = food["food_name"].replace(" ", "_")
        documents.append(doc)
        metadatas.append(meta)
        ids.append(food_id)

    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
    print(f"[OK] 追加/更新 {len(documents)} 条食物数据")


def show_stats():
    """显示数据库统计。"""
    client = get_client()
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print("[WARN] 数据库尚未创建，请先运行 build_vectordb.py")
        sys.exit(1)

    count = collection.count()
    print(f"数据库路径: {DB_PATH}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"食物条目数: {count}")

    # 统计 GI 分布
    all_data = collection.get(include=["metadatas"])
    gi_levels = {"高": 0, "中": 0, "低": 0}
    regions = {}
    categories = {}
    for meta in all_data["metadatas"]:
        level = meta.get("gi_level", "未知")
        gi_levels[level] = gi_levels.get(level, 0) + 1
        region = meta.get("regional_tag", "未知")
        regions[region] = regions.get(region, 0) + 1
        cat = meta.get("food_category", "未知")
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\nGI 分布:")
    for level, n in sorted(gi_levels.items()):
        print(f"  {level}GI: {n} 种")
    print(f"\n地域分布:")
    for region, n in sorted(regions.items(), key=lambda x: -x[1]):
        print(f"  {region}: {n} 种")
    print(f"\n食物分类:")
    for cat, n in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {n} 种")


def main():
    parser = argparse.ArgumentParser(
        description="SugarClaw GI/GL 向量数据库构建器"
    )
    parser.add_argument(
        "--append", metavar="FILE",
        help="追加额外食物 JSON 文件到现有数据库"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="显示数据库统计信息"
    )
    parser.add_argument(
        "--seed", default=SEED_PATH,
        help=f"种子数据文件路径 (默认: {SEED_PATH})"
    )
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.append:
        append_db(args.append)
        return

    # 默认: 从种子文件构建
    with open(args.seed, "r", encoding="utf-8") as f:
        foods = json.load(f)

    print(f"[INFO] 加载 {len(foods)} 条种子食物数据: {args.seed}")
    build_db(foods, replace=True)


if __name__ == "__main__":
    main()
