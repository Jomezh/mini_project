import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart'; // Required for Clipboard
import 'package:flutter_blue_plus/flutter_blue_plus.dart';

// ── GLOBAL CONSTANTS (Must be outside the class to avoid "undefined name") ──
const String _charIp = '12345678-1234-1234-1234-123456789ab5';

class ConnectionResultPage extends StatefulWidget {
  final BluetoothDevice device;
  final List<BluetoothService> services;

  const ConnectionResultPage({
    super.key,
    required this.device,
    required this.services,
  });

  @override
  State<ConnectionResultPage> createState() => _ConnectionResultPageState();
}

class _ConnectionResultPageState extends State<ConnectionResultPage> {
  String _statusMessage = "Connecting MiniK to Hotspot...";
  String _foundIp = "";
  bool _isSuccess = false;
  Timer? _pollingTimer;
  int _retryCount = 0;
  final int _maxRetries = 20; // Approx 40 seconds total polling

  @override
  void initState() {
    super.initState();
    // Start polling the IP characteristic every 2 seconds
    _pollingTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
      _checkPiIpAddress();
    });
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }

  Future<void> _checkPiIpAddress() async {
    if (_retryCount >= _maxRetries) {
      _pollingTimer?.cancel();
      setState(() => _statusMessage = "Connection Timed Out.\nCheck your Hotspot settings.");
      return;
    }

    try {
      // Look for the specific IP characteristic in the discovered services
      final characteristic = widget.services
          .expand((s) => s.characteristics)
          .firstWhere((c) => c.uuid.toString().toLowerCase() == _charIp);

      final value = await characteristic.read();
      final ipString = String.fromCharCodes(value).trim();

      // Check if the Pi has written a real IP (not 0.0.0.0 or empty)
      if (ipString.isNotEmpty && ipString != "0.0.0.0") {
        _pollingTimer?.cancel();
        setState(() {
          _foundIp = ipString;
          _statusMessage = "MiniK is Online!";
          _isSuccess = true;
        });
      }
    } catch (e) {
      debugPrint("Waiting for Pi to write IP... (${_retryCount + 1})");
    }

    if (mounted) {
      setState(() => _retryCount++);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text("Connection Status"),
        automaticallyImplyLeading: false, // Prevents going back to the input form
        centerTitle: true,
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24), // Your requested padding
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Icon Indicator
              _buildIcon(),
              
              const SizedBox(height: 30),
              
              Text(
                _statusMessage,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w500),
              ),

              if (_isSuccess) ...[
                const SizedBox(height: 24),
                // IP Display Box with "Tap to Copy"
                InkWell(
                  onTap: () {
                    Clipboard.setData(ClipboardData(text: _foundIp));
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text("IP Address copied!")),
                    );
                  },
                  borderRadius: BorderRadius.circular(12),
                  child: Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: Colors.blue.shade50,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.blue.shade200),
                    ),
                    child: Column(
                      children: [
                        Text(
                          _foundIp,
                          style: const TextStyle(
                            fontSize: 34,
                            fontWeight: FontWeight.bold,
                            color: Colors.blue,
                            fontFamily: 'monospace',
                          ),
                        ),
                        const SizedBox(height: 8),
                        const Text("Tap to copy IP", style: TextStyle(color: Colors.blueGrey, fontSize: 12)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 48),
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton(
                    onPressed: () => Navigator.popUntil(context, (route) => route.isFirst),
                    child: const Text("DONE", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  ),
                ),
              ] else if (_retryCount < _maxRetries) ...[
                const SizedBox(height: 40),
                const CircularProgressIndicator(),
              ] else ...[
                const SizedBox(height: 30),
                TextButton.icon(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.refresh),
                  label: const Text("Try Again"),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildIcon() {
    if (_isSuccess) return const Icon(Icons.check_circle, color: Colors.green, size: 100);
    if (_retryCount >= _maxRetries) return const Icon(Icons.error_outline, color: Colors.red, size: 100);
    return const Icon(Icons.wifi_tethering, color: Colors.blue, size: 100);
  }
}