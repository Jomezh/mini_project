/*import 'dart:async';
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
}*/
/*
import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

const int _flaskPort = 8765; // must match wifi_manager.py FLASK_PORT

class ViewDataPage extends StatefulWidget {
  final String ip;
  final String deviceName;
  const ViewDataPage({super.key, required this.ip, required this.deviceName});

  @override
  State<ViewDataPage> createState() => _ViewDataPageState();
}

class _ViewDataPageState extends State<ViewDataPage> {
  Timer? _heartbeatTimer;
  Timer? _imageTimer;
  bool _piReachable = false;
  Map<String, dynamic> _sensorData = {};
  int _imgCounter = 0;
  String _connectionMsg = 'Connecting to Pi...';

  @override
  void initState() {
    super.initState();
    // First status ping immediately
    _pingStatus();
    // Then every 5s
    _heartbeatTimer = Timer.periodic(
      const Duration(seconds: 5), (_) => _pingStatus(),
    );
    // Refresh camera image every 2s (cache-busted via counter)
    _imageTimer = Timer.periodic(
      const Duration(seconds: 2),
      (_) { if (mounted) setState(() => _imgCounter++); },
    );
  }

  @override
  void dispose() {
    _heartbeatTimer?.cancel();
    _imageTimer?.cancel();
    super.dispose();
  }

  // ── Hit /status — confirms Pi reachable AND returns sensor data ──────────

  Future<void> _pingStatus() async {
    if (!mounted) return;
    try {
      final res = await http
          .get(Uri.parse('http://${widget.ip}:$_flaskPort/status'))
          .timeout(const Duration(seconds: 4));
      if (!mounted) return;
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        setState(() {
          _piReachable    = true;
          _sensorData     = data;
          _connectionMsg  = 'Pi connected · ${widget.ip}';
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _piReachable   = false;
          _connectionMsg = 'Pi not responding — is hotspot on?';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    // Cache-bust the image URL every tick so Image.network fetches a fresh frame
    final imgUrl = 'http://${widget.ip}:$_flaskPort/snapshot?v=$_imgCounter';

    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: Text(widget.deviceName),
        backgroundColor: _piReachable ? Colors.green : Colors.red,
        foregroundColor: Colors.white,
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
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [

            // ── Connection status banner ────────────────────────────────
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: _piReachable ? Colors.green.shade50 : Colors.red.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                    color: _piReachable ? Colors.green : Colors.red),
              ),
              child: Row(
                children: [
                  Icon(
                    _piReachable ? Icons.check_circle : Icons.error,
                    color: _piReachable ? Colors.green : Colors.red,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _connectionMsg,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                  if (!_piReachable)
                    const SizedBox(
                      width: 16, height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // ── Camera feed ─────────────────────────────────────────────
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Container(
                height: 260,
                color: Colors.black,
                child: Image.network(
                  imgUrl,
                  fit: BoxFit.cover,
                  // gaplessPlayback prevents white flash between frames
                  gaplessPlayback: true,
                  loadingBuilder: (_, child, progress) =>
                      progress == null
                          ? child
                          : const Center(
                              child: CircularProgressIndicator(color: Colors.green),
                            ),
                  errorBuilder: (_, __, ___) => Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.camera_alt,
                            color: Colors.grey.shade600, size: 48),
                        const SizedBox(height: 8),
                        Text(
                          _piReachable
                              ? 'Camera loading...'
                              : 'Camera unavailable',
                          style: TextStyle(color: Colors.grey.shade500),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // ── Sensor data grid ────────────────────────────────────────
            if (_sensorData.isNotEmpty) ...[
              const Text(
                'Sensor Readings',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              const SizedBox(height: 10),
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate:
                    const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 10,
                  mainAxisSpacing: 10,
                  childAspectRatio: 1.6,
                ),
                itemCount: _sensorData.length,
                itemBuilder: (_, i) {
                  final key   = _sensorData.keys.elementAt(i);
                  final value = _sensorData[key];
                  return _SensorCard(label: key, value: '$value');
                },
              ),
            ] else
              Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 30),
                  child: Text(
                    _piReachable
                        ? 'Waiting for sensor data...'
                        : 'Connect to Pi to see sensor data',
                    style: const TextStyle(color: Colors.grey),
                  ),
                ),
              ),

            const SizedBox(height: 24),
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

// ── Sensor card widget ────────────────────────────────────────────────────────

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
                fontWeight: FontWeight.w500),
          ),
          Text(
            value,
            style: const TextStyle(
                fontSize: 20, fontWeight: FontWeight.bold),
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}
*/
/*
import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

// Made public so hotspot.dart can use it for the initial connection ping
const int flaskPort = 8765;

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
            .get(Uri.parse('http://${widget.ip}:$flaskPort/status'))
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
                        'Waiting for sensor data...\nhttp://${widget.ip}:$flaskPort/status',
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
import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

// Made public so hotspot.dart can use it for the initial connection ping
const int flaskPort = 8765;

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
  Timer? _imageTimer;
  bool _piReachable = true;
  Map<String, dynamic> _sensorData = {};
  int _imageCounter = 0;

  @override
  void initState() {
    super.initState();
    if (widget.statusData != null) {
      try {
        _sensorData = jsonDecode(widget.statusData!) as Map<String, dynamic>;
      } catch (_) {}
    }
    _startHeartbeat();
    _startImageStream();
  }

  void _startHeartbeat() {
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 5), (_) async {
      if (!mounted) return;
      try {
        final response = await http
            .get(Uri.parse('http://${widget.ip}:$flaskPort/status'))
            .timeout(const Duration(seconds: 4));
        if (!mounted) return;
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          setState(() {
            _piReachable = true;
            _sensorData = data;
          });
        }
      } catch (_) {
        if (mounted) setState(() => _piReachable = false);
      }
    });
  }

  void _startImageStream() {
    // Refresh the image every 2 seconds by incrementing the cache-busting counter
    _imageTimer = Timer.periodic(const Duration(seconds: 2), (_) {
      if (mounted && _piReachable) {
        setState(() => _imageCounter++);
      }
    });
  }

  @override
  void dispose() {
    _heartbeatTimer?.cancel();
    _imageTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Construct the snapshot URL with the counter to bypass caching
    final String imageUrl = "http://${widget.ip}:$flaskPort/snapshot?v=$_imageCounter";

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
            // ── Connection Status ───────────────────────────────────────────
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

            // ── Camera Feed Preview ─────────────────────────────────────────
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Container(
                height: 250,
                width: double.infinity,
                color: Colors.black,
                child: Image.network(
                  imageUrl,
                  fit: BoxFit.cover,
                  gaplessPlayback: true, // Prevents white flashes between frame loads
                  loadingBuilder: (context, child, loadingProgress) {
                    if (loadingProgress == null) return child;
                    return const Center(
                      child: CircularProgressIndicator(color: Colors.green),
                    );
                  },
                  errorBuilder: (context, error, stackTrace) => Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.videocam_off, color: Colors.white54, size: 50),
                        const SizedBox(height: 10),
                        Text(
                          _piReachable ? "Waiting for Camera Stream..." : "Camera Unavailable",
                          style: const TextStyle(color: Colors.white54),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 20),

            // ── Sensor Data Grid ────────────────────────────────────────────
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
                    final key = _sensorData.keys.elementAt(i);
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
                        'Waiting for sensor data...\nhttp://${widget.ip}:$flaskPort/status',
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 16),
            
            // ── Controls ────────────────────────────────────────────────────
            OutlinedButton.icon(
              onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
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
/* lab work for pic only
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data'; // Added for Uint8List
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

// Made public so hotspot.dart can use it for the initial connection ping
const int flaskPort = 8765;

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
  
  // New variables to store the image in memory
  Uint8List? _imageData;
  bool _isImageLoading = true;
  String? _imageError;

  @override
  void initState() {
    super.initState();
    if (widget.statusData != null) {
      try {
        _sensorData = jsonDecode(widget.statusData!) as Map<String, dynamic>;
      } catch (_) {}
    }
    _startHeartbeat();
    _fetchImage(); // Fetch the image once when the screen loads
  }

  // Method to fetch the image and store it in _imageData
  Future<void> _fetchImage() async {
    final String imageUrl = "http://${widget.ip}:$flaskPort/snapshot";
    
    setState(() {
      _isImageLoading = true;
      _imageError = null;
    });

    try {
      final response = await http
          .get(Uri.parse(imageUrl))
          .timeout(const Duration(seconds: 10)); // Added a timeout

      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            _imageData = response.bodyBytes; // Store the image bytes in the program
            _isImageLoading = false;
          });
        }
      } else {
        if (mounted) {
          setState(() {
            _imageError = "Server returned ${response.statusCode}";
            _isImageLoading = false;
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _imageError = "Failed to load image";
          _isImageLoading = false;
        });
      }
    }
  }

  void _startHeartbeat() {
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 5), (_) async {
      if (!mounted) return;
      try {
        final response = await http
            .get(Uri.parse('http://${widget.ip}:$flaskPort/status'))
            .timeout(const Duration(seconds: 4));
        if (!mounted) return;
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          setState(() {
            _piReachable = true;
            _sensorData = data;
          });
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
          // Optional: A refresh button to manually grab a new image
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white),
            onPressed: _fetchImage, 
          ),
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
            // ── Connection Status ───────────────────────────────────────────
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

            // ── Camera Feed Preview (From Memory) ───────────────────────────
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Container(
                height: 250,
                width: double.infinity,
                color: Colors.black,
                child: _buildImagePreview(),
              ),
            ),
            const SizedBox(height: 20),

            // ── Sensor Data Grid ────────────────────────────────────────────
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
                    final key = _sensorData.keys.elementAt(i);
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
                        'Waiting for sensor data...\nhttp://${widget.ip}:$flaskPort/status',
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 16),
            
            // ── Controls ────────────────────────────────────────────────────
            OutlinedButton.icon(
              onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
              icon: const Icon(Icons.home),
              label: const Text('Back to Home'),
            ),
          ],
        ),
      ),
    );
  }

  // Helper widget to handle the image loading states
  Widget _buildImagePreview() {
    if (_isImageLoading) {
      return const Center(
        child: CircularProgressIndicator(color: Colors.green),
      );
    } else if (_imageData != null) {
      // Displaying the image directly from the stored bytes
      return Image.memory(
        _imageData!,
        fit: BoxFit.cover,
      );
    } else {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.broken_image, color: Colors.white54, size: 50),
            const SizedBox(height: 10),
            Text(
              _imageError ?? "Camera Unavailable",
              style: const TextStyle(color: Colors.white54),
            ),
          ],
        ),
      );
    }
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
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image/image.dart' as img; // For image processing
import 'package:tflite_flutter/tflite_flutter.dart'; // For AI logic

const int flaskPort = 8765;

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
  
  Uint8List? _imageData;
  bool _isImageLoading = true;
  String? _imageError;

  // AI Variables
  Interpreter? _interpreter;
  String _aiResult = "Waiting for Image...";

  @override
  void initState() {
    super.initState();
    _loadModel(); // Start loading model on init
    if (widget.statusData != null) {
      try {
        _sensorData = jsonDecode(widget.statusData!) as Map<String, dynamic>;
      } catch (_) {}
    }
    _startHeartbeat();
    _fetchImage(); 
  }

  // STEP A: Load the Model
  Future<void> _loadModel() async {
    try {
      _interpreter = await Interpreter.fromAsset('assets/food_classifier_model.tflite');
      debugPrint("Model loaded successfully");
    } catch (e) {
      debugPrint("Failed to load model: $e");
    }
  }

  Future<void> _fetchImage() async {
    final String imageUrl = "http://${widget.ip}:$flaskPort/snapshot";
    
    setState(() {
      _isImageLoading = true;
      _imageError = null;
    });

    try {
      final response = await http
          .get(Uri.parse(imageUrl))
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            _imageData = response.bodyBytes;
            _isImageLoading = false;
          });
          // STEP D: Automatically run inference on successful receipt
          _runInference(response.bodyBytes);
        }
      } else {
        setState(() {
          _imageError = "Server Error: ${response.statusCode}";
          _isImageLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _imageError = "Connection Failed";
        _isImageLoading = false;
      });
    }
  }

  // STEP B & C: Process Image and Run Inference
  void _runInference(Uint8List bytes) {
    if (_interpreter == null) {
      setState(() => _aiResult = "Model not loaded");
      return;
    }

    // 1. Decode and Resize
    img.Image? originalImage = img.decodeImage(bytes);
    if (originalImage == null) return;
    img.Image resizedImage = img.copyResize(originalImage, width: 224, height: 224);

    // 2. Normalize to Float32 List [1, 224, 224, 3]
    var input = List.generate(1 * 224 * 224 * 3, (i) => 0.0).reshape([1, 224, 224, 3]);
    for (var y = 0; y < 224; y++) {
      for (var x = 0; x < 224; x++) {
        var pixel = resizedImage.getPixel(x, y);
        input[0][y][x][0] = pixel.r / 255.0;
        input[0][y][x][1] = pixel.g / 255.0;
        input[0][y][x][2] = pixel.b / 255.0;
      }
    }

    // 3. Run the model (Assuming 2 categories: index 0 = Beef, index 1 = Other)
    var output = List.filled(1 * 2, 0.0).reshape([1, 2]);
    _interpreter!.run(input, output);

    // 4. Logic: If index 0 is higher, it's Beef
    setState(() {
      if (output[0][0] > output[0][1]) {
        _aiResult = "BEEF DETECTED";
        _sendSignalToPi("ACTIVATE_BEEF_SENSORS");
      } else {
        _aiResult = "OTHER FOOD";
      }
    });
  }

  // Optional: Send a command back to the Pi based on detection
  Future<void> _sendSignalToPi(String command) async {
    try {
      await http.post(
        Uri.parse('http://${widget.ip}:$flaskPort/command'),
        body: jsonEncode({'action': command}),
      );
    } catch (_) {}
  }

  void _startHeartbeat() {
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 5), (_) async {
      if (!mounted) return;
      try {
        final response = await http
            .get(Uri.parse('http://${widget.ip}:$flaskPort/status'))
            .timeout(const Duration(seconds: 4));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          if (mounted) setState(() { _piReachable = true; _sensorData = data; });
        }
      } catch (_) {
        if (mounted) setState(() => _piReachable = false);
      }
    });
  }

  @override
  void dispose() {
    _heartbeatTimer?.cancel();
    _interpreter?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.deviceName),
        backgroundColor: _piReachable ? Colors.green : Colors.red,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _fetchImage),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            // ── AI Classification Status ────────────────────────────────────
            Container(
              width: double.infinity,
              margin: const EdgeInsets.only(bottom: 20),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.blue.shade900,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Column(
                children: [
                  const Text("AI ANALYSIS", style: TextStyle(color: Colors.white70, fontSize: 12)),
                  Text(_aiResult, style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
                ],
              ),
            ),

            // ── Camera Feed Preview ─────────────────────────────────────────
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Container(
                height: 250,
                width: double.infinity,
                color: Colors.black,
                child: _buildImagePreview(),
              ),
            ),
            const SizedBox(height: 20),

            // ── Sensor Data Grid ────────────────────────────────────────────
            if (_sensorData.isNotEmpty)
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2, crossAxisSpacing: 12, mainAxisSpacing: 12, childAspectRatio: 1.4,
                ),
                itemCount: _sensorData.length,
                itemBuilder: (c, i) {
                  final key = _sensorData.keys.elementAt(i);
                  return _SensorCard(label: key, value: '${_sensorData[key]}');
                },
              ),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
              icon: const Icon(Icons.home),
              label: const Text('Back to Home'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildImagePreview() {
    if (_isImageLoading) return const Center(child: CircularProgressIndicator(color: Colors.green));
    if (_imageData != null) return Image.memory(_imageData!, fit: BoxFit.cover);
    return Center(child: Text(_imageError ?? "No Image", style: const TextStyle(color: Colors.white)));
  }
}

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
        boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 4)],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
          Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}*/
