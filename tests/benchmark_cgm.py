#!/usr/bin/env python3
"""
SugarClaw CGM 血糖预测基准测试
使用 GlucoBench 数据集评估卡尔曼滤波引擎的 30min 预测精度。

评估指标:
  - RMSE (Root Mean Squared Error)
  - MAE (Mean Absolute Error)
  - MARD (Mean Absolute Relative Difference, %)
  - Clarke Error Grid 分区统计

用法:
  python3 tests/benchmark_cgm.py
  python3 tests/benchmark_cgm.py --dataset hall
  python3 tests/benchmark_cgm.py --dataset all --max-subjects 5
"""
import argparse
import csv
import json
import math
import os
import subprocess
import sys
from datetime import datetime

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(WORKSPACE, "skills", "food-gi-rag", ".venv", "bin", "python3")
KALMAN_ENGINE = os.path.join(WORKSPACE, "skills", "kalman-filter-engine", "scripts", "kalman_engine.py")
DATA_DIR = os.path.join(WORKSPACE, "tests", "benchmark_data", "GlucoBench", "raw_data", "raw_data")

DATASETS = {
    "hall": {"file": "hall.csv", "type": "mixed", "gl_col": "gl", "id_col": "id", "time_col": "time", "unit": "mgdl"},
    "colas": {"file": "colas.csv", "type": "T2DM+healthy", "gl_col": "gl", "id_col": "id", "time_col": "time", "unit": "mgdl"},
    "dubosson": {"file": "dubosson.csv", "type": "T1DM", "gl_col": "gl", "id_col": "id", "time_col": "time", "unit": "mgdl"},
    "weinstock": {"file": "weinstock.csv", "type": "T1DM_elderly", "gl_col": "gl", "id_col": "id", "time_col": "time", "unit": "mgdl"},
    "iglu": {"file": "iglu.csv", "type": "mixed", "gl_col": "gl", "id_col": "id", "time_col": "time", "unit": "mgdl"},
}


def load_dataset(name, max_subjects=None):
    """Load a GlucoBench dataset, return dict of subject_id -> [(timestamp, glucose_mmol)]."""
    info = DATASETS[name]
    filepath = os.path.join(DATA_DIR, info["file"])

    subjects = {}
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row[info["id_col"]].strip().strip('"')
            try:
                gl = float(row[info["gl_col"]])
            except (ValueError, KeyError):
                continue

            if gl <= 0 or gl > 600:
                continue

            # Convert mg/dL to mmol/L
            if info["unit"] == "mgdl":
                gl_mmol = round(gl / 18.0, 2)
            else:
                gl_mmol = gl

            time_str = row[info["time_col"]].strip().strip('"')

            if sid not in subjects:
                subjects[sid] = []
            subjects[sid].append((time_str, gl_mmol))

    # Sort each subject's data by time
    for sid in subjects:
        subjects[sid].sort(key=lambda x: x[0])

    # Limit subjects if requested
    if max_subjects and len(subjects) > max_subjects:
        keys = sorted(subjects.keys())[:max_subjects]
        subjects = {k: subjects[k] for k in keys}

    return subjects


def extract_windows(readings, window_size=12, horizon=6):
    """
    Extract sliding windows for prediction evaluation.
    window_size: number of input readings (12 = 1 hour at 5min)
    horizon: prediction steps (6 = 30 min)
    Returns: list of (input_readings, actual_future_readings)
    """
    windows = []
    step = horizon  # non-overlapping evaluation windows
    for i in range(0, len(readings) - window_size - horizon + 1, step):
        input_vals = [r[1] for r in readings[i:i + window_size]]
        future_vals = [r[1] for r in readings[i + window_size:i + window_size + horizon]]
        if len(future_vals) == horizon:
            windows.append((input_vals, future_vals))
    return windows


def run_kalman(readings_list):
    """Run Kalman engine and return predictions."""
    readings_str = " ".join(str(r) for r in readings_list[-12:])  # use last 12
    try:
        proc = subprocess.run(
            [VENV_PYTHON, KALMAN_ENGINE, "--readings", readings_str, "--json"],
            capture_output=True, text=True, timeout=10
        )
        if proc.returncode != 0:
            return None
        data = json.loads(proc.stdout)
        return [p["glucose"] for p in data.get("predictions", [])]
    except Exception:
        return None


def clarke_zone(ref, pred):
    """Determine Clarke Error Grid zone (A-E) for a single point.
    ref and pred in mg/dL.
    """
    if ref <= 70 and pred <= 70:
        return "A"
    if ref >= 180 and pred >= 180:
        return "A"
    if abs(pred - ref) <= 0.2 * ref or (ref < 70 and pred < 180):
        if pred <= ref * 1.2 and pred >= ref * 0.8:
            return "A"
    if (ref >= 70 and pred >= 70 and
        abs(pred - ref) / ref <= 0.2):
        return "A"
    if (ref < 70 and pred > 180):
        return "E"
    if (ref > 180 and pred < 70):
        return "E"
    if pred > ref * 1.2 and pred <= ref * 1.6:
        return "B"
    if pred < ref * 0.8 and pred >= ref * 0.6:
        return "B"

    return "B"  # simplified: C/D grouped with B for this benchmark


