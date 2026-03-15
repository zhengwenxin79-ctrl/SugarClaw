#!/usr/bin/env python3
"""
BLE CGM 数据解析器 — 解析蓝牙低功耗连续血糖监测数据

支持 Bluetooth SIG GATT Glucose Service (UUID 0x1808) 的
CGM Measurement Characteristic (0x2AA7) 数据解析。

用法:
  VENV=~/.openclaw/workspace/skills/food-gi-rag/.venv/bin/python3

  # 解析 BLE hex 通知数据
  $VENV scripts/ble_cgm_parser.py --hex "1A00B4000A00"

  # 解析 BLE 二进制捕获文件
  $VENV scripts/ble_cgm_parser.py --file capture.bin

  # 解析 CGM app 导出 CSV
  $VENV scripts/ble_cgm_parser.py --csv export.csv

  # 生成 24h 演示数据
  $VENV scripts/ble_cgm_parser.py --demo

  # 输出为 kalman_engine.py --readings 格式
  $VENV scripts/ble_cgm_parser.py --demo --to-readings

  # 追加到 cgm_buffer.json
  $VENV scripts/ble_cgm_parser.py --demo --to-buffer memory/cgm_buffer.json

  # 查看 buffer 状态
  $VENV scripts/ble_cgm_parser.py --buffer-status memory/cgm_buffer.json

  # 从 buffer 提取最近 N 个读数
  $VENV scripts/ble_cgm_parser.py --buffer-window memory/cgm_buffer.json --last 12
"""

import argparse
import json
import math
import os
import struct
import sys
from datetime import datetime, timedelta

import numpy as np

# ─────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────
MGDL_TO_MMOL = 1.0 / 18.0
MMOL_TO_MGDL = 18.0

# BLE CGM Measurement Flags (bit field)
FLAG_TREND_INFO_PRESENT   = 0x01
FLAG_QUALITY_PRESENT      = 0x02
FLAG_SENSOR_STATUS_PRESENT = 0x04
FLAG_CAL_TEMP_PRESENT     = 0x08
FLAG_CAL_STATUS_PRESENT   = 0x10

# Sensor status annunciation bits
SENSOR_STATUS = {
    0x0001: "Session stopped",
    0x0002: "Device battery low",
    0x0004: "Sensor type incorrect",
    0x0008: "Sensor malfunction",
    0x0010: "Device specific alert",
    0x0020: "General device fault",
    0x0100: "Time sync required",
    0x0200: "Calibration not allowed",
    0x0400: "Calibration recommended",
    0x0800: "Calibration required",
    0x1000: "Sensor temperature too high",
    0x2000: "Sensor temperature too low",
    0x4000: "Result lower than patient low",
    0x8000: "Result higher than patient high",
}


# ─────────────────────────────────────────────
# SFLOAT 解析 (IEEE 11073 16-bit float)
# ─────────────────────────────────────────────
def parse_sfloat(raw: int) -> float:
    """Parse IEEE 11073 SFLOAT (16-bit) to Python float.

    Format: 4-bit exponent (signed) + 12-bit mantissa (signed).
    Special values: NaN, NRes, +INFINITY, -INFINITY, Reserved.
    """
    # Special values
    if raw == 0x07FF:
        return float('nan')   # NaN
    if raw == 0x0800:
        return float('nan')   # NRes
    if raw == 0x07FE:
        return float('inf')   # +INFINITY
    if raw == 0x0802:
        return float('-inf')  # -INFINITY
    if raw == 0x0801:
        return float('nan')   # Reserved

    exponent = raw >> 12
    mantissa = raw & 0x0FFF

    # Sign-extend exponent (4-bit signed)
    if exponent >= 8:
        exponent -= 16

    # Sign-extend mantissa (12-bit signed)
    if mantissa >= 2048:
        mantissa -= 4096

    return mantissa * (10.0 ** exponent)


