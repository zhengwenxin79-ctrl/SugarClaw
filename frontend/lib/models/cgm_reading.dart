class CgmReading {
  final String timestamp;
  final double glucoseMmol;
  final double glucoseMgdl;
  final String event;

  CgmReading({
    required this.timestamp,
    required this.glucoseMmol,
    this.glucoseMgdl = 0,
    this.event = '',
  });

  factory CgmReading.fromJson(Map<String, dynamic> json) {
    final mmol = (json['glucose_mmol'] ?? 0).toDouble();
    return CgmReading(
      timestamp: json['timestamp'] ?? '',
      glucoseMmol: mmol,
      glucoseMgdl: (json['glucose_mgdl'] ?? mmol * 18.0).toDouble(),
      event: json['event'] ?? '',
    );
  }
}

class CgmSession {
  final String sessionId;
  final String source;
  final String startTime;
  final String endTime;
  final int readingCount;

  CgmSession({
    required this.sessionId,
    required this.source,
    required this.startTime,
    required this.endTime,
    required this.readingCount,
  });

  factory CgmSession.fromJson(Map<String, dynamic> json) {
    return CgmSession(
      sessionId: json['session_id'] ?? '',
      source: json['source'] ?? '',
      startTime: json['start_time'] ?? '',
      endTime: json['end_time'] ?? '',
      readingCount: json['reading_count'] ?? 0,
    );
  }
}
