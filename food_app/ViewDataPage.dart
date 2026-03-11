import 'dart:async';
import 'package:flutter/material.dart';

class ViewDataPage extends StatefulWidget {
  final String ip;
  final String deviceName;

  const ViewDataPage({super.key, required this.ip, required this.deviceName});

  @override
  State<ViewDataPage> createState() => _ViewDataPageState();
}

class _ViewDataPageState extends State<ViewDataPage> {
  Timer? _refreshTimer;
  int _imageCounter = 0; 

  @override
  void initState() {
    super.initState();
    // Refresh the image every 1 second to create a stream effect
    _refreshTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted) setState(() => _imageCounter++);
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final String imageUrl = "http://${widget.ip}:5000/snapshot?v=$_imageCounter";

    return Scaffold(
      backgroundColor: Colors.grey[900],
      appBar: AppBar(
        title: Text(widget.deviceName),
        backgroundColor: Colors.black,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => setState(() => _imageCounter++),
          )
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              height: 300,
              color: Colors.black,
              child: Image.network(
                imageUrl,
                fit: BoxFit.contain,
                loadingBuilder: (context, child, loadingProgress) {
                  if (loadingProgress == null) return child;
                  return const Center(child: CircularProgressIndicator(color: Colors.green));
                },
                errorBuilder: (context, error, stackTrace) => const Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.videocam_off, color: Colors.white54, size: 50),
                      SizedBox(height: 10),
                      Text("Waiting for Pi Image Stream...", style: TextStyle(color: Colors.white54)),
                    ],
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  _buildDataCard("Device IP", widget.ip, Icons.lan),
                  _buildDataCard("Connection", "Stable (Hotspot)", Icons.wifi_tethering),
                  const SizedBox(height: 20),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.redAccent,
                      foregroundColor: Colors.white,
                      minimumSize: const Size(double.infinity, 50),
                    ),
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close),
                    label: const Text("Close Stream"),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDataCard(String label, String value, IconData icon) {
    return Card(
      color: Colors.grey[850],
      child: ListTile(
        leading: Icon(icon, color: Colors.greenAccent),
        title: Text(label, style: const TextStyle(color: Colors.white70, fontSize: 12)),
        subtitle: Text(value, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
      ),
    );
  }
}