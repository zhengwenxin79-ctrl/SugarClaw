// pages/profile/profile.js
const { request } = require('../../utils/request');
const app = getApp();

Page({
  data: {
    form: {
      name: '', age: 0, weight: 0, height: 0,
      diabetes_type: '', regional_preference: '全国',
      isf: 0, icr: 0,
    },
    nameInitial: '?',
    diabetesTypes: ['1型糖尿病', '2型糖尿病', '妊娠糖尿病', '糖尿病前期', '其他'],
    regions: ['全国', '华北', '华东', '华南', '西南', '东北', '西北'],
    saving: false,

    calibBefore: '', calibAfter: '', calibDose: '',
    calibrating: false,

    exportDays: [7, 14, 30, 90],
    selectedExportDays: 30,

    error: '', success: '',
  },

  onLoad() {
    this.loadProfile();
  },

  async loadProfile() {
    try {
      const profile = await request('/api/user/profile', 'GET');
      const form = {
        name: profile.name || '',
        age: profile.age || 0,
        weight: profile.weight || 0,
        height: profile.height || 0,
        diabetes_type: profile.diabetes_type || '',
        regional_preference: profile.regional_preference || '全国',
        isf: profile.isf || 0,
        icr: profile.icr || 0,
      };
      const nameInitial = form.name ? form.name.slice(-1) : '?';
      this.setData({ form, nameInitial });
      app.globalData.userProfile = profile;
    } catch (e) {
      this.setData({ error: e.message });
    }
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field;
    const form = { ...this.data.form, [field]: e.detail.value };
    const nameInitial = form.name ? form.name.slice(-1) : '?';
    this.setData({ form, nameInitial });
  },

  onTypePick(e) {
    const form = { ...this.data.form, diabetes_type: this.data.diabetesTypes[e.detail.value] };
    this.setData({ form });
  },

  onRegionPick(e) {
    const form = { ...this.data.form, regional_preference: this.data.regions[e.detail.value] };
    this.setData({ form });
  },

  onCalibInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({ [field]: e.detail.value });
  },

  async saveProfile() {
    this.setData({ saving: true, error: '', success: '' });
    try {
      const { name, age, weight, height, diabetes_type, regional_preference, isf, icr } = this.data.form;
      await request('/api/user/profile', 'PUT', {
        name, age: Number(age), weight: Number(weight),
        height: Number(height), diabetes_type, regional_preference,
        isf: Number(isf), icr: Number(icr),
      });
      this.setData({ success: '档案已保存', saving: false });
      app.globalData.userProfile = this.data.form;
      setTimeout(() => this.setData({ success: '' }), 2000);
    } catch (e) {
      this.setData({ error: e.message, saving: false });
    }
  },

  async calibrateISF() {
    const before = parseFloat(this.data.calibBefore);
    const after = parseFloat(this.data.calibAfter);
    const dose = parseFloat(this.data.calibDose);
    if (!before || !after || !dose || dose <= 0) {
      wx.showToast({ title: '请填写完整校准数据', icon: 'none' });
      return;
    }
    this.setData({ calibrating: true, error: '' });
    try {
      const res = await request('/api/user/calibrate_isf', 'POST', { before, after, dose });
      const form = { ...this.data.form, isf: res.new_isf };
      this.setData({ form, calibrating: false, success: `ISF 已更新为 ${res.new_isf}` });
      setTimeout(() => this.setData({ success: '' }), 3000);
    } catch (e) {
      this.setData({ error: e.message, calibrating: false });
    }
  },

  onExportDayPick(e) {
    this.setData({ selectedExportDays: this.data.exportDays[e.detail.value] });
  },

  exportCSV() {
    const days = this.data.selectedExportDays;
    const url = `${app.globalData.baseUrl}/api/export/glucose?days=${days}&format=csv`;
    wx.showModal({
      title: '导出血糖数据',
      content: `将导出最近 ${days} 天的血糖记录，在浏览器中打开下载链接`,
      confirmText: '复制链接',
      success: (res) => {
        if (res.confirm) {
          wx.setClipboardData({ data: url, success: () => wx.showToast({ title: '链接已复制', icon: 'success' }) });
        }
      },
    });
  },
});
