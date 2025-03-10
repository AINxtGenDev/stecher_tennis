import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:logger/logger.dart';
import '../config.dart';
import '../models/player.dart';
import '../models/challenge.dart';

class ApiService {
  final Logger _logger = Logger();
  final http.Client _client = http.Client();

  // Fetch all players
  Future<List<Player>> getPlayers() async {
    try {
      final response = await _client.get(
        Uri.parse(AppConfig.getPlayersEndpoint),
      ).timeout(const Duration(milliseconds: AppConfig.connectionTimeout));

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((json) => Player.fromJson(json)).toList();
      } else {
        _logger.e('Failed to load players: ${response.statusCode}');
        throw Exception('Failed to load players: ${response.statusCode}');
      }
    } catch (e) {
      _logger.e('Error getting players: $e');
      throw Exception('Error getting players: $e');
    }
  }

  // Fetch eligible opponents for a challenger
  Future<List<Player>> getEligibleOpponents(int challengerId) async {
    try {
      final response = await _client.post(
        Uri.parse(AppConfig.eligibleOpponentsEndpoint),
        body: {'challenger_id': challengerId.toString()},
      ).timeout(const Duration(milliseconds: AppConfig.connectionTimeout));

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((json) => Player.fromJson(json)).toList();
      } else {
        _logger.e('Failed to load eligible opponents: ${response.statusCode}');
        throw Exception('Failed to load eligible opponents: ${response.statusCode}');
      }
    } catch (e) {
      _logger.e('Error getting eligible opponents: $e');
      throw Exception('Error getting eligible opponents: $e');
    }
  }

  // Create a new challenge
  Future<Map<String, dynamic>> createChallenge(int challengerId, int opponentId) async {
    try {
      final response = await _client.post(
        Uri.parse(AppConfig.challengeEndpoint),
        body: {
          'challenger': challengerId.toString(),
          'opponent': opponentId.toString(),
        },
      ).timeout(const Duration(milliseconds: AppConfig.connectionTimeout));

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        final errorResponse = json.decode(response.body);
        _logger.e('Failed to create challenge: ${response.statusCode} - ${errorResponse['error']}');
        throw Exception('Failed to create challenge: ${errorResponse['error']}');
      }
    } catch (e) {
      _logger.e('Error creating challenge: $e');
      throw Exception('Error creating challenge: $e');
    }
  }

  // Toggle player availability
  Future<Map<String, dynamic>> toggleAvailability(int playerId) async {
    try {
      final response = await _client.post(
        Uri.parse(AppConfig.toggleAvailabilityEndpoint),
        body: {'player_id': playerId.toString()},
      ).timeout(const Duration(milliseconds: AppConfig.connectionTimeout));

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        final errorResponse = json.decode(response.body);
        _logger.e('Failed to toggle availability: ${response.statusCode} - ${errorResponse['message']}');
        throw Exception('Failed to toggle availability: ${errorResponse['message']}');
      }
    } catch (e) {
      _logger.e('Error toggling availability: $e');
      throw Exception('Error toggling availability: $e');
    }
  }

  // Create new player challenge
  Future<Map<String, dynamic>> createNewPlayerChallenge(String newPlayerName, int opponentId) async {
    try {
      final response = await _client.post(
        Uri.parse(AppConfig.newPlayerChallengeEndpoint),
        body: {
          'newplayer_name': newPlayerName,
          'opponent_id': opponentId.toString(),
        },
      ).timeout(const Duration(milliseconds: AppConfig.connectionTimeout));

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        final errorResponse = json.decode(response.body);
        _logger.e('Failed to create new player challenge: ${response.statusCode} - ${errorResponse['error']}');
        throw Exception('Failed to create new player challenge: ${errorResponse['error']}');
      }
    } catch (e) {
      _logger.e('Error creating new player challenge: $e');
      throw Exception('Error creating new player challenge: $e');
    }
  }

  // Submit challenge result (admin functionality)
  Future<Map<String, dynamic>> submitResult(int challengeId, String result) async {
    try {
      final response = await _client.post(
        Uri.parse(AppConfig.submitResultEndpoint),
        body: {
          'challenge_id': challengeId.toString(),
          'result': result,
        },
      ).timeout(const Duration(milliseconds: AppConfig.connectionTimeout));

      if (response.statusCode == 200) {
        return {'success': true};
      } else {
        _logger.e('Failed to submit result: ${response.statusCode}');
        throw Exception('Failed to submit result: ${response.statusCode}');
      }
    } catch (e) {
      _logger.e('Error submitting result: $e');
      throw Exception('Error submitting result: $e');
    }
  }

  // Update player details
  Future<Map<String, dynamic>> updatePlayer(int playerId, String name, int rank) async {
    try {
      final response = await _client.post(
        Uri.parse(AppConfig.updatePlayerEndpoint),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'id': playerId,
          'name': name,
          'rank': rank,
        }),
      ).timeout(const Duration(milliseconds: AppConfig.connectionTimeout));

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        final errorResponse = json.decode(response.body);
        _logger.e('Failed to update player: ${response.statusCode} - ${errorResponse['message']}');
        throw Exception('Failed to update player: ${errorResponse['message']}');
      }
    } catch (e) {
      _logger.e('Error updating player: $e');
      throw Exception('Error updating player: $e');
    }
  }

  // Delete player
  Future<Map<String, dynamic>> deletePlayer(int playerId) async {
    try {
      final response = await _client.post(
        Uri.parse(AppConfig.deletePlayerEndpoint),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'id': playerId}),
      ).timeout(const Duration(milliseconds: AppConfig.connectionTimeout));

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        final errorResponse = json.decode(response.body);
        _logger.e('Failed to delete player: ${response.statusCode} - ${errorResponse['message']}');
        throw Exception('Failed to delete player: ${errorResponse['message']}');
      }
    } catch (e) {
      _logger.e('Error deleting player: $e');
      throw Exception('Error deleting player: $e');
    }
  }

  // Get active challenges
  Future<List<Challenge>> getActiveChallenges() async {
    try {
      // This endpoint is not directly available in the API, so we'll parse from the index page
      // A better approach would be to create a dedicated API endpoint
      final List<Player> players = await getPlayers();

      // Filter players that are in challenge
      final inChallengePlayerIds = players
          .where((player) => player.inChallenge)
          .map((player) => player.id)
          .toList();

      if (inChallengePlayerIds.isEmpty) {
        return [];
      }

      // Return placeholder data until we implement a proper endpoint for fetching challenges
      // In a real application, you'd create a dedicated API endpoint
      return [];
    } catch (e) {
      _logger.e('Error getting active challenges: $e');
      throw Exception('Error getting active challenges: $e');
    }
  }

  // Dispose resources
  void dispose() {
    _client.close();
  }
}