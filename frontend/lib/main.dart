import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'providers/chat_state.dart';
import 'providers/predictor_state.dart';
import 'providers/user_state.dart';
import 'providers/cgm_state.dart';
import 'providers/pubmed_state.dart';
import 'screens/dashboard_screen.dart';
import 'screens/scale_screen.dart';
import 'screens/chat_screen.dart';
import 'screens/profile_screen.dart';
import 'screens/pubmed_screen.dart';
import 'theme.dart';

void main() {
  runApp(const SugarClawApp());
}

class SugarClawApp extends StatelessWidget {
  const SugarClawApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ChatState()),
        ChangeNotifierProvider(create: (_) => PredictorState()),
        ChangeNotifierProvider(create: (_) => UserState()),
        ChangeNotifierProvider(create: (_) => CGMState()),
        ChangeNotifierProvider(create: (_) => PubMedState()),
      ],
      child: MaterialApp(
        title: 'SugarClaw',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: SC.primary,
            brightness: Brightness.light,
          ),
          useMaterial3: true,
          textTheme: GoogleFonts.interTextTheme(),
          scaffoldBackgroundColor: SC.bg,
          cardTheme: CardTheme(
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(SC.radiusMd),
              side: BorderSide(color: SC.borderLight),
            ),
          ),
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: SC.primaryPale,
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(SC.radiusSm),
              borderSide: BorderSide(color: SC.border),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(SC.radiusSm),
              borderSide: BorderSide(color: SC.border),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(SC.radiusSm),
              borderSide: const BorderSide(color: SC.primary, width: 1.5),
            ),
          ),
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

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _checkOnboarding());
  }

  Future<void> _checkOnboarding() async {
    final userState = context.read<UserState>();
    // 等待初始加载完成
    await Future.doWhile(() async {
      await Future.delayed(const Duration(milliseconds: 100));
      return userState.loading;
    });
    if (!mounted) return;
    if (userState.needsOnboarding) {
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => const _OnboardingWrapper(),
          fullscreenDialog: true,
        ),
      );
      // 引导完成后刷新状态
      if (mounted) context.read<UserState>().loadProfile();
    }
  }

  final _screens = const [
    DashboardScreen(),
    ChatScreen(),
    ScaleScreen(),
  ];

  static const _tabMeta = [
    _TabInfo('今日血糖', '🩸', Icons.water_drop_outlined, Icons.water_drop_rounded, SC.primary),
    _TabInfo('AI 问诊', '🌿', Icons.chat_bubble_outline_rounded, Icons.chat_bubble_rounded, SC.primary),
    _TabInfo('饮食平衡', '⚖️', Icons.balance_outlined, Icons.balance_rounded, SC.accent),
  ];

  String get _greeting {
    final hour = DateTime.now().hour;
    if (hour < 6) return '夜深了，好好休息 🌙';
    if (hour < 10) return '早上好，新的一天 ☀️';
    if (hour < 12) return '上午好，状态怎么样？';
    if (hour < 14) return '午间好，记得吃饭 🍱';
    if (hour < 18) return '下午好，别忘了喝水 💧';
    if (hour < 21) return '晚上好，今天辛苦了';
    return '夜晚好，放松一下吧 🌙';
  }

  @override
  Widget build(BuildContext context) {
    final tab = _tabMeta[_currentIndex];
    return Scaffold(
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(64),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 400),
          curve: Curves.easeInOut,
          decoration: BoxDecoration(
            gradient: _currentIndex == 2 ? SC.accentGradient : SC.heroGradient,
            boxShadow: SC.shadowMd,
          ),
          child: AppBar(
            backgroundColor: Colors.transparent,
            foregroundColor: Colors.white,
            elevation: 0,
            toolbarHeight: 64,
            title: _currentIndex == 0
                ? _buildWelcomeTitle()
                : Row(
                    children: [
                      Text(tab.emoji, style: const TextStyle(fontSize: 20)),
                      const SizedBox(width: 10),
                      Text(
                        tab.label,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.3,
                        ),
                      ),
                    ],
                  ),
            actions: [
              _AppBarAction(
                icon: Icons.science_outlined,
                tooltip: 'PubMed 文献',
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const PubMedScreen()),
                ),
              ),
              _AppBarAction(
                icon: Icons.person_outline_rounded,
                tooltip: '我的档案',
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const ProfileScreen()),
                ),
              ),
              const SizedBox(width: 4),
            ],
          ),
        ),
      ),
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: _buildBottomNav(tab),
    );
  }

  Widget _buildWelcomeTitle() {
    return Consumer<UserState>(
      builder: (context, userState, _) {
        final name = userState.profile?.name ?? '朋友';
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              _greeting,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w400,
                color: Colors.white70,
                height: 1.2,
              ),
            ),
            Text(
              'SugarClaw · $name',
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.3,
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildBottomNav(_TabInfo tab) {
    return Container(
      decoration: BoxDecoration(
        color: SC.surface,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withAlpha(8),
            blurRadius: 12,
            offset: const Offset(0, -3),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 64,
          child: Row(
            children: List.generate(_tabMeta.length, (i) {
              final t = _tabMeta[i];
              final selected = i == _currentIndex;
              return Expanded(
                child: GestureDetector(
                  onTap: () => setState(() => _currentIndex = i),
                  behavior: HitTestBehavior.opaque,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    curve: Curves.easeInOut,
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 4),
                          decoration: BoxDecoration(
                            color: selected
                                ? t.color.withAlpha(20)
                                : Colors.transparent,
                            borderRadius:
                                BorderRadius.circular(SC.radiusPill),
                          ),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                t.emoji,
                                style: TextStyle(
                                  fontSize: selected ? 22 : 20,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          t.label,
                          style: SC.caption.copyWith(
                            color: selected ? t.color : SC.textTertiary,
                            fontWeight: selected
                                ? FontWeight.w600
                                : FontWeight.w400,
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }),
          ),
        ),
      ),
    );
  }
}

class _TabInfo {
  final String label;
  final String emoji;
  final IconData icon;
  final IconData selectedIcon;
  final Color color;
  const _TabInfo(
      this.label, this.emoji, this.icon, this.selectedIcon, this.color);
}

// 首次启动引导页，复用 ProfileScreen，加提示说明
class _OnboardingWrapper extends StatelessWidget {
  const _OnboardingWrapper();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: SC.primary,
        foregroundColor: Colors.white,
        title: const Text('完善你的健康档案', style: TextStyle(fontWeight: FontWeight.w700)),
        automaticallyImplyLeading: false,
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('跳过', style: TextStyle(color: Colors.white70)),
          ),
        ],
      ),
      body: Column(
        children: [
          Container(
            width: double.infinity,
            color: SC.primaryPale,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Text(
              '填写你的基本信息后，SugarClaw 才能给出个性化的血糖建议。\n年龄、体重、糖尿病类型是最关键的三项。',
              style: SC.caption.copyWith(color: SC.textSecondary),
            ),
          ),
          const Expanded(child: ProfileScreen()),
        ],
      ),
    );
  }
}

class _AppBarAction extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final VoidCallback onPressed;
  const _AppBarAction({
    required this.icon,
    required this.tooltip,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(SC.radiusSm),
        child: Container(
          width: 36,
          height: 36,
          margin: const EdgeInsets.symmetric(horizontal: 2),
          decoration: BoxDecoration(
            color: Colors.white.withAlpha(22),
            borderRadius: BorderRadius.circular(SC.radiusSm),
          ),
          child: Icon(icon, size: 20),
        ),
      ),
    );
  }
}
