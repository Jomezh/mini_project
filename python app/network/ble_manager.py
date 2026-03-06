"""
BLE GATT peripheral server for MiniK.

Roles:
  - Peripheral: advertises as MiniK-XXXXXX, hosts GATT service
    Phone connects, writes SSID/password/BLE-MAC → Pi reads credentials
    Pi writes IP back → phone reads it

  - Central (scan): uses bleak to scan for known phone MACs on boot

Requirements:
    pip install bleak bless
    sudo apt install bluetooth bluez
    See /etc/bluetooth/main.conf for Zero 2W stability settings
"""

import asyncio
import threading
import time

# ── GATT UUIDs — must match phone app exactly ────────────────────────────────
GATT_SERVICE_UUID  = '12345678-1234-1234-1234-123456789ab0'
CHAR_SSID_UUID     = '12345678-1234-1234-1234-123456789ab1'
CHAR_PASSWORD_UUID = '12345678-1234-1234-1234-123456789ab2'
CHAR_BLE_NAME_UUID = '12345678-1234-1234-1234-123456789ab3'
CHAR_BLE_MAC_UUID  = '12345678-1234-1234-1234-123456789ab4'
CHAR_IP_UUID       = '12345678-1234-1234-1234-123456789ab5'
CHAR_STATUS_UUID   = '12345678-1234-1234-1234-123456789ab6'

_WRITABLE_CHARS = {
    CHAR_SSID_UUID,
    CHAR_PASSWORD_UUID,
    CHAR_BLE_NAME_UUID,
    CHAR_BLE_MAC_UUID,
}
_READABLE_CHARS = {CHAR_IP_UUID, CHAR_STATUS_UUID}

_UUID_TO_KEY = {
    CHAR_SSID_UUID:     'ssid',
    CHAR_PASSWORD_UUID: 'password',
    CHAR_BLE_NAME_UUID: 'ble_name',
    CHAR_BLE_MAC_UUID:  'ble_mac',
}
_REQUIRED_CREDS = {'ssid', 'password', 'ble_name', 'ble_mac'}

# How long to wait after server.start() before advertising.
# Pi Zero 2W / CYW43439 needs this or phone finds empty GATT and drops.
_GATT_READY_DELAY = 1.0


