# SugarClaw 安全架构与容错机制

## 概述

SugarClaw 处理的是糖尿病患者的代谢数据，错误的建议可能导致严重的健康后果。系统采用**三层纵深防御（Defense in Depth）** 架构，确保即使上层 LLM 发生幻觉，底层硬编码逻辑仍然能够拦截违反生理常识的输出。

核心原则：**越靠近患者的层级，约束越硬、越不可被 LLM 绕过。**

---

## 三层容错架构

```
┌───────────────────────────────────────────────────────────┐
│  Layer 3: 认知框架层 (SOUL.md / AGENTS.md)               │  提示词约束
│  "认知重构而非限制"、"数据优先"、"AI 不确定性提示"         │  可被 LLM 忽略
├───────────────────────────────────────────────────────────┤
│  Layer 2: Agent SOP 协作层 (AGENTS.md 工作流)             │  行为规则约束
│  触发条件、权重路由、强制检索、跨 Skill 联动              │  依赖 LLM 遵循
├───────────────────────────────────────────────────────────┤
│  Layer 1: Skill 硬编码层 (Python 脚本)                    │  代码级约束
│  阈值告警、数值 clamp、矩阵正定性、输入校验               │  LLM 无法绕过
└───────────────────────────────────────────────────────────┘
      ↑ 可靠性递增 / ↓ 灵活性递增
```

---

## Layer 1: Skill 硬编码层 — 最强拦截

**位置**：`skills/` 目录下的 Python 脚本
**特点**：纯代码逻辑，LLM 无法绕过，不依赖提示词

### 1.1 生理阈值告警系统

`kalman_engine.py` 中的 `generate_alerts()` 基于硬编码常量触发告警，不受 LLM 输出影响：

```python
# kalman_engine.py L42-46
HYPO_THRESHOLD  = 3.9    # 低血糖阈值 mmol/L
HYPER_THRESHOLD = 10.0   # 高血糖警戒 mmol/L
URGENT_LOW      = 3.0    # 紧急低血糖
URGENT_HIGH     = 13.9   # 紧急高血糖（酮体风险）
```

三级预警：

| 级别 | 触发条件 | 行为 |
|---|---|---|
| **CRITICAL** | 当前值 < 3.0 或 > 13.9 mmol/L | 立即输出紧急指令（补充 15g 速效碳水 / 监测酮体） |
| **WARNING** | 当前值 < 3.9 或 > 10.0 mmol/L | 输出预警建议 |
| **PREDICTIVE** | 30 分钟预测值 95% CI 下界 < 3.9 或预测值 > 10.0 | 输出趋势预警 |

**安全意义**：即使 LLM 产生幻觉认为"15.0 mmol/L 是安全的"，`generate_alerts()` 仍然会强制输出 `CRITICAL: Hyper_Alert`，LLM 无法抑制这个告警。

### 1.2 输入校验与拒绝执行

```python
# kalman_engine.py L710-712
if len(readings) < 3:
    print("错误: 至少需要 3 个血糖读数")
    sys.exit(1)

# ble_cgm_parser.py L124-126
if len(data) < 5:
    raise ValueError(f"CGM measurement too short: {len(data)} bytes (min 5)")
```

引擎在数据不足时**直接拒绝运行**，而非用 LLM 猜测填充缺失数据。

### 1.3 BLE 数据解析容错

`ble_cgm_parser.py` 的 `parse_binary_data()` 在遇到畸形数据包时**跳过并继续**，而非终止整个解析流程：

```python
# ble_cgm_parser.py L208-214
try:
    r = parse_cgm_measurement(chunk)
    readings.append(r)
except ValueError as e:
    print(f"Warning: skipping malformed measurement at offset {offset}: {e}",
          file=sys.stderr)
```

### 1.4 数值计算稳定性保障

UKF（无迹卡尔曼滤波）中针对协方差矩阵退化的防御：

- **Sigma 点生成**：使用特征值分解（`np.linalg.eigh`）替代 Cholesky 分解，对半正定矩阵更稳健。强制非负特征值 `np.maximum(eigvals, 1e-10)` 防止数值崩溃。
- **协方差矩阵维护**：每步预测和更新后强制对称化 `(P + P.T) / 2 + eye * 1e-10`，防止浮点累积误差导致滤波器发散。

```python
# kalman_engine.py L424-432 (sigma 点)
eigvals, eigvecs = np.linalg.eigh(M)
eigvals = np.maximum(eigvals, 1e-10)  # 强制非负

# kalman_engine.py L456 (predict 后)
self.P = (self.P + self.P.T) / 2 + np.eye(self.n) * 1e-10
```

### 1.5 校准参数热更新

`load_calibrated_params()` 基于文件修改时间（`mtime`）自动检测 `calibrated_params.json` 变更并重新加载，无需重启服务：

```python
# kalman_engine.py L54-67
mtime = os.path.getmtime(params_path)
if CALIBRATED_PARAMS is None or mtime != _PARAMS_MTIME:
    with open(params_path, 'r') as f:
        CALIBRATED_PARAMS = json.load(f)
```

### 1.6 向量搜索距离阈值

`query_food.py` 对 ChromaDB 语义搜索结果设置了距离阈值，过滤掉不相关的匹配：

```python
# query_food.py L29
DISTANCE_THRESHOLD = 1.2  # 超过此值视为不相关

# query_food.py L141-145
if dist <= DISTANCE_THRESHOLD:
    filtered_metas.append(meta)
```

防止 LLM 将低置信度的食物匹配结果作为高置信度建议传递给用户。

