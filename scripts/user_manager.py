#!/usr/bin/env python3
"""
SugarClaw 用户档案管理器 (user_manager.py)

功能:
  1. 从 Mock Persona 加载测试画像 (开发期)
  2. 从 JSON/表单数据生成 USER.md (产品期 Onboarding)
  3. 动态更新单个参数 (Agent 对话收集 / 自适应校准)
  4. 解析 USER.md 为结构化 dict (供 kalman_engine 等读取)

用法:
  # 切换到测试画像
  python3 user_manager.py --load-mock T2DM_foodie

  # 从 JSON 生成 USER.md
  python3 user_manager.py --from-json '{"diabetes_type":"T2DM","isf":0.73}'

  # 更新单个字段 (Agent 对话收集)
  python3 user_manager.py --update allergies "乳糖不耐受"

  # 自适应参数覆写 (RL 闭环)
  python3 user_manager.py --calibrate-isf 1.2

  # 解析当前 USER.md 为 JSON
  python3 user_manager.py --parse

  # 检查缺失字段 (Onboarding 拦截)
  python3 user_manager.py --check-missing
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_MD_PATH = os.path.join(WORKSPACE, "USER.md")
MOCK_DIR = os.path.join(WORKSPACE, "tests", "mock_users")
BACKUP_DIR = os.path.join(WORKSPACE, "memory", "user_backups")

# --- 字段映射: USER.md 中的 Markdown 标签 → 结构化 key ---
FIELD_MAP = {
    "diabetes_type":   "糖尿病类型",
    "age":             "年龄/性别",
    "height_weight":   "身高/体重",
    "bmi":             "BMI",
    "target_glucose":  "目标血糖区间 (TIR)",
    "hypo_threshold":  "低血糖预警 (L1)",
    "hyper_threshold": "高血糖警戒 (H1)",
    "icr":             "碳水系数 (ICR)",
    "isf":             "胰岛素敏感因子 (ISF)",
    "medications":     "口服药",
    "basal_insulin":   "基础胰岛素",
    "bolus_insulin":   "餐时胰岛素",
    "hypo_frequency":  "低血糖频率",
    "region":          "地域饮食标签",
    "diet_pref":       "饮食习惯",
    "counter_pref":    "对冲偏好",
    "allergies":       "禁忌/过敏",
    "cgm_device":      "CGM 设备",
}

# 关键字段: 为空时触发 Onboarding 拦截
REQUIRED_FIELDS = ["diabetes_type", "isf", "allergies", "region"]


def parse_user_md(path=None):
    """解析 USER.md 为结构化 dict。"""
    path = path or USER_MD_PATH
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    result = {}
    for key, label in FIELD_MAP.items():
        # 匹配 "**标签**: 值" 或 "* **标签**: 值" 格式
        pattern = rf"\*\*{re.escape(label)}\*\*[：:]\s*(.+)"
        match = re.search(pattern, content)
        if match:
            val = match.group(1).strip()
            # 去掉 Markdown 注释和占位符
            if val and not val.startswith("[") and val != "未知":
                result[key] = val

    return result


def extract_isf_numeric(parsed: dict):
    """从解析结果中提取 ISF 数值 (mmol/L per unit)。"""
    isf_str = parsed.get("isf", "")
    match = re.search(r"([\d.]+)", isf_str)
    if match:
        return float(match.group(1))
    return None


def check_missing(parsed: dict) -> list:
    """检查缺失的关键字段，返回需要 Onboarding 收集的字段列表。"""
    missing = []
    for field in REQUIRED_FIELDS:
        if field not in parsed or not parsed[field]:
            missing.append(field)
    return missing


def backup_user_md():
    """备份当前 USER.md。"""
    if not os.path.exists(USER_MD_PATH):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"USER_{ts}.md")
    shutil.copy2(USER_MD_PATH, backup_path)
    return backup_path


def load_mock(persona_name: str):
    """加载测试画像到 USER.md。"""
    # 支持带或不带 .md 后缀
    if not persona_name.endswith(".md"):
        persona_name += ".md"

    mock_path = os.path.join(MOCK_DIR, persona_name)
    if not os.path.exists(mock_path):
        available = [f for f in os.listdir(MOCK_DIR) if f.endswith(".md")]
        print(f"[ERROR] 画像不存在: {persona_name}")
        print(f"可用画像: {', '.join(f.replace('.md','') for f in available)}")
        sys.exit(1)

    backup = backup_user_md()
    if backup:
        print(f"[BACKUP] 已备份当前 USER.md → {backup}")

    shutil.copy2(mock_path, USER_MD_PATH)
    print(f"[OK] 已加载测试画像: {persona_name.replace('.md','')} → USER.md")

    # 验证加载
    parsed = parse_user_md()
    print(f"     糖尿病类型: {parsed.get('diabetes_type', 'N/A')}")
    print(f"     ISF: {parsed.get('isf', 'N/A')}")
    print(f"     地域: {parsed.get('region', 'N/A')}")
    print(f"     过敏: {parsed.get('allergies', 'N/A')}")


def generate_from_json(data: dict):
    """从结构化 JSON 生成 USER.md (Onboarding Flow)。"""
    backup = backup_user_md()
    if backup:
        print(f"[BACKUP] 已备份当前 USER.md → {backup}")

    template = f"""# SugarClaw 用户代谢档案

