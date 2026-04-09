# SugarClaw

**AI 驱动的糖尿病决策引擎** | AI-Powered Diabetes Decision Engine

---

## 项目简介

SugarClaw 是一个基于 OpenClaw 架构的多智能体系统，专为糖尿病患者设计。系统通过卡尔曼滤波预测血糖趋势、向量化中国食物 GI/GL 数据库提供饮食评估、PubMed 文献检索提供循证支撑，并结合心理疏导，为用户构建数据驱动的"代谢对冲"决策体系。

核心理念：**认知重构而非限制** -- 不说"禁止吃"，而是提供"最小代价补偿方案"。

---

## 系统架构

```
                         ┌─────────────────────────┐
                         │       SugarClaw          │
                         │     决策引擎中枢         │
                         └────────┬────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
    ┌─────────▼────────┐ ┌───────▼────────┐ ┌────────▼───────┐
    │   生理罗盘       │ │   地道风味     │ │   心理防线     │
    │ Physiological    │ │ Regional       │ │ Empathy        │
    │ Analyst          │ │ Dietitian      │ │ Coach          │
    │ weight: 1.0      │ │ weight: 0.8    │ │ weight: 0.6    │
    └──┬────┬────┬─────┘ └──┬────┬───────┘ └──┬─────────────┘
       │    │    │           │    │             │
       │    │    │           │    │             │
  ┌────▼──┐ │ ┌─▼───────┐ ┌▼────▼──┐    ┌────▼──────────┐
  │Kalman │ │ │ PubMed  │ │Food GI │    │   PubMed      │
  │Filter │ │ │Research │ │RAG     │    │  (mental)     │
  │Engine │ │ │  er     │ │ChromaDB│    │               │
  └───────┘ │ └─────────┘ └────────┘    └───────────────┘
            │
     ┌──────▼──────┐
     │ user_manager │
     └─────────────┘

  Skills: kalman-filter-engine | food-gi-rag | pubmed-researcher | user_manager
```

---

## 核心功能

### 卡尔曼滤波预测引擎 (kalman-filter-engine)

- 支持三种滤波器变体：**KF**（稳态/睡眠）、**EKF**（胰岛素注射后）、**UKF**（餐后非线性峰值）
- 自动模式根据血糖变化率动态选择最优滤波器
- 临床校准参数：基于 **125 例患者**、**128,157 个 CGM 数据点**（上海 T1DM/T2DM 数据集）
- 自适应 ISF（胰岛素敏感因子）校准管线：从原始默认 2.5 校准至 0.73
- 三级预警系统：CRITICAL / WARNING / PREDICTIVE，覆盖低血糖（<3.9）和高血糖（>10.0）

### 中国食物 GI/GL 向量检索 (food-gi-rag)

- **501 种中国食物**数据库，覆盖 **36 个地域**、**18 个分类**
- 基于 ChromaDB 的语义向量搜索，支持口语化模糊匹配（"过早吃了碗面" -> 热干面）
- 内置"血糖对冲桩"策略：高 GI 食物自动推荐低 GI 搭配方案
- 数据来源：《中国食物成分表》第6版、悉尼大学 GI 数据库、杨月欣等中国 GI 实测研究

### PubMed 循证文献检索 (pubmed-researcher)

- 通过 NCBI E-Utilities API 实时检索 PubMed/MEDLINE 数据库
- 四种预设检索模式：`food-impact` / `therapy` / `cgm` / `mental`
- 内置 Rate Limiting 保护与自动退避重试机制
- 输出规范：标题 + 核心结论 + PubMed 链接 + 医学免责声明

### Mock Persona 测试系统

- 三套虚拟患者档案，覆盖不同糖尿病类型与行为特征：
  - `T1DM_hypo_prone` -- 1 型糖尿病，低血糖高风险
  - `T2DM_foodie` -- 2 型糖尿病，饮食偏好丰富
  - `prediabetes_athlete` -- 糖尿病前期，运动型用户

---

## 快速开始

### 环境要求

- Python 3.10+
- NumPy
- ChromaDB
- 网络连接（PubMed API 调用）

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd workspace

# 初始化 food-gi-rag 虚拟环境（Kalman 引擎共享此 venv）
cd skills/food-gi-rag
python3 -m venv .venv
source .venv/bin/activate
pip install numpy chromadb

# 构建食物向量数据库
python3 scripts/build_vectordb.py
```

### 基本使用

```bash
VENV=~/.openclaw/workspace/skills/food-gi-rag/.venv/bin/python3

# 血糖趋势预测（自动选择滤波器）
$VENV skills/kalman-filter-engine/scripts/kalman_engine.py \
  --readings "6.2 6.5 6.8 7.3 7.9 8.5"

# 查询食物 GI/GL
$VENV skills/food-gi-rag/scripts/query_food.py "热干面"

# 获取血糖对冲方案
$VENV skills/food-gi-rag/scripts/query_food.py --counter "肠粉"

