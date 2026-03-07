import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/counterbalance.dart';
import '../services/api_service.dart';

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
  String? selectedFood; // currently placed on left pan

  ScaleState() {
    _loadCustomFoods();
  }

  Future<void> _loadCustomFoods() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getStringList(_storageKey);
    if (saved != null && saved.isNotEmpty) {
      for (final food in saved) {
        if (!foodLibrary.contains(food)) {
          foodLibrary.add(food);
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

  RiskResult? riskResult;
  bool loadingRisk = false;

  // ─── Right Pan: counter solutions ───────
  BalanceResult? balanceResult;
  bool loadingBalance = false;
  final Set<int> selectedIndices = {}; // indices dropped onto right pan

  // ─── Error ──────────────────────────────
  String? error;

  // ─── Computed ───────────────────────────
  double get riskWeight => riskResult?.riskWeight ?? 0;

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
    return math.atan((riskWeight - balanceWeight) / c);
  }

  bool get isBalanced => riskWeight > 0 && balanceWeight >= riskWeight;

  // ─── Actions ────────────────────────────

  /// User taps a food card on left pan area
  Future<void> selectFood(String name) async {
    if (name == selectedFood) return;
    selectedFood = name;
    loadingRisk = true;
    error = null;
    riskResult = null;
    balanceResult = null;
    selectedIndices.clear();
    notifyListeners();

    try {
      final risk = await _api.calculateRisk(name);
      riskResult = risk;
      loadingRisk = false;
      notifyListeners();
      // auto-find balance solutions
      await _findBalance(name);
    } catch (e) {
      error = e.toString();
      loadingRisk = false;
      notifyListeners();
    }
  }

  Future<void> _findBalance(String foodName) async {
    if (riskResult == null) return;
    loadingBalance = true;
    notifyListeners();
    try {
      final balance = await _api.findBalance(
        foodName,
        riskWeight: riskWeight,
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
      foodLibrary.add(trimmed);
      await _saveCustomFoods();
    }
    notifyListeners();
    await selectFood(trimmed);
  }

  /// Drop a solution card onto right pan (group-aware single-select)
  void dropSolution(int index) {
    _selectWithinGroup(index);
    notifyListeners();
  }

  /// Tap to toggle a solution on right pan (group-aware single-select)
  void toggleSolution(int index) {
    if (selectedIndices.contains(index)) {
      selectedIndices.remove(index);
    } else {
      _selectWithinGroup(index);
    }
    notifyListeners();
  }

  /// Select [index] and deselect any other selected item in the same group.
  void _selectWithinGroup(int index) {
    if (balanceResult == null) return;
    final solutions = balanceResult!.solutions;
    if (index >= solutions.length) return;

    final group = solutions[index].group;
    if (group.isNotEmpty) {
      // Remove other selections in the same group
      selectedIndices.removeWhere((i) =>
          i < solutions.length && solutions[i].group == group && i != index);
    }
    selectedIndices.add(index);
  }

  /// Remove a solution from right pan
  void removeSolution(int index) {
    selectedIndices.remove(index);
    notifyListeners();
  }

  /// User adds a custom exercise to the right pan
  Future<void> addCustomExercise(String name, int durationMin) async {
    if (balanceResult == null) return;
    try {
      final solution = await _api.addCustomExercise(name, durationMin, riskWeight);
      balanceResult!.solutions.add(solution);
      final newIndex = balanceResult!.solutions.length - 1;
      _selectWithinGroup(newIndex);
      notifyListeners();
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
      _selectWithinGroup(newIndex);
      notifyListeners();
    } catch (e) {
      error = e.toString();
      notifyListeners();
    }
  }
}
