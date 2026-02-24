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

# Map UUID → credentials dict key
_UUID_TO_KEY = {
    CHAR_SSID_UUID:     'ssid',
    CHAR_PASSWORD_UUID: 'password',
    CHAR_BLE_NAME_UUID: 'ble_name',
    CHAR_BLE_MAC_UUID:  'ble_mac',
}
_REQUIRED_CREDS = {'ssid', 'password', 'ble_name', 'ble_mac'}


class BLEManager:
    """
    BLE peripheral + central manager.
    All async work runs on a dedicated background event loop.
    Public methods are synchronous (blocking where needed).
    """

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.ble_name  = f"MiniK-{device_id[-6:]}"

        self._server           = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._bg_thread        = None

        self._creds            = {}                # Populated as phone writes chars
        self._outgoing         = {}                # IP / status values Pi writes
        self._creds_received   = threading.Event()

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
            future.result(timeout=10)
            print(f"[BLE] Advertising as '{self.ble_name}'")
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
        """
        Update IP characteristic and notify phone.
        Phone reads this after connecting to know where to send HTTP data.
        """
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
        Phone app receives BLE notification → shows 'Enable your hotspot' alert.
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

    def stop(self):
        """Stop GATT server and event loop."""
        if self._server and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._server.stop(), self._loop
            )
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        print("[BLE] Stopped")

    def scan_for_devices(self,
                         known_macs: list,
                         known_names: list,
                         timeout: int = 10) -> dict | None:
        """
        Central role — scan for known phone MACs/names.
        Runs a fresh event loop (separate from GATT server loop).
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

        await self._server.add_new_service(GATT_SERVICE_UUID)

        # Phone writes these → Pi receives credentials
        for uuid in _WRITABLE_CHARS:
            await self._server.add_new_characteristic(
                GATT_SERVICE_UUID,
                uuid,
                GATTCharacteristicProperties.write,
                None,
                GATTAttributePermissions.writeable
            )

        # Pi writes these → phone reads / gets notified
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
        print(f"[BLE] GATT server running — UUID: {GATT_SERVICE_UUID}")

    # ── GATT Callbacks ────────────────────────────────────────────────────────

    def _on_write(self, characteristic, value: bytearray):
        """Phone wrote a credential field."""
        uuid = str(characteristic.uuid).lower()
        key  = _UUID_TO_KEY.get(uuid)
        if key is None:
            return

        text = value.decode('utf-8', errors='replace').strip()
        if not text:
            print(f"[BLE] Empty write ignored for {uuid[-4:]}")
            return

        # Basic validation
        if key == 'ssid'     and len(text) > 32:   return
        if key == 'password' and len(text) > 64:   return

        self._creds[key] = text
        print(f"[BLE] Received {key}: "
              f"{'*' * len(text) if key == 'password' else text}")

        if _REQUIRED_CREDS.issubset(self._creds.keys()):
            self._creds_received.set()

    def _on_read(self, characteristic, **kwargs) -> bytearray:
        """Phone read a Pi-managed characteristic."""
        uuid = str(characteristic.uuid).lower()
        if uuid == CHAR_IP_UUID:
            return bytearray(self._outgoing.get('ip', '').encode())
        if uuid == CHAR_STATUS_UUID:
            return bytearray(self._outgoing.get('status', '').encode())
        return bytearray()

    async def _notify_characteristic(self, char_uuid: str):
        """Push notify to connected phone client."""
        try:
            await self._server.update_value(GATT_SERVICE_UUID, char_uuid)
        except Exception as e:
            print(f"[BLE] Notify error ({char_uuid[-4:]}): {e}")

    # ── BLE Scan ──────────────────────────────────────────────────────────────

    async def _scan_async(self,
                          known_macs: list,
                          known_names: list,
                          timeout: int) -> dict | None:
        from bleak import BleakScanner

        known_macs_upper  = {m.upper()  for m in known_macs  if m}
        known_names_lower = {n.lower()  for n in known_names if n}

        devices = await BleakScanner.discover(timeout=timeout)

        for device in devices:
            mac  = (device.address or '').upper()
            name = (device.name    or '').lower()
            if mac in known_macs_upper or name in known_names_lower:
                print(f"[BLE] Found known device: "
                      f"{device.name} ({device.address})")
                return {'mac': device.address, 'name': device.name or ''}

        print("[BLE] No known devices found in scan")
        return None
