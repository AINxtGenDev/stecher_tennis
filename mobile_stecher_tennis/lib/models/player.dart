class Player {
  final int id;
  final String name;
  final int rank;
  final bool available;
  final String? unavailableSince;
  final bool blockChallenger;
  final bool blockOpponent;
  final bool inChallenge;
  final bool isNew;
  final DateTime? blockChallengerUntil;
  final DateTime? blockOpponentUntil;

  Player({
    required this.id,
    required this.name,
    required this.rank,
    required this.available,
    this.unavailableSince,
    this.blockChallenger = false,
    this.blockOpponent = false,
    this.inChallenge = false,
    this.isNew = false,
    this.blockChallengerUntil,
    this.blockOpponentUntil,
  });

  factory Player.fromJson(Map<String, dynamic> json) {
    return Player(
      id: json['id'] as int,
      name: json['name'] as String,
      rank: json['rank'] as int,
      available: json['available'] == true || json['available'] == 1,
      unavailableSince: json['unavailable_since'],
      blockChallenger: json['block_challenger'] == true || json['block_challenger'] == 1,
      blockOpponent: json['block_opponent'] == true || json['block_opponent'] == 1,
      inChallenge: json['in_challenge'] == true || json['in_challenge'] == 1,
      isNew: json['is_new'] == true || json['is_new'] == 1,
      blockChallengerUntil: json['block_challenger_until'] != null ?
      DateTime.parse(json['block_challenger_until']) : null,
      blockOpponentUntil: json['block_opponent_until'] != null ?
      DateTime.parse(json['block_opponent_until']) : null,
    );
  }

  // Create a copy of this player with specified fields updated
  Player copyWith({
    int? id,
    String? name,
    int? rank,
    bool? available,
    String? unavailableSince,
    bool? blockChallenger,
    bool? blockOpponent,
    bool? inChallenge,
    bool? isNew,
    DateTime? blockChallengerUntil,
    DateTime? blockOpponentUntil,
  }) {
    return Player(
      id: id ?? this.id,
      name: name ?? this.name,
      rank: rank ?? this.rank,
      available: available ?? this.available,
      unavailableSince: unavailableSince ?? this.unavailableSince,
      blockChallenger: blockChallenger ?? this.blockChallenger,
      blockOpponent: blockOpponent ?? this.blockOpponent,
      inChallenge: inChallenge ?? this.inChallenge,
      isNew: isNew ?? this.isNew,
      blockChallengerUntil: blockChallengerUntil ?? this.blockChallengerUntil,
      blockOpponentUntil: blockOpponentUntil ?? this.blockOpponentUntil,
    );
  }

  // For debugging
  @override
  String toString() {
    return 'Player{id: $id, name: $name, rank: $rank, available: $available}';
  }
}