/*
/*
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'image_classifier.dart'; // <--- Import your separate file

const int flaskPort = 8765;

class ViewDataPage extends StatefulWidget {
  final String ip;
  final String deviceName;
  final String? statusData;

  const ViewDataPage({super.key, required this.ip, required this.deviceName, this.statusData});

  @override
  State<ViewDataPage> createState() => _ViewDataPageState();
}

class _ViewDataPageState extends State<ViewDataPage> {
  Timer? _heartbeatTimer;
  bool _piReachable = true;
  Map<String, dynamic> _sensorData = {};
  
  Uint8List? _imageData; // This is your "Image Store"
  bool _isImageLoading = true;
  String? _imageError;

  // AI Variables
  final ImageClassifier _classifier = ImageClassifier();
  String _aiResult = "Waiting for Image...";

  @override
  void initState() {
    super.initState();
    _initAI(); // 1. Setup AI
    if (widget.statusData != null) {
      try {
        _sensorData = jsonDecode(widget.statusData!) as Map<String, dynamic>;
      } catch (_) {}
    }
    _startHeartbeat();
    _fetchImage(); 
  }

  Future<void> _initAI() async {
    await _classifier.loadModel();
  }

  Future<void> _fetchImage() async {
    final String imageUrl = "http://${widget.ip}:$flaskPort/snapshot";
    setState(() { _isImageLoading = true; _imageError = null; });

    try {
      final response = await http.get(Uri.parse(imageUrl)).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            _imageData = response.bodyBytes; // 2. Receive and Store image
            _isImageLoading = false;
          });

          // 3. Pass the "Image Store" to the other file for classification
          String result = await _classifier.classify(response.bodyBytes);
          
          setState(() {
            _aiResult = result;
          });
        }
      }
    } catch (e) {
      if (mounted) setState(() => _isImageLoading = false);
    }
  }

  @override
  void dispose() {
    _heartbeatTimer?.cancel();
    _classifier.dispose(); // Clean up model
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.deviceName),
        backgroundColor: _piReachable ? Colors.green : Colors.red,
        actions: [ IconButton(icon: const Icon(Icons.refresh), onPressed: _fetchImage) ],
      ),
      body: Column(
        children: [
          // Display the AI Result prominently
          Card(
            margin: const EdgeInsets.all(20),
            color: _aiResult == "Beef" ? Colors.orange.shade100 : Colors.blue.shade100,
            child: ListTile(
              leading: const Icon(Icons.analytics),
              title: const Text("AI Classification Result"),
              subtitle: Text(_aiResult, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            ),
          ),
          
          // Image Preview
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Container(
              height: 250, width: double.infinity, color: Colors.black,
              child: _buildImagePreview(),
            ),
          ),
          
          // ... rest of your sensor grid UI ...
        ],
      ),
    );
  }

  Widget _buildImagePreview() {
    if (_isImageLoading) return const Center(child: CircularProgressIndicator());
    if (_imageData != null) return Image.memory(_imageData!, fit: BoxFit.cover);
    return Center(child: Text(_imageError ?? "Camera Unavailable", style: const TextStyle(color: Colors.white)));
  }
}*/
/*import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

const int flaskPort = 8765;

class ViewDataPage extends StatefulWidget {
  final String ip;
  final String deviceName;
  final String? statusData;

  const ViewDataPage({
    super.key, 
    required this.ip, 
    required this.deviceName, 
    this.statusData
  });

  @override
  State<ViewDataPage> createState() => _ViewDataPageState();
}

class _ViewDataPageState extends State<ViewDataPage> {
  Timer? _heartbeatTimer;
  bool _piReachable = true;
  Map<String, dynamic> _sensorData = {};
  
  Uint8List? _imageData; 
  bool _isImageLoading = true;
  String? _imageError;

  @override
  void initState() {
    super.initState();
    // Initialize sensor data if passed from previous screen
    if (widget.statusData != null) {
      try { 
        _sensorData = jsonDecode(widget.statusData!) as Map<String, dynamic>; 
      } catch (_) {}
    }
    _startHeartbeat();
    _fetchImage(); 
  }

  /// Fetches the latest snapshot from the Pi's Flask server
  Future<void> _fetchImage() async {
    // Adding a timestamp 't' prevents the app from showing a cached old image
    final String imageUrl = "http://${widget.ip}:$flaskPort/snapshot?t=${DateTime.now().millisecondsSinceEpoch}";
    
    if (!mounted) return;
    setState(() {
      _isImageLoading = true;
      _imageError = null;
    });

    try {
      final response = await http.get(Uri.parse(imageUrl)).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            _imageData = response.bodyBytes; 
            _isImageLoading = false;
          });
        }
      } else {
        throw Exception("Server Error: ${response.statusCode}");
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _imageError = "Could not connect to Camera";
          _isImageLoading = false;
        });
      }
    }
  }

  /// Polls the Raspberry Pi every 5 seconds for JSON sensor updates
  void _startHeartbeat() {
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 5), (_) async {
      if (!mounted) return;
      try {
        final response = await http
            .get(Uri.parse('http://${widget.ip}:$flaskPort/status'))
            .timeout(const Duration(seconds: 4));
        
        if (!mounted) return;
        
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          setState(() {
            _piReachable = true;
            _sensorData = data;
          });
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
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: Text(widget.deviceName),
        centerTitle: true,
        backgroundColor: _piReachable ? Colors.green : Colors.redAccent,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh), 
            onPressed: _fetchImage,
            tooltip: "Refresh Image",
          )
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Connection Status Banner
            if (!_piReachable)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(8),
                margin: const EdgeInsets.only(bottom: 15),
                decoration: BoxDecoration(color: Colors.red[100], borderRadius: BorderRadius.circular(8)),
                child: const Text("Pi Offline - Checking connection...", 
                    textAlign: TextAlign.center, style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
              ),

            const Text("LIVE CAMERA", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.blueGrey)),
            const SizedBox(height: 10),

            // ── Image Preview Card ──
            ClipRRect(
              borderRadius: BorderRadius.circular(15),
              child: Container(
                height: 280,
                width: double.infinity,
                color: Colors.black87,
                child: _isImageLoading 
                  ? const Center(child: CircularProgressIndicator(color: Colors.white)) 
                  : (_imageData != null 
                      ? Image.memory(_imageData!, fit: BoxFit.contain) 
                      : Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.videocam_off, color: Colors.white24, size: 50),
                              Text(_imageError ?? "No Image Data", style: const TextStyle(color: Colors.white54)),
                            ],
                          ))),
              ),
            ),
            
            const SizedBox(height: 25),
            const Text("SENSOR TELEMETRY", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.blueGrey)),
            const SizedBox(height: 10),

            // ── Sensor Data Grid ──
            if (_sensorData.isNotEmpty)
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2, 
                  crossAxisSpacing: 12, 
                  mainAxisSpacing: 12, 
                  childAspectRatio: 1.5,
                ),
                itemCount: _sensorData.length,
                itemBuilder: (context, index) {
                  final key = _sensorData.keys.elementAt(index);
                  return _SensorCard(label: key, value: '${_sensorData[key]}');
                },
              )
            else
              const Center(child: Padding(
                padding: EdgeInsets.all(20.0),
                child: Text("Waiting for sensor data..."),
              )),
          ],
        ),
      ),
    );
  }
}

class _SensorCard extends StatelessWidget {
  final String label;
  final String value;
  const _SensorCard({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 10, offset: const Offset(0, 4))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label.toUpperCase(), style: const TextStyle(fontSize: 10, letterSpacing: 1.1, color: Colors.grey, fontWeight: FontWeight.bold)),
          const Spacer(),
          Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: Colors.black87)),
        ],
      ),
    );
  }
}*/

