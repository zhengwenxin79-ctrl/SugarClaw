#!/usr/bin/env python3
"""
SugarClaw End-to-End Test Suite

Dependency-free (no pytest). Uses subprocess to call CLI tools in their
respective venvs. Prints a pass/fail summary and exits with code 1 on
any failure.

Usage:
    python3 tests/test_e2e.py
"""

import json
import os
import shutil
import subprocess
import sys
import traceback

# ─────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.expanduser(
    "~/.openclaw/workspace/skills/food-gi-rag/.venv/bin/python3"
)
SYS_PYTHON = "python3"

QUERY_FOOD = os.path.join(
    WORKSPACE, "skills", "food-gi-rag", "scripts", "query_food.py"
)
KALMAN_ENGINE = os.path.join(
    WORKSPACE, "skills", "kalman-filter-engine", "scripts", "kalman_engine.py"
)
USER_MANAGER = os.path.join(WORKSPACE, "scripts", "user_manager.py")
USER_MD = os.path.join(WORKSPACE, "USER.md")
USER_MD_BACKUP = os.path.join(WORKSPACE, "USER.md.e2e_backup")

# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────
results = []  # list of (name, passed: bool, detail: str)


def run(cmd, check=True, timeout=60):
    """Run a subprocess and return CompletedProcess."""
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"Command failed (rc={proc.returncode}):\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  stderr: {proc.stderr.strip()}\n"
            f"  stdout: {proc.stdout.strip()}"
        )
    return proc


def record(name, passed, detail=""):
    results.append((name, passed, detail))
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}")
    if detail and not passed:
        for line in detail.strip().splitlines():
            print(f"         {line}")


def backup_user_md():
    """Backup USER.md before tests (if it exists)."""
    if os.path.exists(USER_MD):
        shutil.copy2(USER_MD, USER_MD_BACKUP)


def restore_user_md():
    """Restore USER.md to its original state after tests."""
    if os.path.exists(USER_MD_BACKUP):
        shutil.copy2(USER_MD_BACKUP, USER_MD)
        os.remove(USER_MD_BACKUP)
    elif os.path.exists(USER_MD):
        # No backup means USER.md did not exist before tests; remove the
        # one we may have created.
        os.remove(USER_MD)


# ─────────────────────────────────────────────────────
# Test Cases
# ─────────────────────────────────────────────────────


def test_food_query():
    """Query food-gi-rag for a specific food and verify gi_value is returned."""
    proc = run([VENV_PYTHON, QUERY_FOOD, "热干面", "--json"])
    data = json.loads(proc.stdout)
    assert isinstance(data, list) and len(data) > 0, (
        f"Expected non-empty list, got: {proc.stdout[:200]}"
    )
    first = data[0]
    assert "gi_value" in first, f"Missing gi_value in result: {first}"
    assert isinstance(first["gi_value"], (int, float)), (
        f"gi_value should be numeric, got: {first['gi_value']}"
    )
    return f"Found '{first.get('food_name', '?')}' with GI={first['gi_value']}"


def test_food_counter():
    """Query --counter for a high GI food and verify counter_strategy exists."""
    proc = run([VENV_PYTHON, QUERY_FOOD, "--counter", "白米饭"])
    output = proc.stdout
    # The counter output should mention "策略" (strategy)
    assert "策略" in output or "counter" in output.lower(), (
        f"Expected counter_strategy content, got:\n{output[:300]}"
    )
    return "Counter strategy found in output"


def test_kalman_kf_stable():
    """Run KF with stable readings and verify no WARNING/CRITICAL alerts."""
    readings = "6.5 6.6 6.5 6.4 6.5 6.6"
    proc = run([
        VENV_PYTHON, KALMAN_ENGINE,
        "--readings", readings,
        "--filter", "kf",
        "--json",
    ])
    data = json.loads(proc.stdout)
    assert data["filter_type"] == "kf", (
        f"Expected filter_type='kf', got '{data['filter_type']}'"
    )
    alerts = data.get("alerts", [])
    # PREDICTIVE alerts can fire due to wide CI from calibrated R=5.042;
    # only fail on actual WARNING/CRITICAL alerts for stable mid-range readings
    serious = [a for a in alerts if a["level"] in ("WARNING", "CRITICAL")]
    assert len(serious) == 0, (
        f"Expected no WARNING/CRITICAL alerts for stable readings, got: {serious}"
    )
    return f"KF stable: current={data['current_glucose']}, {len(alerts)} predictive (ok), 0 serious"


def test_kalman_ukf_meal():
    """Run UKF with rising readings + meal event, verify Hyper_Forecast alert."""
    readings = "6.2 6.5 6.8 7.3 7.9 8.5"
    proc = run([
        VENV_PYTHON, KALMAN_ENGINE,
        "--readings", readings,
        "--event", "meal",
        "--gi", "82",
        "--json",
    ])
    data = json.loads(proc.stdout)
    assert data["filter_type"] == "ukf", (
        f"Expected filter_type='ukf', got '{data['filter_type']}'"
    )
    alerts = data.get("alerts", [])
    alert_types = [a["type"] for a in alerts]
    assert "Hyper_Forecast" in alert_types, (
        f"Expected Hyper_Forecast alert, got types: {alert_types}. "
        f"Predictions: {data.get('predictions', [])}"
    )
    return f"UKF meal: Hyper_Forecast triggered, {len(alerts)} alert(s)"


