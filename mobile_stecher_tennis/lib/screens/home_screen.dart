import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:loading_animation_widget/loading_animation_widget.dart';
import 'package:url_launcher/url_launcher.dart';

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
  bool _isExpanded = true;

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
            tooltip: 'Datenbankeinstellungen',
          ),
          IconButton(
            icon: const Icon(Icons.admin_panel_settings),
            onPressed: () {
              Navigator.pushNamed(context, '/admin');
            },
            tooltip: 'Administrationsbereich',
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
                    size: 40,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Lade Spielerdaten...',
                    style: TextStyle(fontSize: 14, color: Colors.grey),
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
                    size: 50,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Fehler: ${provider.errorMessage}',
                    style: const TextStyle(color: Colors.red, fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: _refreshData,
                    child: const Text('Erneut versuchen'),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: _refreshData,
            child: ListView(
              padding: const EdgeInsets.all(12),
              children: [
                // Player pyramid visualization
                const PlayerPyramid(),

                // Challenge form
                const ChallengeForm(),

                // Active challenges section
                const ActiveChallenges(),

                // Expandable sections - collapsible for better space management
                ExpansionPanelList(
                  elevation: 1,
                  expandedHeaderPadding: EdgeInsets.zero,
                  expansionCallback: (int index, bool isExpanded) {
                    setState(() {
                      _isExpanded = !isExpanded;
                    });
                  },
                  children: [
                    ExpansionPanel(
                      headerBuilder: (context, isExpanded) {
                        return Padding(
                          padding: const EdgeInsets.all(8.0),
                          child: Text(
                            'Gesperrte & Nicht verfügbare Spieler',
                            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        );
                      },
                      body: const Column(
                        children: [
                          // Blocked players section
                          BlockedPlayers(),

                          // Unavailable players section
                          UnavailablePlayers(),
                        ],
                      ),
                      isExpanded: _isExpanded,
                    ),
                  ],
                ),

                const SizedBox(height: 10),

                // New player challenge section
                const NewPlayerChallenge(),

                // Footer with contact information
                const SizedBox(height: 10),
                const _FooterWidget(),
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
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Kontaktinformationen',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontSize: 14,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 6),
            const Text('Matthias Stecher', style: TextStyle(fontSize: 12)),
            GestureDetector(
              onTap: () {
                _launchEmail('matthias.stecher@hpe.com');
              },
              child: const Text(
                'matthias.stecher@hpe.com',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.blue,
                  decoration: TextDecoration.underline,
                ),
              ),
            ),
            const Text('Mobile: 0664 105 25 56', style: TextStyle(fontSize: 12)),
            const SizedBox(height: 10),
            Text(
              'Rechtliche Informationen',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontSize: 13,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              '© 2025 Matthias Stecher. Der Inhalt dieser App ist urheberrechtlich geschützt.',
              style: TextStyle(fontSize: 10),
            ),
            const Text(
              'Haftungsausschluss: Keine Haftung für Fehler oder Verzögerungen in den Ranglisten.',
              style: TextStyle(fontSize: 10),
            ),
            const SizedBox(height: 6),
            const Center(
              child: Text(
                'Version: 1.0.0 • März 2025',
                style: TextStyle(fontSize: 10, fontStyle: FontStyle.italic),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _launchEmail(String emailAddress) async {
    final Uri emailLaunchUri = Uri(
      scheme: 'mailto',
      path: emailAddress,
    );

    try {
      await launchUrl(emailLaunchUri);
    } catch (e) {
      // Handle error - could not launch email app
      debugPrint('Could not launch email: $e');
    }
  }
}