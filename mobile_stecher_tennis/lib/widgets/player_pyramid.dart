import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_provider.dart';
import '../models/player.dart';

class PlayerPyramid extends StatelessWidget {
  const PlayerPyramid({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, provider, child) {
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(12.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Spieler-Pyramide',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 8),
                _buildLegend(),
                const SizedBox(height: 12),
                _buildPyramid(context, provider),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildLegend() {
    return Wrap(
      spacing: 12,
      runSpacing: 6,
      children: [
        _legendItem(
          color: Colors.orange.shade300,
          label: 'Verfügbar',
        ),
        _legendItem(
          color: Colors.green.shade200,
          label: 'Herausforderer',
        ),
        _legendItem(
          color: Colors.red.shade200,
          label: 'Gegner',
        ),
        _legendItem(
          color: Colors.amber.shade200,
          label: 'In Challenge',
        ),
        _legendItem(
          color: Colors.grey.shade300,
          label: 'Gesperrt',
        ),
        _legendItem(
          color: Colors.white,
          label: 'Nicht verfügbar',
          borderColor: Colors.grey.shade400,
        ),
      ],
    );
  }

  Widget _legendItem({
    required Color color,
    required String label,
    Color? borderColor,
  }) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            border: Border.all(color: borderColor ?? color.darker()),
            borderRadius: BorderRadius.circular(3),
          ),
        ),
        const SizedBox(width: 3),
        Text(
          label,
          style: const TextStyle(fontSize: 11),
        ),
      ],
    );
  }

  Widget _buildPyramid(BuildContext context, AppProvider provider) {
    // Define the pyramid structure (players per row)
    const List<int> pyramidRows = [1, 2, 3, 4, 5, 6, 7, 8];

    final sortedPlayers = List<Player>.from(provider.players);
    sortedPlayers.sort((a, b) => a.rank.compareTo(b.rank));

    List<Widget> rows = [];
    int playerIndex = 0;

    for (int rowSize in pyramidRows) {
      List<Widget> rowPlayers = [];

      for (int i = 0; i < rowSize; i++) {
        if (playerIndex < sortedPlayers.length) {
          final player = sortedPlayers[playerIndex];
          final isHighlighted = player.id == provider.selectedChallengerId;
          final isOpponent = player.id == provider.selectedOpponentId;

          rowPlayers.add(
            Expanded(
              child: PlayerTile(
                player: player,
                isHighlighted: isHighlighted,
                isOpponent: isOpponent,
              ),
            ),
          );
          playerIndex++;
        } else {
          // Empty tile for missing players
          rowPlayers.add(
            const Expanded(
              child: SizedBox(
                height: 70,
                child: Card(
                  color: Colors.grey,
                  child: Center(
                    child: Text(
                      'Fehlt',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          );
        }
      }

      rows.add(
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: rowPlayers,
        ),
      );
      rows.add(const SizedBox(height: 6));
    }

    return Column(children: rows);
  }
}

class PlayerTile extends StatelessWidget {
  final Player player;
  final bool isHighlighted;
  final bool isOpponent;

  const PlayerTile({
    super.key,
    required this.player,
    this.isHighlighted = false,
    this.isOpponent = false,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        // Show player details on tap
        _showPlayerDetails(context);
      },
      child: Container(
        height: 70,
        margin: const EdgeInsets.all(3),
        decoration: BoxDecoration(
          color: _getPlayerColor(),
          borderRadius: BorderRadius.circular(6),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withAlpha(26),  // Using withAlpha instead of withOpacity
              spreadRadius: 0.5,
              blurRadius: 2,
              offset: const Offset(0, 1),
            ),
          ],
          // Add a colored border for selected players
          border: isHighlighted || isOpponent
              ? Border.all(
            color: isHighlighted ? Colors.green : Colors.red,
            width: 2,
          )
              : null,
        ),
        child: Stack(
          children: [
            // Player information
            Center(
              child: Padding(
                padding: const EdgeInsets.all(3.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      'Rang ${player.rank}',
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      player.name,
                      textAlign: TextAlign.center,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 10),
                    ),
                  ],
                ),
              ),
            ),

            // Availability toggle button
            Positioned(
              top: 3,
              right: 3,
              child: GestureDetector(
                onTap: () {
                  // Toggle player availability
                  _toggleAvailability(context);
                },
                child: Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                    color: player.available ? Colors.white : Colors.grey.shade300,
                    border: Border.all(
                      color: player.available ? Colors.orange : Colors.grey,
                    ),
                    shape: BoxShape.circle,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showPlayerDetails(BuildContext context) {
    final provider = Provider.of<AppProvider>(context, listen: false);

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(player.name, style: const TextStyle(fontSize: 16)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Rang: ${player.rank}', style: const TextStyle(fontSize: 14)),
            Text('Status: ${player.available ? 'Verfügbar' : 'Nicht verfügbar'}',
                style: const TextStyle(fontSize: 14)),
            if (player.inChallenge)
              const Text('In aktiver Herausforderung',
                  style: TextStyle(fontSize: 14, color: Colors.orange)),
          ],
        ),
        actions: [
          // Select as challenger button
          if (player.available && !player.inChallenge && !player.blockChallenger)
            TextButton(
              onPressed: () {
                provider.selectChallenger(player.id);
                Navigator.of(context).pop();
              },
              child: const Text('Als Herausforderer', style: TextStyle(fontSize: 13)),
            ),

          // Select as opponent button if a challenger is already selected
          if (player.available &&
              !player.inChallenge &&
              !player.blockOpponent &&
              provider.selectedChallengerId != null &&
              provider.selectedChallengerId != player.id)
            TextButton(
              onPressed: () {
                provider.selectOpponent(player.id);
                Navigator.of(context).pop();
              },
              child: const Text('Als Gegner', style: TextStyle(fontSize: 13)),
            ),

          // Cancel button
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
            },
            child: const Text('Schließen', style: TextStyle(fontSize: 13)),
          ),
        ],
      ),
    );
  }

  void _toggleAvailability(BuildContext context) {
    final provider = Provider.of<AppProvider>(context, listen: false);
    provider.toggleAvailability(player.id);
  }

  Color _getPlayerColor() {
    if (!player.available) {
      return Colors.white;
    }

    if (player.inChallenge) {
      if (player.blockChallenger || player.blockOpponent) {
        return Colors.amber.shade100;
      }
      return Colors.amber.shade200;
    }

    if (player.blockChallenger || player.blockOpponent) {
      return Colors.grey.shade300;
    }

    return Colors.orange.shade300;
  }
}

// Extension to get a darker shade of color
extension ColorExtension on Color {
  Color darker([double amount = 0.1]) {
    assert(amount >= 0 && amount <= 1);

    final hsl = HSLColor.fromColor(this);
    final hslDark = hsl.withLightness((hsl.lightness - amount).clamp(0.0, 1.0));

    return hslDark.toColor();
  }
}