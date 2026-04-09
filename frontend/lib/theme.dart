import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// SugarClaw Warm Design System — Nature Green × Cream Palette
/// 设计哲学: 像一位陪伴你的朋友，不是冷冰冰的医疗仪器
class SC {
  SC._();

  // ─── 品牌色 (森林绿 × 暖奶油) ──────────────
  static const primary = Color(0xFF3D7D5F);        // 森林绿 (深)
  static const primaryMid = Color(0xFF5A9E7C);      // 鼠尾草绿 (中)
  static const primaryLight = Color(0xFFEBF5EF);    // 薄荷奶油 (背景)
  static const primaryPale = Color(0xFFF4FAF6);     // 极淡绿 (hover)

  static const accent = Color(0xFFE8793A);          // 暖橙 (高亮/CTA)
  static const accentLight = Color(0xFFFDF1E8);     // 暖橙浅

  // ─── 语义色 (情绪抚慰式) ─────────────────
  static const success = Color(0xFF4A9E7A);         // 达标绿
  static const successLight = Color(0xFFE8F5EE);
  static const danger = Color(0xFFD96B5A);          // 暖珊瑚红 / 低血糖
  static const dangerLight = Color(0xFFFDF0EE);
  static const warning = Color(0xFFD4952A);         // 暖琥珀 / 高血糖
  static const warningLight = Color(0xFFFDF6E8);
  static const info = Color(0xFF4A85B8);            // 柔蓝 / 生理Agent
  static const infoLight = Color(0xFFEBF2FA);
  static const purple = Color(0xFF7B5EA7);          // 薰衣草紫 / 协调员
  static const purpleLight = Color(0xFFF2EDF8);

  // ─── 血糖区间色 ──────────────────────────
  static const glucoseHypo = Color(0xFFD96B5A);
  static const glucoseTarget = Color(0xFF4A9E7A);
  static const glucoseHyper = Color(0xFFD4952A);

  // ─── Agent 人格色 ─────────────────────────
  static const agentDietitian = Color(0xFF5A9E7C);  // 营养师 — 鼠尾草绿
  static const agentPhysio = Color(0xFF4A85B8);     // 生理分析师 — 柔蓝
  static const agentAlert = Color(0xFFD4952A);      // 预警系统 — 暖琥珀
  static const agentCoordinator = Color(0xFF7B5EA7);// 协调员 — 薰衣草紫

  // ─── Agent 浅色变体 ─────────────────────────
  static const agentDietitianLight = successLight;
  static const agentPhysioLight = infoLight;
  static const agentAlertLight = warningLight;
  static const agentCoordinatorLight = purpleLight;

  // ─── 中性色 (暖白系) ────────────────────
  static const bg = Color(0xFFFAF8F4);              // 奶油白，去"病房感"
  static const bgWarm = Color(0xFFF5F2EC);          // 更暖的背景
  static const surface = Color(0xFFFFFFFF);
  static const surfaceWarm = Color(0xFFFEFCF8);     // 微暖白卡片
  static const textPrimary = Color(0xFF1E3A2D);     // 深森绿文字
  static const textSecondary = Color(0xFF5A7A68);   // 中灰绿
  static const textTertiary = Color(0xFF9AB5A5);    // 淡灰绿
  static const border = Color(0xFFD8EAE0);          // 绿调边框
  static const borderLight = Color(0xFFEBF3EE);
  static const divider = Color(0xFFF0F5F2);

  // ─── 圆角 ────────────────────────────────
  static const double radiusSm = 10;
  static const double radiusMd = 14;
  static const double radiusLg = 18;
  static const double radiusXl = 24;
  static const double radiusPill = 100;

  // ─── 间距 (8pt 栅格) ─────────────────────
  static const double sp0 = 0;
  static const double sp4 = 4;
  static const double sp8 = 8;
  static const double sp12 = 12;
  static const double sp16 = 16;
  static const double sp20 = 20;
  static const double sp24 = 24;
  static const double sp32 = 32;
  static const double sp40 = 40;
  static const double sp48 = 48;

