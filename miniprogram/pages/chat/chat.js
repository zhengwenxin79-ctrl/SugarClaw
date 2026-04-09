// pages/chat/chat.js
const { request } = require('../../utils/request');
const { formatTime } = require('../../utils/format');
const app = getApp();

Page({
  data: {
    messages: [],
    inputText: '',
    loading: false,
    scrollTarget: 'msg-bottom',
    quickQuestions: [
      '我刚吃完饭血糖 12，怎么处理？',
      '热干面对血糖的影响有多大？',
      '什么运动最适合餐后血糖控制？',
      '空腹血糖 7.2 正常吗？',
    ],
  },

  _history: [],
  _msgId: 0,

  onLoad() {
    this.loadHistory();
  },

  async loadHistory() {
    const sessionId = app.globalData.sessionId;
    try {
      const msgs = await request(`/api/chat/conversation/${sessionId}`, 'GET');
      if (!msgs || msgs.length === 0) return;
      const messages = msgs.map(m => ({
        id: ++this._msgId,
        role: m.role,
        text: m.content,
        thinking: '',
        showThinking: false,
        streaming: false,
        timeStr: formatTime(m.created_at),
      }));
      this._history = msgs.map(m => ({ role: m.role, content: m.content }));
      this.setData({ messages });
      this._scrollBottom();
    } catch (e) {
      console.warn('加载聊天历史失败:', e);
    }
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },

  sendQuick(e) {
    this.setData({ inputText: e.currentTarget.dataset.text });
    this.sendMessage();
  },

  sendMessage() {
    const text = this.data.inputText.trim();
    if (!text || this.data.loading) return;

    const userMsg = {
      id: ++this._msgId,
      role: 'user',
      text,
      thinking: '',
      showThinking: false,
      streaming: false,
      timeStr: formatTime(new Date().toISOString()),
    };
    this._history.push({ role: 'user', content: text });
    const messages = [...this.data.messages, userMsg];
    this.setData({ messages, inputText: '', loading: false });
    this._scrollBottom();

    const aiId = ++this._msgId;
    const aiMsg = {
      id: aiId,
      role: 'assistant',
      text: '',
      thinking: '',
      showThinking: false,
      streaming: true,
      timeStr: formatTime(new Date().toISOString()),
    };
    this.setData({ messages: [...this.data.messages, aiMsg] });

    request('/api/chat', 'POST', { messages: this._history })
      .then((res) => {
        const aiText = res.reply || '';
        this._updateMsg(aiId, { text: aiText, streaming: false });
        this._scrollBottom();
        this._history.push({ role: 'assistant', content: aiText });
        const sessionId = app.globalData.sessionId;
        request('/api/chat/message', 'POST', { session_id: sessionId, role: 'user', content: text }).catch(() => {});
        request('/api/chat/message', 'POST', { session_id: sessionId, role: 'assistant', content: aiText }).catch(() => {});
      })
      .catch((err) => {
        this._updateMsg(aiId, { text: `请求失败：${err.message || err}`, streaming: false });
      });
  },

  _updateMsg(id, patch) {
    const messages = this.data.messages.map(m => m.id === id ? { ...m, ...patch } : m);
    this.setData({ messages });
  },

  _scrollBottom() {
    this.setData({ scrollTarget: 'msg-bottom' });
  },

  toggleThinking(e) {
    const id = e.currentTarget.dataset.id;
    const messages = this.data.messages.map(m =>
      m.id === id ? { ...m, showThinking: !m.showThinking } : m
    );
    this.setData({ messages });
  },
});
