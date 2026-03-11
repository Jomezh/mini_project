import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

// Import the second file
import 'hotspotmod.dart';

// ── Must match ble_manager.py exactly ──────────────────────────────────────
const String _serviceUuid  = '12345678-1234-1234-1234-123456789ab0';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MaterialApp(
    home: BLEScannerPage(),
    debugShowCheckedModeBanner: false,
  ));
}

// ── BLE Scanner Page ────────────────────────────────────────────────────────

class BLEScannerPage extends StatefulWidget {
  const BLEScannerPage({super.key});
  @override
  State<BLEScannerPage> createState() => _BLEScannerPageState();
}

class _BLEScannerPageState extends State<BLEScannerPage> {
  List<ScanResult> _scanResults = [];
  bool _isScanning = false;
  StreamSubscription? _scanSub;
  StreamSubscription? _scanStateSub;

  @override
  void initState() {
    super.initState();
    _initPermissions();
  }

  @override
  void dispose() {
    _scanSub?.cancel();
    _scanStateSub?.cancel();
    super.dispose();
  }

  void _initPermissions() async {
    await [
      Permission.bluetoothScan,
      Permission.bluetoothConnect,
      Permission.location,
      Permission.camera,
    ].request();

    _scanSub = FlutterBluePlus.scanResults.listen((results) {
      if (mounted) {
        setState(() => _scanResults = results
            .where((r) => r.device.platformName.isNotEmpty)
            .toList());
      }
    });

    _scanStateSub = FlutterBluePlus.isScanning.listen((s) {
      if (mounted) setState(() => _isScanning = s);
    });
  }

  Future<void> _startQRFlow() async {
    final String? rawQr = await Navigator.push(
      context,
      MaterialPageRoute(builder: (c) => const QRScannerScreen()),
    );
    if (rawQr == null || !mounted) return;

    String targetName = rawQr;
    if (rawQr.startsWith('minik://')) {
      try {
        final uri = Uri.parse(rawQr);
        targetName = uri.queryParameters['ble'] ?? rawQr;
      } catch (e) {
        debugPrint('[BLE] QR parse failed: $e');
      }
    }
    _autoConnect(targetName);
  }

  void _autoConnect(String targetName) async {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Searching for $targetName...')),
    );

    await FlutterBluePlus.startScan(
      withNames: [targetName],
      timeout: const Duration(seconds: 10),
    );

    StreamSubscription? tempSub;
    bool found = false;
    tempSub = FlutterBluePlus.scanResults.listen((results) async {
      if (found) return;
      for (final r in results) {
        if (r.device.platformName == targetName) {
          found = true;
          await FlutterBluePlus.stopScan();
          tempSub?.cancel();
          _connectToPi(r.device);
          break;
        }
      }
    });

    Future.delayed(const Duration(seconds: 12), () => tempSub?.cancel());
  }

  Future<void> _connectToPi(BluetoothDevice device) async {
    if (!mounted) return;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (c) => const Center(child: CircularProgressIndicator()),
    );

    try {
      await device.connect(
        autoConnect: false,
        timeout: const Duration(seconds: 15),
      );
      await Future.delayed(const Duration(seconds: 1));
      final services = await device.discoverServices();

      final hasService = services.any(
        (s) => s.uuid.toString().toLowerCase().contains(_serviceUuid),
      );

      if (!mounted) return;
      Navigator.pop(context);

      if (hasService) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (c) => HotspotPage(device: device, services: services),
          ),
        );
      } else {
        await device.disconnect();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Device found but not ready. Try again.')),
        );
      }
    } catch (e) {
      if (mounted) Navigator.pop(context);
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('MiniK Connect'),
        actions: [
          IconButton(icon: const Icon(Icons.qr_code), onPressed: _startQRFlow),
          IconButton(
            icon: Icon(_isScanning ? Icons.stop : Icons.search),
            onPressed: () => _isScanning
                ? FlutterBluePlus.stopScan()
                : FlutterBluePlus.startScan(
                    timeout: const Duration(seconds: 10)),
          ),
        ],
      ),
      body: _scanResults.isEmpty
          ? const Center(child: Text('Scan QR or search for BLE devices'))
          : ListView.builder(
              itemCount: _scanResults.length,
              itemBuilder: (c, i) => ListTile(
                leading: const Icon(Icons.bluetooth),
                title: Text(_scanResults[i].device.platformName),
                subtitle: Text(_scanResults[i].device.remoteId.toString()),
                trailing: Text('${_scanResults[i].rssi} dBm'),
                onTap: () => _connectToPi(_scanResults[i].device),
              ),
            ),
    );
  }
}

// ── QR Scanner ──────────────────────────────────────────────────────────────

class QRScannerScreen extends StatelessWidget {
  const QRScannerScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan MiniK QR Code')),
      body: MobileScanner(
        onDetect: (capture) {
          final raw = capture.barcodes.firstOrNull?.rawValue;
          if (raw != null) Navigator.pop(context, raw);
        },
      ),
    );
  }
}