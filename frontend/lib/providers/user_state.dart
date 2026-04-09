import 'package:flutter/material.dart';
import '../models/user_profile.dart';
import '../services/api_service.dart';

class UserState extends ChangeNotifier {
  final ApiService _api = ApiService();

  UserProfile? _profile;
  bool _loading = false;
  String? _error;
  List<String> _missingFields = [];

  UserProfile? get profile => _profile;
  bool get loading => _loading;
  String? get error => _error;
  bool get needsOnboarding {
    if (_profile == null) return false; // Still loading
    final isf = _profile!.isf;
    final weight = _profile!.weight;
    final name = _profile!.name;
    return isf == 0.0 || weight == 0.0 || name.isEmpty || name == '默认用户';
  }
  List<String> get missingFields => _missingFields;

  UserState() {
    _initLoad();
  }

  Future<void> _initLoad() async {
    await loadProfile();
    await checkOnboarding();
  }

  Future<void> checkOnboarding() async {
    try {
      final status = await _api.getOnboardingStatus();
      _missingFields = List<String>.from(status['missing_fields'] ?? []);
      notifyListeners();
    } catch (_) {
      // 检查失败不影响主流程
    }
  }

  Future<void> loadProfile() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _profile = await _api.getUserProfile();
    } catch (e) {
      _error = e.toString();
    }
    _loading = false;
    notifyListeners();
  }

  Future<void> updateProfile(Map<String, dynamic> fields) async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _profile = await _api.updateUserProfile(fields);
    } catch (e) {
      _error = e.toString();
    }
    _loading = false;
    notifyListeners();
  }

  Future<Map<String, dynamic>?> calibrateISF({
    required double before,
    required double after,
    required double dose,
  }) async {
    _error = null;
    try {
      final result = await _api.calibrateISF(before: before, after: after, dose: dose);
      // Reload profile to get updated ISF
      await loadProfile();
      return result;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return null;
    }
  }
}
