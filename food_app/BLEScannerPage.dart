/* ORGINAL WORKING
BLUTOOTH CLASSIC

 */
/*
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_bluetooth_serial/flutter_bluetooth_serial.dart';
import 'package:permission_handler/permission_handler.dart';

class BluetoothPage extends StatefulWidget {
  const BluetoothPage({super.key});

  @override
  State<BluetoothPage> createState() => _BluetoothPageState();
}

class _BluetoothPageState extends State<BluetoothPage> {
  BluetoothState _bluetoothState = BluetoothState.UNKNOWN;
  final List<BluetoothDiscoveryResult> _results = [];
  bool _isDiscovering = false;
  StreamSubscription<BluetoothDiscoveryResult>? _discoveryStreamSubscription;

  @override
  void initState() {
    super.initState();
    _checkPermissions();
    
    // Listen for Bluetooth state changes (On/Off)
    FlutterBluetoothSerial.instance.state.then((state) {
      setState(() { _bluetoothState = state; });
    });
  }

  @override
  void dispose() {
    _discoveryStreamSubscription?.cancel();
    super.dispose();
  }

  // 1. Request necessary permissions for Android 12+
  Future<void> _checkPermissions() async {
    Map<Permission, PermissionStatus> statuses = await [
      Permission.bluetoothScan,
      Permission.bluetoothConnect,
      Permission.location,
    ].request();

    if (statuses[Permission.bluetoothScan]!.isGranted) {
      _startDiscovery();
    }
  }

  // 2. Start the Discovery Process
  void _startDiscovery() {
    setState(() {
      _results.clear();
      _isDiscovering = true;
    });

    _discoveryStreamSubscription =
        FlutterBluetoothSerial.instance.startDiscovery().listen((r) {
      setState(() {
        // Prevent duplicate entries by checking the MAC address
        final existingIndex = _results.indexWhere(
            (element) => element.device.address == r.device.address);
        if (existingIndex >= 0) {
          _results[existingIndex] = r;
        } else {
          _results.add(r);
        }
      });
    });

    _discoveryStreamSubscription?.onDone(() {
      setState(() { _isDiscovering = false; });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Classic Bluetooth Scanner"),
        actions: [
          _isDiscovering
              ? const Center(
                  child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: 20),
                  child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)),
                ))
              : IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: _startDiscovery,
                )
        ],
      ),
      body: Column(
        children: [
          SwitchListTile(
            title: const Text('Enable Bluetooth'),
            value: _bluetoothState.isEnabled,
            onChanged: (bool value) async {
              if (value) {
               await FlutterBluetoothSerial.instance.requestEnable();
              } else {
                await FlutterBluetoothSerial.instance.requestDisable();
              }
            },
          ),
          const Divider(),
          Expanded(
            child: ListView.builder(
              itemCount: _results.length,
              itemBuilder: (context, index) {
                BluetoothDiscoveryResult result = _results[index];
                final device = result.device;
                
                // Classic Bluetooth retrieves the 'name' much more reliably
                String deviceName = device.name ?? "Unknown Device";
                String address = device.address;

                return ListTile(
                  leading: Icon(
                    device.isConnected ? Icons.bluetooth_connected : Icons.bluetooth,
                    color: device.isConnected ? Colors.blue : Colors.grey,
                  ),
                  title: Text(deviceName, style: const TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text(address),
                  trailing: Text("${result.rssi} dBm"),
                  onTap: () {
                    // Logic to pair or connect would go here
                    print("Connecting to ${device.name}...");
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
*/
//ble conncted watch code
/*
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

void main() {
  runApp(const MaterialApp(home: BLEScannerPage()));
}

// --- MAIN PAGE: BLE SCANNER ---
class BLEScannerPage extends StatefulWidget {
  const BLEScannerPage({super.key});

  @override
  State<BLEScannerPage> createState() => _BLEScannerPageState();
}

class _BLEScannerPageState extends State<BLEScannerPage> {
  List<ScanResult> _scanResults = [];
  bool _isScanning = false;
  StreamSubscription<List<ScanResult>>? _scanSubscription;

  @override
  void initState() {
    super.initState();
    _initPermissions();
  }

  void _initPermissions() async {
    // Request all necessary permissions for BLE and Camera
    await [
      Permission.bluetoothScan,
      Permission.bluetoothConnect,
      Permission.location,
      Permission.camera,
    ].request();

    // Listen to global scan results
    _scanSubscription = FlutterBluePlus.scanResults.listen((results) {
      if (mounted) {
        setState(() {
          _scanResults = results.where((r) => r.device.platformName.isNotEmpty).toList();
        });
      }
    });

    // Listen to scanning state
    FlutterBluePlus.isScanning.listen((state) {
      if (mounted) setState(() => _isScanning = state);
    });
  }

  // --- QR SCANNER INTEGRATION ---
  void _openQRScanner() async {
    // 1. Open Scanner and wait for result
    final String? qrData = await Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const QRScannerScreen()),
    );

    // 2. If we got data, try to find and connect to that device name
    if (qrData != null && qrData.isNotEmpty) {
      _autoConnectByQR(qrData);
    }
  }

  void _autoConnectByQR(String deviceName) async {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text("Searching for: $deviceName...")),
    );

    // Start a focused scan for that name
    await FlutterBluePlus.startScan(
      withNames: [deviceName], 
      timeout: const Duration(seconds: 10),
    );

    // Temp listener to catch the specific device
    StreamSubscription? tempSub;
    tempSub = FlutterBluePlus.scanResults.listen((results) {
      for (ScanResult r in results) {
        if (r.device.platformName == deviceName) {
          tempSub?.cancel();
          FlutterBluePlus.stopScan();
          _connectToDevice(r.device);
          break;
        }
      }
    });
  }

  void _startManualScan() async {
    try {
      await FlutterBluePlus.startScan(timeout: const Duration(seconds: 15));
    } catch (e) {
      debugPrint("Scan Error: $e");
    }
  }

  Future<void> _connectToDevice(BluetoothDevice device) async {
    try {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (c) => const Center(child: CircularProgressIndicator()),
      );

      await device.connect();
      
      if (mounted) {
        Navigator.pop(context); // Close loading dialog
        Navigator.push(
          context,
          MaterialPageRoute(builder: (context) => HotspotPage(device: device)),
        );
      }
    } catch (e) {
      if (mounted) Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Connection Failed: $e")));
    }
  }

  @override
  void dispose() {
    _scanSubscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("BLE Scanner"),
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code_scanner),
            onPressed: _openQRScanner, // QR Trigger
          ),
          if (_isScanning)
            const Padding(padding: EdgeInsets.all(16), child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)))
          else
            IconButton(icon: const Icon(Icons.search), onPressed: _startManualScan),
        ],
      ),
      body: ListView.separated(
        itemCount: _scanResults.length,
        separatorBuilder: (c, i) => const Divider(),
        itemBuilder: (context, index) {
          final result = _scanResults[index];
          return ListTile(
            title: Text(result.device.platformName),
            subtitle: Text(result.device.remoteId.str),
            trailing: ElevatedButton(
              onPressed: () => _connectToDevice(result.device),
              child: const Text("CONNECT"),
            ),
          );
        },
      ),
    );
  }
}

// --- QR SCANNER UI ---
class QRScannerScreen extends StatelessWidget {
  const QRScannerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Scan Device QR")),
      body: MobileScanner(
        onDetect: (capture) {
          final List<Barcode> barcodes = capture.barcodes;
          if (barcodes.isNotEmpty) {
            final String? code = barcodes.first.rawValue;
            if (code != null) Navigator.pop(context, code);
          }
        },
      ),
    );
  }
}

// --- TARGET PAGE ---
class HotspotPage extends StatelessWidget {
  final BluetoothDevice device;
  const HotspotPage({super.key, required this.device});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Connected")),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.bluetooth_connected, size: 80, color: Colors.blue),
            const SizedBox(height: 20),
            Text("Linked to: ${device.platformName}"),
            ElevatedButton(
              onPressed: () async {
                await device.disconnect();
                Navigator.pop(context);
              },
              child: const Text("Disconnect"),
            )
          ],
        ),
      ),
    );
  }
}*/
/*
lab code
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

void main() {
  // Required for plugin initialization
  WidgetsFlutterBinding.ensureInitialized(); 
  runApp(const MaterialApp(
    debugShowCheckedModeBanner: false,
    home: BLEScannerPage(),
  ));
}

class BLEScannerPage extends StatefulWidget {
  const BLEScannerPage({super.key});

  @override
  State<BLEScannerPage> createState() => _BLEScannerPageState();
}

class _BLEScannerPageState extends State<BLEScannerPage> {
  List<ScanResult> _scanResults = [];
  bool _isScanning = false;
  StreamSubscription<List<ScanResult>>? _scanResultsSubscription;
  StreamSubscription<bool>? _isScanningSubscription;

  @override
  void initState() {
    super.initState();
    _initBLE();
  }

  void _initBLE() async {
    // 1. Request Permissions
    await [
      Permission.bluetoothScan,
      Permission.bluetoothConnect,
      Permission.location,
      Permission.camera,
    ].request();

    // 2. Setup Listeners
    _scanResultsSubscription = FlutterBluePlus.scanResults.listen((results) {
      if (mounted) {
        setState(() {
          _scanResults = results.where((r) => r.device.platformName.isNotEmpty).toList();
        });
      }
    });

    _isScanningSubscription = FlutterBluePlus.isScanning.listen((state) {
      if (mounted) setState(() => _isScanning = state);
    });
  }

  // --- QR SCAN AND AUTO-CONNECT ---
  Future<void> _scanQRCodeAndConnect() async {
    final String? scannedDeviceName = await Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const QRScannerScreen()),
    );

    if (scannedDeviceName != null && scannedDeviceName.isNotEmpty) {
      _performAutoConnect(scannedDeviceName);
    }
  }

  void _performAutoConnect(String targetName) async {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text("Searching for $targetName...")),
    );

    // Start scanning
    await FlutterBluePlus.startScan(timeout: const Duration(seconds: 10));

    StreamSubscription? tempSub;
    tempSub = FlutterBluePlus.scanResults.listen((results) async {
      for (ScanResult r in results) {
        if (r.device.platformName == targetName) {
          // IMPORTANT: Stop scanning before connecting to stabilize connection
          await FlutterBluePlus.stopScan(); 
          tempSub?.cancel();
          _connectToDevice(r.device);
          break;
        }
      }
    });
  }

  Future<void> _connectToDevice(BluetoothDevice device) async {
    try {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (c) => const Center(child: CircularProgressIndicator()),
      );

      // autoConnect: false is usually more stable for initial pairing
      await device.connect(autoConnect: false, timeout: const Duration(seconds: 15));
      
      if (mounted) {
        Navigator.pop(context); // Remove loader
        Navigator.push(
          context,
          MaterialPageRoute(builder: (context) => HotspotPage(device: device)),
        );
      }
    } catch (e) {
      if (mounted) Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Link Error: $e")));
    }
  }

  @override
  void dispose() {
    _scanResultsSubscription?.cancel();
    _isScanningSubscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Device Scanner"),
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code_scanner),
            onPressed: _scanQRCodeAndConnect,
          ),
          _isScanning 
            ? const Padding(padding: EdgeInsets.all(16), child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)))
            : IconButton(icon: const Icon(Icons.refresh), onPressed: () => FlutterBluePlus.startScan(timeout: const Duration(seconds: 10))),
        ],
      ),
      body: ListView.builder(
        itemCount: _scanResults.length,
        itemBuilder: (c, i) => ListTile(
          title: Text(_scanResults[i].device.platformName),
          subtitle: Text(_scanResults[i].device.remoteId.str),
          trailing: ElevatedButton(
            onPressed: () => _connectToDevice(_scanResults[i].device),
            child: const Text("CONNECT"),
          ),
        ),
      ),
    );
  }
}

// --- QR SCREEN ---
class QRScannerScreen extends StatelessWidget {
  const QRScannerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Scan QR Code")),
      body: MobileScanner(
        onDetect: (capture) {
          final List<Barcode> barcodes = capture.barcodes;
          if (barcodes.isNotEmpty) {
            final String? code = barcodes.first.rawValue;
            if (code != null) Navigator.pop(context, code);
          }
        },
      ),
    );
  }
}

// --- CONNECTED PAGE ---
class HotspotPage extends StatelessWidget {
  final BluetoothDevice device;
  const HotspotPage({super.key, required this.device});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Control Panel")),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.check_circle, size: 100, color: Colors.green),
            Text("Linked to ${device.platformName}"),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: () async {
                await device.disconnect();
                Navigator.pop(context);
              },
              child: const Text("Disconnect"),
            ),
          ],
        ),
      ),
    );
  }
}*///working page
/*
import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

// ── Must match ble_manager.py exactly ──────────────────────────────────────
const String _serviceUuid  = '12345678-1234-1234-1234-123456789ab0';
const String _charSsid     = '12345678-1234-1234-1234-123456789ab1';
const String _charPassword = '12345678-1234-1234-1234-123456789ab2';
const String _charBleName  = '12345678-1234-1234-1234-123456789ab3';
const String _charBleMac   = '12345678-1234-1234-1234-123456789ab4';
const String _charIp       = '12345678-1234-1234-1234-123456789ab5';
const String _charStatus   = '12345678-1234-1234-1234-123456789ab6';

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

  @override
  void initState() {
    super.initState();
    _initPermissions();
  }

  @override
  void dispose() {
    _scanSub?.cancel();
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

    FlutterBluePlus.isScanning.listen((s) {
      if (mounted) setState(() => _isScanning = s);
    });
  }

  // ── 1. Scan QR and parse minik:// deep link ─────────────────────────────

  Future<void> _startQRFlow() async {
    final String? rawQr = await Navigator.push(
      context,
      MaterialPageRoute(builder: (c) => const QRScannerScreen()),
    );
    if (rawQr == null) return;

    // ── FIX 1: Parse deep link — extract BLE name from URL ──────────────
    // Pi QR format: minik://pair?device=MINIK-591F10&ble=MiniK-591F10&uuid=...
    String targetName = rawQr;
    String? serviceUuid;

    if (rawQr.startsWith('minik://')) {
      try {
        final uri = Uri.parse(rawQr);
        targetName  = uri.queryParameters['ble']  ?? rawQr;
        serviceUuid = uri.queryParameters['uuid'];
        print('[BLE] QR parsed → name: $targetName  uuid: $serviceUuid');
      } catch (e) {
        print('[BLE] QR parse failed, using raw: $e');
      }
    }

    _autoConnect(targetName);
  }

  // ── 2. Scan and auto-connect ─────────────────────────────────────────────

  void _autoConnect(String targetName) async {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Searching for $targetName...')),
    );

    await FlutterBluePlus.startScan(
      withNames: [targetName],          // Only match Pi's BLE name
      timeout: const Duration(seconds: 10),
    );

    StreamSubscription? tempSub;
    tempSub = FlutterBluePlus.scanResults.listen((results) async {
      for (ScanResult r in results) {
        if (r.device.platformName == targetName) {
          await FlutterBluePlus.stopScan();
          tempSub?.cancel();
          _connectToPi(r.device);
          break;
        }
      }
    });
  }

  // ── 3. Connect + service discovery ──────────────────────────────────────

  Future<void> _connectToPi(BluetoothDevice device) async {
    if (!mounted) return;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (c) => const Center(child: CircularProgressIndicator()),
    );

    try {
      await device.connect(autoConnect: false,
          timeout: const Duration(seconds: 15));

      // ── FIX 2: Wait for Pi GATT to fully register after connect ───────
      await Future.delayed(const Duration(seconds: 1));

      final services = await device.discoverServices();

      // Verify Pi's MiniK service is present
      final hasService = services.any(
        (s) => s.uuid.toString().toLowerCase() == _serviceUuid,
      );

      if (!mounted) return;
      Navigator.pop(context);   // Close loader

      if (hasService) {
        print('[BLE] MiniK GATT service found ✓');
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (c) => HotspotPage(device: device, services: services),
          ),
        );
      } else {
        print('[BLE] MiniK service NOT found — Pi GATT not ready?');
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Device found but GATT not ready. Try again.'),
          ),
        );
        await device.disconnect();
      }
    } catch (e) {
      if (mounted) Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Connection failed: $e')),
      );
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
            onPressed: _isScanning
                ? FlutterBluePlus.stopScan
                : () => FlutterBluePlus.startScan(
                      timeout: const Duration(seconds: 10),
                    ),
          ),
        ],
      ),
      body: _scanResults.isEmpty
          ? const Center(child: Text('Tap QR icon to scan\nor search icon to browse'))
          : ListView.builder(
              itemCount: _scanResults.length,
              itemBuilder: (c, i) => ListTile(
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

// ── Hotspot Page ─────────────────────────────────────────────────────────────

class HotspotPage extends StatefulWidget {
  final BluetoothDevice device;
  final List<BluetoothService> services;

  const HotspotPage({
    super.key,
    required this.device,
    required this.services,
  });

  @override
  State<HotspotPage> createState() => _HotspotPageState();
}

class _HotspotPageState extends State<HotspotPage> {
  BluetoothConnectionState _connState = BluetoothConnectionState.connected;
  late StreamSubscription _connSub;

  final _ssidCtrl     = TextEditingController();
  final _passwordCtrl = TextEditingController();

  bool _sending   = false;
  bool _sent      = false;
  String _statusMsg = '';
  String _piIp    = '';

  // ── FIX 3 & 4: Characteristic lookup helpers ─────────────────────────────

  BluetoothCharacteristic? _findChar(String uuid) {
    for (final svc in widget.services) {
      if (svc.uuid.toString().toLowerCase() != _serviceUuid) continue;
      for (final c in svc.characteristics) {
        if (c.uuid.toString().toLowerCase() == uuid) return c;
      }
    }
    return null;
  }

  Future<void> _writeString(String uuid, String value) async {
    final c = _findChar(uuid);
    if (c == null) throw Exception('Characteristic $uuid not found');
    await c.write(value.codeUnits, withoutResponse: false);
    print('[BLE] → Wrote $uuid: ${uuid == _charPassword ? "***" : value}');
  }

  // ── Send credentials to Pi ────────────────────────────────────────────────

  Future<void> _sendCredentials() async {
    final ssid     = _ssidCtrl.text.trim();
    final password = _passwordCtrl.text.trim();

    if (ssid.isEmpty || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter SSID and password')),
      );
      return;
    }

    setState(() { _sending = true; _statusMsg = 'Sending credentials...'; });

    try {
      // Get phone's own BLE info to send to Pi
      final phoneName = Platform.localHostname;
      final phoneMac  = widget.device.remoteId.toString();   // Pi's MAC
      // Note: Android doesn't expose own MAC directly — we send device name
      // Pi uses ble_name for display + ble_mac to scan for us next boot

      await _writeString(_charBleName, phoneName);
      setState(() => _statusMsg = 'Sending name... (1/4)');

      await _writeString(_charBleMac, widget.device.remoteId.toString());
      setState(() => _statusMsg = 'Sending identity... (2/4)');

      await _writeString(_charSsid, ssid);
      setState(() => _statusMsg = 'Sending SSID... (3/4)');

      await _writeString(_charPassword, password);
      setState(() => _statusMsg = 'Sending password... (4/4)');

      setState(() => _statusMsg = 'Waiting for Pi to connect...');

      // ── Wait for Pi to write IP back after WiFi connects ────────────────
      await Future.delayed(const Duration(seconds: 8));

      final ipChar = _findChar(_charIp);
      if (ipChar != null) {
        final ipBytes = await ipChar.read();
        final ip = String.fromCharCodes(ipBytes).trim();
        if (ip.isNotEmpty) {
          setState(() {
            _piIp      = ip;
            _statusMsg = 'Connected! Pi IP: $ip';
            _sent      = true;
          });
          print('[BLE] Pi IP received: $ip');
          return;
        }
      }

      // Check status characteristic
      final statusChar = _findChar(_charStatus);
      if (statusChar != null) {
        final statusBytes = await statusChar.read();
        final status = String.fromCharCodes(statusBytes).trim();
        if (status == 'enable_hotspot') {
          setState(() => _statusMsg = '⚠ Please enable your hotspot,\nthen wait...');
        }
      }

      setState(() {
        _statusMsg = 'Credentials sent.\nEnable your hotspot if not on.';
        _sent = true;
      });

    } catch (e) {
      setState(() => _statusMsg = 'Error: $e');
      print('[BLE] Send credentials error: $e');
    } finally {
      setState(() => _sending = false);
    }
  }

  // ── Subscribe to STATUS notifications from Pi ─────────────────────────────

  Future<void> _subscribeToStatus() async {
    final c = _findChar(_charStatus);
    if (c == null) return;
    try {
      await c.setNotifyValue(true);
      c.onValueReceived.listen((value) {
        final status = String.fromCharCodes(value).trim();
        print('[BLE] ← Pi status notification: $status');
        if (status == 'enable_hotspot' && mounted) {
          setState(() => _statusMsg = '⚠ Pi says: Please enable your hotspot');
        }
      });
    } catch (e) {
      print('[BLE] Subscribe status error: $e');
    }
  }

  @override
  void initState() {
    super.initState();
    _connSub = widget.device.connectionState.listen((s) {
      if (mounted) setState(() => _connState = s);
    });
    // Subscribe to Pi status notifications after a short delay
    Future.delayed(const Duration(milliseconds: 500), _subscribeToStatus);
  }

  @override
  void dispose() {
    _connSub.cancel();
    _ssidCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final connected = _connState == BluetoothConnectionState.connected;

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.device.platformName),
        actions: [
          Icon(
            Icons.circle,
            color: connected ? Colors.green : Colors.red,
            size: 14,
          ),
          const SizedBox(width: 12),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Connection status
            Text(
              connected ? '🟢 Connected to Pi' : '🔴 Disconnected',
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 20),

            // Credentials form
            if (!_sent) ...[
              TextField(
                controller: _ssidCtrl,
                decoration: const InputDecoration(
                  labelText: 'Hotspot SSID',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.wifi),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _passwordCtrl,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Hotspot Password',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.lock),
                ),
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: _sending ? null : _sendCredentials,
                icon: _sending
                    ? const SizedBox(
                        width: 18, height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.send),
                label: Text(_sending ? 'Sending...' : 'Send to MiniK'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ],

            // Status message
            if (_statusMsg.isNotEmpty) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: _sent ? Colors.green.shade50 : Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: _sent ? Colors.green : Colors.blue,
                  ),
                ),
                child: Text(_statusMsg, textAlign: TextAlign.center),
              ),
            ],

            // Pi IP display
            if (_piIp.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                'Pi IP: $_piIp',
                style: const TextStyle(
                  fontFamily: 'monospace',
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
            ],

            const SizedBox(height: 30),
            OutlinedButton.icon(
              onPressed: () =>
                  widget.device.disconnect().then((_) => Navigator.pop(context)),
              icon: const Icon(Icons.bluetooth_disabled),
              label: const Text('Disconnect'),
            ),
          ],
        ),
      ),
    );
  }
}
*/
/*
import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'ConnectionResultPage.dart';
import 'package:network_info_plus/network_info_plus.dart';

// ── Must match ble_manager.py exactly ──────────────────────────────────────
const String _serviceUuid  = '12345678-1234-1234-1234-123456789ab0';
const String _charSsid     = '12345678-1234-1234-1234-123456789ab1';
const String _charPassword = '12345678-1234-1234-1234-123456789ab2';
const String _charBleName  = '12345678-1234-1234-1234-123456789ab3';
const String _charBleMac   = '12345678-1234-1234-1234-123456789ab4';
const String _charIp       = '12345678-1234-1234-1234-123456789ab5';
const String _charStatus   = '12345678-1234-1234-1234-123456789ab6';

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

  @override
  void initState() {
    super.initState();
    _initPermissions();
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

    FlutterBluePlus.isScanning.listen((s) {
      if (mounted) setState(() => _isScanning = s);
    });
  }

  Future<void> _startQRFlow() async {
    final String? rawQr = await Navigator.push(
      context,
      MaterialPageRoute(builder: (c) => const QRScannerScreen()),
    );
    if (rawQr == null) return;

    String targetName = rawQr;
    if (rawQr.startsWith('minik://')) {
      try {
        final uri = Uri.parse(rawQr);
        targetName = uri.queryParameters['ble'] ?? rawQr;
      } catch (e) {
        debugPrint('QR parse failed: $e');
      }
    }
    _autoConnect(targetName);
  }

  void _autoConnect(String targetName) async {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Searching for $targetName...')));
    await FlutterBluePlus.startScan(withNames: [targetName], timeout: const Duration(seconds: 10));

    StreamSubscription? tempSub;
    tempSub = FlutterBluePlus.scanResults.listen((results) async {
      for (ScanResult r in results) {
        if (r.device.platformName == targetName) {
          await FlutterBluePlus.stopScan();
          tempSub?.cancel();
          _connectToPi(r.device);
          break;
        }
      }
    });
  }

  Future<void> _connectToPi(BluetoothDevice device) async {
    showDialog(context: context, builder: (c) => const Center(child: CircularProgressIndicator()));
    try {
      await device.connect(autoConnect: false, timeout: const Duration(seconds: 15));
      await Future.delayed(const Duration(seconds: 1));
      final services = await device.discoverServices();
      Navigator.pop(context);

      if (mounted) {
        Navigator.push(context, MaterialPageRoute(
          builder: (c) => HotspotPage(device: device, services: services),
        ));
      }
    } catch (e) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('MiniK Connect'), actions: [
        IconButton(icon: const Icon(Icons.qr_code), onPressed: _startQRFlow),
        IconButton(icon: Icon(_isScanning ? Icons.stop : Icons.search), 
          onPressed: () => _isScanning ? FlutterBluePlus.stopScan() : FlutterBluePlus.startScan(timeout: const Duration(seconds: 10)))
      ]),
      body: ListView.builder(
        itemCount: _scanResults.length,
        itemBuilder: (c, i) => ListTile(
          title: Text(_scanResults[i].device.platformName),
          onTap: () => _connectToPi(_scanResults[i].device),
        ),
      ),
    );
  }
}

// ── QR Scanner Screen ───────────────────────────────────────────────────────

class QRScannerScreen extends StatelessWidget {
  const QRScannerScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: MobileScanner(onDetect: (capture) {
        final raw = capture.barcodes.firstOrNull?.rawValue;
        if (raw != null) Navigator.pop(context, raw);
      }),
    );
  }
}

// ── Hotspot Page (Auto-SSID & Transition) ───────────────────────────────────

class HotspotPage extends StatefulWidget {
  final BluetoothDevice device;
  final List<BluetoothService> services;
  const HotspotPage({super.key, required this.device, required this.services});

  @override
  State<HotspotPage> createState() => _HotspotPageState();
}

class _HotspotPageState extends State<HotspotPage> {
  final _ssidCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _fetchCurrentSSID();
  }

  Future<void> _fetchCurrentSSID() async {
    final info = NetworkInfo();
    String? ssid = await info.getWifiName();
    if (ssid != null) {
      setState(() => _ssidCtrl.text = ssid.replaceAll('"', ''));
    }
  }

  BluetoothCharacteristic? _findChar(String uuid) {
    for (var s in widget.services) {
      if (s.uuid.toString().toLowerCase() == _serviceUuid) {
        for (var c in s.characteristics) {
          if (c.uuid.toString().toLowerCase() == uuid) return c;
        }
      }
    }
    return null;
  }

  Future<void> _send() async {
    setState(() => _sending = true);
    try {
      await _findChar(_charBleName)?.write(Platform.localHostname.codeUnits);
      await _findChar(_charBleMac)?.write(widget.device.remoteId.toString().codeUnits);
      await _findChar(_charSsid)?.write(_ssidCtrl.text.trim().codeUnits);
      await _findChar(_charPassword)?.write(_passwordCtrl.text.trim().codeUnits);

      if (mounted) {
        Navigator.pushReplacement(context, MaterialPageRoute(
          builder: (c) => ConnectionResultPage(device: widget.device, services: widget.services),
        ));
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Configure WiFi')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            TextField(controller: _ssidCtrl, decoration: const InputDecoration(labelText: 'WiFi Name (SSID)')),
            TextField(controller: _passwordCtrl, decoration: const InputDecoration(labelText: 'Password'), obscureText: true),
            const SizedBox(height: 20),
            ElevatedButton(onPressed: _sending ? null : _send, child: Text(_sending ? 'Sending...' : 'Connect MiniK')),
          ],
        ),
      ),
    );
  }
}
*/
/* working code as of library work



import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

// ── Must match ble_manager.py exactly ──────────────────────────────────────
const String _serviceUuid  = '12345678-1234-1234-1234-123456789ab0';
const String _charSsid     = '12345678-1234-1234-1234-123456789ab1';
const String _charPassword = '12345678-1234-1234-1234-123456789ab2';
const String _charBleName  = '12345678-1234-1234-1234-123456789ab3';
const String _charBleMac   = '12345678-1234-1234-1234-123456789ab4';
const String _charIp       = '12345678-1234-1234-1234-123456789ab5';
const String _charStatus   = '12345678-1234-1234-1234-123456789ab6';

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

  // ── 1. Scan QR and parse minik:// deep link ─────────────────────────────

  Future<void> _startQRFlow() async {
    final String? rawQr = await Navigator.push(
      context,
      MaterialPageRoute(builder: (c) => const QRScannerScreen()),
    );
    if (rawQr == null || !mounted) return;

    // Parse deep link: minik://pair?device=MINIK-591F10&ble=MiniK-591F10&uuid=...
    String targetName = rawQr;

    if (rawQr.startsWith('minik://')) {
      try {
        final uri = Uri.parse(rawQr);
        targetName = uri.queryParameters['ble'] ?? rawQr;
        print('[BLE] QR parsed → BLE name: $targetName');
      } catch (e) {
        print('[BLE] QR parse failed, using raw value: $e');
      }
    }

    _autoConnect(targetName);
  }

  // ── 2. Scan and auto-connect by BLE name ─────────────────────────────────

  void _autoConnect(String targetName) async {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Searching for $targetName...')),
    );

    // withNames filters scan to only emit matching devices — saves battery
    await FlutterBluePlus.startScan(
      withNames: [targetName],
      timeout: const Duration(seconds: 10),
    );

    StreamSubscription? tempSub;
    tempSub = FlutterBluePlus.scanResults.listen((results) async {
      for (final r in results) {
        if (r.device.platformName == targetName) {
          await FlutterBluePlus.stopScan();
          tempSub?.cancel();
          _connectToPi(r.device);
          break;
        }
      }
    });
  }

  // ── 3. Connect + service discovery ──────────────────────────────────────

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

      // Wait for Pi GATT to be fully registered after connection
      // Without this, discoverServices() returns empty and phone drops
      await Future.delayed(const Duration(seconds: 1));

      final services = await device.discoverServices();

      // Verify Pi's MiniK service UUID is present before navigating
      final hasService = services.any(
        (s) => s.uuid.toString().toLowerCase() == _serviceUuid,
      );

      if (!mounted) return;
      Navigator.pop(context); // Close loader

      if (hasService) {
        print('[BLE] ✓ MiniK GATT service confirmed');
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (c) =>
                HotspotPage(device: device, services: services),
          ),
        );
      } else {
        print('[BLE] ✗ MiniK service not found — Pi GATT not ready?');
        await device.disconnect();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Device found but not ready. Try again in 5s.'),
          ),
        );
      }
    } catch (e) {
      if (mounted) Navigator.pop(context);
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Connection failed: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('MiniK Connect'),
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code),
            tooltip: 'Scan QR',
            onPressed: _startQRFlow,
          ),
          IconButton(
            icon: Icon(_isScanning ? Icons.stop : Icons.search),
            tooltip: _isScanning ? 'Stop scan' : 'Scan BLE',
            onPressed: _isScanning
                ? FlutterBluePlus.stopScan
                : () => FlutterBluePlus.startScan(
                      timeout: const Duration(seconds: 10),
                    ),
          ),
        ],
      ),
      body: _scanResults.isEmpty
          ? const Center(
              child: Text(
                'Tap  🔍  to scan  or  📷  to scan QR code',
                style: TextStyle(color: Colors.grey),
              ),
            )
          : ListView.builder(
              itemCount: _scanResults.length,
              itemBuilder: (c, i) => ListTile(
                leading: const Icon(Icons.bluetooth),
                title: Text(_scanResults[i].device.platformName),
                subtitle:
                    Text(_scanResults[i].device.remoteId.toString()),
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

// ── Hotspot Page ─────────────────────────────────────────────────────────────

class HotspotPage extends StatefulWidget {
  final BluetoothDevice device;
  final List<BluetoothService> services;

  const HotspotPage({
    super.key,
    required this.device,
    required this.services,
  });

  @override
  State<HotspotPage> createState() => _HotspotPageState();
}

class _HotspotPageState extends State<HotspotPage> {
  BluetoothConnectionState _connState = BluetoothConnectionState.connected;
  late StreamSubscription _connSub;

  final _ssidCtrl     = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _obscurePass   = true;

  bool _sending   = false;
  bool _sent      = false;
  String _statusMsg = '';
  String _piIp      = '';

  // ── Characteristic helper ─────────────────────────────────────────────────

  BluetoothCharacteristic? _findChar(String uuid) {
    for (final svc in widget.services) {
      if (svc.uuid.toString().toLowerCase() != _serviceUuid) continue;
      for (final c in svc.characteristics) {
        if (c.uuid.toString().toLowerCase() == uuid) return c;
      }
    }
    return null;
  }

  Future<void> _writeStr(String uuid, String value) async {
    final c = _findChar(uuid);
    if (c == null) throw Exception('Char $uuid not found');
    await c.write(value.codeUnits, withoutResponse: false);
    print('[BLE] → Wrote ${uuid.substring(uuid.length - 4)}: '
        '${uuid == _charPassword ? "***" : value}');
  }

  // ── Send all 4 credentials to Pi ─────────────────────────────────────────

  Future<void> _sendCredentials() async {
    final ssid     = _ssidCtrl.text.trim();
    final password = _passwordCtrl.text.trim();

    if (ssid.isEmpty || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter SSID and password')),
      );
      return;
    }

    setState(() {
      _sending   = true;
      _statusMsg = 'Sending credentials to Pi...';
    });

    try {
      // ── FIX: Use FlutterBluePlus.adapterName — returns real device name ──
      // Platform.localHostname returns "localhost" on Android (useless to Pi)
      // adapterName returns the phone's Bluetooth name e.g. "iQOO Neo7"
      final adapterName = await FlutterBluePlus.adapterName;
      final phoneName   = adapterName.isNotEmpty ? adapterName : 'MyPhone';

      // ── FIX: Send phone name in BOTH ble_name AND ble_mac ────────────────
      // Pi uses ble_mac only for central-scan on next boot.
      // Android hides the real MAC (privacy randomization) — use name instead.
      // Pi's scan_for_devices() accepts known_names list so name works fine.
      await _writeStr(_charBleName, phoneName);
      setState(() => _statusMsg = 'Sending name... (1/4)');

      await _writeStr(_charBleMac, phoneName);
      setState(() => _statusMsg = 'Sending identity... (2/4)');

      await _writeStr(_charSsid, ssid);
      setState(() => _statusMsg = 'Sending SSID... (3/4)');

      await _writeStr(_charPassword, password);
      setState(() => _statusMsg = 'Sending password... (4/4) ✓\nWaiting for Pi...');

      // Give Pi time to attempt WiFi connection before reading IP back
      await Future.delayed(const Duration(seconds: 8));

      // Try reading IP characteristic
      final ipChar = _findChar(_charIp);
      if (ipChar != null) {
        final bytes = await ipChar.read();
        final ip    = String.fromCharCodes(bytes).trim();
        if (ip.isNotEmpty) {
          setState(() {
            _piIp      = ip;
            _statusMsg = '✅ Pi connected!\nIP: $ip';
            _sent      = true;
          });
          print('[BLE] Pi IP received: $ip');
          return;
        }
      }

      // Check status characteristic — Pi may ask for hotspot
      final statusChar = _findChar(_charStatus);
      if (statusChar != null) {
        final bytes  = await statusChar.read();
        final status = String.fromCharCodes(bytes).trim();
        if (status == 'enable_hotspot') {
          setState(() =>
              _statusMsg = '⚠️ Please enable your hotspot,\nthen wait...');
        }
      }

      setState(() {
        _statusMsg = 'Credentials sent.\n'
            'Enable hotspot if Pi can\'t find your WiFi.';
        _sent = true;
      });

    } catch (e) {
      setState(() => _statusMsg = '❌ Error: $e');
      print('[BLE] _sendCredentials error: $e');
    } finally {
      setState(() => _sending = false);
    }
  }

  // ── Subscribe to Pi STATUS notifications ─────────────────────────────────

  Future<void> _subscribeToStatus() async {
    final c = _findChar(_charStatus);
    if (c == null) return;
    try {
      await c.setNotifyValue(true);
      c.onValueReceived.listen((value) {
        final status = String.fromCharCodes(value).trim();
        print('[BLE] ← Pi status notify: $status');
        if (!mounted) return;
        if (status == 'enable_hotspot') {
          setState(() =>
              _statusMsg = '⚠️ Pi says: Please enable your hotspot');
        }
      });
      print('[BLE] Subscribed to STATUS notifications');
    } catch (e) {
      print('[BLE] STATUS subscribe error (non-fatal): $e');
    }
  }

  @override
  void initState() {
    super.initState();
    _connSub = widget.device.connectionState.listen((s) {
      if (mounted) setState(() => _connState = s);
    });
    Future.delayed(const Duration(milliseconds: 500), _subscribeToStatus);
  }

  @override
  void dispose() {
    _connSub.cancel();
    _ssidCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final connected = _connState == BluetoothConnectionState.connected;

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.device.platformName),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Icon(
              Icons.circle,
              size: 13,
              color: connected ? Colors.green : Colors.red,
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [

            // ── Connection badge ────────────────────────────────────────────
            Row(
              children: [
                Icon(
                  connected ? Icons.bluetooth_connected : Icons.bluetooth_disabled,
                  color: connected ? Colors.green : Colors.red,
                ),
                const SizedBox(width: 8),
                Text(
                  connected ? 'Connected to Pi' : 'Disconnected',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: connected ? Colors.green : Colors.red,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // ── Credentials form ────────────────────────────────────────────
            if (!_sent) ...[
              TextField(
                controller: _ssidCtrl,
                decoration: const InputDecoration(
                  labelText: 'Hotspot SSID',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.wifi),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _passwordCtrl,
                obscureText: _obscurePass,
                decoration: InputDecoration(
                  labelText: 'Hotspot Password',
                  border: const OutlineInputBorder(),
                  prefixIcon: const Icon(Icons.lock),
                  suffixIcon: IconButton(
                    icon: Icon(
                      _obscurePass ? Icons.visibility : Icons.visibility_off,
                    ),
                    onPressed: () =>
                        setState(() => _obscurePass = !_obscurePass),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: (_sending || !connected) ? null : _sendCredentials,
                icon: _sending
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.send),
                label: Text(_sending ? 'Sending...' : 'Send to MiniK'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ],

            // ── Status message ──────────────────────────────────────────────
            if (_statusMsg.isNotEmpty) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: _sent ? Colors.green.shade50 : Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _sent ? Colors.green.shade300 : Colors.blue.shade300,
                  ),
                ),
                child: Text(
                  _statusMsg,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 15),
                ),
              ),
            ],

            // ── Pi IP display ───────────────────────────────────────────────
            if (_piIp.isNotEmpty) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.green.shade100,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.green),
                ),
                child: Column(
                  children: [
                    const Text('Pi IP Address',
                        style: TextStyle(color: Colors.green)),
                    const SizedBox(height: 4),
                    Text(
                      _piIp,
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 30),
            OutlinedButton.icon(
              onPressed: () => widget.device
                  .disconnect()
                  .then((_) => Navigator.pop(context)),
              icon: const Icon(Icons.bluetooth_disabled, color: Colors.red),
              label: const Text('Disconnect',
                  style: TextStyle(color: Colors.red)),
            ),
          ],
        ),
      ),
    );
  }
}
*/
/*
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

// ── Must match ble_manager.py exactly ──────────────────────────────────────
const String _serviceUuid  = '12345678-1234-1234-1234-123456789ab0';
const String _charSsid     = '12345678-1234-1234-1234-123456789ab1';
const String _charPassword = '12345678-1234-1234-1234-123456789ab2';
const String _charBleName  = '12345678-1234-1234-1234-123456789ab3';
const String _charBleMac   = '12345678-1234-1234-1234-123456789ab4';
const String _charIp       = '12345678-1234-1234-1234-123456789ab5';
const String _charStatus   = '12345678-1234-1234-1234-123456789ab6';

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
        print('[BLE] QR parse failed: $e');
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
    tempSub = FlutterBluePlus.scanResults.listen((results) async {
      for (final r in results) {
        if (r.device.platformName == targetName) {
          await FlutterBluePlus.stopScan();
          tempSub?.cancel();
          _connectToPi(r.device);
          break;
        }
      }
    });
  }

  Future<void> _connectToPi(BluetoothDevice device) async {
    if (!mounted) return;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (c) => const Center(child: CircularProgressIndicator()),
    );

    try {
      await device.connect(autoConnect: false, timeout: const Duration(seconds: 15));
      await Future.delayed(const Duration(seconds: 1));
      final services = await device.discoverServices();

      final hasService = services.any(
        (s) => s.uuid.toString().toLowerCase() == _serviceUuid,
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
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
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
            onPressed: () => _isScanning ? FlutterBluePlus.stopScan() : FlutterBluePlus.startScan(timeout: const Duration(seconds: 10)),
          ),
        ],
      ),
      body: _scanResults.isEmpty
          ? const Center(child: Text('Scan QR or Search for BLE devices'))
          : ListView.builder(
              itemCount: _scanResults.length,
              itemBuilder: (c, i) => ListTile(
                title: Text(_scanResults[i].device.platformName),
                subtitle: Text(_scanResults[i].device.remoteId.toString()),
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

// ── Hotspot Page ─────────────────────────────────────────────────────────────

class HotspotPage extends StatefulWidget {
  final BluetoothDevice device;
  final List<BluetoothService> services;
  const HotspotPage({super.key, required this.device, required this.services});
  @override
  State<HotspotPage> createState() => _HotspotPageState();
}

class _HotspotPageState extends State<HotspotPage> {
  BluetoothConnectionState _connState = BluetoothConnectionState.connected;
  late StreamSubscription _connSub;
  Timer? _pollTimer;

  final _ssidCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _obscurePass = true;
  bool _sending = false;
  String _statusMsg = '';

  BluetoothCharacteristic? _findChar(String uuid) {
    for (final svc in widget.services) {
      if (svc.uuid.toString().toLowerCase() != _serviceUuid) continue;
      for (final c in svc.characteristics) {
        if (c.uuid.toString().toLowerCase() == uuid) return c;
      }
    }
    return null;
  }

  Future<void> _writeStr(String uuid, String value) async {
    final c = _findChar(uuid);
    if (c == null) throw Exception('Char not found');
    await c.write(value.codeUnits, withoutResponse: false);
  }

  // ── Polling & Auto-Navigate logic ─────────────────────────────────────────
  void _startPolling() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (timer) async {
      if (!mounted) return;
      try {
        final ipChar = _findChar(_charIp);
        if (ipChar != null) {
          final bytes = await ipChar.read();
          final ip = String.fromCharCodes(bytes).trim();
          if (ip.isNotEmpty && mounted) {
            timer.cancel();
            // GO TO VIEW DATA PAGE
            Navigator.pushAndRemoveUntil(
              context,
              MaterialPageRoute(builder: (c) => ViewDataPage(ip: ip, deviceName: widget.device.platformName)),
              (route) => route.isFirst,
            );
          }
        }
      } catch (e) {
        print('Poll error: $e');
      }
    });
  }

  Future<void> _sendCredentials() async {
    final ssid = _ssidCtrl.text.trim();
    final password = _passwordCtrl.text.trim();
    if (ssid.isEmpty || password.isEmpty) return;

    setState(() { _sending = true; _statusMsg = 'Sending...'; });

    try {
      final name = await FlutterBluePlus.adapterName;
      await _writeStr(_charBleName, name);
      await _writeStr(_charBleMac, name);
      await _writeStr(_charSsid, ssid);
      await _writeStr(_charPassword, password);
      
      setState(() => _statusMsg = 'Credentials sent! Waiting for Pi IP...');
      _startPolling();
    } catch (e) {
      setState(() { _sending = false; _statusMsg = 'Error: $e'; });
    }
  }

  @override
  void initState() {
    super.initState();
    _connSub = widget.device.connectionState.listen((s) {
      if (mounted) setState(() => _connState = s);
    });
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _connSub.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final connected = _connState == BluetoothConnectionState.connected;
    return Scaffold(
      appBar: AppBar(title: Text(widget.device.platformName)),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            TextField(controller: _ssidCtrl, decoration: const InputDecoration(labelText: 'Hotspot SSID')),
            TextField(controller: _passwordCtrl, obscureText: _obscurePass, decoration: const InputDecoration(labelText: 'Password')),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: (_sending || !connected) ? null : _sendCredentials,
              child: Text(_sending ? 'Sending...' : 'Connect Pi to Hotspot'),
            ),
            if (_statusMsg.isNotEmpty) Text(_statusMsg),
          ],
        ),
      ),
    );
  }
}

// ── View Data Page ──────────────────────────────────────────────────────────

class ViewDataPage extends StatelessWidget {
  final String ip;
  final String deviceName;
  const ViewDataPage({super.key, required this.ip, required this.deviceName});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(deviceName), backgroundColor: Colors.green),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.check_circle, color: Colors.green, size: 80),
            const SizedBox(height: 20),
            const Text('Pi Connected Successfully!', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            Text('IP Address: $ip', style: const TextStyle(fontSize: 18, color: Colors.blueGrey)),
            const SizedBox(height: 40),
            ElevatedButton(
              onPressed: () => Navigator.of(context).popUntil((route) => route.isFirst),
              child: const Text('Back to Home'),
            )
          ],
        ),
      ),
    );
  }
}
*/
/*

class work small mistake
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

// ── Must match ble_manager.py exactly ──────────────────────────────────────
const String _serviceUuid  = '12345678-1234-1234-1234-123456789ab0';
const String _charSsid     = '12345678-1234-1234-1234-123456789ab1';
const String _charPassword = '12345678-1234-1234-1234-123456789ab2';
const String _charBleName  = '12345678-1234-1234-1234-123456789ab3';
const String _charBleMac   = '12345678-1234-1234-1234-123456789ab4';
const String _charIp       = '12345678-1234-1234-1234-123456789ab5';
const String _charStatus   = '12345678-1234-1234-1234-123456789ab6';

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

    // FIX: cancel tempSub after scan timeout to prevent memory leak
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

    // Auto-cancel if never found
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

      // FIX: use contains() — flutter_blue_plus may format UUID with different casing
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
          ? const Center(child: Text('Scan QR or Search for BLE devices'))
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

// ── Hotspot Page ─────────────────────────────────────────────────────────────

class HotspotPage extends StatefulWidget {
  final BluetoothDevice device;
  final List<BluetoothService> services;
  const HotspotPage({super.key, required this.device, required this.services});
  @override
  State<HotspotPage> createState() => _HotspotPageState();
}

class _HotspotPageState extends State<HotspotPage> {
  BluetoothConnectionState _connState = BluetoothConnectionState.connected;
  late StreamSubscription _connSub;
  StreamSubscription? _statusSub;
  Timer? _pollTimer;

  final _ssidCtrl     = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _obscurePass   = true;
  bool _sending       = false;
  bool _navigated     = false; // FIX: guard against double-navigation
  String _statusMsg   = '';

  // FIX: use contains() for UUID matching
  BluetoothCharacteristic? _findChar(String uuid) {
    for (final svc in widget.services) {
      if (!svc.uuid.toString().toLowerCase().contains(_serviceUuid)) continue;
      for (final c in svc.characteristics) {
        if (c.uuid.toString().toLowerCase().contains(uuid)) return c;
      }
    }
    return null;
  }

  Future<void> _writeStr(String uuid, String value) async {
    final c = _findChar(uuid);
    if (c == null) throw Exception('Characteristic $uuid not found');
    await c.write(value.codeUnits, withoutResponse: false);
    debugPrint('[BLE] → Wrote ${uuid.substring(uuid.length - 4)}: '
        '${uuid == _charPassword ? "***" : value}');
  }

  // ── Subscribe to Pi status notify (enable_hotspot) ────────────────────────
  Future<void> _subscribeToStatus() async {
    final c = _findChar(_charStatus);
    if (c == null) return;
    try {
      await c.setNotifyValue(true);
      _statusSub = c.onValueReceived.listen((value) {
        if (!mounted) return;
        final status = String.fromCharCodes(value).trim();
        debugPrint('[BLE] ← Pi status: $status');
        if (status == 'enable_hotspot') {
          _showHotspotDialog();
        }
      });
    } catch (e) {
      debugPrint('[BLE] Status subscribe error (non-fatal): $e');
    }
  }

  void _showHotspotDialog() {
    if (!mounted) return;
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: const Text('Enable Hotspot Now'),
        content: const Text(
          'MiniK is trying to connect.\nPlease enable your phone hotspot, then tap Done.',
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              if (mounted) {
                setState(() => _statusMsg = '⏳ Hotspot enabled — Pi connecting...');
              }
            },
            child: const Text('Done'),
          ),
        ],
      ),
    );
  }

  // ── Poll IP characteristic every 2s ──────────────────────────────────────
  void _startPolling() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (timer) async {
      // FIX: check mounted BEFORE async call
      if (!mounted || _navigated) {
        timer.cancel();
        return;
      }

      try {
        final ipChar = _findChar(_charIp);
        if (ipChar == null) return;

        final bytes = await ipChar.read();

        // FIX: check mounted AGAIN after the await returns — widget may have
        // been disposed while the BLE read was in-flight
        if (!mounted || _navigated) {
          timer.cancel();
          return;
        }

        final ip = String.fromCharCodes(bytes).trim();
        if (ip.isNotEmpty && ip.contains('.')) {
          _navigated = true; // FIX: set flag before navigating to prevent re-entry
          timer.cancel();
          _navigateToViewData(ip);
        }
      } catch (e) {
        debugPrint('[BLE] Poll error: $e');
      }
    });
  }

  void _navigateToViewData(String ip) {
    if (!mounted) return;
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(
        builder: (c) => ViewDataPage(
          ip: ip,
          deviceName: widget.device.platformName,
        ),
      ),
      (route) => route.isFirst,
    );
  }

  Future<void> _sendCredentials() async {
    final ssid     = _ssidCtrl.text.trim();
    final password = _passwordCtrl.text.trim();
    if (ssid.isEmpty || password.isEmpty) return;

    setState(() { _sending = true; _statusMsg = 'Sending...'; });

    try {
      final adapterName = await FlutterBluePlus.adapterName;
      final phoneName   = adapterName.isNotEmpty ? adapterName : 'MiniK-Phone';

      await _writeStr(_charBleName, phoneName);
      if (mounted) setState(() => _statusMsg = 'Sending name... (1/4)');

      await _writeStr(_charBleMac, phoneName);
      if (mounted) setState(() => _statusMsg = 'Sending identity... (2/4)');

      await _writeStr(_charSsid, ssid);
      if (mounted) setState(() => _statusMsg = 'Sending SSID... (3/4)');

      await _writeStr(_charPassword, password);
      if (mounted) {
        setState(() => _statusMsg = '✅ Credentials sent!\nWaiting for Pi to connect...');
      }

      _startPolling();

    } catch (e) {
      debugPrint('[BLE] _sendCredentials error: $e');
      if (mounted) setState(() => _statusMsg = '❌ Error: $e');
    } finally {
      // FIX: ALWAYS reset _sending in finally — previously never reset on success
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  void initState() {
    super.initState();
    _connSub = widget.device.connectionState.listen((s) {
      if (mounted) setState(() => _connState = s);
    });
    Future.delayed(
      const Duration(milliseconds: 500),
      _subscribeToStatus,
    );
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _statusSub?.cancel();
    _connSub.cancel();
    _ssidCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final connected = _connState == BluetoothConnectionState.connected;
    return Scaffold(
      appBar: AppBar(title: Text(widget.device.platformName)),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Connection indicator
            Row(
              children: [
                Icon(
                  connected
                      ? Icons.bluetooth_connected
                      : Icons.bluetooth_disabled,
                  color: connected ? Colors.green : Colors.red,
                ),
                const SizedBox(width: 8),
                Text(
                  connected ? 'Connected to Pi' : 'Disconnected',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: connected ? Colors.green : Colors.red,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            TextField(
              controller: _ssidCtrl,
              decoration: const InputDecoration(
                labelText: 'Hotspot SSID',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.wifi),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _passwordCtrl,
              obscureText: _obscurePass,
              decoration: InputDecoration(
                labelText: 'Hotspot Password',
                border: const OutlineInputBorder(),
                prefixIcon: const Icon(Icons.lock),
                suffixIcon: IconButton(
                  icon: Icon(
                    _obscurePass ? Icons.visibility : Icons.visibility_off,
                  ),
                  onPressed: () =>
                      setState(() => _obscurePass = !_obscurePass),
                ),
              ),
            ),
            const SizedBox(height: 20),

            ElevatedButton.icon(
              onPressed: (_sending || !connected) ? null : _sendCredentials,
              icon: _sending
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.send),
              label: Text(_sending ? 'Sending...' : 'Send to MiniK'),
              style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14)),
            ),

            if (_statusMsg.isNotEmpty) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.blue.shade300),
                ),
                child: Text(_statusMsg, textAlign: TextAlign.center),
              ),
            ],

            const Spacer(),
            OutlinedButton.icon(
              onPressed: () => widget.device
                  .disconnect()
                  .then((_) => Navigator.pop(context)),
              icon: const Icon(Icons.bluetooth_disabled, color: Colors.red),
              label: const Text('Disconnect',
                  style: TextStyle(color: Colors.red)),
            ),
          ],
        ),
      ),
    );
  }
}

// ── View Data Page ──────────────────────────────────────────────────────────

class ViewDataPage extends StatelessWidget {
  final String ip;
  final String deviceName;
  const ViewDataPage(
      {super.key, required this.ip, required this.deviceName});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
          title: Text(deviceName), backgroundColor: Colors.green),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.check_circle, color: Colors.green, size: 80),
            const SizedBox(height: 20),
            const Text(
              'Pi Connected!',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            Text(
              'IP: $ip',
              style: const TextStyle(
                  fontSize: 20,
                  fontFamily: 'monospace',
                  color: Colors.blueGrey),
            ),
            const SizedBox(height: 40),
            // ── Add your data stream widgets here ─────────────────────────
            Container(
              padding: const EdgeInsets.all(20),
              margin: const EdgeInsets.symmetric(horizontal: 20),
              decoration: BoxDecoration(
                color: Colors.grey.shade200,
                borderRadius: BorderRadius.circular(10),
              ),
              child:
                  Text('http://$ip:8765  ← connect your data stream here'),
            ),
            const SizedBox(height: 30),
            ElevatedButton(
              onPressed: () =>
                  Navigator.of(context).popUntil((r) => r.isFirst),
              child: const Text('Back to Home'),
            ),
          ],
        ),
      ),
    );
  }
}*/
import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:http/http.dart' as http;

