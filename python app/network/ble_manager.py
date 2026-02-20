"""
BLE GATT Peripheral Server for WiFi provisioning.

Flow:
  Phone writes SSID  → SSID_UUID characteristic
  Phone writes pass  → PASS_UUID characteristic
  Pi connects WiFi   → nmcli
  Pi writes IP back  → IP_UUID characteristic (phone reads before BLE closes)
"""
# pyright: basic
# These D-Bus type annotation strings ('ay', 'a{sv}' etc.) are not
# standard Python types - they are dbus-next wire format descriptors.
# Pylance warnings on these lines are expected and can be ignored.
from __future__ import annotations

import asyncio
import array
import threading
import time
import subprocess
from threading import Event

try:
    from dbus_next.aio import MessageBus
    from dbus_next.service import ServiceInterface, method
    from dbus_next import Variant, BusType
    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False
    print("[BLE] dbus-next not installed: pip install dbus-next")


# ── UUIDs (must match phone app exactly) ────────────────
SERVICE_UUID = '12345678-1234-1234-1234-123456789ab0'
SSID_UUID    = '12345678-1234-1234-1234-123456789abc'  # Phone writes SSID
PASS_UUID    = '12345678-1234-1234-1234-123456789abd'  # Phone writes password
IP_UUID      = '12345678-1234-1234-1234-123456789abf'  # Pi writes IP back

# ── BlueZ D-Bus paths/interfaces ────────────────────────
BLUEZ_SERVICE    = 'org.bluez'
ADAPTER_PATH     = '/org/bluez/hci0'
GATT_MGR_IFACE   = 'org.bluez.GattManager1'
LE_ADV_MGR_IFACE = 'org.bluez.LEAdvertisingManager1'
LE_ADV_IFACE     = 'org.bluez.LEAdvertisement1'
GATT_SVC_IFACE   = 'org.bluez.GattService1'
GATT_CHRC_IFACE  = 'org.bluez.GattCharacteristic1'
DBUS_OM_IFACE    = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE  = 'org.freedesktop.DBus.Properties'

APP_PATH  = '/com/minik/app'
SVC_PATH  = '/com/minik/app/service0'
SSID_PATH = '/com/minik/app/service0/char0'
PASS_PATH = '/com/minik/app/service0/char1'
IP_PATH   = '/com/minik/app/service0/char2'
ADV_PATH  = '/com/minik/advertisement'


# ── D-Bus Object Implementations ────────────────────────

class GattApplication(ServiceInterface):
    """Root app object - exposes all GATT objects via ObjectManager"""

    def __init__(self, service, ssid_char, pass_char, ip_char):
        super().__init__(DBUS_OM_IFACE)
        self._objects = {
            SVC_PATH:  service,
            SSID_PATH: ssid_char,
            PASS_PATH: pass_char,
            IP_PATH:   ip_char,
        }

    @method()
    def GetManagedObjects(self) -> 'a{oa{sa{sv}}}':
        result = {}
        for path, obj in self._objects.items():
            result[path] = obj.get_properties()
        return result


class GattService(ServiceInterface):
    def __init__(self):
        super().__init__(GATT_SVC_IFACE)

    def get_properties(self):
        return {
            GATT_SVC_IFACE: {
                'UUID':    Variant('s', SERVICE_UUID),
                'Primary': Variant('b', True),
            }
        }

    @method()
    def GetManagedObjects(self) -> 'a{oa{sa{sv}}}':
        return {}


class WritableCharacteristic(ServiceInterface):
    """GATT Characteristic that accepts writes from the phone"""

    def __init__(self, uuid, path, on_write):
        super().__init__(GATT_CHRC_IFACE)
        self._uuid     = uuid
        self._path     = path
        self._on_write = on_write
        self._value    = []

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'UUID':    Variant('s', self._uuid),
                'Service': Variant('o', SVC_PATH),
                'Flags':   Variant('as', ['write', 'write-without-response']),
            }
        }

    @method()
    def ReadValue(self, options: 'a{sv}') -> 'ay':
        return self._value

    @method()
    def WriteValue(self, value: 'ay', options: 'a{sv}'):
        self._value = value
        decoded = bytes(value).decode('utf-8').strip()
        if self._on_write:
            self._on_write(decoded)

    @method()
    def StartNotify(self):
        pass

    @method()
    def StopNotify(self):
        pass


class NotifiableCharacteristic(ServiceInterface):
    """GATT Characteristic that Pi writes to / phone reads (IP address)"""

    def __init__(self, uuid):
        super().__init__(GATT_CHRC_IFACE)
        self._uuid       = uuid
        self._value      = []
        self._notifying  = False
        self._connection = None

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'UUID':    Variant('s', self._uuid),
                'Service': Variant('o', SVC_PATH),
                'Flags':   Variant('as', ['read', 'notify']),
            }
        }

    @method()
    def ReadValue(self, options: 'a{sv}') -> 'ay':
        return self._value

    @method()
    def WriteValue(self, value: 'ay', options: 'a{sv}'):
        self._value = value

    @method()
    def StartNotify(self):
        self._notifying = True

    @method()
    def StopNotify(self):
        self._notifying = False

    def set_value(self, text: str):
        self._value = list(text.encode('utf-8'))


class LEAdvertisement(ServiceInterface):
    """BLE advertisement so phones can discover the Pi"""

    def __init__(self, device_id):
        super().__init__(LE_ADV_IFACE)
        self._device_id = device_id

    def get_properties(self):
        return {
            LE_ADV_IFACE: {
                'Type':        Variant('s', 'peripheral'),
                'ServiceUUIDs': Variant('as', [SERVICE_UUID]),
                'LocalName':   Variant('s', f'MiniK-{self._device_id[-6:]}'),
                'Includes':    Variant('as', ['tx-power']),
            }
        }

    @method()
    def Release(self):
        print("[BLE] Advertisement released")


