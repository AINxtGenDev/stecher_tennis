import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:logger/logger.dart';

/// A utility class to monitor network connectivity and provide callbacks.
class ConnectivityUtils {
  final Logger _logger = Logger();
  final Connectivity _connectivity = Connectivity();
  StreamSubscription<ConnectivityResult>? _subscription;
  ConnectivityResult _lastResult = ConnectivityResult.none;

  final Function()? onConnected;
  final Function()? onDisconnected;

  /// Creates a connectivity utility with optional callbacks for
  /// connection state changes.
  ConnectivityUtils({
    this.onConnected,
    this.onDisconnected,
  });

  /// Starts monitoring connectivity changes.
  Future<void> init() async {
    _logger.i('Initializing ConnectivityUtils');

    try {
      _lastResult = await _connectivity.checkConnectivity();
      _logger.i('Initial connectivity status: $_lastResult');

      _subscription = _connectivity.onConnectivityChanged.listen(_handleConnectivityChange);
    } catch (e) {
      _logger.e('Error initializing connectivity monitoring: $e');
    }
  }

  /// Handles connectivity change events.
  void _handleConnectivityChange(ConnectivityResult result) {
    _logger.i('Connectivity changed: $_lastResult -> $result');

    // If we're now connected but were previously disconnected
    if (result != ConnectivityResult.none && _lastResult == ConnectivityResult.none) {
      _logger.i('Network connection restored');
      if (onConnected != null) {
        onConnected!();
      }
    }

    // If we're now disconnected but were previously connected
    else if (result == ConnectivityResult.none && _lastResult != ConnectivityResult.none) {
      _logger.i('Network connection lost');
      if (onDisconnected != null) {
        onDisconnected!();
      }
    }

    _lastResult = result;
  }

  /// Checks if the device is currently connected to the internet.
  Future<bool> isConnected() async {
    final result = await _connectivity.checkConnectivity();
    return result != ConnectivityResult.none;
  }

  /// Stops monitoring connectivity changes.
  void dispose() {
    _logger.i('Disposing ConnectivityUtils');
    _subscription?.cancel();
  }
}