## 1. 身份与合规锚定
- **用户标识**: {data.get('name', '用户')}
- **科研声明**: 本画像仅用于 SugarClaw 决策引擎的算法调优与技术实证，不作为临床处方依据。

## 2. 基础生理画像
- **糖尿病类型**: {data.get('diabetes_type', '未知')}
- **年龄/性别**: {data.get('age', '未知')}
- **身高/体重**: {data.get('height_weight', '未知')}
- **BMI**: {data.get('bmi', '未知')}
- **目标血糖区间 (TIR)**: {data.get('target_glucose', '3.9 - 10.0 mmol/L')}
- **干预阈值**:
    * **低血糖预警 (L1)**: < {data.get('hypo_threshold', '3.9')} mmol/L
    * **高血糖警戒 (H1)**: > {data.get('hyper_threshold', '13.9')} mmol/L

## 3. 代谢基准参数
- **碳水系数 (ICR)**: {data.get('icr', '需通过动态数据校准')}
- **胰岛素敏感因子 (ISF)**: {data.get('isf', '0.73 mmol/L per unit (基线默认值)')}
- **口服药**: {data.get('medications', '无')}
- **基础胰岛素**: {data.get('basal_insulin', '无')}
- **餐时胰岛素**: {data.get('bolus_insulin', '无')}

## 4. 地域饮食与偏好
- **地域饮食标签**: {data.get('region', '未知')}
- **饮食习惯**: {data.get('diet_pref', '无特定偏好')}
- **对冲偏好**: {data.get('counter_pref', '物理对冲 + 纤维素对冲')}
- **禁忌/过敏**: {data.get('allergies', '无')}

## 5. 硬件与算法配置
- **CGM 设备**: {data.get('cgm_device', '未绑定')}
- **卡尔曼滤波配置**:
    * **预测步长**: 30 分钟
    * **更新频率**: 5 分钟/次
    * **过程噪声协方差 (Q)**: 0.004276 (校准值)

