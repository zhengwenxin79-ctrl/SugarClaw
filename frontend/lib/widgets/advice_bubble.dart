import 'package:flutter/material.dart';
import '../theme.dart';

class AdviceBubble extends StatelessWidget {
  final String advice;

  const AdviceBubble({super.key, required this.advice});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: SC.cardPadding,
      decoration: BoxDecoration(
        color: SC.primaryLight,
        borderRadius: BorderRadius.circular(SC.radiusLg),
        border: Border.all(color: SC.primary.withAlpha(30)),
        boxShadow: SC.shadowSm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  gradient: SC.primaryGradient,
                  borderRadius: BorderRadius.circular(SC.radiusMd),
                ),
                child: const Center(
                  child: Text('🌿', style: TextStyle(fontSize: 16)),
                ),
              ),
              const SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'SugarClaw 建议',
                    style: SC.label.copyWith(
                      color: SC.primary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    'AI 个性化分析',
                    style: SC.caption.copyWith(color: SC.textTertiary),
                  ),
                ],
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: SC.primary.withAlpha(15),
                  borderRadius: BorderRadius.circular(SC.radiusPill),
                ),
                child: Text(
                  '● 在线',
                  style: SC.caption.copyWith(
                    color: SC.primary,
                    fontWeight: FontWeight.w600,
                    fontSize: 10,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Container(height: 1, color: SC.primary.withAlpha(20)),
          const SizedBox(height: 12),
          SelectableText(
            advice,
            style: SC.body.copyWith(height: 1.7),
          ),
        ],
      ),
    );
  }
}
