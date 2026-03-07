import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../models/analysis_result.dart';

class GlucoseChart extends StatelessWidget {
  final AnalysisResult result;

  const GlucoseChart({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final chart = result.chartData;
    final historyCount = chart.rawReadings.length;
    final predCount = chart.predictionValues.length;
    final total = historyCount + predCount;

    // Raw readings (grey dots)
    final rawSpots = <FlSpot>[];
    for (int i = 0; i < historyCount; i++) {
      rawSpots.add(FlSpot(i.toDouble(), chart.rawReadings[i]));
    }

    // Filtered readings (blue line)
    final filteredSpots = <FlSpot>[];
    for (int i = 0; i < chart.filteredReadings.length; i++) {
      filteredSpots.add(FlSpot(i.toDouble(), chart.filteredReadings[i]));
    }

    // Predictions (orange dashed)
    final predSpots = <FlSpot>[];
    // Connect from last filtered point
    if (chart.filteredReadings.isNotEmpty) {
      predSpots.add(FlSpot(
        (historyCount - 1).toDouble(),
        chart.filteredReadings.last,
      ));
    }
    for (int i = 0; i < predCount; i++) {
      predSpots.add(FlSpot(
        (historyCount + i).toDouble(),
        chart.predictionValues[i],
      ));
    }

    // CI band (upper)
    final ciHighSpots = <FlSpot>[];
    final ciLowSpots = <FlSpot>[];
    for (int i = 0; i < predCount; i++) {
      final x = (historyCount + i).toDouble();
      ciHighSpots.add(FlSpot(x, chart.ciHigh[i].clamp(0, 25)));
      ciLowSpots.add(FlSpot(x, chart.ciLow[i].clamp(0, 25)));
    }

    return SizedBox(
      height: 280,
      child: Padding(
        padding: const EdgeInsets.only(right: 16, top: 8),
        child: LineChart(
          LineChartData(
            minY: 0,
            maxY: 22,
            minX: 0,
            maxX: (total - 1).toDouble(),
            gridData: FlGridData(
              show: true,
              drawHorizontalLine: true,
              drawVerticalLine: false,
              horizontalInterval: 2,
              getDrawingHorizontalLine: (value) {
                if (value == chart.zones['hypo_warning']! ||
                    value == chart.zones['hyper_warning']!) {
                  return FlLine(
                    color: value < 5
                        ? Colors.red.withAlpha(80)
                        : Colors.orange.withAlpha(80),
                    strokeWidth: 1.5,
                    dashArray: [8, 4],
                  );
                }
                return FlLine(
                  color: Colors.grey.withAlpha(30),
                  strokeWidth: 0.5,
                );
              },
            ),
            titlesData: FlTitlesData(
              leftTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  reservedSize: 40,
                  interval: 4,
                  getTitlesWidget: (value, meta) {
                    return Text(
                      '${value.toInt()}',
                      style: const TextStyle(
                        color: Colors.grey,
                        fontSize: 11,
                      ),
                    );
                  },
                ),
              ),
              bottomTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  reservedSize: 28,
                  interval: 3,
                  getTitlesWidget: (value, meta) {
                    final idx = value.toInt();
                    if (idx < 0 || idx >= total) return const SizedBox.shrink();
                    if (idx < historyCount) {
                      final offset = (historyCount - 1 - idx) * 5;
                      return Text(
                        '-${offset}m',
                        style: const TextStyle(color: Colors.grey, fontSize: 10),
                      );
                    } else {
                      final offset = (idx - historyCount + 1) * 5;
                      return Text(
                        '+${offset}m',
                        style: TextStyle(
                          color: Colors.orange.shade700,
                          fontSize: 10,
                        ),
                      );
                    }
                  },
                ),
              ),
              topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
              rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            ),
            borderData: FlBorderData(show: false),
            // Hypo / target / hyper background zones
            rangeAnnotations: RangeAnnotations(
              horizontalRangeAnnotations: [
                HorizontalRangeAnnotation(
                  y1: 0,
                  y2: chart.zones['hypo_warning']!,
                  color: Colors.red.withAlpha(15),
                ),
                HorizontalRangeAnnotation(
                  y1: chart.zones['target_low']!,
                  y2: chart.zones['target_high']!,
                  color: Colors.green.withAlpha(12),
                ),
                HorizontalRangeAnnotation(
                  y1: chart.zones['hyper_warning']!,
                  y2: 22,
                  color: Colors.orange.withAlpha(15),
                ),
              ],
            ),
            // Vertical line separating history from prediction
            extraLinesData: ExtraLinesData(
              verticalLines: [
                VerticalLine(
                  x: (historyCount - 1).toDouble(),
                  color: Colors.grey.withAlpha(60),
                  strokeWidth: 1,
                  dashArray: [4, 4],
                  label: VerticalLineLabel(
                    show: true,
                    alignment: Alignment.topRight,
                    style: TextStyle(
                      color: Colors.grey.shade600,
                      fontSize: 10,
                    ),
                    labelResolver: (_) => 'now',
                  ),
                ),
              ],
            ),
            lineBarsData: [
              // CI high bound
              if (ciHighSpots.isNotEmpty)
                LineChartBarData(
                  spots: ciHighSpots,
                  isCurved: true,
                  color: Colors.transparent,
                  barWidth: 0,
                  dotData: const FlDotData(show: false),
                  belowBarData: BarAreaData(show: false),
                ),
              // CI band (between low and high)
              if (ciLowSpots.isNotEmpty)
                LineChartBarData(
                  spots: ciHighSpots,
                  isCurved: true,
                  color: Colors.orange.withAlpha(30),
                  barWidth: 0,
                  dotData: const FlDotData(show: false),
                  belowBarData: BarAreaData(
                    show: true,
                    color: Colors.orange.withAlpha(25),
                    cutOffY: 0,
                    applyCutOffY: true,
                  ),
                ),
              // Raw readings (dots only)
              LineChartBarData(
                spots: rawSpots,
                isCurved: false,
                color: Colors.transparent,
                barWidth: 0,
                dotData: FlDotData(
                  show: true,
                  getDotPainter: (spot, percent, barData, index) {
                    return FlDotCirclePainter(
                      radius: 3,
                      color: Colors.grey.shade400,
                      strokeWidth: 0,
                    );
                  },
                ),
              ),
              // Filtered line (solid blue)
              LineChartBarData(
                spots: filteredSpots,
                isCurved: true,
                curveSmoothness: 0.3,
                color: const Color(0xFF2196F3),
                barWidth: 2.5,
                isStrokeCapRound: true,
                dotData: const FlDotData(show: false),
                belowBarData: BarAreaData(
                  show: true,
                  color: const Color(0xFF2196F3).withAlpha(20),
                ),
              ),
              // Prediction line (dashed orange)
              if (predSpots.isNotEmpty)
                LineChartBarData(
                  spots: predSpots,
                  isCurved: true,
                  curveSmoothness: 0.3,
                  color: Colors.orange.shade600,
                  barWidth: 2.5,
                  isStrokeCapRound: true,
                  dashArray: [8, 4],
                  dotData: FlDotData(
                    show: true,
                    getDotPainter: (spot, percent, barData, index) {
                      if (index == 0) {
                        return FlDotCirclePainter(
                          radius: 0,
                          color: Colors.transparent,
                          strokeWidth: 0,
                        );
                      }
                      return FlDotCirclePainter(
                        radius: 3,
                        color: Colors.orange.shade600,
                        strokeWidth: 1.5,
                        strokeColor: Colors.white,
                      );
                    },
                  ),
                ),
            ],
            lineTouchData: LineTouchData(
              touchTooltipData: LineTouchTooltipData(
                getTooltipItems: (spots) {
                  return spots.map((spot) {
                    return LineTooltipItem(
                      '${spot.y.toStringAsFixed(1)} mmol/L',
                      const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    );
                  }).toList();
                },
              ),
            ),
          ),
          duration: const Duration(milliseconds: 600),
          curve: Curves.easeInOut,
        ),
      ),
    );
  }
}
