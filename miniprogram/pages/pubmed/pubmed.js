// pages/pubmed/pubmed.js
const { request } = require('../../utils/request');

Page({
  data: {
    query: '',
    searching: false,
    articles: [],
    totalCount: 0,
    expandedPmids: {},
    history: [],
    error: '',
    presets: [
      { label: 'GLP-1 疗效', query: 'GLP-1 receptor agonist diabetes efficacy' },
      { label: '低碳饮食', query: 'low carbohydrate diet type 2 diabetes' },
      { label: '运动血糖', query: 'exercise blood glucose control diabetes' },
      { label: 'CGM 预测', query: 'continuous glucose monitoring prediction' },
    ],
  },

  onLoad() {
    this.loadHistory();
  },

  onQueryInput(e) {
    this.setData({ query: e.detail.value });
  },

  usePreset(e) {
    this.setData({ query: e.currentTarget.dataset.query });
    this.doSearch();
  },

  useHistory(e) {
    this.setData({ query: e.currentTarget.dataset.query });
    this.doSearch();
  },

  async loadHistory() {
    try {
      const history = await request('/api/pubmed/history', 'GET');
      this.setData({ history: (history || []).slice(0, 5) });
    } catch (_) {}
  },

  async doSearch() {
    const query = this.data.query.trim();
    if (!query) return;
    this.setData({ searching: true, error: '', articles: [] });
    try {
      const res = await request('/api/pubmed/search', 'POST', {
        query,
        mode: 'custom',
        max_results: 10,
        fetch_abstracts: true,
      });
      this.setData({
        articles: res.articles || [],
        totalCount: res.total_count || 0,
        searching: false,
      });
      this.loadHistory();
    } catch (e) {
      this.setData({ error: e.message, searching: false });
    }
  },

  toggleAbstract(e) {
    const pmid = e.currentTarget.dataset.pmid;
    const expanded = { ...this.data.expandedPmids, [pmid]: !this.data.expandedPmids[pmid] };
    this.setData({ expandedPmids: expanded });
  },

  copyPmid(e) {
    const pmid = e.currentTarget.dataset.pmid;
    wx.setClipboardData({
      data: String(pmid),
      success: () => wx.showToast({ title: 'PMID 已复制', icon: 'success' }),
    });
  },
});
