import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_provider.dart';

class UnavailablePlayers extends StatelessWidget {
  const UnavailablePlayers({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, provider, child) {
        final unavailablePlayers = provider.unavailablePlayers;

        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Nicht verfügbare Spieler',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                if (unavailablePlayers.isEmpty)
                  const Text(
                    'Alle Spieler sind derzeit verfügbar.',
                    style: TextStyle(
                      fontStyle: FontStyle.italic,
                    ),
                  )
                else
                  ListView.builder(
                    physics: const NeverScrollableScrollPhysics(),
                    shrinkWrap: true,
                    itemCount: unavailablePlayers.length,
                    itemBuilder: (context, index) {
                      final player = unavailablePlayers[index];
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4.0),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              player.name,
                              style: const TextStyle(fontSize: 14),
                            ),
                            Text(
                              'nicht verfügbar seit: ${player.unavailableSince ?? 'N/A'}',
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