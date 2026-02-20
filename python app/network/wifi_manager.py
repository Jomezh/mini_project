"""
WiFi manager - connects Pi to phone's hotspot,
gets Pi IP, serves Flask endpoint for data transfer.
"""

import subprocess
import socket
import time
import threading
import os

try:
    import netifaces
    HAS_NETIFACES = True
except ImportError:
    HAS_NETIFACES = False
    print("[WIFI] netifaces not installed: pip install netifaces")

try:
    import requests as req_lib
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[WIFI] requests not installed: pip install requests")


class WiFiManager:
    """
    Connects to phone's WiFi hotspot via nmcli.
    Runs Flask server for receiving CNN/ML results from phone.
    Sends images and CSVs to phone via HTTP.
    """

    FLASK_PORT = 8765   # Pi server port (heartbeat also uses this)
    PHONE_PORT = 8080   # Phone app server port

    def __init__(self):
        self._phone_ip     = None
        self._server_ready = threading.Event()
        self._results      = {}          # Stores incoming results keyed by type
        self._results_lock = threading.Lock()
        self._result_events = {
            'cnn_result': threading.Event(),
            'ml_result':  threading.Event(),
        }
        self._flask_thread = None

    # ── WiFi Connection ─────────────────────────────────

    def connect(self, ssid: str, password: str) -> bool:
        """
        Connect to phone's hotspot via nmcli.
        Uses 2-second delay so BLE can ACK the write before
        the network interface changes (avoids SSH drop glitch).
        """
        print(f"[WIFI] Scheduling connection to '{ssid}' in 2s...")

        def delayed():
            time.sleep(2)   # Give BLE time to respond before network changes
            self._do_connect(ssid, password)

        threading.Thread(target=delayed, daemon=True).start()

        # Wait for actual connection (max 30s)
        for _ in range(30):
            time.sleep(1)
            if self._is_connected_to(ssid):
                print(f"[WIFI] Connected to '{ssid}'")
                return True

        print(f"[WIFI] Failed to connect to '{ssid}'")
        return False

    def _do_connect(self, ssid: str, password: str):
        """Execute nmcli connect"""
        try:
            result = subprocess.run(
                ['nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password],
                capture_output=True, text=True, timeout=30
            )
            if 'successfully' in result.stdout.lower():
                print(f"[WIFI] nmcli connected to '{ssid}'")
                return

            # Try bringing up saved profile (already connected before)
            subprocess.run(
                ['nmcli', 'con', 'up', ssid],
                capture_output=True, timeout=15
            )

        except subprocess.TimeoutExpired:
            print("[WIFI] nmcli connect timeout")
        except Exception as e:
            print(f"[WIFI] nmcli error: {e}")

    def _is_connected_to(self, ssid: str) -> bool:
        """Check if currently connected to the given SSID"""
        try:
            result = subprocess.run(
                ['iwgetid', '-r'],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() == ssid
        except Exception:
            return False

    # ── IP Address ──────────────────────────────────────

    def get_local_ip(self) -> str:
        """
        Get Pi's current IP on wlan0 (phone's hotspot).
        Phone needs this to know where to connect for data transfer.
        """
        if HAS_NETIFACES:
            try:
                addrs = netifaces.ifaddresses('wlan0')
                ip = addrs[netifaces.AF_INET][0]['addr']
                print(f"[WIFI] Local IP (wlan0): {ip}")
                return ip
            except Exception:
                pass

        # Fallback: use socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            print(f"[WIFI] Local IP (fallback): {ip}")
            return ip
        except Exception as e:
            print(f"[WIFI] Could not get local IP: {e}")
            return None

    def _get_phone_ip(self) -> str:
        """
        Get phone's IP - it's the gateway when Pi is on phone's hotspot.
        """
        if self._phone_ip:
            return self._phone_ip

        if HAS_NETIFACES:
            try:
                gws = netifaces.gateways()
                gw  = gws['default'][netifaces.AF_INET][0]
                self._phone_ip = gw
                print(f"[WIFI] Phone IP (gateway): {gw}")
                return gw
            except Exception:
                pass

        return None

    # ── Flask Server (Pi side) ───────────────────────────

    def start_server(self):
        """Start Flask server to receive results from phone"""
        self._flask_thread = threading.Thread(
            target=self._run_flask,
            daemon=True,
            name="WiFiServer"
        )
        self._flask_thread.start()
        self._server_ready.wait(timeout=5)
        print(f"[WIFI] Server ready on port {self.FLASK_PORT}")

    def _run_flask(self):
        from flask import Flask, request, jsonify
        app = Flask(__name__)

        @app.route('/ping', methods=['GET'])
        def ping():
            return jsonify({'status': 'ok', 'device': 'minik'})

        @app.route('/result/<result_type>', methods=['POST'])
        def receive_result(result_type):
            data = request.json
            print(f"[WIFI SERVER] Received {result_type}: {data}")
            with self._results_lock:
                self._results[result_type] = data
            if result_type in self._result_events:
                self._result_events[result_type].set()
            return jsonify({'status': 'received'})

        self._server_ready.set()
        app.run(host='0.0.0.0', port=self.FLASK_PORT,
                debug=False, use_reloader=False)

    # ── Send Data to Phone ───────────────────────────────

    def send_image(self, image_path: str) -> bool:
        """POST image file to phone's server"""
        if not HAS_REQUESTS:
            return False
        url = self._build_phone_url('/upload_image')
        if not url:
            return False
        try:
            with open(image_path, 'rb') as f:
                resp = req_lib.post(
                    url,
                    files={'image': ('image.jpg', f, 'image/jpeg')},
                    timeout=30
                )
            ok = resp.status_code == 200
            print(f"[WIFI] Image send {'OK' if ok else 'FAILED'}: {resp.status_code}")
            return ok
        except Exception as e:
            print(f"[WIFI] Image send error: {e}")
            return False

    def send_file(self, file_path: str) -> bool:
        """POST CSV file to phone's server"""
        if not HAS_REQUESTS:
            return False
        url = self._build_phone_url('/upload_csv')
        if not url:
            return False
        try:
            fname = os.path.basename(file_path)
            with open(file_path, 'rb') as f:
                resp = req_lib.post(
                    url,
                    files={'csv': (fname, f, 'text/csv')},
                    timeout=15
                )
            ok = resp.status_code == 200
            print(f"[WIFI] CSV send {'OK' if ok else 'FAILED'}: {resp.status_code}")
            return ok
        except Exception as e:
            print(f"[WIFI] CSV send error: {e}")
            return False

    # ── Wait for Phone Results ───────────────────────────

    def wait_for_message(self, message_type: str, timeout: int = 120):
        """
        Block until phone POSTs a result to our Flask server.
        Returns result dict or None on timeout.
        """
        print(f"[WIFI] Waiting for {message_type} from phone...")

        event = self._result_events.get(message_type)
        if not event:
            print(f"[WIFI] Unknown message type: {message_type}")
            return None

        # Clear any stale result
        event.clear()
        with self._results_lock:
            self._results.pop(message_type, None)

        received = event.wait(timeout=timeout)

        if received:
            with self._results_lock:
                result = self._results.get(message_type)
            print(f"[WIFI] Got {message_type}: {result}")
            return result

        print(f"[WIFI] Timeout waiting for {message_type}")
        return None

    # ── Helpers ─────────────────────────────────────────

    def _build_phone_url(self, endpoint: str) -> str:
        phone_ip = self._get_phone_ip()
        if not phone_ip:
            print("[WIFI] Phone IP not known - cannot send")
            return None
        return f"http://{phone_ip}:{self.PHONE_PORT}{endpoint}"

    def stop(self):
        print("[WIFI] WiFiManager stopped")
