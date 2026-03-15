#!/usr/bin/env python3
"""
SugarClaw MVP — FastAPI Backend
瘦客户端架构：所有 AI 逻辑在此运行，Flutter App 只做 UI 展示。

Endpoints:
  POST /api/analyze       — 手动输入血糖 + 食物，返回完整分析
  POST /api/replay        — 选择内置案例，回放历史 CGM 数据
  GET  /api/replay/stream — SSE 流式推送回放数据
  POST /api/chat          — DeepSeek R1 深度思考对话（SSE 流式）
  GET  /api/cases         — 获取内置经典案例列表
  GET  /api/health        — 健康检查
"""

import json
import math
import os
import sys
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# 加载 .env 文件（如果存在）
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().strip().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# 把 kalman_engine 和 food query 加入 path
SKILLS_DIR = os.path.expanduser("~/.openclaw/workspace/skills")
sys.path.insert(0, os.path.join(SKILLS_DIR, "kalman-filter-engine", "scripts"))
sys.path.insert(0, os.path.join(SKILLS_DIR, "food-gi-rag", "scripts"))

import kalman_engine as kf_engine

# CGM 模拟数据 + PubMed 文献检索
sys.path.insert(0, os.path.join(SKILLS_DIR, "pubmed-researcher", "scripts"))
import ble_cgm_parser
import pubmed_researcher

# SQLite 持久化
import database
import guidelines

# ─── 内置经典案例 ────────────────────────────
CASES_DIR = os.path.join(os.path.dirname(__file__), "cases")

BUILTIN_CASES = {
    "high_carb_breakfast": {
        "id": "high_carb_breakfast",
        "title": "高碳水早餐后的血糖失控",
        "description": "T2DM 患者早晨吃了两碗热干面，血糖从 6.5 飙升至 16.8 mmol/L",
        "scenario": "meal",
        "readings": [6.5, 7.0, 8.2, 9.8, 11.5, 13.2, 14.8, 15.9, 16.5, 16.8, 16.2, 15.5],
        "event": "meal",
        "food": "热干面 x2",
        "gi": 82,
        "gl": 65,
    },
    "insulin_overcorrection": {
        "id": "insulin_overcorrection",
        "title": "胰岛素过量纠正后的低血糖危机",
        "description": "注射 8U 速效胰岛素后血糖快速下降，触发低血糖预警",
        "scenario": "insulin",
        "readings": [14.2, 13.5, 12.1, 10.8, 9.2, 7.5, 6.1, 5.0, 4.2, 3.8, 3.5, 3.3],
        "event": "insulin",
        "dose": 8,
        "food": None,
        "gi": 0,
        "gl": 0,
    },
    "nighttime_stable": {
        "id": "nighttime_stable",
        "title": "夜间稳态：理想的血糖控制",
        "description": "睡眠期间血糖平稳维持在 5.5~6.2 mmol/L，标准 KF 滤波",
        "scenario": "stable",
        "readings": [5.8, 5.7, 5.6, 5.5, 5.6, 5.5, 5.7, 5.8, 5.9, 6.0, 6.1, 6.2],
        "event": None,
        "food": None,
        "gi": 0,
        "gl": 0,
    },
    "postlunch_spike": {
        "id": "postlunch_spike",
        "title": "午餐后血糖缓慢攀升",
        "description": "中等 GI 午餐后血糖逐渐上升，触发高血糖预测预警",
        "scenario": "meal",
        "readings": [6.8, 7.1, 7.5, 8.0, 8.6, 9.3, 9.8, 10.2, 10.5, 10.3, 9.9, 9.5],
        "event": "meal",
        "food": "米饭 + 红烧肉",
        "gi": 73,
        "gl": 42,
    },
    "dawn_phenomenon": {
        "id": "dawn_phenomenon",
        "title": "黎明现象：清晨激素驱动的血糖升高",
        "description": "凌晨 4-7 点血糖自发上升，无进食触发",
        "scenario": "stable",
        "readings": [5.5, 5.6, 5.8, 6.1, 6.5, 7.0, 7.6, 8.1, 8.5, 8.8, 9.0, 9.1],
        "event": None,
        "food": None,
        "gi": 0,
        "gl": 0,
    },
}


# ─── Pydantic Models ────────────────────────────

class AnalyzeRequest(BaseModel):
    readings: List[float] = Field(..., min_length=3, description="血糖读数序列 (mmol/L)")
    event: Optional[str] = Field(None, description="事件类型: meal / insulin / exercise / sleep")
    food: Optional[str] = Field(None, description="食物名称（用于 GI/GL 查询）")
    gi: float = Field(0, description="食物 GI 值")
    gl: float = Field(0, description="食物 GL 值")
    dose: float = Field(0, description="胰岛素剂量")
    isf: Optional[float] = Field(None, description="胰岛素敏感因子")


class PredictionPoint(BaseModel):
    time_offset_min: int
    glucose: float
    ci_low: float
    ci_high: float
    sigma: float


class Alert(BaseModel):
    level: str
    type: str
    message: str
    time_minutes: Optional[int] = None


class AgentTrace(BaseModel):
    agent: str
    action: str
    result: str
    duration_ms: int


class AnalyzeResponse(BaseModel):
    # 滤波结果
    filter_type: str
    current_glucose: float
    trend: str
    filtered_readings: List[float]
    predictions: List[PredictionPoint]
    alerts: List[Alert]
    # 时间轴（供图表绘制）
    chart_data: dict
    # AI 建议
    advice: str
    # Agent trace（供调试和展示）
    agent_traces: List[AgentTrace]
    timestamp: str


class ReplayRequest(BaseModel):
    case_id: str


class CaseInfo(BaseModel):
    id: str
    title: str
    description: str
    scenario: str


# ─── Counterbalance Scale Models ──────────────

class FoodItem(BaseModel):
    name: str
    gi: float = 0
    gl: float = 0
    carb_g: float = 0
    protein_g: float = 0
    fat_g: float = 0
    fiber_g: float = 0
    serving_size_g: float = 0
    category: str = ""
    risk_weight: float = 0


class CalculateRiskRequest(BaseModel):
    food_name: str
    query_time: Optional[str] = Field(None, description="ISO8601 时间戳，用于推断用餐场景")
    quantity_multiplier: float = Field(1.0, ge=0.5, le=5.0, description="份数倍数，1.0=1份")


class CalculateRiskResponse(BaseModel):
    food: FoodItem
    risk_weight: float = Field(..., description="0-100 standardized risk score")
    risk_level: str = Field(..., description="low / medium / high / very_high")
    risk_detail: str
    meal_context: str = Field("", description="推断的用餐场景，如 午后加餐")
    time_advice: str = Field("", description="基于时间的建议")
    agent_traces: List[AgentTrace]


class CounterSolution(BaseModel):
    type: str = Field(..., description="food / exercise / medication")
    name: str
    description: str
    balance_weight: float = Field(..., description="How much this offsets the risk (0-100)")
    group: str = Field("", description="Group label for grouped single-select UI")
    details: dict = Field(default_factory=dict)


class FindBalanceRequest(BaseModel):
    food_name: str
    risk_weight: float = 0
    query_time: Optional[str] = Field(None, description="ISO8601 时间戳，用于推断用餐场景")


class AddExerciseRequest(BaseModel):
    exercise_name: str
    duration_min: int = Field(20, gt=0, le=180)
    risk_weight: float = 0


class AddFoodCounterRequest(BaseModel):
    food_name: str
    risk_weight: float = 0


class RefreshAdviceRequest(BaseModel):
    food_name: str
    risk_weight: float
    selected_indices: List[int] = Field(default_factory=list, description="用户选中的对冲方案索引列表")
    all_solutions: List[CounterSolution] = Field(default_factory=list, description="全部可选对冲方案")
    query_time: Optional[str] = Field(None, description="ISO8601 时间戳")


class RefreshAdviceResponse(BaseModel):
    advice: str
    meal_context: str = ""
    time_advice: str = ""


class FindBalanceResponse(BaseModel):
    risk_weight: float
    food: FoodItem
    solutions: List[CounterSolution]
    advice: str
    meal_context: str = Field("", description="推断的用餐场景")
    time_advice: str = Field("", description="基于时间的建议")
    agent_traces: List[AgentTrace]


# ─── 食物查询辅助 ────────────────────────────