# ─────────────────────────────────────────────
# BLE CGM Measurement 解析
# ─────────────────────────────────────────────
def parse_cgm_measurement(data: bytes) -> dict:
    """Parse a CGM Measurement characteristic (0x2AA7) notification.

    Minimum payload: 1 (flags) + 2 (glucose SFLOAT) + 2 (time offset) = 5 bytes.
    Optional trailing fields depend on flags.

    Returns dict with parsed fields.
    """
    if len(data) < 5:
        raise ValueError(f"CGM measurement too short: {len(data)} bytes (min 5)")

    offset = 0

    # --- Size (1 byte, per GATT spec the first byte is size) ---
    size = data[offset]
    offset += 1

    # --- Flags (1 byte) ---
    flags = data[offset]
    offset += 1

    # --- Glucose Concentration (2 bytes, SFLOAT) ---
    glucose_raw = struct.unpack_from('<H', data, offset)[0]
    offset += 2
    glucose_mgdl = parse_sfloat(glucose_raw)
    glucose_mmol = glucose_mgdl * MGDL_TO_MMOL

    # --- Time Offset (2 bytes, uint16, minutes from session start) ---
    time_offset_min = struct.unpack_from('<H', data, offset)[0]
    offset += 2

    result = {
        "size": size,
        "flags": flags,
        "glucose_mgdl": round(glucose_mgdl, 1),
        "glucose_mmol": round(glucose_mmol, 2),
        "time_offset_min": time_offset_min,
    }

    # --- Optional: Sensor Status Annunciation (3 bytes) ---
    if flags & FLAG_SENSOR_STATUS_PRESENT and offset + 2 <= len(data):
        # Annunciation is a 24-bit field (Octet + uint16)
        status_bytes = data[offset:offset + 3] if offset + 3 <= len(data) else data[offset:offset + 2] + b'\x00'
        status = int.from_bytes(status_bytes[:3], 'little')
        offset += 3
        warnings = [msg for bit, msg in SENSOR_STATUS.items() if status & bit]
        result["sensor_status"] = status
        result["sensor_warnings"] = warnings

    # --- Optional: Trend Info (2 bytes, SFLOAT, mmol/L per min) ---
    if flags & FLAG_TREND_INFO_PRESENT and offset + 2 <= len(data):
        trend_raw = struct.unpack_from('<H', data, offset)[0]
        offset += 2
        trend = parse_sfloat(trend_raw)
        result["trend_mmol_per_min"] = round(trend, 4)

    # --- Optional: Quality (2 bytes, SFLOAT, percentage) ---
    if flags & FLAG_QUALITY_PRESENT and offset + 2 <= len(data):
        quality_raw = struct.unpack_from('<H', data, offset)[0]
        offset += 2
        quality = parse_sfloat(quality_raw)
        result["quality_pct"] = round(quality, 1)

    return result


def parse_hex_string(hex_str: str) -> list:
    """Parse a hex string (one or more concatenated CGM measurements)."""
    hex_str = hex_str.strip().replace(' ', '').replace('0x', '').replace(',', '')
    data = bytes.fromhex(hex_str)
    return parse_binary_data(data)


def parse_binary_data(data: bytes) -> list:
    """Parse binary data containing one or more CGM measurements.

    Each measurement starts with a size byte indicating total length.
    """
    readings = []
    offset = 0
    while offset < len(data):
        if offset >= len(data):
            break
        size = data[offset]
        if size < 5 or offset + size > len(data):
            # Try parsing remaining as single measurement
            try:
                r = parse_cgm_measurement(data[offset:])
                readings.append(r)
            except ValueError:
                pass
            break
        chunk = data[offset:offset + size]
        try:
            r = parse_cgm_measurement(chunk)
            readings.append(r)
        except ValueError as e:
            print(f"Warning: skipping malformed measurement at offset {offset}: {e}",
                  file=sys.stderr)
        offset += size
    return readings


def parse_binary_file(path: str) -> list:
    """Parse a binary BLE capture file."""
    with open(path, 'rb') as f:
        data = f.read()
    return parse_binary_data(data)


