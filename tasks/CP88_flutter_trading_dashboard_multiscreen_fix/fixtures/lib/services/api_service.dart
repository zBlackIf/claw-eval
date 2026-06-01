import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String baseUrl = 'http://localhost:8080/api';

  /// Fetch dashboard metrics
  static Future<Map<String, dynamic>> getDashboardMetrics() async {
    final response = await http.get(Uri.parse('$baseUrl/dashboard/metrics'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception('Failed to load dashboard metrics');
  }

  /// Fetch risk indicators
  static Future<Map<String, dynamic>> getRiskIndicators() async {
    final response = await http.get(Uri.parse('$baseUrl/risk/indicators'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception('Failed to load risk indicators');
  }

  /// Fetch order list
  static Future<List<dynamic>> getOrders({int page = 1, int pageSize = 20}) async {
    final response = await http.get(
      Uri.parse('$baseUrl/orders?page=$page&pageSize=$pageSize'),
    );
    if (response.statusCode == 200) {
      return json.decode(response.body)['data'];
    }
    throw Exception('Failed to load orders');
  }

  /// Fetch alerts
  static Future<List<dynamic>> getAlerts() async {
    final response = await http.get(Uri.parse('$baseUrl/alerts'));
    if (response.statusCode == 200) {
      return json.decode(response.body)['data'];
    }
    throw Exception('Failed to load alerts');
  }

  /// Fetch strategies with versions
  static Future<List<dynamic>> getStrategies() async {
    final response = await http.get(Uri.parse('$baseUrl/strategies'));
    if (response.statusCode == 200) {
      return json.decode(response.body)['data'];
    }
    throw Exception('Failed to load strategies');
  }

  /// Fetch strategy versions
  static Future<List<dynamic>> getStrategyVersions(String strategyId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/strategies/$strategyId/versions'),
    );
    if (response.statusCode == 200) {
      return json.decode(response.body)['data'];
    }
    throw Exception('Failed to load strategy versions');
  }
}
