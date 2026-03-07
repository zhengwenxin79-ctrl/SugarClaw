import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import '../models/analysis_result.dart';
import '../models/counterbalance.dart';

// Web 平台用 dart:html 获取当前页面 host
String _getBaseUrl() {
  if (kIsWeb) {
    // 在 Web 端自动使用当前页面的 host:port，手机/电脑都能用
    final uri = Uri.base;
    return '${uri.scheme}://${uri.host}:${uri.port}';
  }
  // 非 Web（原生 App）回退到 localhost
  return 'http://localhost:8080';
}

class ApiService {
  static final String baseUrl = _getBaseUrl();

  Future<List<CaseInfo>> getCases() async {
    final response = await http.get(Uri.parse('$baseUrl/api/cases'));
    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body);
      return data.map((e) => CaseInfo.fromJson(e)).toList();
    }
    throw Exception('Failed to load cases: ${response.statusCode}');
  }

  Future<AnalysisResult> analyze({
    required List<double> readings,
    String? event,
    String? food,
    double gi = 0,
    double gl = 0,
    double dose = 0,
  }) async {
    final body = {
      'readings': readings,
      'event': event,
      'food': food,
      'gi': gi,
      'gl': gl,
      'dose': dose,
    };
    final response = await http.post(
      Uri.parse('$baseUrl/api/analyze'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(body),
    );
    if (response.statusCode == 200) {
      return AnalysisResult.fromJson(json.decode(response.body));
    }
    throw Exception('Analysis failed: ${response.body}');
  }

  Future<AnalysisResult> replayCase(String caseId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/replay'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'case_id': caseId}),
    );
    if (response.statusCode == 200) {
      return AnalysisResult.fromJson(json.decode(response.body));
    }
    throw Exception('Replay failed: ${response.body}');
  }

  Future<RiskResult> calculateRisk(String foodName) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/scale/risk'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'food_name': foodName}),
    );
    if (response.statusCode == 200) {
      return RiskResult.fromJson(json.decode(response.body));
    }
    throw Exception('Risk calculation failed: ${response.body}');
  }

  Future<BalanceResult> findBalance(String foodName, {double riskWeight = 0}) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/scale/balance'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'food_name': foodName, 'risk_weight': riskWeight}),
    );
    if (response.statusCode == 200) {
      return BalanceResult.fromJson(json.decode(response.body));
    }
    throw Exception('Balance search failed: ${response.body}');
  }

  Future<CounterSolution> addCustomExercise(String name, int durationMin, double riskWeight) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/scale/add_exercise'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'exercise_name': name,
        'duration_min': durationMin,
        'risk_weight': riskWeight,
      }),
    );
    if (response.statusCode == 200) {
      return CounterSolution.fromJson(json.decode(response.body));
    }
    throw Exception('Add exercise failed: ${response.body}');
  }

  /// SSE 流式调用 /api/chat，逐 token 回调
  /// [onContent] 收到最终回答的增量文本
  /// [onThinking] 收到思考过程的增量文本
  /// [onDone] 流结束
  /// [onError] 出错
  Future<void> sendChat({
    required List<Map<String, String>> messages,
    required void Function(String text) onContent,
    void Function(String text)? onThinking,
    void Function()? onDone,
    void Function(String error)? onError,
  }) async {
    final request = http.Request(
      'POST',
      Uri.parse('$baseUrl/api/chat'),
    );
    request.headers['Content-Type'] = 'application/json';
    request.body = json.encode({'messages': messages});

    try {
      final response = await http.Client().send(request);
      if (response.statusCode != 200) {
        onError?.call('HTTP ${response.statusCode}');
        return;
      }

      // 解析 SSE 流
      final stream = response.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter());

      await for (final line in stream) {
        if (!line.startsWith('data: ')) continue;
        final data = json.decode(line.substring(6));
        final type = data['type'] as String;

        if (type == 'content') {
          onContent(data['content'] as String);
        } else if (type == 'thinking') {
          onThinking?.call(data['content'] as String);
        } else if (type == 'done') {
          onDone?.call();
          break;
        } else if (type == 'error') {
          onError?.call(data['message'] as String);
          break;
        }
      }
    } catch (e) {
      onError?.call(e.toString());
    }
  }

  Future<CounterSolution> addCustomFoodCounter(String name, double riskWeight) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/scale/add_food_counter'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'food_name': name,
        'risk_weight': riskWeight,
      }),
    );
    if (response.statusCode == 200) {
      return CounterSolution.fromJson(json.decode(response.body));
    }
    throw Exception('Add food counter failed: ${response.body}');
  }
}
