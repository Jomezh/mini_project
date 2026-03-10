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
    print("[WIFI] netifaces not installed — pip install netifaces")


try:
    import requests as reqlib
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[WIFI] requests not installed — pip install requests")


class WiFiManager:
    """
    Connects to phone's WiFi hotspot via nmcli.
    Runs Flask server for receiving CNN/ML results from phone.
    Sends images and CSVs to phone via HTTP.
    """

    FLASK_PORT = 8765
    PHONE_PORT = 8080

    def __init__(self):
        self.phone_ip      = None
        self.server_ready  = threading.Event()
        self.results       = {}
        self.results_lock  = threading.Lock()
        self.result_events = {
            'cnn_result': threading.Event(),
            'ml_result':  threading.Event(),
        }
        self.flask_thread  = None
        self._flask_server = None

    # ── WiFi connect ──────────────────────────────────────────────────────

    def connect(self, ssid: str, password: str = None) -> bool:
        print(f"[WIFI] Scheduling connection to '{ssid}' in 2s...")
        threading.Thread(
            target=self._do_connect, args=(ssid, password), daemon=True
        ).start()
        for _ in range(45):
            time.sleep(1)
            if self.is_connected_to(ssid):
                print(f"[WIFI] Connected to '{ssid}' ✓")
                return True
        print(f"[WIFI] Failed to connect to '{ssid}' after 45s")
        return False

    def _do_connect(self, ssid: str, password: str = None):
        try:
            time.sleep(2)  # BLE ACK window

            print("[WIFI] Running blocking rescan (nmcli dev wifi list --rescan yes)...")
            scan_result = subprocess.run(
                ['nmcli', 'dev', 'wifi', 'list', '--rescan', 'yes'],
                capture_output=True, text=True, timeout=20
            )
            if ssid not in scan_result.stdout:
                print(f"[WIFI] WARNING: '{ssid}' not visible after rescan — hotspot may still be starting")
            else:
                print(f"[WIFI] '{ssid}' confirmed visible in scan ✓")

            if password:
                cmd = ['nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password]
                print(f"[WIFI] Connecting to '{ssid}' with password")
            elif self._profile_exists(ssid):
                cmd = ['nmcli', 'con', 'up', ssid]
                print(f"[WIFI] Bringing up saved profile for '{ssid}'")
            else:
                print(f"[WIFI] No saved profile for '{ssid}' and no password — cannot connect")
                return

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if 'successfully' in stdout.lower() or result.returncode == 0:
                print(f"[WIFI] nmcli connected to '{ssid}' ✓")
            else:
                print(f"[WIFI] nmcli stdout: {stdout}")
                if stderr:
                    print(f"[WIFI] nmcli stderr: {stderr}")
                if password:
                    print(f"[WIFI] Fallback: trying saved profile 'nmcli con up {ssid}'")
                    subprocess.run(
                        ['nmcli', 'con', 'up', ssid],
                        capture_output=True, timeout=15
                    )

        except subprocess.TimeoutExpired:
            print("[WIFI] nmcli connect timeout")
        except Exception as e:
            print(f"[WIFI] nmcli error: {e}")

    def _profile_exists(self, ssid: str) -> bool:
        try:
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'NAME', 'con', 'show'],
                capture_output=True, text=True, timeout=5
            )
            return ssid in result.stdout
        except Exception:
            return False

    def is_connected_to(self, ssid: str) -> bool:
        try:
            result = subprocess.run(
                ['iwgetid', '-r'],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() == ssid
        except Exception:
            return False

    # ── IP helpers ────────────────────────────────────────────────────────

    def get_local_ip(self) -> str:
        if HAS_NETIFACES:
            try:
                addrs = netifaces.ifaddresses('wlan0')
                ip    = addrs[netifaces.AF_INET][0]['addr']
                print(f"[WIFI] Local IP (wlan0): {ip}")
                return ip
            except Exception:
                pass
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

    def get_phone_ip(self) -> str:
        if self.phone_ip:
            return self.phone_ip
        if HAS_NETIFACES:
            try:
                gws = netifaces.gateways()
                gw  = gws['default'][netifaces.AF_INET][0]
                self.phone_ip = gw
                print(f"[WIFI] Phone IP (gateway): {gw}")
                return gw
            except Exception:
                pass
        return None

    # ── Flask server ──────────────────────────────────────────────────────

    def start_server(self):
        """
        Start Flask server. Shuts down any previously running instance first
        to prevent 'Address already in use' on reconnect.
        """
        # FIX: kill previous instance before rebinding — prevents OSError port in use
        self.stop()

        self.server_ready.clear()
        self.flask_thread = threading.Thread(
            target=self._run_flask, daemon=True, name='WiFiServer'
        )
        self.flask_thread.start()
        ready = self.server_ready.wait(timeout=8)
        if ready:
            print(f"[WIFI] Flask server ready on port {self.FLASK_PORT} ✓")
        else:
            print(f"[WIFI] WARNING: Flask server did not start within 8s")

    def _run_flask(self):
        from flask import Flask, request, jsonify
        from werkzeug.serving import make_server

        app = Flask(__name__)

        @app.route('/ping', methods=['GET'])
        def ping():
            print("[WIFI SERVER] Ping received from phone ✓")
            return jsonify(status='ok', device='minik')

        @app.route('/result/<result_type>', methods=['POST'])
        def receive_result(result_type):
            data = request.json
            print(f"[WIFI SERVER] ← Received {result_type}: {data}")
            with self.results_lock:
                self.results[result_type] = data
            if result_type in self.result_events:
                self.result_events[result_type].set()
            return jsonify(status='received')

        try:
            server = make_server('0.0.0.0', self.FLASK_PORT, app)
            # FIX: allow port reuse immediately after previous server closes
            server.socket.setsockopt(
                __import__('socket').SOL_SOCKET,
                __import__('socket').SO_REUSEADDR,
                1
            )
            self._flask_server = server
            self.server_ready.set()
            print(f"[WIFI SERVER] Listening on 0.0.0.0:{self.FLASK_PORT}")
            self._flask_server.serve_forever()
        except OSError as e:
            print(f"[WIFI SERVER] Failed to bind port {self.FLASK_PORT}: {e}")
            print(f"[WIFI SERVER] Try: sudo fuser -k {self.FLASK_PORT}/tcp")

    # ── Send to phone ─────────────────────────────────────────────────────

    def send_image(self, image_path: str) -> bool:
        if not HAS_REQUESTS:
            print("[WIFI] requests not available — cannot send image")
            return False
        url = self._build_phone_url('upload/image')
        if not url:
            return False
        for attempt in range(1, 4):
            try:
                print(f"[WIFI] Sending image to phone (attempt {attempt}/3)...")
                with open(image_path, 'rb') as f:
                    resp = reqlib.post(
                        url,
                        files={'image': ('image.jpg', f, 'image/jpeg')},
                        timeout=30
                    )
                if resp.status_code == 200:
                    print(f"[WIFI] Image sent ✓")
                    return True
                else:
                    print(f"[WIFI] Image send failed — HTTP {resp.status_code}")
            except Exception as e:
                print(f"[WIFI] Image send error (attempt {attempt}): {e}")
            if attempt < 3:
                time.sleep(2)
        print("[WIFI] Image send failed after 3 attempts")
        return False

    def send_file(self, file_path: str) -> bool:
        if not HAS_REQUESTS:
            print("[WIFI] requests not available — cannot send CSV")
            return False
        url = self._build_phone_url('upload/csv')
        if not url:
            return False
        for attempt in range(1, 4):
            try:
                fname = os.path.basename(file_path)
                print(f"[WIFI] Sending CSV '{fname}' to phone (attempt {attempt}/3)...")
                with open(file_path, 'rb') as f:
                    resp = reqlib.post(
                        url,
                        files={'csv': (fname, f, 'text/csv')},
                        timeout=15
                    )
                if resp.status_code == 200:
                    print(f"[WIFI] CSV sent ✓")
                    return True
                else:
                    print(f"[WIFI] CSV send failed — HTTP {resp.status_code}")
            except Exception as e:
                print(f"[WIFI] CSV send error (attempt {attempt}): {e}")
            if attempt < 3:
                time.sleep(2)
        print("[WIFI] CSV send failed after 3 attempts")
        return False

    # ── Wait for results ──────────────────────────────────────────────────

    def wait_for_message(self, message_type: str, timeout: int = 120):
        print(f"[WIFI] Waiting for '{message_type}' from phone (timeout: {timeout}s)...")
        event = self.result_events.get(message_type)
        if not event:
            print(f"[WIFI] Unknown message type: {message_type}")
            return None
        event.clear()
        with self.results_lock:
            self.results.pop(message_type, None)
        received = event.wait(timeout=timeout)
        if received:
            with self.results_lock:
                result = self.results.get(message_type)
            print(f"[WIFI] ← Got '{message_type}': {result}")
            return result
        print(f"[WIFI] Timeout waiting for '{message_type}'")
        return None

    # ── Helpers ───────────────────────────────────────────────────────────

    def _build_phone_url(self, endpoint: str) -> str:
        phone_ip = self.get_phone_ip()
        if not phone_ip:
            print("[WIFI] Phone IP not known — cannot build URL")
            return None
        url = f'http://{phone_ip}:{self.PHONE_PORT}/{endpoint}'
        print(f"[WIFI] Target URL: {url}")
        return url

    def stop(self):
        """
        Shut down Flask server cleanly.
        Called before every start_server() to prevent port reuse errors.
        """
        if self._flask_server:
            print("[WIFI] Shutting down Flask server...")
            try:
                self._flask_server.shutdown()
            except Exception as e:
                print(f"[WIFI] Flask shutdown warning (non-fatal): {e}")
            self._flask_server = None
            print("[WIFI] Flask server stopped ✓")
        # FIX: reset phone IP so stale gateway from previous session isn't reused
        self.phone_ip = None
