import 'package:flutter/material.dart';
import 'package:wifi_scan/wifi_scan.dart';

class WiFiPage extends StatefulWidget {
  const WiFiPage({super.key});

  @override
  State<WiFiPage> createState() => _WiFiPageState();
}

class _WiFiPageState extends State<WiFiPage> {
  List<WiFiAccessPoint> accessPoints = [];

  void _startScan() async {
    // Check if hardware supports scanning
    final canScan = await WiFiScan.instance.canStartScan();
    if (canScan == CanStartScan.yes) {
      await WiFiScan.instance.startScan();
      final results = await WiFiScan.instance.getScannedResults();
      setState(() {
        accessPoints = results;
      });
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Scan not available: $canScan")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Available WiFi")),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: ElevatedButton(
              onPressed: _startScan,
              child: const Text("Refresh Networks"),
            ),
          ),
          Expanded(
            child: accessPoints.isEmpty
                ? const Center(child: Text("No networks found. Tap Refresh."))
                : ListView.builder(
                    itemCount: accessPoints.length,
                    itemBuilder: (context, index) {
                      final network = accessPoints[index];
                      return ListTile(
                        leading: const Icon(Icons.wifi),
                        title: Text(network.ssid.isEmpty ? "Hidden Network" : network.ssid),
                        subtitle: Text("Signal Strength: ${network.level} dBm"),
                        trailing: const Icon(Icons.lock_outline),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}