## 6. 参数更新日志
| 日期 | 参数 | 旧值 | 新值 | 来源 |
|---|---|---|---|---|
| {datetime.now().strftime('%Y-%m-%d')} | 初始化 | - | - | Onboarding |
"""

    with open(USER_MD_PATH, "w", encoding="utf-8") as f:
        f.write(template)

    print(f"[OK] USER.md 已生成: {USER_MD_PATH}")


def update_field(field_key: str, new_value: str):
    """更新 USER.md 中的单个字段 (Agent 对话收集场景)。"""
    if field_key not in FIELD_MAP:
        print(f"[ERROR] 未知字段: {field_key}")
        print(f"可用字段: {', '.join(FIELD_MAP.keys())}")
        sys.exit(1)

    if not os.path.exists(USER_MD_PATH):
        print("[ERROR] USER.md 不存在，请先初始化")
        sys.exit(1)

    label = FIELD_MAP[field_key]

    with open(USER_MD_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 读取旧值
    old_match = re.search(rf"\*\*{re.escape(label)}\*\*[：:]\s*(.+)", content)
    old_value = old_match.group(1).strip() if old_match else "无"

    # 替换
    pattern = rf"(\*\*{re.escape(label)}\*\*[：:]\s*)(.+)"
    replacement = rf"\g<1>{new_value}"
    new_content, count = re.subn(pattern, replacement, content)

    if count == 0:
        print(f"[WARN] 未找到字段 '{label}'，无法更新")
        sys.exit(1)

    # 追加更新日志
    log_line = f"| {datetime.now().strftime('%Y-%m-%d %H:%M')} | {label} | {old_value} | {new_value} | Agent 对话收集 |\n"
    if "## 6. 参数更新日志" in new_content:
        # 在表格末尾追加
        new_content = new_content.rstrip() + "\n" + log_line

    backup_user_md()

    with open(USER_MD_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[OK] 已更新: {label}")
    print(f"     旧值: {old_value}")
    print(f"     新值: {new_value}")


def calibrate_isf(new_isf: float):
    """自适应 ISF 校准覆写 (RL 闭环场景)。"""
    if not os.path.exists(USER_MD_PATH):
        print("[ERROR] USER.md 不存在")
        sys.exit(1)

    parsed = parse_user_md()
    old_isf = extract_isf_numeric(parsed)
    old_isf_str = parsed.get("isf", "未知")

    new_isf_str = f"{new_isf:.2f} mmol/L per unit (自适应校准 {datetime.now().strftime('%Y-%m-%d')})"
    update_field("isf", new_isf_str)

    # 同步更新 kalman_engine 的校准参数
    cal_path = os.path.join(WORKSPACE, "skills", "kalman-filter-engine", "data", "calibrated_params.json")
    if os.path.exists(cal_path):
        with open(cal_path, "r", encoding="utf-8") as f:
            cal = json.load(f)
        old_cal_isf = cal.get("ekf_params", {}).get("isf_mmol_per_unit", "N/A")
        cal["ekf_params"]["isf_mmol_per_unit"] = new_isf
        cal["ekf_params"]["isf_source"] = "adaptive_calibration"
        cal["ekf_params"]["isf_updated"] = datetime.now().isoformat()
        with open(cal_path, "w", encoding="utf-8") as f:
            json.dump(cal, f, ensure_ascii=False, indent=2)
        print(f"[SYNC] calibrated_params.json ISF: {old_cal_isf} → {new_isf}")


def main():
    parser = argparse.ArgumentParser(description="SugarClaw 用户档案管理器")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--load-mock", metavar="PERSONA",
                       help="加载测试画像 (如: T2DM_foodie, T1DM_hypo_prone)")
    group.add_argument("--from-json", metavar="JSON",
                       help="从 JSON 字符串生成 USER.md")
    group.add_argument("--from-file", metavar="FILE",
                       help="从 JSON 文件生成 USER.md")
    group.add_argument("--update", nargs=2, metavar=("FIELD", "VALUE"),
                       help="更新单个字段 (如: --update allergies '乳糖不耐受')")
    group.add_argument("--calibrate-isf", type=float, metavar="VALUE",
                       help="自适应 ISF 校准覆写 (如: --calibrate-isf 1.2)")
    group.add_argument("--parse", action="store_true",
                       help="解析当前 USER.md 为 JSON 输出")
    group.add_argument("--check-missing", action="store_true",
                       help="检查缺失的关键字段")
    group.add_argument("--list-mocks", action="store_true",
                       help="列出所有可用测试画像")

    args = parser.parse_args()

    if args.load_mock:
        load_mock(args.load_mock)

    elif args.from_json:
        data = json.loads(args.from_json)
        generate_from_json(data)

    elif args.from_file:
        with open(args.from_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        generate_from_json(data)

    elif args.update:
        update_field(args.update[0], args.update[1])

    elif args.calibrate_isf is not None:
        calibrate_isf(args.calibrate_isf)

    elif args.parse:
        parsed = parse_user_md()
        if not parsed:
            print("[WARN] USER.md 为空或不存在")
            sys.exit(1)
        print(json.dumps(parsed, ensure_ascii=False, indent=2))

    elif args.check_missing:
        parsed = parse_user_md()
        missing = check_missing(parsed)
        if missing:
            labels = [FIELD_MAP[f] for f in missing]
            print(f"[ONBOARDING] 以下关键字段缺失，需要收集:")
            for f, l in zip(missing, labels):
                print(f"  - {l} ({f})")
            sys.exit(1)
        else:
            print("[OK] 所有关键字段已填写")

    elif args.list_mocks:
        if not os.path.exists(MOCK_DIR):
            print("[WARN] 测试画像目录不存在")
            sys.exit(1)
        mocks = [f.replace(".md", "") for f in os.listdir(MOCK_DIR) if f.endswith(".md")]
        print(f"可用测试画像 ({len(mocks)} 个):")
        for m in sorted(mocks):
            mock_path = os.path.join(MOCK_DIR, m + ".md")
            parsed = parse_user_md(mock_path)
            dtype = parsed.get("diabetes_type", "N/A")
            print(f"  {m:30s} [{dtype}]")


if __name__ == "__main__":
    main()
