// utils/request.js
const app = getApp();

/**
 * 封装 wx.request，返回 Promise
 */
function request(path, method = 'GET', data = null) {
  return new Promise((resolve, reject) => {
    const baseUrl = app.globalData.baseUrl;
    wx.request({
      url: `${baseUrl}${path}`,
      method,
      data: data || undefined,
      header: { 'Content-Type': 'application/json' },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          const msg = (res.data && res.data.detail) ? res.data.detail : `HTTP ${res.statusCode}`;
          reject(new Error(msg));
        }
      },
      fail(err) {
        reject(new Error(err.errMsg || '网络请求失败，请检查连接'));
      },
    });
  });
}

/**
 * SSE 流式请求（使用 enableChunked 分块接收）
 */
function streamRequest(path, data, callbacks) {
  const { onContent, onThinking, onDone, onError } = callbacks;
  const baseUrl = app.globalData.baseUrl;
  let buffer = '';

  const task = wx.request({
    url: `${baseUrl}${path}`,
    method: 'POST',
    data,
    header: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    enableChunked: true,
    responseType: 'text',
    success() {
      onDone && onDone();
    },
    fail(err) {
      onError && onError(err.errMsg || '流式请求失败');
    },
  });

  task.onChunkReceived((res) => {
    try {
      // ArrayBuffer → string
      const decoder = new TextDecoder('utf-8');
      const chunk = decoder.decode(new Uint8Array(res.data));
      buffer += chunk;

      const lines = buffer.split('\n');
      buffer = lines.pop(); // 末行可能不完整，保留下次拼接

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data:')) continue;
        const payload = trimmed.slice(5).trim();
        if (payload === '[DONE]') { onDone && onDone(); return; }
        try {
          const obj = JSON.parse(payload);
          const text = obj.text || obj.content || '';
          if (obj.type === 'thinking') {
            onThinking && onThinking(text);
          } else {
            onContent && onContent(text);
          }
        } catch (_) {
          if (payload) onContent && onContent(payload);
        }
      }
    } catch (e) {
      console.error('SSE chunk parse error:', e);
    }
  });

  return task;
}

module.exports = { request, streamRequest };
