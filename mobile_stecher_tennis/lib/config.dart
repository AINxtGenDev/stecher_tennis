class AppConfig {
  // Backend URL configuration - Updated to use your specific server
  static const String baseUrl = 'https://stechertennis.duckdns.org:10443';

  // Socket.IO configuration
  static const String socketUrl = baseUrl;

  // App information
  static const String appName = 'Mobile Tennisranking App';
  static const String appVersion = '1.0.0';

  // API endpoints
  static String get getPlayersEndpoint => '$baseUrl/get_players';
  static String get eligibleOpponentsEndpoint => '$baseUrl/eligible_opponents';
  static String get challengeEndpoint => '$baseUrl/challenge';
  static String get toggleAvailabilityEndpoint => '$baseUrl/toggle_availability';
  static String get newPlayerChallengeEndpoint => '$baseUrl/newplayer_challenge';
  static String get submitResultEndpoint => '$baseUrl/submit_result';
  static String get updatePlayerEndpoint => '$baseUrl/update_player';
  static String get deletePlayerEndpoint => '$baseUrl/delete_player';

  // Timeouts
  static const int connectionTimeout = 10000; // 10 seconds
  static const int receiveTimeout = 5000; // 5 seconds

  // Socket.IO event names
  static const String updateEvent = 'update';

  // Logging
  static const bool enableDebugLogs = true;
}