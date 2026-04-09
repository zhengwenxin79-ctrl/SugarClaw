import 'package:flutter/material.dart';
import '../models/pubmed_article.dart';
import '../services/api_service.dart';

class PubMedState extends ChangeNotifier {
  final ApiService _api = ApiService();

  PubMedSearchResult? _lastResult;
  List<Map<String, dynamic>> _history = [];
  bool _loading = false;
  String? _error;

  PubMedSearchResult? get lastResult => _lastResult;
  List<Map<String, dynamic>> get history => _history;
  bool get loading => _loading;
  String? get error => _error;

  Future<void> search({
    required String query,
    String mode = 'custom',
    int maxResults = 5,
    bool includeAbstracts = false,
  }) async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _lastResult = await _api.pubmedSearch(
        query: query,
        mode: mode,
        maxResults: maxResults,
        includeAbstracts: includeAbstracts,
      );
    } catch (e) {
      _error = e.toString();
    }
    _loading = false;
    notifyListeners();
  }

  Future<void> loadHistory() async {
    try {
      _history = await _api.pubmedHistory();
    } catch (e) {
      _error = e.toString();
    }
    notifyListeners();
  }
}
