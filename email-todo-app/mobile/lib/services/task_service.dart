import 'dart:convert';
import 'package:http/http.dart' as http;
import 'auth_service.dart';

class TaskService {
  final AuthService _authService = AuthService();

  Future<List<dynamic>> getTasks({String? status, String? priority}) async {
    final token = await _authService.getSessionToken();
    if (token == null) throw Exception("Not authenticated");

    String url = "${AuthService.baseUrl}/tasks/";
    List<String> params = [];
    if (status != null) params.add("status=$status");
    if (priority != null) params.add("priority=$priority");
    if (params.isNotEmpty) {
      url += "?${params.join('&')}";
    }

    final response = await http.get(
      Uri.parse(url),
      headers: {"Authorization": "Bearer $token"},
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception("Failed to load tasks: ${response.body}");
    }
  }

  Future<void> updateTaskStatus(String taskId, String status) async {
    final token = await _authService.getSessionToken();
    if (token == null) throw Exception("Not authenticated");

    final response = await http.patch(
      Uri.parse("${AuthService.baseUrl}/tasks/$taskId"),
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer $token",
      },
      body: jsonEncode({"status": status}),
    );

    if (response.statusCode != 200) {
      throw Exception("Failed to update task: ${response.body}");
    }
  }
}