# ─────────────────────────────────────────────
# CSV 解析
# ─────────────────────────────────────────────
def parse_csv_file(path: str) -> list:
    """Parse a CSV export from CGM apps.

    Expects columns containing timestamp and glucose values.
    Auto-detects column names: timestamp/time/date, glucose_mg_dl/glucose_mgdl/glucose_mmol_l/glucose_mmol/glucose.
    """
    import csv

    readings = []
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames_lower = {fn.lower().strip(): fn for fn in reader.fieldnames}

        # Detect timestamp column
        ts_col = None
        for candidate in ['timestamp', 'time', 'date', 'datetime', 'device_timestamp',
                          'display_time']:
            if candidate in fieldnames_lower:
                ts_col = fieldnames_lower[candidate]
                break

        # Detect glucose column and unit
        glucose_col = None
        is_mmol = False
        for candidate in ['glucose_mg_dl', 'glucose_mgdl', 'glucose mg/dl',
                          'blood glucose value (mg/dl)', 'historic glucose mg/dl',
                          'scan glucose mg/dl', 'glucose']:
            if candidate in fieldnames_lower:
                glucose_col = fieldnames_lower[candidate]
                is_mmol = False
                break
        if glucose_col is None:
            for candidate in ['glucose_mmol_l', 'glucose_mmol', 'glucose mmol/l',
                              'blood glucose value (mmol/l)', 'historic glucose mmol/l',
                              'scan glucose mmol/l']:
                if candidate in fieldnames_lower:
                    glucose_col = fieldnames_lower[candidate]
                    is_mmol = True
                    break

        if glucose_col is None:
            raise ValueError(
                f"Cannot find glucose column in CSV. Available columns: {list(reader.fieldnames)}"
            )

        # Detect event column (optional)
        event_col = None
        for candidate in ['event', 'notes', 'note', 'event_type']:
            if candidate in fieldnames_lower:
                event_col = fieldnames_lower[candidate]
                break

        for row in reader:
            val_str = row.get(glucose_col, '').strip()
            if not val_str:
                continue
            try:
                val = float(val_str)
            except ValueError:
                continue

            if is_mmol:
                glucose_mmol = round(val, 2)
                glucose_mgdl = round(val * MMOL_TO_MGDL, 1)
            else:
                glucose_mgdl = round(val, 1)
                glucose_mmol = round(val * MGDL_TO_MMOL, 2)

            entry = {
                "glucose_mgdl": glucose_mgdl,
                "glucose_mmol": glucose_mmol,
            }

            if ts_col and row.get(ts_col, '').strip():
                entry["timestamp"] = row[ts_col].strip()

            if event_col and row.get(event_col, '').strip():
                entry["event"] = row[event_col].strip()

            readings.append(entry)

    return readings


