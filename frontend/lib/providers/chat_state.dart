import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_service.dart';

enum AgentType {
  coordinator,  // 协调员
  dietitian,    // 地域营养师
  physio,       // 生理分析师
  alert,        // 预警系统
  user,         // 用户
}

class ChatMessage {
  String text;
  final bool isUser;
  final DateTime time;
  AgentType agentType;

  ChatMessage({
    required this.text,
    required this.isUser,
    DateTime? time,
    AgentType? agentType,
  })  : time = time ?? DateTime.now(),
        agentType = agentType ?? (isUser ? AgentType.user : AgentType.coordinator);

  Map<String, dynamic> toJson() => {
        'role': isUser ? 'user' : 'assistant',
        'content': text,
        'time': time.toIso8601String(),
      };

  factory ChatMessage.fromJson(Map<String, dynamic> json) => ChatMessage(
        text: json['content'] as String,
        isUser: json['role'] == 'user',
        time: DateTime.parse(json['time'] as String),
      );

  /// 从文本关键词检测 Agent 类型
  static AgentType detectAgentType(String text) {
    final lower = text.toLowerCase();
    if (lower.contains('营养') || lower.contains('食物') ||
        lower.contains('gi') || lower.contains('gl') ||
        lower.contains('饮食') || lower.contains('卡路里')) {
      return AgentType.dietitian;
    }
    if (lower.contains('血糖') && (lower.contains('趋势') || lower.contains('预测') ||
        lower.contains('波动') || lower.contains('生理'))) {
      return AgentType.physio;
    }
    if (lower.contains('警告') || lower.contains('危险') ||
        lower.contains('低血糖') || lower.contains('高血糖') ||
        lower.contains('紧急')) {
      return AgentType.alert;
    }
    return AgentType.coordinator;
  }
}

class ChatState extends ChangeNotifier {
  static const _storageKey = 'chat_history';

  final List<ChatMessage> messages = [];
  final List<Map<String, String>> _history = [];
  final ApiService _api = ApiService();
  bool isLoading = false;

  /// Unique session identifier generated once per app run.
  final String _sessionId = DateTime.now().millisecondsSinceEpoch.toString();

  ChatState() {
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    final prefs = await SharedPreferences.getInstance();
    final jsonStr = prefs.getString(_storageKey);
    if (jsonStr == null) return;

    final List<dynamic> list = jsonDecode(jsonStr) as List<dynamic>;
    for (final item in list) {
      final map = item as Map<String, dynamic>;
      messages.add(ChatMessage.fromJson(map));
      _history.add({
        'role': map['role'] as String,
        'content': map['content'] as String,
      });
    }
    notifyListeners();
  }

  Future<void> _saveHistory() async {
    final prefs = await SharedPreferences.getInstance();
    final jsonStr = jsonEncode(messages.map((m) => m.toJson()).toList());
    await prefs.setString(_storageKey, jsonStr);
  }

  void clearHistory() {
    messages.clear();
    _history.clear();
    notifyListeners();
    _saveHistory();
  }

  /// Persist a user+assistant message pair to the backend.
  Future<void> _persistMessages(String userMsg, String assistantMsg) async {
    try {
      await _api.saveMessage(_sessionId, 'user', userMsg);
      await _api.saveMessage(_sessionId, 'assistant', assistantMsg);
    } catch (_) {
      // Persistence failure is non-fatal — local history is already saved.
    }
  }

  /// Load recent conversation history from the backend for this session.
  Future<void> loadHistory() async {
    try {
      final remote = await _api.getConversation(_sessionId);
      if (remote.isEmpty) return;
      messages.clear();
      _history.clear();
      for (final item in remote) {
        messages.add(ChatMessage.fromJson(item));
        _history.add({
          'role': item['role'] as String,
          'content': item['content'] as String,
        });
      }
      notifyListeners();
    } catch (_) {
      // Fall back to local history if backend is unavailable.
    }
  }

  void sendMessage(String text, {String? predictorContext}) {
    if (text.trim().isEmpty || isLoading) return;

    if (predictorContext != null && predictorContext.isNotEmpty) {
      _history.add({'role': 'system', 'content': predictorContext});
    }

    messages.add(ChatMessage(text: text, isUser: true));
    _history.add({'role': 'user', 'content': text});
    isLoading = true;
    notifyListeners();

    final aiMessage = ChatMessage(text: '', isUser: false);
    messages.add(aiMessage);

    _api.sendChat(
      messages: _history,
      onContent: (chunk) {
        aiMessage.text += chunk;
        // 动态检测 agent 类型
        aiMessage.agentType = ChatMessage.detectAgentType(aiMessage.text);
        notifyListeners();
      },
      onThinking: (chunk) {},
      onDone: () {
        _history.add({'role': 'assistant', 'content': aiMessage.text});
        isLoading = false;
        notifyListeners();
        _saveHistory();
        _persistMessages(text, aiMessage.text);
      },
      onError: (error) {
        aiMessage.text = '抱歉，回复出错了：$error';
        isLoading = false;
        notifyListeners();
        _saveHistory();
      },
    );
  }
}
