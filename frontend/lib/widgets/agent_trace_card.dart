import 'package:flutter/material.dart';
import '../models/analysis_result.dart';
import '../theme.dart';

class AgentTraceCard extends StatelessWidget {
  final List<AgentTrace> traces;

  const AgentTraceCard({super.key, required this.traces});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: SC.bg,
        borderRadius: BorderRadius.circular(SC.radiusMd),
        border: Border.all(color: SC.borderLight),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.account_tree_rounded,
                  color: SC.textSecondary, size: 16),
              const SizedBox(width: 8),
              Text(
                'Agent 追踪日志',
                style: SC.label.copyWith(
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.3,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...traces.map((t) => _traceRow(t)),
        ],
      ),
    );
  }

  Widget _traceRow(AgentTrace trace) {
    Color dotColor;
    switch (trace.agent) {
      case 'Regional Dietitian':
        dotColor = SC.agentDietitian;
        break;
      case 'Physiological Analyst':
        dotColor = SC.agentPhysio;
        break;
      case 'Alert System':
        dotColor = SC.agentAlert;
        break;
      case 'Coordinator':
        dotColor = SC.agentCoordinator;
        break;
      default:
        dotColor = SC.textTertiary;
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
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      trace.agent,
                      style: SC.label.copyWith(
                        color: dotColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const Spacer(),
                    Text(
                      '${trace.durationMs}ms',
                      style: SC.caption.copyWith(
                        fontSize: 10,
                        fontFamily: SC.monoStyle.fontFamily,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                SelectableText(
                  trace.result,
                  style: SC.caption.copyWith(
                    color: SC.textSecondary,
                  ),
                  maxLines: 2,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
