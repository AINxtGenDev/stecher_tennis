import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_provider.dart';

class NewPlayerChallenge extends StatefulWidget {
  const NewPlayerChallenge({super.key});

  @override
  State<NewPlayerChallenge> createState() => _NewPlayerChallengeState();
}

class _NewPlayerChallengeState extends State<NewPlayerChallenge> {
  final _formKey = GlobalKey<FormState>();
  final _newPlayerNameController = TextEditingController();
  int? _selectedOpponentId;
  bool _isLoading = false;
  String? _errorMessage;
  String? _successMessage;

  @override
  void dispose() {
    _newPlayerNameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Neue Spieler-Herausforderung',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _newPlayerNameController,
                decoration: const InputDecoration(
                  labelText: 'Neuer Spieler',
                  hintText: 'Name eingeben',
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Bitte geben Sie einen Namen ein';
                  }

                  // Check if the name contains at least 5 letters
                  final lettersCount = RegExp(r'[A-Za-z]').allMatches(value).length;
                  if (lettersCount < 5) {
                    return 'Der Name muss mindestens 5 Buchstaben enthalten';
                  }

                  // Check if the name contains any digits
                  if (RegExp(r'\d').hasMatch(value)) {
                    return 'Der Name darf keine Ziffern enthalten';
                  }

                  return null;
                },
                onChanged: (_) {
                  setState(() {
                    _errorMessage = null;
                    _successMessage = null;
                  });
                },
              ),
              const SizedBox(height: 16),
              _buildOpponentDropdown(),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _isFormValid() ? _submitNewPlayerChallenge : null,
                  child: _isLoading
                      ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(color: Colors.white),
                  )
                      : const Text('Neue Spieler-Herausforderung'),
                ),
              ),
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
      ),
    );
  }

  Widget _buildOpponentDropdown() {
    final provider = Provider.of<AppProvider>(context);

    // Filter players for ranks 11-35, available, not in challenge, not blocked as opponent
    final eligibleOpponents = provider.players.where((player) {
      return player.rank >= 11 &&
          player.rank <= 35 &&
          player.available &&
          !player.inChallenge &&
          !player.blockOpponent;
    }).toList();

    return DropdownButtonFormField<int>(
      decoration: const InputDecoration(
        labelText: 'Wählen Sie einen Gegner (Rang 11-35)',
        border: OutlineInputBorder(),
      ),
      value: _selectedOpponentId,
      hint: Text(
        eligibleOpponents.isEmpty
            ? 'Keine geeigneten Gegner verfügbar'
            : 'Bitte auswählen...',
      ),
      isExpanded: true,
      items: eligibleOpponents.map((player) {
        return DropdownMenuItem<int>(
          value: player.id,
          child: Text('${player.name} (Rang ${player.rank})'),
        );
      }).toList(),
      validator: (value) {
        if (value == null) {
          return 'Bitte wählen Sie einen Gegner aus';
        }
        return null;
      },
      onChanged: eligibleOpponents.isEmpty
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

  bool _isFormValid() {
    if (_formKey.currentState == null) return false;
    if (!_formKey.currentState!.validate()) return false;
    if (_selectedOpponentId == null) return false;
    if (_isLoading) return false;

    final newPlayerName = _newPlayerNameController.text.trim();
    if (newPlayerName.isEmpty) return false;

    return true;
  }

  Future<void> _submitNewPlayerChallenge() async {
    if (!_isFormValid()) return;

    // Validate form again to show validation messages
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
    });

    try {
      final provider = Provider.of<AppProvider>(context, listen: false);
      final newPlayerName = _newPlayerNameController.text.trim();
      final opponentId = _selectedOpponentId!;

      final result = await provider.createNewPlayerChallenge(newPlayerName, opponentId);

      if (result.containsKey('error')) {
        setState(() {
          _errorMessage = result['error'];
          _isLoading = false;
        });
        return;
      }

      setState(() {
        _successMessage = result['message'] ?? 'Neue Spieler-Herausforderung erfolgreich erstellt!';
        _newPlayerNameController.clear();
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