import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_provider.dart';

class ChallengeForm extends StatefulWidget {
  const ChallengeForm({super.key});

  @override
  State<ChallengeForm> createState() => _ChallengeFormState();
}

class _ChallengeFormState extends State<ChallengeForm> {
  bool _isLoading = false;
  String? _errorMessage;
  String? _successMessage;

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<AppProvider>(context);
    final selectedChallengerId = provider.selectedChallengerId;
    final selectedOpponentId = provider.selectedOpponentId;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Herausforderung erstellen',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 12),
            _buildChallengerDropdown(provider),
            const SizedBox(height: 8),
            _buildOpponentDropdown(provider),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: (selectedChallengerId != null && selectedOpponentId != null && !_isLoading)
                    ? () => _submitChallenge(provider)
                    : null,
                child: _isLoading
                    ? const SizedBox(
                  height: 18,
                  width: 18,
                  child: CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2,
                  ),
                )
                    : const Text('Herausfordern'),
              ),
            ),
            if (_errorMessage != null) ...[
              const SizedBox(height: 6),
              Text(
                _errorMessage!,
                style: const TextStyle(color: Colors.red, fontSize: 12),
              ),
            ],
            if (_successMessage != null) ...[
              const SizedBox(height: 6),
              Text(
                _successMessage!,
                style: const TextStyle(color: Colors.green, fontSize: 12),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildChallengerDropdown(AppProvider provider) {
    final availablePlayers = provider.availablePlayers;
    final selectedChallengerId = provider.selectedChallengerId;

    return DropdownButtonFormField<int>(
      decoration: const InputDecoration(
        labelText: 'Herausforderer',
        border: OutlineInputBorder(),
      ),
      value: selectedChallengerId,
      hint: const Text('Wählen Sie einen Herausforderer...', style: TextStyle(fontSize: 12)),
      isExpanded: true,
      items: availablePlayers.map((player) {
        return DropdownMenuItem<int>(
          value: player.id,
          child: Text(
              '${player.name} (Rang ${player.rank})',
              style: const TextStyle(fontSize: 12)
          ),
        );
      }).toList(),
      onChanged: (int? value) {
        if (value != null) {
          provider.selectChallenger(value);
          setState(() {
            _errorMessage = null;
            _successMessage = null;
          });
        }
      },
    );
  }

  Widget _buildOpponentDropdown(AppProvider provider) {
    final eligibleOpponents = provider.eligibleOpponents;
    final selectedChallengerId = provider.selectedChallengerId;
    final selectedOpponentId = provider.selectedOpponentId;
    final isLoading = provider.status == LoadingStatus.loading;

    return DropdownButtonFormField<int>(
      decoration: const InputDecoration(
        labelText: 'Gegner',
        border: OutlineInputBorder(),
      ),
      value: selectedOpponentId,
      hint: Text(
        selectedChallengerId == null
            ? 'Wählen Sie zuerst einen Herausforderer...'
            : isLoading
            ? 'Lade mögliche Gegner...'
            : eligibleOpponents.isEmpty
            ? 'Keine geeigneten Gegner verfügbar'
            : 'Wählen Sie einen Gegner...',
        style: const TextStyle(fontSize: 12),
      ),
      isExpanded: true,
      items: eligibleOpponents.map((player) {
        return DropdownMenuItem<int>(
          value: player.id,
          child: Text(
            '${player.name} (Rang ${player.rank})',
            style: const TextStyle(fontSize: 12),
          ),
        );
      }).toList(),
      onChanged: selectedChallengerId == null || isLoading || eligibleOpponents.isEmpty
          ? null
          : (int? value) {
        if (value != null) {
          provider.selectOpponent(value);
          setState(() {
            _errorMessage = null;
            _successMessage = null;
          });
        }
      },
    );
  }

  Future<void> _submitChallenge(AppProvider provider) async {
    final selectedChallengerId = provider.selectedChallengerId;
    final selectedOpponentId = provider.selectedOpponentId;

    if (selectedChallengerId == null || selectedOpponentId == null) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
    });

    try {
      final challenger = provider.findPlayerById(selectedChallengerId);
      final opponent = provider.findPlayerById(selectedOpponentId);

      if (challenger == null || opponent == null) {
        throw Exception('Spieler nicht gefunden');
      }

      final result = await provider.createChallenge(selectedChallengerId, selectedOpponentId);

      if (result.containsKey('error')) {
        setState(() {
          _errorMessage = result['error'];
          _isLoading = false;
        });
        return;
      }

      setState(() {
        _successMessage = 'Ich, ${challenger.name} (Rang ${challenger.rank}), fordere hiermit ${opponent.name} (Rang ${opponent.rank}) heraus.';
        _isLoading = false;
      });

      // Clear success message after 5 seconds
      Future.delayed(const Duration(seconds: 5), () {
        if (mounted) {
          setState(() {
            _successMessage = null;
          });
        }
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Fehler: $e';
        _isLoading = false;
      });
    }
  }
}