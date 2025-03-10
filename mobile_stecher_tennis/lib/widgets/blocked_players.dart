import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';

import '../providers/app_provider.dart';

class BlockedPlayers extends StatelessWidget {
  const BlockedPlayers({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, provider, child) {
        final blockedChallengers = provider.blockedChallengers;
        final blockedOpponents = provider.blockedOpponents;

        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Gesperrte Spieler',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 16),

                // Blocked challengers section
                const Text(
                  'Von der Herausforderung ausgeschlossen',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                if (blockedChallengers.isEmpty)
                  const Text(
                    'Keine Spieler von der Herausforderung ausgeschlossen.',
                    style: TextStyle(
                      fontStyle: FontStyle.italic,
                      fontSize: 12,
                    ),
                  )
                else
                  ListView.builder(
                    physics: const NeverScrollableScrollPhysics(),
                    shrinkWrap: true,
                    itemCount: blockedChallengers.length,
                    itemBuilder: (context, index) {
                      final player = blockedChallengers[index];
                      final blockUntil = player.blockChallengerUntil;
                      final untilStr = blockUntil != null
                          ? DateFormat('yyyy-MM-dd').format(blockUntil)
                          : 'Unbekannt';

                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4.0),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(player.name),
                            Text(
                              '- Herausforderer gesperrt bis: $untilStr',
                              style: const TextStyle(
                                fontSize: 12,
                                color: Colors.grey,
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),

                const SizedBox(height: 16),

                // Blocked opponents section
                const Text(
                  'Als Gegner gesperrt',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                if (blockedOpponents.isEmpty)
                  const Text(
                    'Keine Spieler als Gegner gesperrt.',
                    style: TextStyle(
                      fontStyle: FontStyle.italic,
                      fontSize: 12,
                    ),
                  )
                else
                  ListView.builder(
                    physics: const NeverScrollableScrollPhysics(),
                    shrinkWrap: true,
                    itemCount: blockedOpponents.length,
                    itemBuilder: (context, index) {
                      final player = blockedOpponents[index];
                      final blockUntil = player.blockOpponentUntil;
                      final untilStr = blockUntil != null
                          ? DateFormat('yyyy-MM-dd').format(blockUntil)
                          : 'Unbekannt';

                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4.0),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(player.name),
                            Text(
                              '- Gegner gesperrt bis: $untilStr',
                              style: const TextStyle(
                                fontSize: 12,
                                color: Colors.grey,
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}