# PubMed 文献检索
python3 skills/pubmed-researcher/scripts/pubmed_researcher.py \
  "metformin diabetes" --mode therapy --abstract --max 5
```

---

## 项目结构

```
workspace/
├── AGENTS.md                          # 智能体定义与协作 SOP
├── SOUL.md                            # 系统人格与沟通风格
├── USER.md                            # 用户健康档案
├── TOOLS.md                           # 工具配置备忘
├── scripts/
│   └── user_manager.py                # 用户档案管理工具
├── skills/
│   ├── kalman-filter-engine/          # 卡尔曼滤波血糖预测
│   │   ├── SKILL.md
│   │   ├── data/
│   │   │   └── calibrated_params.json # 临床校准参数
│   │   ├── memory/
│   │   │   └── cgm_buffer.json        # CGM 实时缓冲
│   │   └── scripts/
│   │       ├── kalman_engine.py        # 主引擎 (KF/EKF/UKF)
│   │       ├── calibrate_kalman.py     # 参数校准脚本
│   │       └── cgm_replay.py           # CGM 数据回放
│   ├── food-gi-rag/                   # 食物 GI/GL 向量检索
│   │   ├── SKILL.md
│   │   ├── data/
│   │   │   ├── seed_foods.json         # 种子食物数据
│   │   │   └── foods_500.json          # 501 种食物完整库
│   │   └── scripts/
│   │       ├── build_vectordb.py       # ChromaDB 构建
│   │       └── query_food.py           # 语义查询接口
│   └── pubmed-researcher/             # PubMed 文献检索
│       ├── SKILL.md
│       └── scripts/
│           └── pubmed_researcher.py    # NCBI E-Utilities 封装
├── tests/
│   └── mock_users/                    # Mock Persona 测试
│       ├── T1DM_hypo_prone.md
│       ├── T2DM_foodie.md
│       └── prediabetes_athlete.md
├── literature/                        # 文献管理库
│   ├── literature_manager.py
│   └── literature/
│       ├── metadata/                  # PubMed 文献元数据
│       └── summaries/                 # AI 文献摘要
└── memory/                            # 会话记忆与日志
    └── YYYY-MM-DD.md
```

---

## 安全架构与容错机制

系统采用三层纵深防御（Defense in Depth）架构，确保即使 LLM 发生幻觉，底层硬编码逻辑仍然能够拦截违反生理常识的输出。详见 **[ARCHITECTURE.md](ARCHITECTURE.md)**。

---

## 技术栈

| 组件 | 技术 |
|---|---|
| 运行时 | Python 3.10+ |
| 数值计算 | NumPy |
| 向量数据库 | ChromaDB |
| 文献检索 | NCBI E-Utilities API (PubMed) |
| 智能体架构 | OpenClaw |
| 滤波算法 | KF / EKF / UKF (Kalman Filter) |

---

## License

TBD

---

## 医学免责声明

**本项目仅供科研与数据参考，不构成临床诊断或治疗建议。**

SugarClaw 是一个实验性的 AI 辅助工具。所有血糖预测、饮食建议和文献检索结果均由算法生成，可能存在误差或不适用于个体情况。在涉及药物剂量调整或重大饮食结构改变前，请务必咨询您的主治医师。AI 生成内容可能存在幻觉（hallucination），请以专业医疗意见为准。

---

# English

## SugarClaw -- AI-Powered Diabetes Decision Engine

SugarClaw is a multi-agent system built on the OpenClaw architecture, designed as an intelligent companion for diabetes patients. It combines Kalman filter-based blood glucose prediction, a vectorized Chinese food GI/GL database, PubMed evidence-based literature retrieval, and empathetic coaching to deliver data-driven metabolic decision support.

### Core Philosophy

**Cognitive reframing over restriction** -- instead of "don't eat that," SugarClaw provides minimum-cost compensation strategies (e.g., pairing high-GI foods with fiber-rich counterbalances, or suggesting a post-meal walk).

### Three Agents

- **Physiological Analyst** -- CGM signal processing, Kalman filter prediction, hypo/hyper alerts
- **Regional Dietitian** -- Chinese food GI/GL lookup, counter-strategy recommendations across 36 regions
- **Empathy Coach** -- Psychological support, adherence coaching, behavioral intervention backed by literature

### Four Skills

- **kalman-filter-engine** -- KF/EKF/UKF blood glucose prediction, clinically calibrated on 125 patients / 128,157 CGM data points
- **food-gi-rag** -- 501 Chinese foods with ChromaDB vector search, semantic matching for colloquial food names
- **pubmed-researcher** -- Real-time PubMed/MEDLINE search via NCBI E-Utilities with 4 preset query modes
- **user_manager** -- Patient profile management and adaptive ISF calibration

### Medical Disclaimer

**This project is for research and informational purposes only. It does not constitute clinical diagnosis or treatment advice.** All predictions and recommendations are algorithm-generated and may contain errors. Always consult your physician before making changes to medication or diet.
