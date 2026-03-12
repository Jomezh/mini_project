import socket
import threading
from kivy.clock import Clock


class HeartbeatManager:
    """
    Periodically checks if the phone app is reachable via TCP.
    Fires callbacks when connection state changes.
    Tolerates up to MAX_FAILURES consecutive failures before alerting.

    Call pause() before long operations (image send, CNN wait) so a
    busy phone doesn't trigger a false disconnect. Call resume() after.
    """

    HEARTBEAT_INTERVAL = 30   # seconds between checks
    HEARTBEAT_TIMEOUT  = 5    # TCP connect timeout
    HEARTBEAT_PORT     = 8080 # phone's server port
    MAX_FAILURES       = 3    # alert after this many consecutive failures

    def __init__(self, phone_address, on_connected=None, on_disconnected=None):
        self.phone_address   = phone_address
        self.on_connected    = on_connected
        self.on_disconnected = on_disconnected

        self._thread        = None
        self._stop_event    = threading.Event()
        self._pause_event   = threading.Event()   # ← NEW: set = paused
        self._failure_count = 0
        self._is_connected  = None  # None=unknown, True/False=known

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self):
        self._stop_event.clear()
        self._pause_event.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name='HeartbeatManager'
        )
        self._thread.start()
        print(f"[HEARTBEAT] Monitoring {self.phone_address}:{self.HEARTBEAT_PORT} "
              f"every {self.HEARTBEAT_INTERVAL}s")

    def stop(self):
        self._stop_event.set()
        print("[HEARTBEAT] Stopped")

    # ── Pause / resume ────────────────────────────────────────────────────

    def pause(self):
        """
        Suppress disconnect callbacks temporarily.
        Use during image send and CNN wait — phone may be busy and
        fail TCP pings without actually being gone.
        Pings still run so reconnection is detected immediately on resume.
        """
        self._pause_event.set()
        self._failure_count = 0     # reset so resume starts with clean slate
        print("[HEARTBEAT] Paused — disconnect callbacks suppressed")

    def resume(self):
        """Re-enable disconnect callbacks after long operation finishes."""
        self._pause_event.clear()
        self._failure_count = 0     # reset — don't carry over failures from pause
        print("[HEARTBEAT] Resumed")

    # ── Internal loop ─────────────────────────────────────────────────────

    def _loop(self):
        while not self._stop_event.wait(timeout=self.HEARTBEAT_INTERVAL):
            self._check()

    def _check(self):
        reachable = self._tcp_ping()
        paused    = self._pause_event.is_set()

        if reachable:
            self._failure_count = 0
            if self._is_connected is not True:
                self._is_connected = True
                print("[HEARTBEAT] Phone app ONLINE ✓")
                if self.on_connected:
                    Clock.schedule_once(lambda dt: self.on_connected(), 0)
        else:
            self._failure_count += 1
            print(f"[HEARTBEAT] Phone unreachable "
                  f"({'paused — ' if paused else ''}"
                  f"{self._failure_count}/{self.MAX_FAILURES})")

            if self._failure_count >= self.MAX_FAILURES:
                if self._is_connected is not False:
                    self._is_connected = False
                    if paused:
                        # Phone appears gone but we're mid-analysis — log only,
                        # do not fire callback. resume() will reassess.
                        print("[HEARTBEAT] Disconnect detected but suppressed (paused)")
                    else:
                        print("[HEARTBEAT] Phone app OFFLINE ✗")
                        if self.on_disconnected:
                            Clock.schedule_once(lambda dt: self.on_disconnected(), 0)

    def _tcp_ping(self):
        try:
            sock = socket.create_connection(
                (self.phone_address, self.HEARTBEAT_PORT),
                timeout=self.HEARTBEAT_TIMEOUT
            )
            sock.close()
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    @property
    def is_phone_online(self):
        """True only if last check confirmed phone is reachable."""
        return self._is_connected is True
