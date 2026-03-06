#!/usr/bin/env python3
"""
SugarClaw 卡尔曼滤波血糖预测引擎
实现 KF / EKF / UKF 三种滤波器，用于 CGM 信号降噪与 30 分钟血糖预测。

用法:
  # 从 JSON 数据输入（CGM 读数序列）
  python3 kalman_engine.py --input readings.json

  # 从命令行直接输入最近的 CGM 读数（每 5 分钟一个，mmol/L）
  python3 kalman_engine.py --readings "6.2 6.5 6.8 7.3 7.9 8.5"

  # 指定滤波器类型
  python3 kalman_engine.py --readings "6.2 6.5 6.8 7.3 7.9 8.5" --filter ekf

  # 自动选择滤波器 + 报告进食事件
  python3 kalman_engine.py --readings "6.2 6.5 6.8 7.3 7.9 8.5" --event meal --gi 82

  # 报告注射胰岛素
  python3 kalman_engine.py --readings "12.5 11.8 10.9 10.1 9.5 9.0" --event insulin --dose 4

  # 报告运动事件（自动切换 EKF 运动模式）
  python3 kalman_engine.py --readings "8.5 8.2 7.8 7.3 6.9 6.5" --event exercise --intensity moderate --duration 30

  # JSON 输出（供下游模块解析）
  python3 kalman_engine.py --readings "6.2 6.5 6.8 7.3 7.9 8.5" --json
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timedelta

import numpy as np

# ─────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────
DT = 5.0            # CGM 采样间隔（分钟）
PREDICT_STEPS = 6   # 预测步数（6 × 5min = 30min）
HYPO_THRESHOLD = 3.9   # 低血糖阈值 mmol/L
HYPER_THRESHOLD = 10.0  # 高血糖警戒 mmol/L
URGENT_LOW = 3.0       # 紧急低血糖
URGENT_HIGH = 13.9     # 紧急高血糖（酮体风险）

# ─────────────────────────────────────────────
# 校准参数加载
# ─────────────────────────────────────────────
CALIBRATED_PARAMS = None

def load_calibrated_params():
    """加载校准参数文件（如果存在）。"""
    global CALIBRATED_PARAMS
    if CALIBRATED_PARAMS is not None:
        return CALIBRATED_PARAMS
    params_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "calibrated_params.json"
    )
    if os.path.exists(params_path):
        with open(params_path, 'r') as f:
            CALIBRATED_PARAMS = json.load(f)
    return CALIBRATED_PARAMS


def get_param(filter_type, param_name, default):
    """从校准参数中获取值，回退到默认值。"""
    params = load_calibrated_params()
    if params is None:
        return default
    section = params.get(f"{filter_type}_params", {})
    return section.get(param_name, default)


# ─────────────────────────────────────────────
# 标准卡尔曼滤波 (KF) — 稳态/睡眠期
# 状态: [血糖值, 变化率]
# ─────────────────────────────────────────────
class KalmanFilter:
    """线性卡尔曼滤波器，适用于稳态血糖（平缓期/睡眠期）。"""

    def __init__(self, process_noise=None, measurement_noise=None):
        # 加载校准参数（如有）
        if process_noise is None:
            process_noise = get_param("kf", "process_noise_scale", 0.004276)
        if measurement_noise is None:
            measurement_noise = get_param("kf", "measurement_noise_R", 5.042)
        # 状态转移矩阵 F: x(k) = x(k-1) + v(k-1)*dt
        self.F = np.array([
            [1.0, DT],
            [0.0, 1.0]
        ])
        # 观测矩阵 H: 只观测血糖值
        self.H = np.array([[1.0, 0.0]])
        # 过程噪声协方差 Q
        self.Q = process_noise * np.array([
            [DT**3/3, DT**2/2],
            [DT**2/2, DT]
        ])
        # 观测噪声协方差 R
        self.R = np.array([[measurement_noise]])
        # 状态估计与协方差
        self.x = None  # [glucose, rate]
        self.P = np.eye(2) * 10.0

    def initialize(self, readings):
        """用前几个读数初始化状态。"""
        if len(readings) >= 2:
            self.x = np.array([
                readings[-1],
                (readings[-1] - readings[-2]) / DT
            ])
        else:
            self.x = np.array([readings[-1], 0.0])

    def predict_step(self):
        """预测步骤。"""
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q

    def update_step(self, z):
        """更新步骤。"""
        y = np.array([z]) - self.H @ self.x  # 残差
        S = self.H @ self.P @ self.H.T + self.R  # 残差协方差
        K = self.P @ self.H.T @ np.linalg.inv(S)  # 卡尔曼增益
        self.x = self.x + (K @ y).flatten()
        I = np.eye(2)
        self.P = (I - K @ self.H) @ self.P

    def filter(self, readings):
        """对完整读数序列进行滤波。"""
        self.initialize(readings[:2] if len(readings) >= 2 else readings)
        filtered = []
        for z in readings:
            self.predict_step()
            self.update_step(z)
            filtered.append(self.x[0])
        return filtered

    def forecast(self, steps=PREDICT_STEPS):
        """从当前状态预测未来。"""
        predictions = []
        x_pred = self.x.copy()
        P_pred = self.P.copy()
        for _ in range(steps):
            x_pred = self.F @ x_pred
            P_pred = self.F @ P_pred @ self.F.T + self.Q
            sigma = math.sqrt(P_pred[0, 0])
            predictions.append({
                "glucose": round(float(x_pred[0]), 2),
                "sigma": round(sigma, 2),
                "ci_low": round(float(x_pred[0] - 1.96 * sigma), 2),
                "ci_high": round(float(x_pred[0] + 1.96 * sigma), 2),
            })
        return predictions


# ─────────────────────────────────────────────
# 扩展卡尔曼滤波 (EKF) — 注射胰岛素后
# 状态: [血糖值, 变化率, 胰岛素活性]
# 非线性: 胰岛素吸收遵循指数衰减动力学
# ─────────────────────────────────────────────
class ExtendedKalmanFilter:
    """扩展卡尔曼滤波器，模拟胰岛素或运动的非线性动力学。"""

    # 运动强度映射
    EXERCISE_INTENSITY_MAP = {
        "light": 0.3,
        "moderate": 0.6,
        "vigorous": 0.9,
    }

    def __init__(self, insulin_dose=0.0, isf=None, process_noise=None,
                 measurement_noise=None, exercise_mode=False,
                 exercise_intensity="moderate", exercise_duration=30):
        """
        isf: 胰岛素敏感因子（每单位胰岛素降低血糖 mmol/L）
        insulin_dose: 注射剂量（单位）
        exercise_mode: 是否启用运动模式
        exercise_intensity: 运动强度 (light/moderate/vigorous)
        exercise_duration: 运动持续时间（分钟）
        """
        if isf is None:
            isf = get_param("ekf", "isf_mmol_per_unit", 0.73)
        if process_noise is None:
            process_noise = get_param("ekf", "process_noise_scale", 0.008552)
        if measurement_noise is None:
            measurement_noise = get_param("ekf", "measurement_noise_R", 5.042)
        self.isf = isf
        self.tau = get_param("ekf", "insulin_tau_minutes", 77.0)
        self.H = np.array([[1.0, 0.0, 0.0]])
        self.Q = process_noise * np.diag([DT**2, DT, 0.1])
        self.R = np.array([[measurement_noise]])
        # 状态: [glucose, rate, insulin_on_board / exercise_elapsed_minutes]
        self.x = None
        self.P = np.eye(3) * 10.0
        self.insulin_dose = insulin_dose

        # 运动模式参数
        self.exercise_mode = exercise_mode
        if exercise_mode:
            self.exercise_intensity = self.EXERCISE_INTENSITY_MAP.get(
                exercise_intensity, 0.6
            )
            self.exercise_duration = exercise_duration
            self.exercise_tau = get_param(
                "exercise", "exercise_tau_minutes", 15.0
            )
            self.exercise_drop_rate = get_param(
                "exercise", "exercise_drop_rate", 0.5
            )
            self.post_exercise_rebound = get_param(
                "exercise", "post_exercise_rebound", 0.3
            )

    def initialize(self, readings):
        if len(readings) >= 2:
            rate = (readings[-1] - readings[-2]) / DT
        else:
            rate = 0.0
        if self.exercise_mode:
            # 第三状态: 运动已进行时间（分钟），从 0 开始
            self.x = np.array([readings[-1], rate, 0.0])
        else:
            self.x = np.array([readings[-1], rate, self.insulin_dose])

    def _exercise_glucose_effect(self, elapsed):
        """计算运动对血糖的影响量（mmol/L per DT 分钟）。

        模型:
          - 延迟期 (0-10min): 最小效应，身体启动有氧代谢
          - 活跃期 (10min ~ duration): 血糖以强度相关速率下降
          - 运动后期 (> duration): 肝糖原释放导致轻微反弹
        公式: effect = -intensity * drop_rate * (1 - exp(-(t - delay) / tau))
        """
        delay = 10.0  # 运动效应延迟（分钟）
        intensity = self.exercise_intensity
        drop_rate = self.exercise_drop_rate
        tau = self.exercise_tau
        duration = self.exercise_duration

        if elapsed <= delay:
            # 延迟期：几乎无效应
            return 0.0
        elif elapsed <= duration:
            # 活跃期：指数渐进的降糖效应
            t_active = elapsed - delay
            effect = -intensity * drop_rate * (
                1.0 - math.exp(-t_active / tau)
            ) * (DT / 15.0)  # 归一化到每 DT 分钟
            return effect
        else:
            # 运动后：轻微反弹（肝糖原释放）
            t_post = elapsed - duration
            # 反弹随时间指数衰减
            rebound = self.post_exercise_rebound * math.exp(-t_post / 30.0) * (DT / 15.0)
            return rebound

    def _f(self, x):
        """非线性状态转移函数。"""
        glucose, rate, third_state = x

        if self.exercise_mode:
            # 运动模式：third_state = 运动已进行时间
            elapsed = third_state
            exercise_effect = self._exercise_glucose_effect(elapsed)
            new_glucose = glucose + rate * DT + exercise_effect
            # 变化率受运动影响
            new_rate = rate + (exercise_effect / DT - rate) * 0.2
            new_elapsed = elapsed + DT
            return np.array([new_glucose, new_rate, new_elapsed])
        else:
            # 胰岛素模式：third_state = insulin_on_board
            iob = third_state
            decay = math.exp(-DT / self.tau)
            new_iob = iob * decay
            insulin_effect = (iob - new_iob) * self.isf
            new_glucose = glucose + rate * DT - insulin_effect
            new_rate = rate - insulin_effect / DT * 0.3
            return np.array([new_glucose, new_rate, new_iob])

    def _jacobian_F(self, x):
        """状态转移的雅可比矩阵。"""
        _, _, third_state = x

        if self.exercise_mode:
            elapsed = third_state
            # 数值近似雅可比（运动效应对 elapsed 的导数）
            eps = 0.1
            de = (self._exercise_glucose_effect(elapsed + eps)
                  - self._exercise_glucose_effect(elapsed)) / eps
            return np.array([
                [1.0, DT, de],
                [0.0, 1.0, de / DT * 0.2],
                [0.0, 0.0, 1.0]  # elapsed 线性递增
            ])
        else:
            iob = third_state
            decay = math.exp(-DT / self.tau)
            d_insulin = (1 - decay) * self.isf
            return np.array([
                [1.0, DT, -d_insulin],
                [0.0, 1.0, -d_insulin / DT * 0.3],
                [0.0, 0.0, decay]
            ])

    def predict_step(self):
        self.x = self._f(self.x)
        F_jac = self._jacobian_F(self.x)
        self.P = F_jac @ self.P @ F_jac.T + self.Q

    def update_step(self, z):
        y = np.array([z]) - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + (K @ y).flatten()
        I = np.eye(3)
        self.P = (I - K @ self.H) @ self.P

    def filter(self, readings):
        self.initialize(readings[:2] if len(readings) >= 2 else readings)
        filtered = []
        for z in readings:
            self.predict_step()
            self.update_step(z)
            filtered.append(self.x[0])
        return filtered

    def forecast(self, steps=PREDICT_STEPS):
        predictions = []
        x_pred = self.x.copy()
        P_pred = self.P.copy()
        for _ in range(steps):
            F_jac = self._jacobian_F(x_pred)
            x_pred = self._f(x_pred)
            P_pred = F_jac @ P_pred @ F_jac.T + self.Q
            sigma = math.sqrt(P_pred[0, 0])
            pred_entry = {
                "glucose": round(float(x_pred[0]), 2),
                "sigma": round(sigma, 2),
                "ci_low": round(float(x_pred[0] - 1.96 * sigma), 2),
                "ci_high": round(float(x_pred[0] + 1.96 * sigma), 2),
            }
            if self.exercise_mode:
                pred_entry["exercise_elapsed_min"] = round(float(x_pred[2]), 1)
            else:
                pred_entry["iob"] = round(float(x_pred[2]), 3)
            predictions.append(pred_entry)
        return predictions


# ─────────────────────────────────────────────
# 无迹卡尔曼滤波 (UKF) — 进食高 GI 食物后
# 捕捉高度非线性的餐后血糖爆发峰值
# 状态: [血糖值, 变化率, 碳水吸收量]
# ─────────────────────────────────────────────
class UnscentedKalmanFilter:
    """无迹卡尔曼滤波器，用 sigma 点采样捕捉餐后血糖非线性峰值。"""

    def __init__(self, gl_value=0.0, process_noise=None,
                 measurement_noise=None):
        """
        gl_value: 摄入食物的 GL 值（血糖负荷）
        """
        if process_noise is None:
            process_noise = get_param("ukf", "process_noise_scale", 0.012828)
        if measurement_noise is None:
            measurement_noise = get_param("ukf", "measurement_noise_R", 5.042)
        self.n = 3  # 状态维度
        self.alpha = 1.0
        self.beta = 2.0
        self.kappa = 3.0 - self.n  # 标准推荐: kappa = 3 - n
        self.lam = self.alpha**2 * (self.n + self.kappa) - self.n

        self.H = np.array([[1.0, 0.0, 0.0]])
        self.Q = process_noise * np.diag([DT**2, DT, 1.0])
        self.R = np.array([[measurement_noise]])

        self.x = None
        self.P = np.eye(3) * 10.0
        self.gl_value = gl_value
        # 碳水吸收动力学参数（校准值）
        self.t_peak = get_param("ukf", "carb_t_peak_minutes", 45.0)
        self.t_decay = get_param("ukf", "carb_t_decay_minutes", 60.0)

    def initialize(self, readings):
        if len(readings) >= 2:
            rate = (readings[-1] - readings[-2]) / DT
        else:
            rate = 0.0
        self.x = np.array([readings[-1], rate, self.gl_value])

    def _f(self, x):
        """非线性状态转移：餐后碳水吸收模型。"""
        glucose, rate, carb_remain = x
        # 碳水吸收速率（Scheiner 模型近似）
        if carb_remain > 0.1:
            absorption = carb_remain * (DT / self.t_decay)
            glucose_rise = absorption * 0.12  # GL 到 mmol/L 的转换系数
        else:
            absorption = 0.0
            glucose_rise = 0.0
        new_carb = max(0.0, carb_remain - absorption)
        new_glucose = glucose + rate * DT + glucose_rise
        # 变化率受碳水吸收影响
        new_rate = rate + (glucose_rise / DT - rate) * 0.15
        return np.array([new_glucose, new_rate, new_carb])

    def _sigma_points(self, x, P):
        """生成 sigma 点（使用特征值分解，比 Cholesky 更稳健）。"""
        n = len(x)
        sigmas = np.zeros((2 * n + 1, n))
        sigmas[0] = x
        scale = n + self.lam
        if scale <= 0:
            scale = 1.0
        M = scale * P
        # 对称化
        M = (M + M.T) / 2
        # 特征值分解（比 Cholesky 更稳健）
        eigvals, eigvecs = np.linalg.eigh(M)
        # 强制非负特征值
        eigvals = np.maximum(eigvals, 1e-10)
        sqrt_P = eigvecs @ np.diag(np.sqrt(eigvals))
        for i in range(n):
            sigmas[i + 1] = x + sqrt_P[:, i]
            sigmas[n + i + 1] = x - sqrt_P[:, i]
        return sigmas

    def _weights(self):
        """计算 sigma 点权重。"""
        n = self.n
        wm = np.full(2 * n + 1, 1.0 / (2 * (n + self.lam)))
        wc = np.full(2 * n + 1, 1.0 / (2 * (n + self.lam)))
        wm[0] = self.lam / (n + self.lam)
        wc[0] = self.lam / (n + self.lam) + (1 - self.alpha**2 + self.beta)
        return wm, wc

    def predict_step(self):
        wm, wc = self._weights()
        sigmas = self._sigma_points(self.x, self.P)
        # 传播 sigma 点
        sigmas_f = np.array([self._f(s) for s in sigmas])
        # 加权均值
        self.x = np.sum(wm[:, None] * sigmas_f, axis=0)
        # 加权协方差
        self.P = self.Q.copy()
        for i in range(len(sigmas_f)):
            d = sigmas_f[i] - self.x
            self.P += wc[i] * np.outer(d, d)
        # 确保对称正定
        self.P = (self.P + self.P.T) / 2 + np.eye(self.n) * 1e-10

    def update_step(self, z):
        wm, wc = self._weights()
        sigmas = self._sigma_points(self.x, self.P)
        # 观测预测
        z_sigmas = np.array([self.H @ s for s in sigmas]).flatten()
        z_mean = np.sum(wm * z_sigmas)
        # 协方差
        Pzz = self.R[0, 0]
        Pxz = np.zeros(self.n)
        for i in range(len(sigmas)):
            Pzz += wc[i] * (z_sigmas[i] - z_mean)**2
            Pxz += wc[i] * (sigmas[i] - self.x) * (z_sigmas[i] - z_mean)
        # 卡尔曼增益
        K = Pxz / Pzz
        self.x = self.x + K * (z - z_mean)
        self.P = self.P - np.outer(K, K) * Pzz
        # 确保对称正定
        self.P = (self.P + self.P.T) / 2 + np.eye(self.n) * 1e-10

    def filter(self, readings):
        self.initialize(readings[:2] if len(readings) >= 2 else readings)
        filtered = []
        for z in readings:
            self.predict_step()
            self.update_step(z)
            filtered.append(self.x[0])
        return filtered

    def forecast(self, steps=PREDICT_STEPS):
        predictions = []
        x_pred = self.x.copy()
        P_pred = self.P.copy()
        for _ in range(steps):
            # 简化预测：用当前状态转移
            x_pred = self._f(x_pred)
            # 近似协方差增长
            P_pred = P_pred * 1.1 + self.Q
            sigma = math.sqrt(abs(P_pred[0, 0]))
            predictions.append({
                "glucose": round(float(x_pred[0]), 2),
                "sigma": round(sigma, 2),
                "ci_low": round(float(x_pred[0] - 1.96 * sigma), 2),
                "ci_high": round(float(x_pred[0] + 1.96 * sigma), 2),
                "carb_remaining": round(float(max(0, x_pred[2])), 1),
            })
        return predictions


# ─────────────────────────────────────────────
# 自动选择器 + 预警系统
# ─────────────────────────────────────────────
def auto_select_filter(readings, event=None, **kwargs):
    """根据场景自动选择最优滤波器。"""
    if event == "insulin":
        return "ekf", ExtendedKalmanFilter(
            insulin_dose=kwargs.get("dose", 0),
            isf=kwargs.get("isf", None)
        )
    elif event == "exercise":
        return "ekf", ExtendedKalmanFilter(
            exercise_mode=True,
            exercise_intensity=kwargs.get("intensity", "moderate"),
            exercise_duration=kwargs.get("duration", 30),
        )
    elif event == "meal":
        return "ukf", UnscentedKalmanFilter(
            gl_value=kwargs.get("gl", kwargs.get("gi", 0) * 0.5)
        )
    else:
        # 分析变化率判断是否稳态
        if len(readings) >= 3:
            rates = [abs(readings[i] - readings[i-1]) for i in range(1, len(readings))]
            avg_rate = sum(rates) / len(rates)
            if avg_rate > 0.8:
                # 高变异 → UKF
                return "ukf", UnscentedKalmanFilter(gl_value=0)
            elif avg_rate > 0.4:
                # 中等变异 → EKF（可能有药物/进食影响）
                return "ekf", ExtendedKalmanFilter()
        return "kf", KalmanFilter()


def generate_alerts(predictions, current_glucose):
    """根据预测结果生成预警。"""
    alerts = []

    # 当前值告警
    if current_glucose < URGENT_LOW:
        alerts.append({
            "level": "CRITICAL",
            "type": "Hypo_Alert",
            "message": f"紧急低血糖！当前 {current_glucose} mmol/L < {URGENT_LOW}，立即补充 15g 速效碳水"
        })
    elif current_glucose < HYPO_THRESHOLD:
        alerts.append({
            "level": "WARNING",
            "type": "Hypo_Alert",
            "message": f"低血糖预警：当前 {current_glucose} mmol/L，建议少量加餐"
        })
    elif current_glucose > URGENT_HIGH:
        alerts.append({
            "level": "CRITICAL",
            "type": "Hyper_Alert",
            "message": f"严重高血糖！当前 {current_glucose} mmol/L > {URGENT_HIGH}，有酮体风险，建议监测酮体并咨询医师"
        })
    elif current_glucose > HYPER_THRESHOLD:
        alerts.append({
            "level": "WARNING",
            "type": "Hyper_Alert",
            "message": f"高血糖警戒：当前 {current_glucose} mmol/L，建议增加活动量"
        })

    # 预测告警
    for i, pred in enumerate(predictions):
        t = (i + 1) * 5
        if pred["ci_low"] < HYPO_THRESHOLD and current_glucose > HYPO_THRESHOLD:
            alerts.append({
                "level": "PREDICTIVE",
                "type": "Hypo_Forecast",
                "message": f"预测 {t} 分钟后可能低血糖（预测 {pred['glucose']} mmol/L，95%CI [{pred['ci_low']}, {pred['ci_high']}]）",
                "time_minutes": t
            })
            break  # 只报第一次
        if pred["glucose"] > HYPER_THRESHOLD and current_glucose <= HYPER_THRESHOLD:
            alerts.append({
                "level": "PREDICTIVE",
                "type": "Hyper_Forecast",
                "message": f"预测 {t} 分钟后可能高血糖（预测 {pred['glucose']} mmol/L）",
                "time_minutes": t
            })
            break

    return alerts


def trend_arrow(predictions):
    """生成趋势箭头（模拟 CGM 显示）。"""
    if not predictions:
        return "→"
    rate = (predictions[-1]["glucose"] - predictions[0]["glucose"]) / (len(predictions) * DT)
    if rate > 0.1:
        return "↑↑" if rate > 0.2 else "↑"
    elif rate < -0.1:
        return "↓↓" if rate < -0.2 else "↓"
    elif rate > 0.05:
        return "↗"
    elif rate < -0.05:
        return "↘"
    else:
        return "→"


def format_output(readings, filtered, predictions, alerts, filter_type, event):
    """格式化人类可读输出。"""
    lines = []
    current = filtered[-1] if filtered else readings[-1]
    arrow = trend_arrow(predictions)

    lines.append(f"{'═' * 55}")
    lines.append(f"  SugarClaw 卡尔曼滤波引擎 — 血糖预测报告")
    lines.append(f"{'═' * 55}")
    lines.append(f"  滤波器: {filter_type.upper()}"
                 f"{'  事件: ' + event if event else ''}")
    lines.append(f"  当前血糖: {current:.1f} mmol/L  {arrow}")
    lines.append(f"  原始读数: {' → '.join(f'{r:.1f}' for r in readings[-6:])}")
    lines.append(f"  滤波结果: {' → '.join(f'{f:.1f}' for f in filtered[-6:])}")
    lines.append(f"{'─' * 55}")

    # 预警
    if alerts:
        for a in alerts:
            icon = {"CRITICAL": "🚨", "WARNING": "⚠️", "PREDICTIVE": "🔮"}.get(a["level"], "ℹ️")
            lines.append(f"  {icon} [{a['level']}] {a['message']}")
        lines.append(f"{'─' * 55}")

    # 30 分钟预测
    lines.append(f"  {'未来 30 分钟预测':^45}")
    lines.append(f"  {'时间':>8}  {'预测值':>8}  {'95% CI':>16}  {'状态':>6}")
    now = datetime.now()
    for i, pred in enumerate(predictions):
        t = now + timedelta(minutes=(i + 1) * 5)
        status = ""
        if pred["glucose"] < HYPO_THRESHOLD:
            status = "⚠低"
        elif pred["glucose"] > HYPER_THRESHOLD:
            status = "⚠高"
        else:
            status = "✓"
        lines.append(
            f"  +{(i+1)*5:>2}min ({t.strftime('%H:%M')})  "
            f"{pred['glucose']:>6.1f}  "
            f"[{pred['ci_low']:>5.1f}, {pred['ci_high']:>5.1f}]  "
            f"{status:>6}"
        )

    lines.append(f"{'═' * 55}")
    lines.append("  声明: 预测结果仅供参考，不构成临床诊断。如需调整用药请咨询医师。")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="SugarClaw 卡尔曼滤波血糖预测引擎"
    )
    parser.add_argument(
        "--readings", type=str,
        help="血糖读数序列（空格分隔，mmol/L），至少 3 个"
    )
    parser.add_argument(
        "--input", type=str,
        help="从 JSON 文件读取（格式: {\"readings\": [6.2, 6.5, ...]}）"
    )
    parser.add_argument(
        "--filter", choices=["kf", "ekf", "ukf", "auto"],
        default="auto", help="滤波器类型（默认 auto 自动选择）"
    )
    parser.add_argument(
        "--event", choices=["meal", "insulin", "exercise", "sleep"],
        default=None, help="当前事件类型"
    )
    parser.add_argument("--gi", type=float, default=0, help="进食食物 GI 值")
    parser.add_argument("--gl", type=float, default=0, help="进食食物 GL 值")
    parser.add_argument("--dose", type=float, default=0, help="胰岛素剂量（单位）")
    parser.add_argument("--isf", type=float, default=None,
                        help="胰岛素敏感因子 ISF（默认从校准参数读取）")
    parser.add_argument("--intensity", choices=["light", "moderate", "vigorous"],
                        default="moderate", help="运动强度（默认 moderate）")
    parser.add_argument("--duration", type=int, default=30,
                        help="运动持续时间（分钟，默认 30）")
    parser.add_argument("--steps", type=int, default=PREDICT_STEPS,
                        help=f"预测步数（默认 {PREDICT_STEPS}，每步 {int(DT)} 分钟）")
    parser.add_argument("--process-noise", type=float, default=None,
                        help="过程噪声协方差 Q（默认由滤波器类型决定）")
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="JSON 输出")
    args = parser.parse_args()

    # 加载数据
    if args.input:
        with open(args.input, "r") as f:
            data = json.load(f)
        readings = data.get("readings", data.get("glucose", []))
    elif args.readings:
        readings = [float(x) for x in args.readings.split()]
    else:
        parser.print_help()
        print("\n错误: 请提供 --readings 或 --input 参数")
        sys.exit(1)

    if len(readings) < 3:
        print("错误: 至少需要 3 个血糖读数（每 5 分钟一个）")
        sys.exit(1)

    # 选择滤波器
    if args.filter == "auto":
        filter_type, kf = auto_select_filter(
            readings, event=args.event,
            dose=args.dose, isf=args.isf,
            gi=args.gi, gl=args.gl,
            intensity=args.intensity, duration=args.duration
        )
    elif args.filter == "kf":
        filter_type = "kf"
        kf = KalmanFilter(process_noise=args.process_noise)
    elif args.filter == "ekf":
        filter_type = "ekf"
        if args.event == "exercise":
            kf = ExtendedKalmanFilter(
                exercise_mode=True,
                exercise_intensity=args.intensity,
                exercise_duration=args.duration,
                process_noise=args.process_noise,
            )
        else:
            kf = ExtendedKalmanFilter(
                insulin_dose=args.dose, isf=args.isf, process_noise=args.process_noise
            )
    elif args.filter == "ukf":
        filter_type = "ukf"
        gl = args.gl if args.gl else args.gi * 0.5
        kf = UnscentedKalmanFilter(gl_value=gl, process_noise=args.process_noise)

    # 运行滤波
    filtered = kf.filter(readings)
    predictions = kf.forecast(args.steps)
    alerts = generate_alerts(predictions, filtered[-1])

    if args.json_out:
        output = {
            "filter_type": filter_type,
            "event": args.event,
            "timestamp": datetime.now().isoformat(),
            "current_glucose": round(filtered[-1], 2),
            "trend": trend_arrow(predictions),
            "raw_readings": readings,
            "filtered_readings": [round(f, 2) for f in filtered],
            "predictions": predictions,
            "alerts": alerts,
            "params": {
                "dt_minutes": DT,
                "predict_steps": args.steps,
                "gi": args.gi,
                "gl": args.gl,
                "insulin_dose": args.dose,
                "isf": args.isf,
                "exercise_intensity": args.intensity if args.event == "exercise" else None,
                "exercise_duration": args.duration if args.event == "exercise" else None,
            }
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(format_output(
            readings, filtered, predictions, alerts, filter_type, args.event
        ))


if __name__ == "__main__":
    main()
