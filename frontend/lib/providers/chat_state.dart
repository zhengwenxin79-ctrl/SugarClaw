import 'package:flutter/material.dart';
import '../services/api_service.dart';

class ChatMessage {
  String text;
  final bool isUser;
  final DateTime time;

  ChatMessage({required this.text, required this.isUser})
      : time = DateTime.now();
}

class ChatState extends ChangeNotifier {
  final List<ChatMessage> messages = [];
  final List<Map<String, String>> _history = [];
  final ApiService _api = ApiService();
  bool isLoading = false;

  void sendMessage(String text) {
    if (text.trim().isEmpty || isLoading) return;

    // 添加用户消息
    messages.add(ChatMessage(text: text, isUser: true));
    _history.add({'role': 'user', 'content': text});
    isLoading = true;
    notifyListeners();

    // 创建占位 AI 消息，用于流式更新
    final aiMessage = ChatMessage(text: '', isUser: false);
    messages.add(aiMessage);

    _api.sendChat(
      messages: _history,
      onContent: (chunk) {
        aiMessage.text += chunk;
        notifyListeners();
      },
      onThinking: (chunk) {
        // 可选：忽略思考过程，或者后续扩展显示
      },
      onDone: () {
        _history.add({'role': 'assistant', 'content': aiMessage.text});
        isLoading = false;
        notifyListeners();
      },
      onError: (error) {
        aiMessage.text = '抱歉，回复出错了：$error';
        isLoading = false;
        notifyListeners();
      },
    );
  }
}
