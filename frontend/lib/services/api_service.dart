import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import '../models/analysis_result.dart';
import '../models/counterbalance.dart';
import '../models/user_profile.dart';
import '../models/cgm_reading.dart';
import '../models/pubmed_article.dart';

// Web 平台根据当前页面 URL 自动推断后端地址
String _getBaseUrl() {
  if (kIsWeb) {
    final uri = Uri.base;
    // flutter dev 模式（8080）→ 后端在 8082
    if (uri.port == 8080) {
      return '${uri.scheme}://${uri.host}:8082';
    }
    // 生产部署 / 公网隧道 → 前后端同域同端口（后端 mount 了静态文件）
    return uri.origin;
  }
  return 'http://localhost:8082';
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

  Future<RiskResult> calculateRisk(
    String foodName, {
    String? queryTime,
    double quantityMultiplier = 1.0,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/scale/risk'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'food_name': foodName,
        'query_time': queryTime ?? DateTime.now().toIso8601String(),
        'quantity_multiplier': quantityMultiplier,
      }),
    );
    if (response.statusCode == 200) {
      return RiskResult.fromJson(json.decode(response.body));
    }
    throw Exception('Risk calculation failed: ${response.body}');
  }

  Future<BalanceResult> findBalance(String foodName, {double riskWeight = 0, String? queryTime}) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/scale/balance'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'food_name': foodName,
        'risk_weight': riskWeight,
        'query_time': queryTime ?? DateTime.now().toIso8601String(),
      }),
    );
    if (response.statusCode == 200) {
      return BalanceResult.fromJson(json.decode(response.body));
    }
    throw Exception('Balance search failed: ${response.body}');
  }

  Future<Map<String, String>> refreshAdvice({
    required String foodName,
    required double riskWeight,
    required List<int> selectedIndices,
    required List<CounterSolution> allSolutions,
    String? queryTime,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/scale/advice'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'food_name': foodName,
        'risk_weight': riskWeight,
        'selected_indices': selectedIndices,
        'all_solutions': allSolutions.map((s) {
          return {
            'type': s.type,
            'name': s.name,
            'description': s.description,
            'balance_weight': s.balanceWeight,
            'group': s.group,
            'details': s.details,
          };
        }).toList(),
        'query_time': queryTime ?? DateTime.now().toIso8601String(),
      }),
    );
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return {
        'advice': data['advice'] as String,
        'meal_context': (data['meal_context'] ?? '') as String,
        'time_advice': (data['time_advice'] ?? '') as String,
      };
    }
    throw Exception('Refresh advice failed: ${response.body}');
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

  // ─── 用户档案 ──────────────────────────────

  Future<Map<String, dynamic>> getOnboardingStatus() async {
    final response = await http.get(Uri.parse('$baseUrl/api/user/onboarding_status'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception('Failed to load onboarding status: ${response.statusCode}');
  }

  Future<UserProfile> getUserProfile() async {
    final response = await http.get(Uri.parse('$baseUrl/api/user/profile'));
    if (response.statusCode == 200) {
      return UserProfile.fromJson(json.decode(response.body));
    }
    throw Exception('Failed to load profile: ${response.statusCode}');
  }

  Future<UserProfile> updateUserProfile(Map<String, dynamic> fields) async {
    final response = await http.put(
      Uri.parse('$baseUrl/api/user/profile'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(fields),
    );
    if (response.statusCode == 200) {
      return UserProfile.fromJson(json.decode(response.body));
    }
    throw Exception('Failed to update profile: ${response.body}');
  }

  // ─── 血糖日志 ──────────────────────────────

  Future<Map<String, dynamic>> addGlucoseLog({
    required String timestamp,
    required double glucoseMmol,
    String note = '',
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/glucose/log'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'timestamp': timestamp,
        'glucose_mmol': glucoseMmol,
        'note': note,
      }),
    );
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception('Failed to add glucose log: ${response.body}');
  }

  Future<List<Map<String, dynamic>>> getGlucoseLog({int limit = 100}) async {
    final response = await http.get(Uri.parse('$baseUrl/api/glucose/log?limit=$limit'));
    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body);
      return data.map((e) => Map<String, dynamic>.from(e)).toList();
    }
    throw Exception('Failed to load glucose log: ${response.statusCode}');
  }

  Future<void> deleteGlucoseLog(int entryId) async {
    final response = await http.delete(Uri.parse('$baseUrl/api/glucose/log/$entryId'));
    if (response.statusCode != 200) {
      throw Exception('Failed to delete glucose log: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> calibrateISF({
    required double before,
    required double after,
    required double dose,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/user/calibrate_isf'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'before': before, 'after': after, 'dose': dose}),
    );
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception('ISF calibration failed: ${response.body}');
  }

  // ─── CGM 模拟 ──────────────────────────────

  Future<Map<String, dynamic>> cgmSimulate({int? seed}) async {
    final body = <String, dynamic>{};
    if (seed != null) body['seed'] = seed;
    final response = await http.post(
      Uri.parse('$baseUrl/api/cgm/simulate'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(body),
    );
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception('CGM simulation failed: ${response.body}');
  }

  Future<List<CgmReading>> cgmHistory({int limit = 100}) async {
    final response = await http.get(Uri.parse('$baseUrl/api/cgm/history?limit=$limit'));
    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body);
      return data.map((e) => CgmReading.fromJson(e)).toList();
    }
    throw Exception('Failed to load CGM history: ${response.statusCode}');
  }

  Future<List<CgmSession>> cgmSessions() async {
    final response = await http.get(Uri.parse('$baseUrl/api/cgm/sessions'));
    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body);
      return data.map((e) => CgmSession.fromJson(e)).toList();
    }
    throw Exception('Failed to load CGM sessions: ${response.statusCode}');
  }

  // ─── PubMed 文献检索 ──────────────────────────────

  Future<PubMedSearchResult> pubmedSearch({
    required String query,
    String mode = 'custom',
    int maxResults = 5,
    bool includeAbstracts = false,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/pubmed/search'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'query': query,
        'mode': mode,
        'max_results': maxResults,
        'include_abstracts': includeAbstracts,
      }),
    );
    if (response.statusCode == 200) {
      return PubMedSearchResult.fromJson(json.decode(response.body));
    }
    throw Exception('PubMed search failed: ${response.body}');
  }

  Future<List<Map<String, dynamic>>> pubmedHistory({int limit = 20}) async {
    final response = await http.get(Uri.parse('$baseUrl/api/pubmed/history?limit=$limit'));
    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body);
      return data.map((e) => Map<String, dynamic>.from(e)).toList();
    }
    throw Exception('Failed to load PubMed history: ${response.statusCode}');
  }

  // ─── 聊天会话持久化 ──────────────────────────────

  Future<void> saveMessage(String sessionId, String role, String content) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/chat/message'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'session_id': sessionId,
        'role': role,
        'content': content,
      }),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to save message: ${response.body}');
    }
  }

  Future<List<Map<String, dynamic>>> getConversation(String sessionId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/chat/conversation/$sessionId'),
    );
    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body);
      return data.map((e) => Map<String, dynamic>.from(e)).toList();
    }
    throw Exception('Failed to load conversation: ${response.statusCode}');
  }
}
