import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_provider.dart';
import '../models/player.dart';

class DbSettingsScreen extends StatefulWidget {
  const DbSettingsScreen({super.key});

  @override
  State<DbSettingsScreen> createState() => _DbSettingsScreenState();
}

class _DbSettingsScreenState extends State<DbSettingsScreen> {
  final _newPlayerNameController = TextEditingController();
  final _newPlayerRankController = TextEditingController();

  int? _editingPlayerId;
  String? _editingPlayerName;
  String? _editingPlayerRank;

  String? _notificationMessage;
  bool _isNotificationSuccess = true;
  bool _isProcessing = false;

  @override
  void dispose() {
    _newPlayerNameController.dispose();
    _newPlayerRankController.dispose();
    super.dispose();
  }

  void _showNotification(String message, bool isSuccess) {
    setState(() {
      _notificationMessage = message;
      _isNotificationSuccess = isSuccess;
    });

    // Auto-hide notification after 3 seconds
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) {
        setState(() {
          _notificationMessage = null;
        });
      }
    });
  }

  Future<void> _refreshData() async {
    await Provider.of<AppProvider>(context, listen: false).refreshData();
  }

  void _editPlayer(Player player) {
    setState(() {
      _editingPlayerId = player.id;
      _editingPlayerName = player.name;
      _editingPlayerRank = player.rank.toString();
    });
  }

  void _cancelEditing() {
    setState(() {
      _editingPlayerId = null;
      _editingPlayerName = null;
      _editingPlayerRank = null;
    });
  }

  Future<void> _savePlayer() async {
    if (_editingPlayerId == null ||
        _editingPlayerName == null ||
        _editingPlayerName!.trim().isEmpty ||
        _editingPlayerRank == null) {
      return;
    }

    final newRank = int.tryParse(_editingPlayerRank!);
    if (newRank == null || newRank < 1) {
      _showNotification('Ungültiger Rang.', false);
      return;
    }

    setState(() {
      _isProcessing = true;
    });

    try {
      final provider = Provider.of<AppProvider>(context, listen: false);
      final result = await provider.updatePlayer(
        _editingPlayerId!,
        _editingPlayerName!.trim(),
        newRank,
      );

      if (result['success'] == true) {
        _showNotification('Spieler erfolgreich aktualisiert.', true);
        _cancelEditing();
      } else {
        _showNotification(result['message'] ?? 'Fehler beim Aktualisieren des Spielers.', false);
      }
    } catch (e) {
      _showNotification('Fehler: $e', false);
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  Future<void> _confirmDeletePlayer(Player player) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Spieler löschen'),
        content: Text('Sind Sie sicher, dass Sie ${player.name} löschen möchten?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Abbrechen'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Löschen'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await _deletePlayer(player.id);
    }
  }

  Future<void> _deletePlayer(int playerId) async {
    setState(() {
      _isProcessing = true;
    });

    try {
      final provider = Provider.of<AppProvider>(context, listen: false);
      final result = await provider.deletePlayer(playerId);

      if (result['success'] == true) {
        _showNotification('Spieler erfolgreich gelöscht.', true);
      } else {
        _showNotification(result['message'] ?? 'Fehler beim Löschen des Spielers.', false);
      }
    } catch (e) {
      _showNotification('Fehler: $e', false);
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  Future<void> _addNewPlayer() async {
    final name = _newPlayerNameController.text.trim();
    if (name.isEmpty) {
      _showNotification('Name darf nicht leer sein.', false);
      return;
    }

    final rankText = _newPlayerRankController.text.trim();
    final rank = int.tryParse(rankText);
    if (rank == null || rank < 1) {
      _showNotification('Ungültiger Rang.', false);
      return;
    }

    setState(() {
      _isProcessing = true;
    });

    try {
      // We don't have a direct API for adding players, so we'll show a mock success
      // In a real app, you would call your API service

      await Future.delayed(const Duration(seconds: 1)); // Simulate API call

      _showNotification('Spieler erfolgreich hinzugefügt.', true);
      _newPlayerNameController.clear();
      _newPlayerRankController.clear();

      // In a real app, you would refresh the data after adding a player
      await _refreshData();
    } catch (e) {
      _showNotification('Fehler: $e', false);
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Spielerdatenbank-Einstellungen'),
      ),
      body: Consumer<AppProvider>(
        builder: (context, provider, child) {
          final players = List<Player>.from(provider.players);
          players.sort((a, b) => a.rank.compareTo(b.rank));

          return Stack(
            children: [
              RefreshIndicator(
                onRefresh: _refreshData,
                child: ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    _buildAddPlayerForm(),
                    const SizedBox(height: 24),
                    _buildPlayersTable(players),
                  ],
                ),
              ),
              if (_notificationMessage != null)
                Positioned(
                  top: 16,
                  left: 16,
                  right: 16,
                  child: _buildNotification(),
                ),
              if (_isProcessing)
                const Center(
                  child: CircularProgressIndicator(),
                ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildNotification() {
    return Card(
      color: _isNotificationSuccess ? Colors.green.shade100 : Colors.red.shade100,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            Icon(
              _isNotificationSuccess ? Icons.check_circle : Icons.error,
              color: _isNotificationSuccess ? Colors.green : Colors.red,
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Text(_notificationMessage ?? ''),
            ),
            IconButton(
              icon: const Icon(Icons.close),
              onPressed: () {
                setState(() {
                  _notificationMessage = null;
                });
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAddPlayerForm() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Neuen Spieler hinzufügen',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _newPlayerNameController,
              decoration: const InputDecoration(
                labelText: 'Name',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _newPlayerRankController,
              decoration: const InputDecoration(
                labelText: 'Rang',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isProcessing ? null : _addNewPlayer,
                child: const Text('Spieler hinzufügen'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlayersTable(List<Player> players) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Spielerliste',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                columns: const [
                  DataColumn(label: Text('ID')),
                  DataColumn(label: Text('Name')),
                  DataColumn(label: Text('Rang')),
                  DataColumn(label: Text('Aktionen')),
                ],
                rows: players.map((player) {
                  if (_editingPlayerId == player.id) {
                    return _buildEditingRow(player);
                  } else {
                    return _buildPlayerRow(player);
                  }
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  DataRow _buildPlayerRow(Player player) {
    return DataRow(
      cells: [
        DataCell(Text(player.id.toString())),
        DataCell(Text(player.name)),
        DataCell(Text(player.rank.toString())),
        DataCell(
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              IconButton(
                icon: const Icon(Icons.edit, color: Colors.blue),
                onPressed: _isProcessing ? null : () => _editPlayer(player),
              ),
              IconButton(
                icon: const Icon(Icons.delete, color: Colors.red),
                onPressed: _isProcessing ? null : () => _confirmDeletePlayer(player),
              ),
            ],
          ),
        ),
      ],
    );
  }

  DataRow _buildEditingRow(Player player) {
    return DataRow(
      cells: [
        DataCell(Text(player.id.toString())),
        DataCell(
          TextField(
            controller: TextEditingController(text: _editingPlayerName),
            onChanged: (value) {
              _editingPlayerName = value;
            },
            decoration: const InputDecoration(
              border: InputBorder.none,
            ),
          ),
        ),
        DataCell(
          TextField(
            controller: TextEditingController(text: _editingPlayerRank),
            onChanged: (value) {
              _editingPlayerRank = value;
            },
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              border: InputBorder.none,
            ),
          ),
        ),
        DataCell(
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              IconButton(
                icon: const Icon(Icons.save, color: Colors.green),
                onPressed: _isProcessing ? null : _savePlayer,
              ),
              IconButton(
                icon: const Icon(Icons.cancel, color: Colors.red),
                onPressed: _isProcessing ? null : _cancelEditing,
              ),
            ],
          ),
        ),
      ],
    );
  }
}