---

## Layer 2: Agent SOP 协作层 — 行为规则约束

**位置**：`AGENTS.md` 中的智能体定义与协作工作流
**特点**：通过 OpenClaw 的多 Agent 架构实现角色分工与行为约束，依赖 LLM 的指令遵循能力

### 2.1 权重路由与触发条件

三个 Agent 按场景激活，避免职能越界：

| Agent | 权重 | 触发条件 | 约束 |
|---|---|---|---|
| 生理罗盘 (Physiological Analyst) | 1.0 | 输入包含血糖数值、BLE 字节流、"趋势"关键词 | 500ms 内完成 30 分钟预测 |
| 地道风味 (Regional Dietitian) | 0.8 | 输入匹配中国食物向量库 | 高 GI 食物必须强制检索对冲桩 |
| 心理防线 (Empathy Coach) | 0.6 | 检测到焦虑、内疚感、依从性下降 | **严禁使用限制性指令** |

### 2.2 串行化工作流 (SOP)

AGENTS.md 定义了严格的执行顺序：

```
1. 监听层 → NLP 实体识别（数值、食物、情绪）
2. 并发处理：
   - 生理罗盘：计算血糖动态变化率 + 30min 预测
   - 地道风味：计算 GL 负荷 + 匹配对冲方案
3. 聚合层 → Task Orchestrator 整合，确保逻辑不冲突
   （例：若预测将发生低血糖，则不建议快走）
4. 输出层 → 通过 SOUL.md 语调发送结构化回复
```

**聚合层的冲突检测**是关键：它防止了"生理罗盘预测低血糖"与"心理防线建议餐后快走"同时出现的矛盾。

### 2.3 跨 Skill 强制联动

AGENTS.md 规定了 Skill 之间的强制数据流：

- 用户报告进食 → `query_food.py --json` 获取 GI/GL → 注入 `kalman_engine.py --event meal --gi <GI>` 进行餐后预测
- 用户问"昨晚为什么低血糖" → 必须同时调用 food-gi-rag + 读取 `memory/` 日志中的饮食记录与步数进行交叉关联
- PubMed 检索异常 → 脚本内置 Rate Limiting（请求间隔 >= 400ms，429/5xx 自动退避重试）

### 2.4 OpenClaw Lane Queue 保障

OpenClaw 的 Lane-based 命令队列确保同一会话中的 Skill 调用**串行执行**，避免竞态条件。例如：BLE 数据写入 `cgm_buffer.json` 完成后，Kalman 引擎才读取该文件，不会出现读到半写入状态的数据。

---

## Layer 3: 认知框架层 — 最灵活但最弱

**位置**：`SOUL.md`
**特点**：通过系统提示词塑造 LLM 的行为倾向，是最柔性的约束

### 3.1 核心信念约束

SOUL.md 中定义了四条不可违反的认知原则：

1. **数据优先**：未检索到当日血糖趋势或 ISF 数据前，不得给出具体饮食建议
2. **专业咨询优先**：涉及药物剂量调整或重大饮食结构改变前，必须要求用户咨询主治医师
3. **AI 不确定性提示**：处理复杂代谢模型时，需告知用户 AI 生成内容可能存在幻觉
4. **因果关联前置**：深度分析前必须关联前一晚的饮食日志、步数记录与胰岛素剂量

### 3.2 沟通风格硬约束

- 单次回复中，核心行动指令（Actionable Steps）**必须置顶且不超过 3 条**
- 不使用绝对限制性指令（如"严禁食用"），而是提供"最小代价补偿方案"
- 避免无效的礼貌用语，直接切入核心建议

### 3.3 局限性

这一层完全依赖 LLM 的指令遵循能力。在以下场景中可能失效：

- 上下文窗口过长，系统提示被"冲淡"
- LLM 在多轮对话中逐渐偏离初始人格设定
- 用户通过 prompt injection 诱导 LLM 忽略 SOUL.md 约束

因此，**任何涉及患者安全的硬性约束，都不应仅依赖这一层**，必须在 Layer 1 有对应的代码级兜底。

---

## 执行链路与容错点全景

```
BLE 原始字节
  │
  ▼
ble_cgm_parser.py ──── [L1] 最小字节数校验、畸形包跳过、SFLOAT 特殊值处理
  │
  ▼
cgm_buffer.json ─────── [L2] Lane Queue 串行写入，防止竞态
  │
  ▼
auto_select_filter() ── [L1] 基于变化率阈值自动选择 KF/EKF/UKF
  │                      [L2] event 参数由 Agent SOP 强制注入
  ▼
KF / EKF / UKF ──────── [L1] 协方差矩阵正定性维护、sigma 点稳健生成
  │                      [L1] 校准参数热更新（mtime 检测）
  ▼
generate_alerts() ────── [L1] 硬编码阈值三级告警，LLM 无法抑制
  │
  ▼
query_food.py ─────────── [L1] 距离阈值过滤低置信度匹配
  │                       [L2] 高 GI 食物强制触发对冲检索
  ▼
LLM 生成回复 ─────────── [L2] Agent 权重路由、冲突检测（低血糖时不建议运动）
                          [L3] SOUL.md 沟通风格约束、医学免责声明
```

---

## 医学免责声明

本项目仅供科研与数据参考，不构成临床诊断或治疗建议。所有血糖预测、饮食建议和文献检索结果均由算法生成，可能存在误差或不适用于个体情况。在涉及药物剂量调整或重大饮食结构改变前，请务必咨询您的主治医师。
