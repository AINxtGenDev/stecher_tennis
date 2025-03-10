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
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Spieler-Pyramide',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                _buildLegend(),
                const SizedBox(height: 16),
                _buildPyramid(provider.players),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildLegend() {
    return Wrap(
      spacing: 16,
      runSpacing: 8,
      children: [
        _legendItem(
          color: Colors.orange,
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
          label: 'In Herausforderung',
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
          width: 16,
          height: 16,
          decoration: BoxDecoration(
            color: color,
            border: Border.all(color: borderColor ?? color.darker()),
            borderRadius: BorderRadius.circular(4),
          ),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(fontSize: 12),
        ),
      ],
    );
  }

  Widget _buildPyramid(List<Player> players) {
    // Define the pyramid structure (players per row)
    const List<int> pyramidRows = [1, 2, 3, 4, 5, 6, 7, 8];

    final sortedPlayers = List<Player>.from(players);
    sortedPlayers.sort((a, b) => a.rank.compareTo(b.rank));

    List<Widget> rows = [];
    int playerIndex = 0;

    for (int rowSize in pyramidRows) {
      List<Widget> rowPlayers = [];

      for (int i = 0; i < rowSize; i++) {
        if (playerIndex < sortedPlayers.length) {
          rowPlayers.add(
            Expanded(
              child: PlayerTile(
                player: sortedPlayers[playerIndex],
              ),
            ),
          );
          playerIndex++;
        } else {
          // Empty tile for missing players
          rowPlayers.add(
            const Expanded(
              child: SizedBox(
                height: 80,
                child: Card(
                  color: Colors.grey,
                  child: Center(
                    child: Text('Spieler fehlt', style: TextStyle(color: Colors.white)),
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
      rows.add(const SizedBox(height: 8));
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
        // Show player details or selection for challenge
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${player.name} (Rang ${player.rank}) ausgewählt'),
            duration: const Duration(seconds: 1),
          ),
        );
      },
      child: Container(
        height: 80,
        margin: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: _getPlayerColor(),
          borderRadius: BorderRadius.circular(8),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.1),
              spreadRadius: 1,
              blurRadius: 3,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Stack(
          children: [
            // Player information
            Center(
              child: Padding(
                padding: const EdgeInsets.all(4.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      'Rang ${player.rank}',
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      player.name,
                      textAlign: TextAlign.center,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12),
                    ),
                  ],
                ),
              ),
            ),

            // Availability toggle button
            Positioned(
              top: 4,
              right: 4,
              child: GestureDetector(
                onTap: () {
                  // Toggle player availability
                  final provider = Provider.of<AppProvider>(context, listen: false);
                  provider.toggleAvailability(player.id);
                },
                child: Container(
                  width: 12,
                  height: 12,
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

    if (isHighlighted) {
      return Colors.green.shade200;
    }

    if (isOpponent) {
      return Colors.red.shade200;
    }

    return Colors.orange.shade200;
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