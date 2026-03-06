---
name: kalman-filter-engine
description: "SugarClaw CGM 血糖卡尔曼滤波预测引擎。Use when: (1) user provides CGM blood glucose readings and asks for trend/prediction (血糖趋势预测), (2) user reports eating a meal and wants to know future glucose impact (餐后血糖预测), (3) user took insulin and wants glucose forecast (注射胰岛素后预测), (4) system needs to generate Hypo_Alert or Hyper_Alert (低/高血糖预警), (5) Physiological Analyst agent needs to process CGM data stream, (6) user asks 'will I go low/high'. NOT for: food GI/GL lookup (use food-gi-rag), PubMed search (use pubmed-researcher), or clinical dosing decisions."
---

# SugarClaw 卡尔曼滤波血糖预测引擎

CGM 信号降噪 + 未来 30 分钟血糖预测 + 自动预警。实现 KF / EKF / UKF 三种滤波器。

## 环境

使用 food-gi-rag 的共享 venv（含 numpy）：

```bash
VENV=~/.openclaw/workspace/skills/food-gi-rag/.venv/bin/python3
```

## 核心用法

```bash
# 基础预测（自动选择滤波器）
$VENV scripts/kalman_engine.py --readings "6.2 6.5 6.8 7.3 7.9 8.5"

# 进食事件 — 自动切换 UKF 捕捉餐后峰值
$VENV scripts/kalman_engine.py --readings "6.2 6.5 6.8 7.3 7.9 8.5" --event meal --gi 82

# 注射胰岛素 — 自动切换 EKF 模拟胰岛素动力学
$VENV scripts/kalman_engine.py --readings "12.5 11.8 10.9 10.1 9.5 9.0" --event insulin --dose 4

# 睡眠/稳态 — 强制使用标准 KF
$VENV scripts/kalman_engine.py --readings "5.8 5.7 5.6 5.5 5.6 5.5" --filter kf

# JSON 输出（供下游模块解析）
$VENV scripts/kalman_engine.py --readings "6.2 6.5 6.8 7.3 7.9 8.5" --json

# 从文件输入
$VENV scripts/kalman_engine.py --input cgm_data.json
```

## 滤波器自动选择逻辑

| 场景 | 滤波器 | 原因 |
|---|---|---|
| `--event meal` | **UKF** | sigma 点采样捕捉餐后非线性峰值 |
| `--event insulin` | **EKF** | 模拟胰岛素指数衰减动力学 |
| 稳态（变化率 < 0.4/5min） | **KF** | 线性足够，低功耗 |
| 高变异（变化率 > 0.8/5min） | **UKF** | 自动推断非线性事件 |
| 中等变异 | **EKF** | 可能有药物/进食影响 |

## 预警阈值

| 类型 | 阈值 | 预警级别 |
|---|---|---|
| 紧急低血糖 | < 3.0 mmol/L | CRITICAL |
| 低血糖 | < 3.9 mmol/L | WARNING |
| 高血糖 | > 10.0 mmol/L | WARNING |
| 紧急高血糖（酮体风险） | > 13.9 mmol/L | CRITICAL |
| 预测性低/高血糖 | 30min 内预测越线 | PREDICTIVE |

## 参数说明

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--isf` | 0.73 (校准) | 胰岛素敏感因子（mmol/L per unit），从校准参数或 USER.md 读取 |
| `--gi` | 0 | 食物 GI 值，联动 food-gi-rag 获取 |
| `--gl` | 0 | 食物 GL 值，优先使用 |
| `--dose` | 0 | 胰岛素注射剂量（单位） |
| `--steps` | 6 | 预测步数（每步 5min，默认 30min） |
| `--process-noise` | auto | 过程噪声 Q，从校准参数自动读取 |

## 参数校准（基于上海 T1DM/T2DM 临床数据集）

引擎参数已通过 125 例患者、128,157 个 CGM 数据点校准，存储在 `data/calibrated_params.json`。

| 参数 | 原始默认 | 校准值 | 变化 | 数据基础 |
|---|---|---|---|---|
| 测量噪声 R | 0.25 | 5.042 | +1917% | 4,019 CGM-CBG 配对 |
| 过程噪声 Q | 0.01 | 0.004276 | -57% | 311,059 稳态段变化量 |
| 胰岛素 tau | 55 min | 77 min | +40% | 584 注射后衰减曲线 |
| 碳水 t_peak | 35 min | 45 min | +29% | 2,765 餐后上升段 |
| 碳水 t_decay | 90 min | 60 min | -33% | 1,345 餐后回落段 |
| ISF | 2.5 | 0.73 | -71% | 292 胰岛素-血糖对 |

校准脚本: `scripts/calibrate_kalman.py --data-dir <数据集路径>`

重新校准: `$VENV scripts/calibrate_kalman.py --data-dir /path/to/diabetes_datasets`

## 联动工作流

### 用户报告进食
1. `food-gi-rag` 查询食物 → 获取 GI/GL
2. `kalman_engine.py --readings "..." --event meal --gi <GI> --gl <GL>`
3. 若预测峰值超阈值 → 输出对冲方案

### 用户报告注射胰岛素
1. 从 USER.md 读取 ISF
2. `kalman_engine.py --readings "..." --event insulin --dose <剂量> --isf <ISF>`
3. 若预测低血糖 → 触发 Hypo_Alert

### CGM 实时流
1. 每 5 分钟追加新读数到 `memory/cgm_buffer.json`
2. 取最近 12 个读数（1 小时窗口）运行滤波预测
3. 有预警时主动通知用户