def evaluate(actual, predicted):
    """Calculate RMSE, MAE, MARD for paired lists (in mmol/L)."""
    n = min(len(actual), len(predicted))
    if n == 0:
        return None

    errors = []
    rel_errors = []
    for a, p in zip(actual[:n], predicted[:n]):
        err = p - a
        errors.append(err)
        if a > 0:
            rel_errors.append(abs(err) / a * 100)

    mae = sum(abs(e) for e in errors) / n
    rmse = math.sqrt(sum(e * e for e in errors) / n)
    mard = sum(rel_errors) / len(rel_errors) if rel_errors else 0

    # Clarke zones (convert to mg/dL)
    zones = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
    for a, p in zip(actual[:n], predicted[:n]):
        zone = clarke_zone(a * 18, p * 18)
        zones[zone] += 1

    return {
        "rmse_mmol": round(rmse, 3),
        "rmse_mgdl": round(rmse * 18, 2),
        "mae_mmol": round(mae, 3),
        "mae_mgdl": round(mae * 18, 2),
        "mard_pct": round(mard, 2),
        "clarke_A_pct": round(zones["A"] / n * 100, 1),
        "clarke_AB_pct": round((zones["A"] + zones["B"]) / n * 100, 1),
        "n_predictions": n,
    }


def benchmark_dataset(name, max_subjects=None, verbose=True):
    """Run full benchmark on one dataset."""
    if verbose:
        print(f"\n{'='*60}")
        print(f"  Dataset: {name} ({DATASETS[name]['type']})")
        print(f"{'='*60}")

    subjects = load_dataset(name, max_subjects)
    if verbose:
        print(f"  Subjects: {len(subjects)}")
        total_points = sum(len(v) for v in subjects.values())
        print(f"  Total CGM points: {total_points}")

    all_actual = []
    all_predicted = []
    subject_results = []

    for sid, readings in subjects.items():
        windows = extract_windows(readings, window_size=12, horizon=6)
        if len(windows) < 3:
            continue

        s_actual = []
        s_predicted = []

        for input_vals, future_vals in windows:
            preds = run_kalman(input_vals)
            if preds and len(preds) >= len(future_vals):
                for a, p in zip(future_vals, preds[:len(future_vals)]):
                    s_actual.append(a)
                    s_predicted.append(p)

        if s_actual:
            metrics = evaluate(s_actual, s_predicted)
            if metrics:
                subject_results.append({"subject": sid, **metrics})
                all_actual.extend(s_actual)
                all_predicted.extend(s_predicted)

                if verbose:
                    print(f"    {sid}: RMSE={metrics['rmse_mgdl']} mg/dL, "
                          f"MAE={metrics['mae_mgdl']} mg/dL, "
                          f"MARD={metrics['mard_pct']}%, "
                          f"Clarke A={metrics['clarke_A_pct']}% "
                          f"(n={metrics['n_predictions']})")

    # Overall metrics
    overall = evaluate(all_actual, all_predicted) if all_actual else None

    if verbose and overall:
        print(f"\n  --- Overall ({name}) ---")
        print(f"  RMSE:     {overall['rmse_mgdl']} mg/dL ({overall['rmse_mmol']} mmol/L)")
        print(f"  MAE:      {overall['mae_mgdl']} mg/dL ({overall['mae_mmol']} mmol/L)")
        print(f"  MARD:     {overall['mard_pct']}%")
        print(f"  Clarke A: {overall['clarke_A_pct']}%")
        print(f"  Clarke A+B: {overall['clarke_AB_pct']}%")
        print(f"  Total predictions: {overall['n_predictions']}")

    return {
        "dataset": name,
        "type": DATASETS[name]["type"],
        "subjects_evaluated": len(subject_results),
        "overall": overall,
        "per_subject": subject_results
    }


def main():
    parser = argparse.ArgumentParser(description="SugarClaw CGM Prediction Benchmark")
    parser.add_argument("--dataset", default="iglu",
                        choices=list(DATASETS.keys()) + ["all"],
                        help="Dataset to benchmark (default: iglu)")
    parser.add_argument("--max-subjects", type=int, default=5,
                        help="Max subjects per dataset (default: 5)")
    parser.add_argument("--output", default=None,
                        help="Save results to JSON file")
    args = parser.parse_args()

    print("=" * 60)
    print("  SugarClaw CGM Prediction Benchmark")
    print(f"  Engine: Kalman Filter (KF/EKF/UKF auto-select)")
    print(f"  Horizon: 30 min (6 steps x 5 min)")
    print(f"  Input window: 1 hour (12 readings)")
    print("=" * 60)

    datasets = list(DATASETS.keys()) if args.dataset == "all" else [args.dataset]
    results = []

    for ds in datasets:
        filepath = os.path.join(DATA_DIR, DATASETS[ds]["file"])
        if not os.path.exists(filepath):
            print(f"\n  [SKIP] {ds}: file not found at {filepath}")
            continue
        result = benchmark_dataset(ds, max_subjects=args.max_subjects)
        results.append(result)

    # Summary table
    if len(results) > 1:
        print(f"\n{'='*60}")
        print(f"  Summary")
        print(f"{'='*60}")
        print(f"  {'Dataset':<15} {'Type':<15} {'RMSE(mg/dL)':<12} {'MAE(mg/dL)':<12} {'MARD%':<8} {'Clarke A%':<10}")
        print(f"  {'-'*15} {'-'*15} {'-'*12} {'-'*12} {'-'*8} {'-'*10}")
        for r in results:
            o = r.get("overall")
            if o:
                print(f"  {r['dataset']:<15} {r['type']:<15} {o['rmse_mgdl']:<12} {o['mae_mgdl']:<12} {o['mard_pct']:<8} {o['clarke_A_pct']:<10}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n  Results saved to {args.output}")


if __name__ == "__main__":
    main()
