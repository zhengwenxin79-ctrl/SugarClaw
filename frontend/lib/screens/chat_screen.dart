import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/chat_state.dart';
import '../providers/predictor_state.dart';
import '../theme.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  final _focusNode = FocusNode();

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  // Agent 人格配色
  static const _agentConfig = <AgentType, _AgentVisual>{
    AgentType.coordinator: _AgentVisual(
      color: SC.agentCoordinator,
      icon: Icons.psychology_rounded,
      label: 'SugarClaw 协调员',
    ),
    AgentType.dietitian: _AgentVisual(
      color: SC.agentDietitian,
      icon: Icons.eco_rounded,
      label: '地域营养师',
    ),
    AgentType.physio: _AgentVisual(
      color: SC.agentPhysio,
      icon: Icons.monitor_heart_rounded,
      label: '生理分析师',
    ),
    AgentType.alert: _AgentVisual(
      color: SC.agentAlert,
      icon: Icons.notifications_active_rounded,
      label: '预警系统',
    ),
  };

  @override
  Widget build(BuildContext context) {
    return Consumer<ChatState>(
      builder: (context, state, _) {
        if (state.messages.isNotEmpty) {
          _scrollToBottom();
        }
        return Scaffold(
          backgroundColor: SC.bg,
          body: SafeArea(
            child: Column(
              children: [
                _buildHeader(),
                Expanded(
                  child: state.messages.isEmpty
                      ? _buildEmptyState()
                      : _buildMessageList(state),
                ),
                _buildInput(state),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      decoration: BoxDecoration(
        color: SC.surface,
        boxShadow: [
          BoxShadow(
            color: SC.primary.withAlpha(8),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              gradient: SC.primaryGradient,
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Center(
              child: Text('🌿', style: TextStyle(fontSize: 20)),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'SugarClaw',
                  style: SC.headline.copyWith(fontSize: 16),
                ),
                Text(
                  '你的贴身血糖管理伙伴',
                  style: SC.caption,
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: SC.success.withAlpha(25),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.circle, size: 8, color: SC.success),
                const SizedBox(width: 4),
                Text(
                  '在线',
                  style: SC.caption.copyWith(
                    fontWeight: FontWeight.w600,
                    color: SC.success,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: () {
              context.read<ChatState>().clearHistory();
            },
            child: const Icon(
              Icons.delete_outline_rounded,
              size: 20,
              color: SC.textTertiary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              gradient: SC.primaryGradient,
              shape: BoxShape.circle,
              boxShadow: SC.shadowMd,
            ),
            child: const Center(
              child: Text('🌿', style: TextStyle(fontSize: 32)),
            ),
          ),
          const SizedBox(height: 18),
          Text(
            '你好，我是 SugarClaw',
            style: SC.headline.copyWith(fontSize: 20),
          ),
          const SizedBox(height: 8),
          Text(
            '有什么关于血糖的问题，尽管问我～',
            style: SC.body.copyWith(color: SC.textSecondary),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 28),
          // 场景快捷问题
          Wrap(
            spacing: 8,
            runSpacing: 10,
            alignment: WrapAlignment.center,
            children: [
              _quickAction('🍚 餐后血糖高怎么办？'),
              _quickAction('🥦 低GI食物推荐'),
              _quickAction('🏃 运动后血糖变化'),
              _quickAction('💊 什么是胰岛素抵抗？'),
              _quickAction('📊 TIR 是什么意思？'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _quickAction(String text) {
    return SC.pressable(
      onTap: () {
        final state = context.read<ChatState>();
        final summary = context.read<PredictorState>().buildContextSummary();
        state.sendMessage(text, predictorContext: summary);
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: SC.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: SC.primary.withAlpha(60)),
        ),
        child: Text(
          text,
          style: SC.label.copyWith(
            color: SC.primary,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
    );
  }

  Widget _buildMessageList(ChatState state) {
    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      itemCount: state.messages.length,
      itemBuilder: (context, i) {
        final msg = state.messages[i];
        return _buildBubble(msg);
      },
    );
  }

  Widget _buildBubble(ChatMessage msg) {
    final isUser = msg.isUser;
    final visual = isUser ? null : _agentConfig[msg.agentType];
    final agentColor = visual?.color ?? SC.primary;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.78,
        ),
        margin: const EdgeInsets.only(bottom: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: isUser ? SC.primary : SC.surface,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(16),
                  topRight: const Radius.circular(16),
                  bottomLeft: Radius.circular(isUser ? 16 : 4),
                  bottomRight: Radius.circular(isUser ? 4 : 16),
                ),
                border: isUser
                    ? null
                    : Border.all(color: agentColor.withAlpha(40)),
                boxShadow: [
                  BoxShadow(
                    color: (isUser ? SC.primary : agentColor).withAlpha(8),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Agent 人格色带 + 标签
                  if (!isUser && visual != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 4,
                            height: 14,
                            decoration: BoxDecoration(
                              color: agentColor,
                              borderRadius: BorderRadius.circular(2),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Icon(visual.icon, size: 12, color: agentColor),
                          const SizedBox(width: 4),
                          Text(
                            visual.label,
                            style: SC.caption.copyWith(
                              fontWeight: FontWeight.w700,
                              color: agentColor,
                            ),
                          ),
                        ],
                      ),
                    ),
                  // 呼吸式打字指示器
                  if (!isUser && msg.text.isEmpty)
                    const _BreathingDots()
                  else
                    SelectableText(
                      msg.text,
                      style: SC.body.copyWith(
                        color: isUser ? Colors.white : SC.textPrimary,
                        height: 1.4,
                      ),
                    ),
                  const SizedBox(height: 4),
                  Align(
                    alignment: Alignment.bottomRight,
                    child: Text(
                      '${msg.time.hour.toString().padLeft(2, '0')}:${msg.time.minute.toString().padLeft(2, '0')}',
                      style: SC.caption.copyWith(
                        fontSize: 9,
                        color: isUser ? Colors.white60 : SC.textTertiary,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInput(ChatState state) {
    return Container(
      padding: EdgeInsets.fromLTRB(
          12, 8, 12, MediaQuery.of(context).viewPadding.bottom + 8),
      decoration: BoxDecoration(
        color: SC.surface,
        boxShadow: [
          BoxShadow(
            color: SC.primary.withAlpha(8),
            blurRadius: 8,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              focusNode: _focusNode,
              enabled: !state.isLoading,
              decoration: InputDecoration(
                hintText: state.isLoading ? '正在思考...' : '问问 SugarClaw...',
                hintStyle: SC.body.copyWith(color: SC.textTertiary),
                filled: true,
                fillColor: SC.bg,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                isDense: true,
              ),
              style: SC.body,
              textInputAction: TextInputAction.send,
              onSubmitted: (text) => _send(state),
            ),
          ),
          const SizedBox(width: 8),
          SC.pressable(
            onTap: state.isLoading ? null : () => _send(state),
            child: Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: state.isLoading
                      ? [SC.textTertiary, SC.textSecondary]
                      : const [SC.primaryMid, SC.primary],
                ),
                borderRadius: BorderRadius.circular(20),
              ),
              child:
                  const Icon(Icons.send_rounded, color: Colors.white, size: 18),
            ),
          ),
        ],
      ),
    );
  }

  void _send(ChatState state) {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    final summary = context.read<PredictorState>().buildContextSummary();
    state.sendMessage(text, predictorContext: summary);
    _controller.clear();
  }
}

// Agent 视觉配置
class _AgentVisual {
  final Color color;
  final IconData icon;
  final String label;
  const _AgentVisual({required this.color, required this.icon, required this.label});
}

// 呼吸式打字指示器 — 3 个序列脉动圆点
class _BreathingDots extends StatefulWidget {
  const _BreathingDots();

  @override
  State<_BreathingDots> createState() => _BreathingDotsState();
}

class _BreathingDotsState extends State<_BreathingDots>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(3, (i) {
        return AnimatedBuilder(
          animation: _controller,
          builder: (context, _) {
            final phase = (_controller.value - i * 0.15) % 1.0;
            final scale = 0.5 + 0.5 * (0.5 + 0.5 * math.sin(phase * 2 * math.pi));
            final opacity = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(phase * 2 * math.pi));
            return Container(
              margin: EdgeInsets.only(right: i < 2 ? 4 : 0),
              child: Transform.scale(
                scale: scale,
                child: Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: SC.primary.withAlpha((opacity * 255).toInt()),
                    shape: BoxShape.circle,
                  ),
                ),
              ),
            );
          },
        );
      }),
    );
  }
}
