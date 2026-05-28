import 'package:flutter/material.dart';

class AlertScreen extends StatefulWidget {
  const AlertScreen({Key? key}) : super(key: key);

  @override
  State<AlertScreen> createState() => _AlertScreenState();
}

class _AlertScreenState extends State<AlertScreen> {
  // BUG: Chinese field names use garbled encoding
  final List<Map<String, String>> _alertTypes = [
    {'label': '\u544a\u8b66\u7c7b\u578b', 'value': 'type'},  // Should be readable Chinese
    {'label': '\u89e6\u53d1\u65f6\u95f4', 'value': 'time'},
    {'label': '\u4e25\u91cd\u7b49\u7ea7', 'value': 'severity'},
    {'label': '\u5904\u7406\u72b6\u6001', 'value': 'status'},
  ];

  final List<Map<String, dynamic>> _alerts = [
    {
      '\u544a\u8b66ID': 'ALT-001',
      '\u7c7b\u578b': '\u4ef7\u683c\u5f02\u5e38',
      '\u65f6\u95f4': '2026-04-27 10:30',
      '\u7b49\u7ea7': '\u9ad8',
      '\u72b6\u6001': '\u672a\u5904\u7406',
      '\u63cf\u8ff0': 'BTC/USDT \u4ef7\u683c\u57285\u5206\u949f\u5185\u4e0b\u8dcc3%',
    },
    {
      '\u544a\u8b66ID': 'ALT-002',
      '\u7c7b\u578b': '\u6301\u4ed3\u8d85\u9650',
      '\u65f6\u95f4': '2026-04-27 09:15',
      '\u7b49\u7ea7': '\u4e2d',
      '\u72b6\u6001': '\u5df2\u5904\u7406',
      '\u63cf\u8ff0': 'ETH\u6301\u4ed3\u8d85\u8fc7\u603b\u8d44\u91d115%',
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('\u544a\u8b66\u7ba1\u7406')),
      body: Column(
        children: [
          // Filter row with garbled labels
          Padding(
            padding: EdgeInsets.all(8.0),
            child: Row(
              children: _alertTypes.map((t) => Padding(
                padding: EdgeInsets.symmetric(horizontal: 4.0),
                child: Chip(label: Text(t['label']!)),
              )).toList(),
            ),
          ),
          // Alert list with garbled field names
          Expanded(
            child: ListView.builder(
              itemCount: _alerts.length,
              itemBuilder: (context, index) {
                final alert = _alerts[index];
                return Card(
                  margin: EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
                  child: ListTile(
                    title: Text('${alert["\u544a\u8b66ID"]} - ${alert["\u7c7b\u578b"]}'),
                    subtitle: Text(alert['\u63cf\u8ff0'] ?? ''),
                    trailing: Text(alert['\u72b6\u6001'] ?? ''),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
