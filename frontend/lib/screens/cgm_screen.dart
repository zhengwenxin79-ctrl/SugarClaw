import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:provider/provider.dart';
import '../providers/cgm_state.dart';
import '../theme.dart';

class CGMScreen extends StatelessWidget {
  const CGMScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<CGMState>(
      builder: (context, state, _) {
        return Scaffold(
          backgroundColor: SC.bg,
          body: SafeArea(
            child: Column(
              children: [
                _buildHeader(context, state),
                Expanded(
                  child: state.readings.isEmpty
                      ? _buildEmptyState(context, state)
                      : _buildContent(context, state),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildHeader(BuildContext context, CGMState state) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: SC.surface,
        boxShadow: SC.shadowSm,
      ),
      child: Row(
        children: [
          const Icon(Icons.monitor_heart, color: SC.info, size: 28),
          const SizedBox(width: 8),
          Text('CGM Monitor', style: SC.headline),
          const Spacer(),
          if (state.loading || state.streaming)
            const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: SC.info)),
          const SizedBox(width: 8),
          ElevatedButton.icon(
            icon: const Icon(Icons.play_arrow, size: 18),
            label: Text('模拟', style: SC.label.copyWith(color: Colors.white)),
            style: ElevatedButton.styleFrom(
              backgroundColor: SC.info,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            ),
            onPressed: state.loading ? null : () => state.simulate(),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, CGMState state) {
    return Column(
      children: [
        Expanded(
          child: SC.emptyState(
            Icons.monitor_heart_outlined,
            '尚无 CGM 数据',
            subtitle: '点击"模拟"生成 24 小时模拟数据',
            ctaLabel: '开始模拟',
            onCta: state.loading ? null : () => state.simulate(),
          ),
        ),
        if (state.error != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 8),
            child: Text(state.error!, style: SC.body.copyWith(color: SC.danger, fontSize: 13)),
          ),
      ],
    );
  }

  Widget _buildContent(BuildContext context, CGMState state) {
    return SingleChildScrollView(
      padding: SC.cardPadding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildStatsSummary(state),
          SC.sectionSpacing,
          _buildChart(state),
          SC.sectionSpacing,
          _buildEventsList(state),
          SC.sectionSpacing,
          _buildSessionsList(state),
        ],
      ),
    );
  }

  Widget _buildStatsSummary(CGMState state) {
    return Container(
      padding: SC.cardPadding,
      decoration: SC.card,
      child: Row(
        children: [
          _statCard('平均', state.meanGlucose.toStringAsFixed(1), 'mmol/L', SC.info),
          _statCard('最低', state.minGlucose.toStringAsFixed(1), 'mmol/L', SC.glucoseTarget),
          _statCard('最高', state.maxGlucose.toStringAsFixed(1), 'mmol/L', SC.glucoseHypo),
          _statCard('TIR', '${state.timeInRange.toStringAsFixed(0)}%', '3.9-10', SC.success),
        ],
      ),
    );
  }

  Widget _statCard(String label, String value, String unit, Color color) {
    return Expanded(
      child: Column(
        children: [
          Text(label, style: SC.label),
          const SizedBox(height: 4),
          Text(value, style: SC.headline.copyWith(fontSize: 20, color: color)),
          Text(unit, style: SC.caption),
        ],
      ),
    );
  }

  Widget _buildChart(CGMState state) {
    final readings = state.readings;
    if (readings.isEmpty) return const SizedBox.shrink();

    final step = (readings.length / 144).ceil().clamp(1, 10);
    final sampled = <FlSpot>[];
    for (int i = 0; i < readings.length; i += step) {
      sampled.add(FlSpot(i.toDouble(), readings[i].glucoseMmol));
    }

    final minY = (state.minGlucose - 1).clamp(0.0, 20.0);
    final maxY = (state.maxGlucose + 1).clamp(5.0, 25.0);

    return Container(
      height: 250,
      padding: const EdgeInsets.all(12),
      decoration: SC.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('血糖趋势', style: SC.body.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Expanded(
            child: LineChart(
              LineChartData(
                minY: minY,
                maxY: maxY,
                gridData: FlGridData(
                  show: true,
                  horizontalInterval: 2,
                  getDrawingHorizontalLine: (value) {
                    if (value == 3.9 || value == 10.0) {
                      return FlLine(color: SC.warning.withAlpha(128), strokeWidth: 1, dashArray: [5, 5]);
                    }
                    return FlLine(color: SC.border.withAlpha(51), strokeWidth: 0.5);
                  },
                ),
                titlesData: FlTitlesData(
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 35,
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
                lineBarsData: [
                  LineChartBarData(
                    spots: sampled,
                    isCurved: true,
                    color: SC.info,
                    barWidth: 2,
                    dotData: const FlDotData(show: false),
                    belowBarData: BarAreaData(
                      show: true,
                      color: SC.info.withAlpha(38),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEventsList(CGMState state) {
    final events = state.readings.where((r) => r.event.isNotEmpty).toList();
    if (events.isEmpty) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: SC.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('事件标记', style: SC.body.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          ...events.map((e) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    Icon(
                      e.event.contains('meal')
                          ? Icons.restaurant
                          : e.event.contains('insulin')
                              ? Icons.medication
                              : Icons.event,
                      size: 16,
                      color: e.event.contains('meal') ? SC.accent : SC.info,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      e.timestamp.length >= 16 ? e.timestamp.substring(11, 16) : e.timestamp,
                      style: SC.label.copyWith(fontWeight: FontWeight.w500),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(e.event, style: SC.label.copyWith(color: SC.textSecondary)),
                    ),
                    Text(
                      '${e.glucoseMmol.toStringAsFixed(1)} mmol/L',
                      style: SC.label.copyWith(fontWeight: FontWeight.bold, color: SC.textPrimary),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  Widget _buildSessionsList(CGMState state) {
    if (state.sessions.isEmpty) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: SC.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('历史会话', style: SC.body.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          ...state.sessions.take(5).map((s) => ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.history, size: 20, color: SC.info),
                title: Text(s.sessionId, style: SC.label),
                subtitle: Text('${s.readingCount} 条读数', style: SC.caption),
                trailing: IconButton(
                  icon: const Icon(Icons.play_circle_outline, size: 20, color: SC.info),
                  onPressed: state.streaming ? null : () => state.startStream(s.sessionId),
                ),
              )),
        ],
      ),
    );
  }
}
