# SugarClaw 项目评估报告
> 生成时间：2026-03-30
> 测试环境：生产服务器 https://sugarclaw.top（阿里云 ECS 北京，39.103.75.192）

---

## 一、项目概览

SugarClaw 是一个面向糖尿病患者的 AI 代谢健康教练，核心能力：

- **血糖预测**：卡尔曼滤波（KF/EKF/UKF）三态自适应，预测未来 30 分钟血糖趋势
- **对冲天平**：输入食物 → 计算血糖风险 → 生成食物/运动/药物对冲方案
- **AI 对话**：DeepSeek 大模型 + 糖尿病权威指南 + 用户档案，流式输出
- **文献检索**：PubMed 实时检索，循证医学支撑建议
- **CGM 模拟**：连续血糖监测数据流式回放

**技术栈**：FastAPI + SQLite + ChromaDB + Flutter + DeepSeek API + Nginx + Let's Encrypt

---

## 二、接口测试结果

| 接口 | 状态 | 说明 |
|------|------|------|
| `GET /api/health` | ✅ 正常 | 返回 `{"status":"ok"}` |
| `POST /api/analyze` | ✅ 正常 | UKF 滤波，返回预测点+告警 |
| `GET /api/cases` | ✅ 正常 | 5 个内置案例 |
| `POST /api/scale/risk` | ✅ 正常（修复后）| 食物风险评估，热干面 = 74.1/high |
| `POST /api/scale/balance` | ✅ 正常 | 返回 13 条对冲方案 |
| `POST /api/chat` | ✅ 正常 | DeepSeek 流式对话 |
| `POST /api/pubmed/search` | ✅ 正常 | 返回 16345 条相关文献 |
| `POST /api/cgm/simulate` | ✅ 正常 | CGM 模拟会话创建成功 |
| `GET /api/user/profile` | ✅ 正常 | 用户档案返回（待填写） |
| `POST /api/user/calibrate_isf` | ❌ 422 错误 | 请求参数格式不匹配 |
| HTTPS / SSL | ✅ 正常 | Let's Encrypt 证书，有效至 2026-06-28 |

---

## 三、发现的问题

### 3.1 已在本次修复的问题

**问题 1：食物查询 500 错误**
- 原因：`api.py` 中 `from query_food import exact_match` 无法找到模块，因为服务器上 `query_food.py` 未在 Python 路径中
- 修复：在 `backend/` 目录创建软链接指向 `~/.openclaw/workspace/skills/food-gi-rag/scripts/query_food.py`
- 影响范围：`/api/scale/risk`、`/api/scale/balance` 全部 500 失败

**问题 2：HTTPS 未配置**
- 原因：nginx 只监听 80 端口，微信小程序强制要求 HTTPS
- 修复：运行 certbot，自动配置 SSL 并更新 nginx 配置
- 影响范围：微信小程序所有接口无法访问

**问题 3：DNS 指向错误**
- 原因：服务器换 IP 后 DNS A 记录未更新，仍指向旧 IP `47.97.126.240`
- 修复：在阿里云云解析 DNS 控制台将 A 记录改为 `39.103.75.192`
- 影响范围：`sugarclaw.top` 域名完全不可访问

**问题 4：后端未启动**
- 原因：新服务器无 systemd 服务，重启后 uvicorn 不会自动启动
- 修复（临时）：手动 nohup 启动
- 状态：**未根治**（见待修复问题）

### 3.2 待修复问题

**问题 A：ISF 校准接口 422 错误**
```
POST /api/user/calibrate_isf → HTTP 422
请求体：{"recent_readings": [12.0, 10.5, 9.0], "recent_doses": [4.0], "carbs": 0}
```
Pydantic 参数校验失败，需对照 `CalibrateISFRequest` 模型确认字段名称。

**问题 B：后端无开机自启**
服务器重启后 sugarclaw 不会自动启动，需配置 systemd 服务。
```bash
# 临时解决：手动启动
cd ~/SugarClaw/backend && nohup .venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000 > /var/log/sugarclaw.log 2>&1 &
```

**问题 C：用户档案为空**
数据库中用户档案全部为默认值（姓名"默认用户"，年龄/体重/ISF 均为 0），影响 Chat 的个性化建议质量。

**问题 D：服务器公网遭扫描**
日志中出现大量 `/dashboard`、`/billing`、`/checkout`、`/admin` 等路径的探测请求（来自爬虫/黑客扫描），建议配置 nginx 速率限制或防火墙规则。

---

## 四、改进建议

### 4.1 高优先级（影响可用性）

**1. 配置 systemd 开机自启**
```bash
# 在服务器执行
cat > /etc/systemd/system/sugarclaw.service << EOF
[Unit]
Description=SugarClaw Backend
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/SugarClaw/backend
ExecStart=/root/SugarClaw/backend/.venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=append:/var/log/sugarclaw.log
StandardError=append:/var/log/sugarclaw.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable sugarclaw
systemctl start sugarclaw
```

**2. 修复 ISF 校准接口**
需检查 `api.py` 中 `CalibrateISFRequest` 模型的字段定义，确认参数名称和类型。

