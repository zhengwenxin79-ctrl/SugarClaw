---
name: pubmed-researcher
description: "SugarClaw 糖尿病文献智能检索引擎。通过 NCBI E-Utilities API 实时检索 PubMed 数据库。Use when: (1) user asks about food impact on blood glucose (食物对血糖的影响), (2) latest diabetes therapies or drug research (糖尿病最新疗法), (3) CGM or insulin studies, (4) GI/GL values for specific foods, (5) diabetes self-management or psychological intervention research, (6) any biomedical literature query related to metabolism, nutrition, or endocrinology. NOT for: full-text PDF downloads, non-biomedical queries, or real-time clinical decision-making. Outputs structured [Title][Summary][PubMed Link]."
---

# PubMed Researcher — SugarClaw 文献检索引擎

通过 NCBI E-Utilities API 实时检索 PubMed/MEDLINE，为 SugarClaw 决策引擎提供循证医学支撑。

## 核心用法

使用 bundled 脚本一步完成检索：

```bash
# 基础检索
python3 scripts/pubmed_researcher.py "metformin diabetes" --max 5

# 带完整摘要
python3 scripts/pubmed_researcher.py "hot dry noodles glycemic index" --max 3 --abstract

# JSON 输出（供程序解析）
python3 scripts/pubmed_researcher.py "SGLT2 inhibitors" --max 5 --json

# 最新文献优先
python3 scripts/pubmed_researcher.py "GLP-1 agonist" --max 5 --sort date
```

## SugarClaw 预设检索模式

脚本内置 4 种与 SugarClaw Agent 角色对齐的检索模板，自动扩展查询词：

```bash
# [生理罗盘] 食物血糖影响 —— 自动关联 glycemic index + blood glucose + diabetes MeSH
python3 scripts/pubmed_researcher.py "热干面" --mode food-impact --max 5

# [生理罗盘] 最新疗法 —— 自动限定 Clinical Trial / Review / Meta-Analysis
python3 scripts/pubmed_researcher.py "SGLT2 inhibitors" --mode therapy --max 5

# [生理罗盘] CGM 研究
python3 scripts/pubmed_researcher.py "accuracy" --mode cgm --max 5

# [心理防线] 心理干预文献
python3 scripts/pubmed_researcher.py "burnout" --mode mental --max 3
```

## 手动高级检索（curl）

当需要精确控制检索式时直接调用 E-Utilities：

```bash
# Step 1: esearch 获取 PMID 列表
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=%22glycemic+index%22[mh]+AND+%22rice+noodles%22[tiab]+AND+%22diabetes%22[mh]&retmax=5&retmode=json&sort=relevance"

# Step 2: esummary 获取标题和元数据
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=PMID1,PMID2&retmode=json"

# Step 3: efetch 获取完整摘要
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=PMID1,PMID2&rettype=abstract&retmode=text"
```

### PubMed 字段标签

- `[ti]` 标题 / `[tiab]` 标题+摘要 / `[au]` 作者
- `[mh]` MeSH 主题词 / `[dp]` 出版日期 / `[pt]` 出版类型
- 布尔运算: `AND`, `OR`, `NOT`
- 出版类型: `"Review"[pt]`, `"Clinical Trial"[pt]`, `"Meta-Analysis"[pt]`

## 输出规范

结果必须包含以下三要素：

1. **[标题]** — 文献完整标题
2. **[核心结论摘要]** — 基于摘要提炼 1-2 句核心发现
3. **[PubMed 链接]** — `https://pubmed.ncbi.nlm.nih.gov/{PMID}/`

末尾附加声明："以上文献检索结果仅供科研与数据参考，不构成临床诊断或治疗建议。"

## 异常处理

脚本已内置以下保护机制：

- **Rate Limiting**: 请求间隔 ≥ 400ms（无 API Key 限 3 req/s），遇 429/5xx 自动指数退避重试
- **空结果反馈**: 返回医学严谨的建议（检查术语拼写、使用 MeSH 标准词、扩大检索范围）
- **网络异常**: 自动重试 2 次，超时后报错退出
- **API Key 可选**: 通过 `--api-key` 参数传入以提升频率限制至 10 req/s

## Agent 调用约定

### 生理罗盘 (Physiological Analyst)
- **触发**: 用户询问特定食物的血糖影响、胰岛素药代动力学、CGM 校准研究
- **调用**: `python3 scripts/pubmed_researcher.py "<食物/药物名>" --mode food-impact --abstract`
- **后处理**: 提取 GI/GL 数值，输入卡尔曼滤波引擎进行血糖预测修正

### 地道风味 (Regional Dietitian)
- **触发**: 用户提及中国特色食物，需要循证营养学依据
- **调用**: `python3 scripts/pubmed_researcher.py "<食物名> glycemic" --mode food-impact --max 3`
- **后处理**: 与本地 GI/GL 向量库交叉验证，输出对冲方案

### 心理防线 (Empathy Coach)
- **触发**: 检测到用户依从性下降，需要行为干预文献支撑
- **调用**: `python3 scripts/pubmed_researcher.py "<关键词>" --mode mental --max 3`
- **后处理**: 提炼为认知重构话术，避免限制性指令
