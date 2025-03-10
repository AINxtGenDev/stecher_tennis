import 'dart:async';
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

  // Selection state
  int? _selectedChallengerId;
  int? _selectedOpponentId;

  // Debounce for frequent updates
  Timer? _debounceTimer;
  bool _hasPendingUpdates = false;

  // Getters
  LoadingStatus get status => _status;
  String? get errorMessage => _errorMessage;
  List<Player> get players => List.unmodifiable(_players);
  List<Player> get eligibleOpponents => List.unmodifiable(_eligibleOpponents);
  List<Challenge> get activeChallenges => List.unmodifiable(_activeChallenges);
  bool get isInitialized => _isInitialized;

  // Selection getters
  int? get selectedChallengerId => _selectedChallengerId;
  int? get selectedOpponentId => _selectedOpponentId;

  // Cached & memoized filtered player lists for performance
  late List<Player> _cachedAvailablePlayers;
  late List<Player> _cachedUnavailablePlayers;
  late List<Player> _cachedBlockedChallengers;
  late List<Player> _cachedBlockedOpponents;
  late List<Player> _cachedInChallengePlayers;
  late List<Player> _cachedNewPlayers;
  bool _needsFiltersRefresh = true;

  // Filtered player lists
  List<Player> get availablePlayers {
    if (_needsFiltersRefresh) _refreshFilters();
    return _cachedAvailablePlayers;
  }

  List<Player> get unavailablePlayers {
    if (_needsFiltersRefresh) _refreshFilters();
    return _cachedUnavailablePlayers;
  }

  List<Player> get blockedChallengers {
    if (_needsFiltersRefresh) _refreshFilters();
    return _cachedBlockedChallengers;
  }

  List<Player> get blockedOpponents {
    if (_needsFiltersRefresh) _refreshFilters();
    return _cachedBlockedOpponents;
  }

  List<Player> get inChallengePlayers {
    if (_needsFiltersRefresh) _refreshFilters();
    return _cachedInChallengePlayers;
  }

  List<Player> get newPlayers {
    if (_needsFiltersRefresh) _refreshFilters();
    return _cachedNewPlayers;
  }

  // Constructor
  AppProvider({required ApiService apiService}) : _apiService = apiService {
    _initFilterCache();
    _socketService = SocketService(
      onUpdateCallback: () => refreshData(),
    );
    initialize();
  }

  // Selection methods
  void selectChallenger(int id) {
    if (_selectedChallengerId != id) {
      _selectedChallengerId = id;
      _selectedOpponentId = null;  // Reset opponent when challenger changes
      fetchEligibleOpponents(id);
      notifyListeners();
    }
  }

  void selectOpponent(int id) {
    if (_selectedOpponentId != id) {
      _selectedOpponentId = id;
      notifyListeners();
    }
  }

  void clearSelections() {
    if (_selectedChallengerId != null || _selectedOpponentId != null) {
      _selectedChallengerId = null;
      _selectedOpponentId = null;
      _eligibleOpponents = [];
      notifyListeners();
    }
  }

  // Initialize filter caches
  void _initFilterCache() {
    _cachedAvailablePlayers = [];
    _cachedUnavailablePlayers = [];
    _cachedBlockedChallengers = [];
    _cachedBlockedOpponents = [];
    _cachedInChallengePlayers = [];
    _cachedNewPlayers = [];
    _needsFiltersRefresh = true;
  }

  // Refresh filter caches
  void _refreshFilters() {
    _cachedAvailablePlayers = _players.where(
            (p) => p.available && !p.inChallenge
    ).toList();

    _cachedUnavailablePlayers = _players.where(
            (p) => !p.available
    ).toList();

    _cachedBlockedChallengers = _players.where(
            (p) => p.blockChallenger
    ).toList();

    _cachedBlockedOpponents = _players.where(
            (p) => p.blockOpponent
    ).toList();

    _cachedInChallengePlayers = _players.where(
            (p) => p.inChallenge
    ).toList();

    _cachedNewPlayers = _players.where(
            (p) => p.isNew
    ).toList();

    _needsFiltersRefresh = false;
  }

  // Initialize the provider
  Future<void> initialize() async {
    if (_isInitialized) return;

    _logger.i('Initializing AppProvider');
    _socketService.connect();
    await refreshData();
    _isInitialized = true;
  }

  // Refresh all data from the API with debounce
  Future<void> refreshData() async {
    // Cancel existing timer if it's still active
    if (_debounceTimer?.isActive ?? false) {
      _hasPendingUpdates = true;
      return;
    }

    // Use a debounce mechanism to avoid multiple rapid refreshes
    if (_status == LoadingStatus.loading) {
      _logger.i('Already refreshing, applying debounce');
      _hasPendingUpdates = true;

      // Set debounce timer to check for pending updates
      _debounceTimer = Timer(const Duration(milliseconds: 300), () {
        if (_hasPendingUpdates) {
          _hasPendingUpdates = false;
          refreshData();
        }
      });

      return;
    }

    _setLoading();

    try {
      // Load data in parallel for efficiency
      await Future.wait([
        _fetchPlayers(),
        _fetchActiveChallenges(),
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

  // Fetch all players (internal method)
  Future<void> _fetchPlayers() async {
    try {
      final players = await _apiService.getPlayers();
      if (!listEquals(_players, players)) {
        _players = players;
        _needsFiltersRefresh = true;
      }
    } catch (e) {
      _logger.e('Error fetching players: $e');
      rethrow;
    }
  }

  // Fetch active challenges (internal method)
  Future<void> _fetchActiveChallenges() async {
    try {
      final challenges = await _apiService.getActiveChallenges();
      if (!listEquals(_activeChallenges, challenges)) {
        _activeChallenges = challenges;
      }
    } catch (e) {
      _logger.e('Error fetching active challenges: $e');
      // Don't throw - this is secondary data
    }
  }

  // Fetch all players (public method - can be called separately)
  Future<void> fetchPlayers() async {
    try {
      _setLoading();
      await _fetchPlayers();
      _setSuccess();
    } catch (e) {
      _logger.e('Error fetching players: $e');
      _setError('Failed to load players: $e');
    }
  }

  // Fetch active challenges (public method - can be called separately)
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

      // Clear selections after successful challenge
      _selectedChallengerId = null;
      _selectedOpponentId = null;

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
    _debounceTimer?.cancel();
    super.dispose();
  }
}