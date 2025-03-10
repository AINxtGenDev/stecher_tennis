# mobile_stecher_tennis

Mobile Tennis Ranking App

## Getting Started

This project is a starting point for a Flutter application.

A few resources to get you started if this is your first Flutter project:

#### Project structure
tennis_ladder/
├── android/            # Android-specific configuration
├── ios/                # iOS-specific configuration
├── lib/
│   ├── main.dart       # Entry point
│   ├── config.dart     # Global configuration
│   ├── models/         # Data models
│   │   ├── player.dart
│   │   ├── challenge.dart
│   ├── services/       # API and Socket services
│   │   ├── api_service.dart
│   │   ├── socket_service.dart
│   ├── providers/      # State management
│   │   ├── app_provider.dart
│   ├── screens/        # Main application screens
│   │   ├── home_screen.dart
│   │   ├── admin_screen.dart
│   │   ├── db_settings_screen.dart
│   ├── widgets/        # Reusable UI components
│   │   ├── player_pyramid.dart
│   │   ├── challenge_form.dart
│   │   ├── active_challenges.dart
│   │   ├── player_list.dart
│   │   └── ...
│   └── utils/          # Utilities and helpers
├── pubspec.yaml        # Dependencies
└── test/               # Tests
