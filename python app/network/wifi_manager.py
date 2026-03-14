import subprocess
import socket
import time
import threading
import os
import re

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
    Runs Flask server on port 8765 (phone polls /status and /snapshot).
    Sends images and CSVs to phone's HTTP server on port 8080.
    CNN/ML results are returned synchronously in the POST response.
    """

    FLASK_PORT = 8765
    PHONE_PORT = 8080

    _frame_lock          = threading.Lock()
    _latest_frame: bytes = None   # raw JPEG bytes written by camera_manager

    def __init__(self):
        self.phone_ip      = None
        self._server_ready = threading.Event()
        self._results      = {}
        self._results_lock = threading.Lock()
        self._result_events = {
            'cnn_result': threading.Event(),
            'ml_result':  threading.Event(),
        }
        self._flask_thread = None
        self._flask_server = None


    # ── Frame buffer ──────────────────────────────────────────────────────

    @classmethod
    def set_snapshot_frame(cls, jpeg_bytes: bytes):
        with cls._frame_lock:
            cls._latest_frame = jpeg_bytes


    # ── WiFi Connection ───────────────────────────────────────────────────

    def connect(self, ssid: str, password: str = None) -> bool:
        """
        Connect to hotspot and wait until BOTH:
          1. WiFi is associated (iwgetid confirms SSID)
          2. DHCP has assigned an IP (ip addr shows inet on wlan0)

        Returning True only when both are true means get_local_ip() will
        ALWAYS succeed immediately after connect() — no separate DHCP wait
        needed in the controller, IP is ready to send over BLE instantly.
        """
        print(f"[WIFI] Scheduling connection to '{ssid}' in 2s...")
        threading.Thread(
            target=self._do_connect,
            args=(ssid, password),
            daemon=True
        ).start()

        for _ in range(60):   # up to 60s — covers association + DHCP
            time.sleep(1)
            if self.is_connected_to(ssid):
                ip = self.get_local_ip()
                if ip:
                    print(f"[WIFI] Connected to '{ssid}' — IP ready: {ip}")
                    return True
                else:
                    # Associated but DHCP not done yet — keep waiting
                    print("[WIFI] Associated, waiting for DHCP...")

        print(f"[WIFI] Failed to connect+DHCP for '{ssid}' within 60s")
        return False

    def _do_connect(self, ssid: str, password: str = None):
        try:
            time.sleep(2)   # BLE ACK window

            # Scan retry: up to 3×8s for hotspot to appear
            ssid_visible = False
            for scan_attempt in range(1, 4):
                print("[WIFI] Running blocking rescan nmcli dev wifi list --rescan yes...")
                scan_result = subprocess.run(
                    ['nmcli', 'dev', 'wifi', 'list', '--rescan', 'yes'],
                    capture_output=True, text=True, timeout=20
                )
                if ssid in scan_result.stdout:
                    print(f"[WIFI] '{ssid}' confirmed visible in scan")
                    ssid_visible = True
                    break
                else:
                    print(f"[WIFI] WARNING: '{ssid}' not visible "
                          f"(attempt {scan_attempt}/3) — hotspot may still be starting")
                    if scan_attempt < 3:
                        time.sleep(8)

            if not ssid_visible:
                print(f"[WIFI] '{ssid}' never appeared after 3 scans — aborting")
                return

            # Delete stale profile to avoid saved-password conflicts
            if self._profile_exists(ssid):
                print(f"[WIFI] Deleting stale profile for '{ssid}'...")
                subprocess.run(
                    ['nmcli', 'con', 'delete', ssid],
                    capture_output=True, timeout=10
                )
                print("[WIFI] Stale profile deleted")

            if password:
                cmd = ['nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password]
                print(f"[WIFI] Connecting to '{ssid}' with password")
            elif self._profile_exists(ssid):
                cmd = ['nmcli', 'con', 'up', ssid]
                print(f"[WIFI] Bringing up saved profile for '{ssid}'")
            else:
                print(f"[WIFI] No profile and no password for '{ssid}' — cannot connect")
                return

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if 'successfully' in stdout.lower() or result.returncode == 0:
                print(f"[WIFI] nmcli connected to '{ssid}'")
            else:
                print(f"[WIFI] nmcli stdout: {stdout}")
                if stderr:
                    print(f"[WIFI] nmcli stderr: {stderr}")
                if password:
                    print(f"[WIFI] Fallback: trying saved profile for '{ssid}'")
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


    # ── IP Helpers ────────────────────────────────────────────────────────

    def get_local_ip(self) -> str:
        """
        Read wlan0 IP directly from kernel via 'ip addr show wlan0'.
        Live read — no cached values, always reflects current DHCP state.
        netifaces caches interface state and misses new DHCP assignments.
        """
        # Primary: subprocess ip addr — live kernel read, no cache
        try:
            result = subprocess.run(
                ['ip', 'addr', 'show', 'wlan0'],
                capture_output=True, text=True, timeout=5
            )
            match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/', result.stdout)
            if match:
                ip = match.group(1)
                print(f"[WIFI] Local IP (ip addr): {ip}")
                return ip
            else:
                print("[WIFI] wlan0 has no inet addr yet (DHCP pending)")
        except Exception as e:
            print(f"[WIFI] ip addr show failed: {e}")

        # Secondary: netifaces
        if HAS_NETIFACES:
            try:
                addrs = netifaces.ifaddresses('wlan0')
                ip    = addrs[netifaces.AF_INET][0]['addr']
                print(f"[WIFI] Local IP (netifaces): {ip}")
                return ip
            except Exception:
                pass

        # Tertiary: socket trick
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            print(f"[WIFI] Local IP (socket): {ip}")
            return ip
        except Exception as e:
            print(f"[WIFI] Could not get local IP: {e}")
            return None

    def get_phone_ip(self) -> str:
        """
        Get phone IP (default gateway on wlan0) via 'ip route' — live kernel
        read. Cache cleared on stop() so stale IPs are never reused.
        """
        if self.phone_ip:
            return self.phone_ip

        # Primary: ip route — live routing table
        try:
            result = subprocess.run(
                ['ip', 'route', 'show', 'dev', 'wlan0'],
                capture_output=True, text=True, timeout=5
            )
            match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', result.stdout)
            if match:
                gw            = match.group(1)
                self.phone_ip = gw
                print(f"[WIFI] Phone IP (ip route): {gw}")
                return gw
            else:
                print("[WIFI] No default gateway on wlan0 yet")
        except Exception as e:
            print(f"[WIFI] ip route failed: {e}")

        # Secondary: netifaces
        if HAS_NETIFACES:
            try:
                gws           = netifaces.gateways()
                gw            = gws['default'][netifaces.AF_INET][0]
                self.phone_ip = gw
                print(f"[WIFI] Phone IP (netifaces): {gw}")
                return gw
            except Exception:
                pass

        return None


    # ── Flask Server (Pi-side, port 8765) ─────────────────────────────────

    def start_server(self):
        """Idempotent — safe to call multiple times. No-op if already running."""
        if self._flask_server is not None:
            print("[WIFI] Flask server already running — skipping restart")
            return
        self._server_ready.clear()
        self._flask_thread = threading.Thread(
            target=self._run_flask,
            daemon=True,
            name="WiFiServer"
        )
        self._flask_thread.start()
        ready = self._server_ready.wait(timeout=8)
        if ready:
            print(f"[WIFI] Flask server ready on port {self.FLASK_PORT}")
        else:
            print(f"[WIFI] WARNING: Flask server did not start within 8s")

    def _run_flask(self):
        from flask import Flask, request, jsonify, Response
        from werkzeug.serving import make_server
        import socket as _socket

        app = Flask(__name__)

        @app.route('/ping', methods=['GET'])
        def ping():
            return jsonify(status='ok', device='minik')

        @app.route('/status', methods=['GET'])
        def status():
            try:
                import config
                from datetime import datetime
                return jsonify(
                    status   = 'ok',
                    device   = 'minik',
                    time     = datetime.now().isoformat(),
                    platform = 'raspberry_pi' if config.IS_RASPBERRY_PI else 'dev',
                )
            except Exception:
                return jsonify(status='ok', device='minik')

        @app.route('/snapshot', methods=['GET'])
        def snapshot():
            with WiFiManager._frame_lock:
                frame = WiFiManager._latest_frame
            if frame:
                return Response(frame, mimetype='image/jpeg')
            return Response(status=204)

        @app.route('/result/<result_type>', methods=['POST'])
        def receive_result(result_type):
            data = request.json
            print(f"[WIFI] SERVER Received {result_type}: {data}")
            with self._results_lock:
                self._results[result_type] = data
            if result_type in self._result_events:
                self._result_events[result_type].set()
            return jsonify(status='received')

        try:
            server = make_server('0.0.0.0', self.FLASK_PORT, app)
            server.socket.setsockopt(
                _socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1
            )
            self._flask_server = server
            self._server_ready.set()
            print(f"[WIFI] SERVER Listening on 0.0.0.0:{self.FLASK_PORT}")
            self._flask_server.serve_forever()
        except OSError as e:
            print(f"[WIFI] SERVER Failed to bind port {self.FLASK_PORT}: {e}")
            print(f"[WIFI] SERVER Try: sudo fuser -k {self.FLASK_PORT}/tcp")


    # ── Send Image (Pi → Phone) ────────────────────────────────────────────

    def send_image(self, image_path: str) -> bool:
        if not HAS_REQUESTS:
            print("[WIFI] requests not available — cannot send image")
            return False

        url      = self._build_phone_url('upload/image')
        ping_url = self._build_phone_url('ping')
        if not url or not ping_url:
            return False

        if not self._wait_for_phone_server(ping_url, timeout=15):
            print("[WIFI] Phone server unreachable — aborting image send")
            return False

        try:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
        except Exception as e:
            print(f"[WIFI] Could not read image file: {e}")
            return False

        with self._results_lock:
            self._results.pop('cnn_result', None)
        self._result_events['cnn_result'].clear()

        for attempt in range(1, 4):
            try:
                print(f"[WIFI] Sending image to phone attempt {attempt}/3...")
                # Raw JPEG bytes — NOT multipart. Phone's img.decodeImage()
                # needs pure JPEG, multipart envelope causes decode failure.
                resp = reqlib.post(
                    url,
                    data    = image_bytes,
                    headers = {'Content-Type': 'image/jpeg'},
                    timeout = 60
                )
                if resp.status_code == 200:
                    print("[WIFI] Image sent ✓")
                    try:
                        result = resp.json()
                        print(f"[WIFI] CNN result from phone: {result}")
                        with self._results_lock:
                            self._results['cnn_result'] = result
                        self._result_events['cnn_result'].set()
                    except Exception as e:
                        print(f"[WIFI] Could not parse CNN result: {e}")
                    return True
                else:
                    print(f"[WIFI] Image send failed HTTP {resp.status_code}")
            except Exception as e:
                print(f"[WIFI] Image send error attempt {attempt}: {e}")
                if attempt < 3:
                    time.sleep(2)

        print("[WIFI] Image send failed after 3 attempts")
        return False


    # ── Send CSV (Pi → Phone) ──────────────────────────────────────────────

    def send_file(self, filepath: str) -> bool:
        if not HAS_REQUESTS:
            print("[WIFI] requests not available — cannot send CSV")
            return False

        url = self._build_phone_url('upload/csv')
        if not url:
            return False

        try:
            with open(filepath, 'rb') as f:
                csv_bytes = f.read()
        except Exception as e:
            print(f"[WIFI] Could not read CSV file: {e}")
            return False

        with self._results_lock:
            self._results.pop('ml_result', None)
        self._result_events['ml_result'].clear()

        fname = os.path.basename(filepath)
        for attempt in range(1, 4):
            try:
                print(f"[WIFI] Sending CSV '{fname}' to phone attempt {attempt}/3...")
                resp = reqlib.post(
                    url,
                    data    = csv_bytes,
                    headers = {'Content-Type': 'text/csv; charset=utf-8'},
                    timeout = 30
                )
                if resp.status_code == 200:
                    print("[WIFI] CSV sent ✓")
                    try:
                        result = resp.json()
                        print(f"[WIFI] ML result from phone: {result}")
                        with self._results_lock:
                            self._results['ml_result'] = result
                        self._result_events['ml_result'].set()
                    except Exception as e:
                        print(f"[WIFI] Could not parse ML result: {e}")
                    return True
                else:
                    print(f"[WIFI] CSV send failed HTTP {resp.status_code}")
            except Exception as e:
                print(f"[WIFI] CSV send error attempt {attempt}: {e}")
                if attempt < 3:
                    time.sleep(2)

        print("[WIFI] CSV send failed after 3 attempts")
        return False


    # ── Wait for Results ──────────────────────────────────────────────────

    def wait_for_cnn_result(self, cancel_event=None, timeout: int = 120):
        print(f"[WIFI] Waiting for CNN result (timeout {timeout}s)...")
        with self._results_lock:
            existing = self._results.get('cnn_result')
        if existing:
            print("[WIFI] CNN result already available")
            return existing
        event   = self._result_events['cnn_result']
        elapsed = 0
        while elapsed < timeout:
            if cancel_event and cancel_event.is_set():
                print("[WIFI] CNN wait cancelled")
                return None
            if event.wait(timeout=1):
                with self._results_lock:
                    return self._results.get('cnn_result')
            elapsed += 1
        print("[WIFI] CNN result wait timed out")
        return None

    def wait_for_ml_result(self, cancel_event=None, timeout: int = 60):
        print(f"[WIFI] Waiting for ML result (timeout {timeout}s)...")
        with self._results_lock:
            existing = self._results.get('ml_result')
        if existing:
            print("[WIFI] ML result already available")
            return existing
        event   = self._result_events['ml_result']
        elapsed = 0
        while elapsed < timeout:
            if cancel_event and cancel_event.is_set():
                print("[WIFI] ML wait cancelled")
                return None
            if event.wait(timeout=1):
                with self._results_lock:
                    return self._results.get('ml_result')
            elapsed += 1
        print("[WIFI] ML result wait timed out")
        return None

    def wait_for_message(self, message_type: str, timeout: int = 120):
        if message_type == 'cnn_result':
            return self.wait_for_cnn_result(timeout=timeout)
        if message_type == 'ml_result':
            return self.wait_for_ml_result(timeout=timeout)
        print(f"[WIFI] Unknown message type: {message_type}")
        return None


    # ── Phone Server Readiness ────────────────────────────────────────────

    def _wait_for_phone_server(self, url: str, timeout: int = 15) -> bool:
        print(f"[WIFI] Waiting for phone server (up to {timeout}s)...")
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                resp = reqlib.get(url, timeout=2)
                if resp.status_code == 200:
                    print("[WIFI] Phone server is ready ✓")
                    return True
            except Exception:
                pass
            time.sleep(2)
        print("[WIFI] Phone server did not respond in time")
        return False


    # ── URL Builder ───────────────────────────────────────────────────────

    def _build_phone_url(self, endpoint: str) -> str | None:
        phone_ip = self.get_phone_ip()
        if not phone_ip:
            print("[WIFI] Phone IP not known — cannot build URL")
            return None
        url = f"http://{phone_ip}:{self.PHONE_PORT}/{endpoint}"
        print(f"[WIFI] Target URL: {url}")
        return url


    # ── Stop ──────────────────────────────────────────────────────────────

    def stop(self):
        """
        Reset WiFi session state only. Flask keeps running — it was started
        at app boot and lives for the full app lifetime. Clearing phone_ip
        ensures the stale gateway from this session is not reused next time.
        """
        self.phone_ip = None
        print("[WIFI] WiFi session reset (Flask keeps running)")