// ── Must match ble_manager.py exactly ──────────────────────────────────────
const String _serviceUuid  = '12345678-1234-1234-1234-123456789ab0';
const String _charSsid     = '12345678-1234-1234-1234-123456789ab1';
const String _charPassword = '12345678-1234-1234-1234-123456789ab2';
const String _charBleName  = '12345678-1234-1234-1234-123456789ab3';
const String _charBleMac   = '12345678-1234-1234-1234-123456789ab4';
const String _charIp       = '12345678-1234-1234-1234-123456789ab5';
const String _charStatus   = '12345678-1234-1234-1234-123456789ab6';

const int _flaskPort = 8765;

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

// ── Hotspot Page ─────────────────────────────────────────────────────────────

class HotspotPage extends StatefulWidget {
  final BluetoothDevice device;
  final List<BluetoothService> services;
  const HotspotPage({super.key, required this.device, required this.services});
  @override
  State<HotspotPage> createState() => _HotspotPageState();
}

class _HotspotPageState extends State<HotspotPage> {
  BluetoothConnectionState _connState = BluetoothConnectionState.connected;
  late StreamSubscription _connSub;
  StreamSubscription? _statusSub;
  StreamSubscription? _ipSub;      // ← NEW: notify subscription
  Timer? _pollTimer;

