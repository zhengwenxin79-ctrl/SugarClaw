class PubMedArticle {
  final String pmid;
  final String title;
  final String authors;
  final String journal;
  final String pubdate;
  final String url;

  PubMedArticle({
    required this.pmid,
    required this.title,
    required this.authors,
    required this.journal,
    required this.pubdate,
    required this.url,
  });

  factory PubMedArticle.fromJson(Map<String, dynamic> json) {
    return PubMedArticle(
      pmid: json['pmid'] ?? '',
      title: json['title'] ?? '',
      authors: json['authors'] ?? '',
      journal: json['journal'] ?? '',
      pubdate: json['pubdate'] ?? '',
      url: json['url'] ?? '',
    );
  }
}

class PubMedSearchResult {
  final String query;
  final String mode;
  final int totalCount;
  final List<PubMedArticle> articles;
  final String abstracts;

  PubMedSearchResult({
    required this.query,
    required this.mode,
    required this.totalCount,
    required this.articles,
    this.abstracts = '',
  });

  factory PubMedSearchResult.fromJson(Map<String, dynamic> json) {
    return PubMedSearchResult(
      query: json['query'] ?? '',
      mode: json['mode'] ?? 'custom',
      totalCount: json['total_count'] ?? 0,
      articles: (json['articles'] as List<dynamic>? ?? [])
          .map((e) => PubMedArticle.fromJson(e))
          .toList(),
      abstracts: json['abstracts'] ?? '',
    );
  }
}