**3. 引导用户填写档案**
用户档案为空时，Chat 无法做个性化建议。前端应在首次启动时引导用户填写姓名、糖尿病类型、ISF、体重等信息。

### 4.2 中优先级（提升体验）

**4. 对冲天平方案排序优化**
当前返回 13 条方案，运动对冲排在食物对冲前面，但用户可能更想先看食物搭配。建议按 `type` 分组显示：食物 → 运动 → 药物。

**5. 食物库扩充**
当前 501 种食物，缺少很多区域性食物（如川菜、东北菜）。建议：
- 开放用户贡献食物数据
- 对未命中的食物调用 DeepSeek 估算后自动入库（已有 `_deepseek_food_lookup` 但需验证是否触发）

**6. Chat 历史持久化**
当前 Chat 无跨会话记忆，每次重新打开都要重新说明情况。建议将对话历史存入 SQLite。

**7. nginx 安全加固**
```nginx
# 限制请求频率
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;
limit_req zone=api burst=10 nodelay;

# 拦截常见扫描路径
location ~* ^/(admin|dashboard|billing|checkout|shop|cart) {
    return 404;
}
```

### 4.3 低优先级（长期规划）

**8. 多用户支持**
当前系统硬编码 `user_id=1`，需添加注册/登录/JWT 鉴权才能支持多用户。

**9. 真实 BLE/CGM 设备接入**
`ble_cgm_parser.py` 已实现协议解析，但后端未暴露 BLE 连接接口，目前只能模拟数据。

**10. 前端离线缓存**
微信小程序在弱网下体验差，建议对食物库和用户档案做本地缓存。

**11. 数据导出**
血糖日志、CGM 历史目前只能通过 API 查询，缺少 CSV/PDF 导出功能，不利于与医生沟通。

---

## 五、架构总结

### 5.1 核心数据流

```
用户输入食物/血糖
    │
    ▼
FastAPI 后端（Python 3.10）
    ├── 食物查询：ChromaDB 向量搜索（501种食物）→ 精确匹配优先
    ├── 血糖分析：KF/EKF/UKF 自动选择 → 30分钟预测 + 三级告警
    ├── AI 对话：SOUL.md + USER.md + 指南库 → DeepSeek 流式输出
    └── 文献支撑：PubMed NCBI API → 循证依据
    │
    ▼
SQLite（5张表）
    users / food_cache / cgm_readings / glucose_log / search_history
    │
    ▼
Nginx 反向代理 → HTTPS → 微信小程序 / Flutter 前端
```

### 5.2 技能模块依赖关系

```
api.py
  ├── import query_food（直接 import，需在 sys.path 中）
  ├── subprocess: kalman_engine.py（用 .venv/bin/python3 调用）
  ├── subprocess: query_food.py --json（用 food-gi-rag/.venv/bin/python3 调用）
  └── subprocess: pubmed_researcher.py（系统 python3 调用）
```

**注意**：api.py 对 `query_food` 有两种调用方式，一种是直接 import，一种是 subprocess，需保持一致。

### 5.3 服务器文件结构

```
/root/
├── SugarClaw/
│   └── backend/
│       ├── api.py
│       ├── query_food.py → (软链接) ~/.openclaw/workspace/skills/food-gi-rag/scripts/query_food.py
│       ├── database.py
│       ├── guidelines.py
│       ├── .venv/          # Python 虚拟环境
│       └── sugarclaw.db    # SQLite 数据库
└── .openclaw/
    └── workspace/
        ├── SOUL.md          # AI 人格配置
        ├── USER.md          # 用户画像
        ├── AGENTS.md        # 多智能体 SOP
        └── skills/
            └── food-gi-rag/
                ├── data/foods_500.json   # 食物库
                ├── scripts/query_food.py # 查询脚本
                └── .venv/bin/python3     # 软链接 → 系统 python3
```

---

## 六、快速测试命令

```bash
BASE="https://sugarclaw.top"

# 健康检查
curl $BASE/api/health

# 食物风险评估
curl -X POST $BASE/api/scale/risk \
  -H "Content-Type: application/json" \
  -d '{"food_name": "热干面"}'

# 血糖分析
curl -X POST $BASE/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"readings": [6.2, 6.5, 6.8, 7.3, 7.9, 8.5], "event": "meal", "food": "热干面", "gi": 82}'

# AI 对话
curl -X POST $BASE/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "我吃了热干面，血糖会怎样"}], "stream": false}'

# Swagger UI（需要开放防火墙或本地访问）
# http://39.103.75.192:8000/docs
```

---

## 七、待办清单（优先级排序）

- [ ] **P0** 配置 systemd 开机自启（防止服务器重启后服务掉线）
- [ ] **P0** 修复 ISF 校准接口 422 错误
- [ ] **P1** 引导用户填写档案（提升 Chat 个性化质量）
- [ ] **P1** nginx 限流 + 拦截扫描路径
- [ ] **P2** 对冲方案分组显示（食物 → 运动 → 药物）
- [ ] **P2** Chat 历史持久化
- [ ] **P3** 食物库扩充（区域食物 + 用户贡献）
- [ ] **P3** 数据导出功能（CSV/PDF）
- [ ] **P4** 多用户支持（JWT 鉴权）
- [ ] **P4** 真实 BLE/CGM 设备接入
