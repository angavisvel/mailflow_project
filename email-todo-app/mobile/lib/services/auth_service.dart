import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

class AuthService {
  static String get baseUrl {
    try {
      if (Platform.isAndroid) {
        return "http://10.0.2.2:8000";
      }
    } catch (_) {}
    return "http://127.0.0.1:8000";
  }

  final _storage = const FlutterSecureStorage();

  Future<void> connectGmail() async {
    HttpServer? server;
    String? capturedCode;
    try {
      // 1. Bind local HTTP server on port 8080 with shared: true
      server = await HttpServer.bind(
        InternetAddress.loopbackIPv4, 
        8080, 
        shared: true,
      );
      
      // 2. Open browser to FastAPI login route with explicit redirect_uri
      final redirectUri = "http://127.0.0.1:8080/callback";
      final loginUrl = Uri.parse("$baseUrl/auth/login?redirect_uri=${Uri.encodeComponent(redirectUri)}");
      
      if (await canLaunchUrl(loginUrl)) {
        await launchUrl(loginUrl, mode: LaunchMode.externalApplication);
      } else {
        throw Exception("Could not launch login URL");
      }

      // 3. Listen for the incoming request from Google
      await for (HttpRequest request in server) {
        final uri = request.uri;
        if (uri.path == "/callback") {
          capturedCode = uri.queryParameters["code"];
          
          // Send success page to the browser
          request.response
            ..statusCode = HttpStatus.ok
            ..headers.contentType = ContentType.html
            ..write("<html><body style='font-family:Arial;text-align:center;padding-top:50px;'><h2>Authentication Successful!</h2><p>You can close this window and return to your app.</p><script>window.close();</script></body></html>");
          await request.response.close();
          break; // Exit the listener loop
        }
      }
    } finally {
      await server?.close(); // Ensure port 8080 is always freed immediately
    }

    // 4. Exchange code for JWT token *after* server has shut down
    if (capturedCode != null) {
      await _exchangeCodeForToken(capturedCode);
    }
  }

  Future<void> _exchangeCodeForToken(String code) async {
    final response = await http.post(
      Uri.parse("$baseUrl/auth/exchange-code"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({"code": code}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final token = data["session_token"];
      if (token != null) {
        await saveSessionToken(token);
      }
    } else {
      throw Exception("Failed to exchange auth code: ${response.body}");
    }
  }

  Stream<String?> listenForSessionToken() async* {
    yield await getSessionToken();
  }

  Future<void> saveSessionToken(String token) async {
    await _storage.write(key: "session_token", value: token);
  }

  Future<String?> getSessionToken() async {
    try {
      return await _storage.read(key: "session_token");
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>?> getGmailStatus() async {
    final token = await getSessionToken();
    if (token == null) return null;

    try {
      final response = await http.get(
        Uri.parse("$baseUrl/auth/gmail/status"),
        headers: {"Authorization": "Bearer $token"},
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else if (response.statusCode == 401) {
        // Clear invalid token if unauthorized
        await _storage.delete(key: "session_token");
      }
    } catch (_) {}
    return null;
  }

  Future<bool> disconnectGmail() async {
    final token = await getSessionToken();
    if (token != null) {
      try {
        await http.post(
          Uri.parse("$baseUrl/auth/gmail/disconnect"),
          headers: {"Authorization": "Bearer $token"},
        );
      } catch (_) {}
    }
    await _storage.delete(key: "session_token");
    return true;
  }
}