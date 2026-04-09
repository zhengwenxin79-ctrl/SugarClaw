class UserProfile {
  final int id;
  final String name;
  final int age;
  final double weight;
  final double height;
  final String diabetesType;
  final List<String> medications;
  final double isf;
  final double icr;
  final String regionalPreference;

  UserProfile({
    this.id = 1,
    this.name = '',
    this.age = 0,
    this.weight = 0,
    this.height = 0,
    this.diabetesType = '',
    this.medications = const [],
    this.isf = 0,
    this.icr = 0,
    this.regionalPreference = '全国',
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: json['id'] ?? 1,
      name: json['name'] ?? '',
      age: json['age'] ?? 0,
      weight: (json['weight'] ?? 0).toDouble(),
      height: (json['height'] ?? 0).toDouble(),
      diabetesType: json['diabetes_type'] ?? '',
      medications: List<String>.from(json['medications'] ?? []),
      isf: (json['isf'] ?? 0).toDouble(),
      icr: (json['icr'] ?? 0).toDouble(),
      regionalPreference: json['regional_preference'] ?? '全国',
    );
  }

  Map<String, dynamic> toJson() => {
        'name': name,
        'age': age,
        'weight': weight,
        'height': height,
        'diabetes_type': diabetesType,
        'medications': medications,
        'isf': isf,
        'icr': icr,
        'regional_preference': regionalPreference,
      };
}
