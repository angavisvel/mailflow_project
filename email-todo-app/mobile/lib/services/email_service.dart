import 'dart:convert';
import 'package:http/http.dart' as http;
import 'auth_service.dart';

class EmailService {
  final AuthService _authService = AuthService();

  static String get baseUrl => AuthService.baseUrl;

  Future<Map<String, dynamic>> syncEmails() async {
    final token = await _authService.getSessionToken();
    if (token == null) throw Exception("Not authenticated");

    final response = await http.post(
      Uri.parse("${AuthService.baseUrl}/emails/sync"),
      headers: {
        "Authorization": "Bearer $token",
        "Content-Type": "application/json",
      },
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception("Failed to sync emails: ${response.body}");
    }
  }

  Future<List<dynamic>> getStoredEmails() async {
    final token = await _authService.getSessionToken();
    if (token == null) throw Exception("Not authenticated");

    final response = await http.get(
      Uri.parse("$baseUrl/emails/list"),
      headers: {
        "Authorization": "Bearer $token",
        "Content-Type": "application/json",
      },
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data["emails"] ?? [];
    } else {
      throw Exception("Failed to fetch emails: ${response.body}");
    }
  }
}