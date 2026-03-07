import 'package:flutter_test/flutter_test.dart';
import 'package:sugarclaw/main.dart';

void main() {
  testWidgets('App renders', (WidgetTester tester) async {
    await tester.pumpWidget(const SugarClawApp());
    expect(find.text('SugarClaw'), findsOneWidget);
  });
}
