class Challenge {
  final int id;
  final int challengerId;
  final int opponentId;
  final String challengerName;
  final String opponentName;
  final DateTime timestamp;
  final DateTime deadline;
  final DateTime? resolvedAt;
  final bool resolved;
  final String? result;

  Challenge({
    required this.id,
    required this.challengerId,
    required this.opponentId,
    required this.challengerName,
    required this.opponentName,
    required this.timestamp,
    required this.deadline,
    this.resolvedAt,
    required this.resolved,
    this.result,
  });

  factory Challenge.fromJson(Map<String, dynamic> json) {
    return Challenge(
      id: json['id'] as int,
      challengerId: json['challenger_id'] as int,
      opponentId: json['opponent_id'] as int,
      challengerName: json['challenger_name'] as String,
      opponentName: json['opponent_name'] as String,
      timestamp: DateTime.parse(json['timestamp'] as String),
      deadline: DateTime.parse(json['deadline'] as String),
      resolvedAt: json['resolved_at'] != null ? DateTime.parse(json['resolved_at'] as String) : null,
      resolved: json['resolved'] == 1 || json['resolved'] == true,
      result: json['result'] as String?,
    );
  }

  // Check if challenge is expired but not resolved
  bool get isExpired => deadline.isBefore(DateTime.now()) && !resolved;

  // Get formatted deadline date
  String get formattedDeadline {
    return '${deadline.year}-${deadline.month.toString().padLeft(2, '0')}-${deadline.day.toString().padLeft(2, '0')}';
  }

  // Create a copy of this challenge with specified fields updated
  Challenge copyWith({
    int? id,
    int? challengerId,
    int? opponentId,
    String? challengerName,
    String? opponentName,
    DateTime? timestamp,
    DateTime? deadline,
    DateTime? resolvedAt,
    bool? resolved,
    String? result,
  }) {
    return Challenge(
      id: id ?? this.id,
      challengerId: challengerId ?? this.challengerId,
      opponentId: opponentId ?? this.opponentId,
      challengerName: challengerName ?? this.challengerName,
      opponentName: opponentName ?? this.opponentName,
      timestamp: timestamp ?? this.timestamp,
      deadline: deadline ?? this.deadline,
      resolvedAt: resolvedAt ?? this.resolvedAt,
      resolved: resolved ?? this.resolved,
      result: result ?? this.result,
    );
  }

  // For debugging
  @override
  String toString() {
    return 'Challenge{id: $id, challenger: $challengerName, opponent: $opponentName, deadline: $formattedDeadline, resolved: $resolved}';
  }
}