# ─────────────────────────────────────────────
# 演示数据生成
# ─────────────────────────────────────────────
def generate_demo_data(seed: int = 42) -> list:
    """Generate 24 hours of realistic CGM data at 5-minute intervals.

    Simulates:
    - Base glucose ~6.0 mmol/L
    - Dawn phenomenon (4:00-6:00 rise)
    - 3 meals with postprandial spikes (breakfast GI=75, lunch GI=60, dinner GI=70)
    - 1 insulin injection (after lunch)
    - Gaussian noise (std=0.3 mmol/L)

    Returns list of 288 data points.
    """
    rng = np.random.default_rng(seed)
    n_points = 288  # 24h * 60min / 5min
    dt = 5  # minutes

    base_glucose = 6.0  # mmol/L
    glucose = np.full(n_points, base_glucose, dtype=float)

    # Time axis
    start_time = datetime(2026, 3, 6, 0, 0, 0)
    times = [start_time + timedelta(minutes=i * dt) for i in range(n_points)]

    # Dawn phenomenon: gradual rise from 4:00 to 6:30 (+1.5 mmol/L)
    for i in range(n_points):
        hour = times[i].hour + times[i].minute / 60.0
        if 4.0 <= hour <= 6.5:
            progress = (hour - 4.0) / 2.5
            glucose[i] += 1.5 * math.sin(progress * math.pi / 2)
        elif 6.5 < hour <= 8.0:
            progress = (hour - 6.5) / 1.5
            glucose[i] += 1.5 * (1 - progress)

    # Meal model: glucose spike after carb intake
    # Parameters: (meal_time_hour, GI, peak_rise_mmol, t_peak_min, t_decay_min)
    meals = [
        (7.5,  75, 4.5, 40, 80),   # Breakfast: GI=75, +4.5 mmol/L
        (12.0, 60, 3.2, 50, 90),   # Lunch: GI=60, +3.2 mmol/L
        (18.5, 70, 3.8, 45, 85),   # Dinner: GI=70, +3.8 mmol/L
    ]
    events = {}

    for meal_hour, gi, peak_rise, t_peak, t_decay in meals:
        meal_min = meal_hour * 60
        meal_idx = int(meal_min / dt)
        meal_name = {7.5: "breakfast", 12.0: "lunch", 18.5: "dinner"}[meal_hour]
        events[meal_idx] = f"meal_{meal_name}_GI{gi}"

        for i in range(n_points):
            t = i * dt - meal_min  # minutes since meal
            if t < 0:
                continue
            if t <= t_peak:
                # Rising phase (quadratic rise)
                progress = t / t_peak
                glucose[i] += peak_rise * (1 - (1 - progress) ** 2)
            elif t <= t_peak + t_decay:
                # Decay phase (exponential decay)
                decay_progress = (t - t_peak) / t_decay
                glucose[i] += peak_rise * math.exp(-2.5 * decay_progress)

    # Insulin injection: after lunch at 12:30, 4 units, ISF ~0.73
    insulin_hour = 12.5
    insulin_min = insulin_hour * 60
    insulin_idx = int(insulin_min / dt)
    events[insulin_idx] = "insulin_4u"
    insulin_dose = 4.0
    isf = 0.73  # mmol/L per unit
    tau_insulin = 77  # minutes (calibrated)

    for i in range(n_points):
        t = i * dt - insulin_min  # minutes since injection
        if t < 0:
            continue
        # Insulin action model: delayed exponential
        action = insulin_dose * isf * (t / tau_insulin) * math.exp(1 - t / tau_insulin)
        glucose[i] -= action

    # Add Gaussian noise
    noise = rng.normal(0, 0.3, n_points)
    glucose += noise

    # Clamp to physiological range
    glucose = np.clip(glucose, 2.2, 22.2)

    # Build output
    readings = []
    for i in range(n_points):
        entry = {
            "timestamp": times[i].isoformat(),
            "glucose_mmol": round(float(glucose[i]), 2),
            "glucose_mgdl": round(float(glucose[i]) * MMOL_TO_MGDL, 1),
        }
        if i in events:
            entry["event"] = events[i]
        readings.append(entry)

    return readings


# ─────────────────────────────────────────────
# Buffer 管理
# ─────────────────────────────────────────────
def load_buffer(path: str) -> list:
    """Load cgm_buffer.json, returning list of readings."""
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        data = json.load(f)
    if isinstance(data, dict) and "readings" in data:
        return data["readings"]
    if isinstance(data, list):
        return data
    return []


def save_buffer(path: str, readings: list):
    """Save readings to cgm_buffer.json."""
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, 'w') as f:
        json.dump({"readings": readings, "updated": datetime.now().isoformat()}, f,
                  indent=2, ensure_ascii=False)


def append_to_buffer(path: str, new_readings: list):
    """Append new readings to cgm_buffer.json."""
    existing = load_buffer(path)
    existing.extend(new_readings)
    save_buffer(path, existing)
    return len(existing)


