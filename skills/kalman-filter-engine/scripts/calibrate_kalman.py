#!/usr/bin/env python3
"""
SugarClaw 卡尔曼滤波参数校准器
从上海 T1DM/T2DM CGM 数据集中提取事件段，拟合最优滤波参数。

用法:
  python3 calibrate_kalman.py --data-dir /path/to/diabetes_datasets
  python3 calibrate_kalman.py --data-dir /path/to/diabetes_datasets --type t1dm
  python3 calibrate_kalman.py --data-dir /path/to/diabetes_datasets --output params.json
  python3 calibrate_kalman.py --data-dir /path/to/diabetes_datasets --verbose
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timedelta

import numpy as np

# ─────────────────────────────────────────────
# 数据加载
# ─────────────────────────────────────────────

def load_xlsx(path):
    """加载 .xlsx 文件，返回 (timestamps, cgm_mgdl, events) 列表。"""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        ts = row[0]
        if ts is None or not isinstance(ts, datetime):
            continue
        cgm = row[1]
        cbg = row[2]
        # 饮食
        diet_en = row[4] if row[4] and str(row[4]).strip() not in ('', 'data not available') else None
        diet_cn = row[5] if row[5] and str(row[5]).strip() not in ('', '未记录') else None
        diet = diet_cn or diet_en
        # 胰岛素（合并多列）
        insulin = 0.0
        for ci in [6, 8, 10]:
            if ci < len(row) and row[ci] is not None:
                try:
                    v = float(row[ci])
                    if v > 0:
                        insulin += v
                except (ValueError, TypeError):
                    pass
        # 基础率（CSII basal, col 9）
        basal = 0.0
        if len(row) > 9 and row[9] is not None:
            try:
                basal = float(row[9])
            except (ValueError, TypeError):
                pass
        rows.append({
            'ts': ts,
            'cgm': float(cgm) if cgm is not None else None,
            'cbg': float(cbg) if cbg is not None else None,
            'diet': diet,
            'insulin': insulin,
            'basal': basal,
        })
    wb.close()
    return rows


def load_xls(path):
    """加载 .xls 文件。"""
    import xlrd
    wb = xlrd.open_workbook(path)
    ws = wb.sheet_by_index(0)
    rows = []
    for r in range(1, ws.nrows):
        # 日期
        if ws.cell_type(r, 0) != 3:  # not date
            continue
        try:
            ts_tuple = xlrd.xldate_as_tuple(ws.cell_value(r, 0), wb.datemode)
            ts = datetime(*ts_tuple)
        except Exception:
            continue
        # CGM
        cgm = ws.cell_value(r, 1) if ws.cell_type(r, 1) == 2 else None
        cbg = ws.cell_value(r, 2) if ws.cell_type(r, 2) == 2 else None
        # 饮食
        diet_en = ws.cell_value(r, 4) if ws.cell_type(r, 4) == 1 and ws.cell_value(r, 4).strip() not in ('', 'data not available') else None
        diet_cn = ws.cell_value(r, 5) if ws.cell_type(r, 5) == 1 and ws.cell_value(r, 5).strip() not in ('', '未记录') else None
        diet = diet_cn or diet_en
        # 胰岛素
        insulin = 0.0
        for ci in [6, 8, 10]:
            if ci < ws.ncols and ws.cell_type(r, ci) == 2:
                v = ws.cell_value(r, ci)
                if v > 0:
                    insulin += v
        # 基础率
        basal = 0.0
        if ws.ncols > 9 and ws.cell_type(r, 9) == 2:
            basal = ws.cell_value(r, 9)
        rows.append({
            'ts': ts,
            'cgm': float(cgm) if cgm is not None else None,
            'cbg': float(cbg) if cbg is not None else None,
            'diet': diet,
            'insulin': insulin,
            'basal': basal,
        })
    return rows


def load_patient_file(path):
    """自动识别文件类型并加载。"""
    if path.endswith('.xlsx'):
        return load_xlsx(path)
    elif path.endswith('.xls'):
        return load_xls(path)
    return []


def mg_to_mmol(mg):
    """mg/dL → mmol/L"""
    return mg / 18.0


# ─────────────────────────────────────────────
# 事件段提取
# ─────────────────────────────────────────────

def extract_segments(rows, dt_minutes=15):
    """
    从患者数据中提取三种事件段：
    1. 稳态段（stable）：连续 CGM 无进食/胰岛素事件，变异 < 0.4 mmol/L/5min
    2. 餐后段（postmeal）：进食事件后 3 小时窗口
    3. 胰岛素段（postinsulin）：胰岛素注射后 4 小时窗口
    返回 {'stable': [...], 'postmeal': [...], 'postinsulin': [...]}
    """
    segments = {'stable': [], 'postmeal': [], 'postinsulin': []}

    # 先构建纯 CGM 时间序列（跳过空值）
    cgm_series = [(r['ts'], mg_to_mmol(r['cgm'])) for r in rows if r['cgm'] is not None]
    if len(cgm_series) < 6:
        return segments

    # 找出所有进食和胰岛素事件的时间点
    meal_times = [r['ts'] for r in rows if r['diet'] is not None]
    insulin_times = [(r['ts'], r['insulin']) for r in rows if r['insulin'] > 0]

    # ── 餐后段 ──
    for mt in meal_times:
        window_start = mt
        window_end = mt + timedelta(hours=3)
        seg_readings = []
        for ts, val in cgm_series:
            if window_start <= ts <= window_end:
                seg_readings.append((ts, val))
        if len(seg_readings) >= 8:  # 至少 2 小时数据
            segments['postmeal'].append({
                'event_time': mt,
                'readings': seg_readings,
                'dt': dt_minutes,
            })

    # ── 胰岛素段 ──
    for it_time, dose in insulin_times:
        window_start = it_time
        window_end = it_time + timedelta(hours=4)
        seg_readings = []
        for ts, val in cgm_series:
            if window_start <= ts <= window_end:
                seg_readings.append((ts, val))
        if len(seg_readings) >= 8:
            segments['postinsulin'].append({
                'event_time': it_time,
                'dose': dose,
                'readings': seg_readings,
                'dt': dt_minutes,
            })

    # ── 稳态段 ──
    # 找 2 小时内无进食/胰岛素事件、CGM 变化平缓的区间
    event_times = set()
    for mt in meal_times:
        for delta in range(-30, 181, 15):
            event_times.add(mt + timedelta(minutes=delta))
    for it_time, _ in insulin_times:
        for delta in range(-30, 241, 15):
            event_times.add(it_time + timedelta(minutes=delta))

    # 滑动窗口找稳态段
    window_size = 8  # 8 × 15min = 2h
    for i in range(len(cgm_series) - window_size):
        window = cgm_series[i:i + window_size]
        # 检查窗口内无事件
        has_event = False
        for ts, _ in window:
            for et in event_times:
                if abs((ts - et).total_seconds()) < 900:  # 15min tolerance
                    has_event = True
                    break
            if has_event:
                break
        if has_event:
            continue
        # 检查变异性
        values = [v for _, v in window]
        max_rate = max(abs(values[j] - values[j-1]) for j in range(1, len(values)))
        if max_rate < 0.8:  # < 0.8 mmol/L per 15min → 稳态
            segments['stable'].append({
                'readings': window,
                'dt': dt_minutes,
            })
            # 避免重叠
            i += window_size

    return segments


# ─────────────────────────────────────────────
# 参数拟合
# ─────────────────────────────────────────────

def fit_measurement_noise(all_rows):
    """
    从 CGM vs CBG 配对数据估计测量噪声 R。
    R = Var(CGM - CBG) / 18² (转换到 mmol/L²)
    """
    diffs = []
    for r in all_rows:
        if r['cgm'] is not None and r['cbg'] is not None:
            diff_mmol = (r['cgm'] - r['cbg']) / 18.0
            diffs.append(diff_mmol)
    if len(diffs) < 10:
        return 0.25, len(diffs)  # 默认 0.5²
    r_var = np.var(diffs)
    return round(float(r_var), 4), len(diffs)


def fit_process_noise(segments_stable, dt=15.0):
    """
    从稳态段估计过程噪声 Q 的缩放因子。
    Q_scale = Var(Δglucose) / dt
    """
    deltas = []
    for seg in segments_stable:
        values = [v for _, v in seg['readings']]
        for i in range(1, len(values)):
            deltas.append(values[i] - values[i-1])
    if len(deltas) < 20:
        return 0.01, len(deltas)
    q_scale = np.var(deltas) / dt
    return round(float(q_scale), 6), len(deltas)


def fit_insulin_tau(segments_insulin, dt=15.0):
    """
    从胰岛素注射后的 CGM 下降曲线拟合时间常数 τ。
    模型: glucose(t) = g0 + A * exp(-t/τ)
    用最小二乘法拟合。
    """
    all_taus = []
    for seg in segments_insulin:
        readings = seg['readings']
        values = [v for _, v in readings]
        if len(values) < 6:
            continue
        # 找到峰值后的下降段
        peak_idx = np.argmax(values)
        descent = values[peak_idx:]
        if len(descent) < 4:
            descent = values  # 如果已经在下降就用全部
        # 时间轴（分钟）
        t = np.arange(len(descent)) * dt
        y = np.array(descent)
        # 简单指数拟合: ln(y - y_min) = ln(A) - t/τ
        y_min = min(y) - 0.5  # 偏移避免 log(0)
        y_shifted = y - y_min
        y_shifted = np.maximum(y_shifted, 0.1)
        try:
            log_y = np.log(y_shifted)
            # 线性回归: log_y = a + b*t, τ = -1/b
            coeffs = np.polyfit(t, log_y, 1)
            if coeffs[0] < -1e-6:  # 确保是下降
                tau = -1.0 / coeffs[0]
                if 20 < tau < 200:  # 合理范围
                    all_taus.append(tau)
        except (np.linalg.LinAlgError, ValueError):
            continue

    if not all_taus:
        return 55.0, 0  # 默认值
    # 用中位数（比均值更鲁棒）
    tau = float(np.median(all_taus))
    return round(tau, 1), len(all_taus)


def fit_carb_absorption(segments_meal, dt=15.0):
    """
    从餐后 CGM 上升曲线拟合碳水吸收参数 t_peak 和 t_decay。
    t_peak: 血糖上升最快的时间点
    t_decay: 从峰值回落到 (peak-baseline)/e 的时间
    """
    all_t_peak = []
    all_t_decay = []

    for seg in segments_meal:
        readings = seg['readings']
        values = [v for _, v in readings]
        if len(values) < 6:
            continue
        # 变化率
        rates = [(values[i] - values[i-1]) / dt for i in range(1, len(values))]
        # t_peak: 最大上升速率的时间
        max_rate_idx = np.argmax(rates)
        t_peak = (max_rate_idx + 1) * dt  # 分钟
        if 5 < t_peak < 120:
            all_t_peak.append(t_peak)
        # t_decay: 从峰值开始衰减
        peak_idx = np.argmax(values)
        peak_val = values[peak_idx]
        baseline = values[0]
        threshold = baseline + (peak_val - baseline) / math.e
        # 找到峰值后降到阈值的时间
        for j in range(peak_idx + 1, len(values)):
            if values[j] <= threshold:
                t_decay_val = (j - peak_idx) * dt
                if 15 < t_decay_val < 300:
                    all_t_decay.append(t_decay_val)
                break

    t_peak = float(np.median(all_t_peak)) if all_t_peak else 35.0
    t_decay = float(np.median(all_t_decay)) if all_t_decay else 90.0
    return round(t_peak, 1), round(t_decay, 1), len(all_t_peak), len(all_t_decay)


def fit_isf(segments_insulin):
    """
    从胰岛素注射段估计 ISF（胰岛素敏感因子）。
    ISF = (glucose_before - glucose_nadir) / dose
    """
    isf_values = []
    for seg in segments_insulin:
        dose = seg.get('dose', 0)
        if dose <= 0:
            continue
        values = [v for _, v in seg['readings']]
        if len(values) < 4:
            continue
        glucose_start = values[0]
        glucose_min = min(values)
        drop = glucose_start - glucose_min
        if drop > 0.5:  # 至少降了 0.5 mmol/L
            isf = drop / dose
            if 0.3 < isf < 10.0:  # 合理范围
                isf_values.append(isf)
    if not isf_values:
        return 2.5, 0
    return round(float(np.median(isf_values)), 2), len(isf_values)


# ─────────────────────────────────────────────
# 交叉验证评估
# ─────────────────────────────────────────────

def evaluate_kf_params(segments_stable, q_scale, r_var, dt=15.0):
    """用稳态段评估 KF 参数的预测 RMSE。"""
    from kalman_engine import KalmanFilter
    errors = []
    for seg in segments_stable[:50]:  # 限制数量
        values = [v for _, v in seg['readings']]
        if len(values) < 6:
            continue
        # 用前 4 个点滤波，预测后续
        train = values[:4]
        kf = KalmanFilter(process_noise=q_scale, measurement_noise=r_var)
        # 调整 dt
        orig_F = kf.F.copy()
        kf.F[0, 1] = dt  # 使用实际 dt
        kf.filter(train)
        preds = kf.forecast(len(values) - 4)
        for i, pred in enumerate(preds):
            if i + 4 < len(values):
                errors.append((pred['glucose'] - values[i + 4]) ** 2)
    if not errors:
        return float('inf')
    return math.sqrt(np.mean(errors))


# ─────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SugarClaw 卡尔曼滤波参数校准器"
    )
    parser.add_argument(
        "--data-dir", required=True,
        help="数据集根目录（包含 Shanghai_T1DM/ 和 Shanghai_T2DM/ 子目录）"
    )
    parser.add_argument(
        "--type", choices=["t1dm", "t2dm", "all"], default="all",
        help="使用哪个子集（默认 all）"
    )
    parser.add_argument(
        "--output", default=None,
        help="输出参数文件路径（JSON，默认打印到 stdout）"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="输出详细过程信息"
    )
    args = parser.parse_args()

    # 收集文件
    folders = []
    if args.type in ("t1dm", "all"):
        t1_dir = os.path.join(args.data_dir, "Shanghai_T1DM")
        if os.path.isdir(t1_dir):
            folders.append(("T1DM", t1_dir))
    if args.type in ("t2dm", "all"):
        t2_dir = os.path.join(args.data_dir, "Shanghai_T2DM")
        if os.path.isdir(t2_dir):
            folders.append(("T2DM", t2_dir))

    if not folders:
        print("[ERROR] 未找到数据目录")
        sys.exit(1)

    all_rows = []
    all_segments = {'stable': [], 'postmeal': [], 'postinsulin': []}
    file_count = 0

    for dtype, folder in folders:
        files = sorted([
            f for f in os.listdir(folder)
            if f.endswith('.xlsx') or f.endswith('.xls')
        ])
        if args.verbose:
            print(f"\n[{dtype}] 处理 {len(files)} 个文件...")

        for fname in files:
            path = os.path.join(folder, fname)
            try:
                rows = load_patient_file(path)
                if not rows:
                    continue
                all_rows.extend(rows)
                segs = extract_segments(rows)
                for key in all_segments:
                    all_segments[key].extend(segs[key])
                file_count += 1
                if args.verbose and file_count % 20 == 0:
                    print(f"  已处理 {file_count} 个文件...")
            except Exception as e:
                if args.verbose:
                    print(f"  [WARN] {fname}: {e}")
                continue

    print(f"\n{'═' * 60}")
    print(f"  SugarClaw 卡尔曼滤波参数校准报告")
    print(f"{'═' * 60}")
    print(f"  数据集: {args.type.upper()}")
    print(f"  文件数: {file_count}")
    print(f"  CGM 数据点: {sum(1 for r in all_rows if r['cgm'] is not None)}")
    print(f"  提取事件段:")
    print(f"    稳态段: {len(all_segments['stable'])}")
    print(f"    餐后段: {len(all_segments['postmeal'])}")
    print(f"    胰岛素段: {len(all_segments['postinsulin'])}")
    print(f"{'─' * 60}")

    # ── 拟合参数 ──
    print(f"\n  [1/5] 测量噪声 R（CGM vs CBG 配对分析）...")
    r_var, r_n = fit_measurement_noise(all_rows)
    print(f"    R = {r_var} mmol/L² (n={r_n} 配对)")
    if r_n < 10:
        print(f"    [WARN] 配对数据不足，使用默认 R=0.25")
        r_var = 0.25

    print(f"\n  [2/5] 过程噪声 Q 缩放因子（稳态段分析）...")
    q_scale, q_n = fit_process_noise(all_segments['stable'])
    print(f"    Q_scale = {q_scale} (n={q_n} 个变化量)")

    print(f"\n  [3/5] 胰岛素时间常数 τ（注射后衰减曲线）...")
    tau, tau_n = fit_insulin_tau(all_segments['postinsulin'])
    print(f"    τ = {tau} 分钟 (n={tau_n} 段有效拟合)")

    print(f"\n  [4/5] 碳水吸收参数（餐后曲线）...")
    t_peak, t_decay, tp_n, td_n = fit_carb_absorption(all_segments['postmeal'])
    print(f"    t_peak = {t_peak} 分钟 (n={tp_n} 段)")
    print(f"    t_decay = {t_decay} 分钟 (n={td_n} 段)")

    print(f"\n  [5/5] 胰岛素敏感因子 ISF...")
    isf, isf_n = fit_isf(all_segments['postinsulin'])
    print(f"    ISF = {isf} mmol/L per unit (n={isf_n} 段)")

    # ── 汇总 ──
    params = {
        "calibration_source": "Shanghai_T1DM_T2DM_CGM_Dataset",
        "calibration_date": datetime.now().strftime("%Y-%m-%d"),
        "dataset_type": args.type,
        "data_stats": {
            "files": file_count,
            "cgm_points": sum(1 for r in all_rows if r['cgm'] is not None),
            "cgm_cbg_pairs": r_n if r_n >= 10 else 0,
            "stable_segments": len(all_segments['stable']),
            "postmeal_segments": len(all_segments['postmeal']),
            "postinsulin_segments": len(all_segments['postinsulin']),
        },
        "kf_params": {
            "process_noise_scale": q_scale,
            "measurement_noise_R": r_var,
            "description": "标准 KF，用于稳态/睡眠期",
        },
        "ekf_params": {
            "process_noise_scale": round(q_scale * 2, 6),
            "measurement_noise_R": r_var,
            "insulin_tau_minutes": tau,
            "isf_mmol_per_unit": isf,
            "description": "EKF，用于胰岛素注射后",
        },
        "ukf_params": {
            "process_noise_scale": round(q_scale * 3, 6),
            "measurement_noise_R": r_var,
            "carb_t_peak_minutes": t_peak,
            "carb_t_decay_minutes": t_decay,
            "description": "UKF，用于进食后",
        },
        "alert_thresholds": {
            "hypo_warning": 3.9,
            "hypo_critical": 3.0,
            "hyper_warning": 10.0,
            "hyper_critical": 13.9,
        },
        "comparison_with_defaults": {
            "measurement_noise_R": {"default": 0.25, "calibrated": r_var},
            "process_noise_Q": {"default": 0.01, "calibrated": q_scale},
            "insulin_tau": {"default": 55.0, "calibrated": tau},
            "carb_t_peak": {"default": 35.0, "calibrated": t_peak},
            "carb_t_decay": {"default": 90.0, "calibrated": t_decay},
            "isf": {"default": 2.5, "calibrated": isf},
        }
    }

    print(f"\n{'═' * 60}")
    print(f"  校准结果汇总")
    print(f"{'═' * 60}")
    print(f"  {'参数':<25} {'默认值':>10} {'校准值':>10} {'变化':>10}")
    print(f"  {'─' * 55}")
    for key, comp in params['comparison_with_defaults'].items():
        default = comp['default']
        cal = comp['calibrated']
        change = ((cal - default) / default * 100) if default != 0 else 0
        arrow = "↑" if change > 5 else ("↓" if change < -5 else "≈")
        print(f"  {key:<25} {default:>10} {cal:>10} {change:>+8.1f}% {arrow}")
    print(f"{'═' * 60}")

    # 输出
    if args.output:
        output_path = args.output
    else:
        output_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "calibrated_params.json"
        )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(params, f, indent=2, ensure_ascii=False)
    print(f"\n  参数已保存到: {output_path}")
    print(f"  声明: 校准参数基于群体数据，个体使用时仍需微调。")


if __name__ == "__main__":
    main()
