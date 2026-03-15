"""
权威糖尿病临床指南知识库
整合中国、美国、国际权威组织的最新循证指南核心要点。

来源：
1. CDS 《中国2型糖尿病防治指南（2024版）》 — 中华医学会糖尿病学分会
2. ADA Standards of Care in Diabetes — 2025 — 美国糖尿病协会
3. IDF Diabetes Atlas & Clinical Practice Recommendations — 国际糖尿病联盟
4. EASD/ADA Consensus Report on Management of Hyperglycemia — 欧洲/美国联合共识
5. WHO Guidelines on Diabetes Screening and Management — 世界卫生组织

每条指南条目包含：来源、类别、推荐等级、核心内容。
Chat 系统在回答用户问题时可引用这些条目以提供循证支持。
"""

from typing import List, Optional

# ─── 指南条目结构 ───────────────────────────────

class GuidelineEntry:
    def __init__(self, source: str, category: str, grade: str,
                 title: str, content: str, tags: list):
        self.source = source      # 来源缩写: CDS, ADA, IDF, EASD, WHO
        self.category = category  # 类别: 血糖目标, 饮食, 运动, 用药, 监测, 并发症, 特殊人群
        self.grade = grade        # 推荐等级: A/B/C/E/专家共识
        self.title = title        # 条目标题
        self.content = content    # 核心内容
        self.tags = tags          # 检索标签


# ─── 完整指南知识库 ───────────────────────────────