  final _ssidCtrl     = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _obscurePass   = true;
  bool _sending       = false;
  bool _navigated     = false;
  String _statusMsg   = '';

  // ── UUID helper ───────────────────────────────────────────────────────────
  BluetoothCharacteristic? _findChar(String uuid) {
    for (final svc in widget.services) {
      if (!svc.uuid.toString().toLowerCase().contains(_serviceUuid)) continue;
      for (final c in svc.characteristics) {
        if (c.uuid.toString().toLowerCase().contains(uuid)) return c;
      }
    }
    return null;
  }

  Future<void> _writeStr(String uuid, String value) async {
    final c = _findChar(uuid);
    if (c == null) throw Exception('Characteristic $uuid not found');
    await c.write(value.codeUnits, withoutResponse: false);
    debugPrint('[BLE] → Wrote ${uuid.substring(uuid.length - 4)}: '
        '${uuid == _charPassword ? "***" : value}');
  }

  // ── Subscribe to Pi STATUS notify (enable_hotspot) ────────────────────────
  Future<void> _subscribeToStatus() async {
    final c = _findChar(_charStatus);
    if (c == null) return;
    try {
      await c.setNotifyValue(true);
      _statusSub = c.onValueReceived.listen((value) {
        if (!mounted) return;
        final status = String.fromCharCodes(value).trim();
        debugPrint('[BLE] ← Pi status notify: $status');
        if (status == 'enable_hotspot') _showHotspotDialog();
      });
      debugPrint('[BLE] Subscribed to STATUS notifications');
    } catch (e) {
      debugPrint('[BLE] Status subscribe error (non-fatal): $e');
    }
  }

