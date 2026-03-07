import 'package:flutter/material.dart';
import '../models/analysis_result.dart';

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
        bgColor = const Color(0xFFFDE8E8);
        borderColor = const Color(0xFFE53E3E);
        icon = Icons.warning_rounded;
        break;
      case 'WARNING':
        bgColor = const Color(0xFFFEF5E7);
        borderColor = const Color(0xFFED8936);
        icon = Icons.error_outline_rounded;
        break;
      case 'PREDICTIVE':
        bgColor = const Color(0xFFF0EBFE);
        borderColor = const Color(0xFF805AD5);
        icon = Icons.auto_graph_rounded;
        break;
      default:
        bgColor = Colors.grey.shade100;
        borderColor = Colors.grey;
        icon = Icons.info_outline;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: borderColor.withAlpha(80)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: borderColor, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  alert.level,
                  style: TextStyle(
                    color: borderColor,
                    fontWeight: FontWeight.w700,
                    fontSize: 11,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  alert.message,
                  style: TextStyle(
                    color: Colors.grey.shade800,
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