GUIDELINES: List[GuidelineEntry] = [

    # ══════════════════════════════════════════════
    # CDS 《中国2型糖尿病防治指南（2024版）》
    # ══════════════════════════════════════════════

    GuidelineEntry(
        source="CDS 2024",
        category="血糖目标",
        grade="A",
        title="HbA1c 控制目标",
        content=(
            "大多数非妊娠成人2型糖尿病患者 HbA1c 控制目标为 <7.0%。"
            "对于病程较短、预期寿命长、无严重并发症的患者，可考虑更严格的 <6.5% 目标。"
            "老年或合并严重并发症者可适当放宽至 <8.0%。"
        ),
        tags=["HbA1c", "血糖目标", "糖化血红蛋白", "控制标准"],
    ),
    GuidelineEntry(
        source="CDS 2024",
        category="血糖目标",
        grade="A",
        title="自我血糖监测（SMBG）目标范围",
        content=(
            "空腹血糖目标：4.4-7.0 mmol/L。"
            "非空腹（餐后2h）血糖目标：<10.0 mmol/L。"
            "使用 CGM 时，葡萄糖目标范围内时间（TIR，3.9-10.0 mmol/L）应 >70%，"
            "低血糖时间（<3.9 mmol/L）应 <4%，严重低血糖（<3.0 mmol/L）应 <1%。"
        ),
        tags=["血糖监测", "空腹血糖", "餐后血糖", "TIR", "CGM", "低血糖"],
    ),
    GuidelineEntry(
        source="CDS 2024",
        category="饮食",
        grade="B",
        title="医学营养治疗（MNT）总则",
        content=(
            "糖尿病患者应接受个体化医学营养治疗。"
            "碳水化合物供能比 45-60%，优选低GI食物（GI<55）。"
            "膳食纤维摄入建议 25-30g/天。"
            "蛋白质供能比 15-20%（肾功能正常者）。"
            "脂肪供能比 20-30%，限制饱和脂肪酸 <7%，避免反式脂肪酸。"
        ),
        tags=["饮食", "营养", "碳水", "GI", "膳食纤维", "蛋白质", "脂肪"],
    ),
    GuidelineEntry(
        source="CDS 2024",
        category="饮食",
        grade="B",
        title="进餐顺序与血糖管理",
        content=(
            "研究表明先吃蔬菜和蛋白质、后吃碳水化合物的进餐顺序，"
            "可使餐后血糖峰值降低约 30-40%，餐后血糖增量显著减少。"
            "推荐顺序：汤/蔬菜 → 蛋白质/脂肪 → 碳水化合物/主食。"
            "细嚼慢咽（每口咀嚼 20-30 次）也有助于延缓血糖上升。"
        ),
        tags=["进餐顺序", "蔬菜", "蛋白质", "碳水", "餐后血糖", "吃饭顺序"],
    ),
    GuidelineEntry(
        source="CDS 2024",
        category="运动",
        grade="A",
        title="运动处方",
        content=(
            "建议每周至少 150 分钟中等强度有氧运动（如快走、游泳、骑车），"
            "分布于每周至少 3 天，不宜连续 2 天不运动。"
            "如无禁忌，每周应进行 2-3 次抗阻训练（力量训练）。"
            "运动可降低 HbA1c 约 0.5-0.7%。"
            "餐后 30 分钟开始运动降糖效果最佳。"
        ),
        tags=["运动", "有氧运动", "抗阻训练", "力量训练", "餐后运动"],
    ),
    GuidelineEntry(
        source="CDS 2024",
        category="用药",
        grade="A",
        title="2型糖尿病一线用药",
        content=(
            "生活方式干预是2型糖尿病治疗的基础，贯穿全程。"
            "二甲双胍（Metformin）为首选一线口服降糖药（无禁忌证时）。"
            "对于合并动脉粥样硬化性心血管疾病（ASCVD）的患者，"
            "优先选择有心血管获益证据的 GLP-1RA 或 SGLT2i。"
            "对于合并心衰或慢性肾脏病（CKD）的患者，优先选择 SGLT2i。"
        ),
        tags=["二甲双胍", "用药", "GLP-1", "SGLT2", "一线治疗", "metformin"],
    ),
    GuidelineEntry(
        source="CDS 2024",
        category="用药",
        grade="A",
        title="胰岛素治疗时机",
        content=(
            "新诊断2型糖尿病患者 HbA1c≥9.0% 或空腹血糖≥11.1 mmol/L 时，"
            "可考虑短期胰岛素强化治疗。"
            "口服药联合治疗 3 个月 HbA1c 仍不达标者，应启动胰岛素治疗。"
            "1型糖尿病患者必须使用胰岛素治疗。"
        ),
        tags=["胰岛素", "强化治疗", "1型糖尿病", "HbA1c"],
    ),
    GuidelineEntry(
        source="CDS 2024",
        category="监测",
        grade="B",
        title="持续葡萄糖监测（CGM）推荐",
        content=(
            "使用胰岛素治疗的患者推荐使用 CGM 以改善血糖控制。"
            "CGM 关键指标：TIR（目标范围内时间）>70%，TBR（低于范围时间）<4%，"
            "TAR（高于范围时间）<25%，血糖变异系数 CV <36%。"
            "CGM 数据应结合 HbA1c 综合评估血糖管理质量。"
        ),
        tags=["CGM", "持续监测", "TIR", "TBR", "TAR", "血糖变异", "CV"],
    ),
    GuidelineEntry(
        source="CDS 2024",
        category="并发症",
        grade="A",
        title="低血糖防治",
        content=(
            "血糖 <3.9 mmol/L 为低血糖预警值，<3.0 mmol/L 为临床显著低血糖。"
            "反复低血糖可导致低血糖无感知，增加严重低血糖风险。"
            "发生低血糖时立即口服 15-20g 速效碳水（葡萄糖片、果汁），"
            "15 分钟后复测，未恢复则重复。"
            "使用胰岛素或磺脲类药物的患者低血糖风险较高，应加强监测。"
        ),
        tags=["低血糖", "hypoglycemia", "急救", "葡萄糖", "磺脲类"],
    ),
    GuidelineEntry(
        source="CDS 2024",
        category="特殊人群",
        grade="B",
        title="妊娠期糖尿病管理",
        content=(
            "妊娠期空腹血糖目标：<5.3 mmol/L。"
            "餐后1h：<7.8 mmol/L，餐后2h：<6.7 mmol/L。"
            "HbA1c 目标 <6.0%（如可安全达标）。"
            "生活方式管理为首选，血糖不达标者应使用胰岛素。"
            "妊娠期禁用口服降糖药（二甲双胍在部分指南中允许使用）。"
        ),
        tags=["妊娠", "孕期", "妊娠糖尿病", "GDM"],
    ),

    # ══════════════════════════════════════════════
    # ADA Standards of Care in Diabetes — 2025
    # ══════════════════════════════════════════════

    GuidelineEntry(
        source="ADA 2025",
        category="血糖目标",
        grade="A",
        title="Glycemic Targets",
        content=(
            "大多数非妊娠成人 HbA1c 目标 <7.0%（53 mmol/mol）。"
            "使用 CGM 时，TIR >70%（对应 HbA1c ~7%）。"
            "个体化目标应考虑：低血糖风险、病程、预期寿命、合并症、患者偏好。"
            "对于新诊断或仅用生活方式/二甲双胍的患者，可追求 <6.5%。"
        ),
        tags=["HbA1c", "TIR", "glycemic targets", "血糖目标"],
    ),
    GuidelineEntry(
        source="ADA 2025",
        category="饮食",
        grade="A",
        title="Nutrition Therapy — 个体化营养方案",
        content=(
            "所有糖尿病患者应接受个体化 MNT（医学营养治疗），最好由注册营养师提供。"
            "没有单一理想的碳水化合物比例，应根据个人偏好和代谢目标调整。"
            "推荐选择全谷物、蔬菜、豆类等高纤维食物替代精制碳水。"
            "地中海饮食、DASH 饮食和植物性饮食均有改善血糖的证据。"
            "减少含糖饮料摄入，酒精适量（女性≤1份/天，男性≤2份/天）。"
        ),
        tags=["MNT", "营养", "地中海饮食", "DASH", "全谷物", "饮食模式"],
    ),
    GuidelineEntry(
        source="ADA 2025",
        category="饮食",
        grade="B",
        title="碳水化合物计数与GI应用",
        content=(
            "碳水化合物计数（Carb Counting）对使用胰岛素的患者有助于精确匹配餐时胰岛素剂量。"
            "低GI饮食（GI<55）可适度改善血糖控制，尤其是餐后血糖。"
            "膳食纤维目标 ≥14g/1000kcal（约 25-35g/天）。"
            "蛋白质不会显著升高血糖，但可影响胰岛素需求。"
        ),
        tags=["碳水计数", "GI", "膳食纤维", "蛋白质", "胰岛素匹配"],
    ),
    GuidelineEntry(
        source="ADA 2025",
        category="运动",
        grade="A",
        title="Physical Activity Recommendations",
        content=(
            "每周至少 150 分钟中高强度有氧运动，或每周至少 75 分钟高强度有氧运动。"
            "每周 2-3 次抗阻训练，涵盖所有主要肌群。"
            "减少久坐时间，每 30 分钟起身活动一次。"
            "运动前评估心血管风险、自主神经病变和足部状况。"
            "运动可独立于体重减轻改善胰岛素敏感性。"
        ),
        tags=["运动", "有氧", "抗阻", "久坐", "physical activity"],
    ),
    GuidelineEntry(
        source="ADA 2025",
        category="用药",
        grade="A",
        title="Pharmacologic Management — 降糖药物选择",
        content=(
            "二甲双胍仍为多数2型糖尿病一线用药。"
            "对于已确诊 ASCVD 或高心血管风险者，无论 HbA1c 水平，"
            "应在方案中加入有心血管获益的 GLP-1RA（利拉鲁肽/司美格鲁肽等）。"
            "合并心衰（HFrEF/HFpEF）或 CKD 者，优先使用 SGLT2i（达格列净/恩格列净等）。"
            "对于需要强效降糖的患者，双重 GIP/GLP-1 RA（替尔泊肽）可降低 HbA1c 达 2.0%+。"
        ),
        tags=["二甲双胍", "GLP-1", "SGLT2", "替尔泊肽", "心血管", "心衰", "CKD"],
    ),
    GuidelineEntry(
        source="ADA 2025",
        category="用药",
        grade="A",
        title="体重管理与降糖药物",
        content=(
            "对于合并肥胖的2型糖尿病患者，优先选择有减重效果的降糖药物。"
            "GLP-1RA 可减重 5-15%，双重 GIP/GLP-1 RA（替尔泊肽）可减重 15-20%+。"
            "SGLT2i 可减轻体重约 2-3kg。"
            "避免使用导致体重增加的药物（磺脲类、噻唑烷二酮类、胰岛素）作为首选。"
            "BMI ≥27 合并代谢异常者可考虑减重药物辅助。"
        ),
        tags=["体重", "减重", "肥胖", "GLP-1", "BMI"],
    ),
    GuidelineEntry(
        source="ADA 2025",
        category="监测",
        grade="B",
        title="CGM Technology — 持续监测技术",
        content=(
            "实时 CGM（rtCGM）和间歇扫描 CGM（isCGM）均可用于1型和2型糖尿病。"
            "CGM 可减少低血糖发生率和 HbA1c，改善生活质量。"
            "AGP（动态葡萄糖图谱）报告是标准化 CGM 数据分析工具。"
            "推荐至少每 2 周回顾一次 CGM 数据以调整治疗方案。"
            "CGM 传感器应定期校准（如设备要求）。"
        ),
        tags=["CGM", "rtCGM", "isCGM", "AGP", "传感器", "持续监测"],
    ),
    GuidelineEntry(
        source="ADA 2025",
        category="并发症",
        grade="A",
        title="心血管风险综合管理",
        content=(
            "ASCVD 是2型糖尿病患者的首要死亡原因。"
            "血压目标 <130/80 mmHg（合并高血压者）。"
            "LDL-C 目标：<2.6 mmol/L（无 ASCVD），<1.8 mmol/L（有 ASCVD）。"
            "推荐使用他汀类药物进行一级预防（40-75岁糖尿病患者）。"
            "戒烟是最有效的心血管风险干预之一。"
        ),
        tags=["心血管", "血压", "血脂", "LDL", "他汀", "ASCVD"],
    ),
    GuidelineEntry(
        source="ADA 2025",
        category="特殊人群",
        grade="B",
        title="老年糖尿病管理",
        content=(
            "老年患者（≥65岁）需简化治疗方案，减少低血糖风险。"
            "健康老年人 HbA1c 目标 <7.5%，复杂老年人 <8.0%，"
            "合并多种慢病或认知障碍者可放宽至 <8.5%。"
            "优先选择低低血糖风险药物（二甲双胍、DPP-4i、GLP-1RA、SGLT2i）。"
            "关注营养不良、肌少症和跌倒风险。"
        ),
        tags=["老年", "elderly", "简化方案", "低血糖风险"],
    ),

    # ══════════════════════════════════════════════
    # IDF 国际糖尿病联盟指南
    # ══════════════════════════════════════════════

    GuidelineEntry(
        source="IDF 2024",
        category="血糖目标",
        grade="专家共识",
        title="餐后血糖管理",
        content=(
            "餐后高血糖是心血管风险的独立危险因素。"
            "餐后2小时血糖目标 <7.8 mmol/L（<140 mg/dL）。"
            "管理餐后血糖的策略：选择低GI食物、控制碳水总量、"
            "先菜后饭的进餐顺序、餐后适量运动、必要时使用餐时胰岛素或α-糖苷酶抑制剂。"
        ),
        tags=["餐后血糖", "postprandial", "心血管风险", "α-糖苷酶"],
    ),
    GuidelineEntry(
        source="IDF 2024",
        category="饮食",
        grade="专家共识",
        title="全球营养建议",
        content=(
            "鼓励摄入全谷物、蔬菜、水果、豆类、坚果等天然食物。"
            "减少加工食品、含糖饮料和超加工食品的摄入。"
            "尊重文化和地域饮食传统，在传统饮食基础上做出健康调整。"
            "定时定量进餐有助于血糖稳定。"
        ),
        tags=["饮食", "全球", "加工食品", "定时进餐"],
    ),
    GuidelineEntry(
        source="IDF 2024",
        category="监测",
        grade="专家共识",
        title="糖尿病自我管理教育（DSMES）",
        content=(
            "每位糖尿病患者都应在诊断时接受自我管理教育。"
            "DSMES 内容涵盖：血糖监测、饮食管理、运动指导、用药依从、"
            "低血糖识别与处理、足部护理、心理健康。"
            "建议在关键时间节点（诊断、年度评估、并发症出现、治疗调整）提供 DSMES。"
        ),
        tags=["自我管理", "教育", "DSMES", "依从性"],
    ),

    # ══════════════════════════════════════════════
    # EASD/ADA 联合共识（2022 更新）
    # ══════════════════════════════════════════════

    GuidelineEntry(
        source="EASD/ADA 2022",
        category="用药",
        grade="A",
        title="以器官保护为中心的降糖策略",
        content=(
            "降糖治疗不应仅关注 HbA1c，更应关注心肾保护。"
            "SGLT2i 在心衰和 CKD 中具有独立于降糖的器官保护作用（eGFR≥20 即可使用）。"
            "GLP-1RA 可降低 MACE（主要心血管不良事件）风险 12-14%。"
            "对于高心血管风险患者，即使 HbA1c 已达标，仍应加用 GLP-1RA 或 SGLT2i。"
        ),
        tags=["器官保护", "心衰", "CKD", "SGLT2", "GLP-1", "MACE"],
    ),
    GuidelineEntry(
        source="EASD/ADA 2022",
        category="用药",
        grade="专家共识",
        title="以患者为中心的决策",
        content=(
            "药物选择应综合考虑：疗效、低血糖风险、体重影响、副作用、费用、患者偏好。"
            "治疗方案应每 3-6 个月评估一次，及时调整。"
            "鼓励共同决策（Shared Decision Making），尊重患者意愿。"
            "避免治疗惰性：HbA1c 不达标时应积极调整方案。"
        ),
        tags=["共同决策", "治疗惰性", "个体化", "患者偏好"],
    ),

    # ══════════════════════════════════════════════
    # WHO 世界卫生组织指南
    # ══════════════════════════════════════════════

    GuidelineEntry(
        source="WHO 2024",
        category="血糖目标",
        grade="推荐",
        title="糖尿病诊断标准",
        content=(
            "空腹血糖 ≥7.0 mmol/L（126 mg/dL），或 "
            "OGTT 2h 血糖 ≥11.1 mmol/L（200 mg/dL），或 "
            "HbA1c ≥6.5%（48 mmol/mol），或 "
            "有典型症状 + 随机血糖 ≥11.1 mmol/L。"
            "需在无急性代谢紊乱情况下，至少两次检测确认。"
        ),
        tags=["诊断", "空腹血糖", "OGTT", "HbA1c", "诊断标准"],
    ),
    GuidelineEntry(
        source="WHO 2024",
        category="饮食",
        grade="推荐",
        title="糖摄入限制",
        content=(
            "游离糖（Free Sugars）摄入应 <总能量的 10%，进一步减至 <5% 有额外健康获益。"
            "游离糖包括：添加糖、蜂蜜、糖浆、果汁中的天然糖。"
            "全水果中的糖不计入游离糖，鼓励每天摄入 400g+ 蔬果。"
            "钠摄入 <2g/天（约5g盐），钾摄入 ≥3.5g/天。"
        ),
        tags=["糖", "游离糖", "添加糖", "钠", "蔬果"],
    ),
    GuidelineEntry(
        source="WHO 2024",
        category="运动",
        grade="推荐",
        title="身体活动指南",
        content=(
            "18-64岁成人：每周至少 150-300 分钟中等强度或 75-150 分钟高强度有氧运动。"
            "≥65岁老年人：同上，另加平衡和功能训练以预防跌倒（每周≥3天）。"
            "任何量的身体活动都优于不活动。"
            "减少久坐和屏幕时间。"
        ),
        tags=["运动", "身体活动", "久坐", "老年", "平衡训练"],
    ),

    # ══════════════════════════════════════════════
    # 实用临床场景指南
    # ══════════════════════════════════════════════

    GuidelineEntry(
        source="CDS 2024",
        category="饮食",
        grade="B",
        title="血糖生成指数（GI）分类与应用",
        content=(
            "低 GI（≤55）：全麦面包、燕麦、大多数蔬菜和豆类、苹果、梨。"
            "中 GI（56-69）：糙米、全麦意面、甜玉米、香蕉。"
            "高 GI（≥70）：白米饭、白面包、土豆、西瓜。"
            "混合膳食的 GI 受蛋白质、脂肪、纤维影响而降低。"
            "GI 应与 GL（血糖负荷）结合使用：GL = GI × 碳水含量(g) / 100。"
            "低 GL <10，中 GL 11-19，高 GL ≥20。"
        ),
        tags=["GI", "GL", "血糖生成指数", "血糖负荷", "低GI"],
    ),
    GuidelineEntry(
        source="ADA 2025",
        category="饮食",
        grade="B",
        title="酒精与血糖",
        content=(
            "酒精可导致延迟性低血糖（饮酒后 12-24 小时），尤其是使用胰岛素或磺脲类者。"
            "饮酒时应进食，切勿空腹饮酒。"
            "饮酒量限制：女性 ≤1 标准杯/天，男性 ≤2 标准杯/天。"
            "1标准杯 = 350ml 啤酒 = 150ml 葡萄酒 = 45ml 烈酒。"
            "饮酒后睡前应检测血糖，必要时加餐。"
        ),
        tags=["酒精", "饮酒", "低血糖", "延迟性低血糖"],
    ),
    GuidelineEntry(
        source="CDS 2024",
        category="运动",
        grade="B",
        title="运动与低血糖预防",
        content=(
            "使用胰岛素或促泌剂的患者，运动前血糖 <5.6 mmol/L 应先补充碳水。"
            "长时间运动（>60分钟）应每 30 分钟补充 15-20g 碳水。"
            "运动前可适当减少胰岛素剂量（减 20-50%，具体遵医嘱）。"
            "运动后数小时仍可能发生低血糖，应注意监测。"
            "随身携带速效碳水（葡萄糖片/果汁）。"
        ),
        tags=["运动", "低血糖", "胰岛素", "碳水补充"],
    ),
    GuidelineEntry(
        source="ADA 2025",
        category="并发症",
        grade="A",
        title="糖尿病肾病（DKD）管理",
        content=(
            "每年筛查尿白蛋白/肌酐比（UACR）和 eGFR。"
            "UACR ≥30 mg/g 或 eGFR <60 为 DKD。"
            "首选 ACEI/ARB 控制血压和减少蛋白尿。"
            "eGFR ≥20 时应使用 SGLT2i。"
            "非甾体 MRA（非奈利酮）可进一步减少肾脏进展（UACR≥30 + eGFR≥25）。"
            "蛋白质摄入 0.8g/kg/天（CKD 3-5期）。"
        ),
        tags=["肾病", "DKD", "蛋白尿", "eGFR", "SGLT2", "非奈利酮"],
    ),
    GuidelineEntry(
        source="CDS 2024",
        category="并发症",
        grade="B",
        title="糖尿病足护理",
        content=(
            "每年至少一次全面足部检查（触觉、振动觉、足背动脉搏动）。"
            "高风险患者每 1-3 个月检查一次。"
            "每天检查双足，注意伤口、水疱、胼胝。"
            "穿合适的鞋袜，避免赤足行走。"
            "发现足部破损应在 24 小时内就诊。"
        ),
        tags=["糖尿病足", "足部护理", "神经病变", "检查"],
    ),
    GuidelineEntry(
        source="ADA 2025",
        category="特殊人群",
        grade="B",
        title="1型糖尿病技术管理",
        content=(
            "推荐所有1型患者使用 CGM。"
            "胰岛素泵治疗（CSII）联合 CGM 可改善血糖控制并减少低血糖。"
            "混合闭环系统（Hybrid Closed Loop / AID）可显著提高 TIR，推荐使用。"
            "碳水计数、胰岛素敏感系数（ISF）和碳水比（ICR）是精准剂量调整的基础。"
        ),
        tags=["1型", "胰岛素泵", "CGM", "闭环", "ISF", "ICR"],
    ),
    GuidelineEntry(
        source="IDF 2024",
        category="特殊人群",
        grade="专家共识",
        title="心理健康与糖尿病",
        content=(
            "糖尿病患者抑郁发生率是普通人群的 2-3 倍。"
            "糖尿病倦怠（Diabetes Distress）影响 25-45% 的患者，可降低自我管理依从性。"
            "建议定期筛查心理健康，提供心理支持。"
            "良好的心理状态与更好的血糖控制呈正相关。"
        ),
        tags=["心理", "抑郁", "糖尿病倦怠", "心理健康"],
    ),
]


