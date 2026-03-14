/*import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:http/http.dart' as http;

// ── Constants for BLE and HTTP ─────────────────────────────────────────────
const String _serviceUuid  = '12345678-1234-1234-1234-123456789ab0';
const String _charSsid     = '12345678-1234-1234-1234-123456789ab1';
const String _charPassword = '12345678-1234-1234-1234-123456789ab2';
const String _charBleName  = '12345678-1234-1234-1234-123456789ab3';
const String _charBleMac   = '12345678-1234-1234-1234-123456789ab4';
const String _charIp       = '12345678-1234-1234-1234-123456789ab5';
const String _charStatus   = '12345678-1234-1234-1234-123456789ab6';

const int _flaskPort = 8765;

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

  // ── Subscribe to Pi IP notify ───────────────────────────────────────
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

      if (mounted) {
        setState(() => _statusMsg =
            '📶 Pi on WiFi — waiting for server...\n(${i + 1}/$maxAttempts)');
      }
      await Future.delayed(const Duration(seconds: 2));
    }

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
        debugPrint('[BLE] Poll read error: $e');
      }
    });

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
    if (widget.statusData != null) {
      try {
        _sensorData = jsonDecode(widget.statusData!) as Map<String, dynamic>;
      } catch (_) {}
    }
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
}*/
/*
laetest faile for hotspot page, not yet fully implemented. 
*/
/*
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:http/http.dart' as http;
import 'viewdata.dart'; 
// Import the view data page and its constants


// ── Constants for BLE ──────────────────────────────────────────────────────
const String _serviceUuid  = '12345678-1234-1234-1234-123456789ab0';
const String _charSsid     = '12345678-1234-1234-1234-123456789ab1';
const String _charPassword = '12345678-1234-1234-1234-123456789ab2';
const String _charBleName  = '12345678-1234-1234-1234-123456789ab3';
const String _charBleMac   = '12345678-1234-1234-1234-123456789ab4';
const String _charIp       = '12345678-1234-1234-1234-123456789ab5';
const String _charStatus   = '12345678-1234-1234-1234-123456789ab6';

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
  StreamSubscription? _ipSub;      
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

  // ── Subscribe to Pi IP notify ───────────────────────────────────────
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
          _pollTimer?.cancel(); 
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
  Future<void> _confirmAndNavigate(String ip) async {
    // Note: flaskPort is imported from viewdata.dart
    final url = Uri.parse('http://$ip:$flaskPort/status');
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

      if (mounted) {
        setState(() => _statusMsg =
            '📶 Pi on WiFi — waiting for server...\n(${i + 1}/$maxAttempts)');
      }
      await Future.delayed(const Duration(seconds: 2));
    }

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
        debugPrint('[BLE] Poll read error: $e');
      }
    });

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
}*/
/*
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:http/http.dart' as http;

import 'ViewDataPage.dart'; // Import the second file

// ── Constants for BLE and HTTP ─────────────────────────────────────────────
const String _serviceUuid  = '12345678-1234-1234-1234-123456789ab0';
const String _charSsid     = '12345678-1234-1234-1234-123456789ab1';
const String _charPassword = '12345678-1234-1234-1234-123456789ab2';
const String _charBleName  = '12345678-1234-1234-1234-123456789ab3';
const String _charBleMac   = '12345678-1234-1234-1234-123456789ab4';
const String _charIp       = '12345678-1234-1234-1234-123456789ab5';
const String _charStatus   = '12345678-1234-1234-1234-123456789ab6';

const int _flaskPort = 8765;

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
  StreamSubscription? _ipSub;
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

  // ── Subscribe to Pi IP notify ───────────────────────────────────────
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
  Future<void> _confirmAndNavigate(String ip) async {
    // Note: We're still pinging the base/status route to confirm it's online
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

      if (mounted) {
        setState(() => _statusMsg =
            '📶 Pi on WiFi — waiting for server...\n(${i + 1}/$maxAttempts)');
      }
      await Future.delayed(const Duration(seconds: 2));
    }

    debugPrint('[HTTP] All ping attempts failed — navigating anyway');
    if (mounted) {
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
        debugPrint('[BLE] Poll read error: $e');
      }
    });

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
}*/
import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:http/http.dart' as http;

// ── Constants for BLE and HTTP ─────────────────────────────────────────────
const String _serviceUuid  = '12345678-1234-1234-1234-123456789ab0';
const String _charSsid     = '12345678-1234-1234-1234-123456789ab1';
const String _charPassword = '12345678-1234-1234-1234-123456789ab2';
const String _charBleName  = '12345678-1234-1234-1234-123456789ab3';
const String _charBleMac   = '12345678-1234-1234-1234-123456789ab4';
const String _charIp       = '12345678-1234-1234-1234-123456789ab5';
const String _charStatus   = '12345678-1234-1234-1234-123456789ab6';

const int _flaskPort = 8765;

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

  // ── Subscribe to Pi IP notify ───────────────────────────────────────
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

      if (mounted) {
        setState(() => _statusMsg =
            '📶 Pi on WiFi — waiting for server...\n(${i + 1}/$maxAttempts)');
      }
      await Future.delayed(const Duration(seconds: 2));
    }

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
        debugPrint('[BLE] Poll read error: $e');
      }
    });

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
    if (widget.statusData != null) {
      try {
        _sensorData = jsonDecode(widget.statusData!) as Map<String, dynamic>;
      } catch (_) {}
    }
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