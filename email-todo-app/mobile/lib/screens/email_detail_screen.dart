import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../services/auth_service.dart';
import '../services/email_service.dart';

class EmailDetailScreen extends StatefulWidget {
  final Map<String, dynamic> email;

  const EmailDetailScreen({super.key, required this.email});

  @override
  State<EmailDetailScreen> createState() => _EmailDetailScreenState();
}

class _EmailDetailScreenState extends State<EmailDetailScreen> {
  final AuthService _authService = AuthService();
  final TextEditingController _hintController = TextEditingController(
    text: "Politely acknowledge and confirm details.",
  );

  bool _loadingDraft = false;
  bool _savingDraft = false;
  Map<String, dynamic>? _generatedDraft;

  /// Helper function to strip HTML tags and clean up spacing
  String _cleanHtml(String htmlString) {
    // Remove HTML tags
    final exp = RegExp(r'<[^>]*>', multiLine: true, caseSensitive: true);
    String cleaned = htmlString.replaceAll(exp, '');
    
    // Decode common HTML entities
    cleaned = cleaned
        .replaceAll('&nbsp;', ' ')
        .replaceAll('&amp;', '&')
        .replaceAll('&lt;', '<')
        .replaceAll('&gt;', '>')
        .replaceAll('&quot;', '"');

    // Clean up excessive blank lines
    final lines = cleaned.split('\n');
    final nonEmptyLines = lines.map((line) => line.trim()).where((line) => line.isNotEmpty);
    return nonEmptyLines.join('\n\n');
  }

  Future<void> _generateDraft() async {
    setState(() => _loadingDraft = true);
    try {
      final token = await _authService.getSessionToken();
      final response = await http.post(
        Uri.parse("${EmailService.baseUrl}/emails/draft-preview/${widget.email["id"]}"),
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer $token",
        },
        body: jsonEncode({"user_hint": _hintController.text}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _generatedDraft = data["draft"];
        });
      } else {
        throw Exception(response.body);
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed to generate draft: $e")),
      );
    } finally {
      setState(() => _loadingDraft = false);
    }
  }

  Future<void> _saveToGmail() async {
    setState(() => _savingDraft = true);
    try {
      final token = await _authService.getSessionToken();
      final response = await http.post(
        Uri.parse("${EmailService.baseUrl}/emails/draft-reply/${widget.email["id"]}"),
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer $token",
        },
        body: jsonEncode({"user_hint": _hintController.text}),
      );

      if (response.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Draft successfully saved to your Gmail! Check your Gmail Drafts folder.")),
        );
      } else {
        throw Exception(response.body);
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed to save draft to Gmail: $e")),
      );
    } finally {
      setState(() => _savingDraft = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final rawBody = widget.email["body_text"] ?? widget.email["snippet"] ?? "No content available.";
    final formattedBody = _cleanHtml(rawBody);

    return Scaffold(
      appBar: AppBar(title: const Text("Email Details")),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: ListView(
          children: [
            // Subject
            Text(
              widget.email["subject"] ?? "No Subject",
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            // Sender
            Text(
              "From: ${widget.email["sender"] ?? "Unknown"}",
              style: TextStyle(fontSize: 14, color: Colors.grey[700], fontWeight: FontWeight.w500),
            ),
            const Divider(height: 30),
            // Email Body Container
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.grey.shade300),
              ),
              child: Text(
                formattedBody.isNotEmpty ? formattedBody : "No readable content.",
                style: const TextStyle(fontSize: 15, height: 1.5, color: Colors.black87),
              ),
            ),
            const SizedBox(height: 32),
            // AI Section Header
            const Text(
              "🤖 AI Reply Assistant",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _hintController,
              decoration: const InputDecoration(
                labelText: "Instruction/Hint for AI Reply",
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: _loadingDraft ? null : _generateDraft,
              icon: _loadingDraft
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.auto_awesome),
              label: Text(_loadingDraft ? "Generating AI Reply..." : "Generate AI Reply Preview"),
            ),
            if (_generatedDraft != null) ...[
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.grey[100],
                  border: Border.all(color: Colors.grey[300]!),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("Generated Subject:", style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text(_generatedDraft!["subject"] ?? ""),
                    const SizedBox(height: 12),
                    const Text("Generated Body:", style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text(_generatedDraft!["body"] ?? ""),
                    const SizedBox(height: 16),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        foregroundColor: Colors.white,
                      ),
                      onPressed: _savingDraft ? null : _saveToGmail,
                      icon: _savingDraft
                          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                          : const Icon(Icons.send),
                      label: Text(_savingDraft ? "Saving..." : "Save Draft to Gmail"),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}