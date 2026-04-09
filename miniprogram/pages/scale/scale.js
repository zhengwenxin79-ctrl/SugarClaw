// pages/scale/scale.js
const { request } = require('../../utils/request');
const { riskPillClass, riskLevelText } = require('../../utils/format');

const PRESET_FOODS = ['热干面', '白米饭', '螺蛳粉', '肠粉', '馒头', '面包', '牛奶', '苹果', '红烧肉', '饺子'];

Page({
  data: {
    foodLibrary: [...PRESET_FOODS],
    selectedFoods: {},   // { name: true }
    foodQty: {},         // { name: qty }
    riskDetails: [],
    riskWeight: 0,
    loadingRisk: false,

    solutions: [],
    selectedSolutions: {},  // { index: true }
    balanceWeight: 0,
    loadingBalance: false,
    cobImpact: 0,

    advice: '',
    isBalanced: false,
    tiltDeg: 0,

    searchText: '',
    addingFood: false,
    exerciseName: '',
    exerciseDuration: '20',
    addingExercise: false,
    error: '',
  },

  async toggleFood(e) {
    const name = e.currentTarget.dataset.name;
    const selected = { ...this.data.selectedFoods };

    if (selected[name]) {
      delete selected[name];
      const details = this.data.riskDetails.filter(d => d.name !== name);
      const riskWeight = details.reduce((s, d) => s + d.score, 0);
      this.setData({ selectedFoods: selected, riskDetails: details, riskWeight });
      this._updateTilt(riskWeight, this.data.balanceWeight);
      this._refetchBalance(selected, riskWeight);
      return;
    }

    selected[name] = true;
    this.setData({ selectedFoods: selected, loadingRisk: true, error: '' });

    try {
      const res = await request('/api/scale/risk', 'POST', {
        food_name: name,
        query_time: new Date().toISOString(),
        quantity_multiplier: this.data.foodQty[name] || 1,
      });
      const detail = {
        name,
        score: res.risk_weight,
        level: res.risk_level,
        levelText: riskLevelText(res.risk_level),
      };
      const details = [...this.data.riskDetails.filter(d => d.name !== name), detail];
      const riskWeight = details.reduce((s, d) => s + d.score, 0);
      this.setData({ riskDetails: details, riskWeight, loadingRisk: false });
      this._updateTilt(riskWeight, this.data.balanceWeight);
      await this._refetchBalance(selected, riskWeight);
    } catch (e) {
      delete selected[name];
      this.setData({ selectedFoods: selected, loadingRisk: false, error: e.message });
    }
  },

  async _refetchBalance(selectedFoods, riskWeight) {
    const names = Object.keys(selectedFoods || this.data.selectedFoods);
    if (names.length === 0 || riskWeight <= 0) {
      this.setData({ solutions: [], advice: '', balanceWeight: 0, selectedSolutions: {} });
      return;
    }
    this.setData({ loadingBalance: true, selectedSolutions: {} });
    try {
      const res = await request('/api/scale/balance', 'POST', {
        food_name: names[0],
        risk_weight: riskWeight,
        query_time: new Date().toISOString(),
      });
      this.setData({
        solutions: res.solutions || [],
        advice: res.advice || '',
        cobImpact: res.cob_glucose_impact || 0,
        loadingBalance: false,
      });
    } catch (e) {
      this.setData({ loadingBalance: false, error: e.message });
    }
  },

  async toggleSolution(e) {
    const index = e.currentTarget.dataset.index;
    const selected = { ...this.data.selectedSolutions };
    if (selected[index]) {
      delete selected[index];
    } else {
      selected[index] = true;
    }
    const balanceWeight = Object.keys(selected).reduce((s, i) => {
      return s + (this.data.solutions[parseInt(i)]?.balance_weight || 0);
    }, 0);
    const isBalanced = this.data.riskWeight > 0 && balanceWeight >= this.data.riskWeight;
    this.setData({ selectedSolutions: selected, balanceWeight, isBalanced });
    this._updateTilt(this.data.riskWeight, balanceWeight);
    this._refreshAdvice(selected);
  },

  async _refreshAdvice(selected) {
    if (this.data.solutions.length === 0) return;
    const indices = Object.keys(selected).map(Number);
    try {
      const res = await request('/api/scale/advice', 'POST', {
        food_name: Object.keys(this.data.selectedFoods).join('、'),
        risk_weight: this.data.riskWeight,
        selected_indices: indices,
        all_solutions: this.data.solutions,
        query_time: new Date().toISOString(),
      });
      this.setData({ advice: res.advice || this.data.advice });
    } catch (_) {}
  },

  _updateTilt(risk, balance) {
    const diff = risk - balance;
    const maxTilt = 15;
    const tiltDeg = Math.max(-maxTilt, Math.min(maxTilt, diff * 0.3));
    this.setData({ tiltDeg });
  },

  onSearchInput(e) {
    this.setData({ searchText: e.detail.value });
  },

  async addCustomFood() {
    const name = this.data.searchText.trim();
    if (!name) return;
    if (!this.data.foodLibrary.includes(name)) {
      this.setData({ foodLibrary: [name, ...this.data.foodLibrary], searchText: '' });
    }
    const fakeEvent = { currentTarget: { dataset: { name } } };
    await this.toggleFood(fakeEvent);
  },

  async addFoodToCounter(e) {
    const name = e.currentTarget.dataset.name;
    this.setData({ addingFood: true, error: '' });
    try {
      const solution = await request('/api/scale/add_food_counter', 'POST', {
        food_name: name,
        risk_weight: this.data.riskWeight,
      });
      const solutions = [...this.data.solutions, solution];
      const balanceWeight = this.data.balanceWeight + solution.balance_weight;
      const isBalanced = this.data.riskWeight > 0 && balanceWeight >= this.data.riskWeight;
      this.setData({ solutions, balanceWeight, isBalanced, addingFood: false });
      this._updateTilt(this.data.riskWeight, balanceWeight);
      wx.showToast({ title: `已加入右盘`, icon: 'success', duration: 1500 });
    } catch (err) {
      this.setData({ addingFood: false, error: err.message });
      wx.showToast({ title: err.message || '添加失败', icon: 'none', duration: 2500 });
    }
  },

  onExerciseInput(e) { this.setData({ exerciseName: e.detail.value }); },
  onDurationInput(e) { this.setData({ exerciseDuration: e.detail.value }); },

  async addExercise() {
    const name = this.data.exerciseName.trim();
    const duration = parseInt(this.data.exerciseDuration) || 20;
    if (!name) return;
    this.setData({ addingExercise: true });
    try {
      const solution = await request('/api/scale/add_exercise', 'POST', {
        exercise_name: name,
        duration_min: duration,
        risk_weight: this.data.riskWeight,
      });
      const solutions = [...this.data.solutions, solution];
      this.setData({ solutions, exerciseName: '', addingExercise: false });
    } catch (e) {
      this.setData({ error: e.message, addingExercise: false });
    }
  },
});