# ─── 检索函数 ───────────────────────────────

def search_guidelines(query: str, max_results: int = 5) -> List[GuidelineEntry]:
    """根据关键词搜索相关指南条目。简单匹配标签、标题和内容。"""
    query_lower = query.lower()
    scored = []
    for entry in GUIDELINES:
        score = 0
        # 标签完全匹配权重最高
        for tag in entry.tags:
            if tag.lower() in query_lower or query_lower in tag.lower():
                score += 10
        # 标题匹配
        if query_lower in entry.title.lower():
            score += 5
        # 内容匹配（按关键词拆分）
        keywords = query_lower.replace("，", " ").replace(",", " ").split()
        for kw in keywords:
            if kw in entry.title.lower():
                score += 3
            if kw in entry.content.lower():
                score += 1
            for tag in entry.tags:
                if kw in tag.lower():
                    score += 2
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:max_results]]


def format_guidelines_for_prompt(entries: List[GuidelineEntry]) -> str:
    """将指南条目格式化为可嵌入 system prompt 的文本。"""
    if not entries:
        return ""
    lines = ["", "# 相关权威指南参考（请在回答时适当引用）", ""]
    for e in entries:
        lines.append(f"### [{e.source}] {e.title}（推荐等级：{e.grade}）")
        lines.append(f"类别：{e.category}")
        lines.append(e.content)
        lines.append("")
    lines.append("引用格式示例：根据《CDS 2024 指南》推荐（等级A）……")
    lines.append("注意：请根据用户问题的上下文选择性引用，不要机械罗列所有指南。")
    return "\n".join(lines)


