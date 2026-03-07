class PredictionPoint {
  final int timeOffsetMin;
  final double glucose;
  final double ciLow;
  final double ciHigh;
  final double sigma;

  PredictionPoint({
    required this.timeOffsetMin,
    required this.glucose,
    required this.ciLow,
    required this.ciHigh,
    required this.sigma,
  });

  factory PredictionPoint.fromJson(Map<String, dynamic> json) {
    return PredictionPoint(
      timeOffsetMin: json['time_offset_min'],
      glucose: (json['glucose'] as num).toDouble(),
      ciLow: (json['ci_low'] as num).toDouble(),
      ciHigh: (json['ci_high'] as num).toDouble(),
      sigma: (json['sigma'] as num).toDouble(),
    );
  }
}

class Alert {
  final String level;
  final String type;
  final String message;
  final int? timeMinutes;

  Alert({
    required this.level,
    required this.type,
    required this.message,
    this.timeMinutes,
  });

  factory Alert.fromJson(Map<String, dynamic> json) {
    return Alert(
      level: json['level'],
      type: json['type'],
      message: json['message'],
      timeMinutes: json['time_minutes'],
    );
  }
}

class AgentTrace {
  final String agent;
  final String action;
  final String result;
  final int durationMs;

  AgentTrace({
    required this.agent,
    required this.action,
    required this.result,
    required this.durationMs,
  });

  factory AgentTrace.fromJson(Map<String, dynamic> json) {
    return AgentTrace(
      agent: json['agent'],
      action: json['action'],
      result: json['result'],
      durationMs: json['duration_ms'],
    );
  }
}

class ChartData {
  final List<String> historyTimestamps;
  final List<double> rawReadings;
  final List<double> filteredReadings;
  final List<String> predictionTimestamps;
  final List<double> predictionValues;
  final List<double> ciLow;
  final List<double> ciHigh;
  final Map<String, double> zones;

  ChartData({
    required this.historyTimestamps,
    required this.rawReadings,
    required this.filteredReadings,
    required this.predictionTimestamps,
    required this.predictionValues,
    required this.ciLow,
    required this.ciHigh,
    required this.zones,
  });

  factory ChartData.fromJson(Map<String, dynamic> json) {
    final history = json['history'];
    final prediction = json['prediction'];
    final zones = json['zones'] as Map<String, dynamic>;
    return ChartData(
      historyTimestamps: List<String>.from(history['timestamps']),
      rawReadings: (history['raw'] as List).map((e) => (e as num).toDouble()).toList(),
      filteredReadings: (history['filtered'] as List).map((e) => (e as num).toDouble()).toList(),
      predictionTimestamps: List<String>.from(prediction['timestamps']),
      predictionValues: (prediction['values'] as List).map((e) => (e as num).toDouble()).toList(),
      ciLow: (prediction['ci_low'] as List).map((e) => (e as num).toDouble()).toList(),
      ciHigh: (prediction['ci_high'] as List).map((e) => (e as num).toDouble()).toList(),
      zones: zones.map((k, v) => MapEntry(k, (v as num).toDouble())),
    );
  }
}

class AnalysisResult {
  final String filterType;
  final double currentGlucose;
  final String trend;
  final List<double> filteredReadings;
  final List<PredictionPoint> predictions;
  final List<Alert> alerts;
  final ChartData chartData;
  final String advice;
  final List<AgentTrace> agentTraces;
  final String timestamp;

  AnalysisResult({
    required this.filterType,
    required this.currentGlucose,
    required this.trend,
    required this.filteredReadings,
    required this.predictions,
    required this.alerts,
    required this.chartData,
    required this.advice,
    required this.agentTraces,
    required this.timestamp,
  });

  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    return AnalysisResult(
      filterType: json['filter_type'],
      currentGlucose: (json['current_glucose'] as num).toDouble(),
      trend: json['trend'],
      filteredReadings: (json['filtered_readings'] as List).map((e) => (e as num).toDouble()).toList(),
      predictions: (json['predictions'] as List).map((e) => PredictionPoint.fromJson(e)).toList(),
      alerts: (json['alerts'] as List).map((e) => Alert.fromJson(e)).toList(),
      chartData: ChartData.fromJson(json['chart_data']),
      advice: json['advice'],
      agentTraces: (json['agent_traces'] as List).map((e) => AgentTrace.fromJson(e)).toList(),
      timestamp: json['timestamp'],
    );
  }
}

class CaseInfo {
  final String id;
  final String title;
  final String description;
  final String scenario;

  CaseInfo({
    required this.id,
    required this.title,
    required this.description,
    required this.scenario,
  });

  factory CaseInfo.fromJson(Map<String, dynamic> json) {
    return CaseInfo(
      id: json['id'],
      title: json['title'],
      description: json['description'],
      scenario: json['scenario'],
    );
  }
}
