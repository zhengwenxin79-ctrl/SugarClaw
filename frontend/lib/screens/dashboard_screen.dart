import 'package:flutter/material.dart';
import '../models/analysis_result.dart';
import '../services/api_service.dart';
import '../widgets/glucose_chart.dart';
import '../widgets/alert_card.dart';
import '../widgets/advice_bubble.dart';
import '../widgets/agent_trace_card.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen>
    with SingleTickerProviderStateMixin {
  final _api = ApiService();
  List<CaseInfo> _cases = [];
  AnalysisResult? _result;
  bool _loading = false;
  String? _error;
  late TabController _tabController;

  // Manual input controllers
  final _readingsController = TextEditingController(
    text: '6.2 6.5 6.8 7.3 7.9 8.5',
  );
  final _foodController = TextEditingController();
  String? _selectedEvent;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadCases();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _readingsController.dispose();
    _foodController.dispose();
    super.dispose();
  }

  Future<void> _loadCases() async {
    try {
      final cases = await _api.getCases();
      setState(() => _cases = cases);
    } catch (e) {
      setState(() => _error = 'Cannot connect to server: $e');
    }
  }

  Future<void> _runAnalysis() async {
    final readingsText = _readingsController.text.trim();
    if (readingsText.isEmpty) return;

    final readings = readingsText
        .split(RegExp(r'[\s,]+'))
        .map((s) => double.tryParse(s))
        .where((v) => v != null)
        .cast<double>()
        .toList();

    if (readings.length < 3) {
      setState(() => _error = 'Need at least 3 readings');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final result = await _api.analyze(
        readings: readings,
        event: _selectedEvent,
        food: _foodController.text.isNotEmpty ? _foodController.text : null,
      );
      setState(() {
        _result = result;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _runReplay(String caseId) async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final result = await _api.replayCase(caseId);
      setState(() {
        _result = result;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            // Header
            SliverToBoxAdapter(child: _buildHeader()),
            // Tab bar
            SliverToBoxAdapter(child: _buildTabBar()),
            // Content
            SliverToBoxAdapter(
              child: SizedBox(
                height: _result != null ? 200 : 400,
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    _buildManualInput(),
                    _buildCaseList(),
                  ],
                ),
              ),
            ),
            // Loading
            if (_loading)
              const SliverToBoxAdapter(
                child: Padding(
                  padding: EdgeInsets.all(40),
                  child: Center(
                    child: Column(
                      children: [
                        CircularProgressIndicator(
                          color: Color(0xFF6C63FF),
                        ),
                        SizedBox(height: 16),
                        Text(
                          'SugarClaw agents are analyzing...',
                          style: TextStyle(color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            // Error
            if (_error != null)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(_error!,
                        style: TextStyle(color: Colors.red.shade700, fontSize: 13)),
                  ),
                ),
              ),
            // Results
            if (_result != null && !_loading) ...[
              SliverToBoxAdapter(child: _buildResultHeader()),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: GlucoseChart(result: _result!),
                ),
              ),
              if (_result!.alerts.isNotEmpty)
                SliverToBoxAdapter(child: _buildAlerts()),
              SliverToBoxAdapter(child: _buildAdvice()),
              SliverToBoxAdapter(child: _buildTrace()),
              const SliverToBoxAdapter(child: SizedBox(height: 40)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF6C63FF), Color(0xFF48C6EF)],
              ),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(Icons.bloodtype_rounded,
                color: Colors.white, size: 22),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'SugarClaw',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF1A202C),
                  letterSpacing: -0.5,
                ),
              ),
              Text(
                'Kalman Filter Blood Glucose Predictor',
                style: TextStyle(
                  fontSize: 11,
                  color: Colors.grey.shade500,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTabBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.grey.shade100,
          borderRadius: BorderRadius.circular(12),
        ),
        child: TabBar(
          controller: _tabController,
          indicator: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(10),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withAlpha(15),
                blurRadius: 4,
                offset: const Offset(0, 1),
              ),
            ],
          ),
          indicatorSize: TabBarIndicatorSize.tab,
          dividerHeight: 0,
          labelColor: const Color(0xFF1A202C),
          unselectedLabelColor: Colors.grey.shade500,
          labelStyle: const TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 13,
          ),
          tabs: const [
            Tab(text: 'Manual Input'),
            Tab(text: 'Case Replay'),
          ],
        ),
      ),
    );
  }

  Widget _buildManualInput() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 8),
            Text('CGM Readings (mmol/L, space-separated)',
                style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: Colors.grey.shade700)),
            const SizedBox(height: 6),
            TextField(
              controller: _readingsController,
              decoration: InputDecoration(
                hintText: '6.2 6.5 6.8 7.3 7.9 8.5',
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide(color: Colors.grey.shade200),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide(color: Colors.grey.shade200),
                ),
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              ),
              style: const TextStyle(fontSize: 14, fontFamily: 'monospace'),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Food (optional)',
                          style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: Colors.grey.shade700)),
                      const SizedBox(height: 6),
                      TextField(
                        controller: _foodController,
                        decoration: InputDecoration(
                          hintText: 'e.g. hot dry noodles',
                          filled: true,
                          fillColor: Colors.white,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10),
                            borderSide: BorderSide(color: Colors.grey.shade200),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10),
                            borderSide: BorderSide(color: Colors.grey.shade200),
                          ),
                          contentPadding: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 12),
                        ),
                        style: const TextStyle(fontSize: 14),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Event',
                          style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: Colors.grey.shade700)),
                      const SizedBox(height: 6),
                      Container(
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: Colors.grey.shade200),
                        ),
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<String?>(
                            value: _selectedEvent,
                            isExpanded: true,
                            hint: Text('None',
                                style: TextStyle(
                                    color: Colors.grey.shade400, fontSize: 14)),
                            items: const [
                              DropdownMenuItem(value: null, child: Text('None')),
                              DropdownMenuItem(
                                  value: 'meal', child: Text('Meal')),
                              DropdownMenuItem(
                                  value: 'insulin', child: Text('Insulin')),
                              DropdownMenuItem(
                                  value: 'exercise', child: Text('Exercise')),
                              DropdownMenuItem(
                                  value: 'sleep', child: Text('Sleep')),
                            ],
                            onChanged: (v) =>
                                setState(() => _selectedEvent = v),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                onPressed: _loading ? null : _runAnalysis,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6C63FF),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  elevation: 0,
                ),
                child: const Text(
                  'Launch SugarClaw Agent',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCaseList() {
    if (_cases.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      itemCount: _cases.length,
      itemBuilder: (ctx, i) {
        final c = _cases[i];
        IconData icon;
        Color iconColor;
        switch (c.scenario) {
          case 'meal':
            icon = Icons.restaurant_rounded;
            iconColor = Colors.orange;
            break;
          case 'insulin':
            icon = Icons.vaccines_rounded;
            iconColor = Colors.blue;
            break;
          default:
            icon = Icons.nightlight_round;
            iconColor = Colors.indigo;
        }
        return Card(
          margin: const EdgeInsets.only(bottom: 10),
          elevation: 0,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: _loading ? null : () => _runReplay(c.id),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: iconColor.withAlpha(25),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(icon, color: iconColor, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(c.title,
                            style: const TextStyle(
                                fontWeight: FontWeight.w600, fontSize: 14)),
                        const SizedBox(height: 3),
                        Text(c.description,
                            style: TextStyle(
                                color: Colors.grey.shade600, fontSize: 12),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis),
                      ],
                    ),
                  ),
                  Icon(Icons.play_circle_outline_rounded,
                      color: Colors.grey.shade400),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildResultHeader() {
    final r = _result!;
    Color glucoseColor;
    if (r.currentGlucose < 3.9) {
      glucoseColor = Colors.red;
    } else if (r.currentGlucose > 10.0) {
      glucoseColor = Colors.orange;
    } else {
      glucoseColor = const Color(0xFF48BB78);
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(
            r.currentGlucose.toStringAsFixed(1),
            style: TextStyle(
              fontSize: 48,
              fontWeight: FontWeight.w800,
              color: glucoseColor,
              height: 1,
            ),
          ),
          const SizedBox(width: 6),
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  r.trend,
                  style: TextStyle(fontSize: 24, color: glucoseColor),
                ),
                Text(
                  'mmol/L',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey.shade500,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: const Color(0xFF6C63FF).withAlpha(20),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              r.filterType.toUpperCase(),
              style: const TextStyle(
                color: Color(0xFF6C63FF),
                fontWeight: FontWeight.w700,
                fontSize: 12,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAlerts() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Column(
        children: _result!.alerts.map((a) => AlertCard(alert: a)).toList(),
      ),
    );
  }

  Widget _buildAdvice() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: AdviceBubble(advice: _result!.advice),
    );
  }

  Widget _buildTrace() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: AgentTraceCard(traces: _result!.agentTraces),
    );
  }
}
