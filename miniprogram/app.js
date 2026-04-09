// app.js
const { request } = require('./utils/request');

App({
  globalData: {
    userProfile: null,
    baseUrl: 'https://sugarclaw.top',
    sessionId: '',
  },

  onLaunch() {
    // 生成会话ID
    this.globalData.sessionId = `wx_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

    // 加载用户档案
    this.loadUserProfile();
  },

  async loadUserProfile() {
    try {
      const profile = await request('/api/user/profile', 'GET');
      this.globalData.userProfile = profile;
    } catch (e) {
      console.warn('加载用户档案失败:', e);
    }
  },
});