class BLEManager:
    """
    BLE peripheral + central manager.
    All async work runs on a dedicated background event loop.
    Public methods are synchronous (blocking where needed).
    """

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.ble_name  = f"MiniK-{device_id[-6:]}"

        self._server         = None
        self._loop           = None
        self._bg_thread      = None

        self._creds          = {}
        self._outgoing       = {}
        self._creds_received = threading.Event()

        # ── Connection state tracking ────────────────────────────────────────
        self._connected_clients = set()
        self._connection_lock   = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def start_advertising(self):
        return self.start_ble_advertising()

    def start_ble_advertising(self) -> bool:
        """Start GATT server and begin BLE advertising."""
        try:
            self._loop = asyncio.new_event_loop()
            self._bg_thread = threading.Thread(
                target=self._run_event_loop,
                daemon=True,
                name="BLEServer"
            )
            self._bg_thread.start()
            time.sleep(0.5)   # Let loop start

            future = asyncio.run_coroutine_threadsafe(
                self._start_gatt_server(), self._loop
            )
            # Timeout includes _GATT_READY_DELAY so phone never
            # sees an empty GATT service list
            future.result(timeout=15)
            print(f"[BLE] Advertising as '{self.ble_name}'")
            print(f"[BLE] Service UUID: {GATT_SERVICE_UUID}")
            return True

        except Exception as e:
            print(f"[BLE] start_advertising failed: {e}")
            return False

    def wait_for_pairing(self, timeout: int = 180) -> dict | None:
        """
        Block until phone writes all 4 GATT characteristics.
        Returns credentials dict or None on timeout.
        """
        print("[BLE] Waiting for phone to send credentials...")
        self._creds_received.clear()
        self._creds.clear()
        received = self._creds_received.wait(timeout=timeout)

        if received:
            result = dict(self._creds)
            print(f"[BLE] Credentials received: "
                  f"SSID='{result.get('ssid')}' "
                  f"from '{result.get('ble_name')}'")
            return result

        print("[BLE] Pairing wait timeout")
        return None

    def send_ip_to_phone(self, ip_address: str) -> bool:
        """Pi's WiFi IP → written to GATT characteristic → phone reads it."""
        try:
            self._outgoing['ip'] = ip_address
            if self._server and self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._notify_characteristic(CHAR_IP_UUID),
                    self._loop
                )
            print(f"[BLE] IP characteristic set: {ip_address}")
            return True
        except Exception as e:
            print(f"[BLE] send_ip_to_phone error: {e}")
            return False

    def notify_enable_hotspot(self) -> bool:
        """
        Write 'enable_hotspot' to STATUS characteristic.
        Phone receives BLE notify → shows 'Enable your hotspot' alert.
        """
        try:
            self._outgoing['status'] = 'enable_hotspot'
            if self._server and self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._notify_characteristic(CHAR_STATUS_UUID),
                    self._loop
                )
            print("[BLE] Notified phone: enable hotspot")
            return True
        except Exception as e:
            print(f"[BLE] notify_enable_hotspot error: {e}")
            return False

    @property
    def is_phone_connected(self) -> bool:
        """True if at least one phone is currently connected via BLE."""
        with self._connection_lock:
            return len(self._connected_clients) > 0

    @property
    def connected_count(self) -> int:
        with self._connection_lock:
            return len(self._connected_clients)

    def stop(self):
        """Stop GATT server and event loop cleanly."""
        if self._server and self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._stop_server(), self._loop
            )
            try:
                future.result(timeout=5)
            except Exception as e:
                print(f"[BLE] Stop warning (non-fatal): {e}")

        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        self._server = None
        print("[BLE] Stopped")

    async def _stop_server(self):
        """Properly awaited server stop — prevents 'coroutine never awaited'."""
        try:
            await self._server.stop()
        except Exception as e:
            print(f"[BLE] Server stop error (non-fatal): {e}")

    def scan_for_devices(self,
                         known_macs: list,
                         known_names: list,
                         timeout: int = 10) -> dict | None:
        """
        Central role — scan for known phone MACs/names.
        Runs a fresh event loop separate from GATT server loop.
        Returns {'mac': ..., 'name': ...} or None.
        """
        print(f"[BLE] Scanning {timeout}s for "
              f"{len(known_macs)} known device(s)...")
        try:
            loop   = asyncio.new_event_loop()
            result = loop.run_until_complete(
                self._scan_async(known_macs, known_names, timeout)
            )
            loop.close()
            return result
        except Exception as e:
            print(f"[BLE] Scan error: {e}")
            return None

    # ── Event Loop ────────────────────────────────────────────────────────────

    def _run_event_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    # ── GATT Server Setup ─────────────────────────────────────────────────────

    async def _start_gatt_server(self):
        from bless import (
            BlessServer,
            GATTCharacteristicProperties,
            GATTAttributePermissions,
        )

        self._server = BlessServer(name=self.ble_name, loop=self._loop)
        self._server.read_request_func  = self._on_read
        self._server.write_request_func = self._on_write

        # Connection callbacks (BlueZ backend only)
        if hasattr(self._server, 'on_connect'):
            self._server.on_connect    = self._on_client_connect
        if hasattr(self._server, 'on_disconnect'):
            self._server.on_disconnect = self._on_client_disconnect

        await self._server.add_new_service(GATT_SERVICE_UUID)

        # Phone writes credentials to these
        for uuid in _WRITABLE_CHARS:
            await self._server.add_new_characteristic(
                GATT_SERVICE_UUID,
                uuid,
                GATTCharacteristicProperties.write,
                None,
                GATTAttributePermissions.writeable
            )

        # Pi writes IP/status — phone reads / gets notified
        for uuid in _READABLE_CHARS:
            await self._server.add_new_characteristic(
                GATT_SERVICE_UUID,
                uuid,
                (GATTCharacteristicProperties.read |
                 GATTCharacteristicProperties.notify),
                None,
                GATTAttributePermissions.readable
            )

        await self._server.start()

        # ── Critical: wait for BlueZ to fully register the GATT service ──
        # Without this delay the phone's discoverServices() returns an empty
        # list → phone drops with CONNECTION_TERMINATED_BY_LOCAL_HOST (22).
        await asyncio.sleep(_GATT_READY_DELAY)

        print(f"[BLE] GATT server ready — {len(_WRITABLE_CHARS)} writable + "
              f"{len(_READABLE_CHARS)} readable characteristics registered")
        print(f"[BLE] Monitor: sudo btmon | grep -E 'Connect|Address'")

    # ── Connection Tracking ───────────────────────────────────────────────────

    def _on_client_connect(self, client_mac: str):
        with self._connection_lock:
            self._connected_clients.add(client_mac)
        print(f"[BLE] ✓ Phone connected: {client_mac}  "
              f"(total: {len(self._connected_clients)})")

    def _on_client_disconnect(self, client_mac: str):
        with self._connection_lock:
            self._connected_clients.discard(client_mac)
        print(f"[BLE] ✗ Phone disconnected: {client_mac}  "
              f"(remaining: {len(self._connected_clients)})")

    # ── GATT Callbacks ────────────────────────────────────────────────────────

    def _on_write(self, characteristic, value: bytearray):
        """Phone wrote a credential field."""
        uuid = str(characteristic.uuid).lower()
        key  = _UUID_TO_KEY.get(uuid)
        if key is None:
            return

        text = value.decode('utf-8', errors='replace').strip()
        if not text:
            print(f"[BLE] Empty write ignored for ...{uuid[-4:]}")
            return

        if key == 'ssid'     and len(text) > 32:  return
        if key == 'password' and len(text) > 64:  return

        self._creds[key] = text
        print(f"[BLE] ← Received {key}: "
              f"{'*' * len(text) if key == 'password' else text}")

        got  = len(self._creds)
        need = len(_REQUIRED_CREDS)
        print(f"[BLE]   Credentials: {got}/{need} received")

        if _REQUIRED_CREDS.issubset(self._creds.keys()):
            print("[BLE] ✓ All credentials received")
            self._creds_received.set()

    def _on_read(self, characteristic, **kwargs) -> bytearray:
        """Phone read a Pi-managed characteristic."""
        uuid = str(characteristic.uuid).lower()
        if uuid == CHAR_IP_UUID:
            ip = self._outgoing.get('ip', '')
            print(f"[BLE] → Phone read IP: '{ip}'")
            return bytearray(ip.encode())
        if uuid == CHAR_STATUS_UUID:
            status = self._outgoing.get('status', '')
            print(f"[BLE] → Phone read status: '{status}'")
            return bytearray(status.encode())
        return bytearray()

    async def _notify_characteristic(self, char_uuid: str):
        """Push notify to connected phone client."""
        try:
            await self._server.update_value(GATT_SERVICE_UUID, char_uuid)
            print(f"[BLE] Notified characteristic: ...{char_uuid[-4:]}")
        except Exception as e:
            print(f"[BLE] Notify error ({char_uuid[-4:]}): {e}")

    # ── BLE Scan ──────────────────────────────────────────────────────────────

    async def _scan_async(self,
                          known_macs: list,
                          known_names: list,
                          timeout: int) -> dict | None:
        from bleak import BleakScanner

        known_macs_upper  = {m.upper() for m in known_macs  if m}
        known_names_lower = {n.lower() for n in known_names if n}

        devices = await BleakScanner.discover(timeout=timeout)
        print(f"[BLE] Scan complete — {len(devices)} device(s) visible nearby")

        for device in devices:
            mac  = (device.address or '').upper()
            name = (device.name    or '').lower()
            if mac in known_macs_upper or name in known_names_lower:
                print(f"[BLE] ✓ Found known device: "
                      f"{device.name} ({device.address})")
                return {'mac': device.address, 'name': device.name or ''}

        print("[BLE] No known devices found in scan")
        return None