  // ─── 8pt 栅格辅助常量 ──────────────────────
  static const cardPadding = EdgeInsets.all(16);
  static const sectionPadding = EdgeInsets.symmetric(horizontal: 16);
  static const itemSpacing = SizedBox(height: 8);
  static const sectionSpacing = SizedBox(height: 16);
  static const groupSpacing = SizedBox(height: 24);

  // ─── 阴影 (自然柔和) ─────────────────────
  static List<BoxShadow> get shadowSm => [
        BoxShadow(
          color: const Color(0xFF3D7D5F).withAlpha(10),
          blurRadius: 6,
          offset: const Offset(0, 2),
        ),
      ];

  static List<BoxShadow> get shadowMd => [
        BoxShadow(
          color: const Color(0xFF3D7D5F).withAlpha(14),
          blurRadius: 12,
          offset: const Offset(0, 4),
        ),
      ];

  static List<BoxShadow> get shadowLg => [
        BoxShadow(
          color: const Color(0xFF3D7D5F).withAlpha(20),
          blurRadius: 24,
          offset: const Offset(0, 6),
        ),
      ];

  // ─── 渐变 (自然森林感) ─────────────────────
  static const primaryGradient = LinearGradient(
    colors: [Color(0xFF4A9272), Color(0xFF3D7D5F)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const accentGradient = LinearGradient(
    colors: [Color(0xFFEF8A4A), Color(0xFFE8793A)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  /// 首屏 Hero 渐变 — 晨光森林
  static const heroGradient = LinearGradient(
    colors: [Color(0xFF3D7D5F), Color(0xFF5AA87E)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const calmGradient = LinearGradient(
    colors: [Color(0xFFF4FAF6), Color(0xFFFAF8F4)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  // ─── 排版 5 级体系 ──────────────────────────
  static TextTheme get textTheme => GoogleFonts.interTextTheme();

  static TextStyle get monoStyle => GoogleFonts.jetBrainsMono(
        fontWeight: FontWeight.w700,
      );

  /// Display — 32pt / w800 → 血糖大数字
  static TextStyle get display => GoogleFonts.inter(
        fontSize: 32,
        fontWeight: FontWeight.w800,
        height: 1.1,
        color: textPrimary,
      );

  /// monoDisplay — 32pt JetBrains Mono → 数字专用
  static TextStyle get monoDisplay => GoogleFonts.jetBrainsMono(
        fontSize: 32,
        fontWeight: FontWeight.w700,
        height: 1.1,
        color: textPrimary,
      );

  /// Headline — 18pt / w700 → 区块标题
  static TextStyle get headline => GoogleFonts.inter(
        fontSize: 18,
        fontWeight: FontWeight.w700,
        height: 1.3,
        color: textPrimary,
        letterSpacing: -0.3,
      );

  /// Body — 14pt / w400 → 正文
  static TextStyle get body => GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        height: 1.6,
        color: textPrimary,
      );

  /// Label — 12pt / w500 → 标签/meta
  static TextStyle get label => GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w500,
        height: 1.4,
        color: textSecondary,
      );

  /// Caption — 11pt / w400 → 时间戳/提示
  static TextStyle get caption => GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w400,
        height: 1.3,
        color: textTertiary,
      );

  // ─── 卡片装饰 ────────────────────────────
  static BoxDecoration get card => BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(radiusMd),
        border: Border.all(color: borderLight),
        boxShadow: shadowSm,
      );

  static BoxDecoration get cardWarm => BoxDecoration(
        color: surfaceWarm,
        borderRadius: BorderRadius.circular(radiusMd),
        border: Border.all(color: borderLight),
        boxShadow: shadowSm,
      );

  static BoxDecoration get cardElevated => BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(radiusMd),
        boxShadow: shadowMd,
      );

  static BoxDecoration get cardHero => BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(radiusLg),
        boxShadow: shadowMd,
      );

  // ─── 玻璃态卡片 ──────────────────────────
  static BoxDecoration glassCard({Color? tint}) => BoxDecoration(
        color: (tint ?? surface).withAlpha(220),
        borderRadius: BorderRadius.circular(radiusLg),
        border: Border.all(color: Colors.white.withAlpha(60)),
        boxShadow: shadowSm,
      );

  // ─── 标签/徽章 ────────────────────────────
  static Widget badge(String text, {Color? bg, Color? fg}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg ?? primaryLight,
        borderRadius: BorderRadius.circular(radiusPill),
      ),
      child: Text(
        text,
        style: caption.copyWith(
          fontWeight: FontWeight.w600,
          color: fg ?? primary,
        ),
      ),
    );
  }

