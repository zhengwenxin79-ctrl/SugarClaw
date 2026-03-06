#!/usr/bin/env python3
"""
SugarClaw CGM 数据回放器
从真实上海 T1DM/T2DM 数据集中读取患者 CGM 数据，
以可控速度回放到 cgm_buffer.json，模拟实时 CGM 数据流。

每次写入最近 12 个读数（1 小时窗口），供 kalman_engine.py --input 消费。
回放完成后自动调用 kalman_engine.py 进行预测。

用法:
  # 默认：每 2 秒推送一个读数（原始间隔 15 分钟压缩到 2 秒）
  python3 cgm_replay.py --file /path/to/patient.xlsx

  # 指定回放速度（秒/读数）
  python3 cgm_replay.py --file /path/to/patient.xlsx --interval 1

  # 从第 100 个读数开始回放
  python3 cgm_replay.py --file /path/to/patient.xlsx --start 100

  # 只回放，不调用 kalman_engine
  python3 cgm_replay.py --file /path/to/patient.xlsx --no-predict
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_PATH = os.path.join(SCRIPT_DIR, "kalman_engine.py")
BUFFER_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "memory")
BUFFER_PATH = os.path.join(BUFFER_DIR, "cgm_buffer.json")
WINDOW_SIZE = 12  # 保留最近 12 个读数（1 小时窗口，每 5 分钟一个）


def load_cgm_from_xlsx(path):
    """从 xlsx 文件提取 CGM 读数，转换为 mmol/L。"""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active
    readings = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        ts = row[0]
        cgm = row[1]
        if ts is None or cgm is None:
            continue
        if not isinstance(ts, datetime):
            continue
        mmol = round(float(cgm) / 18.0, 2)
        readings.append({
            "timestamp": ts.isoformat(),
            "glucose_mmol": mmol,
        })
    wb.close()
    return readings


def load_cgm_from_xls(path):
    """从 xls 文件提取 CGM 读数。"""
    import xlrd
    wb = xlrd.open_workbook(path)
    ws = wb.sheet_by_index(0)
    readings = []
    for r in range(1, ws.nrows):
        if ws.cell_type(r, 0) != 3:
            continue
        try:
            ts_tuple = xlrd.xldate_as_tuple(ws.cell_value(r, 0), wb.datemode)
            ts = datetime(*ts_tuple)
        except Exception:
            continue
        cgm = ws.cell_value(r, 1) if ws.cell_type(r, 1) == 2 else None
        if cgm is None:
            continue
        mmol = round(float(cgm) / 18.0, 2)
        readings.append({
            "timestamp": ts.isoformat(),
            "glucose_mmol": mmol,
        })
    return readings


def load_cgm(path):
    if path.endswith(".xlsx"):
        return load_cgm_from_xlsx(path)
    elif path.endswith(".xls"):
        return load_cgm_from_xls(path)
    elif path.endswith(".json"):
        with open(path) as f:
            data = json.load(f)
        if "all_readings" in data:
            return data["all_readings"]
        return data.get("readings", [])
    else:
        print(f"[ERROR] 不支持的文件格式: {path}")
        sys.exit(1)


def write_buffer(window, source_file):
    """写入 cgm_buffer.json，格式兼容 kalman_engine.py --input。"""
    os.makedirs(BUFFER_DIR, exist_ok=True)
    buf = {
        "source": os.path.basename(source_file),
        "updated_at": datetime.now().isoformat(),
        "window_size": len(window),
        "readings": [r["glucose_mmol"] for r in window],
        "timestamps": [r["timestamp"] for r in window],
    }
    with open(BUFFER_PATH, "w") as f:
        json.dump(buf, f, indent=2, ensure_ascii=False)


def run_prediction(python_path):
    """调用 kalman_engine.py 对当前 buffer 进行预测。"""
    try:
        result = subprocess.run(
            [python_path, ENGINE_PATH, "--input", BUFFER_PATH],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"[predict error] {e}"


def main():
    parser = argparse.ArgumentParser(
        description="SugarClaw CGM 数据回放器 — 用真实数据模拟实时 CGM 流"
    )
    parser.add_argument(
        "--file", required=True,
        help="患者数据文件路径 (.xlsx / .xls / .json)"
    )
    parser.add_argument(
        "--interval", type=float, default=2.0,
        help="回放间隔（秒/读数，默认 2.0）"
    )
    parser.add_argument(
        "--start", type=int, default=0,
        help="从第 N 个读数开始回放（默认 0）"
    )
    parser.add_argument(
        "--no-predict", action="store_true",
        help="只回放数据，不调用 kalman_engine 预测"
    )
    args = parser.parse_args()

    # 加载数据
    readings = load_cgm(args.file)
    if not readings:
        print("[ERROR] 未提取到任何 CGM 读数")
        sys.exit(1)

    total = len(readings)
    start = max(0, min(args.start, total - 1))
    python_path = sys.executable

    print(f"{'=' * 58}")
    print(f"  SugarClaw CGM Replay — Real Patient Data")
    print(f"{'=' * 58}")
    print(f"  Source : {os.path.basename(args.file)}")
    print(f"  Total  : {total} readings")
    print(f"  Range  : {readings[0]['timestamp']}")
    print(f"         ~ {readings[-1]['timestamp']}")
    glucose_vals = [r["glucose_mmol"] for r in readings]
    print(f"  Glucose: {min(glucose_vals)} ~ {max(glucose_vals)} mmol/L")
    print(f"  Start  : index {start}")
    print(f"  Speed  : 1 reading / {args.interval}s")
    print(f"  Predict: {'OFF' if args.no_predict else 'ON'}")
    print(f"  Buffer : {BUFFER_PATH}")
    print(f"{'=' * 58}")
    print()

    # 回放循环
    for i in range(start, total):
        r = readings[i]
        # 维护滑动窗口
        window_start = max(0, i - WINDOW_SIZE + 1)
        window = readings[window_start:i + 1]

        # 写入 buffer
        write_buffer(window, args.file)

        # 显示当前状态
        ts = r.get("timestamp", "?")
        gl = r["glucose_mmol"]

        # 简易趋势箭头
        if len(window) >= 2:
            delta = gl - window[-2]["glucose_mmol"]
            if delta > 0.5:
                arrow = "^^"
            elif delta > 0.2:
                arrow = "^"
            elif delta < -0.5:
                arrow = "vv"
            elif delta < -0.2:
                arrow = "v"
            else:
                arrow = "--"
        else:
            arrow = "--"

        status = ""
        if gl < 3.0:
            status = " !! URGENT LOW"
        elif gl < 3.9:
            status = " ! LOW"
        elif gl > 13.9:
            status = " !! URGENT HIGH"
        elif gl > 10.0:
            status = " ! HIGH"

        print(
            f"[{i+1:>4}/{total}] {ts}  "
            f"{gl:>5.1f} mmol/L {arrow}{status}"
        )

        # 运行预测（每 3 个读数预测一次，约 15 分钟间隔）
        if not args.no_predict and len(window) >= 6 and i % 3 == 0:
            print(f"  --- KF Prediction ---")
            output = run_prediction(python_path)
            # 只打印关键行
            for line in output.split("\n"):
                if any(k in line for k in [
                    "当前血糖", "滤波器", "mmol/L", "预警",
                    "CRITICAL", "WARNING", "PREDICTIVE",
                    "+5min", "+10min", "+15min", "+20min", "+25min", "+30min",
                ]):
                    print(f"  {line}")
            print()

        if i < total - 1:
            time.sleep(args.interval)

    print(f"\n{'=' * 58}")
    print(f"  Replay complete. {total - start} readings played.")
    print(f"{'=' * 58}")


if __name__ == "__main__":
    main()
