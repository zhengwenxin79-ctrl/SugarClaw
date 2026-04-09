import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/counterbalance.dart';
import '../services/api_service.dart';

const _foodUnitMap = {
  '羊肉串': '串', '白米饭': '碗', '热干面': '碗', '螺蛳粉': '碗',
  '肠粉': '份', '馒头': '个', '面包': '片', '牛奶': '杯',
  '苹果': '个', '鸡蛋': '个', '豆浆': '杯', '包子': '个',
  '饺子': '份', '油条': '根',
};
const _defaultUnit = '份';

class ScaleState extends ChangeNotifier {
  final ApiService _api = ApiService();

  static const _presetFoods = [
    '热干面',
    '白米饭',
    '螺蛳粉',
    '肠粉',
    '馒头',
    '面包',
    '牛奶',
    '苹果',
  ];
  static const _storageKey = 'custom_food_library';

  // ─── Left Pan: user's food library ──────
  // Preset common foods + user-added custom foods
  final List<String> foodLibrary = [..._presetFoods];
  final Set<String> selectedFoods = {}; // multi-select foods on left pan

  ScaleState() {
    _loadCustomFoods();
  }

  Future<void> _loadCustomFoods() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getStringList(_storageKey);
    if (saved != null && saved.isNotEmpty) {
      // 自定义食物插到最前面，最新的排第一
      for (var i = saved.length - 1; i >= 0; i--) {
        if (!foodLibrary.contains(saved[i])) {
          foodLibrary.insert(0, saved[i]);
        }
      }
      notifyListeners();
    }
  }

  Future<void> _saveCustomFoods() async {
    final prefs = await SharedPreferences.getInstance();
    final custom = foodLibrary.where((f) => !_presetFoods.contains(f)).toList();
    await prefs.setStringList(_storageKey, custom);
  }

  // ─── Quantity per food ────────────────────
  final Map<String, int> foodQuantities = {};

  String unitFor(String food) => _foodUnitMap[food] ?? _defaultUnit;
  int quantityOf(String food) => foodQuantities[food] ?? 1;

  // ─── Risk results per food ────────────────
  final Map<String, RiskResult> riskResults = {};
  bool loadingRisk = false;

  // ─── Right Pan: counter solutions ───────
  BalanceResult? balanceResult;
  bool loadingBalance = false;
  final Set<int> selectedIndices = {}; // indices dropped onto right pan

  // ─── Coordinator advice (refreshed on selection change) ──
  String? currentAdvice; // null = use balanceResult.advice as fallback
  String? _queryTime; // stored from toggleFood for advice refresh

  // ─── Error ──────────────────────────────
  String? error;

  // ─── Computed ───────────────────────────
  double get riskWeight {
    double total = 0;
    for (final food in selectedFoods) {
      total += riskResults[food]?.riskWeight ?? 0;
    }
    return total;
  }

  double get balanceWeight {
    if (balanceResult == null) return 0;
    double total = 0;
    for (final idx in selectedIndices) {
      if (idx < balanceResult!.solutions.length) {
        total += balanceResult!.solutions[idx].balanceWeight;
      }
    }
    return total;
  }

  /// theta = arctan((Wleft - Wright) / C)
  double get tiltAngle {
    if (riskWeight == 0 && balanceWeight == 0) return 0;
    const c = 50.0;
    // 限制最大倾斜 ±60°
    final diff = riskWeight - balanceWeight;
    if (diff.isNaN || diff.isInfinite) return 0;
    final angle = math.atan(diff / c);
    if (angle.isNaN || angle.isInfinite) return 0;
    return angle.clamp(-1.05, 1.05);
  }

  bool get isBalanced => riskWeight > 0 && balanceWeight >= riskWeight;

  /// Names of selected foods joined for display
  String get selectedFoodNames => selectedFoods.join('、');

  // ─── Actions ────────────────────────────

  /// User taps a food card — toggle selection
  Future<void> toggleFood(String name) async {
    if (selectedFoods.contains(name)) {
      // Deselect
      selectedFoods.remove(name);
      riskResults.remove(name);
      notifyListeners();
      // Re-fetch balance with updated total riskWeight
      await _refetchBalance();
      return;
    }

    // Select — add food and fetch its risk
    selectedFoods.add(name);
    loadingRisk = true;
    error = null;
    notifyListeners();

    final queryTime = DateTime.now().toIso8601String();
    _queryTime = queryTime;

    try {
      final risk = await _api.calculateRisk(
        name, queryTime: queryTime,
        quantityMultiplier: (foodQuantities[name] ?? 1).toDouble(),
      );
      riskResults[name] = risk;
      loadingRisk = false;
      notifyListeners();
      // Re-fetch balance with updated total riskWeight
      await _refetchBalance();
    } catch (e) {
      error = e.toString();
      loadingRisk = false;
      notifyListeners();
    }
  }

  /// Remove a specific food from selection
  void deselectFood(String name) {
    selectedFoods.remove(name);
    riskResults.remove(name);
    foodQuantities.remove(name);
    notifyListeners();
    _refetchBalance();
  }

  /// Update quantity for a food and refresh risk if selected
  Future<void> setQuantity(String name, int qty) async {
    qty = qty.clamp(1, 5);
    foodQuantities[name] = qty;
    notifyListeners();
    if (selectedFoods.contains(name)) {
      loadingRisk = true;
      notifyListeners();
      try {
        final risk = await _api.calculateRisk(
          name, queryTime: _queryTime,
          quantityMultiplier: qty.toDouble(),
        );
        riskResults[name] = risk;
        loadingRisk = false;
        notifyListeners();
        await _refetchBalance();
      } catch (e) {
        error = e.toString();
        loadingRisk = false;
        notifyListeners();
      }
    }
  }

  /// Re-fetch balance solutions based on total riskWeight of all selected foods
  Future<void> _refetchBalance() async {
    if (selectedFoods.isEmpty) {
      balanceResult = null;
      currentAdvice = null;
      selectedIndices.clear();
      notifyListeners();
      return;
    }

    // Use the first selected food as primary for the balance API
    final primaryFood = selectedFoods.first;
    final totalRisk = riskWeight;
    if (totalRisk <= 0) {
      balanceResult = null;
      currentAdvice = null;
      selectedIndices.clear();
      notifyListeners();
      return;
    }

    loadingBalance = true;
    selectedIndices.clear();
    currentAdvice = null;
    notifyListeners();

    try {
      final balance = await _api.findBalance(
        primaryFood,
        riskWeight: totalRisk,
        queryTime: _queryTime,
      );
      balanceResult = balance;
      loadingBalance = false;
      notifyListeners();
    } catch (e) {
      error = e.toString();
      loadingBalance = false;
      notifyListeners();
    }
  }

  /// User searches and adds a new food to library, then selects it
  Future<void> addCustomFood(String name) async {
    final trimmed = name.trim();
    if (trimmed.isEmpty) return;
    // avoid duplicates
    if (!foodLibrary.contains(trimmed)) {
      foodLibrary.insert(0, trimmed);
      await _saveCustomFoods();
    }
    notifyListeners();
    await toggleFood(trimmed);
  }

  /// Drop a solution card onto right pan (multi-select)
  void dropSolution(int index) {
    if (balanceResult == null) return;
    if (index >= balanceResult!.solutions.length) return;
    selectedIndices.add(index);
    notifyListeners();
    _refreshAdvice();
  }

  /// Tap to toggle a solution on right pan (multi-select)
  void toggleSolution(int index) {
    if (balanceResult == null) return;
    if (index >= balanceResult!.solutions.length) return;
    if (selectedIndices.contains(index)) {
      selectedIndices.remove(index);
    } else {
      selectedIndices.add(index);
    }
    notifyListeners();
    _refreshAdvice();
  }

  /// Remove a solution from right pan
  void removeSolution(int index) {
    selectedIndices.remove(index);
    notifyListeners();
    _refreshAdvice();
  }

  /// Refresh coordinator advice based on user's current selection
  Future<void> _refreshAdvice() async {
    if (balanceResult == null || selectedFoods.isEmpty) return;
    try {
      final result = await _api.refreshAdvice(
        foodName: selectedFoodNames,
        riskWeight: riskWeight,
        selectedIndices: selectedIndices.toList(),
        allSolutions: balanceResult!.solutions,
        queryTime: _queryTime,
      );
      currentAdvice = result['advice'];
      notifyListeners();
    } catch (_) {
      // Silently fail — keep existing advice
    }
  }

  /// User adds a custom exercise to the right pan
  Future<void> addCustomExercise(String name, int durationMin) async {
    if (balanceResult == null) return;
    try {
      final solution = await _api.addCustomExercise(name, durationMin, riskWeight);
      balanceResult!.solutions.add(solution);
      final newIndex = balanceResult!.solutions.length - 1;
      selectedIndices.add(newIndex);
      notifyListeners();
      _refreshAdvice();
    } catch (e) {
      error = e.toString();
      notifyListeners();
    }
  }

  /// User adds a custom food counter to the right pan
  Future<void> addCustomFoodCounter(String name) async {
    if (balanceResult == null) return;
    try {
      final solution = await _api.addCustomFoodCounter(name, riskWeight);
      balanceResult!.solutions.add(solution);
      final newIndex = balanceResult!.solutions.length - 1;
      selectedIndices.add(newIndex);
      notifyListeners();
      _refreshAdvice();
    } catch (e) {
      error = e.toString();
      notifyListeners();
    }
  }
}