def buffer_status(path: str) -> dict:
    """Return buffer statistics."""
    readings = load_buffer(path)
    if not readings:
        return {"count": 0, "message": "Buffer is empty"}

    info = {"count": len(readings)}

    # Time range
    timestamps = [r.get("timestamp") for r in readings if r.get("timestamp")]
    if timestamps:
        info["first_timestamp"] = timestamps[0]
        info["last_timestamp"] = timestamps[-1]

    # Latest reading
    last = readings[-1]
    info["latest_glucose_mmol"] = last.get("glucose_mmol")
    info["latest_glucose_mgdl"] = last.get("glucose_mgdl")

    # Stats
    mmol_values = [r["glucose_mmol"] for r in readings if "glucose_mmol" in r]
    if mmol_values:
        info["mean_mmol"] = round(float(np.mean(mmol_values)), 2)
        info["std_mmol"] = round(float(np.std(mmol_values)), 2)
        info["min_mmol"] = round(min(mmol_values), 2)
        info["max_mmol"] = round(max(mmol_values), 2)

    return info


def buffer_window(path: str, last_n: int) -> list:
    """Extract last N readings from buffer."""
    readings = load_buffer(path)
    return readings[-last_n:]


# ─────────────────────────────────────────────
# 输出格式化
# ─────────────────────────────────────────────
def format_reading_human(r: dict) -> str:
    """Format a single reading for human display."""
    parts = []
    if "timestamp" in r:
        parts.append(f"[{r['timestamp']}]")
    parts.append(f"{r.get('glucose_mmol', '?')} mmol/L")
    parts.append(f"({r.get('glucose_mgdl', '?')} mg/dL)")
    if "time_offset_min" in r:
        parts.append(f"T+{r['time_offset_min']}min")
    if "event" in r:
        parts.append(f"<{r['event']}>")
    if "trend_mmol_per_min" in r:
        trend = r["trend_mmol_per_min"]
        arrow = "→" if abs(trend) < 0.01 else ("↑" if trend > 0.05 else
                "↓" if trend < -0.05 else ("↗" if trend > 0 else "↘"))
        parts.append(f"trend: {arrow} {trend:+.3f}/min")
    if "sensor_warnings" in r and r["sensor_warnings"]:
        parts.append(f"WARN: {', '.join(r['sensor_warnings'])}")
    if "quality_pct" in r:
        parts.append(f"Q:{r['quality_pct']}%")
    return "  ".join(parts)


