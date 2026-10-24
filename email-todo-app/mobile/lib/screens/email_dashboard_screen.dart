import 'package:flutter/material.dart';
import '../services/email_service.dart';
import '../services/auth_service.dart';
import 'gmail_connect_screen.dart';
import 'email_detail_screen.dart';
import '../services/notification_service.dart';

class EmailDashboardScreen extends StatefulWidget {
  const EmailDashboardScreen({super.key});

  @override
  State<EmailDashboardScreen> createState() => _EmailDashboardScreenState();
}

class _EmailDashboardScreenState extends State<EmailDashboardScreen> {
  final EmailService _emailService = EmailService();
  final AuthService _authService = AuthService();
  
  List<dynamic> _emails = [];
  bool _loading = true;
  bool _syncing = false;

  @override
  void initState() {
    super.initState();
    _loadEmails();
  }

  Future<void> _loadEmails() async {
    setState(() => _loading = true);
    try {
      final emails = await _emailService.getStoredEmails();
      setState(() {
        _emails = emails;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error loading emails: $e")),
      );
    }
  }

  Future<void> _syncInbox() async {
    setState(() => _syncing = true);
    try {
      // 1. Call the backend sync endpoint
      final result = await EmailService().syncEmails(); 
      int tasksExtracted = result['tasks_extracted'] ?? 0;

      // 2. Trigger notification (Forced test alert so you see it pop up right now!)
      await NotificationService().showTaskAlert(
        id: DateTime.now().millisecondsSinceEpoch ~/ 1000,
        title: "Task Sync Successful! 🚀",
        body: tasksExtracted > 0 
            ? "We found $tasksExtracted new urgent task(s) from your emails." 
            : "Inbox synced successfully. Check your Priorities tab.",
      );
      
      // 3. Reload your emails list so they show on screen
      await _loadEmails(); 
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Sync complete! $tasksExtracted task(s) extracted.")),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Sync failed: $e")),
      );
    } finally {
      setState(() => _syncing = false);
    }
  }

  Future<void> _disconnect() async {
    await _authService.disconnectGmail();
    if (!mounted) return;
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (context) => const GmailConnectScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Email Dashboard & Inbox"),
        actions: [
          IconButton(
            icon: const Icon(Icons.sync),
            tooltip: "Sync Inbox",
            onPressed: _syncing ? null : _syncInbox,
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: "Disconnect Gmail",
            onPressed: _disconnect,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _syncing
              ? const Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      CircularProgressIndicator(),
                      SizedBox(height: 16),
                      Text("Syncing emails from Gmail..."),
                    ],
                  ),
                )
              : _emails.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.inbox, size: 64, color: Colors.grey),
                          const SizedBox(height: 16),
                          const Text("No emails synced yet."),
                          const SizedBox(height: 16),
                          ElevatedButton.icon(
                            onPressed: _syncInbox,
                            icon: const Icon(Icons.sync),
                            label: const Text("Sync Now"),
                          ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      itemCount: _emails.length,
                      itemBuilder: (context, index) {
                        final email = _emails[index];
                        return Card(
                          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                          child: ListTile(
                            title: Text(
                              email["subject"] ?? "No Subject",
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const SizedBox(height: 4),
                                Text("From: ${email["sender"] ?? "Unknown"}"),
                                const SizedBox(height: 2),
                                Text(
                                  email["snippet"] ?? "",
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(color: Colors.grey[600]),
                                ),
                              ],
                            ),
                            isThreeLine: true,
                            trailing: const Icon(Icons.chevron_right),
                            onTap: () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (context) => EmailDetailScreen(email: email),
                                ),
                              );
                            },
                          ),
                        );
                      },
                    ),
    );
  }
}