def query_food_gi(food_name: str) -> dict:
    """调用 food-gi-rag 查询食物 GI/GL。"""
    import subprocess
    venv_python = os.path.expanduser(
        "~/.openclaw/workspace/skills/food-gi-rag/.venv/bin/python3"
    )
    query_script = os.path.join(SKILLS_DIR, "food-gi-rag", "scripts", "query_food.py")
    try:
        result = subprocess.run(
            [venv_python, query_script, food_name, "--json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            parsed = json.loads(result.stdout)
            # query_food.py --json returns a list directly
            if isinstance(parsed, list):
                return {"results": parsed}
            return parsed
    except Exception:
        pass
    return {}


def generate_advice(filter_type, current_glucose, predictions, alerts, event, food) -> str:
    """基于分析结果生成 Coordinator 综合建议。"""
    lines = []

    # 当前状态描述
    if current_glucose < 3.9:
        lines.append(f"你的血糖目前偏低（{current_glucose:.1f} mmol/L），需要立即关注。")
    elif current_glucose > 10.0:
        lines.append(f"你的血糖目前偏高（{current_glucose:.1f} mmol/L），我来帮你想想对策。")
    else:
        lines.append(f"你的血糖目前在正常范围内（{current_glucose:.1f} mmol/L），状态不错。")

    # 趋势分析
    if predictions:
        pred_30 = predictions[-1]["glucose"]
        if pred_30 > 10.0 and current_glucose <= 10.0:
            lines.append(f"不过模型预测 30 分钟后可能升到 {pred_30:.1f} mmol/L。")
        elif pred_30 < 3.9 and current_glucose >= 3.9:
            lines.append(f"需要注意，模型预测 30 分钟后可能降到 {pred_30:.1f} mmol/L。")

    # 基于事件的建议
    if event == "meal" and food:
        if any(a["level"] in ("WARNING", "PREDICTIVE") and "高" in a.get("message", "") for a in alerts):
            lines.append(f"刚吃的{food}升糖速度较快，建议餐后 15 分钟开始快走 20 分钟，这是最小代价的对冲方案。")
            lines.append("如果方便的话，下次可以试试全麦版本搭配无糖豆浆，能显著削平血糖峰值。")
        else:
            lines.append(f"这顿{food}对血糖的影响在可控范围内，继续保持。")
    elif event == "insulin":
        if any(a["level"] == "CRITICAL" for a in alerts):
            lines.append("胰岛素降糖效果强烈，请立即补充 15g 速效碳水（如葡萄糖片或果汁），15 分钟后复测。")
        elif any("低血糖" in a.get("message", "") for a in alerts):
            lines.append("胰岛素还在起效，建议备好碳水零食以防血糖过低。")

    # 滤波器说明
    filter_names = {"kf": "标准卡尔曼", "ekf": "扩展卡尔曼", "ukf": "无迹卡尔曼"}
    lines.append(f"（本次使用 {filter_names.get(filter_type, filter_type)} 滤波器分析）")

    return "\n".join(lines)


# ─── 对冲天平核心逻辑 ────────────────────────

# 风险权重参考上限：GL=50 对应 risk_weight=100
MAX_GL_REFERENCE = 50.0

# 运动 MET 查询表：(标准名, 别名列表, MET值)
# MET 数据参考: Compendium of Physical Activities (Ainsworth 2011)
EXERCISE_MET_ENTRIES = [
    # ── 走路类 ──
    ("散步",     ["走路", "走走", "逛街", "遛弯", "饭后走", "溜达", "步行", "walking"], 2.5),
    ("快走",     ["快步走", "健走", "竞走", "快速步行", "brisk walking"], 3.5),
    ("徒步",     ["远足", "越野徒步", "hiking", "登山徒步"], 5.5),
    ("爬山",     ["登山", "山地徒步", "爬坡", "hiking uphill"], 6.5),
    ("爬楼梯",   ["上楼梯", "爬楼", "走楼梯", "stair climbing"], 8.0),
    # ── 跑步类 ──
    ("慢跑",     ["小跑", "轻跑", "jogging", "慢速跑"], 7.0),
    ("跑步",     ["跑步机", "跑步运动", "running", "室外跑", "户外跑", "路跑",
                  "夜跑", "晨跑", "公园跑步", "操场跑步", "中速跑", "run"], 9.0),
    ("快跑",     ["冲刺", "短跑", "sprint", "间歇跑", "变速跑", "冲刺跑"], 11.0),
    ("马拉松",   ["半马", "全马", "半程马拉松", "全程马拉松", "长跑", "marathon", "越野跑", "trail running"], 10.0),
    # ── 骑行类 ──
    ("骑车",     ["骑自行车", "骑行", "自行车", "单车", "cycling", "bike",
                  "共享单车", "公路骑行", "山地骑行"], 6.0),
    ("动感单车", ["spinning", "室内骑行", "单车课"], 8.5),
    ("骑车(高强度)", ["竞速骑行", "自行车竞速", "高强度骑行"], 10.0),
    # ── 游泳水上类 ──
    ("游泳",     ["游泳池", "蛙泳", "自由泳", "仰泳", "swimming", "游泳运动"], 6.0),
    ("游泳(高强度)", ["快速游泳", "蝶泳", "竞速游泳", "游泳训练"], 9.0),
    ("冲浪",     ["surfing", "冲浪运动"], 3.0),
    ("皮划艇",   ["划艇", "kayak", "kayaking", "独木舟"], 5.0),
    ("划船",     ["赛艇", "划船机", "rowing", "划船运动"], 7.0),
    ("水中有氧", ["水中操", "水上瑜伽", "aqua aerobics"], 4.0),
    # ── 球类运动 ──
    ("羽毛球",   ["打羽毛球", "badminton"], 5.5),
    ("乒乓球",   ["打乒乓球", "ping pong", "table tennis"], 4.0),
    ("篮球",     ["打篮球", "半场篮球", "全场篮球", "basketball", "投篮"], 6.5),
    ("足球",     ["踢足球", "踢球", "soccer", "football", "五人制足球", "室内足球"], 7.0),
    ("网球",     ["打网球", "tennis"], 7.0),
    ("排球",     ["打排球", "volleyball", "沙滩排球"], 4.0),
    ("高尔夫",   ["打高尔夫", "golf", "高尔夫球"], 3.5),
    ("棒球",     ["打棒球", "baseball", "垒球", "softball"], 5.0),
    ("壁球",     ["squash", "打壁球"], 7.5),
    ("手球",     ["handball"], 8.0),
    ("橄榄球",   ["rugby", "美式足球", "american football"], 8.0),
    ("曲棍球",   ["field hockey", "冰球", "ice hockey"], 8.0),
    ("保龄球",   ["bowling", "打保龄球"], 3.0),
    ("台球",     ["打台球", "桌球", "billiards", "斯诺克", "snooker"], 2.5),
    # ── 健身房 / 力量训练 ──
    ("举重",     ["力量训练", "撸铁", "杠铃", "哑铃", "weight training", "weightlifting",
                  "卧推", "硬拉", "负重训练", "器械训练", "力量举"], 6.0),
    ("深蹲",     ["负重深蹲", "徒手深蹲", "squat", "squats", "蹲起", "深蹲跳"], 5.0),
    ("俯卧撑",   ["push up", "pushup", "俯卧撑训练"], 3.8),
    ("平板支撑", ["plank", "核心训练", "腹肌训练", "仰卧起坐", "卷腹", "sit up"], 3.5),
    ("引体向上", ["pull up", "pullup", "单杠", "吊环", "chin up"], 8.0),
    ("壶铃",     ["kettlebell", "壶铃摆荡", "壶铃训练"], 6.0),
    ("弹力带",   ["resistance band", "弹力绳", "拉力带", "拉力器"], 3.5),
    ("椭圆机",   ["elliptical", "太空漫步机", "交叉训练机"], 5.0),
    ("划船机",   ["rowing machine", "室内划船"], 7.0),
    ("战绳",     ["battle rope", "甩大绳", "战绳训练"], 10.0),
    ("HIIT",     ["高强度间歇", "间歇训练", "tabata", "高强度间歇训练",
                  "hiit训练", "间歇有氧", "circuit training", "循环训练"], 9.0),
    ("CrossFit", ["crossfit", "混合训练", "功能性训练", "综合体能训练"], 9.0),
    # ── 有氧 / 操课类 ──
    ("健身操",   ["有氧操", "aerobics", "健美操", "操课", "有氧运动", "燃脂操"], 6.5),
    ("尊巴",     ["zumba", "拉丁健身操"], 6.5),
    ("搏击操",   ["body combat", "有氧搏击", "拳击操"], 7.0),
    # ── 跳跃类 ──
    ("跳绳",     ["跳绳子", "jump rope", "skipping"], 10.0),
    ("开合跳",   ["jumping jacks", "星星跳", "开合跳训练"], 8.0),
    ("波比跳",   ["burpee", "burpees", "波比", "立卧撑跳"], 8.0),
    ("跳箱",     ["box jump", "箱跳", "跳台阶"], 8.0),
    # ── 舞蹈类 ──
    ("跳舞",     ["舞蹈", "dance", "dancing", "拉丁舞", "街舞", "现代舞", "民族舞",
                  "爵士舞", "肚皮舞", "芭蕾", "钢管舞", "breaking"], 5.0),
    ("广场舞",   ["广场跳舞", "square dance", "坝坝舞"], 4.5),
    ("国标舞",   ["交谊舞", "华尔兹", "探戈", "ballroom dance", "社交舞"], 4.5),
    # ── 柔韧 / 身心类 ──
    ("瑜伽",     ["yoga", "流瑜伽", "阴瑜伽", "热瑜伽", "哈他瑜伽", "阿斯汤加",
                  "空中瑜伽", "高温瑜伽", "vinyasa", "拜日式"], 2.5),
    ("普拉提",   ["pilates", "核心普拉提", "器械普拉提"], 3.0),
    ("太极",     ["太极拳", "太极剑", "八段锦", "五禽戏", "tai chi", "taichi"], 3.0),
    ("拉伸",     ["stretching", "柔韧训练", "压腿", "劈叉", "筋膜放松",
                  "泡沫轴", "foam roller", "放松运动", "拉筋"], 2.3),
    ("冥想",     ["meditation", "打坐", "正念", "呼吸训练", "深呼吸"], 1.5),
    # ── 搏击 / 武术类 ──
    ("拳击",     ["boxing", "打拳", "沙袋", "拳击训练", "打沙袋"], 7.5),
    ("跆拳道",   ["taekwondo", "TKD"], 7.0),
    ("空手道",   ["karate"], 6.5),
    ("柔道",     ["judo"], 7.0),
    ("散打",     ["自由搏击", "综合格斗", "MMA", "格斗", "kickboxing"], 8.0),
    ("击剑",     ["fencing", "剑术"], 6.0),
    ("武术",     ["kung fu", "功夫", "套路"], 6.0),
    # ── 冰雪 / 滑行类 ──
    ("滑冰",     ["溜冰", "花样滑冰", "速滑", "ice skating", "skating"], 5.5),
    ("滑雪",     ["skiing", "单板滑雪", "双板滑雪", "snowboard", "越野滑雪"], 7.0),
    ("滑板",     ["skateboard", "长板", "滑板运动"], 5.0),
    ("轮滑",     ["旱冰", "roller skating", "roller blade", "溜旱冰"], 7.0),
    # ── 攀爬类 ──
    ("攀岩",     ["rock climbing", "抱石", "bouldering", "室内攀岩", "岩壁"], 8.0),
    # ── 日常活动 ──
    ("做家务",   ["拖地", "扫地", "吸尘", "擦地", "打扫卫生", "大扫除", "收拾房间",
                  "housework", "cleaning", "洗碗"], 3.0),
    ("园艺",     ["种花", "种菜", "浇花", "除草", "gardening", "种地"], 4.0),
    ("带娃",     ["陪孩子玩", "抱孩子", "遛娃", "陪小孩", "带孩子"], 3.5),
    ("遛狗",     ["溜狗", "dog walking", "遛宠物"], 3.0),
    ("搬运重物", ["搬家", "搬东西", "扛东西", "提重物"], 6.0),
    # ── 其他 ──
    ("站立办公", ["站着工作", "站立", "standing desk", "站着办公"], 1.8),
    ("骑马",     ["马术", "horse riding", "equestrian"], 4.0),
    ("飞盘",     ["frisbee", "ultimate", "极限飞盘", "飞盘高尔夫"], 4.0),
    ("跑酷",     ["parkour", "自由跑"], 8.0),
    ("蹦床",     ["trampoline", "蹦蹦床", "弹跳床"], 3.5),
    ("健身环",   ["ring fit", "switch健身", "体感游戏", "健身环大冒险"], 5.0),
    ("跳操",     ["有氧跳操", "燃脂跳操", "刘畊宏", "帕梅拉", "周六野", "keep课程"], 6.5),
]

# 构建精确查找字典和别名反查字典
EXERCISE_MET_DB = {}
_EXERCISE_ALIAS_MAP = {}  # 别名 → (标准名, MET值)

for _std_name, _aliases, _met in EXERCISE_MET_ENTRIES:
    EXERCISE_MET_DB[_std_name] = _met
    for _alias in _aliases:
        _EXERCISE_ALIAS_MAP[_alias.lower()] = (_std_name, _met)


def lookup_exercise_met(name: str) -> tuple:
    """模糊匹配运动名称，返回 (标准名, MET值, 匹配来源)。
    优先级: 精确匹配 → 别名匹配 → 子串匹配 → 默认值。
    """
    name = name.strip()
    name_lower = name.lower()

    # 1. 精确匹配标准名
    if name in EXERCISE_MET_DB:
        return (name, EXERCISE_MET_DB[name], "精确匹配")

    # 2. 精确匹配别名
    if name_lower in _EXERCISE_ALIAS_MAP:
        std, met = _EXERCISE_ALIAS_MAP[name_lower]
        return (std, met, "别名匹配")

    # 3. 子串匹配（查询词包含标准名，或标准名包含查询词）
    best = None
    best_ratio = 0
    for std_name, aliases, met in EXERCISE_MET_ENTRIES:
        # 标准名是查询词的子串（如"跑步"在"户外跑步"中）
        if std_name in name and len(std_name) >= 2:
            ratio = len(std_name) / len(name)
            if ratio > best_ratio:
                best = (std_name, met, "子串匹配")
                best_ratio = ratio
        # 查询词是标准名的子串（如"跑"在"跑步"中 → 不够长，跳过）
        if name in std_name and len(name) >= 2:
            ratio = len(name) / len(std_name)
            if ratio >= 0.5 and ratio > best_ratio:
                best = (std_name, met, "子串匹配")
                best_ratio = ratio
        # 别名子串匹配
        for alias in aliases:
            alias_lower = alias.lower()
            if alias_lower in name_lower and len(alias_lower) >= 2:
                ratio = len(alias_lower) / len(name_lower)
                if ratio > best_ratio:
                    best = (std_name, met, "别名子串匹配")
                    best_ratio = ratio
            if name_lower in alias_lower and len(name_lower) >= 2:
                ratio = len(name_lower) / len(alias_lower)
                if ratio >= 0.5 and ratio > best_ratio:
                    best = (std_name, met, "别名子串匹配")
                    best_ratio = ratio

    if best and best_ratio >= 0.4:
        return best

    # 4. 默认
    return (name, 4.0, "默认估算")

# 运动 MET 值和卡路里 → 血糖影响的换算
EXERCISE_OPTIONS = [
    {
        "name": "餐后快走 20 分钟",
        "met": 3.5, "duration_min": 20, "kcal_approx": 80,
        "description": "最小代价对冲：饭后散步即可，不需换装备",
    },
    {
        "name": "餐后快走 30 分钟",
        "met": 3.5, "duration_min": 30, "kcal_approx": 120,
        "description": "中等强度散步，可以边走边听播客",
    },
    {
        "name": "骑车 20 分钟",
        "met": 6.0, "duration_min": 20, "kcal_approx": 140,
        "description": "共享单车或自行车通勤即可完成",
    },
    {
        "name": "爬楼梯 10 分钟",
        "met": 8.0, "duration_min": 10, "kcal_approx": 90,
        "description": "办公室午餐后直接爬几层楼梯",
    },
]


def infer_meal_context(query_time: Optional[str]) -> dict:
    """
    根据查询时间推断用餐场景，返回 meal_context 信息。

    时段划分:
      6:00-9:00   早餐
      9:00-11:00  上午加餐
      11:00-13:30 午餐
      13:30-17:00 午后加餐
      17:00-20:00 晚餐
      20:00-23:00 夜间加餐/宵夜
      23:00-6:00  深夜进食
    """
    if not query_time:
        return {"label": "", "period": "", "risk_modifier": 0.0, "hour": -1}

    try:
        dt = datetime.fromisoformat(query_time.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return {"label": "", "period": "", "risk_modifier": 0.0, "hour": -1}

    hour = dt.hour + dt.minute / 60.0

    if 6.0 <= hour < 9.0:
        return {"label": "早餐", "period": "breakfast", "risk_modifier": 0.0, "hour": hour}
    elif 9.0 <= hour < 11.0:
        return {"label": "上午加餐", "period": "morning_snack", "risk_modifier": 3.0, "hour": hour}
    elif 11.0 <= hour < 13.5:
        return {"label": "午餐", "period": "lunch", "risk_modifier": 0.0, "hour": hour}
    elif 13.5 <= hour < 17.0:
        return {"label": "午后加餐", "period": "afternoon_snack", "risk_modifier": 5.0, "hour": hour}
    elif 17.0 <= hour < 20.0:
        return {"label": "晚餐", "period": "dinner", "risk_modifier": 2.0, "hour": hour}
    elif 20.0 <= hour < 23.0:
        return {"label": "宵夜", "period": "late_snack", "risk_modifier": 8.0, "hour": hour}
    else:
        return {"label": "深夜进食", "period": "midnight", "risk_modifier": 10.0, "hour": hour}


def generate_time_advice(meal_ctx: dict, food_name: str, risk_weight: float) -> str:
    """根据用餐时段和食物风险生成时间相关的建议。"""
    period = meal_ctx.get("period", "")
    label = meal_ctx.get("label", "")
    if not period:
        return ""

    lines = []

    if period == "afternoon_snack":
        lines.append(f"现在是午后时段，搜索「{food_name}」看起来你想吃点零食。")
        if risk_weight >= 50:
            lines.append("午后血糖通常已从午餐峰值回落，此时高GI零食容易造成二次血糖波动。")
            lines.append("建议：先吃一小把坚果或一杯无糖酸奶垫底，10分钟后再少量享用，可以显著削平血糖峰值。")
        else:
            lines.append("午后适量加餐有助于避免晚餐前低血糖，这个选择的血糖负荷不算高。")
    elif period == "late_snack":
        lines.append(f"已经是晚上了，此时进食「{food_name}」需要格外注意。")
        lines.append("夜间身体代谢减慢、胰岛素敏感性下降，同样的食物在夜间对血糖的影响比白天更大。")
        if risk_weight >= 40:
            lines.append("建议：如果确实想吃，可以将份量减半，搭配高蛋白食物（如鸡蛋、奶酪）来减缓吸收。")
        else:
            lines.append("好在这个食物血糖负荷不高，控制好份量问题不大。")
    elif period == "midnight":
        lines.append(f"现在已经是深夜了，进食「{food_name}」对血糖影响会比白天大很多。")
        lines.append("深夜进食会干扰昼夜节律，显著降低胰岛素敏感性，建议尽量避免。")
        lines.append("如果实在饿了，建议选择一小杯温牛奶或几颗坚果，既能缓解饥饿又不会大幅升糖。")
    elif period == "morning_snack":
        lines.append(f"上午加餐时间，「{food_name}」作为加餐需要注意份量。")
        if risk_weight >= 50:
            lines.append("距离午餐还有一段时间，高GI加餐可能导致午餐前血糖波动，建议选择低GI替代或减量。")
    elif period == "breakfast":
        lines.append(f"早餐时间吃「{food_name}」。")
        if risk_weight >= 60:
            lines.append("早晨皮质醇水平较高，胰岛素抵抗相对较强，高GI早餐更容易引起血糖飙升。")
            lines.append("建议搭配蛋白质（鸡蛋、豆浆）和膳食纤维，采用先菜后饭的进食顺序。")
    elif period == "lunch":
        if risk_weight >= 60:
            lines.append(f"午餐选择「{food_name}」升糖较快，建议饭后20分钟散步来帮助控制餐后血糖。")
    elif period == "dinner":
        lines.append(f"晚餐时间吃「{food_name}」。")
        if risk_weight >= 50:
            lines.append("晚餐后活动量通常较少，建议适当减量或饭后散步15-20分钟。")

    return "\n".join(lines)


def calculate_risk_weight(gi: float, gl: float, carb_g: float,
                          fiber_g: float, protein_g: float, fat_g: float,
                          time_modifier: float = 0.0) -> float:
    """
    将食物的 GI/GL/营养素转换为 0-100 的标准化风险权重。

    公式:
      base = GL / MAX_GL_REFERENCE * 100
      fiber_discount = min(fiber_g * 2, 15)      # 纤维最多减 15 分
      protein_discount = min(protein_g * 0.5, 10) # 蛋白质最多减 10 分
      fat_slow = min(fat_g * 0.3, 5)              # 脂肪减缓吸收最多减 5 分
      risk = base - fiber_discount - protein_discount - fat_slow
    """
    base = (gl / MAX_GL_REFERENCE) * 100.0
    fiber_discount = min(fiber_g * 2.0, 15.0)
    protein_discount = min(protein_g * 0.5, 10.0)
    fat_slow = min(fat_g * 0.3, 5.0)
    risk = base - fiber_discount - protein_discount - fat_slow + time_modifier
    return round(max(0, min(100, risk)), 1)


def risk_level_label(risk: float) -> str:
    if risk < 25:
        return "low"
    elif risk < 50:
        return "medium"
    elif risk < 75:
        return "high"
    else:
        return "very_high"


def lookup_food(food_name: str) -> Optional[dict]:
    """查询食物信息：SQLite 缓存 → 精确匹配 → 拆词组合估算 → 向量搜索。"""
    # === 第零步：SQLite 缓存命中 ===
    cached = database.get_cached_food(food_name)
    if cached:
        return {k: v for k, v in cached.items() if k not in ("id", "created_at")}

    all_foods = _load_all_foods()

    # === 第一步：精确匹配 ===
    from query_food import exact_match
    exact = exact_match(food_name, all_foods, max_results=1)
    if exact:
        food = exact[0]
        matched_name = food["food_name"]

        # 如果查询词≠匹配结果，且查询词包含主食后缀，优先走拆词
        # 例如"鸡排饭"匹配到"鸡排"，但"饭"部分被漏掉了
        staple_suffixes = ["饭", "面", "粉", "粥", "饼", "糕"]
        query_has_staple = any(s in food_name for s in staple_suffixes)
        match_has_staple = any(s in matched_name for s in staple_suffixes)

        if food_name != matched_name and query_has_staple and not match_has_staple:
            # 查询词有主食后缀但匹配结果没有 → 优先拆词
            combo = _try_combo_estimate(food_name, all_foods)
            if combo and combo.get("carb_g", 0) > food.get("macro", {}).get("carb_g", 0):
                return combo

        macro = food.get("macro", {})
        return {
            "food_name": food["food_name"],
            "gi_value": food["gi_value"],
            "gi_level": food["gi_level"],
            "gl_per_serving": food["gl_per_serving"],
            "serving_size_g": food["serving_size_g"],
            "carb_g": macro.get("carb_g", 0),
            "protein_g": macro.get("protein_g", 0),
            "fat_g": macro.get("fat_g", 0),
            "fiber_g": macro.get("fiber_g", 0),
            "regional_tag": food["regional_tag"],
            "food_category": food["food_category"],
            "counter_strategy": food["counter_strategy"],
            "data_source": food["data_source"],
        }

    # === 第二步：拆词组合估算 ===
    # 尝试把复合食物名拆成子词，分别查找，加权合并
    combo = _try_combo_estimate(food_name, all_foods)
    if combo:
        return combo

    # === 第三步：向量语义搜索（兜底） ===
    import subprocess
    venv_python = os.path.expanduser(
        "~/.openclaw/workspace/skills/food-gi-rag/.venv/bin/python3"
    )
    query_script = os.path.join(SKILLS_DIR, "food-gi-rag", "scripts", "query_food.py")
    try:
        result = subprocess.run(
            [venv_python, query_script, food_name, "--json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            parsed = json.loads(result.stdout)
            items = parsed if isinstance(parsed, list) else parsed.get("results", [])
            if items:
                item = items[0]
                # 语义搜索结果验证：至少要有1个共同汉字，防止完全不相关的匹配
                # 例如"旺仔小馒头"不应匹配"小龙虾"，"蛋卷"不应匹配"春卷"
                matched_food = item.get("food_name", "")
                matched_core = matched_food.split("(")[0].split("（")[0].strip()
                query_chars = set(food_name)
                match_chars = set(matched_core)
                common_chars = query_chars & match_chars
                # 去掉无意义的单字（的、小、大、老等）再算重叠
                trivial_chars = set("的小大老新鲜")
                meaningful_common = common_chars - trivial_chars
                if len(meaningful_common) >= 1:
                    return item
                # 没有有意义的共同字符 → 丢弃，视为未找到
    except Exception:
        pass

    # === 第四步：DeepSeek AI 查询（兜底） ===
    ai_result = _deepseek_food_lookup(food_name)
    if ai_result:
        _cache_food_to_db(ai_result)
        return ai_result

    return None


def _deepseek_food_lookup(food_name: str) -> Optional[dict]:
    """调用 DeepSeek AI 估算食物的 GI/GL/营养素数据（兜底方案）。"""
    system_prompt = (
        "你是一个食物营养数据库专家。用户会给你一个食物名称，"
        "请返回该食物的升糖指数(GI)和营养信息。\n"
        "必须返回严格的 JSON，不要有任何其他文字。字段如下：\n"
        "{\n"
        '  "food_name": "食物名称",\n'
        '  "gi_value": 整数(0-100),\n'
        '  "gi_level": "低"或"中"或"高",\n'
        '  "gl_per_serving": 数值,\n'
        '  "serving_size_g": 整数(常见一份的克数),\n'
        '  "carb_g": 数值(每份碳水化合物克数),\n'
        '  "protein_g": 数值(每份蛋白质克数),\n'
        '  "fat_g": 数值(每份脂肪克数),\n'
        '  "fiber_g": 数值(每份膳食纤维克数),\n'
        '  "regional_tag": "全国",\n'
        '  "food_category": "食物分类",\n'
        '  "counter_strategy": "简短的饮食建议"\n'
        "}\n"
        "gi_level 规则：GI≤55为低，56-69为中，≥70为高。\n"
        "如果你完全不认识这个食物或它不是食物，返回 null。"
    )
    try:
        resp = _deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": food_name},
            ],
            temperature=0.1,
            timeout=10,
        )
        content = resp.choices[0].message.content.strip()
        # 去掉可能的 markdown 代码块标记
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3].strip()
        if content == "null" or content == "None":
            return None
        data = json.loads(content)
        if not isinstance(data, dict):
            return None
        # 基础校验
        gi = data.get("gi_value")
        if gi is None or not (0 <= gi <= 100):
            return None
        if not data.get("food_name"):
            return None
        # 补充 data_source
        data["data_source"] = "DeepSeek AI 估算"
        return data
    except Exception:
        return None


def _cache_food_to_db(food_data: dict):
    """将 AI 返回的食物数据缓存到 SQLite food_cache 表。"""
    global _ALL_FOODS
    try:
        database.cache_food(food_data)
        # 同时追加到内存缓存以便当次会话可用
        db_entry = {
            "food_name": food_data["food_name"],
            "aliases": [food_data["food_name"]],
            "gi_value": food_data["gi_value"],
            "gi_level": food_data["gi_level"],
            "gl_per_serving": food_data["gl_per_serving"],
            "serving_size_g": food_data["serving_size_g"],
            "macro": {
                "carb_g": food_data.get("carb_g", 0),
                "protein_g": food_data.get("protein_g", 0),
                "fat_g": food_data.get("fat_g", 0),
                "fiber_g": food_data.get("fiber_g", 0),
            },
            "regional_tag": food_data.get("regional_tag", "全国"),
            "food_category": food_data.get("food_category", "其他"),
            "counter_strategy": food_data.get("counter_strategy", ""),
            "data_source": food_data.get("data_source", "DeepSeek AI 估算"),
        }
        all_foods = _load_all_foods()
        all_foods.append(db_entry)
    except Exception:
        pass


def _try_combo_estimate(food_name: str, all_foods: list) -> Optional[dict]:
    """拆词组合估算：把'炸鸡咖喱饭'拆成'炸鸡'+'咖喱'+'饭'，分别查找后加权合并。
    注意：如果食物名能被精确匹配（完全匹配或别名匹配），不应走拆词路径。
    """
    from query_food import exact_match

    # 先检查是否能整体精确匹配 — 如果能，不拆词
    whole_match = exact_match(food_name, all_foods, max_results=1)
    if whole_match:
        matched_name = whole_match[0]["food_name"]
        # 如果整体匹配命中（food_name完全匹配 or 别名完全匹配），直接返回None让调用方用精确结果
        if (food_name.lower() == matched_name.lower() or
                food_name.lower() in [a.lower() for a in whole_match[0].get("aliases", [])]):
            return None

    # 常见食物词根，用于拆词（长词优先匹配，避免"面"误吞"面条"）
    food_keywords = [
        # 主食（长词优先）
        "糙米饭", "米饭", "白饭", "面条", "拉面", "米粉", "河粉", "凉皮",
        "馒头", "包子", "饺子", "馄饨", "烧饼", "煎饼", "披萨", "吐司", "面包",
        # 单字主食（最后匹配）
        "饭", "面", "粉", "粥",
        # 烹饪方式+食材
        "炸鸡", "烤鸡", "鸡排", "鸡腿", "鸡翅", "鸡肉", "鸡块",
        "牛肉", "猪肉", "羊肉", "排骨", "五花肉",
        "豆腐", "鸡蛋",
        # 海鲜
        "鱼", "虾", "蟹", "鱿鱼",
        # 调味/菜式
        "咖喱", "红烧", "糖醋", "鱼香", "宫保", "麻辣", "酸辣",
        "番茄", "土豆", "青椒", "洋葱", "白菜", "茄子",
        # 饮品
        "牛奶", "豆浆", "酸奶", "奶茶", "咖啡", "可乐", "果汁",
    ]

    # 单字词映射到标准食物名（因为 exact_match 要求 >=2 字符）
    single_char_map = {
        "面": "面条", "饭": "白米饭", "粉": "米粉", "粥": "白粥",
        "鱼": "鱼(清蒸)", "虾": "虾(白灼)", "蟹": "螃蟹",
    }

    matched_parts = []
    matched_names = set()
    remaining = food_name
    for kw in sorted(food_keywords, key=len, reverse=True):
        if kw in remaining:
            lookup_kw = single_char_map.get(kw, kw)
            result = exact_match(lookup_kw, all_foods, max_results=1)
            if result:
                food = result[0]
                # 避免同一食物被多个关键词重复匹配
                if food["food_name"] in matched_names:
                    remaining = remaining.replace(kw, "", 1)
                    continue
                matched_names.add(food["food_name"])
                macro = food.get("macro", {})
                matched_parts.append({
                    "name": food["food_name"],
                    "gi": food["gi_value"],
                    "carb_g": macro.get("carb_g", 0),
                    "protein_g": macro.get("protein_g", 0),
                    "fat_g": macro.get("fat_g", 0),
                    "fiber_g": macro.get("fiber_g", 0),
                    "regional_tag": food["regional_tag"],
                    "food_category": food["food_category"],
                })
                remaining = remaining.replace(kw, "", 1)

    if len(matched_parts) < 2:
        return None

    # 加权合并：按碳水量加权计算综合 GI
    total_carb = sum(p["carb_g"] for p in matched_parts)
    if total_carb == 0:
        weighted_gi = sum(p["gi"] for p in matched_parts) / len(matched_parts)
    else:
        weighted_gi = sum(p["gi"] * p["carb_g"] / total_carb for p in matched_parts)

    total_protein = sum(p["protein_g"] for p in matched_parts)
    total_fat = sum(p["fat_g"] for p in matched_parts)
    total_fiber = sum(p["fiber_g"] for p in matched_parts)
    gl = round(weighted_gi * total_carb / 100, 1)

    gi_level = "高" if weighted_gi > 70 else ("中" if weighted_gi > 55 else "低")
    part_names = " + ".join(p["name"] for p in matched_parts)

    return {
        "food_name": f"{food_name} (组合估算)",
        "gi_value": round(weighted_gi),
        "gi_level": gi_level,
        "gl_per_serving": gl,
        "serving_size_g": 350,
        "carb_g": total_carb,
        "protein_g": total_protein,
        "fat_g": total_fat,
        "fiber_g": total_fiber,
        "regional_tag": matched_parts[0]["regional_tag"],
        "food_category": matched_parts[0]["food_category"],
        "counter_strategy": f"组合估算({part_names})；建议减少主食量，增加蔬菜蛋白",
        "data_source": f"组合估算: {part_names}",
    }


# ─── 地域感知食物数据库 ─────────────────────────
FOODS_DB_PATH = os.path.join(SKILLS_DIR, "food-gi-rag", "data", "foods_500.json")
_ALL_FOODS = None

REGION_AFFINITY = {
    "武汉": ["湖北", "湖南", "江西"],
    "湖北": ["武汉", "湖南", "江西"],
    "湖南": ["湖北", "武汉", "贵州", "江西"],
    "广东": ["广西", "华南", "福建", "海南"],
    "广西": ["广东", "华南", "云南"],
    "福建": ["广东", "华南", "江浙"],
    "四川": ["重庆", "贵州", "云南", "西南"],
    "重庆": ["四川", "贵州", "西南"],
    "贵州": ["四川", "云南", "湖南", "西南"],
    "云南": ["四川", "贵州", "广西", "西南"],
    "江浙": ["上海", "杭州", "浙江", "安徽", "南方"],
    "上海": ["江浙", "杭州", "浙江"],
    "杭州": ["江浙", "上海", "浙江"],
    "浙江": ["江浙", "上海", "杭州"],
    "北京": ["北方", "天津", "河北"],
    "天津": ["北京", "北方", "河北"],
    "东北": ["北方", "内蒙古"],
    "北方": ["北京", "东北", "天津", "河北", "山西"],
    "山西": ["北方", "陕西", "河南"],
    "陕西": ["山西", "甘肃", "西北", "河南"],
    "河南": ["山西", "陕西", "北方", "湖北"],
    "甘肃": ["陕西", "西北", "宁夏", "新疆"],
    "西北": ["陕西", "甘肃", "新疆", "宁夏"],
    "新疆": ["西北", "甘肃"],
    "海南": ["广东", "热带", "华南"],
    "热带": ["海南", "广东", "广西"],
    "内蒙古": ["东北", "北方", "西北"],
    "西藏": ["西北", "四川"],
    "全国": [],
}


def _load_all_foods():
    global _ALL_FOODS
    if _ALL_FOODS is None:
        with open(FOODS_DB_PATH, "r", encoding="utf-8") as f:
            _ALL_FOODS = json.load(f)
    return _ALL_FOODS


def lookup_regional_low_gi(source_region: str, source_category: str,
                           source_name: str, max_results: int = 10) -> list:
    """按地域亲和度查询低GI对冲食物，优先推荐同地域食物。"""
    all_foods = _load_all_foods()
    low_gi = [f for f in all_foods if f["gi_value"] <= 55]

    source_core = source_name.split("(")[0].split("（")[0].strip()
    affinity = REGION_AFFINITY.get(source_region, [])

    # 按优先级分桶
    same_region_same_cat = []
    same_region_diff_cat = []
    affinity_region = []
    national = []

    for f in low_gi:
        core = f["food_name"].split("(")[0].split("（")[0].strip()
        if core == source_core:
            continue
        r = f["regional_tag"]
        cat = f["food_category"]
        if cat == "调味品":
            continue

        if r == source_region and cat == source_category:
            same_region_same_cat.append(f)
        elif r == source_region:
            same_region_diff_cat.append(f)
        elif r in affinity:
            affinity_region.append(f)
        elif r == "全国":
            national.append(f)

    # 合并去重
    result = []
    seen_cores = set()
    for bucket in [same_region_same_cat, same_region_diff_cat,
                   affinity_region, national]:
        for f in bucket:
            core = f["food_name"].split("(")[0].split("（")[0].strip()
            if core not in seen_cores:
                seen_cores.add(core)
                # 转为 query_food.py --json 兼容的 flat dict
                macro = f.get("macro", {})
                result.append({
                    "food_name": f["food_name"],
                    "gi_value": f["gi_value"],
                    "gi_level": f["gi_level"],
                    "gl_per_serving": f["gl_per_serving"],
                    "serving_size_g": f["serving_size_g"],
                    "carb_g": macro.get("carb_g", 0),
                    "protein_g": macro.get("protein_g", 0),
                    "fat_g": macro.get("fat_g", 0),
                    "fiber_g": macro.get("fiber_g", 0),
                    "regional_tag": f["regional_tag"],
                    "food_category": f["food_category"],
                    "counter_strategy": f["counter_strategy"],
                    "data_source": f["data_source"],
                })
            if len(result) >= max_results:
                break
        if len(result) >= max_results:
            break

    return result


def build_food_item(raw: dict, risk: float = 0) -> FoodItem:
    return FoodItem(
        name=raw.get("food_name", "Unknown"),
        gi=raw.get("gi_value", 0),
        gl=raw.get("gl_per_serving", 0),
        carb_g=raw.get("carb_g", 0),
        protein_g=raw.get("protein_g", 0),
        fat_g=raw.get("fat_g", 0),
        fiber_g=raw.get("fiber_g", 0),
        serving_size_g=raw.get("serving_size_g", 0),
        category=raw.get("food_category", ""),
        risk_weight=risk,
    )


# 每类别对冲食物的合理推荐克数上限
MAX_SERVING = {
    "蔬菜": 100, "菌菇": 80, "豆类": 80, "坚果": 30,
    "水果": 100, "肉类": 50, "奶类": 200, "饮料": 250,
    "蛋类": 60, "主食": 100, "谷物": 50, "薯类": 100,
}


def _get_serving_label(category: str, grams: int, food_name: str) -> str:
    """将克数转为语义化描述。"""
    FOOD_SPECIFIC = {
        "豆腐": "约1/4块", "魔芋": "几片", "黄瓜": "半根",
        "西红柿": "1个", "番茄": "1个", "鸡蛋": "1个", "牛奶": "1杯",
        "豆浆": "1杯", "西兰花": "小半朵",
    }
    for key, label in FOOD_SPECIFIC.items():
        if key in food_name:
            return label
    labels = {
        "蔬菜": "1小把", "菌菇": "1小碟", "豆类": "适量",
        "坚果": "一小把", "水果": "约半个", "肉类": "薄切几片",
        "奶类": "1杯", "饮料": "1杯",
    }
    return labels.get(category, "适量")


def generate_food_counters(risk_weight: float, source_food: dict) -> List[CounterSolution]:
    """生成饮食对冲方案：按地域推荐低 GI 配菜来平衡高 GI 主食。"""
    solutions = []

    source_region = source_food.get("regional_tag", "全国")
    source_category = source_food.get("food_category", "")
    source_name = source_food.get("food_name", "")

    # 1. 如果原食物有 counter_strategy，先把它拆出来
    counter_text = source_food.get("counter_strategy", "")
    if counter_text:
        solutions.append(CounterSolution(
            type="food",
            name="原食物自带对冲",
            description=counter_text,
            balance_weight=round(risk_weight * 0.15, 1),
            group="烹饪技巧",
            details={"source": "counter_strategy field"},
        ))

    # 2. 按地域查询低GI食物，优先推荐同地域特色食物
    low_gi_foods = lookup_regional_low_gi(
        source_region, source_category, source_name, max_results=15
    )

    # 按类别分组推荐，避免全是同一类
    category_budget = {"蔬菜": 2, "豆类": 1, "坚果": 1, "饮料": 1, "水果": 1,
                       "菌菇": 1, "肉类": 1, "奶类": 1}
    category_count = {}

    # 食物类别 → group 名称映射
    CATEGORY_TO_GROUP = {
        "蔬菜": "蔬菜搭配",
        "菌菇": "蔬菜搭配",
        "豆类": "蛋白搭配",
        "肉类": "蛋白搭配",
        "奶类": "蛋白搭配",
        "蛋类": "蛋白搭配",
        "主食": "主食替换",
        "谷物": "主食替换",
        "米制品": "主食替换",
        "面食": "主食替换",
        "面点": "主食替换",
        "粥类": "主食替换",
        "薯类": "主食替换",
        "杂粮": "主食替换",
        "饮料": "汤饮搭配",
        "汤": "汤饮搭配",
        "水果": "蔬菜搭配",
        "坚果": "蛋白搭配",
    }

    for item in low_gi_foods:
        cat = item.get("food_category", "其他")
        # 跳过调味品
        if cat == "调味品":
            continue
        if category_count.get(cat, 0) >= category_budget.get(cat, 1):
            continue

        gi = item.get("gi_value", 50)
        gl = item.get("gl_per_serving", 10)
        fiber = item.get("fiber_g", 0)
        protein = item.get("protein_g", 0)

        # 计算这个配菜能抵消多少风险
        # 高纤维、高蛋白的低 GI 食物效果更好
        fiber_effect = min(fiber * 3.0, 15.0)
        protein_effect = min(protein * 1.5, 10.0)
        gi_bonus = max(0, (55 - gi) / 55.0) * 10.0  # GI 越低加分越多
        balance = round(fiber_effect + protein_effect + gi_bonus, 1)
        balance = min(balance, 35.0)  # 单个食物最多抵消 35 分

        name = item.get("food_name", "")
        serving = item.get("serving_size_g", 0)
        counter = item.get("counter_strategy", "")
        desc = f"GI {gi}({item.get('gi_level', '')}) | "
        desc += f"纤维 {fiber}g 蛋白质 {protein}g | "
        if counter:
            desc += counter

        group = CATEGORY_TO_GROUP.get(cat, "其他搭配")

        capped_serving = int(min(serving, MAX_SERVING.get(cat, 150))) if serving else 0
        label = _get_serving_label(cat, capped_serving, name)
        counter_name = f"搭配 {name}"
        if capped_serving:
            counter_name += f" · {label}({capped_serving}g)"

        solutions.append(CounterSolution(
            type="food",
            name=counter_name,
            description=desc,
            balance_weight=balance,
            group=group,
            details={
                "food_name": name,
                "gi": gi,
                "gl": gl,
                "fiber_g": fiber,
                "protein_g": protein,
            },
        ))
        category_count[cat] = category_count.get(cat, 0) + 1

    return solutions


def generate_exercise_counters(risk_weight: float) -> List[CounterSolution]:
    """生成运动对冲方案。"""
    solutions = []
    for ex in EXERCISE_OPTIONS:
        # 运动平衡权重：基于 MET * duration，缩放到风险等级
        raw_effect = ex["met"] * ex["duration_min"] / 60.0 * 15.0
        balance = round(min(raw_effect, 40.0), 1)

        group = "运动"

        solutions.append(CounterSolution(
            type="exercise",
            name=ex["name"],
            description=ex["description"],
            balance_weight=balance,
            group=group,
            details={
                "met": ex["met"],
                "duration_min": ex["duration_min"],
                "kcal_approx": ex["kcal_approx"],
            },
        ))
    return solutions


def _classify_food_role(sol: CounterSolution) -> str:
    """将对冲食物分类为用餐顺序角色。"""
    name = sol.name.replace("搭配 ", "").split(" (")[0]  # 提取纯食物名
    group = sol.group
    details = sol.details or {}
    fiber = details.get("fiber_g", 0)
    protein = details.get("protein_g", 0)
    gi = details.get("gi", 50)

    # 蔬菜/菌菇类 → 先吃（高纤维打底）
    if group == "蔬菜搭配":
        return "vegetable"
    # 蛋白类（豆/肉/奶/蛋/坚果）→ 中间吃
    if group == "蛋白搭配":
        return "protein"
    # 汤饮类 → 餐前或餐中
    if group == "汤饮搭配":
        return "soup"
    # 主食替换 → 最后吃
    if group == "主食替换":
        return "staple"
    # 烹饪技巧 → 贯穿全程
    if group == "烹饪技巧":
        return "technique"
    # 兜底：高纤维当蔬菜，高蛋白当蛋白，其他当配菜
    if fiber >= 3:
        return "vegetable"
    if protein >= 5:
        return "protein"
    return "side"


def _build_meal_plan(food_name: str, food_sols: List[CounterSolution],
                     exercise_sols: List[CounterSolution],
                     meal_ctx: Optional[dict] = None,
                     risk_weight: float = 0) -> str:
    """根据用户选择的对冲食物和运动，生成结构化用餐方案。"""
    period = (meal_ctx or {}).get("period", "")
    label = (meal_ctx or {}).get("label", "")

    # 按角色分类所有对冲食物
    roles = {}
    for sol in food_sols:
        role = _classify_food_role(sol)
        roles.setdefault(role, []).append(sol)

    plan_lines = ["", "🍽️ 推荐用餐方案："]
    step = 1

    def _short_name(sol: CounterSolution) -> str:
        return sol.name.replace("搭配 ", "")

    # ── 第一步：汤饮打底（如果有）──
    if "soup" in roles:
        soup_names = "、".join(_short_name(s) for s in roles["soup"])
        plan_lines.append(f"  Step {step}. 餐前先喝 {soup_names}")
        plan_lines.append(f"         → 温热汤饮能激活消化酶，延缓后续碳水吸收")
        step += 1

    # ── 第二步：蔬菜先行 ──
    if "vegetable" in roles:
        veg_names = "、".join(_short_name(s) for s in roles["vegetable"])
        total_fiber = sum(s.details.get("fiber_g", 0) for s in roles["vegetable"])
        plan_lines.append(f"  Step {step}. 先吃蔬菜：{veg_names}")
        reason = "膳食纤维在胃中形成凝胶层，减缓糖分进入血液的速度"
        if total_fiber >= 5:
            reason += f"（共约 {total_fiber:.0f}g 纤维）"
        plan_lines.append(f"         → {reason}")
        step += 1

    # ── 第三步：蛋白质 ──
    if "protein" in roles:
        prot_names = "、".join(_short_name(s) for s in roles["protein"])
        total_protein = sum(s.details.get("protein_g", 0) for s in roles["protein"])
        plan_lines.append(f"  Step {step}. 再吃蛋白质：{prot_names}")
        reason = "蛋白质刺激 GLP-1 分泌，延缓胃排空"
        if total_protein >= 8:
            reason += f"（共约 {total_protein:.0f}g 蛋白质）"
        plan_lines.append(f"         → {reason}")
        step += 1

    # ── 第四步：主食/高碳水最后吃 ──
    # 主食替换 + 原食物
    staple_names = []
    if "staple" in roles:
        staple_names.extend(_short_name(s) for s in roles["staple"])
    staple_names.append(food_name)  # 原食物始终是主角
    plan_lines.append(f"  Step {step}. 最后吃主食：{' 或 '.join(staple_names)}")
    plan_lines.append(f"         → 先吃菜和蛋白后再吃碳水，血糖峰值可降低约 30-40%")
    step += 1

    # ── 烹饪技巧贯穿 ──
    if "technique" in roles:
        tech_descs = "；".join(s.description for s in roles["technique"] if s.description)
        if tech_descs:
            plan_lines.append(f"  * 烹饪提示：{tech_descs}")

    # ── 其他配菜穿插 ──
    if "side" in roles:
        side_names = "、".join(_short_name(s) for s in roles["side"])
        plan_lines.append(f"  * 可穿插搭配：{side_names}")

    # ── 餐后运动建议 ──
    if exercise_sols:
        plan_lines.append("")
        plan_lines.append("🏃 餐后消食建议：")
        names = "、".join(s.name for s in exercise_sols)
        if period == "late_snack":
            plan_lines.append(f"  · 饭后 10-15 分钟：{names}（夜间宜轻柔，避免影响睡眠）")
        elif period == "breakfast":
            plan_lines.append(f"  · 饭后 15-30 分钟：{names}（早餐后活动帮助唤醒身体代谢）")
        else:
            plan_lines.append(f"  · 饭后 15-30 分钟：{names}（餐后运动抑制血糖快速攀升）")

        # 运动时长与消耗提示
        total_kcal = sum(s.details.get("kcal_approx", 0) for s in exercise_sols)
        total_min = sum(s.details.get("duration_min", 0) for s in exercise_sols)
        if total_kcal > 0:
            plan_lines.append(f"  → 预计总运动约 {total_min} 分钟，消耗约 {total_kcal} kcal")
    else:
        # 没选运动也给一个通用消食建议
        plan_lines.append("")
        plan_lines.append("🏃 餐后消食建议：")
        if period == "late_snack":
            plan_lines.append("  · 饭后可原地站立或缓慢踱步 10 分钟，避免立即躺下")
        elif period == "midnight":
            plan_lines.append("  · 深夜进食后建议至少保持直立姿势 15-20 分钟再休息")
        else:
            plan_lines.append("  · 建议饭后散步 10-15 分钟，哪怕是短距离走动也能帮助降低餐后血糖峰值")

    return "\n".join(plan_lines)


def generate_counterbalance_advice(food_name: str, risk_weight: float,
                                   selected_solutions: List[CounterSolution],
                                   meal_ctx: Optional[dict] = None) -> str:
    """生成 Coordinator 综合建议。注意使用非绝对化的建议性措辞。含时间上下文。"""
    total_balance = sum(s.balance_weight for s in selected_solutions)
    lines = []

    # 时间上下文前缀
    period = (meal_ctx or {}).get("period", "")
    label = (meal_ctx or {}).get("label", "")
    if label:
        lines.append(f"当前时段：{label}")

    if risk_weight < 25:
        lines.append(f"{food_name}的血糖负荷相对较低，通常对血糖影响有限。")
    elif risk_weight < 50:
        lines.append(f"{food_name}对血糖有一定影响，建议搭配低GI配菜来帮助缓冲。")
    elif risk_weight < 75:
        lines.append(f"{food_name}升糖较快，建议做好饮食和运动搭配。")
    else:
        lines.append(f"{food_name}对血糖影响较大，建议结合以下方案进行综合管理。")

    # 基于时段的血糖预测提示
    if period in ("afternoon_snack", "morning_snack"):
        lines.append(f"加餐时段进食会在当前基础上叠加血糖波动，预计餐后30分钟血糖可能额外升高1-3 mmol/L。")
    elif period == "late_snack":
        lines.append("夜间胰岛素敏感性下降约20-30%，同等食物的血糖峰值可能比白天高出1.5-2 mmol/L。")
    elif period == "midnight":
        lines.append("深夜进食时身体代谢最低，血糖峰值可能比正常用餐时高出2-3 mmol/L，且恢复更慢。")
    elif period == "breakfast" and risk_weight >= 50:
        lines.append("早晨皮质醇高峰期胰岛素抵抗较强，餐后血糖峰值可能比午餐同等食物高1-2 mmol/L。")

    food_sols = [s for s in selected_solutions if s.type == "food"]
    exercise_sols = [s for s in selected_solutions if s.type == "exercise"]

    if not selected_solutions:
        lines.append("请从右侧方案中选择搭配来对冲血糖风险。")
    else:
        # 对冲覆盖分析
        if total_balance >= risk_weight:
            lines.append(f"当前方案总对冲 {total_balance:.0f} 分，已覆盖风险权重 {risk_weight:.0f} 分，组合较为合理。")
        else:
            gap = round(risk_weight - total_balance, 1)
            coverage = round(total_balance / risk_weight * 100) if risk_weight > 0 else 0
            lines.append(f"当前方案对冲 {total_balance:.0f}/{risk_weight:.0f} 分（覆盖 {coverage}%），还差约 {gap} 分，可考虑再加一项搭配。")

        # 生成结构化用餐方案
        meal_plan = _build_meal_plan(food_name, food_sols, exercise_sols, meal_ctx, risk_weight)
        lines.append(meal_plan)

    lines.append("")
    lines.append("⚠️ 以上建议仅供参考，不构成医疗建议。请遵医嘱，结合个人血糖监测数据调整饮食。")

    return "\n".join(lines)


# ─── 核心分析逻辑 ────────────────────────────

def run_analysis(req: AnalyzeRequest) -> AnalyzeResponse:
    """执行完整的 SugarClaw 分析流水线。"""
    traces = []
    t0 = datetime.now()

    # Step 1: 食物 GI/GL 查询
    gi, gl = req.gi, req.gl
    food_info = None
    if req.food and gi == 0:
        t_start = datetime.now()
        food_info = query_food_gi(req.food)
        if food_info:
            results = food_info.get("results", [])
            if results:
                top = results[0]
                gi = top.get("gi_value", gi)
                gl = top.get("gl_per_serving", gl)
        elapsed = int((datetime.now() - t_start).total_seconds() * 1000)
        traces.append(AgentTrace(
            agent="Regional Dietitian",
            action=f"query_food_gi('{req.food}')",
            result=f"GI={gi}, GL={gl}" if gi > 0 else "未找到匹配食物",
            duration_ms=elapsed,
        ))

    # Step 1.5: ISF 为空时从数据库读用户 ISF
    isf = req.isf
    if isf is None or isf == 0:
        user = database.get_user(1)
        if user and user.get("isf"):
            isf = user["isf"]

    # Step 2: 自动选择滤波器 + 运行
    t_start = datetime.now()
    filter_type, kf = kf_engine.auto_select_filter(
        req.readings, event=req.event,
        dose=req.dose, isf=isf,
        gi=gi, gl=gl,
    )
    filtered = kf.filter(req.readings)
    predictions_raw = kf.forecast(6)
    current_glucose = round(filtered[-1], 2)
    elapsed = int((datetime.now() - t_start).total_seconds() * 1000)
    traces.append(AgentTrace(
        agent="Physiological Analyst",
        action=f"kalman_filter(type={filter_type}, readings={len(req.readings)})",
        result=f"current={current_glucose} mmol/L, trend={kf_engine.trend_arrow(predictions_raw)}",
        duration_ms=elapsed,
    ))

    # Step 3: 生成预警
    t_start = datetime.now()
    alerts_raw = kf_engine.generate_alerts(predictions_raw, current_glucose)
    alerts = [Alert(
        level=a["level"],
        type=a["type"],
        message=a["message"],
        time_minutes=a.get("time_minutes"),
    ) for a in alerts_raw]
    elapsed = int((datetime.now() - t_start).total_seconds() * 1000)
    traces.append(AgentTrace(
        agent="Alert System",
        action="generate_alerts(predictions, current_glucose)",
        result=f"{len(alerts)} alert(s)" if alerts else "No alerts",
        duration_ms=elapsed,
    ))

    # Step 4: 构建图表数据
    now = datetime.now()
    # 历史读数时间轴（每 5 分钟一个，倒推）
    history_times = [
        (now - timedelta(minutes=5 * (len(req.readings) - 1 - i))).isoformat()
        for i in range(len(req.readings))
    ]
    # 预测时间轴
    prediction_times = [
        (now + timedelta(minutes=5 * (i + 1))).isoformat()
        for i in range(len(predictions_raw))
    ]

    predictions = [PredictionPoint(
        time_offset_min=(i + 1) * 5,
        glucose=p["glucose"],
        ci_low=p["ci_low"],
        ci_high=p["ci_high"],
        sigma=p["sigma"],
    ) for i, p in enumerate(predictions_raw)]

    chart_data = {
        "history": {
            "timestamps": history_times,
            "raw": req.readings,
            "filtered": [round(f, 2) for f in filtered],
        },
        "prediction": {
            "timestamps": prediction_times,
            "values": [p["glucose"] for p in predictions_raw],
            "ci_low": [p["ci_low"] for p in predictions_raw],
            "ci_high": [p["ci_high"] for p in predictions_raw],
        },
        "zones": {
            "hypo_critical": 3.0,
            "hypo_warning": 3.9,
            "target_low": 3.9,
            "target_high": 10.0,
            "hyper_warning": 10.0,
            "hyper_critical": 13.9,
        },
    }

    # Step 5: 生成综合建议
    t_start = datetime.now()
    advice = generate_advice(
        filter_type, current_glucose, predictions_raw,
        alerts_raw, req.event, req.food,
    )
    elapsed = int((datetime.now() - t_start).total_seconds() * 1000)
    traces.append(AgentTrace(
        agent="Coordinator",
        action="generate_advice(analysis_results)",
        result=advice[:80] + "..." if len(advice) > 80 else advice,
        duration_ms=elapsed,
    ))

    total_ms = int((datetime.now() - t0).total_seconds() * 1000)
    traces.append(AgentTrace(
        agent="Task Orchestrator",
        action="pipeline_complete",
        result=f"Total {total_ms}ms, {len(traces)} agents invoked",
        duration_ms=total_ms,
    ))

    return AnalyzeResponse(
        filter_type=filter_type,
        current_glucose=current_glucose,
        trend=kf_engine.trend_arrow(predictions_raw),
        filtered_readings=[round(f, 2) for f in filtered],
        predictions=predictions,
        alerts=alerts,
        chart_data=chart_data,
        advice=advice,
        agent_traces=traces,
        timestamp=now.isoformat(),
    )


# ─── FastAPI App ────────────────────────────

app = FastAPI(
    title="SugarClaw API",
    description="SugarClaw MVP — 卡尔曼滤波血糖预测 + 多智能体分析",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动时初始化 SQLite
database.init_db()


@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/cases", response_model=List[CaseInfo])
async def list_cases():
    """获取内置经典案例列表。"""
    return [
        CaseInfo(
            id=c["id"], title=c["title"],
            description=c["description"], scenario=c["scenario"],
        )
        for c in BUILTIN_CASES.values()
    ]


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    """手动输入模式：提交血糖读数 + 事件信息，返回完整分析。"""
    try:
        return run_analysis(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/replay", response_model=AnalyzeResponse)
async def replay(req: ReplayRequest):
    """历史回放模式：选择内置案例，返回完整分析。"""
    case = BUILTIN_CASES.get(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{req.case_id}' not found")
    analyze_req = AnalyzeRequest(
        readings=case["readings"],
        event=case.get("event"),
        food=case.get("food"),
        gi=case.get("gi", 0),
        gl=case.get("gl", 0),
        dose=case.get("dose", 0),
    )
    return run_analysis(analyze_req)


@app.get("/api/replay/stream/{case_id}")
async def replay_stream(case_id: str):
    """SSE 流式推送：逐个推送读数 + 每 3 个读数推送一次预测，模拟实时 CGM 流。"""
    case = BUILTIN_CASES.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    async def generate():
        readings = case["readings"]
        for i, r in enumerate(readings):
            # 推送当前读数
            point = {
                "type": "reading",
                "index": i,
                "total": len(readings),
                "glucose": r,
                "timestamp": (datetime.now() + timedelta(minutes=5 * i)).isoformat(),
            }
            yield f"data: {json.dumps(point, ensure_ascii=False)}\n\n"

            # 每积累 6 个读数后推送一次预测
            if i >= 5 and i % 3 == 0:
                window = readings[max(0, i - 11):i + 1]
                try:
                    analyze_req = AnalyzeRequest(
                        readings=window,
                        event=case.get("event"),
                        food=case.get("food"),
                        gi=case.get("gi", 0),
                        gl=case.get("gl", 0),
                        dose=case.get("dose", 0),
                    )
                    result = run_analysis(analyze_req)
                    prediction_event = {
                        "type": "prediction",
                        "index": i,
                        "analysis": result.dict(),
                    }
                    yield f"data: {json.dumps(prediction_event, ensure_ascii=False, default=str)}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

            await asyncio.sleep(0.8)

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ─── Counterbalance Scale Endpoints ──────────

@app.post("/api/scale/risk", response_model=CalculateRiskResponse)
async def calculate_risk(req: CalculateRiskRequest):
    """左盘：计算食物的风险权重（含时间上下文）。"""
    traces = []
    t0 = datetime.now()

    # Step 0: 推断用餐场景
    meal_ctx = infer_meal_context(req.query_time)
    if meal_ctx["label"]:
        traces.append(AgentTrace(
            agent="Coordinator",
            action=f"infer_meal_context('{req.query_time}')",
            result=f"场景={meal_ctx['label']}，时段风险修正+{meal_ctx['risk_modifier']}",
            duration_ms=0,
        ))

    # Step 1: 查询食物信息
    t_start = datetime.now()
    raw = lookup_food(req.food_name)
    elapsed = int((datetime.now() - t_start).total_seconds() * 1000)

    if not raw:
        traces.append(AgentTrace(
            agent="Regional Dietitian",
            action=f"lookup_food('{req.food_name}')",
            result="Not found in database",
            duration_ms=elapsed,
        ))
        raise HTTPException(status_code=404, detail=f"Food '{req.food_name}' not found")

    is_ai_estimated = "DeepSeek" in raw.get("data_source", "")
    source_tag = "（AI 估算）" if is_ai_estimated else ""
    traces.append(AgentTrace(
        agent="Regional Dietitian",
        action=f"lookup_food('{req.food_name}')",
        result=f"Found{source_tag}: {raw.get('food_name')} GI={raw.get('gi_value')} GL={raw.get('gl_per_serving')}",
        duration_ms=elapsed,
    ))

    # Step 2: 计算风险权重（含时间修正）
    t_start = datetime.now()
    risk = calculate_risk_weight(
        gi=raw.get("gi_value", 0),
        gl=raw.get("gl_per_serving", 0),
        carb_g=raw.get("carb_g", 0),
        fiber_g=raw.get("fiber_g", 0),
        protein_g=raw.get("protein_g", 0),
        fat_g=raw.get("fat_g", 0),
        time_modifier=meal_ctx["risk_modifier"],
    )
    # 乘以份数倍数，上限100
    if req.quantity_multiplier != 1.0:
        risk = round(min(risk * req.quantity_multiplier, 100.0), 1)

    level = risk_level_label(risk)
    elapsed = int((datetime.now() - t_start).total_seconds() * 1000)

    time_note = f"（含时段修正+{meal_ctx['risk_modifier']}）" if meal_ctx["risk_modifier"] > 0 else ""
    traces.append(AgentTrace(
        agent="Physiological Analyst",
        action="calculate_risk_weight(gi, gl, nutrients, time)",
        result=f"risk={risk}/100 ({level}){time_note}",
        duration_ms=elapsed,
    ))

    food = build_food_item(raw, risk)

    gi = raw.get("gi_value", 0)
    gl = raw.get("gl_per_serving", 0)
    detail = f"GI {gi} ({raw.get('gi_level', '')}) | GL {gl} | "
    detail += f"碳水 {raw.get('carb_g', 0)}g 纤维 {raw.get('fiber_g', 0)}g "
    detail += f"蛋白质 {raw.get('protein_g', 0)}g 脂肪 {raw.get('fat_g', 0)}g"

    # Step 3: 生成时间相关建议
    time_advice = generate_time_advice(meal_ctx, req.food_name, risk)

    return CalculateRiskResponse(
        food=food,
        risk_weight=risk,
        risk_level=level,
        risk_detail=detail,
        meal_context=meal_ctx["label"],
        time_advice=time_advice,
        agent_traces=traces,
    )


@app.post("/api/scale/balance", response_model=FindBalanceResponse)
async def find_balance(req: FindBalanceRequest):
    """右盘：生成对冲方案列表（含时间上下文）。"""
    traces = []
    t0 = datetime.now()

    # Step 0: 推断用餐场景
    meal_ctx = infer_meal_context(req.query_time)
    if meal_ctx["label"]:
        traces.append(AgentTrace(
            agent="Coordinator",
            action=f"infer_meal_context('{req.query_time}')",
            result=f"场景={meal_ctx['label']}",
            duration_ms=0,
        ))

    # Step 1: 如果没有提供 risk_weight，先计算
    t_start = datetime.now()
    raw = lookup_food(req.food_name)
    elapsed = int((datetime.now() - t_start).total_seconds() * 1000)

    if not raw:
        raise HTTPException(status_code=404, detail=f"Food '{req.food_name}' not found")

    traces.append(AgentTrace(
        agent="Regional Dietitian",
        action=f"lookup_food('{req.food_name}')",
        result=f"Found: {raw.get('food_name')} GI={raw.get('gi_value')} GL={raw.get('gl_per_serving')}",
        duration_ms=elapsed,
    ))

    risk = req.risk_weight
    if risk <= 0:
        risk = calculate_risk_weight(
            gi=raw.get("gi_value", 0),
            gl=raw.get("gl_per_serving", 0),
            carb_g=raw.get("carb_g", 0),
            fiber_g=raw.get("fiber_g", 0),
            protein_g=raw.get("protein_g", 0),
            fat_g=raw.get("fat_g", 0),
            time_modifier=meal_ctx["risk_modifier"],
        )

    food = build_food_item(raw, risk)

    # Step 2: 生成饮食对冲
    t_start = datetime.now()
    food_solutions = generate_food_counters(risk, raw)
    elapsed = int((datetime.now() - t_start).total_seconds() * 1000)
    traces.append(AgentTrace(
        agent="Dietary Specialist",
        action="generate_food_counters(risk, food_db)",
        result=f"{len(food_solutions)} dietary solutions",
        duration_ms=elapsed,
    ))

    # Step 3: 生成运动对冲
    t_start = datetime.now()
    exercise_solutions = generate_exercise_counters(risk)
    elapsed = int((datetime.now() - t_start).total_seconds() * 1000)
    traces.append(AgentTrace(
        agent="Physiological Analyst",
        action="generate_exercise_counters(risk)",
        result=f"{len(exercise_solutions)} exercise solutions",
        duration_ms=elapsed,
    ))

    all_solutions = food_solutions + exercise_solutions
    # 按 balance_weight 降序排列
    all_solutions.sort(key=lambda s: s.balance_weight, reverse=True)

    # Step 4: 生成初始建议（用户尚未选择方案，传空列表）
    t_start = datetime.now()
    advice = generate_counterbalance_advice(
        req.food_name, risk, [], meal_ctx=meal_ctx,
    )
    elapsed = int((datetime.now() - t_start).total_seconds() * 1000)
    traces.append(AgentTrace(
        agent="Coordinator",
        action="generate_counterbalance_advice(initial, no_selection)",
        result=advice[:80] + "..." if len(advice) > 80 else advice,
        duration_ms=elapsed,
    ))

    total_ms = int((datetime.now() - t0).total_seconds() * 1000)
    traces.append(AgentTrace(
        agent="Task Orchestrator",
        action="counterbalance_pipeline_complete",
        result=f"Total {total_ms}ms, {len(all_solutions)} solutions",
        duration_ms=total_ms,
    ))

    # 生成时间相关建议
    time_advice = generate_time_advice(meal_ctx, req.food_name, risk)

    return FindBalanceResponse(
        risk_weight=risk,
        food=food,
        solutions=all_solutions,
        advice=advice,
        meal_context=meal_ctx["label"],
        time_advice=time_advice,
        agent_traces=traces,
    )


@app.post("/api/scale/advice", response_model=RefreshAdviceResponse)
async def refresh_advice(req: RefreshAdviceRequest):
    """根据用户实际选中的对冲方案，重新生成 Coordinator 建议。"""
    meal_ctx = infer_meal_context(req.query_time)

    # 从全部方案中筛选用户选中的
    selected = []
    for idx in req.selected_indices:
        if 0 <= idx < len(req.all_solutions):
            selected.append(req.all_solutions[idx])

    advice = generate_counterbalance_advice(
        req.food_name, req.risk_weight, selected, meal_ctx=meal_ctx,
    )
    time_advice = generate_time_advice(meal_ctx, req.food_name, req.risk_weight)

    return RefreshAdviceResponse(
        advice=advice,
        meal_context=meal_ctx["label"],
        time_advice=time_advice,
    )


@app.post("/api/scale/add_exercise", response_model=CounterSolution)
async def add_custom_exercise(req: AddExerciseRequest):
    """右盘：用户自定义运动，查 MET 表计算 balance_weight（支持模糊匹配）。"""
    raw_name = req.exercise_name.strip()
    std_name, met, match_source = lookup_exercise_met(raw_name)

    raw_effect = met * req.duration_min / 60.0 * 15.0
    balance = round(min(raw_effect, 40.0), 1)

    group = "运动"

    display_name = std_name if std_name != raw_name else raw_name

    return CounterSolution(
        type="exercise",
        name=f"{display_name} {req.duration_min}分钟",
        description=f"MET={met} | {match_source} | 预估消耗 {round(met * 3.5 * 70 / 200 * req.duration_min)}kcal",
        balance_weight=balance,
        group=group,
        details={
            "met": met,
            "duration_min": req.duration_min,
            "kcal_approx": round(met * 3.5 * 70 / 200 * req.duration_min),
            "met_source": match_source,
            "matched_as": std_name,
        },
    )


@app.post("/api/scale/add_food_counter", response_model=CounterSolution)
async def add_custom_food_counter(req: AddFoodCounterRequest):
    """右盘：用户自定义食物对冲，查食物库计算 balance_weight。"""
    raw = lookup_food(req.food_name)
    if not raw:
        raise HTTPException(status_code=404, detail=f"Food '{req.food_name}' not found")

    gi = raw.get("gi_value", 50)
    fiber = raw.get("fiber_g", 0)
    protein = raw.get("protein_g", 0)

    fiber_effect = min(fiber * 3.0, 15.0)
    protein_effect = min(protein * 1.5, 10.0)
    gi_bonus = max(0, (55 - gi) / 55.0) * 10.0
    balance = round(min(fiber_effect + protein_effect + gi_bonus, 35.0), 1)

    name = raw.get("food_name", req.food_name)
    serving = raw.get("serving_size_g", 0)
    counter = raw.get("counter_strategy", "")
    desc = f"GI {gi}({raw.get('gi_level', '')}) | "
    desc += f"纤维 {fiber}g 蛋白质 {protein}g"
    if counter:
        desc += f" | {counter}"

    cat = raw.get("food_category", "")
    CATEGORY_TO_GROUP = {
        "蔬菜": "蔬菜搭配", "菌菇": "蔬菜搭配", "水果": "蔬菜搭配",
        "豆类": "蛋白搭配", "肉类": "蛋白搭配", "奶类": "蛋白搭配", "坚果": "蛋白搭配",
        "主食": "主食替换", "谷物": "主食替换",
        "饮料": "汤饮搭配", "汤": "汤饮搭配",
    }
    group = CATEGORY_TO_GROUP.get(cat, "其他搭配")

    capped_serving = int(min(serving, MAX_SERVING.get(cat, 150))) if serving else 0
    label = _get_serving_label(cat, capped_serving, name)
    counter_name = f"搭配 {name}"
    if capped_serving:
        counter_name += f" · {label}({capped_serving}g)"

    return CounterSolution(
        type="food",
        name=counter_name,
        description=desc,
        balance_weight=balance,
        group=group,
        details={
            "food_name": name,
            "gi": gi,
            "fiber_g": fiber,
            "protein_g": protein,
        },
    )


# ─── DeepSeek Chat Endpoint ─────────────────────

from openai import OpenAI

_deepseek_client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
    base_url="https://api.deepseek.com/v1",
)

# 从 OpenClaw workspace 读取 SOUL.md / USER.md / AGENTS.md 注入 system prompt
_WORKSPACE = os.path.expanduser("~/.openclaw/workspace")


def _read_workspace_file(name: str) -> str:
    path = os.path.join(_WORKSPACE, name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _build_system_prompt() -> str:
    soul = _read_workspace_file("SOUL.md")
    user = _read_workspace_file("USER.md")
    agents = _read_workspace_file("AGENTS.md")

    parts = [
        "# 你是 SugarClaw — 代谢进化教练",
        "",
        "你正在 SugarClaw 网页端 Chat 中与用户对话。",
        "请严格遵循以下配置文件定义的身份、风格和规则。",
        "",
        "## 回复要求",
        "- 使用中文回复",
        "- 追求高效干预：避免无效礼貌用语，直接切入核心建议",
        "- 认知重构而非限制：不使用「严禁」「绝对不能」等限制性指令",
        "- 单次回复核心行动指令不超过 3 条",
        "- 涉及药物剂量调整时，必须建议咨询主治医师",
        "- 适时声明 AI 建议仅供参考，不构成临床诊断",
        "",
    ]

    if soul:
        parts.append("---")
        parts.append(soul)
        parts.append("")

    if user:
        parts.append("---")
        parts.append("# 当前用户画像（你正在服务的用户）")
        parts.append(user)
        parts.append("")

    # 注入数据库中的真实用户档案
    db_user = database.get_user(1)
    if db_user and db_user.get("name"):
        parts.append("---")
        parts.append("# 用户档案（来自数据库）")
        profile_lines = []
        if db_user.get("name"):
            profile_lines.append(f"- 姓名: {db_user['name']}")
        if db_user.get("age"):
            profile_lines.append(f"- 年龄: {db_user['age']}")
        if db_user.get("weight"):
            profile_lines.append(f"- 体重: {db_user['weight']} kg")
        if db_user.get("height"):
            profile_lines.append(f"- 身高: {db_user['height']} cm")
        if db_user.get("diabetes_type"):
            profile_lines.append(f"- 糖尿病类型: {db_user['diabetes_type']}")
        if db_user.get("isf"):
            profile_lines.append(f"- ISF: {db_user['isf']}")
        if db_user.get("icr"):
            profile_lines.append(f"- ICR: {db_user['icr']}")
        if db_user.get("medications"):
            meds = db_user["medications"]
            if meds:
                profile_lines.append(f"- 用药: {', '.join(meds) if isinstance(meds, list) else meds}")
        if db_user.get("regional_preference") and db_user["regional_preference"] != "全国":
            profile_lines.append(f"- 地域偏好: {db_user['regional_preference']}")
        parts.extend(profile_lines)
        parts.append("")

    if agents:
        parts.append("---")
        parts.append("# Agent 协作角色定义（你的多重身份）")
        parts.append(agents)
        parts.append("")

    # 注入权威糖尿病指南知识库
    parts.append("---")
    parts.append(guidelines.get_all_guidelines_summary())
    parts.append("")

    return "\n".join(parts)


class ChatRequest(BaseModel):
    messages: List[dict]


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """DeepSeek Chat 对话，SSE 流式返回。"""
    # 每次请求重新读取配置文件，确保 SOUL.md / USER.md / AGENTS.md 的修改即时生效
    system_prompt = _build_system_prompt()

    # 根据用户最新消息检索最相关的指南条目，注入上下文
    last_user_msg = ""
    for msg in reversed(req.messages):
        if msg.get("role") == "user" and msg.get("content"):
            last_user_msg = msg["content"]
            break
    if last_user_msg:
        relevant = guidelines.search_guidelines(last_user_msg, max_results=3)
        if relevant:
            system_prompt += "\n" + guidelines.format_guidelines_for_prompt(relevant)

    full_messages = [{"role": "system", "content": system_prompt}]
    for msg in req.messages:
        full_messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", ""),
        })

    async def generate():
        try:
            stream = _deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=full_messages,
                stream=True,
            )
            for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if not choice:
                    continue
                delta = choice.delta

                # 最终回答内容
                if delta.content:
                    event = {"type": "content", "content": delta.content}
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                if choice.finish_reason:
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    break
        except Exception as e:
            import traceback
            detail = traceback.format_exc()
            print(f"[chat error] {detail}", flush=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'detail': detail})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ─── 用户档案 Endpoints ────────────────────────────

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    diabetes_type: Optional[str] = None
    medications: Optional[List[str]] = None
    isf: Optional[float] = None
    icr: Optional[float] = None
    regional_preference: Optional[str] = None


@app.get("/api/user/profile")
async def get_profile():
    """获取当前用户档案 (MVP 单用户 id=1)。"""
    user = database.get_user(1)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@app.put("/api/user/profile")
async def update_profile(body: UserProfileUpdate):
    """更新用户档案字段。"""
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(400, "No fields to update")
    updated = database.update_user(1, **fields)
    return updated


class CalibrateISFRequest(BaseModel):
    before: float = Field(..., description="餐前血糖 mmol/L")
    after: float = Field(..., description="餐后血糖 mmol/L")
    dose: float = Field(..., description="胰岛素剂量 U")


@app.post("/api/user/calibrate_isf")
async def calibrate_isf(req: CalibrateISFRequest):
    """根据观测数据 EMA 更新 ISF。"""
    if req.dose <= 0:
        raise HTTPException(400, "Dose must be positive")
    observed_isf = abs(req.before - req.after) / req.dose
    user = database.get_user(1)
    stored_isf = user.get("isf", 0) if user else 0
    if stored_isf > 0:
        new_isf = round(0.3 * observed_isf + 0.7 * stored_isf, 3)
    else:
        new_isf = round(observed_isf, 3)
    updated = database.update_user(1, isf=new_isf)
    return {
        "observed_isf": round(observed_isf, 3),
        "previous_isf": stored_isf,
        "new_isf": new_isf,
        "user": updated,
    }


# ─── 血糖日志 Endpoints ────────────────────────────

class GlucoseLogEntry(BaseModel):
    timestamp: str = Field(..., description="ISO 格式时间戳")
    glucose_mmol: float = Field(..., ge=0.5, le=40, description="血糖值 mmol/L")
    note: str = Field("", description="备注（如：早餐后、运动前）")


@app.post("/api/glucose/log")
async def add_glucose_log(entry: GlucoseLogEntry):
    """添加一条手动血糖记录。"""
    saved = database.save_glucose_entry(
        timestamp=entry.timestamp,
        glucose_mmol=entry.glucose_mmol,
        note=entry.note,
    )
    return saved


@app.get("/api/glucose/log")
async def get_glucose_log(limit: int = 100):
    """获取血糖日志。"""
    return database.get_glucose_log(limit=limit)


@app.delete("/api/glucose/log/{entry_id}")
async def delete_glucose_log(entry_id: int):
    """删除一条血糖记录。"""
    ok = database.delete_glucose_entry(entry_id)
    if not ok:
        raise HTTPException(404, "Entry not found")
    return {"deleted": True}


# ─── CGM 模拟 Endpoints ────────────────────────────

import uuid


class CGMSimulateRequest(BaseModel):
    seed: Optional[int] = None


@app.post("/api/cgm/simulate")
def cgm_simulate(req: CGMSimulateRequest = CGMSimulateRequest()):
    """调用 generate_demo_data() 生成 24h 模拟数据，存入 SQLite。"""
    seed = req.seed if req.seed is not None else int(datetime.now().timestamp()) % 100000
    readings = ble_cgm_parser.generate_demo_data(seed=seed)
    session_id = f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    database.save_cgm_readings(session_id, readings, source="simulation")
    return {
        "session_id": session_id,
        "count": len(readings),
        "readings": readings,
    }


@app.get("/api/cgm/stream/{session_id}")
async def cgm_stream(session_id: str):
    """SSE 逐条推送 CGM 读数（复用 replay_stream 模式）。"""
    readings = database.get_cgm_session(session_id)
    if not readings:
        raise HTTPException(404, f"Session {session_id} not found")

    async def generate():
        for i, r in enumerate(readings):
            event = {
                "type": "reading",
                "index": i,
                "total": len(readings),
                "timestamp": r.get("timestamp", ""),
                "glucose_mmol": r.get("glucose_mmol", 0),
                "glucose_mgdl": r.get("glucose_mgdl", 0),
                "event": r.get("event", ""),
            }
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/cgm/history")
async def cgm_history(limit: int = 100):
    """查询最近 N 条 CGM 读数。"""
    return database.get_cgm_history(limit)


@app.get("/api/cgm/sessions")
async def cgm_sessions():
    """列出历史模拟会话。"""
    return database.list_cgm_sessions()


# ─── PubMed 文献检索 Endpoints ────────────────────────────

PUBMED_PRESETS = {
    "food-impact": "({query}) AND (glycemic index OR glycemic load OR blood glucose)",
    "therapy": "({query}) AND (treatment OR therapy OR management) AND diabetes",
    "cgm": "({query}) AND (continuous glucose monitoring OR CGM)",
    "mental": "({query}) AND (mental health OR depression OR anxiety) AND diabetes",
}


class PubMedSearchRequest(BaseModel):
    query: str
    mode: str = Field("custom", description="搜索模式: custom / food-impact / therapy / cgm / mental")
    max_results: int = Field(5, ge=1, le=20)
    include_abstracts: bool = False


@app.post("/api/pubmed/search")
def pubmed_search(req: PubMedSearchRequest):
    """搜索 PubMed 文献（sync def，FastAPI 自动放线程池）。"""
    search_query = req.query
    if req.mode in PUBMED_PRESETS:
        search_query = PUBMED_PRESETS[req.mode].format(query=req.query)

    api_key = os.environ.get("NCBI_API_KEY")
    pmids, count = pubmed_researcher.esearch(search_query, max_results=req.max_results, api_key=api_key)

    summaries = pubmed_researcher.esummary(pmids, api_key=api_key)

    abstracts_text = ""
    if req.include_abstracts and pmids:
        abstracts_text = pubmed_researcher.efetch_abstracts(pmids, api_key=api_key)

    # 保存搜索历史
    database.save_search(req.query, req.mode, summaries, total_count=count)

    return {
        "query": req.query,
        "mode": req.mode,
        "total_count": count,
        "articles": summaries,
        "abstracts": abstracts_text,
    }


@app.get("/api/pubmed/history")
async def pubmed_history(limit: int = 20):
    """获取最近的 PubMed 搜索历史。"""
    return database.get_recent_searches(limit)


# Serve Flutter web build as static files at root
WEB_BUILD = os.path.join(os.path.dirname(__file__), "..", "frontend", "build", "web")
if os.path.isdir(WEB_BUILD):
    app.mount("/", StaticFiles(directory=WEB_BUILD, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    # 监听的额外目录：配置文件变更时也自动重启
    _watch_dirs = []
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _workspace_root = os.path.expanduser("~/.openclaw/workspace")
    for d in [_project_root, _workspace_root]:
        if os.path.isdir(d):
            _watch_dirs.append(d)

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        reload_dirs=_watch_dirs,
        reload_includes=["*.py", "*.json", "*.md", "*.env"],
    )