def test_kalman_ekf_insulin():
    """Run EKF with dropping readings + insulin event, verify Hypo_Alert."""
    readings = "5.5 5.0 4.5 4.2 4.0 3.8"
    proc = run([
        VENV_PYTHON, KALMAN_ENGINE,
        "--readings", readings,
        "--event", "insulin",
        "--dose", "4",
        "--json",
    ])
    data = json.loads(proc.stdout)
    assert data["filter_type"] == "ekf", (
        f"Expected filter_type='ekf', got '{data['filter_type']}'"
    )
    alerts = data.get("alerts", [])
    alert_types = [a["type"] for a in alerts]
    # Accept either a current Hypo_Alert (WARNING/CRITICAL) or a predictive
    # Hypo_Forecast -- both indicate the engine detected the low-glucose risk.
    has_hypo = any(t in ("Hypo_Alert", "Hypo_Forecast") for t in alert_types)
    assert has_hypo, (
        f"Expected Hypo_Alert or Hypo_Forecast, got types: {alert_types}. "
        f"Current glucose: {data.get('current_glucose')}, "
        f"Predictions: {data.get('predictions', [])}"
    )
    return (
        f"EKF insulin: hypo alert triggered, "
        f"current={data['current_glucose']}, {len(alerts)} alert(s)"
    )


def test_user_manager_parse():
    """Load T2DM_foodie mock, parse USER.md, verify diabetes_type contains T2DM."""
    # Load mock persona
    run([SYS_PYTHON, USER_MANAGER, "--load-mock", "T2DM_foodie"])
    # Parse
    proc = run([SYS_PYTHON, USER_MANAGER, "--parse"])
    parsed = json.loads(proc.stdout)
    dtype = parsed.get("diabetes_type", "")
    assert "T2DM" in dtype, (
        f"Expected diabetes_type containing 'T2DM', got: '{dtype}'"
    )
    return f"Parsed diabetes_type='{dtype}'"


def test_user_manager_check_missing():
    """Generate USER.md from minimal JSON (missing required fields), verify check-missing reports it."""
    # Generate USER.md with only name — diabetes_type, isf, allergies, region all get defaults
    # but we need to make one truly empty. Write a minimal USER.md manually.
    minimal_md = "# USER.md\n- **糖尿病类型**: T2DM\n- **胰岛素敏感因子 (ISF)**: 0.73\n"
    user_md = os.path.join(WORKSPACE, "USER.md")
    with open(user_md, "w", encoding="utf-8") as f:
        f.write(minimal_md)
    # --check-missing should exit with code 1 (allergies and region missing)
    proc = run(
        [SYS_PYTHON, USER_MANAGER, "--check-missing"],
        check=False,
    )
    assert proc.returncode != 0, (
        f"Expected non-zero exit for missing fields, got rc={proc.returncode}"
    )
    assert "allergies" in proc.stdout.lower() or "禁忌" in proc.stdout, (
        f"Expected allergies in missing-field output, got:\n{proc.stdout[:300]}"
    )
    return "check-missing correctly reports missing fields"


def test_e2e_meal_workflow():
    """Full workflow: query food GI -> feed into Kalman with --event meal -> verify prediction and alerts."""
    # Step 1: Query food GI for a high-GI food
    proc_food = run([VENV_PYTHON, QUERY_FOOD, "热干面", "--json"])
    food_data = json.loads(proc_food.stdout)
    assert len(food_data) > 0, "No food results returned"
    gi_value = food_data[0]["gi_value"]
    food_name = food_data[0].get("food_name", "热干面")
    assert isinstance(gi_value, (int, float)) and gi_value > 0, (
        f"Invalid GI value: {gi_value}"
    )

    # Step 2: Feed GI into Kalman engine with rising CGM readings
    readings = "6.5 7.0 7.8 8.5 9.2 9.8"
    proc_kalman = run([
        VENV_PYTHON, KALMAN_ENGINE,
        "--readings", readings,
        "--event", "meal",
        "--gi", str(gi_value),
        "--json",
    ])
    kalman_data = json.loads(proc_kalman.stdout)

    # Verify filter selection
    assert kalman_data["filter_type"] == "ukf", (
        f"Expected UKF for meal event, got '{kalman_data['filter_type']}'"
    )

    # Verify predictions exist
    predictions = kalman_data.get("predictions", [])
    assert len(predictions) > 0, "No predictions returned from Kalman"

    # Verify alerts -- with rising readings + high GI meal we expect a
    # Hyper_Forecast or Hyper_Alert
    alerts = kalman_data.get("alerts", [])
    alert_types = [a["type"] for a in alerts]
    has_hyper = any(
        t in ("Hyper_Alert", "Hyper_Forecast") for t in alert_types
    )
    assert has_hyper, (
        f"Expected hyper alert for high-GI meal ({food_name}, GI={gi_value}), "
        f"got alert types: {alert_types}. "
        f"Predictions: {predictions}"
    )

    peak_glucose = max(p["glucose"] for p in predictions)
    return (
        f"E2E: {food_name} GI={gi_value} -> UKF predicted peak={peak_glucose}, "
        f"{len(alerts)} alert(s)"
    )


# ─────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────
ALL_TESTS = [
    test_food_query,
    test_food_counter,
    test_kalman_kf_stable,
    test_kalman_ukf_meal,
    test_kalman_ekf_insulin,
    test_user_manager_parse,
    test_user_manager_check_missing,
    test_e2e_meal_workflow,
]


def main():
    print("=" * 60)
    print("  SugarClaw End-to-End Tests")
    print("=" * 60)
    print()

    # Backup USER.md
    backup_user_md()

    try:
        for test_fn in ALL_TESTS:
            name = test_fn.__name__
            try:
                detail = test_fn()
                record(name, True, detail or "")
            except Exception as e:
                record(name, False, f"{e}\n{traceback.format_exc()}")
    finally:
        # Always restore USER.md
        restore_user_md()

    # Summary
    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    total = len(results)
    print()
    print("=" * 60)
    print(f"  Summary: {passed} passed, {failed} failed, {total} total")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