  // ── NEW: Subscribe to Pi IP notify ───────────────────────────────────────
  // Pi writes IP to this char and sends a notify right before dropping BLE.
  // This fires BEFORE the BLE connection drops, so we never miss it.
  Future<void> _subscribeToIp() async {
    final c = _findChar(_charIp);
    if (c == null) {
      debugPrint('[BLE] IP char not found — polling only');
      return;
    }
    try {
      await c.setNotifyValue(true);
      _ipSub = c.onValueReceived.listen((bytes) {
        if (!mounted || _navigated) return;
        final ip = String.fromCharCodes(bytes).trim();
        debugPrint('[BLE] ← IP notify received: $ip');
        if (ip.isNotEmpty && ip.contains('.')) {
          _navigated = true;
          _pollTimer?.cancel(); // notify beat the poll — stop it
          if (mounted) setState(() => _statusMsg = '📶 Pi connected to WiFi!\nConfirming via HTTP...');
          _confirmAndNavigate(ip);
        }
      });
      debugPrint('[BLE] Subscribed to IP notifications');
    } catch (e) {
      debugPrint('[BLE] IP subscribe error (non-fatal): $e');
    }
  }

  // ── HTTP ping: confirm Flask is actually up before navigating ─────────────
  // Retries every 2s for up to 30s total (Flask may need a second to start).
  Future<void> _confirmAndNavigate(String ip) async {
    final url = Uri.parse('http://$ip:$_flaskPort/status');
    const maxAttempts = 15;

    for (int i = 0; i < maxAttempts; i++) {
      if (!mounted) return;
      try {
        debugPrint('[HTTP] Pinging $url (attempt ${i + 1}/$maxAttempts)');
        final response = await http.get(url).timeout(const Duration(seconds: 3));

        if (response.statusCode == 200) {
          debugPrint('[HTTP] ✅ Flask responded: ${response.body}');
          if (mounted) {
            Navigator.pushAndRemoveUntil(
              context,
              MaterialPageRoute(
                builder: (c) => ViewDataPage(
                  ip: ip,
                  deviceName: widget.device.platformName,
                  // Pass any data from the /status response if needed
                  statusData: response.body,
                ),
              ),
              (route) => route.isFirst,
            );
          }
          return;
        }
      } catch (e) {
        debugPrint('[HTTP] Ping attempt ${i + 1} failed: $e');
      }

      // Update status message with attempt count so user isn't staring at nothing
      if (mounted) {
        setState(() => _statusMsg =
            '📶 Pi on WiFi — waiting for server...\n(${i + 1}/$maxAttempts)');
      }
      await Future.delayed(const Duration(seconds: 2));
    }

    // All attempts exhausted — navigate anyway with a warning
    debugPrint('[HTTP] All ping attempts failed — navigating anyway');
    if (mounted) {
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(
          builder: (c) => ViewDataPage(
            ip: ip,
            deviceName: widget.device.platformName,
            statusData: null,
          ),
        ),
        (route) => route.isFirst,
      );
    }
  }

  // ── Poll IP characteristic every 2s (fallback if notify is missed) ────────
  void _startPolling() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (timer) async {
      if (!mounted || _navigated) { timer.cancel(); return; }
      try {
        final ipChar = _findChar(_charIp);
        if (ipChar == null) return;
        final bytes = await ipChar.read();
        if (!mounted || _navigated) { timer.cancel(); return; }
        final ip = String.fromCharCodes(bytes).trim();
        if (ip.isNotEmpty && ip.contains('.')) {
          _navigated = true;
          timer.cancel();
          if (mounted) setState(() => _statusMsg = '📶 Pi on WiFi!\nConfirming via HTTP...');
          _confirmAndNavigate(ip);
        }
      } catch (e) {
        // BLE likely dropped — poll will naturally stop when _navigated is set
        // by the IP notify. If notify also failed, we keep polling until timeout.
        debugPrint('[BLE] Poll read error: $e');
      }
    });

    // Stop polling after 90s regardless — Pi has a 180s timeout on its side
    Future.delayed(const Duration(seconds: 90), () {
      if (!_navigated) {
        _pollTimer?.cancel();
        if (mounted) {
          setState(() => _statusMsg = '❌ Timed out. Pi may not have connected.\nTry again.');
          _sending = false;
        }
      }
    });
  }

  void _showHotspotDialog() {
    if (!mounted) return;
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: const Text('Enable Hotspot Now'),
        content: const Text(
          'MiniK is trying to connect to your hotspot.\nEnable it now, then tap Done.',
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              if (mounted) setState(() => _statusMsg = '⏳ Hotspot enabled — Pi is connecting...');
            },
            child: const Text('Done'),
          ),
        ],
      ),
    );
  }

  // ── Send all 4 credentials ────────────────────────────────────────────────
  Future<void> _sendCredentials() async {
    final ssid     = _ssidCtrl.text.trim();
    final password = _passwordCtrl.text.trim();
    if (ssid.isEmpty || password.isEmpty) return;

    setState(() { _sending = true; _statusMsg = 'Starting...'; });

    try {
      final adapterName = await FlutterBluePlus.adapterName;
      final phoneName   = adapterName.isNotEmpty ? adapterName : 'MiniK-Phone';

      await _writeStr(_charBleName, phoneName);
      if (mounted) setState(() => _statusMsg = 'Sending name... (1/4)');

      await _writeStr(_charBleMac, phoneName);
      if (mounted) setState(() => _statusMsg = 'Sending identity... (2/4)');

      await _writeStr(_charSsid, ssid);
      if (mounted) setState(() => _statusMsg = 'Sending SSID... (3/4)');

      await _writeStr(_charPassword, password);
      if (mounted) setState(() => _statusMsg = '✅ Credentials sent!\nWaiting for Pi to connect to WiFi...');

      // Start BOTH — notify fires first if BLE stays up long enough, 
      // poll catches it if BLE drops before notify is processed
      _startPolling();

    } catch (e) {
      debugPrint('[BLE] _sendCredentials error: $e');
      if (mounted) setState(() => _statusMsg = '❌ Error: $e');
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  void initState() {
    super.initState();
    _connSub = widget.device.connectionState.listen((s) {
      if (mounted) setState(() => _connState = s);
    });
    // Subscribe to both notifications right after connecting
    Future.delayed(const Duration(milliseconds: 500), () async {
      await _subscribeToStatus();
      await _subscribeToIp();
    });
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _statusSub?.cancel();
    _ipSub?.cancel();
    _connSub.cancel();
    _ssidCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final connected = _connState == BluetoothConnectionState.connected;
    return Scaffold(
      appBar: AppBar(title: Text(widget.device.platformName)),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(
                  connected ? Icons.bluetooth_connected : Icons.bluetooth_disabled,
                  color: connected ? Colors.green : Colors.red,
                ),
                const SizedBox(width: 8),
                Text(
                  connected ? 'Connected to Pi' : 'Disconnected',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: connected ? Colors.green : Colors.red,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _ssidCtrl,
              decoration: const InputDecoration(
                labelText: 'Hotspot SSID',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.wifi),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _passwordCtrl,
              obscureText: _obscurePass,
              decoration: InputDecoration(
                labelText: 'Hotspot Password',
                border: const OutlineInputBorder(),
                prefixIcon: const Icon(Icons.lock),
                suffixIcon: IconButton(
                  icon: Icon(_obscurePass ? Icons.visibility : Icons.visibility_off),
                  onPressed: () => setState(() => _obscurePass = !_obscurePass),
                ),
              ),
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: (_sending || !connected) ? null : _sendCredentials,
              icon: _sending
                  ? const SizedBox(
                      width: 18, height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.send),
              label: Text(_sending ? 'Sending...' : 'Send to MiniK'),
              style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14)),
            ),
            if (_statusMsg.isNotEmpty) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.blue.shade300),
                ),
                child: Text(_statusMsg, textAlign: TextAlign.center),
              ),
            ],
            const Spacer(),
            OutlinedButton.icon(
              onPressed: () =>
                  widget.device.disconnect().then((_) => Navigator.pop(context)),
              icon: const Icon(Icons.bluetooth_disabled, color: Colors.red),
              label: const Text('Disconnect', style: TextStyle(color: Colors.red)),
            ),
          ],
        ),
      ),
    );
  }
}

