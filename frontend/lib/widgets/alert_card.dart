import 'package:flutter/material.dart';
import '../models/analysis_result.dart';
import '../theme.dart';

class AlertCard extends StatelessWidget {
  final Alert alert;

  const AlertCard({super.key, required this.alert});

  @override
  Widget build(BuildContext context) {
    Color bgColor;
    Color borderColor;
    IconData icon;

    switch (alert.level) {
      case 'CRITICAL':
        bgColor = SC.dangerLight;
        borderColor = SC.danger;
        icon = Icons.info_rounded;
        break;
      case 'WARNING':
        bgColor = SC.warningLight;
        borderColor = SC.warning;
        icon = Icons.error_outline_rounded;
        break;
      case 'PREDICTIVE':
        bgColor = SC.purpleLight;
        borderColor = SC.purple;
        icon = Icons.auto_graph_rounded;
        break;
      default:
        bgColor = SC.borderLight;
        borderColor = SC.textTertiary;
        icon = Icons.info_outline;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(SC.radiusMd),
        border: Border.all(color: borderColor.withAlpha(80)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: borderColor, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  alert.level,
                  style: SC.caption.copyWith(
                    color: borderColor,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 4),
                SelectableText(
                  alert.message,
                  style: SC.body.copyWith(
                    fontSize: 13,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
