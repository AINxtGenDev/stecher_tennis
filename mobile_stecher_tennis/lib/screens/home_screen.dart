import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:loading_animation_widget/loading_animation_widget.dart';

import '../providers/app_provider.dart';
import '../widgets/player_pyramid.dart';
import '../widgets/challenge_form.dart';
import '../widgets/active_challenges.dart';
import '../widgets/blocked_players.dart';
import '../widgets/unavailable_players.dart';
import '../widgets/new_player_challenge.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    // Refresh data on initial load
    Future.microtask(() {
      final provider = Provider.of<AppProvider>(context, listen: false);
      provider.refreshData();
    });
  }

  Future<void> _refreshData() async {
    await Provider.of<AppProvider>(context, listen: false).refreshData();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Tennis-Rangliste 2025'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              Navigator.pushNamed(context, '/db_settings');
            },
          ),
          IconButton(
            icon: const Icon(Icons.admin_panel_settings),
            onPressed: () {
              Navigator.pushNamed(context, '/admin');
            },
          ),
        ],
      ),
      body: Consumer<AppProvider>(
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
                    'Loading player data...',
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

          return RefreshIndicator(
            onRefresh: _refreshData,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: const [
                // Player pyramid visualization
                PlayerPyramid(),

                // Challenge form
                ChallengeForm(),

                // Active challenges section
                ActiveChallenges(),

                // Blocked players section
                BlockedPlayers(),

                // Unavailable players section
                UnavailablePlayers(),

                // New player challenge section
                NewPlayerChallenge(),

                // Footer with contact information
                SizedBox(height: 16),
                _FooterWidget(),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _FooterWidget extends StatelessWidget {
  const _FooterWidget();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Kontaktinformationen',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text('Matthias Stecher'),
            GestureDetector(
              onTap: () {
                // Launch email app
                // You'll need to implement url_launcher functionality here
              },
              child: const Text(
                'matthias.stecher@hpe.com',
                style: TextStyle(
                  color: Colors.blue,
                  decoration: TextDecoration.underline,
                ),
              ),
            ),
            const Text('Mobile: 0664 105 25 56'),
            const SizedBox(height: 16),
            const Text(
              'Rechtliche Informationen',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              '© 2025 Matthias Stecher. Der Inhalt dieser App ist urheberrechtlich geschützt.',
              style: TextStyle(fontSize: 12),
            ),
            const Text(
              'Haftungsausschluss: Keine Haftung für Fehler oder Verzögerungen in den Ranglisten.',
              style: TextStyle(fontSize: 12),
            ),
            const SizedBox(height: 8),
            const Text(
              'Version: 1.0.0 • März 2025',
              style: TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}