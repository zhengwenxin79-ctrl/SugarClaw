---
name: food-gi-rag
description: "SugarClaw 中国食物 GI/GL 向量检索引擎 (ChromaDB)。Use when: (1) user mentions a specific food and asks about blood sugar impact (食物对血糖影响), (2) user needs GI/GL values for Chinese foods (热干面/肠粉/馒头等), (3) user asks for dietary counter-strategies (血糖对冲方案), (4) user asks which foods are high/low GI, (5) Regional Dietitian agent needs to evaluate a meal, (6) user asks 'what can I eat' or 'is this food OK for diabetes'. NOT for: PubMed literature search (use pubmed-researcher), clinical drug queries, or CGM data analysis."
---

# SugarClaw 食物 GI/GL 向量检索引擎

基于 ChromaDB 的中国食物 GI/GL 语义搜索系统，支持模糊语义匹配 + 结构化元数据过滤。

## 环境

所有脚本必须使用 skill 内置的 venv：

```bash
VENV=~/.openclaw/workspace/skills/food-gi-rag/.venv/bin/python3
```

## 核心查询命令

```bash
# 语义搜索（支持口语化输入）
$VENV scripts/query_food.py "过早吃了碗面" --max 3

# 精确食物查询
$VENV scripts/query_food.py "热干面"

# 直接获取对冲方案
$VENV scripts/query_food.py --counter "肠粉"

# 按地域过滤
$VENV scripts/query_food.py "早茶" --region 广东 --max 5

# 列出高GI食物
$VENV scripts/query_food.py --high-gi --max 10

# 列出低GI食物（推荐替代）
$VENV scripts/query_food.py --low-gi --max 10

# 按分类过滤
$VENV scripts/query_food.py "主食" --category 面食

# JSON 输出（供程序解析）
$VENV scripts/query_food.py "米饭" --json
```

## 数据库管理

```bash
# 重建数据库（从 seed_foods.json）
$VENV scripts/build_vectordb.py

# 追加新食物数据
$VENV scripts/build_vectordb.py --append data/extra_foods.json

# 查看统计
$VENV scripts/build_vectordb.py --stats
```

### 添加新食物

创建 JSON 文件遵循此 Schema：

```json
{
  "food_name": "食物名称",
  "aliases": ["别名1", "别名2"],
  "gi_value": 75,
  "gi_level": "高|中|低",
  "gl_per_serving": 30,
  "serving_size_g": 200,
  "macro": {"carb_g": 40, "protein_g": 10, "fat_g": 5, "fiber_g": 2},
  "regional_tag": "地域",
  "food_category": "分类",
  "counter_strategy": "对冲建议",
  "data_source": "数据来源"
}
```

GI 分级标准: 低 ≤55, 中 56-69, 高 ≥70

## 数据来源

当前 49 种食物的数据来自：

| 来源 | 用途 |
|---|---|
| 《中国食物成分表》第6版 | 营养素(碳水/蛋白/脂肪/纤维)、GL 计算基础 |
| 悉尼大学 GI 数据库 (glycemicindex.com) | 权威 GI 数值 |
| 杨月欣等中国 GI 实测研究 | 中国特色食物的实测 GI 值 |

部分地域特色食物（如炸酱面、兰州牛肉面）GI 值为基于成分和烹饪方式的专家估算，标注"估算"。

## Agent 调用约定

### 地道风味 (Regional Dietitian) — 主要调用者
1. 用户提及食物名 → `query_food.py "<食物名>"` 获取 GI/GL + 对冲方案
2. 若为高 GI 食物 → 自动调用 `--counter` 获取对冲桩建议
3. 结合 LBS Skill 检索附近便利店获取对冲食材

### 生理罗盘 (Physiological Analyst)
1. 用户报告进食 → 调用 `query_food.py` 获取 GL 值
2. 将 GL 输入卡尔曼滤波引擎预测餐后血糖曲线
3. 若预测峰值超阈值 → 联动对冲方案
