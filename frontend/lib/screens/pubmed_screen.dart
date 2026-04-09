import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../providers/pubmed_state.dart';
import '../theme.dart';

class PubMedScreen extends StatefulWidget {
  const PubMedScreen({super.key});

  @override
  State<PubMedScreen> createState() => _PubMedScreenState();
}

class _PubMedScreenState extends State<PubMedScreen> {
  final _queryCtrl = TextEditingController();
  String _mode = 'custom';
  bool _includeAbstracts = false;

  static const _modes = {
    'custom': '自定义搜索',
    'food-impact': '食物与血糖',
    'therapy': '治疗方案',
    'cgm': 'CGM 研究',
    'mental': '心理健康',
  };

  @override
  void dispose() {
    _queryCtrl.dispose();
    super.dispose();
  }

  Future<void> _search(PubMedState state) async {
    if (_queryCtrl.text.trim().isEmpty) return;
    await state.search(
      query: _queryCtrl.text.trim(),
      mode: _mode,
      maxResults: 5,
      includeAbstracts: _includeAbstracts,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<PubMedState>(
      builder: (context, state, _) {
        return Scaffold(
          backgroundColor: SC.bg,
          appBar: AppBar(
            title: Text('PubMed 文献检索', style: SC.headline.copyWith(color: Colors.white)),
            backgroundColor: SC.primary,
            foregroundColor: Colors.white,
          ),
          body: Column(
            children: [
              _buildSearchBar(state),
              Expanded(
                child: state.loading
                    ? const Center(child: CircularProgressIndicator(color: SC.primary))
                    : state.lastResult != null
                        ? _buildResults(state)
                        : _buildPlaceholder(),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildSearchBar(PubMedState state) {
    return Container(
      padding: SC.cardPadding,
      color: SC.surface,
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _queryCtrl,
                  decoration: InputDecoration(
                    hintText: '输入搜索关键词...',
                    hintStyle: SC.body.copyWith(color: SC.textTertiary),
                    prefixIcon: const Icon(Icons.search, color: SC.textTertiary),
                    border: const OutlineInputBorder(),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  style: SC.body,
                  onSubmitted: (_) => _search(state),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: SC.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                ),
                onPressed: state.loading ? null : () => _search(state),
                child: Text('搜索', style: SC.label.copyWith(color: Colors.white)),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _mode,
                  isExpanded: true,
                  items: _modes.entries
                      .map((e) => DropdownMenuItem(
                          value: e.key,
                          child: Text(e.value, style: SC.body.copyWith(fontSize: 13))))
                      .toList(),
                  onChanged: (v) => setState(() => _mode = v ?? 'custom'),
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    labelText: '搜索模式',
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Checkbox(
                    value: _includeAbstracts,
                    activeColor: SC.primary,
                    onChanged: (v) => setState(() => _includeAbstracts = v ?? false),
                  ),
                  Text('含摘要', style: SC.body.copyWith(fontSize: 13)),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPlaceholder() {
    return SC.emptyState(
      Icons.science_outlined,
      '搜索 PubMed 医学文献',
      subtitle: '输入关键词开始检索',
    );
  }

  Widget _buildResults(PubMedState state) {
    final result = state.lastResult!;
    if (result.articles.isEmpty) {
      return SC.emptyState(
        Icons.search_off_rounded,
        '未找到相关文献',
        subtitle: result.query,
      );
    }
    return ListView(
      padding: SC.cardPadding,
      children: [
        Text(
          '共 ${result.totalCount} 条结果 (显示 ${result.articles.length} 条)',
          style: SC.label.copyWith(color: SC.textSecondary),
        ),
        const SizedBox(height: 12),
        ...result.articles.map((article) => Card(
              margin: const EdgeInsets.only(bottom: 12),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(SC.radiusMd)),
              elevation: 0,
              color: SC.surface,
              child: Container(
                padding: SC.cardPadding,
                decoration: SC.card,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      article.title,
                      style: SC.body.copyWith(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      article.authors,
                      style: SC.label.copyWith(color: SC.textSecondary),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        const Icon(Icons.book_outlined, size: 14, color: SC.textTertiary),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(
                            '${article.journal} (${article.pubdate})',
                            style: SC.caption,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Text(
                          'PMID: ${article.pmid}',
                          style: SC.caption,
                        ),
                        const Spacer(),
                        TextButton.icon(
                          icon: const Icon(Icons.open_in_new, size: 14),
                          label: Text('查看全文', style: SC.label.copyWith(color: SC.primary)),
                          onPressed: () async {
                            final uri = Uri.parse(article.url);
                            if (await canLaunchUrl(uri)) {
                              await launchUrl(uri, mode: LaunchMode.externalApplication);
                            }
                          },
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            )),
        if (state.error != null)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Text(state.error!, style: SC.body.copyWith(color: SC.danger, fontSize: 13)),
          ),
      ],
    );
  }
}
