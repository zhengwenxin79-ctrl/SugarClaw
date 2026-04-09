import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../models/counterbalance.dart';
import '../providers/scale_state.dart';
import '../theme.dart';
import '../widgets/advice_bubble.dart';

class ScaleScreen extends StatelessWidget {
  const ScaleScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => ScaleState(),
      child: const _ScaleBody(),
    );
  }
}

class _ScaleBody extends StatefulWidget {
  const _ScaleBody();

  @override
  State<_ScaleBody> createState() => _ScaleBodyState();
}

class _ScaleBodyState extends State<_ScaleBody> with TickerProviderStateMixin {
  late AnimationController _tiltController;
  late Animation<double> _tiltAnimation;
  double _prevTilt = 0;

  late AnimationController _rippleController;
  late Animation<double> _rippleAnimation;

  // 悬浮天平尺寸与位置
  static const double _floatSize = 100.0;
  Offset _floatOffset = const Offset(double.infinity, 16); // sentinel for init
  bool _floatExpanded = false; // 点击展开显示详情

  @override
  void initState() {
    super.initState();
    _tiltController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    );
    _tiltAnimation = Tween<double>(begin: 0, end: 0).animate(
      CurvedAnimation(parent: _tiltController, curve: Curves.elasticOut),
    );
    _rippleController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    _rippleAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _rippleController, curve: Curves.easeOut),
    );
  }

  @override
  void dispose() {
    _tiltController.dispose();
    _rippleController.dispose();
    super.dispose();
  }

  void _animateTilt(double target, {bool balanced = false}) {
    if ((target - _prevTilt).abs() < 0.001) return;
    _tiltAnimation = Tween<double>(
      begin: _tiltAnimation.value,
      end: target,
    ).animate(
      CurvedAnimation(parent: _tiltController, curve: Curves.elasticOut),
    );
    _tiltController.forward(from: 0);
    _prevTilt = target;
    if (balanced) {
      HapticFeedback.heavyImpact();
      _rippleController.forward(from: 0);
    }
  }

  // ─── Dialogs ───────────────────────────────────

  void _showAddFoodDialog(ScaleState state) {
    HapticFeedback.lightImpact();
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text('添加食物', style: SC.headline.copyWith(fontSize: 16)),
        content: TextField(
          controller: controller,
          autofocus: true,
          style: SC.body,
          decoration: InputDecoration(
            hintText: '输入食物名称...',
            hintStyle: SC.body.copyWith(color: SC.textTertiary),
            filled: true,
            fillColor: SC.bg,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide.none,
            ),
          ),
          onSubmitted: (val) {
            if (val.trim().isNotEmpty) {
              state.addCustomFood(val.trim());
              Navigator.of(ctx).pop();
            }
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text('取消', style: SC.body.copyWith(color: SC.textTertiary)),
          ),
          ElevatedButton(
            onPressed: () {
              if (controller.text.trim().isNotEmpty) {
                state.addCustomFood(controller.text.trim());
                Navigator.of(ctx).pop();
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: SC.accent,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(SC.radiusMd)),
              elevation: 0,
            ),
            child: Text('添加并分析', style: SC.label.copyWith(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  void _showAddExerciseDialog(ScaleState state) {
    HapticFeedback.lightImpact();
    final nameController = TextEditingController();
    final durationController = TextEditingController(text: '20');
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text('添加自定义运动', style: SC.headline.copyWith(fontSize: 16)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              autofocus: true,
              style: SC.body,
              decoration: InputDecoration(
                hintText: '运动名称（如瑜伽、跳绳）',
                hintStyle: SC.body.copyWith(color: SC.textTertiary),
                filled: true,
                fillColor: SC.bg,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: durationController,
              keyboardType: TextInputType.number,
              style: SC.body,
              decoration: InputDecoration(
                hintText: '时长（分钟）',
                hintStyle: SC.body.copyWith(color: SC.textTertiary),
                filled: true,
                fillColor: SC.bg,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
                suffixText: '分钟',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text('取消', style: SC.body.copyWith(color: SC.textTertiary)),
          ),
          ElevatedButton(
            onPressed: () {
              final name = nameController.text.trim();
              final dur = int.tryParse(durationController.text.trim()) ?? 0;
              if (name.isNotEmpty && dur > 0) {
                state.addCustomExercise(name, dur);
                Navigator.of(ctx).pop();
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: SC.info,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(SC.radiusMd)),
              elevation: 0,
            ),
            child: Text('添加', style: SC.label.copyWith(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  void _showAddFoodCounterDialog(ScaleState state) {
    HapticFeedback.lightImpact();
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text('添加对冲食物', style: SC.headline.copyWith(fontSize: 16)),
        content: TextField(
          controller: controller,
          autofocus: true,
          style: SC.body,
          decoration: InputDecoration(
            hintText: '食物名称（如豆腐、西兰花）',
            hintStyle: SC.body.copyWith(color: SC.textTertiary),
            filled: true,
            fillColor: SC.bg,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide.none,
            ),
          ),
          onSubmitted: (val) {
            if (val.trim().isNotEmpty) {
              state.addCustomFoodCounter(val.trim());
              Navigator.of(ctx).pop();
            }
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text('取消', style: SC.body.copyWith(color: SC.textTertiary)),
          ),
          ElevatedButton(
            onPressed: () {
              if (controller.text.trim().isNotEmpty) {
                state.addCustomFoodCounter(controller.text.trim());
                Navigator.of(ctx).pop();
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: SC.success,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(SC.radiusMd)),
              elevation: 0,
            ),
            child: Text('添加', style: SC.label.copyWith(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  // ─── Build ─────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SC.bg,
      body: SafeArea(
        child: Consumer<ScaleState>(
          builder: (context, state, _) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              _animateTilt(state.tiltAngle, balanced: state.isBalanced);
            });

            return LayoutBuilder(
              builder: (context, constraints) {
                // 初始化悬浮位置：右上角
                if (_floatOffset.dx == double.infinity) {
                  _floatOffset = Offset(
                      constraints.maxWidth - _floatSize - 12, 12);
                }

                return Stack(
                  children: [
                    // ── 全宽可滚动内容 ──
                    CustomScrollView(
                      slivers: [
                        // ── 标题行 ──
                        SliverToBoxAdapter(child: _buildTitle(state)),
                        // ── 食物卡片行 ──
                        SliverToBoxAdapter(child: _buildFoodCardRow(state)),
                        // ── 加载/错误状态 ──
                        if (state.loadingRisk || state.loadingBalance)
                          const SliverToBoxAdapter(
                            child: Padding(
                              padding: EdgeInsets.symmetric(vertical: 24),
                              child: Center(
                                child: CircularProgressIndicator(
                                    color: SC.accent, strokeWidth: 3),
                              ),
                            ),
                          ),
                        if (state.error != null)
                          SliverToBoxAdapter(
                            child: Padding(
                              padding: const EdgeInsets.symmetric(horizontal: 16),
                              child: SC.emptyState(
                                Icons.error_outline,
                                '分析失败',
                                subtitle: state.error,
                                ctaLabel: '重试',
                                onCta: () {
                                  final foods = state.selectedFoods.toList();
                                  state.selectedFoods.clear();
                                  state.riskResults.clear();
                                  for (final f in foods) {
                                    state.toggleFood(f);
                                  }
                                },
                              ),
                            ),
                          ),
                        // ── 风险卡片 ──
                        if (state.riskResults.isNotEmpty)
                          SliverToBoxAdapter(child: _buildRiskBadges(state)),
                        if (state.riskResults.isNotEmpty) ...[
                          for (final rr in state.riskResults.values)
                            if (rr.timeAdvice.isNotEmpty)
                              SliverToBoxAdapter(
                                  child: _buildTimeAdvice(rr.timeAdvice)),
                        ],
                        // ── 对冲方案 ──
                        if (state.balanceResult != null) ...[
                          SliverToBoxAdapter(
                            child: _buildSectionTitle(
                              '对冲方案',
                              Icons.auto_fix_high_rounded,
                              SC.success,
                              '点击选择 · 长按拖拽',
                            ),
                          ),
                          SliverToBoxAdapter(child: _buildProgressBar(state)),
                          SliverToBoxAdapter(child: _buildSolutionCards(state)),
                          if (state.isBalanced)
                            SliverToBoxAdapter(child: _buildBalancedBanner()),
                          SliverToBoxAdapter(
                            child: Padding(
                              padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                              child: AdviceBubble(
                                  advice: state.currentAdvice ??
                                      state.balanceResult!.advice),
                            ),
                          ),
                        ],
                        const SliverToBoxAdapter(child: SizedBox(height: 32)),
                      ],
                    ),
                    // ── 悬浮可拖动天平 ──
                    Positioned(
                      left: _floatOffset.dx,
                      top: _floatOffset.dy,
                      child: _buildFloatingScale(
                          state, constraints.maxWidth, constraints.maxHeight),
                    ),
                  ],
                );
              },
            );
          },
        ),
      ),
    );
  }

  // ─── Floating Draggable Scale ──────────────────

  Widget _buildFloatingScale(
      ScaleState state, double maxW, double maxH) {
    final expanded = _floatExpanded;
    final size = expanded ? _floatSize * 1.8 : _floatSize;

    return GestureDetector(
      onPanUpdate: (d) {
        setState(() {
          _floatOffset = Offset(
            (_floatOffset.dx + d.delta.dx).clamp(0, maxW - size),
            (_floatOffset.dy + d.delta.dy).clamp(0, maxH - size),
          );
        });
      },
      onTap: () {
        setState(() => _floatExpanded = !_floatExpanded);
      },
      child: DragTarget<int>(
        onAcceptWithDetails: (d) {
          HapticFeedback.mediumImpact();
          state.dropSolution(d.data);
        },
        builder: (context, candidates, _) {
          final hovering = candidates.isNotEmpty;
          return AnimatedContainer(
            duration: const Duration(milliseconds: 250),
            curve: Curves.easeOut,
            width: size,
            height: size,
            decoration: BoxDecoration(
              color: hovering
                  ? SC.success.withAlpha(30)
                  : SC.surface.withAlpha(245),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: hovering
                    ? SC.success.withAlpha(150)
                    : state.isBalanced
                        ? SC.success.withAlpha(100)
                        : SC.border.withAlpha(120),
                width: hovering ? 2 : 1,
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withAlpha(20),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(15),
              child: Column(
                children: [
                  // 天平动画
                  Expanded(
                    child: AnimatedBuilder(
                      animation: Listenable.merge(
                          [_tiltAnimation, _rippleAnimation]),
                      builder: (context, _) {
                        return CustomPaint(
                          painter: _ScalePainter(
                            tilt: _tiltAnimation.value,
                            riskWeight: state.riskWeight,
                            balanceWeight: state.balanceWeight,
                            leftFood: null, // 小尺寸不显示食物名
                            isBalanced: state.isBalanced,
                            rippleProgress: _rippleAnimation.value,
                          ),
                          size: Size.infinite,
                        );
                      },
                    ),
                  ),
                  // 底部百分比条
                  if (state.riskWeight > 0)
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 3),
                      color: (state.isBalanced ? SC.success : SC.accent)
                          .withAlpha(15),
                      child: Text(
                        '${(state.balanceWeight / state.riskWeight * 100).clamp(0, 999).toStringAsFixed(0)}%  ${state.balanceWeight.toStringAsFixed(0)}/${state.riskWeight.toStringAsFixed(0)}',
                        textAlign: TextAlign.center,
                        style: SC.caption.copyWith(
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                          color: state.isBalanced ? SC.success : SC.accent,
                        ),
                      ),
                    ),
                  // 展开时显示已选食物
                  if (expanded && state.selectedFoods.isNotEmpty)
                    Container(
                      constraints: BoxConstraints(maxHeight: size * 0.3),
                      padding: const EdgeInsets.fromLTRB(4, 2, 4, 4),
                      child: SingleChildScrollView(
                        child: Wrap(
                          spacing: 3,
                          runSpacing: 3,
                          alignment: WrapAlignment.center,
                          children: state.selectedFoods.map((food) {
                            return Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 4, vertical: 2),
                              decoration: BoxDecoration(
                                color: SC.danger.withAlpha(15),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                '${_foodEmoji(food)}$food×${state.quantityOf(food)}${state.unitFor(food)}',
                                style: SC.caption.copyWith(
                                    fontSize: 8,
                                    fontWeight: FontWeight.w600),
                              ),
                            );
                          }).toList(),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  // ─── Title Row ───────────────────────────────

  Widget _buildTitle(ScaleState state) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 8, 4),
      child: Row(
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              gradient: SC.accentGradient,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.balance_rounded,
                color: Colors.white, size: 16),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('饮食对冲天平',
                    style: SC.headline.copyWith(fontSize: 14)),
                Text('点击食物卡片多选，天平风险叠加', style: SC.caption),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ─── Section Title ──────────────────────────────

  Widget _buildSectionTitle(
      String title, IconData icon, Color color, String subtitle) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
      child: Row(
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 8),
          Text(title,
              style: SC.body.copyWith(fontWeight: FontWeight.w700, color: color)),
          const SizedBox(width: 8),
          Expanded(child: Text(subtitle, style: SC.caption)),
        ],
      ),
    );
  }

  // ─── Food Card Row ──────────────────────────────

  Widget _buildFoodCardRow(ScaleState state) {
    return SizedBox(
      height: 110,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: state.foodLibrary.length + 1,
        itemBuilder: (context, i) {
          if (i == 0) return _buildAddFoodCard(state);
          final name = state.foodLibrary[i - 1];
          final isActive = state.selectedFoods.contains(name);
          return _buildFoodCard(name, isActive, state);
        },
      ),
    );
  }

  Widget _buildFoodCard(String name, bool isActive, ScaleState state) {
    final qty = state.quantityOf(name);
    final unit = state.unitFor(name);
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SC.pressable(
            onTap: () {
              HapticFeedback.lightImpact();
              state.toggleFood(name);
            },
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              width: 76,
              height: 72,
              decoration: BoxDecoration(
                color: isActive ? SC.accent : SC.surface,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: isActive ? SC.accent : SC.border,
                  width: isActive ? 2 : 1,
                ),
                boxShadow: isActive
                    ? [BoxShadow(color: SC.accent.withAlpha(40), blurRadius: 8, offset: const Offset(0, 4))]
                    : [],
              ),
              child: Stack(
                children: [
                  Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          _foodEmoji(name),
                          style: const TextStyle(fontSize: 22),
                        ),
                        const SizedBox(height: 4),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: Text(
                            isActive ? '$name×$qty$unit' : name,
                            style: SC.caption.copyWith(
                              fontWeight: FontWeight.w600,
                              color: isActive ? Colors.white : SC.textPrimary,
                              fontSize: isActive ? 9 : null,
                            ),
                            maxLines: 2,
                            textAlign: TextAlign.center,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
                  // Checkmark for selected
                  if (isActive)
                    Positioned(
                      top: 4,
                      right: 4,
                      child: Container(
                        width: 18,
                        height: 18,
                        decoration: BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                          boxShadow: [BoxShadow(color: Colors.black.withAlpha(20), blurRadius: 2)],
                        ),
                        child: const Icon(Icons.check, size: 12, color: SC.accent),
                      ),
                    ),
                ],
              ),
            ),
          ),
          if (isActive) _buildQuantityStepper(name, qty, state),
        ],
      ),
    );
  }

  Widget _buildQuantityStepper(String name, int qty, ScaleState state) {
    return Container(
      width: 76,
      height: 28,
      margin: const EdgeInsets.only(top: 4),
      decoration: BoxDecoration(
        color: SC.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: SC.border),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          GestureDetector(
            onTap: () {
              HapticFeedback.selectionClick();
              state.setQuantity(name, qty - 1);
            },
            child: Container(
              width: 26,
              height: 28,
              alignment: Alignment.center,
              child: Text('−', style: SC.caption.copyWith(fontWeight: FontWeight.w700, color: SC.accent)),
            ),
          ),
          Text(
            '$qty',
            style: SC.caption.copyWith(fontWeight: FontWeight.w700, color: SC.textPrimary),
          ),
          GestureDetector(
            onTap: () {
              HapticFeedback.selectionClick();
              state.setQuantity(name, qty + 1);
            },
            child: Container(
              width: 26,
              height: 28,
              alignment: Alignment.center,
              child: Text('+', style: SC.caption.copyWith(fontWeight: FontWeight.w700, color: SC.accent)),
            ),
          ),
        ],
      ),
    );
  }

  String _foodEmoji(String name) {
    const map = {
      '热干面': '🍜',
      '白米饭': '🍚',
      '螺蛳粉': '🍜',
      '肠粉': '🥟',
      '馒头': '🍞',
      '面包': '🥖',
      '牛奶': '🥛',
      '苹果': '🍎',
    };
    return map[name] ?? '🍽️';
  }

  Widget _buildAddFoodCard(ScaleState state) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: SC.pressable(
        onTap: () => _showAddFoodDialog(state),
        child: Container(
          width: 76,
          decoration: BoxDecoration(
            color: SC.surface,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: SC.border, width: 1.5),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.add_rounded, size: 28, color: SC.textTertiary),
              const SizedBox(height: 4),
              Text('搜索',
                  style: SC.caption.copyWith(fontWeight: FontWeight.w600)),
            ],
          ),
        ),
      ),
    );
  }

  // ─── Risk Badges (all selected foods) ──────────

  Widget _buildRiskBadges(ScaleState state) {
    return Column(
      children: state.riskResults.entries.map((entry) {
        final r = entry.value;
        Color lc;
        String levelText;
        switch (r.riskLevel) {
          case 'low':
            lc = SC.success;
            levelText = '低风险';
            break;
          case 'medium':
            lc = SC.warning;
            levelText = '中风险';
            break;
          default:
            lc = SC.danger;
            levelText = '高风险';
        }
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: SC.surface,
              borderRadius: BorderRadius.circular(SC.radiusMd),
              border: Border.all(color: lc.withAlpha(50)),
            ),
            child: Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: lc.withAlpha(20),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Center(
                    child: Text(
                      r.riskWeight.toStringAsFixed(0),
                      style: SC.headline.copyWith(fontSize: 16, color: lc),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(children: [
                        Text(r.food.name,
                            style:
                                SC.body.copyWith(fontWeight: FontWeight.w700)),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: lc.withAlpha(20),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(levelText,
                              style: SC.caption.copyWith(
                                  color: lc, fontWeight: FontWeight.w700)),
                        ),
                        if (r.mealContext.isNotEmpty) ...[
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: SC.primaryLight,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(r.mealContext,
                                style: SC.caption.copyWith(
                                    color: SC.primary,
                                    fontWeight: FontWeight.w700)),
                          ),
                        ],
                      ]),
                      const SizedBox(height: 4),
                      Text(r.riskDetail,
                          style: SC.caption,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis),
                    ],
                  ),
                ),
                // Remove button
                GestureDetector(
                  onTap: () {
                    HapticFeedback.lightImpact();
                    state.deselectFood(entry.key);
                  },
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    child: Icon(Icons.close_rounded,
                        size: 16, color: SC.textTertiary),
                  ),
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }

  // ─── Time Advice ────────────────────────────────

  Widget _buildTimeAdvice(String advice) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: SC.primaryLight,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: SC.primary.withAlpha(40)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.schedule_rounded, size: 16, color: SC.primary),
            const SizedBox(width: 8),
            Expanded(
              child: Text(advice,
                  style: SC.label.copyWith(color: SC.textPrimary, height: 1.5)),
            ),
          ],
        ),
      ),
    );
  }

  // ─── Progress Bar ───────────────────────────────

  Widget _buildProgressBar(ScaleState state) {
    final progress = state.riskWeight > 0
        ? (state.balanceWeight / state.riskWeight).clamp(0.0, 1.0)
        : 0.0;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
      child: Row(
        children: [
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: LinearProgressIndicator(
                value: progress,
                minHeight: 8,
                backgroundColor: SC.borderLight,
                valueColor: AlwaysStoppedAnimation<Color>(
                  state.isBalanced ? SC.success : SC.accent,
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Text(
            '${state.balanceWeight.toStringAsFixed(0)} / ${state.riskWeight.toStringAsFixed(0)}',
            style: SC.label.copyWith(
              fontWeight: FontWeight.w700,
              color: state.isBalanced ? SC.success : SC.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  // ─── Solution Cards ─────────────────────────────

  Widget _buildSolutionCards(ScaleState state) {
    final solutions = state.balanceResult!.solutions;

    final groupOrder = <String>[];
    final groupIndices = <String, List<int>>{};
    for (int i = 0; i < solutions.length; i++) {
      final g = solutions[i].group.isEmpty ? '其他' : solutions[i].group;
      if (!groupIndices.containsKey(g)) {
        groupOrder.add(g);
        groupIndices[g] = [];
      }
      groupIndices[g]!.add(i);
    }

    const groupEmojis = <String, String>{
      '蔬菜搭配': '🥦',
      '蛋白搭配': '🥚',
      '主食替换': '🍙',
      '汤饮搭配': '🍵',
      '烹饪技巧': '👨‍🍳',
      '运动': '🏃',
    };
    const groupColors = <String, Color>{
      '蔬菜搭配': SC.success,
      '蛋白搭配': SC.accent,
      '主食替换': SC.purple,
      '汤饮搭配': SC.info,
      '烹饪技巧': SC.textSecondary,
      '运动': SC.info,
    };

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final group in groupOrder) ...[
            const SizedBox(height: 10),
            // Group header
            Row(
              children: [
                Text(groupEmojis[group] ?? '📦', style: const TextStyle(fontSize: 14)),
                const SizedBox(width: 6),
                Text(group,
                    style: SC.label.copyWith(
                        fontWeight: FontWeight.w700,
                        color: groupColors[group] ?? SC.textSecondary)),
                const SizedBox(width: 8),
                Text(group == '烹饪技巧' ? '固定展示' : '可多选',
                    style: SC.caption),
              ],
            ),
            const SizedBox(height: 6),
            // Horizontal scroll of solution chips
            SizedBox(
              height: 44,
              child: Builder(builder: (context) {
                final isExerciseGroup = group == '运动';
                final isFoodGroup = group == '蔬菜搭配' ||
                    group == '蛋白搭配' ||
                    group == '主食替换' ||
                    group == '汤饮搭配';
                final hasAddButton = isExerciseGroup || isFoodGroup;
                final indices = groupIndices[group]!;
                final itemCount = indices.length + (hasAddButton ? 1 : 0);
                return ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: itemCount,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (context, j) {
                    if (j == 0 && hasAddButton) {
                      return _buildAddSolutionChip(
                        state,
                        isExercise: isExerciseGroup,
                        color: isExerciseGroup ? SC.info : SC.success,
                      );
                    }
                    final listIdx = hasAddButton ? j - 1 : j;
                    final idx = indices[listIdx];
                    return _draggableMiniCard(state, idx, solutions[idx]);
                  },
                );
              }),
            ),
          ],
        ],
      ),
    );
  }

  Widget _draggableMiniCard(
      ScaleState state, int index, CounterSolution s) {
    final selected = state.selectedIndices.contains(index);
    Color ac;
    String emoji;
    switch (s.type) {
      case 'exercise':
        ac = SC.info;
        emoji = '🏃';
        break;
      default:
        ac = SC.success;
        emoji = '🥗';
    }

    final chip = AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: selected ? ac.withAlpha(20) : SC.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: selected ? ac : SC.border,
          width: selected ? 2 : 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(emoji, style: const TextStyle(fontSize: 14)),
          const SizedBox(width: 6),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 100),
            child: Text(
              s.name,
              style: SC.caption.copyWith(
                fontWeight: FontWeight.w600,
                color: selected ? ac : SC.textPrimary,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
            decoration: BoxDecoration(
              color: selected ? ac : SC.borderLight,
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              '+${s.balanceWeight.toStringAsFixed(0)}',
              style: SC.caption.copyWith(
                fontWeight: FontWeight.w700,
                color: selected ? Colors.white : SC.textSecondary,
              ),
            ),
          ),
          if (selected)
            const Padding(
              padding: EdgeInsets.only(left: 4),
              child: Icon(Icons.check_circle, size: 14, color: SC.success),
            ),
        ],
      ),
    );

    return LongPressDraggable<int>(
      data: index,
      feedback: Material(
        elevation: 6,
        borderRadius: BorderRadius.circular(12),
        child: Opacity(opacity: 0.9, child: chip),
      ),
      childWhenDragging: Opacity(opacity: 0.3, child: chip),
      child: GestureDetector(
        onTap: () {
          HapticFeedback.lightImpact();
          state.toggleSolution(index);
        },
        child: chip,
      ),
    );
  }

  Widget _buildAddSolutionChip(ScaleState state,
      {required bool isExercise, required Color color}) {
    return SC.pressable(
      onTap: () {
        if (isExercise) {
          _showAddExerciseDialog(state);
        } else {
          _showAddFoodCounterDialog(state);
        }
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: color.withAlpha(15),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withAlpha(100), width: 1.5),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isExercise ? Icons.add_rounded : Icons.search_rounded,
              size: 16,
              color: color,
            ),
            const SizedBox(width: 4),
            Text(
              isExercise ? '添加运动' : '搜索食物',
              style: SC.caption.copyWith(
                fontWeight: FontWeight.w700,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─── Balanced Banner ────────────────────────────

  Widget _buildBalancedBanner() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [SC.success, SC.success.withAlpha(200)],
          ),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Center(
          child: Column(
            children: [
              const Text('🎉', style: TextStyle(fontSize: 24)),
              const SizedBox(height: 4),
              Text('完美平衡！',
                  style: SC.headline.copyWith(color: Colors.white)),
              const SizedBox(height: 4),
              Text('放心享用你的美食吧',
                  style: SC.label.copyWith(color: Colors.white70)),
            ],
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// CUSTOM PAINTER — Scale (compact, warm style)
// ═══════════════════════════════════════════

class _ScalePainter extends CustomPainter {
  final double tilt;
  final double riskWeight;
  final double balanceWeight;
  final String? leftFood;
  final bool isBalanced;
  final double rippleProgress;

  _ScalePainter({
    required this.tilt,
    required this.riskWeight,
    required this.balanceWeight,
    this.leftFood,
    this.isBalanced = false,
    this.rippleProgress = 0,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final baseY = size.height - 12;

    // 比例自适应
    final pillarH = size.height * 0.48;
    final pivotY = baseY - pillarH;
    final beamLen = (size.width * 0.32).clamp(30.0, 120.0);

    final beamColor = isBalanced
        ? SC.success
        : tilt.abs() > 0.1
            ? (tilt > 0 ? SC.danger : SC.success)
            : const Color(0xFFB0B8C0);

    // 1. 底座
    _drawBase(canvas, cx, baseY);
    // 2. 支柱
    _drawPillar(canvas, cx, pivotY, baseY);
    // 3. 支点
    _drawPivot(canvas, cx, pivotY, beamColor);

    // 4. 横梁
    final lEnd = Offset(
        cx - beamLen * math.cos(tilt), pivotY + beamLen * math.sin(tilt));
    final rEnd = Offset(
        cx + beamLen * math.cos(tilt), pivotY - beamLen * math.sin(tilt));
    _drawBeam(canvas, lEnd, rEnd, beamColor);

    // 5. 绳索 + 托盘
    const ropeLen = 22.0;
    const panR = 18.0;
    final lPan = Offset(lEnd.dx, lEnd.dy + ropeLen);
    final rPan = Offset(rEnd.dx, rEnd.dy + ropeLen);
    _drawRope(canvas, lEnd, lPan);
    _drawRope(canvas, rEnd, rPan);
    _drawPan(canvas, lPan, panR, riskWeight > 0, SC.danger);
    _drawPan(canvas, rPan, panR, balanceWeight > 0, SC.success);

    // 6. 托盘内数字
    if (riskWeight > 0) {
      _text(canvas, lPan.dx, lPan.dy - panR * 0.5,
          riskWeight.toStringAsFixed(0), 11, SC.danger, bold: true);
    }
    if (balanceWeight > 0) {
      _text(canvas, rPan.dx, rPan.dy - panR * 0.5,
          balanceWeight.toStringAsFixed(0), 11, SC.success, bold: true);
    }

    // 7. 标签
    _text(canvas, lPan.dx, lPan.dy + panR + 2, '放纵', 9, SC.textTertiary);
    if (leftFood != null && leftFood!.isNotEmpty) {
      // Truncate long multi-food names
      final displayName = leftFood!.length > 8
          ? '${leftFood!.substring(0, 8)}...'
          : leftFood!;
      _text(canvas, lPan.dx, lPan.dy + panR + 13, displayName, 8,
          SC.textTertiary);
    }
    _text(canvas, rPan.dx, rPan.dy + panR + 2, '对冲', 9, SC.textTertiary);

    // 8. 平衡光环
    if (isBalanced && rippleProgress > 0) {
      _drawGlow(canvas, cx, pivotY, rippleProgress);
    }
  }

  void _drawBase(Canvas canvas, double cx, double baseY) {
    final basePath = Path()
      ..moveTo(cx - 32, baseY)
      ..lineTo(cx + 32, baseY)
      ..lineTo(cx + 26, baseY - 6)
      ..lineTo(cx - 26, baseY - 6)
      ..close();
    canvas.drawPath(
      basePath,
      Paint()
        ..shader = LinearGradient(
          colors: [
            const Color(0xFFD4B896),
            const Color(0xFFC09060),
            const Color(0xFFD4B896),
          ],
          stops: const [0, 0.5, 1],
        ).createShader(Rect.fromLTRB(cx - 32, baseY - 6, cx + 32, baseY)),
    );
    // 阴影
    canvas.drawLine(
      Offset(cx - 34, baseY + 2),
      Offset(cx + 34, baseY + 2),
      Paint()
        ..color = Colors.black.withAlpha(12)
        ..strokeWidth = 4
        ..strokeCap = StrokeCap.round
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4),
    );
  }

  void _drawPillar(Canvas canvas, double cx, double pivotY, double baseY) {
    final rect = RRect.fromRectAndRadius(
      Rect.fromLTRB(cx - 3, pivotY + 6, cx + 3, baseY - 6),
      const Radius.circular(2),
    );
    canvas.drawRRect(
      rect,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
          colors: [
            const Color(0xFFB8B8C8),
            const Color(0xFFD8D8E4),
            const Color(0xFFB8B8C8),
          ],
        ).createShader(rect.outerRect),
    );
  }

  void _drawPivot(Canvas canvas, double cx, double pivotY, Color beamColor) {
    canvas.drawCircle(
        Offset(cx, pivotY), 7, Paint()..color = beamColor.withAlpha(25));
    canvas.drawCircle(
      Offset(cx, pivotY),
      6,
      Paint()
        ..shader = RadialGradient(
          center: const Alignment(-0.3, -0.3),
          colors: [Colors.white, beamColor.withAlpha(200), beamColor],
          stops: const [0, 0.5, 1],
        ).createShader(Rect.fromCircle(center: Offset(cx, pivotY), radius: 6)),
    );
    canvas.drawCircle(
      Offset(cx - 1.5, pivotY - 1.5),
      2,
      Paint()..color = Colors.white.withAlpha(200),
    );
  }

  void _drawBeam(Canvas canvas, Offset lEnd, Offset rEnd, Color beamColor) {
    // 阴影
    canvas.save();
    canvas.translate(0, 3);
    canvas.drawLine(
      lEnd,
      rEnd,
      Paint()
        ..color = Colors.black.withAlpha(12)
        ..strokeWidth = 6
        ..strokeCap = StrokeCap.round
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3),
    );
    canvas.restore();
    // 梁体
    canvas.drawLine(
      lEnd,
      rEnd,
      Paint()
        ..color = beamColor
        ..strokeWidth = 4
        ..strokeCap = StrokeCap.round,
    );
    // 高光
    canvas.drawLine(
      lEnd + const Offset(0, -1),
      rEnd + const Offset(0, -1),
      Paint()
        ..color = Colors.white.withAlpha(70)
        ..strokeWidth = 1.5
        ..strokeCap = StrokeCap.round,
    );
  }

  void _drawRope(Canvas canvas, Offset beamEnd, Offset panCenter) {
    final paint = Paint()
      ..color = SC.textTertiary.withAlpha(100)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;
    final left = Path()
      ..moveTo(beamEnd.dx, beamEnd.dy)
      ..quadraticBezierTo(panCenter.dx - 18, (beamEnd.dy + panCenter.dy) / 2 + 3,
          panCenter.dx - 14, panCenter.dy - 6);
    final right = Path()
      ..moveTo(beamEnd.dx, beamEnd.dy)
      ..quadraticBezierTo(panCenter.dx + 18, (beamEnd.dy + panCenter.dy) / 2 + 3,
          panCenter.dx + 14, panCenter.dy - 6);
    canvas.drawPath(left, paint);
    canvas.drawPath(right, paint);
  }

  void _drawPan(Canvas canvas, Offset c, double r, bool active, Color ac) {
    // 碟子阴影
    canvas.drawOval(
      Rect.fromCenter(
          center: Offset(c.dx, c.dy + 3), width: r * 2.1, height: r * 0.5),
      Paint()
        ..color = Colors.black.withAlpha(8)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3),
    );
    // 碟子
    final panPath = Path()
      ..addArc(Rect.fromCircle(center: c, radius: r), 0, math.pi);
    canvas.drawPath(
      panPath,
      Paint()
        ..shader = RadialGradient(
          center: const Alignment(0, -0.5),
          colors: active
              ? [ac.withAlpha(50), ac.withAlpha(15)]
              : [SC.bg, const Color(0xFFF0ECE8)],
        ).createShader(Rect.fromCircle(center: c, radius: r)),
    );
    final stroke = Paint()
      ..color = active ? ac.withAlpha(100) : SC.textTertiary.withAlpha(60)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    canvas.drawPath(panPath, stroke);
    canvas.drawLine(Offset(c.dx - r, c.dy), Offset(c.dx + r, c.dy), stroke);
    // 碟沿高光
    canvas.drawLine(
      Offset(c.dx - r + 3, c.dy),
      Offset(c.dx + r - 3, c.dy),
      Paint()
        ..color = Colors.white.withAlpha(80)
        ..strokeWidth = 0.8
        ..strokeCap = StrokeCap.round,
    );
  }

  void _drawGlow(
      Canvas canvas, double cx, double pivotY, double progress) {
    for (int i = 0; i < 3; i++) {
      final delay = i * 0.2;
      final p = ((progress - delay) / (1 - delay)).clamp(0.0, 1.0);
      if (p <= 0) continue;
      canvas.drawCircle(
        Offset(cx, pivotY),
        10 + p * 24,
        Paint()
          ..color = SC.success.withAlpha(((1 - p) * 35).toInt().clamp(0, 255))
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.5,
      );
    }
  }

  void _text(Canvas canvas, double cx, double cy, String text, double fontSize,
      Color color,
      {bool bold = false}) {
    final tp = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(
          color: color,
          fontSize: fontSize,
          fontWeight: bold ? FontWeight.w800 : FontWeight.w600,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    tp.layout(maxWidth: 80);
    tp.paint(canvas, Offset(cx - tp.width / 2, cy));
  }

  @override
  bool shouldRepaint(covariant _ScalePainter o) =>
      o.tilt != tilt ||
      o.riskWeight != riskWeight ||
      o.balanceWeight != balanceWeight ||
      o.isBalanced != isBalanced ||
      o.leftFood != leftFood ||
      o.rippleProgress != rippleProgress;
}