def readings_to_kalman_string(readings: list) -> str:
    """Convert readings list to space-separated mmol/L values for --readings."""
    values = [str(r["glucose_mmol"]) for r in readings if "glucose_mmol" in r]
    return " ".join(values)


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ble_cgm_parser",
        description=(
            "BLE CGM 数据解析器 — 解析蓝牙低功耗连续血糖监测数据\n"
            "Bluetooth SIG GATT Glucose Service (UUID 0x1808)\n"
            "CGM Measurement Characteristic (0x2AA7)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  # 解析 BLE hex 通知\n"
            "  %(prog)s --hex \"0600B4000A00\"\n\n"
            "  # 生成 24h 演示数据并输出为 kalman_engine.py --readings 格式\n"
            "  %(prog)s --demo --to-readings\n\n"
            "  # 追加演示数据到 buffer 文件\n"
            "  %(prog)s --demo --to-buffer memory/cgm_buffer.json\n\n"
            "  # 查看 buffer 状态\n"
            "  %(prog)s --buffer-status memory/cgm_buffer.json\n\n"
            "  # 提取最近 12 个读数用于卡尔曼滤波\n"
            "  %(prog)s --buffer-window memory/cgm_buffer.json --last 12 --to-readings"
        ),
    )

    # Input sources (mutually exclusive)
    input_group = p.add_argument_group("数据输入 (选择一种)")
    input_group.add_argument("--hex", type=str, metavar="HEX",
                             help="BLE 通知原始 hex 字符串 (如 \"0600B4000A00\")")
    input_group.add_argument("--file", type=str, metavar="PATH",
                             help="BLE 捕获二进制文件")
    input_group.add_argument("--csv", type=str, metavar="PATH",
                             help="CGM app 导出的 CSV 文件")
    input_group.add_argument("--demo", action="store_true",
                             help="生成 24h 演示 CGM 数据 (288 个 5 分钟间隔的读数)")
    input_group.add_argument("--demo-seed", type=int, default=42,
                             help="演示数据随机种子 (默认 42)")

    # Output format
    out_group = p.add_argument_group("输出格式")
    out_group.add_argument("--json", action="store_true", dest="output_json",
                           help="JSON 结构化输出")
    out_group.add_argument("--to-readings", action="store_true",
                           help="输出为空格分隔的 mmol/L 值 (用于 kalman_engine.py --readings)")
    out_group.add_argument("--to-buffer", type=str, metavar="PATH",
                           help="追加读数到 cgm_buffer.json 文件")

    # Buffer management
    buf_group = p.add_argument_group("Buffer 管理")
    buf_group.add_argument("--buffer-status", type=str, metavar="PATH",
                           help="显示 cgm_buffer.json 统计信息")
    buf_group.add_argument("--buffer-window", type=str, metavar="PATH",
                           help="从 buffer 提取最近 N 个读数")
    buf_group.add_argument("--last", type=int, default=12,
                           help="与 --buffer-window 配合，提取最近 N 个读数 (默认 12)")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    # ── Buffer management (independent operations) ──
    if args.buffer_status:
        info = buffer_status(args.buffer_status)
        if args.output_json:
            print(json.dumps(info, indent=2, ensure_ascii=False))
        else:
            print(f"=== CGM Buffer Status: {args.buffer_status} ===")
            for k, v in info.items():
                print(f"  {k}: {v}")
        return

    if args.buffer_window:
        readings = buffer_window(args.buffer_window, args.last)
        if not readings:
            print("Buffer is empty or file not found.", file=sys.stderr)
            sys.exit(1)
        if args.to_readings:
            print(readings_to_kalman_string(readings))
        elif args.output_json:
            print(json.dumps(readings, indent=2, ensure_ascii=False))
        else:
            for r in readings:
                print(format_reading_human(r))
        return

    # ── Parse input ──
    readings = []

    if args.hex:
        readings = parse_hex_string(args.hex)
    elif args.file:
        if not os.path.exists(args.file):
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        readings = parse_binary_file(args.file)
    elif args.csv:
        if not os.path.exists(args.csv):
            print(f"Error: file not found: {args.csv}", file=sys.stderr)
            sys.exit(1)
        readings = parse_csv_file(args.csv)
    elif args.demo:
        readings = generate_demo_data(seed=args.demo_seed)
    else:
        parser.print_help()
        sys.exit(1)

    if not readings:
        print("No readings parsed.", file=sys.stderr)
        sys.exit(1)

    # ── Append to buffer if requested ──
    if args.to_buffer:
        total = append_to_buffer(args.to_buffer, readings)
        print(f"Appended {len(readings)} readings to {args.to_buffer} (total: {total})",
              file=sys.stderr)

    # ── Output ──
    if args.to_readings:
        print(readings_to_kalman_string(readings))
    elif args.output_json:
        print(json.dumps(readings, indent=2, ensure_ascii=False))
    else:
        print(f"=== Parsed {len(readings)} CGM readings ===")
        # For demo data (288 points), show summary + first/last few
        if len(readings) > 20:
            for r in readings[:5]:
                print(format_reading_human(r))
            print(f"  ... ({len(readings) - 10} more readings) ...")
            for r in readings[-5:]:
                print(format_reading_human(r))
            # Summary stats
            mmol_vals = [r["glucose_mmol"] for r in readings]
            events = [r for r in readings if "event" in r]
            print(f"\nSummary:")
            print(f"  Mean: {np.mean(mmol_vals):.2f} mmol/L  "
                  f"Std: {np.std(mmol_vals):.2f}  "
                  f"Range: {min(mmol_vals):.2f} - {max(mmol_vals):.2f} mmol/L")
            print(f"  Events: {len(events)}")
            for e in events:
                print(f"    [{e['timestamp']}] {e['event']}  "
                      f"glucose={e['glucose_mmol']} mmol/L")
        else:
            for r in readings:
                print(format_reading_human(r))


if __name__ == "__main__":
    main()
