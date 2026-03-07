import 'package:flutter/material.dart';
import '../models/analysis_result.dart';

class AgentTraceCard extends StatelessWidget {
  final List<AgentTrace> traces;

  const AgentTraceCard({super.key, required this.traces});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF7FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.account_tree_rounded,
                  color: Colors.grey.shade600, size: 16),
              const SizedBox(width: 6),
              Text(
                'Agent Trace Log',
                style: TextStyle(
                  color: Colors.grey.shade700,
                  fontWeight: FontWeight.w600,
                  fontSize: 12,
                  letterSpacing: 0.3,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ...traces.map((t) => _traceRow(t)),
        ],
      ),
    );
  }

  Widget _traceRow(AgentTrace trace) {
    Color dotColor;
    switch (trace.agent) {
      case 'Regional Dietitian':
        dotColor = const Color(0xFF48BB78);
        break;
      case 'Physiological Analyst':
        dotColor = const Color(0xFF4299E1);
        break;
      case 'Alert System':
        dotColor = const Color(0xFFED8936);
        break;
      case 'Coordinator':
        dotColor = const Color(0xFF9F7AEA);
        break;
      default:
        dotColor = Colors.grey;
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            margin: const EdgeInsets.only(top: 4),
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: dotColor,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      trace.agent,
                      style: TextStyle(
                        color: dotColor,
                        fontWeight: FontWeight.w600,
                        fontSize: 12,
                      ),
                    ),
                    const Spacer(),
                    Text(
                      '${trace.durationMs}ms',
                      style: TextStyle(
                        color: Colors.grey.shade500,
                        fontSize: 10,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  trace.result,
                  style: TextStyle(
                    color: Colors.grey.shade600,
                    fontSize: 11,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
