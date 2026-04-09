# SugarClaw 运维手册 (Runbook)

> 本文档面向**无 AI 辅助**时的独立运维场景。所有命令均可直接复制执行。

---

## 目录

1. [快速启动](#1-快速启动)
2. [项目目录结构](#2-项目目录结构)
3. [环境依赖总览](#3-环境依赖总览)
4. [后端运维](#4-后端运维)
5. [技能库运维](#5-技能库运维)
6. [数据库运维](#6-数据库运维)
7. [前端运维](#7-前端运维)
8. [常见故障排查](#8-常见故障排查)
9. [关键配置速查](#9-关键配置速查)
10. [API 接口速查](#10-api-接口速查)

---

## 1. 快速启动

```bash
# ── 终端 1：启动后端 ──────────────────────────────────────
cd /Users/zwx/sugarclaw-app/backend
source .venv/bin/activate          # 若无 .venv 见 §3
uvicorn api:app --reload --port 8082

# ── 终端 2：启动前端 ──────────────────────────────────────
cd /Users/zwx/sugarclaw-app/frontend
flutter run -d chrome              # 浏览器
# flutter run -d macos             # macOS 桌面

# ── 验证 ──────────────────────────────────────────────────
open http://localhost:8082/docs    # 后端 Swagger UI
open http://localhost:8080         # Flutter Web UI
```

---

## 2. 项目目录结构

```
/Users/zwx/sugarclaw-app/
├── backend/
│   ├── api.py          主服务（2347行，27个路由）
│   ├── database.py     SQLite 封装（5张表）
│   ├── guidelines.py   Agent SOP & Prompt 模板
│   ├── sugarclaw.db    数据库文件
│   └── .env            环境变量（API Key 等）
│
├── frontend/lib/
│   ├── main.dart       App 入口 & Provider 装配
│   ├── theme.dart      设计系统（颜色/字体/间距）
│   ├── models/         数据模型（JSON 映射）
│   ├── providers/      状态管理（5个 ChangeNotifier）
│   ├── screens/        界面（Dashboard/Scale/Chat/CGM/Profile/PubMed）
│   ├── services/       api_service.dart（HTTP 封装）
│   └── widgets/        可复用组件
│
~/.openclaw/workspace/skills/      技能库（与项目解耦）
│   ├── kalman-filter-engine/scripts/
│   │   ├── kalman_engine.py       KF/EKF/UKF 预测引擎
│   │   ├── ble_cgm_parser.py      BLE 传感器解析
│   │   └── calibrate_kalman.py    参数校准工具
│   ├── food-gi-rag/
│   │   ├── scripts/query_food.py  向量食物检索
│   │   ├── scripts/build_vectordb.py  重建向量库
│   │   └── .venv/                 独立 Python 环境（含 ChromaDB）
│   └── pubmed-researcher/scripts/pubmed_researcher.py
│
~/.openclaw/openclaw.json          全局配置（API Key / 技能路径）
```

---

## 3. 环境依赖总览

### 3.1 系统要求

| 依赖 | 版本 | 检查命令 |
|------|------|---------|
| Python | 3.10+ | `python3 --version` |
| Flutter | 3.x | `flutter --version` |
| SQLite | 任意 | `sqlite3 --version` |
| Node.js | 可选（Web 构建） | `node --version` |

### 3.2 后端 Python 依赖

```bash
# 首次创建 venv
cd /Users/zwx/sugarclaw-app/backend
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn httpx pydantic python-dotenv numpy
```

### 3.3 技能库依赖

```bash
# 技能库使用独立 venv（food-gi-rag 的 .venv 同时服务于 kalman 引擎）
SKILL_VENV=~/.openclaw/workspace/skills/food-gi-rag/.venv

# 验证存在
ls $SKILL_VENV/bin/python3

# 若不存在，重建
cd ~/.openclaw/workspace/skills/food-gi-rag
python3 -m venv .venv
source .venv/bin/activate
pip install chromadb numpy sentence-transformers
python3 scripts/build_vectordb.py    # 重建向量库（501种食物）
```

### 3.4 前端 Flutter 依赖

```bash
cd /Users/zwx/sugarclaw-app/frontend
flutter pub get     # 安装所有 Dart 依赖
```

---

## 4. 后端运维

### 4.1 启动 / 停止

```bash
# 开发模式（热重载）
uvicorn api:app --reload --port 8082

# 生产模式（多 worker）
uvicorn api:app --host 0.0.0.0 --port 8082 --workers 2

# 停止：Ctrl+C
```

### 4.2 环境变量（backend/.env）

```bash
# 查看当前配置
cat /Users/zwx/sugarclaw-app/backend/.env
```

| 变量名 | 用途 | 必须？ |
|--------|------|--------|
| `DEEPSEEK_API_KEY` | /api/chat 流式对话 | 是（Chat功能） |
| `SKILL_BASE_DIR` | 技能库根路径 | 否（有默认值） |
| `DATABASE_PATH` | SQLite 路径 | 否（默认 ./sugarclaw.db） |

```bash
# 修改 API Key
echo "DEEPSEEK_API_KEY=sk-xxxxxxxx" >> /Users/zwx/sugarclaw-app/backend/.env
```

### 4.3 验证后端正常

```bash
# 健康检查
curl http://localhost:8082/api/health

# 测试分析接口
curl -X POST http://localhost:8082/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"readings": [6.2, 6.5, 6.8, 7.3, 7.9, 8.5], "event": "meal", "food": "热干面"}'

# 列出内置案例
curl http://localhost:8082/api/cases
```

### 4.4 查看运行日志

```bash
# uvicorn 日志直接输出到终端，无单独日志文件
# 若需持久化：
uvicorn api:app --port 8082 2>&1 | tee /tmp/sugarclaw-backend.log
```

---

## 5. 技能库运维

### 5.1 命令行直接测试（不依赖后端）

```bash
# 快捷变量
VENV=~/.openclaw/workspace/skills/food-gi-rag/.venv/bin/python3
KF=~/.openclaw/workspace/skills/kalman-filter-engine/scripts/kalman_engine.py
FOOD=~/.openclaw/workspace/skills/food-gi-rag/scripts/query_food.py
PUB=~/.openclaw/workspace/skills/pubmed-researcher/scripts/pubmed_researcher.py

# ── Kalman 预测 ──────────────────────────────────────────
# 饭后（自动选 UKF）
$VENV $KF --readings "6.2 6.5 6.8 7.3 7.9 8.5" --event meal --gi 82 --json

# 胰岛素注射后（EKF）
$VENV $KF --readings "14.0 13.5 13.0 12.5 12.0 11.5" --event insulin --dose 4 --json

# 稳定睡眠（KF）
$VENV $KF --readings "5.5 5.6 5.5 5.7 5.6 5.5" --event sleep --json

# 强制指定滤波器
$VENV $KF --readings "6.2 6.5 6.8" --filter ukf --json

# ── 食物查询 ──────────────────────────────────────────────
$VENV $FOOD "热干面" --json           # 精确查询
$VENV $FOOD "过早吃了碗面" --json      # 模糊语义查询
$VENV $FOOD --counter "肠粉"          # 获取反制食物
$VENV $FOOD --region 广东 --json      # 按地区筛选
$VENV $FOOD --high-gi                 # 列出高GI食物
$VENV $FOOD --max 5 "米饭"            # 最多5条结果

# ── PubMed 文献检索 ──────────────────────────────────────
python3 $PUB "SGLT2 inhibitors" --mode therapy --max 5
python3 $PUB "热干面 glycemic index" --mode food-impact --max 3
python3 $PUB "CGM accuracy" --mode cgm --abstract --json
# 模式: food-impact | therapy | cgm | mental
```

### 5.2 重建食物向量数据库

```bash
# 在修改种子数据或向量库损坏时执行
cd ~/.openclaw/workspace/skills/food-gi-rag
source .venv/bin/activate
python3 scripts/build_vectordb.py

# 验证重建成功
$VENV $FOOD "热干面" --json
```

### 5.3 Kalman 参数热更新

```bash
# 校准参数文件（无需重启，api.py 通过 mtime 自动热重载）
cat ~/.openclaw/workspace/skills/kalman-filter-engine/data/calibrated_params.json

# 查看关键参数
# process_noise_scale: 0.004276  (过程噪声，越大对新读数越敏感)
# measurement_noise_R: 5.042     (测量噪声，越大越平滑)
# tau_insulin: 77                (胰岛素作用时间，分钟)
# t_peak_meal: 45                (碳水吸收峰值时间，分钟)
```

---

## 6. 数据库运维

### 6.1 常用查询

```bash
sqlite3 /Users/zwx/sugarclaw-app/backend/sugarclaw.db

# 查看所有表
.tables

# 查看用户档案
SELECT name, age, diabetes_type, isf, icr FROM users;

# 查看食物缓存（最近10条）
SELECT food_name, gi_value, gi_level, gl_per_serving FROM food_cache
ORDER BY created_at DESC LIMIT 10;

# 查看血糖日志（最近7天）
SELECT timestamp, glucose_mmol, note FROM glucose_log
WHERE timestamp > datetime('now', '-7 days')
ORDER BY timestamp DESC;

# 查看CGM会话
SELECT session_id, COUNT(*) as points, MIN(glucose_mmol), MAX(glucose_mmol)
FROM cgm_readings GROUP BY session_id ORDER BY MIN(timestamp) DESC LIMIT 5;

# 查看PubMed搜索历史
SELECT query, mode, total_count, created_at FROM search_history
ORDER BY created_at DESC LIMIT 10;

.quit
```

### 6.2 备份与恢复

```bash
# 备份（每次重要操作前执行）
cp /Users/zwx/sugarclaw-app/backend/sugarclaw.db \
   /Users/zwx/sugarclaw-app/backend/sugarclaw.db.bak.$(date +%Y%m%d)

# 验证备份完整性
sqlite3 /Users/zwx/sugarclaw-app/backend/sugarclaw.db.bak.$(date +%Y%m%d) ".tables"

# 恢复（从备份）
cp /Users/zwx/sugarclaw-app/backend/sugarclaw.db.bak.YYYYMMDD \
   /Users/zwx/sugarclaw-app/backend/sugarclaw.db
```

### 6.3 数据库表结构

```sql
-- 用户档案（单用户系统）
users: id, name, age, weight, height, diabetes_type,
       medications(JSON), isf, icr, regional_preference,
       created_at, updated_at

-- 食物 RAG 缓存（避免重复调用 ChromaDB）
food_cache: food_name(UNIQUE), gi_value, gi_level,
            gl_per_serving, serving_size_g,
            carb_g, protein_g, fat_g, fiber_g,
            regional_tag, food_category, counter_strategy,
            data_source, created_at

-- CGM 读数（按 session_id 分组）
cgm_readings: id, session_id, timestamp,
              glucose_mmol, glucose_mgdl, event, source, created_at
              INDEX: idx_cgm_session(session_id)

-- PubMed 搜索历史
search_history: id, query, mode, results_json(JSON),
                total_count, created_at

-- 手动血糖日志
glucose_log: id, user_id, timestamp, glucose_mmol, note, created_at
             INDEX: idx_glucose_log_ts(timestamp)
```

### 6.4 清理旧数据

```bash
sqlite3 /Users/zwx/sugarclaw-app/backend/sugarclaw.db

-- 删除90天前的CGM数据
DELETE FROM cgm_readings WHERE created_at < datetime('now', '-90 days');

-- 删除30天前的PubMed搜索历史
DELETE FROM search_history WHERE created_at < datetime('now', '-30 days');

-- 回收磁盘空间
VACUUM;

.quit
```

---

## 7. 前端运维

### 7.1 开发调试

```bash
cd /Users/zwx/sugarclaw-app/frontend

# 运行（选择目标平台）
flutter run -d chrome          # Chrome 浏览器
flutter run -d macos           # macOS 桌面应用
flutter run -d iphone          # iOS 模拟器（需 Xcode）
flutter devices                # 查看所有可用设备

# 热重载（运行时在终端按）
# r  → 热重载（不重置状态）
# R  → 热重启（重置状态）
# q  → 退出
```

### 7.2 构建发布版本

```bash
cd /Users/zwx/sugarclaw-app/frontend

# Web 发布包
flutter build web --release
# 输出: build/web/（可直接部署到静态托管）

# macOS 应用
flutter build macos --release
# 输出: build/macos/Build/Products/Release/sugarclaw.app
```

### 7.3 修改后端地址

如果后端不在 localhost，修改 `frontend/lib/services/api_service.dart`：

```dart
// 找到 baseUrl 或 _baseUrl 定义，修改为新地址
static const String _baseUrl = 'http://YOUR_SERVER_IP:8082';
```

---

## 8. 常见故障排查

### 故障 1：后端启动失败 — ModuleNotFoundError

```bash
# 症状: ImportError: No module named 'fastapi'
# 原因: 未激活 venv 或依赖未安装

source /Users/zwx/sugarclaw-app/backend/.venv/bin/activate
pip install fastapi uvicorn httpx pydantic python-dotenv numpy
```

### 故障 2：食物查询返回空结果

```bash
# 症状: query_food.py 返回 "未找到" 或 ChromaDB 错误
# 原因: 向量库损坏或未初始化

cd ~/.openclaw/workspace/skills/food-gi-rag
source .venv/bin/activate
python3 scripts/build_vectordb.py    # 重建向量库
```

### 故障 3：Kalman 预测报 numpy 错误

```bash
# 症状: No module named 'numpy' 或 linalg 错误
# 原因: 用了系统 python3 而非技能库 venv

# 必须用技能库 venv 的 python
~/.openclaw/workspace/skills/food-gi-rag/.venv/bin/python3 \
  ~/.openclaw/workspace/skills/kalman-filter-engine/scripts/kalman_engine.py \
  --readings "6.2 6.5 6.8" --json
```

### 故障 4：/api/chat 无响应或报错

```bash
# 症状: 500 错误或超时
# 原因 1: DeepSeek API Key 无效或余额不足

cat /Users/zwx/sugarclaw-app/backend/.env | grep DEEPSEEK

# 原因 2: 网络问题，测试连通性
curl https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 故障 5：前端无法连接后端

```bash
# 症状: Flutter 界面显示"连接失败"
# 检查后端是否在运行
curl http://localhost:8082/api/health

# 检查端口占用
lsof -i :8082
lsof -i :8080

# 后端日志里是否有 CORS 错误
# → 检查 api.py 里的 CORSMiddleware 配置
```

### 故障 6：数据库锁定（database is locked）

```bash
# 症状: sqlite3.OperationalError: database is locked
# 原因: 多个进程同时写入，或上次异常退出留下锁

# 查找占用数据库的进程
lsof /Users/zwx/sugarclaw-app/backend/sugarclaw.db

# 若数据库文件损坏
sqlite3 /Users/zwx/sugarclaw-app/backend/sugarclaw.db "PRAGMA integrity_check;"

# 从备份恢复
cp /Users/zwx/sugarclaw-app/backend/sugarclaw.db.bak.YYYYMMDD \
   /Users/zwx/sugarclaw-app/backend/sugarclaw.db
```

### 故障 7：Flutter 编译失败

```bash
# 清理缓存后重试
cd /Users/zwx/sugarclaw-app/frontend
flutter clean
flutter pub get
flutter run -d chrome
```

---

## 9. 关键配置速查

### 9.1 告警阈值（kalman_engine.py）

```python
URGENT_LOW   = 3.0    # mmol/L → CRITICAL（立刻就医）
HYPO_LOWER   = 3.9    # mmol/L → WARNING（低血糖）
HYPER_UPPER  = 10.0   # mmol/L → WARNING（高血糖）
URGENT_HIGH  = 13.9   # mmol/L → CRITICAL（立刻就医）
```

### 9.2 滤波器切换阈值（kalman_engine.py）

```python
# 变化率 < 0.3 mmol/L/5min → KF（稳定）
# event == 'insulin'        → EKF（胰岛素）
# event == 'meal' 且 GI>70 → UKF（饭后峰值）
# 变化率 > 0.8             → 强制 UKF
```

### 9.3 食物向量搜索（query_food.py）

```python
DISTANCE_THRESHOLD = 0.85   # 余弦距离阈值，超过则视为无匹配
# 支持语言: 中文（含方言别名），36个地区，18个食物类别
# 数据量: 501种中国食物
```

### 9.4 ISF 校准权重（api.py）

```python
new_ISF = 0.7 * old_ISF + 0.3 * measured_ISF
# 新测值权重 30%，避免单次异常值剧烈影响
```

### 9.5 食物风险评分公式（api.py）

```python
base = (GL / 50.0) * 100
- fiber_discount   = min(fiber_g * 2,    15)
- protein_discount = min(protein_g * 0.5, 10)
- fat_discount     = min(fat_g * 0.3,     5)
+ time_modifier    = 0(早餐) ~ +10(深夜)
risk = clamp(result, 0, 100)
```

### 9.6 全局配置文件

```bash
# OpenClaw 配置（API Key / 技能路径）
cat ~/.openclaw/openclaw.json

# 后端环境变量
cat /Users/zwx/sugarclaw-app/backend/.env

# Kalman 校准参数（热更新，无需重启）
cat ~/.openclaw/workspace/skills/kalman-filter-engine/data/calibrated_params.json
```

---

## 10. API 接口速查

### 10.1 核心接口（27个路由总览）

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/cases` | 获取5个内置测试案例 |
| POST | `/api/analyze` | 血糖+食物 → 完整分析（Kalman+AI建议） |
| POST | `/api/replay` | 回放内置案例 |
| GET | `/api/replay/stream/{case_id}` | SSE 流式回放 |
| POST | `/api/scale/risk` | 食物名 → 风险分数(0-100) |
| POST | `/api/scale/balance` | 食物名 → 反制策略列表 |
| POST | `/api/scale/advice` | 刷新 AI 建议 |
| POST | `/api/scale/add_exercise` | 添加运动干预方案 |
| POST | `/api/scale/add_food_counter` | 添加食物反制方案 |
| POST | `/api/chat` | SSE 流式 DeepSeek R1 对话 |
| GET | `/api/user/profile` | 获取用户档案 |
| PUT | `/api/user/profile` | 更新用户档案 |
| POST | `/api/user/calibrate_isf` | 校准胰岛素敏感因子 |
| POST | `/api/glucose/log` | 保存手动血糖记录 |
| GET | `/api/glucose/log` | 获取血糖日志历史 |
| DELETE | `/api/glucose/log/{entry_id}` | 删除血糖记录 |
| POST | `/api/cgm/simulate` | 生成24小时模拟CGM数据 |
| GET | `/api/cgm/stream/{session_id}` | SSE 流式CGM数据 |
| GET | `/api/cgm/history` | 获取最近CGM读数 |
| GET | `/api/cgm/sessions` | 列出所有CGM会话 |
| POST | `/api/pubmed/search` | PubMed 文献检索 |
| GET | `/api/pubmed/history` | 获取搜索历史 |

### 10.2 主要接口示例

```bash
BASE=http://localhost:8082

# 健康检查
curl $BASE/api/health

# 血糖分析（完整）
curl -X POST $BASE/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "readings": [6.2, 6.5, 6.8, 7.3, 7.9, 8.5],
    "event": "meal",
    "food": "热干面",
    "gi": 82
  }'

# 食物风险评分
curl -X POST $BASE/api/scale/risk \
  -H "Content-Type: application/json" \
  -d '{"food_name": "热干面"}'

# 反制策略
curl -X POST $BASE/api/scale/balance \
  -H "Content-Type: application/json" \
  -d '{"food_name": "热干面"}'

# 更新用户档案
curl -X PUT $BASE/api/user/profile \
  -H "Content-Type: application/json" \
  -d '{"name": "张三", "age": 45, "diabetes_type": "T2DM", "isf": 2.5}'

# ISF 校准（注射4单位，血糖从14降到8）
curl -X POST $BASE/api/user/calibrate_isf \
  -H "Content-Type: application/json" \
  -d '{"before_glucose": 14.0, "dose": 4.0, "after_glucose": 8.0}'

# 模拟CGM数据
curl -X POST $BASE/api/cgm/simulate \
  -H "Content-Type: application/json" \
  -d '{"hours": 24}'

# PubMed 搜索
curl -X POST $BASE/api/pubmed/search \
  -H "Content-Type: application/json" \
  -d '{"query": "SGLT2 inhibitors", "mode": "therapy", "max_results": 5}'
```

---

*最后更新: 2026-03-15 | SugarClaw v2026.3*
