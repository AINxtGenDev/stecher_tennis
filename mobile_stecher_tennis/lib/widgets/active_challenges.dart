import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';

import '../providers/app_provider.dart';

class ActiveChallenges extends StatelessWidget {
  const ActiveChallenges({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AppProvider>(
      builder: (context, provider, child) {
        final activeChallenges = provider.activeChallenges;
        final inChallengePlayers = provider.inChallengePlayers;

        // Temporary solution until we have a proper API endpoint for challenges
        // Create fake challenges based on players who are in challenges
        final List<ChallengeEntry> challengeEntries = [];

        if (inChallengePlayers.isNotEmpty) {
          // Group players by 2 to create challenge pairs
          // This is a simplification, in reality you'd get this data from the backend
          for (int i = 0; i < inChallengePlayers.length; i += 2) {
            if (i + 1 < inChallengePlayers.length) {
              final challenger = inChallengePlayers[i];
              final opponent = inChallengePlayers[i + 1];

              challengeEntries.add(
                ChallengeEntry(
                  challengerName: challenger.name,
                  opponentName: opponent.name,
                  deadline: DateTime.now().add(const Duration(days: 10)),
                ),
              );
            }
          }
        }

        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Aktive Herausforderungen',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                if (challengeEntries.isEmpty && activeChallenges.isEmpty)
                  const Text('Derzeit keine aktiven Herausforderungen.')
                else
                  ListView.separated(
                    physics: const NeverScrollableScrollPhysics(),
                    shrinkWrap: true,
                    itemCount: activeChallenges.isNotEmpty
                        ? activeChallenges.length
                        : challengeEntries.length,
                    separatorBuilder: (context, index) => const Divider(height: 1),
                    itemBuilder: (context, index) {
                      if (activeChallenges.isNotEmpty) {
                        final challenge = activeChallenges[index];
                        return _buildChallengeItem(
                          context,
                          challenge.challengerName,
                          challenge.opponentName,
                          challenge.deadline,
                        );
                      } else {
                        final entry = challengeEntries[index];
                        return _buildChallengeItem(
                          context,
                          entry.challengerName,
                          entry.opponentName,
                          entry.deadline,
                        );
                      }
                    },
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildChallengeItem(
      BuildContext context,
      String challengerName,
      String opponentName,
      DateTime deadline,
      ) {
    final formatter = DateFormat('yyyy-MM-dd');
    final formattedDeadline = formatter.format(deadline);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Text(
              '$challengerName gegen $opponentName',
              style: const TextStyle(fontSize: 14),
            ),
          ),
          Text(
            '(Frist: $formattedDeadline)',
            style: const TextStyle(
              fontSize: 12,
              color: Colors.grey,
            ),
          ),
        ],
      ),
    );
  }
}

// Temporary class to represent a challenge entry
class ChallengeEntry {
  final String challengerName;
  final String opponentName;
  final DateTime deadline;

  ChallengeEntry({
    required this.challengerName,
    required this.opponentName,
    required this.deadline,
  });
}