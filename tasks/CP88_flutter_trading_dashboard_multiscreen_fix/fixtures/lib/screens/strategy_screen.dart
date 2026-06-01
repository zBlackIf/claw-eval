import 'package:flutter/material.dart';

/// BUG: This strategy page does NOT match the requirements document.
/// Current implementation allows adding new strategies directly,
/// but the requirement says new strategies can ONLY be added via backtesting.
/// Also missing: version numbers, weights, win rates.
class StrategyScreen extends StatefulWidget {
  const StrategyScreen({Key? key}) : super(key: key);

  @override
  State<StrategyScreen> createState() => _StrategyScreenState();
}

class _StrategyScreenState extends State<StrategyScreen> {
  final List<Map<String, dynamic>> _strategies = [
    {'name': 'Moving Average', 'enabled': true},
    {'name': 'RSI Reversal', 'enabled': false},
    {'name': 'Bollinger Breakout', 'enabled': true},
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Strategy Management'),
        actions: [
          // BUG: Should NOT have "Add Strategy" button per requirements
          IconButton(
            icon: Icon(Icons.add),
            onPressed: () => _addStrategy(),
            tooltip: 'Add Strategy',
          ),
        ],
      ),
      body: ListView.builder(
        itemCount: _strategies.length,
        itemBuilder: (context, index) {
          final strategy = _strategies[index];
          return ListTile(
            title: Text(strategy['name']),
            // BUG: Missing version number display
            // BUG: Missing weight and win rate display
            trailing: Switch(
              value: strategy['enabled'],
              onChanged: (val) {
                setState(() {
                  strategy['enabled'] = val;
                });
              },
            ),
          );
        },
      ),
    );
  }

  void _addStrategy() {
    // BUG: This should not exist - strategies are only added via backtesting
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Add Strategy'),
        content: TextField(decoration: InputDecoration(labelText: 'Strategy Name')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(context), child: Text('Add')),
        ],
      ),
    );
  }
}
