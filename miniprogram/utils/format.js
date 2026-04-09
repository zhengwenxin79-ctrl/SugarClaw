// utils/format.js

/**
 * 血糖等级判断
 */
function glucoseLevel(mmol) {
  if (mmol < 3.0) return { label: '危险低血糖', cls: 'glucose-critical', emoji: '🚨' };
  if (mmol < 3.9) return { label: '低血糖',     cls: 'glucose-low',      emoji: '⚠️' };
  if (mmol <= 10.0) return { label: '正常',      cls: 'glucose-normal',   emoji: '✅' };
  if (mmol <= 13.9) return { label: '偏高',      cls: 'glucose-high',     emoji: '📈' };
  return { label: '危险高血糖', cls: 'glucose-very-high', emoji: '🚨' };
}

/**
 * 风险等级颜色
 */
function riskPillClass(level) {
  const map = {
    low: 'pill-low',
    medium: 'pill-medium',
    high: 'pill-high',
    very_high: 'pill-high',
  };
  return map[level] || 'pill-medium';
}

/**
 * 风险等级中文
 */
function riskLevelText(level) {
  const map = {
    low: '低风险',
    medium: '中等风险',
    high: '高风险',
    very_high: '极高风险',
  };
  return map[level] || level;
}

/**
 * 时间戳格式化
 */
function formatTime(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  const h = String(d.getHours()).padStart(2, '0');
  const m = String(d.getMinutes()).padStart(2, '0');
  return `${h}:${m}`;
}

/**
 * 日期格式化
 */
function formatDate(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}

module.exports = { glucoseLevel, riskPillClass, riskLevelText, formatTime, formatDate };
