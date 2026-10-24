import 'package:flutter/material.dart';
import '../services/auth_service.dart';
import 'email_dashboard_screen.dart';
import 'main_navigation_screen.dart';

class GmailConnectScreen extends StatefulWidget {
  const GmailConnectScreen({super.key});

  @override
  State<GmailConnectScreen> createState() => _GmailConnectScreenState();
}

class _GmailConnectScreenState extends State<GmailConnectScreen> {
  final AuthService _authService = AuthService();
  bool _connected = false;
  String? _gmailEmail;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _authService.listenForSessionToken().listen((token) async {
      if (token != null) {
        await _authService.saveSessionToken(token);
        _refreshStatus();
      }
    });
    _refreshStatus();
  }

  Future<void> _refreshStatus() async {
    setState(() => _loading = true);
    try {
      final status = await _authService.getGmailStatus();
      if (status != null && status["connected"] == true) {
        // If connected, navigate directly to the Email Dashboard!
        if (!mounted) return;
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (context) => const MainNavigationScreen()),
        );
        return;
      }
      setState(() {
        _connected = false;
        _gmailEmail = null;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  Future<void> _connect() async {
    try {
      await _authService.connectGmail();
      await _refreshStatus();
    } catch (e) {
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Connection note: $e")),
      );
    }
  }

  Future<void> _disconnect() async {
    final ok = await _authService.disconnectGmail();
    if (ok) {
      setState(() {
        _connected = false;
        _gmailEmail = null;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Gmail Integration")),
      body: Center(
        child: _loading
            ? const CircularProgressIndicator()
            : Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    _connected ? Icons.check_circle : Icons.mail_outline,
                    size: 64,
                    color: _connected ? Colors.green : Colors.grey,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    _connected
                        ? "Connected as $_gmailEmail"
                        : "Gmail not connected",
                    style: const TextStyle(fontSize: 16),
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton(
                    onPressed: _connected ? _disconnect : _connect,
                    child: Text(_connected ? "Disconnect Gmail" : "Connect Gmail"),
                  ),
                ],
              ),
      ),
    );
  }
}