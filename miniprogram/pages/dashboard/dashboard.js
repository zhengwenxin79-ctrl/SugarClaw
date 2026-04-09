// pages/dashboard/dashboard.js
const { request } = require('../../utils/request');
const { glucoseLevel, formatTime } = require('../../utils/format');

Page({
  data: {
    currentGlucose: 0,
    currentLevel: { label: '--', cls: '', emoji: '' },
    lastLogTime: '',
    inputGlucose: '',
    selectedMeal: '餐前',
    mealOptions: ['空腹', '早餐前', '早餐后', '午餐前', '午餐后', '晚餐前', '晚餐后', '睡前', '随机'],
    addingLog: false,
    glucoseLog: [],
    analyzing: false,
    result: null,
    cases: [],
    selectedCase: '',
    replaying: false,
    error: '',
  },

  onLoad() {
    this.loadLog();
    this.loadCases();
  },

  onShow() {
    this.loadLog();
  },

  onInputChange(e) {
    this.setData({ inputGlucose: e.detail.value });
  },

  onMealPick(e) {
    this.setData({ selectedMeal: this.data.mealOptions[e.detail.value] });
  },

  async loadLog() {
    try {
      const log = await request('/api/glucose/log?limit=20', 'GET');
      const enriched = (log || []).map(item => ({
        ...item,
        levelCls: glucoseLevel(item.glucose_mmol).cls,
        timeStr: formatTime(item.timestamp),
      }));
      const latest = enriched[0];
      this.setData({
        glucoseLog: enriched,
        currentGlucose: latest ? latest.glucose_mmol : 0,
        currentLevel: latest ? glucoseLevel(latest.glucose_mmol) : { label: '--', cls: '', emoji: '' },
        lastLogTime: latest ? formatTime(latest.timestamp) : '',
      });
    } catch (e) {
      console.warn('加载日志失败', e);
    }
  },

  async loadCases() {
    try {
      const cases = await request('/api/cases', 'GET');
      this.setData({ cases: cases || [] });
    } catch (e) {
      console.warn('加载案例失败', e);
    }
  },

  async addLog() {
    const val = parseFloat(this.data.inputGlucose);
    if (!val || val < 0.5 || val > 35) {
      wx.showToast({ title: '请输入有效血糖值 (0.5–35)', icon: 'none' });
      return;
    }
    this.setData({ addingLog: true, error: '' });
    try {
      await request('/api/glucose/log', 'POST', {
        timestamp: new Date().toISOString(),
        glucose_mmol: val,
        note: this.data.selectedMeal,
      });
      this.setData({ inputGlucose: '' });
      wx.showToast({ title: '记录成功', icon: 'success' });
      await this.loadLog();
    } catch (e) {
      this.setData({ error: e.message });
    } finally {
      this.setData({ addingLog: false });
    }
  },

  async deleteLog(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认删除',
      content: '删除这条血糖记录？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await request(`/api/glucose/log/${id}`, 'DELETE');
            await this.loadLog();
          } catch (err) {
            this.setData({ error: err.message });
          }
        }
      },
    });
  },

  async runAnalysis() {
    const readings = this.data.glucoseLog
      .slice(0, 12)
      .map(r => r.glucose_mmol)
      .reverse();
    if (readings.length < 3) {
      wx.showToast({ title: '至少需要3条记录', icon: 'none' });
      return;
    }
    this.setData({ analyzing: true, error: '' });
    try {
      const result = await request('/api/analyze', 'POST', { readings });
      this.setData({ result });
    } catch (e) {
      this.setData({ error: e.message });
    } finally {
      this.setData({ analyzing: false });
    }
  },

  selectCase(e) {
    this.setData({ selectedCase: e.currentTarget.dataset.id });
  },

  async replayCase() {
    if (!this.data.selectedCase) return;
    this.setData({ replaying: true, error: '' });
    try {
      const result = await request('/api/replay', 'POST', { case_id: this.data.selectedCase });
      this.setData({ result });
      wx.showToast({ title: '回放完成', icon: 'success' });
    } catch (e) {
      this.setData({ error: e.message });
    } finally {
      this.setData({ replaying: false });
    }
  },
});
