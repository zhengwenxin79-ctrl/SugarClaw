import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/counterbalance.dart';
import '../providers/scale_state.dart';
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
  }

  @override
  void dispose() {
    _tiltController.dispose();
    super.dispose();
  }

  void _animateTilt(double target) {
    if ((target - _prevTilt).abs() < 0.001) return;
    _tiltAnimation = Tween<double>(
      begin: _tiltAnimation.value,
      end: target,
    ).animate(
      CurvedAnimation(parent: _tiltController, curve: Curves.elasticOut),
    );
    _tiltController.forward(from: 0);
    _prevTilt = target;
  }

  void _showAddFoodDialog(ScaleState state) {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Add Food',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: InputDecoration(
            hintText: 'Enter food name...',
            filled: true,
            fillColor: const Color(0xFFF7FAFC),
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
            child: Text('Cancel',
                style: TextStyle(color: Colors.grey.shade500)),
          ),
          ElevatedButton(
            onPressed: () {
              if (controller.text.trim().isNotEmpty) {
                state.addCustomFood(controller.text.trim());
                Navigator.of(ctx).pop();
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFED8936),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10)),
              elevation: 0,
            ),
            child: const Text('Add & Analyze'),
          ),
        ],
      ),
    );
  }

  void _showAddExerciseDialog(ScaleState state) {
    final nameController = TextEditingController();
    final durationController = TextEditingController(text: '20');
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('添加自定义运动',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              autofocus: true,
              decoration: InputDecoration(
                hintText: '运动名称（如瑜伽、跳绳）',
                filled: true,
                fillColor: const Color(0xFFF7FAFC),
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
              decoration: InputDecoration(
                hintText: '时长（分钟）',
                filled: true,
                fillColor: const Color(0xFFF7FAFC),
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
            child: Text('取消', style: TextStyle(color: Colors.grey.shade500)),
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
              backgroundColor: const Color(0xFF4299E1),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10)),
              elevation: 0,
            ),
            child: const Text('添加'),
          ),
        ],
      ),
    );
  }

  void _showAddFoodCounterDialog(ScaleState state) {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('添加对冲食物',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: InputDecoration(
            hintText: '食物名称（如豆腐、西兰花）',
            filled: true,
            fillColor: const Color(0xFFF7FAFC),
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
            child: Text('取消', style: TextStyle(color: Colors.grey.shade500)),
          ),
          ElevatedButton(
            onPressed: () {
              if (controller.text.trim().isNotEmpty) {
                state.addCustomFoodCounter(controller.text.trim());
                Navigator.of(ctx).pop();
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF48BB78),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10)),
              elevation: 0,
            ),
            child: const Text('添加'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: SafeArea(
        child: Consumer<ScaleState>(
          builder: (context, state, _) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              _animateTilt(state.tiltAngle);
            });

            return Column(
              children: [
                _buildHeader(),
                Expanded(
                  child: SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // ── Left Pan: Food card library ──
                        _buildSectionTitle(
                          'Indulgence',
                          Icons.restaurant_rounded,
                          const Color(0xFFE53E3E),
                          'Choose what you ate',
                        ),
                        _buildFoodCardRow(state),
                        // ── The Scale ──
                        _buildScale(state),
                        // ── Risk info ──
                        if (state.riskResult != null) _buildRiskBadge(state),
                        // ── Loading ──
                        if (state.loadingRisk || state.loadingBalance)
                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 16),
                            child: Center(
                              child: CircularProgressIndicator(
                                  color: Color(0xFFED8936), strokeWidth: 3),
                            ),
                          ),
                        // ── Error ──
                        if (state.error != null)
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 20),
                            child: Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: Colors.red.shade50,
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Text(state.error!,
                                  style: TextStyle(
                                      color: Colors.red.shade700,
                                      fontSize: 12)),
                            ),
                          ),
                        // ── Right Pan: Draggable solutions ──
                        if (state.balanceResult != null) ...[
                          _buildSectionTitle(
                            'Balance',
                            Icons.auto_fix_high_rounded,
                            const Color(0xFF48BB78),
                            'Drag cards onto the right pan',
                          ),
                          _buildSolutionCards(state),
                          if (state.isBalanced) _buildBalancedBanner(),
                          Padding(
                            padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
                            child: AdviceBubble(
                                advice: state.balanceResult!.advice),
                          ),
                        ],
                        const SizedBox(height: 30),
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
      child: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFFED8936), Color(0xFFDD6B20)],
              ),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.balance_rounded,
                color: Colors.white, size: 20),
          ),
          const SizedBox(width: 10),
          const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Counterbalance Scale',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF1A202C),
                  letterSpacing: -0.5,
                ),
              ),
              Text(
                'Pick food on left, drag solutions to right',
                style: TextStyle(fontSize: 10, color: Colors.grey),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSectionTitle(
      String title, IconData icon, Color color, String subtitle) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 6),
      child: Row(
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 6),
          Text(
            title,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              subtitle,
              style: TextStyle(fontSize: 11, color: Colors.grey.shade400),
            ),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════
  // LEFT PAN: Horizontal scrollable food cards
  // ═══════════════════════════════════════════
  Widget _buildFoodCardRow(ScaleState state) {
    return SizedBox(
      height: 80,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: state.foodLibrary.length + 1, // +1 for the "+" card
        itemBuilder: (context, i) {
          // Last card is the "+" add button
          if (i == state.foodLibrary.length) {
            return _buildAddFoodCard(state);
          }
          final name = state.foodLibrary[i];
          final isActive = state.selectedFood == name;
          return _buildFoodCard(name, isActive, state);
        },
      ),
    );
  }

  Widget _buildFoodCard(String name, bool isActive, ScaleState state) {
    return Padding(
      padding: const EdgeInsets.only(right: 10),
      child: GestureDetector(
        onTap: () => state.selectFood(name),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 250),
          width: 76,
          decoration: BoxDecoration(
            color: isActive ? const Color(0xFFE53E3E) : Colors.white,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: isActive
                  ? const Color(0xFFE53E3E)
                  : Colors.grey.shade200,
              width: isActive ? 2 : 1,
            ),
            boxShadow: isActive
                ? [
                    BoxShadow(
                      color: const Color(0xFFE53E3E).withAlpha(40),
                      blurRadius: 8,
                      offset: const Offset(0, 3),
                    )
                  ]
                : [],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.restaurant_rounded,
                size: 22,
                color: isActive ? Colors.white : const Color(0xFFED8936),
              ),
              const SizedBox(height: 6),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: Text(
                  name,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: isActive ? Colors.white : const Color(0xFF4A5568),
                  ),
                  maxLines: 2,
                  textAlign: TextAlign.center,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAddFoodCard(ScaleState state) {
    return Padding(
      padding: const EdgeInsets.only(right: 10),
      child: GestureDetector(
        onTap: () => _showAddFoodDialog(state),
        child: Container(
          width: 76,
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: Colors.grey.shade300,
              style: BorderStyle.solid,
              width: 1.5,
            ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.add_rounded, size: 28, color: Colors.grey.shade400),
              const SizedBox(height: 4),
              Text(
                'Search',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: Colors.grey.shade400,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════
  // THE SCALE (with DragTarget on right pan)
  // ═══════════════════════════════════════════
  Widget _buildScale(ScaleState state) {
    return AnimatedBuilder(
      animation: _tiltAnimation,
      builder: (context, _) {
        final tilt = _tiltAnimation.value;
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
          child: SizedBox(
            height: 210,
            child: Stack(
              children: [
                CustomPaint(
                  painter: _ScalePainter(
                    tilt: tilt,
                    riskWeight: state.riskWeight,
                    balanceWeight: state.balanceWeight,
                    leftFood: state.riskResult?.food.name,
                    isBalanced: state.isBalanced,
                  ),
                  size: Size.infinite,
                ),
                // DragTarget on right pan area
                if (state.balanceResult != null)
                  Positioned(
                    right: 0,
                    top: 20,
                    width: MediaQuery.of(context).size.width * 0.38,
                    height: 160,
                    child: DragTarget<int>(
                      onAcceptWithDetails: (d) => state.dropSolution(d.data),
                      builder: (context, candidates, _) {
                        final hovering = candidates.isNotEmpty;
                        return AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          decoration: BoxDecoration(
                            color: hovering
                                ? const Color(0xFF48BB78).withAlpha(25)
                                : Colors.transparent,
                            borderRadius: BorderRadius.circular(20),
                            border: hovering
                                ? Border.all(
                                    color: const Color(0xFF48BB78).withAlpha(100),
                                    width: 2)
                                : null,
                          ),
                          child: hovering
                              ? const Center(
                                  child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.add_circle_outline_rounded,
                                          color: Color(0xFF48BB78), size: 32),
                                      SizedBox(height: 4),
                                      Text('Drop here',
                                          style: TextStyle(
                                            color: Color(0xFF48BB78),
                                            fontSize: 11,
                                            fontWeight: FontWeight.w700,
                                          )),
                                    ],
                                  ),
                                )
                              : const SizedBox(),
                        );
                      },
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  // ═══════════════════════════════════════════
  // RISK BADGE under the scale
  // ═══════════════════════════════════════════
  Widget _buildRiskBadge(ScaleState state) {
    final r = state.riskResult!;
    Color lc;
    switch (r.riskLevel) {
      case 'low':
        lc = const Color(0xFF48BB78);
        break;
      case 'medium':
        lc = const Color(0xFFED8936);
        break;
      case 'high':
        lc = const Color(0xFFE53E3E);
        break;
      default:
        lc = const Color(0xFF9B2C2C);
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 2, 20, 0),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: lc.withAlpha(50)),
        ),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: lc.withAlpha(25),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Center(
                child: Text(
                  r.riskWeight.toStringAsFixed(0),
                  style: TextStyle(
                      color: lc, fontSize: 16, fontWeight: FontWeight.w800),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Text(r.food.name,
                        style: const TextStyle(
                            fontWeight: FontWeight.w700, fontSize: 13)),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 5, vertical: 1),
                      decoration: BoxDecoration(
                        color: lc.withAlpha(20),
                        borderRadius: BorderRadius.circular(5),
                      ),
                      child: Text(r.riskLevel.toUpperCase(),
                          style: TextStyle(
                              color: lc,
                              fontSize: 9,
                              fontWeight: FontWeight.w700)),
                    ),
                  ]),
                  const SizedBox(height: 2),
                  Text(r.riskDetail,
                      style: TextStyle(
                          fontSize: 10, color: Colors.grey.shade500),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════
  // RIGHT PAN: Draggable solution mini-cards
  // ═══════════════════════════════════════════
  Widget _buildSolutionCards(ScaleState state) {
    final solutions = state.balanceResult!.solutions;

    // Group solutions by their group field, preserving order of first appearance
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

    // Group display config
    const groupIcons = <String, IconData>{
      '蔬菜搭配': Icons.eco_rounded,
      '蛋白搭配': Icons.egg_rounded,
      '主食替换': Icons.rice_bowl_rounded,
      '汤饮搭配': Icons.local_cafe_rounded,
      '烹饪技巧': Icons.auto_fix_high_rounded,
      '轻度运动': Icons.directions_walk_rounded,
      '中度运动': Icons.directions_bike_rounded,
      '高强度运动': Icons.directions_run_rounded,
    };
    const groupColors = <String, Color>{
      '蔬菜搭配': Color(0xFF48BB78),
      '蛋白搭配': Color(0xFFED8936),
      '主食替换': Color(0xFF9F7AEA),
      '汤饮搭配': Color(0xFF4299E1),
      '烹饪技巧': Color(0xFF718096),
      '轻度运动': Color(0xFF48BB78),
      '中度运动': Color(0xFF4299E1),
      '高强度运动': Color(0xFFE53E3E),
    };

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildProgressBar(state),
          const SizedBox(height: 8),
          for (final group in groupOrder) ...[
            const SizedBox(height: 6),
            _groupHeader(
              group,
              groupIcons[group] ?? Icons.category_rounded,
              groupColors[group] ?? const Color(0xFF718096),
              group == '烹饪技巧' ? '固定展示' : '选一项',
            ),
            const SizedBox(height: 6),
            SizedBox(
              height: 44,
              child: Builder(builder: (context) {
                final isExerciseGroup = group == '轻度运动' || group == '中度运动' || group == '高强度运动';
                final isFoodGroup = group == '蔬菜搭配' || group == '蛋白搭配' || group == '主食替换' || group == '汤饮搭配';
                final hasAddButton = isExerciseGroup || isFoodGroup;
                // 反转卡片顺序：最新添加的排在前面（靠近搜索按钮）
                final indices = groupIndices[group]!.reversed.toList();
                final itemCount = indices.length + (hasAddButton ? 1 : 0);
                return ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: itemCount,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (context, j) {
                    // 搜索/添加按钮始终排第一个
                    if (j == 0 && hasAddButton) {
                      return _buildAddSolutionChip(
                        state,
                        isExercise: isExerciseGroup,
                        color: isExerciseGroup
                            ? const Color(0xFF4299E1)
                            : const Color(0xFF48BB78),
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

  Widget _groupHeader(String label, IconData icon, Color color, String hint) {
    return Row(
      children: [
        Icon(icon, size: 13, color: color),
        const SizedBox(width: 4),
        Text(label,
            style: TextStyle(
                fontSize: 12, fontWeight: FontWeight.w700, color: color)),
        const SizedBox(width: 6),
        Text(hint,
            style: TextStyle(fontSize: 10, color: Colors.grey.shade400)),
      ],
    );
  }

  Widget _buildProgressBar(ScaleState state) {
    final progress = state.riskWeight > 0
        ? (state.balanceWeight / state.riskWeight).clamp(0.0, 1.0)
        : 0.0;
    return Row(
      children: [
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 8,
              backgroundColor: Colors.grey.shade200,
              valueColor: AlwaysStoppedAnimation<Color>(
                state.isBalanced
                    ? const Color(0xFF48BB78)
                    : const Color(0xFFED8936),
              ),
            ),
          ),
        ),
        const SizedBox(width: 10),
        Text(
          '${state.balanceWeight.toStringAsFixed(0)} / ${state.riskWeight.toStringAsFixed(0)}',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: state.isBalanced
                ? const Color(0xFF48BB78)
                : Colors.grey.shade600,
          ),
        ),
      ],
    );
  }

  Widget _miniSectionLabel(String label, IconData icon, Color color) {
    return Row(
      children: [
        Icon(icon, size: 13, color: color),
        const SizedBox(width: 4),
        Text(label,
            style: TextStyle(
                fontSize: 11, fontWeight: FontWeight.w700, color: color)),
      ],
    );
  }

  Widget _draggableMiniCard(
      ScaleState state, int index, CounterSolution s) {
    final selected = state.selectedIndices.contains(index);
    Color ac;
    IconData ic;
    switch (s.type) {
      case 'exercise':
        ac = const Color(0xFF4299E1);
        ic = Icons.directions_run_rounded;
        break;
      default:
        ac = const Color(0xFF48BB78);
        ic = Icons.eco_rounded;
    }

    final chip = AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: selected ? ac.withAlpha(20) : Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: selected ? ac : Colors.grey.shade200,
          width: selected ? 2 : 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(ic, size: 14, color: ac),
          const SizedBox(width: 6),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 100),
            child: Text(
              s.name,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: selected ? ac : Colors.grey.shade700,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
            decoration: BoxDecoration(
              color: selected ? ac : Colors.grey.shade100,
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              '+${s.balanceWeight.toStringAsFixed(0)}',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: selected ? Colors.white : Colors.grey.shade600,
              ),
            ),
          ),
          if (selected)
            const Padding(
              padding: EdgeInsets.only(left: 4),
              child: Icon(Icons.check_circle, size: 14, color: Color(0xFF48BB78)),
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
        onTap: () => state.toggleSolution(index),
        child: chip,
      ),
    );
  }

  Widget _buildAddSolutionChip(ScaleState state,
      {required bool isExercise, required Color color}) {
    return GestureDetector(
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
          color: color.withAlpha(25),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withAlpha(150), width: 1.5),
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
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBalancedBanner() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFF48BB78), Color(0xFF38A169)],
          ),
          borderRadius: BorderRadius.circular(14),
        ),
        child: const Center(
          child: Column(
            children: [
              Icon(Icons.celebration_rounded, color: Colors.white, size: 26),
              SizedBox(height: 4),
              Text('Perfectly Balanced!',
                  style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                      fontSize: 17)),
              SizedBox(height: 2),
              Text('Enjoy your meal with confidence',
                  style: TextStyle(color: Colors.white70, fontSize: 12)),
            ],
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// CUSTOM PAINTER — The Scale
// ═══════════════════════════════════════════

class _ScalePainter extends CustomPainter {
  final double tilt;
  final double riskWeight;
  final double balanceWeight;
  final String? leftFood;
  final bool isBalanced;

  _ScalePainter({
    required this.tilt,
    required this.riskWeight,
    required this.balanceWeight,
    this.leftFood,
    this.isBalanced = false,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final baseY = size.height - 26;
    final pivotY = size.height * 0.32;
    final beamLen = size.width * 0.38;

    final beamColor = isBalanced
        ? const Color(0xFF48BB78)
        : tilt > 0.15
            ? const Color(0xFFE53E3E)
            : tilt < -0.15
                ? const Color(0xFF4299E1)
                : const Color(0xFF718096);

    // Base triangle
    final tri = Path()
      ..moveTo(cx, pivotY)
      ..lineTo(cx - 13, baseY)
      ..lineTo(cx + 13, baseY)
      ..close();
    canvas.drawPath(tri, Paint()..color = const Color(0xFFE2E8F0));

    // Base line
    canvas.drawLine(
      Offset(cx - 36, baseY),
      Offset(cx + 36, baseY),
      Paint()
        ..color = const Color(0xFFCBD5E0)
        ..strokeWidth = 3
        ..strokeCap = StrokeCap.round,
    );

    // Beam
    final lEnd = Offset(
      cx - beamLen * math.cos(tilt),
      pivotY + beamLen * math.sin(tilt),
    );
    final rEnd = Offset(
      cx + beamLen * math.cos(tilt),
      pivotY - beamLen * math.sin(tilt),
    );
    canvas.drawLine(
      lEnd,
      rEnd,
      Paint()
        ..color = beamColor
        ..strokeWidth = 4
        ..strokeCap = StrokeCap.round,
    );

    // Pivot
    canvas.drawCircle(Offset(cx, pivotY), 6, Paint()..color = beamColor);
    canvas.drawCircle(Offset(cx, pivotY), 3, Paint()..color = Colors.white);

    // Strings
    final sp = Paint()
      ..color = const Color(0xFFCBD5E0)
      ..strokeWidth = 1.5;
    final lPan = Offset(lEnd.dx, lEnd.dy + 46);
    final rPan = Offset(rEnd.dx, rEnd.dy + 46);
    canvas.drawLine(lEnd, lPan + const Offset(-18, -7), sp);
    canvas.drawLine(lEnd, lPan + const Offset(18, -7), sp);
    canvas.drawLine(rEnd, rPan + const Offset(-18, -7), sp);
    canvas.drawLine(rEnd, rPan + const Offset(18, -7), sp);

    // Pans
    _drawPan(canvas, lPan, 38, riskWeight > 0, const Color(0xFFE53E3E));
    _drawPan(canvas, rPan, 38, balanceWeight > 0, const Color(0xFF48BB78));

    // Labels
    _text(canvas, lPan.dx, lPan.dy + 18, 'Indulgence', 10,
        const Color(0xFF718096));
    _text(
        canvas, rPan.dx, rPan.dy + 18, 'Balance', 10, const Color(0xFF718096));

    // Weight numbers
    if (riskWeight > 0) {
      _text(canvas, lPan.dx, lPan.dy - 4, riskWeight.toStringAsFixed(0), 16,
          const Color(0xFFE53E3E),
          bold: true);
    }
    if (balanceWeight > 0) {
      _text(canvas, rPan.dx, rPan.dy - 4, balanceWeight.toStringAsFixed(0), 16,
          const Color(0xFF48BB78),
          bold: true);
    }

    // Food name
    if (leftFood != null && leftFood!.isNotEmpty) {
      _text(canvas, lPan.dx, lPan.dy + 30, leftFood!, 9,
          const Color(0xFF718096));
    }
  }

  void _drawPan(Canvas canvas, Offset c, double r, bool active, Color ac) {
    final fill = Paint()
      ..color = active ? ac.withAlpha(30) : const Color(0xFFF7FAFC)
      ..style = PaintingStyle.fill;
    final stroke = Paint()
      ..color = active ? ac.withAlpha(120) : const Color(0xFFCBD5E0)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    final path = Path()..addArc(Rect.fromCircle(center: c, radius: r), 0, math.pi);
    canvas.drawPath(path, fill);
    canvas.drawPath(path, stroke);
    canvas.drawLine(Offset(c.dx - r, c.dy), Offset(c.dx + r, c.dy), stroke);
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
    tp.layout(maxWidth: 90);
    tp.paint(canvas, Offset(cx - tp.width / 2, cy));
  }

  @override
  bool shouldRepaint(covariant _ScalePainter o) =>
      o.tilt != tilt ||
      o.riskWeight != riskWeight ||
      o.balanceWeight != balanceWeight ||
      o.isBalanced != isBalanced ||
      o.leftFood != leftFood;
}
