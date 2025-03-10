import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:loading_animation_widget/loading_animation_widget.dart';

import 'config.dart';
import 'services/api_service.dart';
import 'providers/app_provider.dart';
import 'screens/home_screen.dart';
import 'screens/admin_screen.dart';
import 'screens/db_settings_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  final ApiService _apiService = ApiService();

  MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AppProvider(apiService: _apiService),
      child: MaterialApp(
        title: AppConfig.appName,
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          primarySwatch: Colors.orange,
          colorScheme: ColorScheme.fromSwatch(
            primarySwatch: Colors.orange,
            backgroundColor: const Color(0xFFF5F5F5),
            cardColor: Colors.white,
            errorColor: Colors.red,
          ),
          textTheme: const TextTheme(
            // Heading styles
            headlineMedium: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Colors.black87,
            ),
            // Body text styles
            bodyLarge: TextStyle(fontSize: 14),
            bodyMedium: TextStyle(fontSize: 13),
            bodySmall: TextStyle(fontSize: 11, color: Colors.grey),
          ),
          appBarTheme: const AppBarTheme(
            backgroundColor: Colors.orange,
            foregroundColor: Colors.white,
            elevation: 2,
            titleTextStyle: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          cardTheme: const CardTheme(
            elevation: 3,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.all(Radius.circular(8)),
            ),
            margin: EdgeInsets.symmetric(vertical: 6),
          ),
          elevatedButtonTheme: ElevatedButtonThemeData(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.orange,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              textStyle: const TextStyle(fontSize: 13),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(6),
              ),
            ),
          ),
          inputDecorationTheme: InputDecorationTheme(
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(6),
              borderSide: const BorderSide(color: Colors.grey),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(6),
              borderSide: const BorderSide(color: Colors.orange, width: 2),
            ),
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            labelStyle: const TextStyle(fontSize: 13),
            hintStyle: const TextStyle(fontSize: 12),
          ),
        ),
        home: const SplashScreen(),
        routes: {
          '/home': (context) => const HomeScreen(),
          '/admin': (context) => const AdminScreen(),
          '/db_settings': (context) => const DbSettingsScreen(),
        },
      ),
    );
  }
}

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _initializeApp();
  }

  Future<void> _initializeApp() async {
    final provider = Provider.of<AppProvider>(context, listen: false);

    // Allow the splash screen to be visible for at least 2 seconds
    await Future.wait([
      provider.initialize(),
      Future.delayed(const Duration(seconds: 2)),
    ]);

    if (mounted) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const HomeScreen()),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surface,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              'Tennis Ladder',
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
                color: Colors.orange,
              ),
            ),
            const SizedBox(height: 20),
            LoadingAnimationWidget.staggeredDotsWave(
              color: Colors.orange,
              size: 40,
            ),
            const SizedBox(height: 20),
            const Text(
              'Loading data...',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey,
              ),
            ),
          ],
        ),
      ),
    );
  }
}