// ── View Data Page ──────────────────────────────────────────────────────────

class ViewDataPage extends StatefulWidget {
  final String ip;
  final String deviceName;
  final String? statusData;

  const ViewDataPage({
    super.key,
    required this.ip,
    required this.deviceName,
    this.statusData,
  });

  @override
  State<ViewDataPage> createState() => _ViewDataPageState();
}

class _ViewDataPageState extends State<ViewDataPage> {
  Timer? _heartbeatTimer;
  bool _piReachable = true;
  Map<String, dynamic> _sensorData = {};

  @override
  void initState() {
    super.initState();
    // Parse any data from the initial /status response
    if (widget.statusData != null) {
      try {
        _sensorData = jsonDecode(widget.statusData!) as Map<String, dynamic>;
      } catch (_) {}
    }
    // Start polling /status every 5s to keep data fresh and detect disconnection
    _startHeartbeat();
  }

  void _startHeartbeat() {
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 5), (_) async {
      if (!mounted) return;
      try {
        final response = await http
            .get(Uri.parse('http://${widget.ip}:$_flaskPort/status'))
            .timeout(const Duration(seconds: 4));
        if (!mounted) return;
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          setState(() { _piReachable = true; _sensorData = data; });
        }
      } catch (_) {
        if (mounted) setState(() => _piReachable = false);
      }
    });
  }

  @override
  void dispose() {
    _heartbeatTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.deviceName),
        backgroundColor: _piReachable ? Colors.green : Colors.red,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Icon(
              _piReachable ? Icons.wifi : Icons.wifi_off,
              color: Colors.white,
            ),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            // ── Connection status ──────────────────────────────────────────
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: _piReachable ? Colors.green.shade50 : Colors.red.shade50,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: _piReachable ? Colors.green : Colors.red,
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    _piReachable ? Icons.check_circle : Icons.error,
                    color: _piReachable ? Colors.green : Colors.red,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    _piReachable
                        ? 'Pi reachable at ${widget.ip}'
                        : 'Pi not responding — check hotspot',
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: _piReachable ? Colors.green.shade800 : Colors.red.shade800,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // ── Sensor data cards ──────────────────────────────────────────
            if (_sensorData.isNotEmpty)
              Expanded(
                child: GridView.builder(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                    childAspectRatio: 1.4,
                  ),
                  itemCount: _sensorData.length,
                  itemBuilder: (c, i) {
                    final key   = _sensorData.keys.elementAt(i);
                    final value = _sensorData[key];
                    return _SensorCard(label: key, value: '$value');
                  },
                ),
              )
            else
              Expanded(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const CircularProgressIndicator(),
                      const SizedBox(height: 16),
                      Text(
                        'Waiting for sensor data...\nhttp://${widget.ip}:$_flaskPort/status',
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                ),
              ),

            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: () =>
                  Navigator.of(context).popUntil((r) => r.isFirst),
              icon: const Icon(Icons.home),
              label: const Text('Back to Home'),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Sensor card widget ───────────────────────────────────────────────────────

class _SensorCard extends StatelessWidget {
  final String label;
  final String value;
  const _SensorCard({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.07),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 12,
              color: Colors.grey,
              fontWeight: FontWeight.w500,
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.bold,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }
}