# ── Main BLEManager ─────────────────────────────────────

class BLEManager:
    """
    BLE GATT peripheral server.
    Receives SSID + password from phone, sends IP back.
    """

    def __init__(self, device_id):
        self.device_id    = device_id
        self._loop        = None
        self._thread      = None
        self._bus         = None
        self._credentials = {'ssid': None, 'password': None}
        self._cred_event  = Event()
        self._ip_char     = None
        self._running     = False

    # ── Public API ──────────────────────────────────────

    def start_advertising(self):
        """Start BLE GATT server in background thread"""
        if not HAS_DBUS:
            print("[BLE] dbus-next not available")
            return False

        self._running = True
        self._thread  = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="BLEManager"
        )
        self._thread.start()

        # Give the event loop time to start
        time.sleep(1)
        print(f"[BLE] Advertising as MiniK-{self.device_id[-6:]}")
        return True

    def wait_for_pairing(self, timeout=180):
        """
        Block until SSID + password received from phone.
        Returns credentials dict or None on timeout.
        """
        print("[BLE] Waiting for credentials from phone...")

        received = self._cred_event.wait(timeout=timeout)

        if received:
            print(f"[BLE] Credentials received - SSID: {self._credentials['ssid']}")
            return {
                'ssid':          self._credentials['ssid'],
                'password':      self._credentials['password'],
                'phone_address': None   # Set after WiFi connects
            }

        print("[BLE] Timeout waiting for credentials")
        return None

    def send_ip_to_phone(self, ip_address: str):
        """
        Write Pi's WiFi IP to the IP characteristic.
        Phone reads this to know where to connect for image transfer.
        Must be called BEFORE stop() so BLE is still active.
        """
        if self._ip_char is None:
            print("[BLE] IP characteristic not ready")
            return False

        print(f"[BLE] Sending IP to phone: {ip_address}")
        self._ip_char.set_value(ip_address)

        # Give phone time to read the characteristic
        time.sleep(2)
        print(f"[BLE] IP sent: {ip_address}")
        return True

    def stop(self):
        """Stop BLE advertising"""
        self._running = False
        try:
            subprocess.run(
                ['sudo', 'bluetoothctl', 'discoverable', 'off'],
                capture_output=True, timeout=5
            )
            subprocess.run(
                ['sudo', 'bluetoothctl', 'pairable', 'off'],
                capture_output=True, timeout=5
            )
            print("[BLE] Advertising stopped")
        except Exception as e:
            print(f"[BLE] Stop error: {e}")

        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    # ── Internal ────────────────────────────────────────

    def _on_ssid_write(self, value: str):
        print(f"[BLE] SSID received: {value}")
        self._credentials['ssid'] = value
        self._check_credentials()

    def _on_pass_write(self, value: str):
        print("[BLE] Password received")
        self._credentials['password'] = value
        self._check_credentials()

    def _check_credentials(self):
        """Signal when both SSID and password are received"""
        if self._credentials['ssid'] and self._credentials['password']:
            self._cred_event.set()

    def _run_loop(self):
        """Asyncio event loop in background thread"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._start_gatt_server())
        except Exception as e:
            print(f"[BLE] Loop error: {e}")

    async def _start_gatt_server(self):
        """Register GATT application and advertisement with BlueZ"""
        try:
            self._bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

            # Build GATT objects
            service    = GattService()
            ssid_char  = WritableCharacteristic(SSID_UUID, SSID_PATH, self._on_ssid_write)
            pass_char  = WritableCharacteristic(PASS_UUID, PASS_PATH, self._on_pass_write)
            self._ip_char = NotifiableCharacteristic(IP_UUID)
            adv        = LEAdvertisement(self.device_id)
            app        = GattApplication(service, ssid_char, pass_char, self._ip_char)

            # Export objects on D-Bus
            self._bus.export(APP_PATH,  app)
            self._bus.export(SVC_PATH,  service)
            self._bus.export(SSID_PATH, ssid_char)
            self._bus.export(PASS_PATH, pass_char)
            self._bus.export(IP_PATH,   self._ip_char)
            self._bus.export(ADV_PATH,  adv)

            # Get BlueZ adapter proxy
            introspection = await self._bus.introspect(BLUEZ_SERVICE, ADAPTER_PATH)
            adapter_proxy = self._bus.get_proxy_object(
                BLUEZ_SERVICE, ADAPTER_PATH, introspection
            )

            # Register GATT application
            gatt_mgr = adapter_proxy.get_interface(GATT_MGR_IFACE)
            await gatt_mgr.call_register_application(APP_PATH, {})
            print("[BLE] GATT application registered")

            # Register advertisement
            adv_mgr = adapter_proxy.get_interface(LE_ADV_MGR_IFACE)
            await adv_mgr.call_register_advertisement(ADV_PATH, {})
            print("[BLE] Advertisement registered")

            # Make discoverable via bluetoothctl
            subprocess.run(
                ['sudo', 'bluetoothctl', 'discoverable', 'on'],
                capture_output=True
            )
            subprocess.run(
                ['sudo', 'bluetoothctl', 'pairable', 'on'],
                capture_output=True
            )

            # Keep running
            await asyncio.get_event_loop().create_future()

        except Exception as e:
            print(f"[BLE] GATT server error: {e}")
            import traceback
            traceback.print_exc()