  // ─── 渐变按钮 ────────────────────────────
  static Widget gradientButton({
    required String label,
    required VoidCallback? onPressed,
    Gradient? gradient,
    IconData? icon,
    double height = 48,
  }) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        gradient: onPressed != null
            ? (gradient ?? primaryGradient)
            : const LinearGradient(colors: [Color(0xFFCBD5E0), Color(0xFFA0AEC0)]),
        borderRadius: BorderRadius.circular(radiusMd),
        boxShadow: onPressed != null ? shadowSm : [],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onPressed,
          borderRadius: BorderRadius.circular(radiusMd),
          child: Center(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (icon != null) ...[
                  Icon(icon, color: Colors.white, size: 18),
                  const SizedBox(width: 8),
                ],
                Text(
                  label,
                  style: SC.label.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ─── 分节标题 ────────────────────────────
  static Widget sectionHeader(String text, {IconData? icon, Color? color}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          if (icon != null) ...[
            Icon(icon, size: 18, color: color ?? primary),
            const SizedBox(width: 8),
          ],
          Text(
            text,
            style: headline.copyWith(
              fontSize: 16,
              color: color ?? textPrimary,
            ),
          ),
        ],
      ),
    );
  }

  // ─── 统一空状态组件 ──────────────────────────
  static Widget emptyState(
    IconData icon,
    String title, {
    String? subtitle,
    String? ctaLabel,
    VoidCallback? onCta,
  }) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: primaryLight,
                shape: BoxShape.circle,
              ),
              child: Icon(icon, size: 36, color: primaryMid),
            ),
            const SizedBox(height: 20),
            Text(
              title,
              style: headline.copyWith(fontSize: 16, color: textSecondary),
              textAlign: TextAlign.center,
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 8),
              Text(
                subtitle,
                style: body.copyWith(color: textTertiary, fontSize: 13),
                textAlign: TextAlign.center,
              ),
            ],
            if (ctaLabel != null && onCta != null) ...[
              const SizedBox(height: 28),
              SizedBox(
                width: 200,
                child: gradientButton(
                  label: ctaLabel,
                  onPressed: onCta,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  // ─── 按压缩放组件 ─────────────────────────
  static Widget pressable({
    required Widget child,
    VoidCallback? onTap,
    double scaleFactor = 0.96,
  }) {
    return _Pressable(
      onTap: onTap,
      scaleFactor: scaleFactor,
      child: child,
    );
  }
}

/// 按压缩放组件 — 按下 scaleFactor → 松手回弹
class _Pressable extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;
  final double scaleFactor;

  const _Pressable({
    required this.child,
    this.onTap,
    this.scaleFactor = 0.96,
  });

  @override
  State<_Pressable> createState() => _PressableState();
}

class _PressableState extends State<_Pressable>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scale;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 100),
      reverseDuration: const Duration(milliseconds: 200),
    );
    _scale = Tween<double>(begin: 1.0, end: widget.scaleFactor).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => _controller.forward(),
      onTapUp: (_) {
        _controller.reverse();
        widget.onTap?.call();
      },
      onTapCancel: () => _controller.reverse(),
      child: AnimatedBuilder(
        animation: _scale,
        builder: (context, child) => Transform.scale(
          scale: _scale.value,
          child: child,
        ),
        child: widget.child,
      ),
    );
  }
}
