import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_provider.dart';

class ChallengeForm extends StatefulWidget {
  const ChallengeForm({super.key});

  @override
  State<ChallengeForm> createState() => _ChallengeFormState();
}

class _ChallengeFormState extends State<ChallengeForm> {
  int? _selectedChallengerId;
  int? _selectedOpponentId;
  bool _isLoading = false;
  String? _errorMessage;
  String? _successMessage;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Herausforderung erstellen',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            _buildChallengerDropdown(),
            const SizedBox(height: 12),
            _buildOpponentDropdown(),
            const SizedBox(height: 16),
            _buildSubmitButton(),
            if (_errorMessage != null) ...[
              const SizedBox(height: 8),
              Text(
                _errorMessage!,
                style: const TextStyle(color: Colors.red),
              ),
            ],
            if (_successMessage != null) ...[
              const SizedBox(height: 8),
              Text(
                _successMessage!,
                style: const TextStyle(color: Colors.green),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildChallengerDropdown() {
    final provider = Provider.of<AppProvider>(context);
    final availablePlayers = provider.availablePlayers;

    return DropdownButtonFormField<int>(
      decoration: const InputDecoration(
        labelText: 'Herausforderer',
        border: OutlineInputBorder(),
      ),
      value: _selectedChallengerId,
      hint: const Text('Wählen Sie einen Herausforderer...'),
      isExpanded: true,
      items: availablePlayers.map((player) {
        return DropdownMenuItem<int>(
          value: player.id,
          child: Text('${player.name} (Rang ${player.rank})'),
        );
      }).toList(),
      onChanged: (int? value) {
        setState(() {
          _selectedChallengerId = value;
          _selectedOpponentId = null; // Reset opponent when challenger changes
          _errorMessage = null;
          _successMessage = null;
        });

        if (value != null) {
          provider.fetchEligibleOpponents(value);
        }
      },
    );
  }

  Widget _buildOpponentDropdown() {
    final provider = Provider.of<AppProvider>(context);
    final eligibleOpponents = provider.eligibleOpponents;
    final isLoading = provider.status == LoadingStatus.loading;

    return DropdownButtonFormField<int>(
      decoration: const InputDecoration(
        labelText: 'Gegner',
        border: OutlineInputBorder(),
      ),
      value: _selectedOpponentId,
      hint: Text(
        _selectedChallengerId == null
            ? 'Wählen Sie zuerst einen Herausforderer...'
            : isLoading
            ? 'Lade mögliche Gegner...'
            : eligibleOpponents.isEmpty
            ? 'Keine geeigneten Gegner verfügbar'
            : 'Wählen Sie einen Gegner...',
      ),
      isExpanded: true,
      items: eligibleOpponents.map((player) {
        return DropdownMenuItem<int>(
          value: player.id,
          child: Text('${player.name} (Rang ${player.rank})'),
        );
      }).toList(),
      onChanged: _selectedChallengerId == null || isLoading || eligibleOpponents.isEmpty
          ? null
          : (int? value) {
        setState(() {
          _selectedOpponentId = value;
          _errorMessage = null;
          _successMessage = null;
        });
      },
    );
  }

  Widget _buildSubmitButton() {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: (_selectedChallengerId != null && _selectedOpponentId != null && !_isLoading)
            ? _submitChallenge
            : null,
        child: _isLoading
            ? const SizedBox(
          height: 20,
          width: 20,
          child: CircularProgressIndicator(color: Colors.white),
        )
            : const Text('Herausfordern'),
      ),
    );
  }

  Future<void> _submitChallenge() async {
    if (_selectedChallengerId == null || _selectedOpponentId == null) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
    });

    try {
      final provider = Provider.of<AppProvider>(context, listen: false);
      final challengerId = _selectedChallengerId!;
      final opponentId = _selectedOpponentId!;

      final challenger = provider.findPlayerById(challengerId);
      final opponent = provider.findPlayerById(opponentId);

      if (challenger == null || opponent == null) {
        throw Exception('Spieler nicht gefunden');
      }

      final result = await provider.createChallenge(challengerId, opponentId);

      if (result.containsKey('error')) {
        setState(() {
          _errorMessage = result['error'];
          _isLoading = false;
        });
        return;
      }

      setState(() {
        _successMessage = 'Ich, ${challenger.name} (Rang ${challenger.rank}), fordere hiermit ${opponent.name} (Rang ${opponent.rank}) heraus.';
        _selectedChallengerId = null;
        _selectedOpponentId = null;
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