def get_all_guidelines_summary() -> str:
    """生成完整指南摘要，用于嵌入 system prompt 的基础知识层。"""
    lines = [
        "",
        "# 权威糖尿病指南知识库",
        "",
        "你的回答应基于以下权威来源的循证建议，在合适时引用来源：",
        "- **CDS 2024**：中华医学会糖尿病学分会《中国2型糖尿病防治指南（2024版）》",
        "- **ADA 2025**：American Diabetes Association Standards of Care 2025",
        "- **IDF 2024**：International Diabetes Federation Clinical Practice Recommendations",
        "- **EASD/ADA 2022**：European Association for the Study of Diabetes 联合共识",
        "- **WHO 2024**：World Health Organization Diabetes Guidelines",
        "",
        "关键知识要点：",
        "",
    ]

    # 按类别组织
    categories = {}
    for e in GUIDELINES:
        categories.setdefault(e.category, []).append(e)

    for cat, entries in categories.items():
        lines.append(f"## {cat}")
        for e in entries:
            lines.append(f"- **[{e.source}·{e.grade}] {e.title}**：{e.content[:120]}…" if len(e.content) > 120
                         else f"- **[{e.source}·{e.grade}] {e.title}**：{e.content}")
        lines.append("")

    lines.append("回答要求：")
    lines.append("1. 涉及血糖目标、用药、运动、饮食建议时，应注明参考来源（如「根据 ADA 2025 指南，推荐…」）")
    lines.append("2. 不同指南有差异时，优先引用 CDS（中国患者）或 ADA（通用标准），并说明差异")
    lines.append("3. 推荐等级 A 的建议可直接推荐，等级 B/C 应使用建议性措辞，专家共识注明「专家共识建议」")
    lines.append("4. 涉及药物调整必须建议咨询主治医师")

    return "\n".join(lines)
