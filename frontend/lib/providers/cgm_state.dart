import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../models/cgm_reading.dart';
import '../services/api_service.dart';

class CGMState extends ChangeNotifier {
  final ApiService _api = ApiService();

  List<CgmReading> _readings = [];
  List<CgmSession> _sessions = [];
  String? _currentSessionId;
  bool _loading = false;
  bool _streaming = false;
  String? _error;

  List<CgmReading> get readings => _readings;
  List<CgmSession> get sessions => _sessions;
  String? get currentSessionId => _currentSessionId;
  bool get loading => _loading;
  bool get streaming => _streaming;
  String? get error => _error;

  // 统计摘要
  double get meanGlucose {
    if (_readings.isEmpty) return 0;
    return _readings.map((r) => r.glucoseMmol).reduce((a, b) => a + b) / _readings.length;
  }

  double get minGlucose {
    if (_readings.isEmpty) return 0;
    return _readings.map((r) => r.glucoseMmol).reduce((a, b) => a < b ? a : b);
  }

  double get maxGlucose {
    if (_readings.isEmpty) return 0;
    return _readings.map((r) => r.glucoseMmol).reduce((a, b) => a > b ? a : b);
  }

  double get timeInRange {
    if (_readings.isEmpty) return 0;
    final inRange = _readings.where((r) => r.glucoseMmol >= 3.9 && r.glucoseMmol <= 10.0).length;
    return inRange / _readings.length * 100;
  }

  Future<void> simulate({int? seed}) async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      final result = await _api.cgmSimulate(seed: seed);
      _currentSessionId = result['session_id'] as String;
      final readingsList = result['readings'] as List<dynamic>;
      _readings = readingsList.map((r) => CgmReading.fromJson(r)).toList();
      await loadSessions();
    } catch (e) {
      _error = e.toString();
    }
    _loading = false;
    notifyListeners();
  }

  Future<void> startStream(String sessionId) async {
    _streaming = true;
    _readings = [];
    _currentSessionId = sessionId;
    _error = null;
    notifyListeners();

    try {
      final request = http.Request(
        'GET',
        Uri.parse('${ApiService.baseUrl}/api/cgm/stream/$sessionId'),
      );
      final response = await http.Client().send(request);
      final stream = response.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter());

      await for (final line in stream) {
        if (!line.startsWith('data: ')) continue;
        final data = json.decode(line.substring(6));
        if (data['type'] == 'reading') {
          _readings.add(CgmReading(
            timestamp: data['timestamp'] ?? '',
            glucoseMmol: (data['glucose_mmol'] ?? 0).toDouble(),
            glucoseMgdl: (data['glucose_mgdl'] ?? 0).toDouble(),
            event: data['event'] ?? '',
          ));
          notifyListeners();
        } else if (data['type'] == 'done') {
          break;
        }
      }
    } catch (e) {
      _error = e.toString();
    }
    _streaming = false;
    notifyListeners();
  }

  Future<void> loadSessions() async {
    try {
      _sessions = await _api.cgmSessions();
    } catch (e) {
      _error = e.toString();
    }
    notifyListeners();
  }

  Future<void> loadHistory({int limit = 100}) async {
    try {
      final history = await _api.cgmHistory(limit: limit);
      _readings = history;
    } catch (e) {
      _error = e.toString();
    }
    notifyListeners();
  }
}
