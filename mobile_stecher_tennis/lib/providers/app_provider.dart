import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';

import '../models/player.dart';
import '../models/challenge.dart';
import '../services/api_service.dart';
import '../services/socket_service.dart';

enum LoadingStatus { idle, loading, error }

class AppProvider with ChangeNotifier {
  final ApiService _apiService;
  late SocketService _socketService;
  final Logger _logger = Logger();

  // State variables
  LoadingStatus _status = LoadingStatus.idle;
  String? _errorMessage;
  List<Player> _players = [];
  List<Player> _eligibleOpponents = [];
  List<Challenge> _activeChallenges = [];
  bool _isInitialized = false;

  // Getters
  LoadingStatus get status => _status;
  String? get errorMessage => _errorMessage;
  List<Player> get players => List.unmodifiable(_players);
  List<Player> get eligibleOpponents => List.unmodifiable(_eligibleOpponents);
  List<Challenge> get activeChallenges => List.unmodifiable(_activeChallenges);
  bool get isInitialized => _isInitialized;

  // Filtered player lists
  List<Player> get availablePlayers => _players.where((p) => p.available && !p.inChallenge).toList();
  List<Player> get unavailablePlayers => _players.where((p) => !p.available).toList();
  List<Player> get blockedChallengers => _players.where((p) => p.blockChallenger).toList();
  List<Player> get blockedOpponents => _players.where((p) => p.blockOpponent).toList();
  List<Player> get inChallengePlayers => _players.where((p) => p.inChallenge).toList();
  List<Player> get newPlayers => _players.where((p) => p.isNew).toList();

  // Constructor
  AppProvider({required ApiService apiService}) : _apiService = apiService {
    _socketService = SocketService(
      onUpdateCallback: () => refreshData(),
    );
    initialize();
  }

  // Initialize the provider
  Future<void> initialize() async {
    if (_isInitialized) return;

    _logger.i('Initializing AppProvider');
    _socketService.connect();
    await refreshData();
    _isInitialized = true;
  }

  // Refresh all data from the API
  Future<void> refreshData() async {
    _logger.i('Refreshing data');

    // Use a debounce mechanism to avoid multiple rapid refreshes
    if (_status == LoadingStatus.loading) {
      _logger.i('Already refreshing, skipping this request');
      return;
    }

    _setLoading();

    try {
      // Load data in parallel for efficiency
      await Future.wait([
        fetchPlayers(),
        fetchActiveChallenges(),
      ]);

      _setSuccess();
    } catch (e) {
      _logger.e('Error refreshing data: $e');
      _setError('Failed to refresh data: $e');
    }
  }

  // Set loading status
  void _setLoading() {
    _status = LoadingStatus.loading;
    notifyListeners();
  }

  // Set error status
  void _setError(String message) {
    _status = LoadingStatus.error;
    _errorMessage = message;
    notifyListeners();
  }

  // Set success status
  void _setSuccess() {
    _status = LoadingStatus.idle;
    _errorMessage = null;
    notifyListeners();
  }

  // Fetch all players
  Future<void> fetchPlayers() async {
    try {
      _setLoading();
      final players = await _apiService.getPlayers();
      _players = players;
      _setSuccess();
    } catch (e) {
      _logger.e('Error fetching players: $e');
      _setError('Failed to load players: $e');
    }
  }

  // Fetch active challenges
  Future<void> fetchActiveChallenges() async {
    try {
      final challenges = await _apiService.getActiveChallenges();
      _activeChallenges = challenges;
      notifyListeners();
    } catch (e) {
      _logger.e('Error fetching active challenges: $e');
      // Don't set error status as this is secondary data
    }
  }

  // Get eligible opponents for a challenger
  Future<void> fetchEligibleOpponents(int challengerId) async {
    try {
      _setLoading();
      final opponents = await _apiService.getEligibleOpponents(challengerId);
      _eligibleOpponents = opponents;
      _setSuccess();
    } catch (e) {
      _logger.e('Error fetching eligible opponents: $e');
      _setError('Failed to load eligible opponents: $e');
    }
  }

  // Create a challenge
  Future<Map<String, dynamic>> createChallenge(int challengerId, int opponentId) async {
    try {
      _setLoading();
      final result = await _apiService.createChallenge(challengerId, opponentId);
      await refreshData();
      _setSuccess();
      return result;
    } catch (e) {
      _logger.e('Error creating challenge: $e');
      _setError('Failed to create challenge: $e');
      return {'error': e.toString()};
    }
  }

  // Toggle player availability
  Future<Map<String, dynamic>> toggleAvailability(int playerId) async {
    try {
      _setLoading();
      final result = await _apiService.toggleAvailability(playerId);
      await refreshData();
      _setSuccess();
      return result;
    } catch (e) {
      _logger.e('Error toggling availability: $e');
      _setError('Failed to toggle availability: $e');
      return {'success': false, 'message': e.toString()};
    }
  }

  // Create new player challenge
  Future<Map<String, dynamic>> createNewPlayerChallenge(String newPlayerName, int opponentId) async {
    try {
      _setLoading();
      final result = await _apiService.createNewPlayerChallenge(newPlayerName, opponentId);
      await refreshData();
      _setSuccess();
      return result;
    } catch (e) {
      _logger.e('Error creating new player challenge: $e');
      _setError('Failed to create new player challenge: $e');
      return {'error': e.toString()};
    }
  }

  // Submit challenge result (admin functionality)
  Future<Map<String, dynamic>> submitResult(int challengeId, String result) async {
    try {
      _setLoading();
      final response = await _apiService.submitResult(challengeId, result);
      await refreshData();
      _setSuccess();
      return response;
    } catch (e) {
      _logger.e('Error submitting result: $e');
      _setError('Failed to submit result: $e');
      return {'success': false, 'message': e.toString()};
    }
  }

  // Update player details
  Future<Map<String, dynamic>> updatePlayer(int playerId, String name, int rank) async {
    try {
      _setLoading();
      final result = await _apiService.updatePlayer(playerId, name, rank);
      await refreshData();
      _setSuccess();
      return result;
    } catch (e) {
      _logger.e('Error updating player: $e');
      _setError('Failed to update player: $e');
      return {'success': false, 'message': e.toString()};
    }
  }

  // Delete player
  Future<Map<String, dynamic>> deletePlayer(int playerId) async {
    try {
      _setLoading();
      final result = await _apiService.deletePlayer(playerId);
      await refreshData();
      _setSuccess();
      return result;
    } catch (e) {
      _logger.e('Error deleting player: $e');
      _setError('Failed to delete player: $e');
      return {'success': false, 'message': e.toString()};
    }
  }

  // Clear the current error message
  void clearError() {
    _errorMessage = null;
    _status = LoadingStatus.idle;
    notifyListeners();
  }

  // Find a player by ID
  Player? findPlayerById(int id) {
    try {
      return _players.firstWhere((player) => player.id == id);
    } catch (e) {
      return null;
    }
  }

  // Dispose resources
  @override
  void dispose() {
    _logger.i('Disposing AppProvider');
    _socketService.dispose();
    _apiService.dispose();
    super.dispose();
  }
}