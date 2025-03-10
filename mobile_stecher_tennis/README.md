# Mobile Stecher Tennis

A Flutter-based mobile application for tennis ranking management.

## 📋 Overview

Mobile Stecher Tennis is a comprehensive app designed to manage tennis challenges, track player rankings, and visualize the ranking pyramid. Perfect for tennis clubs and communities looking to organize competitive play.

## 🏗️ Project Structure

```
mobile_stecher_tennis/
├── android/            # Android-specific configuration
├── ios/                # iOS-specific configuration
├── lib/
│   ├── main.dart       # Application entry point
│   ├── config.dart     # Global configuration settings
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
├── pubspec.yaml        # Dependencies and assets
└── test/               # Unit and widget tests
```

## ✨ Features

- Player ranking management
- Challenge creation and tracking
- Visual ranking pyramid
- Administrative tools
- Real-time updates via sockets

## 🧑‍💻 Development

### Prerequisites
- Flutter SDK (latest stable version recommended)
- Dart SDK
- Android Studio or VS Code with Flutter extensions
- iOS development tools (for iOS deployment)

### Setup
1. Clone the repository
2. Navigate to the project directory
3. Run `flutter pub get` to install dependencies
4. Configure your database settings through the app interface

## 📱 Deployment

- For Android: `flutter build apk`
- For iOS: `flutter build ios`

## 🧪 Testing

Run `flutter test` to execute the test suite.

## 📄 License

This project is licensed under the MIT License.