*/

import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'ImageClassificationPage.dart'; // Ensure this filename matches your classification file

class ViewDataPage extends StatefulWidget {
  final String ip; // The IP address of your Raspberry Pi

  const ViewDataPage({super.key, required this.ip});

  @override
  State<ViewDataPage> createState() => _ViewDataPageState();
}

class _ViewDataPageState extends State<ViewDataPage> {
  Uint8List? _imageBytes;
  bool _isLoading = false;
  String _message = "Ready to capture";
  final int _flaskPort = 8765; // Matches your Pi's Flask port

  // 1. Fetch the raw image bytes from the Pi
  Future<void> _fetchImage() async {
    setState(() {
      _isLoading = true;
      _message = "Connecting to Pi...";
      _imageBytes = null;
    });

    try {
      // Endpoint where your Pi serves the image
      final url = Uri.parse('http://${widget.ip}:$_flaskPort/image');
      final response = await http.get(url).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        setState(() {
          _imageBytes = response.bodyBytes; // Raw binary data
          _isLoading = false;
          _message = "Image received successfully!";
        });
      } else {
        setState(() {
          _isLoading = false;
          _message = "Server Error: ${response.statusCode}";
        });
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _message = "Error: Check Pi IP and Connection";
      });
      debugPrint("Fetch Error: $e");
    }
  }

  // 2. Navigate to your Classification Page with the data
  void _goToClassification() {
    if (_imageBytes == null) return;

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ImageClassificationPage(
          imageData: _imageBytes!, // Passes the bytes to your page
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Pi Image Capture"),
        backgroundColor: Colors.blueAccent,
      ),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          children: [
            // Display connection info
            Text("Pi Address: ${widget.ip}:$_flaskPort",
                style: const TextStyle(color: Colors.grey)),
            const SizedBox(height: 20),

            // Image Display Area
            Expanded(
              child: Container(
                width: double.infinity,
                decoration: BoxDecoration(
                  color: Colors.grey[200],
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.grey[400]!),
                ),
                child: _isLoading
                    ? const Center(child: CircularProgressIndicator())
                    : _imageBytes != null
                        ? ClipRRect(
                            borderRadius: BorderRadius.circular(12),
                            child: Image.memory(_imageBytes!, fit: BoxFit.contain),
                          )
                        : const Center(
                            child: Text("No image captured"),
                          ),
              ),
            ),

            const SizedBox(height: 20),
            Text(_message, style: const TextStyle(fontSize: 16)),
            const SizedBox(height: 20),

            // Buttons
            Row(
              children: [
                // Fetch Button
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isLoading ? null : _fetchImage,
                    icon: const Icon(Icons.camera_alt),
                    label: const Text("Capture"),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 15),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                
                // Classify Button (Enabled only when image exists)
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _imageBytes == null ? null : _goToClassification,
                    icon: const Icon(Icons.analytics),
                    label: const Text("Classify"),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 15),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}