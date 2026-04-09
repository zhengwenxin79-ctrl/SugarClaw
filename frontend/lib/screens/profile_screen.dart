import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/user_state.dart';
import '../theme.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _nameCtrl = TextEditingController();
  final _ageCtrl = TextEditingController();
  final _weightCtrl = TextEditingController();
  final _heightCtrl = TextEditingController();
  final _isfCtrl = TextEditingController();
  final _icrCtrl = TextEditingController();
  final _medsCtrl = TextEditingController();
  String _diabetesType = '';
  String _region = '全国';

  // ISF 校准
  final _calBeforeCtrl = TextEditingController();
  final _calAfterCtrl = TextEditingController();
  final _calDoseCtrl = TextEditingController();

  bool _initialized = false;

  static const _diabetesTypes = ['', 'T1DM', 'T2DM', 'GDM', '其他'];
  static const _regions = [
    '全国', '北方', '南方', '华东', '华南', '华北', '东北',
    '西南', '西北', '湖北', '湖南', '广东', '广西', '四川',
    '重庆', '云南', '贵州', '江苏', '浙江', '福建', '上海',
    '北京', '天津', '山东', '河南', '海南', '新疆', '内蒙古',
  ];

  void _populateFields(UserState state) {
    if (_initialized || state.profile == null) return;
    final p = state.profile!;
    _nameCtrl.text = p.name;
    _ageCtrl.text = p.age > 0 ? p.age.toString() : '';
    _weightCtrl.text = p.weight > 0 ? p.weight.toString() : '';
    _heightCtrl.text = p.height > 0 ? p.height.toString() : '';
    _isfCtrl.text = p.isf > 0 ? p.isf.toString() : '';
    _icrCtrl.text = p.icr > 0 ? p.icr.toString() : '';
    _medsCtrl.text = p.medications.join(', ');
    _diabetesType = p.diabetesType;
    _region = p.regionalPreference;
    _initialized = true;
  }

  Future<void> _save(UserState state) async {
    final fields = <String, dynamic>{};
    if (_nameCtrl.text.isNotEmpty) fields['name'] = _nameCtrl.text;
    if (_ageCtrl.text.isNotEmpty) fields['age'] = int.tryParse(_ageCtrl.text) ?? 0;
    if (_weightCtrl.text.isNotEmpty) fields['weight'] = double.tryParse(_weightCtrl.text) ?? 0;
    if (_heightCtrl.text.isNotEmpty) fields['height'] = double.tryParse(_heightCtrl.text) ?? 0;
    if (_isfCtrl.text.isNotEmpty) fields['isf'] = double.tryParse(_isfCtrl.text) ?? 0;
    if (_icrCtrl.text.isNotEmpty) fields['icr'] = double.tryParse(_icrCtrl.text) ?? 0;
    if (_medsCtrl.text.isNotEmpty) {
      fields['medications'] = _medsCtrl.text.split(',').map((s) => s.trim()).where((s) => s.isNotEmpty).toList();
    } else {
      fields['medications'] = <String>[];
    }
    fields['diabetes_type'] = _diabetesType;
    fields['regional_preference'] = _region;
    await state.updateProfile(fields);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('档案已保存'), duration: Duration(seconds: 1)),
      );
    }
  }

  Future<void> _calibrate(UserState state) async {
    final before = double.tryParse(_calBeforeCtrl.text);
    final after = double.tryParse(_calAfterCtrl.text);
    final dose = double.tryParse(_calDoseCtrl.text);
    if (before == null || after == null || dose == null || dose <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请填写有效的校准数据')),
      );
      return;
    }
    final result = await state.calibrateISF(before: before, after: after, dose: dose);
    if (result != null && mounted) {
      _isfCtrl.text = result['new_isf'].toString();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('ISF 已更新: ${result['previous_isf']} → ${result['new_isf']}'),
          duration: const Duration(seconds: 2),
        ),
      );
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _ageCtrl.dispose();
    _weightCtrl.dispose();
    _heightCtrl.dispose();
    _isfCtrl.dispose();
    _icrCtrl.dispose();
    _medsCtrl.dispose();
    _calBeforeCtrl.dispose();
    _calAfterCtrl.dispose();
    _calDoseCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<UserState>(
      builder: (context, state, _) {
        _populateFields(state);
        return Scaffold(
          backgroundColor: SC.bg,
          appBar: AppBar(
            title: Text('用户档案', style: SC.headline.copyWith(color: Colors.white)),
            backgroundColor: SC.primary,
            foregroundColor: Colors.white,
            actions: [
              IconButton(
                icon: const Icon(Icons.save),
                onPressed: state.loading ? null : () => _save(state),
              ),
            ],
          ),
          body: state.loading && state.profile == null
              ? const Center(child: CircularProgressIndicator(color: SC.primary))
              : SingleChildScrollView(
                  padding: SC.cardPadding,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _sectionTitle('基本信息'),
                      _textField('姓名', _nameCtrl),
                      Row(children: [
                        Expanded(child: _textField('年龄', _ageCtrl, numeric: true)),
                        const SizedBox(width: 12),
                        Expanded(child: _textField('体重 (kg)', _weightCtrl, numeric: true)),
                        const SizedBox(width: 12),
                        Expanded(child: _textField('身高 (cm)', _heightCtrl, numeric: true)),
                      ]),
                      const SizedBox(height: 12),
                      _dropdownField('糖尿病类型', _diabetesType, _diabetesTypes, (v) {
                        setState(() => _diabetesType = v ?? '');
                      }),
                      _dropdownField('地域偏好', _region, _regions, (v) {
                        setState(() => _region = v ?? '全国');
                      }),
                      _textField('用药 (逗号分隔)', _medsCtrl),
                      const Divider(height: 32, color: SC.divider),
                      _sectionTitle('胰岛素参数'),
                      Row(children: [
                        Expanded(child: _textField('ISF (mmol/L per U)', _isfCtrl, numeric: true)),
                        const SizedBox(width: 12),
                        Expanded(child: _textField('ICR (g carb per U)', _icrCtrl, numeric: true)),
                      ]),
                      const Divider(height: 32, color: SC.divider),
                      _sectionTitle('ISF 自适应校准'),
                      Text(
                        '输入一次餐前/餐后血糖和胰岛素剂量，系统将用 EMA 更新 ISF',
                        style: SC.body.copyWith(fontSize: 13, color: SC.textSecondary),
                      ),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _textField('餐前 (mmol/L)', _calBeforeCtrl, numeric: true)),
                        const SizedBox(width: 8),
                        Expanded(child: _textField('餐后 (mmol/L)', _calAfterCtrl, numeric: true)),
                        const SizedBox(width: 8),
                        Expanded(child: _textField('剂量 (U)', _calDoseCtrl, numeric: true)),
                      ]),
                      const SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          icon: const Icon(Icons.auto_fix_high),
                          label: Text('校准 ISF', style: SC.label.copyWith(color: Colors.white)),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: SC.primary,
                            foregroundColor: Colors.white,
                          ),
                          onPressed: state.loading ? null : () => _calibrate(state),
                        ),
                      ),
                      const SizedBox(height: 32),
                    ],
                  ),
                ),
        );
      },
    );
  }

  Widget _sectionTitle(String title) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Text(title, style: SC.headline),
      );

  Widget _textField(String label, TextEditingController ctrl, {bool numeric = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        controller: ctrl,
        keyboardType: numeric ? TextInputType.number : TextInputType.text,
        style: SC.body,
        decoration: InputDecoration(
          labelText: label,
          labelStyle: SC.label,
          border: const OutlineInputBorder(),
          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        ),
      ),
    );
  }

  Widget _dropdownField(String label, String value, List<String> items, ValueChanged<String?> onChanged) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: DropdownButtonFormField<String>(
        value: items.contains(value) ? value : items.first,
        items: items.map((e) => DropdownMenuItem(value: e, child: Text(e.isEmpty ? '(未选择)' : e))).toList(),
        onChanged: onChanged,
        style: SC.body,
        decoration: InputDecoration(
          labelText: label,
          labelStyle: SC.label,
          border: const OutlineInputBorder(),
          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        ),
      ),
    );
  }
}
