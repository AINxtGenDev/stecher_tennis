import 'dart:async';
import 'package:socket_io_client/socket_io_client.dart' as io;
import 'package:logger/logger.dart';
import '../config.dart';
import '../utils/connectivity_utils.dart';

class SocketService {
  final Logger _logger = Logger();
  late io.Socket _socket;
  final Function onUpdateCallback;
  bool _isConnected = false;
  late ConnectivityUtils _connectivityUtils;
  Timer? _reconnectTimer;
  bool _intentionalDisconnect = false;

  // Constructor
  SocketService({required this.onUpdateCallback}) {
    _initSocket();
    _initConnectivityMonitor();
  }

  // Initialize Socket.IO connection
  void _initSocket() {
    _logger.i('Initializing Socket.IO connection to ${AppConfig.socketUrl}');

    try {
      _socket = io.io(
        AppConfig.socketUrl,
        io.OptionBuilder()
            .setTransports(['websocket'])
            .disableAutoConnect()
            .enableReconnection()
            .setReconnectionAttempts(5)
            .setReconnectionDelay(1000)
            .setReconnectionDelayMax(5000)
            .setTimeout(10000)
            .build(),
      );

      // Event handlers
      _socket.onConnect((_) {
        _logger.i('Socket connected');
        _isConnected = true;
        _cancelReconnectTimer();
      });

      _socket.onDisconnect((_) {
        _logger.i('Socket disconnected');
        _isConnected = false;

        // Only start reconnect timer if the disconnect wasn't intentional
        if (!_intentionalDisconnect) {
          _startReconnectTimer();
        }
      });

      _socket.on(AppConfig.updateEvent, (_) {
        _logger.i('Update event received');
        onUpdateCallback();
      });

      _socket.onConnectError((error) {
        _logger.e('Socket connection error: $error');
        _isConnected = false;
        _startReconnectTimer();
      });

      _socket.onError((error) {
        _logger.e('Socket error: $error');
      });

      _socket.onReconnect((_) {
        _logger.i('Socket reconnected');
        _isConnected = true;
        _cancelReconnectTimer();
      });

      _socket.onReconnectError((error) {
        _logger.e('Socket reconnection error: $error');
      });

      _socket.onReconnectFailed((_) {
        _logger.e('Socket reconnection failed');
        _startReconnectTimer(initialDelay: 5000); // Longer delay after socket.io reconnection fails
      });
    } catch (e) {
      _logger.e('Error initializing socket: $e');
    }
  }

  // Initialize connectivity monitor
  void _initConnectivityMonitor() {
    _connectivityUtils = ConnectivityUtils(
      onConnected: () {
        _logger.i('Network connected, attempting socket reconnection');
        if (!_isConnected) {
          reconnect();
        }
      },
      onDisconnected: () {
        _logger.i('Network disconnected, stopping socket connection');
        // Don't trigger reconnect when disconnecting due to network loss
        _intentionalDisconnect = true;
        disconnect();
        _intentionalDisconnect = false;
      },
    );

    _connectivityUtils.init();
  }

  // Start reconnect timer
  void _startReconnectTimer({int initialDelay = 2000}) {
    _cancelReconnectTimer();

    _reconnectTimer = Timer(Duration(milliseconds: initialDelay), () {
      _logger.i('Reconnect timer fired, attempting reconnection');
      if (!_isConnected) {
        reconnect();
      }
    });
  }

  // Cancel reconnect timer
  void _cancelReconnectTimer() {
    if (_reconnectTimer != null && _reconnectTimer!.isActive) {
      _reconnectTimer!.cancel();
      _reconnectTimer = null;
    }
  }

  // Connect to Socket.IO server
  void connect() {
    if (!_isConnected) {
      _logger.i('Connecting to Socket.IO server');
      _intentionalDisconnect = false;
      _socket.connect();
    }
  }

  // Disconnect from Socket.IO server
  void disconnect() {
    if (_isConnected) {
      _logger.i('Disconnecting from Socket.IO server');
      _intentionalDisconnect = true;
      _socket.disconnect();
      _isConnected = false;
    }
  }

  // Reconnect to Socket.IO server
  void reconnect() {
    _logger.i('Attempting to reconnect to Socket.IO server');
    _cancelReconnectTimer();
    _intentionalDisconnect = false;

    // Check if network is available before attempting reconnection
    _connectivityUtils.isConnected().then((connected) {
      if (connected) {
        disconnect();

        // Small delay to ensure clean disconnect before reconnecting
        Future.delayed(const Duration(milliseconds: 500), () {
          connect();
        });
      } else {
        _logger.i('Network not available, skipping reconnection attempt');
      }
    });
  }

  // Check if socket is connected
  bool get isConnected => _isConnected;

  // Dispose resources
  void dispose() {
    _logger.i('Disposing Socket.IO connection');
    _cancelReconnectTimer();
    _connectivityUtils.dispose();
    disconnect();
  }
}