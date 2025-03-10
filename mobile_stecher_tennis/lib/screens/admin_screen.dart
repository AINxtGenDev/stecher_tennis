import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:loading_animation_widget/loading_animation_widget.dart';

import '../providers/app_provider.dart';
import '../models/challenge.dart';

class AdminScreen extends StatefulWidget {
  const AdminScreen({super.key});

  @override
  State<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends State<AdminScreen> {
  bool _isProcessing = false;
  String? _successMessage;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    // Fetch data on screen load
    _refreshData();
  }

  Future<void> _refreshData() async {
    await Provider.of<AppProvider>(context, listen: false).refreshData();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Administrationsbereich'),
      ),
      body: RefreshIndicator(
        onRefresh: _refreshData,
        child: Consumer<AppProvider>(
          builder: (context, provider, child) {
            if (provider.status == LoadingStatus.loading && !provider.isInitialized) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    LoadingAnimationWidget.staggeredDotsWave(
                      color: Colors.orange,
                      size: 50,
                    ),
                    const SizedBox(height: 24),
                    const Text(
                      'Lade Herausforderungen...',
                      style: TextStyle(fontSize: 16, color: Colors.grey),
                    ),
                  ],
                ),
              );
            }

            if (provider.status == LoadingStatus.error) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(
                      Icons.error_outline,
                      color: Colors.red,
                      size: 60,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Error: ${provider.errorMessage}',
                      style: const TextStyle(color: Colors.red),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: _refreshData,
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              );
            }

            final activeChallenges = provider.activeChallenges;

            // Since we don't have a proper API for challenges yet,
            // let's create a list of mock challenges for demonstration
            final List<Challenge> mockChallenges = [];

            // Use in-challenge players to create mock challenges
            final inChallengePlayers = provider.inChallengePlayers;
            for (int i = 0; i < inChallengePlayers.length - 1; i += 2) {
              final challenger = inChallengePlayers[i];
              final opponent = inChallengePlayers[i + 1];

              mockChallenges.add(
                Challenge(
                  id: i,
                  challengerId: challenger.id,
                  opponentId: opponent.id,
                  challengerName: challenger.name,
                  opponentName: opponent.name,
                  timestamp: DateTime.now().subtract(const Duration(days: 3)),
                  deadline: DateTime.now().add(const Duration(days: 7)),
                  resolved: false,
                ),
              );
            }

            final challenges = activeChallenges.isEmpty ? mockChallenges : activeChallenges;

            if (challenges.isEmpty) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(
                      Icons.check_circle_outline,
                      color: Colors.green,
                      size: 60,
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Derzeit keine ausstehenden Herausforderungen.',
                      style: TextStyle(fontSize: 16),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 24),
                    ElevatedButton(
                      onPressed: _refreshData,
                      child: const Text('Aktualisieren'),
                    ),
                  ],
                ),
              );
            }

            return ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: challenges.length + (_successMessage != null || _errorMessage != null ? 1 : 0),
              itemBuilder: (context, index) {
                if (index == 0 && (_successMessage != null || _errorMessage != null)) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 16.0),
                    child: _buildMessageCard(),
                  );
                }

                final actualIndex = (_successMessage != null || _errorMessage != null) ? index - 1 : index;
                final challenge = challenges[actualIndex];

                return _buildChallengeCard(challenge);
              },
            );
          },
        ),
      ),
    );
  }

  Widget _buildMessageCard() {
    if (_successMessage != null) {
      return Card(
        color: Colors.green.shade100,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              const Icon(Icons.check_circle, color: Colors.green),
              const SizedBox(width: 16),
              Expanded(
                child: Text(_successMessage!),
              ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () {
                  setState(() {
                    _successMessage = null;
                  });
                },
              ),
            ],
          ),
        ),
      );
    } else if (_errorMessage != null) {
      return Card(
        color: Colors.red.shade100,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              const Icon(Icons.error, color: Colors.red),
              const SizedBox(width: 16),
              Expanded(
                child: Text(_errorMessage!),
              ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () {
                  setState(() {
                    _errorMessage = null;
                  });
                },
              ),
            ],
          ),
        ),
      );
    }

    return const SizedBox.shrink();
  }

  Widget _buildChallengeCard(Challenge challenge) {
    final formatter = DateFormat('yyyy-MM-dd');
    final formattedDeadline = formatter.format(challenge.deadline);

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${challenge.challengerName} gegen ${challenge.opponentName}',
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Frist: $formattedDeadline',
              style: const TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 16),
            const Text('Ergebnis:'),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _buildResultButton(
                    '${challenge.challengerName} gewinnt',
                    onPressed: () => _submitResult(challenge.id, 'challenger_wins'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _buildResultButton(
                    '${challenge.opponentName} gewinnt',
                    onPressed: () => _submitResult(challenge.id, 'opponent_wins'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _buildResultButton(
                    'Nicht stattgefunden',
                    onPressed: () => _submitResult(challenge.id, 'not_happened'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResultButton(String label, {required Function() onPressed}) {
    return ElevatedButton(
      onPressed: _isProcessing ? null : onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: Colors.orange,
        padding: const EdgeInsets.symmetric(vertical: 12),
      ),
      child: Text(
        label,
        textAlign: TextAlign.center,
        style: const TextStyle(fontSize: 12),
      ),
    );
  }

  Future<void> _submitResult(int challengeId, String result) async {
    setState(() {
      _isProcessing = true;
      _successMessage = null;
      _errorMessage = null;
    });

    try {
      final provider = Provider.of<AppProvider>(context, listen: false);
      final response = await provider.submitResult(challengeId, result);

      if (response['success'] == true) {
        String resultText;
        switch (result) {
          case 'challenger_wins':
            resultText = 'Herausforderer gewinnt';
            break;
          case 'opponent_wins':
            resultText = 'Gegner gewinnt';
            break;
          case 'not_happened':
            resultText = 'Nicht stattgefunden';
            break;
          default:
            resultText = 'Unbekanntes Ergebnis';
        }

        setState(() {
          _successMessage = 'Ergebnis erfolgreich eingetragen: $resultText';
          _isProcessing = false;
        });
      } else {
        setState(() {
          _errorMessage = response['message'] ?? 'Fehler beim Eintragen des Ergebnisses.';
          _isProcessing = false;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Fehler: $e';
        _isProcessing = false;
      });
    }
  }
}