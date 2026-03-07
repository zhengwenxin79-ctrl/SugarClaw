import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/chat_state.dart';
import 'screens/dashboard_screen.dart';
import 'screens/scale_screen.dart';
import 'screens/chat_screen.dart';

void main() {
  runApp(const SugarClawApp());
}

class SugarClawApp extends StatelessWidget {
  const SugarClawApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => ChatState(),
      child: MaterialApp(
        title: 'SugarClaw',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF6C63FF),
            brightness: Brightness.light,
          ),
          useMaterial3: true,
          scaffoldBackgroundColor: const Color(0xFFF8FAFC),
        ),
        home: const MainShell(),
      ),
    );
  }
}

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _currentIndex = 0;

  final _screens = const [
    DashboardScreen(),
    ChatScreen(),
    ScaleScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: NavigationBar(
        height: 65,
        selectedIndex: _currentIndex,
        onDestinationSelected: (i) => setState(() => _currentIndex = i),
        backgroundColor: Colors.white,
        indicatorColor: const Color(0xFF6C63FF).withAlpha(25),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon:
                Icon(Icons.dashboard_rounded, color: Color(0xFF6C63FF)),
            label: 'Predictor',
          ),
          NavigationDestination(
            icon: Icon(Icons.smart_toy_outlined),
            selectedIcon:
                Icon(Icons.smart_toy_rounded, color: Color(0xFF6C63FF)),
            label: 'SugarClaw',
          ),
          NavigationDestination(
            icon: Icon(Icons.balance_outlined),
            selectedIcon:
                Icon(Icons.balance_rounded, color: Color(0xFFED8936)),
            label: 'Scale',
          ),
        ],
      ),
    );
  }
}
