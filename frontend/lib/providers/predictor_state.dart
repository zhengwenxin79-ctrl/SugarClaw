import 'package:flutter/material.dart';
import '../models/analysis_result.dart';

class PredictorState extends ChangeNotifier {
  Map<String, double> readings = {};
  String? food;
  String? event;
  AnalysisResult? lastResult;

  void update({
    required Map<String, double> readings,
    String? food,
    String? event,
    required AnalysisResult result,
  }) {
    this.readings = readings;
    this.food = food;
    this.event = event;
    lastResult = result;
    notifyListeners();
  }

  String? buildContextSummary() {
    if (readings.isEmpty && lastResult == null) return null;

    final buf = StringBuffer();

    if (readings.isNotEmpty) {
      buf.writeln('[用户当前血糖数据]');
      for (final entry in readings.entries) {
        buf.writeln('- ${entry.key}: ${entry.value} mmol/L');
      }
      if (food != null && food!.isNotEmpty) {
        buf.writeln('- 食物: $food');
      }
      if (event != null && event!.isNotEmpty) {
        buf.writeln('- 事件: $event');
      }
    }

    if (lastResult != null) {
      final r = lastResult!;
      buf.writeln('[最新分析结果]');
      buf.writeln('- 当前血糖: ${r.currentGlucose.toStringAsFixed(1)} mmol/L, 趋势: ${r.trend}');
      if (r.alerts.isNotEmpty) {
        buf.writeln('- 警报: ${r.alerts.map((a) => a.message).join('; ')}');
      }
      if (r.advice.isNotEmpty) {
        buf.writeln('- 建议: ${r.advice}');
      }
    }

    final summary = buf.toString().trim();
    return summary.isEmpty ? null : summary;
  }
}
