class FoodItem {
  final String name;
  final double gi;
  final double gl;
  final double carbG;
  final double proteinG;
  final double fatG;
  final double fiberG;
  final double servingSizeG;
  final String category;
  final double riskWeight;

  FoodItem({
    required this.name,
    this.gi = 0,
    this.gl = 0,
    this.carbG = 0,
    this.proteinG = 0,
    this.fatG = 0,
    this.fiberG = 0,
    this.servingSizeG = 0,
    this.category = '',
    this.riskWeight = 0,
  });

  factory FoodItem.fromJson(Map<String, dynamic> json) {
    return FoodItem(
      name: json['name'] ?? '',
      gi: (json['gi'] as num?)?.toDouble() ?? 0,
      gl: (json['gl'] as num?)?.toDouble() ?? 0,
      carbG: (json['carb_g'] as num?)?.toDouble() ?? 0,
      proteinG: (json['protein_g'] as num?)?.toDouble() ?? 0,
      fatG: (json['fat_g'] as num?)?.toDouble() ?? 0,
      fiberG: (json['fiber_g'] as num?)?.toDouble() ?? 0,
      servingSizeG: (json['serving_size_g'] as num?)?.toDouble() ?? 0,
      category: json['category'] ?? '',
      riskWeight: (json['risk_weight'] as num?)?.toDouble() ?? 0,
    );
  }
}

class CounterSolution {
  final String type; // food / exercise / medication
  final String name;
  final String description;
  final double balanceWeight;
  final String group;
  final Map<String, dynamic> details;
  bool selected;

  CounterSolution({
    required this.type,
    required this.name,
    required this.description,
    required this.balanceWeight,
    this.group = '',
    this.details = const {},
    this.selected = false,
  });

  factory CounterSolution.fromJson(Map<String, dynamic> json) {
    return CounterSolution(
      type: json['type'] ?? '',
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      balanceWeight: (json['balance_weight'] as num?)?.toDouble() ?? 0,
      group: json['group'] ?? '',
      details: json['details'] ?? {},
    );
  }
}

class RiskResult {
  final FoodItem food;
  final double riskWeight;
  final String riskLevel;
  final String riskDetail;

  RiskResult({
    required this.food,
    required this.riskWeight,
    required this.riskLevel,
    required this.riskDetail,
  });

  factory RiskResult.fromJson(Map<String, dynamic> json) {
    return RiskResult(
      food: FoodItem.fromJson(json['food']),
      riskWeight: (json['risk_weight'] as num).toDouble(),
      riskLevel: json['risk_level'],
      riskDetail: json['risk_detail'],
    );
  }
}

class BalanceResult {
  final double riskWeight;
  final FoodItem food;
  final List<CounterSolution> solutions;
  final String advice;

  BalanceResult({
    required this.riskWeight,
    required this.food,
    required this.solutions,
    required this.advice,
  });

  factory BalanceResult.fromJson(Map<String, dynamic> json) {
    return BalanceResult(
      riskWeight: (json['risk_weight'] as num).toDouble(),
      food: FoodItem.fromJson(json['food']),
      solutions: (json['solutions'] as List)
          .map((e) => CounterSolution.fromJson(e))
          .toList(),
      advice: json['advice'],
    );
  }
}
