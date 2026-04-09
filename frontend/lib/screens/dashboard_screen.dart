import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/analysis_result.dart';
import '../providers/predictor_state.dart';
import '../providers/cgm_state.dart';
import '../services/api_service.dart';
import '../theme.dart';
import '../widgets/glucose_chart.dart';
import '../widgets/alert_card.dart';
import '../widgets/advice_bubble.dart';
import '../widgets/agent_trace_card.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen>
    with SingleTickerProviderStateMixin {
  final _api = ApiService();
  List<CaseInfo> _cases = [];
  AnalysisResult? _result;
  bool _loading = false;
  String? _error;
  late TabController _tabController;
  int _tabIndex = 0;
  bool _resultExpanded = false;

  // 血糖日志
  List<Map<String, dynamic>> _glucoseLog = [];
  final _logGlucoseCtrl = TextEditingController();
  final _logNoteCtrl = TextEditingController();
  DateTime _logDate = DateTime.now();
  TimeOfDay _logTime = TimeOfDay.now();

  // Phase 5: 首屏减负
  bool _slotsExpanded = false;
  bool _glucoseLogExpanded = false;

  static const _timeSlots = [
    {'label': '空腹', 'icon': Icons.wb_twilight_rounded, 'hint': '3.9-6.1', 'default': '5.2'},
    {'label': '早餐后', 'icon': Icons.free_breakfast_rounded, 'hint': '< 7.8', 'default': '6.8'},
    {'label': '午餐前', 'icon': Icons.wb_sunny_rounded, 'hint': '3.9-6.1', 'default': ''},
    {'label': '午餐后', 'icon': Icons.lunch_dining_rounded, 'hint': '< 7.8', 'default': '7.3'},
    {'label': '晚餐后', 'icon': Icons.dinner_dining_rounded, 'hint': '< 7.8', 'default': '7.9'},
    {'label': '睡前', 'icon': Icons.nightlight_rounded, 'hint': '6.0-7.0', 'default': '6.5'},
  ];

  // 默认只显示 3 个常用时段的索引
  static const _defaultSlotIndices = [0, 1, 4]; // 空腹 + 早餐后 + 晚餐后

  late final List<TextEditingController> _slotControllers;
  final _foodController = TextEditingController();
  String? _selectedEvent;

  @override
  void initState() {
    super.initState();
    _slotControllers = _timeSlots
        .map((s) => TextEditingController(text: s['default'] as String))
        .toList();
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(() {
      if (!_tabController.indexIsChanging) {
        setState(() => _tabIndex = _tabController.index);
      }
    });
    _loadCases();
    _loadGlucoseLog();
    _loadSlotsExpandedPref();
  }

  Future<void> _loadSlotsExpandedPref() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _slotsExpanded = prefs.getBool('dashboard_slots_expanded') ?? false;
    });
  }

  Future<void> _toggleSlotsExpanded() async {
    final next = !_slotsExpanded;
    setState(() => _slotsExpanded = next);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('dashboard_slots_expanded', next);
  }

  @override
  void dispose() {
    _tabController.dispose();
    for (final c in _slotControllers) {
      c.dispose();
    }
    _foodController.dispose();
    _logGlucoseCtrl.dispose();
    _logNoteCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadCases() async {
    try {
      final cases = await _api.getCases();
      setState(() => _cases = cases);
    } catch (e) {
      // silent — cases tab will show loading
    }
  }

  Future<void> _loadGlucoseLog() async {
    try {
      final log = await _api.getGlucoseLog(limit: 50);
      setState(() => _glucoseLog = log);
    } catch (_) {}
  }

  Future<void> _addGlucoseEntry() async {
    final glucose = double.tryParse(_logGlucoseCtrl.text.trim());
    if (glucose == null || glucose < 0.5 || glucose > 40) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请输入有效血糖值 (0.5-40 mmol/L)')),
      );
      return;
    }
    final dt = DateTime(_logDate.year, _logDate.month, _logDate.day, _logTime.hour, _logTime.minute);
    final ts = dt.toIso8601String();
    try {
      await _api.addGlucoseLog(timestamp: ts, glucoseMmol: glucose, note: _logNoteCtrl.text.trim());
      _logGlucoseCtrl.clear();
      _logNoteCtrl.clear();
      setState(() {
        _logDate = DateTime.now();
        _logTime = TimeOfDay.now();
      });
      await _loadGlucoseLog();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('保存失败: $e')));
      }
    }
  }

  Future<void> _deleteGlucoseEntry(int id) async {
    try {
      await _api.deleteGlucoseLog(id);
      await _loadGlucoseLog();
    } catch (_) {}
  }

  Future<void> _runAnalysis() async {
    final readings = _slotControllers
        .map((c) => double.tryParse(c.text.trim()))
        .where((v) => v != null)
        .cast<double>()
        .toList();

    if (readings.length < 3) {
      setState(() => _error = '请至少填写 3 个时间段的血糖值');
      return;
    }

    setState(() { _loading = true; _error = null; });

    try {
      final result = await _api.analyze(
        readings: readings,
        event: _selectedEvent,
        food: _foodController.text.isNotEmpty ? _foodController.text : null,
      );
      setState(() { _result = result; _loading = false; _resultExpanded = false; });

      if (mounted) {
        final labeledReadings = <String, double>{};
        for (var i = 0; i < _timeSlots.length; i++) {
          final v = double.tryParse(_slotControllers[i].text.trim());
          if (v != null) {
            labeledReadings[_timeSlots[i]['label'] as String] = v;
          }
        }
        context.read<PredictorState>().update(
              readings: labeledReadings,
              food: _foodController.text.isNotEmpty ? _foodController.text : null,
              event: _selectedEvent,
              result: result,
            );
      }
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  Future<void> _runReplay(String caseId) async {
    setState(() { _loading = true; _error = null; });
    try {
      final result = await _api.replayCase(caseId);
      setState(() { _result = result; _loading = false; _resultExpanded = false; });
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  Color _glucoseColor(double glucose) {
    if (glucose < 3.9) return SC.glucoseHypo;
    if (glucose > 10.0) return SC.glucoseHyper;
    return SC.glucoseTarget;
  }

  Color _glucoseBgColor(double glucose) {
    if (glucose < 3.9) return SC.dangerLight;
    if (glucose > 10.0) return SC.warningLight;
    return SC.successLight;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SC.bg,
      body: SafeArea(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            _buildScenarioBanner(),
            _buildTabBar(),
            if (_tabIndex == 0)
              _buildManualInput()
            else if (_tabIndex == 1)
              _buildCGMMonitor()
            else
              _buildCaseList(),

            if (_loading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(child: CircularProgressIndicator(color: SC.primary)),
              ),

            if (_error != null)
              _buildErrorBanner(),

            if (_result != null && !_loading)
              _buildResultSection(),
          ],
        ),
      ),
    );
  }

  // ─── Result Section: 渐进式披露 ─────────────────
  Widget _buildResultSection() {
    final r = _result!;
    final glucoseColor = _glucoseColor(r.currentGlucose);
    final glucoseBg = _glucoseBgColor(r.currentGlucose);

    return Column(
      children: [
        // Hero 指标卡 — 折叠态
        GestureDetector(
          onTap: () => setState(() => _resultExpanded = !_resultExpanded),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
            child: Container(
              padding: SC.cardPadding,
              decoration: SC.cardHero.copyWith(
                color: glucoseBg,
              ),
              child: Column(
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        r.currentGlucose.toStringAsFixed(1),
                        style: SC.monoDisplay.copyWith(
                          fontSize: 36,
                          color: glucoseColor,
                          height: 1,
                        ),
                      ),
                      const SizedBox(width: 4),
                      Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(r.trend, style: SC.headline.copyWith(color: glucoseColor)),
                            Text('mmol/L', style: SC.caption),
                          ],
                        ),
                      ),
                      const Spacer(),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: SC.primaryLight,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          r.filterType.toUpperCase(),
                          style: SC.caption.copyWith(color: SC.primary, fontWeight: FontWeight.w700),
                        ),
                      ),
                      const SizedBox(width: 8),
                      AnimatedRotation(
                        turns: _resultExpanded ? 0.5 : 0,
                        duration: const Duration(milliseconds: 300),
                        child: const Icon(Icons.expand_more_rounded, color: SC.textTertiary),
                      ),
                    ],
                  ),
                  if (!_resultExpanded) ...[
                    const SizedBox(height: 8),
                    // 摘要行 — 最多 1 条最重要的警报预览
                    Row(
                      children: [
                        Icon(
                          r.alerts.isNotEmpty ? Icons.info_rounded : Icons.check_circle_rounded,
                          size: 14,
                          color: r.alerts.isNotEmpty ? SC.warning : SC.success,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            r.alerts.isNotEmpty
                                ? '${r.alerts.length} 条提醒 — 点击展开详情'
                                : '血糖状态良好 — 点击查看详情',
                            style: SC.label.copyWith(color: SC.textSecondary),
                          ),
                        ),
                      ],
                    ),
                    // 迷你 sparkline + 目标范围色带
                    if (r.chartData.filteredReadings.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: SizedBox(
                          height: 40,
                          child: _buildMiniSparkline(r),
                        ),
                      ),
                  ],
                ],
              ),
            ),
          ),
        ),
        // 展开态
        AnimatedSize(
          duration: const Duration(milliseconds: 400),
          curve: Curves.easeInOut,
          child: _resultExpanded
              ? Column(
                  children: [
                    Padding(
                      padding: SC.sectionPadding,
                      child: GlucoseChart(result: _result!),
                    ),
                    if (_result!.alerts.isNotEmpty) _buildAlerts(),
                    _buildAdvice(),
                    _buildTrace(),
                    SC.groupSpacing,
                  ],
                )
              : const SizedBox.shrink(),
        ),
      ],
    );
  }

  Widget _buildMiniSparkline(AnalysisResult r) {
    final data = r.chartData.filteredReadings;
    if (data.isEmpty) return const SizedBox.shrink();
    final spots = <FlSpot>[];
    for (int i = 0; i < data.length; i++) {
      spots.add(FlSpot(i.toDouble(), data[i]));
    }
    return LineChart(
      LineChartData(
        minY: 2,
        maxY: 16,
        gridData: const FlGridData(show: false),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        lineTouchData: const LineTouchData(enabled: false),
        rangeAnnotations: RangeAnnotations(
          horizontalRangeAnnotations: [
            HorizontalRangeAnnotation(y1: 3.9, y2: 10.0, color: SC.glucoseTarget.withAlpha(16)),
          ],
        ),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            curveSmoothness: 0.4,
            color: SC.primary.withAlpha(120),
            barWidth: 1.5,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: SC.primary.withAlpha(15),
            ),
          ),
        ],
      ),
      duration: const Duration(milliseconds: 800),
      curve: Curves.easeInOut,
    );
  }

  // ─── 场景 Banner ─────────────────────────

  static const _scenarios = [
    _ScenarioCard('🍚', '餐后高峰', '进食后 1-2 小时\n血糖波动分析', SC.warning, SC.warningLight),
    _ScenarioCard('🌙', '空腹监测', '晨起空腹\n基础血糖状态', SC.primary, SC.primaryLight),
    _ScenarioCard('🏃', '运动影响', '运动前后\n血糖变化规律', SC.success, SC.successLight),
    _ScenarioCard('💉', '胰岛素效果', '注射后\n降糖效果追踪', SC.info, SC.infoLight),
  ];

  Widget _buildScenarioBanner() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 10),
          child: Row(
            children: [
              Text('选择场景 · 快速分析', style: SC.label.copyWith(
                color: SC.textSecondary,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.3,
              )),
            ],
          ),
        ),
        SizedBox(
          height: 120,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            separatorBuilder: (_, __) => const SizedBox(width: 10),
            itemCount: _scenarios.length,
            itemBuilder: (context, i) {
              final s = _scenarios[i];
              return SC.pressable(
                onTap: () {
                  // 切换到手动输入 tab 并预填食物场景
                  _tabController.animateTo(0);
                  setState(() {
                    _tabIndex = 0;
                    _selectedEvent = s.event;
                  });
                },
                child: Container(
                  width: 130,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: s.bgColor,
                    borderRadius: BorderRadius.circular(SC.radiusMd),
                    border: Border.all(color: s.color.withAlpha(40)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(s.emoji, style: const TextStyle(fontSize: 22)),
                      const SizedBox(height: 8),
                      Text(s.title, style: SC.label.copyWith(
                        color: s.color,
                        fontWeight: FontWeight.w700,
                      )),
                      const SizedBox(height: 2),
                      Text(
                        s.subtitle,
                        style: SC.caption.copyWith(
                          color: s.color.withAlpha(180),
                          fontSize: 10,
                          height: 1.3,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 8),
      ],
    );
  }

  // ─── Tab Bar ───────────────────────────────

  Widget _buildTabBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      child: Container(
        height: 36,
        decoration: BoxDecoration(
          color: SC.borderLight,
          borderRadius: BorderRadius.circular(10),
        ),
        child: TabBar(
          controller: _tabController,
          indicator: BoxDecoration(
            color: SC.surface,
            borderRadius: BorderRadius.circular(8),
            boxShadow: [
              BoxShadow(color: SC.primary.withAlpha(15), blurRadius: 4, offset: const Offset(0, 1)),
            ],
          ),
          indicatorSize: TabBarIndicatorSize.tab,
          dividerHeight: 0,
          labelColor: SC.textPrimary,
          unselectedLabelColor: SC.textTertiary,
          labelStyle: SC.label.copyWith(fontWeight: FontWeight.w600),
          labelPadding: EdgeInsets.zero,
          tabs: const [
            Tab(text: '手动输入', height: 32),
            Tab(text: 'CGM 模拟', height: 32),
            Tab(text: '经典案例', height: 32),
          ],
        ),
      ),
    );
  }

  // ─── Tab 0: 手动输入 ───────────────────────

  Widget _buildManualInput() {
    return Padding(
      padding: SC.sectionPadding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Phase 5A: 默认 3 个时段，可展开全部 6 个
          _card(
            child: Column(
              children: [
                // 默认单行三列 — 空腹 + 早餐后 + 晚餐后
                Row(
                  children: [
                    for (int i = 0; i < _defaultSlotIndices.length; i++) ...[
                      if (i > 0) const SizedBox(width: 8),
                      Expanded(child: _slotChip(_defaultSlotIndices[i])),
                    ],
                  ],
                ),
                // 展开时显示其余 3 个时段
                AnimatedSize(
                  duration: const Duration(milliseconds: 300),
                  curve: Curves.easeInOut,
                  child: _slotsExpanded
                      ? Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Row(
                            children: [
                              for (int col = 0; col < 3; col++) ...[
                                if (col > 0) const SizedBox(width: 8),
                                Expanded(child: _slotChip([2, 3, 5][col])),
                              ],
                            ],
                          ),
                        )
                      : const SizedBox.shrink(),
                ),
                const SizedBox(height: 8),
                // 展开/折叠按钮
                GestureDetector(
                  onTap: _toggleSlotsExpanded,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      AnimatedRotation(
                        turns: _slotsExpanded ? 0.5 : 0,
                        duration: const Duration(milliseconds: 300),
                        child: const Icon(Icons.expand_more_rounded, size: 16, color: SC.textTertiary),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        _slotsExpanded ? '收起' : '展开全部 6 个时段',
                        style: SC.caption.copyWith(color: SC.textTertiary),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          // 食物 + 事件 + 按钮
          Row(
            children: [
              Expanded(
                flex: 3,
                child: SizedBox(
                  height: 36,
                  child: TextField(
                    controller: _foodController,
                    decoration: InputDecoration(
                      hintText: '食物（选填）',
                      hintStyle: SC.label.copyWith(color: SC.textTertiary),
                      filled: true,
                      fillColor: SC.surface,
                      border: _inputBorder(),
                      enabledBorder: _inputBorder(),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                    ),
                    style: SC.body.copyWith(fontSize: 13),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              SizedBox(
                width: 72,
                height: 36,
                child: Container(
                  decoration: BoxDecoration(
                    color: SC.surface,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: SC.border),
                  ),
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<String?>(
                      value: _selectedEvent,
                      isExpanded: true,
                      isDense: true,
                      hint: Text('事件', style: SC.label.copyWith(color: SC.textTertiary)),
                      style: SC.label.copyWith(color: SC.textPrimary),
                      items: const [
                        DropdownMenuItem(value: null, child: Text('无')),
                        DropdownMenuItem(value: 'meal', child: Text('用餐')),
                        DropdownMenuItem(value: 'insulin', child: Text('胰岛素')),
                        DropdownMenuItem(value: 'exercise', child: Text('运动')),
                        DropdownMenuItem(value: 'sleep', child: Text('睡眠')),
                      ],
                      onChanged: (v) => setState(() => _selectedEvent = v),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              SizedBox(
                height: 36,
                child: SC.pressable(
                  onTap: _loading ? null : _runAnalysis,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    decoration: BoxDecoration(
                      color: _loading ? SC.textTertiary : SC.primary,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Center(
                      child: Text('分析', style: SC.label.copyWith(
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      )),
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          // Phase 5C: 血糖日志折叠
          _buildGlucoseLog(),
        ],
      ),
    );
  }

  /// 紧凑的时段输入 chip
  Widget _slotChip(int index) {
    final slot = _timeSlots[index];
    return Row(
      children: [
        Icon(slot['icon'] as IconData, size: 13, color: SC.primary),
        const SizedBox(width: 4),
        Text(slot['label'] as String, style: SC.caption.copyWith(fontWeight: FontWeight.w600, color: SC.textPrimary)),
        const SizedBox(width: 4),
        Expanded(
          child: SizedBox(
            height: 26,
            child: TextField(
              controller: _slotControllers[index],
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              textAlign: TextAlign.center,
              style: SC.label.copyWith(fontFamily: SC.monoStyle.fontFamily),
              decoration: InputDecoration(
                contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                isDense: true,
                filled: true,
                fillColor: SC.borderLight,
                hintText: slot['hint'] as String,
                hintStyle: SC.caption.copyWith(fontSize: 9),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide(color: SC.border),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide(color: SC.border),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide(color: SC.primary),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  // ─── 血糖日志 (Phase 5C: 可折叠) ──────────────

  Widget _buildGlucoseLog() {
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 标题行 — 点击折叠/展开
          GestureDetector(
            onTap: () => setState(() => _glucoseLogExpanded = !_glucoseLogExpanded),
            child: Row(
              children: [
                const Icon(Icons.edit_note_rounded, size: 14, color: SC.textTertiary),
                const SizedBox(width: 4),
                Text('血糖记录', style: SC.label.copyWith(fontWeight: FontWeight.w600)),
                const Spacer(),
                if (_glucoseLog.isNotEmpty)
                  Text('${_glucoseLog.length} 条', style: SC.caption),
                const SizedBox(width: 4),
                AnimatedRotation(
                  turns: _glucoseLogExpanded ? 0.5 : 0,
                  duration: const Duration(milliseconds: 300),
                  child: const Icon(Icons.expand_more_rounded, size: 16, color: SC.textTertiary),
                ),
              ],
            ),
          ),
          // 展开态：录入表单和历史
          AnimatedSize(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeInOut,
            child: _glucoseLogExpanded
                ? Column(
                    children: [
                      const SizedBox(height: 8),
                      // 输入行
                      Row(
                        children: [
                          InkWell(
                            borderRadius: BorderRadius.circular(8),
                            onTap: () async {
                              final picked = await showDatePicker(
                                context: context,
                                initialDate: _logDate,
                                firstDate: DateTime(2020),
                                lastDate: DateTime.now(),
                              );
                              if (picked != null) setState(() => _logDate = picked);
                            },
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: SC.borderLight,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: SC.border),
                              ),
                              child: Text(
                                '${_logDate.month}/${_logDate.day}',
                                style: SC.caption.copyWith(color: SC.textSecondary),
                              ),
                            ),
                          ),
                          const SizedBox(width: 4),
                          InkWell(
                            borderRadius: BorderRadius.circular(8),
                            onTap: () async {
                              final picked = await showTimePicker(context: context, initialTime: _logTime);
                              if (picked != null) setState(() => _logTime = picked);
                            },
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: SC.borderLight,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: SC.border),
                              ),
                              child: Text(
                                '${_logTime.hour.toString().padLeft(2, '0')}:${_logTime.minute.toString().padLeft(2, '0')}',
                                style: SC.caption.copyWith(color: SC.textSecondary),
                              ),
                            ),
                          ),
                          const SizedBox(width: 4),
                          SizedBox(
                            width: 58,
                            height: 28,
                            child: TextField(
                              controller: _logGlucoseCtrl,
                              keyboardType: const TextInputType.numberWithOptions(decimal: true),
                              textAlign: TextAlign.center,
                              style: SC.label.copyWith(fontWeight: FontWeight.w600, color: SC.textPrimary),
                              decoration: InputDecoration(
                                hintText: 'mmol/L',
                                hintStyle: SC.caption.copyWith(fontSize: 9, fontWeight: FontWeight.normal),
                                contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                                isDense: true,
                                filled: true,
                                fillColor: SC.borderLight,
                                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: SC.border)),
                                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: SC.border)),
                                focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: SC.primary)),
                              ),
                            ),
                          ),
                          const SizedBox(width: 4),
                          Expanded(
                            child: SizedBox(
                              height: 28,
                              child: TextField(
                                controller: _logNoteCtrl,
                                style: SC.caption.copyWith(color: SC.textPrimary),
                                decoration: InputDecoration(
                                  hintText: '备注',
                                  hintStyle: SC.caption,
                                  contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                  isDense: true,
                                  filled: true,
                                  fillColor: SC.borderLight,
                                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: SC.border)),
                                  enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: SC.border)),
                                  focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: SC.primary)),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 4),
                          SizedBox(
                            width: 28,
                            height: 28,
                            child: IconButton(
                              onPressed: _addGlucoseEntry,
                              icon: const Icon(Icons.add_circle, size: 20, color: SC.primary),
                              padding: EdgeInsets.zero,
                              splashRadius: 16,
                            ),
                          ),
                        ],
                      ),

                      // 历史记录
                      if (_glucoseLog.isNotEmpty) ...[
                        const Divider(height: 16, color: SC.divider),
                        ..._glucoseLog.take(8).map((entry) {
                          final glucose = (entry['glucose_mmol'] as num).toDouble();
                          final ts = entry['timestamp'] as String? ?? '';
                          final note = entry['note'] as String? ?? '';
                          final id = entry['id'] as int;

                          String displayTime = ts;
                          try {
                            final dt = DateTime.parse(ts);
                            displayTime = '${dt.month}/${dt.day} ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
                          } catch (_) {}

                          final glucoseColor = _glucoseColor(glucose);

                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(
                              children: [
                                Container(width: 8, height: 8, decoration: BoxDecoration(color: glucoseColor, shape: BoxShape.circle)),
                                const SizedBox(width: 8),
                                Text(displayTime, style: SC.caption.copyWith(fontFamily: SC.monoStyle.fontFamily)),
                                const SizedBox(width: 8),
                                Text(glucose.toStringAsFixed(1),
                                    style: SC.label.copyWith(fontWeight: FontWeight.w700, color: glucoseColor)),
                                if (note.isNotEmpty) ...[
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(note,
                                        style: SC.caption,
                                        overflow: TextOverflow.ellipsis),
                                  ),
                                ] else
                                  const Spacer(),
                                InkWell(
                                  onTap: () => _deleteGlucoseEntry(id),
                                  borderRadius: BorderRadius.circular(4),
                                  child: const Icon(Icons.close, size: 12, color: SC.textTertiary),
                                ),
                              ],
                            ),
                          );
                        }),
                        if (_glucoseLog.length > 8)
                          Padding(
                            padding: const EdgeInsets.only(top: 4),
                            child: Center(
                              child: Text('还有 ${_glucoseLog.length - 8} 条', style: SC.caption),
                            ),
                          ),
                      ],
                    ],
                  )
                : const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }

  // ─── Tab 1: CGM 模拟 ──────────────────────

  Widget _buildCGMMonitor() {
    return Consumer<CGMState>(
      builder: (context, cgm, _) {
        return Padding(
          padding: SC.sectionPadding,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: SizedBox(
                      height: 40,
                      child: ElevatedButton.icon(
                        icon: Icon(
                          cgm.loading ? Icons.hourglass_top : Icons.play_arrow_rounded,
                          size: 18,
                        ),
                        label: Text(
                          cgm.readings.isEmpty ? '生成 24h 模拟数据' : '重新模拟',
                          style: SC.body.copyWith(fontWeight: FontWeight.w700, color: Colors.white),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: SC.info,
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          elevation: 0,
                        ),
                        onPressed: cgm.loading ? null : () => cgm.simulate(),
                      ),
                    ),
                  ),
                ],
              ),
              SC.sectionSpacing,

              if (cgm.error != null)
                _errorCard(cgm.error!),

              if (cgm.readings.isEmpty && !cgm.loading)
                _emptyHint(
                  Icons.monitor_heart_outlined,
                  '生成模拟 CGM 数据以查看 24 小时血糖曲线',
                ),

              if (cgm.readings.isNotEmpty) ...[
                _buildCGMStats(cgm),
                SC.sectionSpacing,
                _buildCGMChart(cgm),
                SC.sectionSpacing,
                _buildCGMEvents(cgm),
                SC.sectionSpacing,
                _buildCGMSessions(cgm),
              ],

              const SizedBox(height: 4),
            ],
          ),
        );
      },
    );
  }

  Widget _buildCGMStats(CGMState cgm) {
    return _card(
      child: Row(
        children: [
          _stat('平均', cgm.meanGlucose.toStringAsFixed(1), SC.info),
          _stat('最低', cgm.minGlucose.toStringAsFixed(1), SC.glucoseTarget),
          _stat('最高', cgm.maxGlucose.toStringAsFixed(1), SC.glucoseHypo),
          _stat('TIR', '${cgm.timeInRange.toStringAsFixed(0)}%', SC.success),
        ],
      ),
    );
  }

  Widget _buildCGMChart(CGMState cgm) {
    final readings = cgm.readings;
    final step = (readings.length / 144).ceil().clamp(1, 10);
    final sampled = <FlSpot>[];
    for (int i = 0; i < readings.length; i += step) {
      sampled.add(FlSpot(i.toDouble(), readings[i].glucoseMmol));
    }
    final minY = (cgm.minGlucose - 1).clamp(0.0, 20.0);
    final maxY = (cgm.maxGlucose + 1).clamp(5.0, 25.0);

    return _card(
      child: SizedBox(
        height: 200,
        child: LineChart(
          LineChartData(
            minY: minY,
            maxY: maxY,
            gridData: FlGridData(
              show: true,
              horizontalInterval: 2,
              getDrawingHorizontalLine: (value) {
                if (value == 3.9 || value == 10.0) {
                  return FlLine(color: SC.warning.withAlpha(100), strokeWidth: 1, dashArray: [5, 5]);
                }
                return FlLine(color: SC.border.withAlpha(60), strokeWidth: 0.5);
              },
            ),
            titlesData: FlTitlesData(
              leftTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  reservedSize: 32,
                  getTitlesWidget: (value, meta) =>
                      Text('${value.toInt()}', style: SC.caption.copyWith(fontSize: 10)),
                ),
              ),
              bottomTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  interval: readings.length / 6,
                  getTitlesWidget: (value, meta) {
                    final idx = value.toInt();
                    if (idx < 0 || idx >= readings.length) return const SizedBox.shrink();
                    final ts = readings[idx].timestamp;
                    final timePart = ts.length >= 16 ? ts.substring(11, 16) : ts;
                    return Text(timePart, style: SC.caption.copyWith(fontSize: 9));
                  },
                ),
              ),
              topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
              rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            ),
            borderData: FlBorderData(show: false),
            rangeAnnotations: RangeAnnotations(
              horizontalRangeAnnotations: [
                HorizontalRangeAnnotation(y1: 3.9, y2: 10.0, color: SC.glucoseTarget.withAlpha(12)),
              ],
            ),
            lineBarsData: [
              LineChartBarData(
                spots: sampled,
                isCurved: true,
                color: SC.info,
                barWidth: 2,
                dotData: const FlDotData(show: false),
                belowBarData: BarAreaData(show: true, color: SC.info.withAlpha(30)),
              ),
            ],
            lineTouchData: LineTouchData(
              touchTooltipData: LineTouchTooltipData(
                getTooltipItems: (spots) => spots.map((s) => LineTooltipItem(
                      '${s.y.toStringAsFixed(1)} mmol/L',
                      SC.label.copyWith(color: Colors.white, fontWeight: FontWeight.bold),
                    )).toList(),
              ),
            ),
          ),
          duration: const Duration(milliseconds: 800),
          curve: Curves.easeInOut,
        ),
      ),
    );
  }

  Widget _buildCGMEvents(CGMState cgm) {
    final events = cgm.readings.where((r) => r.event.isNotEmpty).toList();
    if (events.isEmpty) return const SizedBox.shrink();

    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.flag_rounded, size: 14, color: SC.textSecondary),
              const SizedBox(width: 4),
              Text('事件标记', style: SC.label.copyWith(fontWeight: FontWeight.w600)),
            ],
          ),
          const SizedBox(height: 8),
          ...events.map((e) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  children: [
                    Icon(
                      e.event.contains('meal') ? Icons.restaurant : Icons.medication,
                      size: 14,
                      color: e.event.contains('meal') ? SC.accent : SC.info,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      e.timestamp.length >= 16 ? e.timestamp.substring(11, 16) : e.timestamp,
                      style: SC.caption.copyWith(fontWeight: FontWeight.w600, fontFamily: SC.monoStyle.fontFamily, color: SC.textPrimary),
                    ),
                    const SizedBox(width: 8),
                    Expanded(child: Text(e.event, style: SC.caption.copyWith(color: SC.textSecondary))),
                    Text(e.glucoseMmol.toStringAsFixed(1),
                        style: SC.caption.copyWith(fontWeight: FontWeight.bold, color: SC.textPrimary)),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  Widget _buildCGMSessions(CGMState cgm) {
    if (cgm.sessions.isEmpty) return const SizedBox.shrink();

    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.history, size: 14, color: SC.textSecondary),
              const SizedBox(width: 4),
              Text('历史会话', style: SC.label.copyWith(fontWeight: FontWeight.w600)),
            ],
          ),
          const SizedBox(height: 8),
          ...cgm.sessions.take(3).map((s) => InkWell(
                onTap: cgm.streaming ? null : () => cgm.startStream(s.sessionId),
                borderRadius: BorderRadius.circular(8),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Row(
                    children: [
                      const Icon(Icons.play_circle_outline, size: 16, color: SC.info),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(s.sessionId, style: SC.caption.copyWith(color: SC.textPrimary), overflow: TextOverflow.ellipsis),
                      ),
                      Text('${s.readingCount} 条', style: SC.caption),
                    ],
                  ),
                ),
              )),
        ],
      ),
    );
  }

  // ─── Tab 2: 经典案例 ──────────────────────

  Widget _buildCaseList() {
    if (_cases.isEmpty) {
      return _emptyHint(Icons.hourglass_empty, '加载案例中...');
    }

    return Padding(
      padding: SC.sectionPadding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: SC.primaryLight,
              borderRadius: BorderRadius.circular(SC.radiusMd),
            ),
            child: Row(
              children: [
                const Icon(Icons.school_rounded, size: 18, color: SC.primary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '选择一个经典场景，体验 SugarClaw 如何分析真实血糖模式',
                    style: SC.label.copyWith(color: SC.textSecondary, height: 1.4),
                  ),
                ),
              ],
            ),
          ),
          SC.sectionSpacing,

          ..._cases.map((c) {
            final (icon, color) = _caseIcon(c.scenario);
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Material(
                color: SC.surface,
                borderRadius: BorderRadius.circular(12),
                child: InkWell(
                  borderRadius: BorderRadius.circular(12),
                  onTap: _loading ? null : () => _runReplay(c.id),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            color: color.withAlpha(20),
                            borderRadius: BorderRadius.circular(SC.radiusMd),
                          ),
                          child: Icon(icon, color: color, size: 18),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(c.title, style: SC.body.copyWith(fontWeight: FontWeight.w600)),
                              const SizedBox(height: 4),
                              Text(c.description,
                                  style: SC.caption.copyWith(height: 1.3),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: color.withAlpha(15),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text('回放', style: SC.caption.copyWith(color: color, fontWeight: FontWeight.w600)),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          }),
          const SizedBox(height: 4),
        ],
      ),
    );
  }

  (IconData, Color) _caseIcon(String scenario) {
    switch (scenario) {
      case 'meal':
        return (Icons.restaurant_rounded, SC.accent);
      case 'insulin':
        return (Icons.vaccines_rounded, SC.info);
      default:
        return (Icons.nightlight_round, SC.primary);
    }
  }

  // ─── Results helpers ──────────────────────────────

  Widget _buildAlerts() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: Column(children: _result!.alerts.map((a) => AlertCard(alert: a)).toList()),
    );
  }

  Widget _buildAdvice() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: AdviceBubble(advice: _result!.advice),
    );
  }

  Widget _buildTrace() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: AgentTraceCard(traces: _result!.agentTraces),
    );
  }

  Widget _buildErrorBanner() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: _errorCard(_error!),
    );
  }

  // ─── Shared helpers ───────────────────────

  Widget _card({required Widget child}) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: SC.surface,
        borderRadius: BorderRadius.circular(SC.radiusMd),
        border: Border.all(color: SC.borderLight),
      ),
      child: child,
    );
  }

  Widget _stat(String label, String value, Color color) {
    return Expanded(
      child: Column(
        children: [
          Text(label, style: SC.caption),
          const SizedBox(height: 4),
          Text(value, style: SC.headline.copyWith(color: color)),
          Text('mmol/L', style: SC.caption.copyWith(fontSize: 9)),
        ],
      ),
    );
  }

  OutlineInputBorder _inputBorder() {
    return OutlineInputBorder(
      borderRadius: BorderRadius.circular(SC.radiusMd),
      borderSide: BorderSide(color: SC.border),
    );
  }

  Widget _emptyHint(IconData icon, String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 40),
      child: Center(
        child: Column(
          children: [
            Icon(icon, size: 48, color: SC.textTertiary),
            const SizedBox(height: 8),
            Text(text, style: SC.body.copyWith(color: SC.textTertiary)),
          ],
        ),
      ),
    );
  }

  Widget _errorCard(String msg) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: SC.dangerLight,
        borderRadius: BorderRadius.circular(SC.radiusMd),
      ),
      child: Text(msg, style: SC.label.copyWith(color: SC.danger)),
    );
  }
}

/// 场景卡片数据
class _ScenarioCard {
  final String emoji;
  final String title;
  final String subtitle;
  final Color color;
  final Color bgColor;

  const _ScenarioCard(
    this.emoji,
    this.title,
    this.subtitle,
    this.color,
    this.bgColor,
  );

  String? get event {
    if (title.contains('餐')) return 'meal';
    if (title.contains('运动')) return 'exercise';
    if (title.contains('胰岛素')) return 'insulin';
    return null;
  }
}
