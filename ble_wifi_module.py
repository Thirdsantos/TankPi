#!/usr/bin/env python3
import dbus
import dbus.mainloop.glib
import dbus.service
import json
import os
import subprocess
import time
from gi.repository import GLib
import shutil
import sys

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"
CHAR_USER_DESC_UUID = "2901"
WPA_SUPPLICANT_FILE = "/etc/wpa_supplicant/wpa_supplicant.conf"

# ---------- Helper ----------
def has_nmcli():
    return shutil.which("nmcli") is not None

# ---------- WiFi Handling ----------
def connect_to_wifi(ssid, password):
    if has_nmcli():
        print(f"[WiFi] NetworkManager detected. Using nmcli for SSID '{ssid}'...")
        try:
            subprocess.run(["sudo", "nmcli", "radio", "wifi", "on"], check=False)
            subprocess.run(["sudo", "nmcli", "dev", "disconnect", "wlan0"], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "nmcli", "con", "down", ssid], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "nmcli", "con", "delete", ssid], stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "nmcli", "dev", "wifi", "connect", ssid, "password", password], check=True)
            ip = subprocess.check_output("hostname -I", shell=True).decode().strip()
            print(f"[WiFi] Connected via nmcli. IPs: {ip if ip else '(none)'}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[WiFi] nmcli failed: {e}")
            return False
    else:
        # Manual fallback
        print("[WiFi] NetworkManager not found, using wpa_supplicant method...")
        try:
            if os.path.exists(WPA_SUPPLICANT_FILE):
                os.remove(WPA_SUPPLICANT_FILE)

            config = f"""
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=PH

network={{
    ssid="{ssid}"
    psk="{password}"
}}
"""
            with open(WPA_SUPPLICANT_FILE, "w") as f:
                f.write(config.strip() + "\n")

            print(f"[WiFi] Wrote config for SSID: {ssid}")
            subprocess.run(["sudo", "pkill", "-f", "wpa_supplicant"], stderr=subprocess.DEVNULL)
            time.sleep(1)
            subprocess.run(["sudo", "wpa_supplicant", "-B", "-i", "wlan0", "-c", WPA_SUPPLICANT_FILE], check=True)
            print("[WiFi] wpa_supplicant restarted")
            subprocess.run(["sudo", "dhclient", "-r", "wlan0"], stderr=subprocess.DEVNULL)
            time.sleep(1)
            subprocess.run(["sudo", "dhclient", "wlan0"], check=True)
            ip = subprocess.check_output("hostname -I", shell=True).decode().strip()
            print(f"[WiFi] Connected successfully. IPs: {ip if ip else '(none)'}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[WiFi] Command failed: {e}")
            return False
        except Exception as e:
            print(f"[WiFi] Exception: {e}")
            return False

# ---------- BLE GATT ----------
BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_DESC_IFACE = 'org.bluez.GattDescriptor1'

class WiFiCharacteristic(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + f"/char{index}"
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.service = service
        dbus.service.Object.__init__(self, bus, self.path)
        self.descriptor = WiFiDescriptor(bus, 0, CHAR_USER_DESC_UUID, ["read"], self, "Wi-Fi Credentials")

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(dbus_interface=GATT_CHRC_IFACE, in_signature='aya{sv}', out_signature='')
    def WriteValue(self, value, options):
        try:
            payload = bytearray(value).decode()
            creds = json.loads(payload)
            ssid = creds.get("ssid")
            password = creds.get("password")
            print(f"[BLE] Received WiFi creds: {ssid}/{password}")
            success = connect_to_wifi(ssid, password)
            print("[BLE] WiFi connection " + ("successful ✅" if success else "failed ❌"))
        except Exception as e:
            print(f"[BLE] WriteValue error: {e}")

class WiFiDescriptor(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags, characteristic, value):
        self.path = characteristic.path + f"/desc{index}"
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.characteristic = characteristic
        self.value = value
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise dbus.exceptions.DBusException("Invalid interface")
        return {"UUID": self.uuid, "Characteristic": self.characteristic.get_path(),
                "Flags": dbus.Array(self.flags, signature='s')}

    @dbus.service.method(dbus_interface=GATT_DESC_IFACE, in_signature='', out_signature='ay')
    def ReadValue(self):
        return dbus.Array(bytearray(self.value, 'utf-8'), signature='y')


class WiFiService(dbus.service.Object):
    def __init__(self, bus, index):
        self.path = f"/org/bluez/example/service{index}"
        self.bus = bus
        self.uuid = SERVICE_UUID
        self.primary = True
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_characteristic(WiFiCharacteristic(bus, 0, CHAR_UUID, ["write"], self))

    def add_characteristic(self, chrc):
        self.characteristics.append(chrc)

    def get_path(self):
        return dbus.ObjectPath(self.path)

class Application(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/application'
    def __init__(self, bus):
        self.path = self.PATH_BASE
        self.bus = bus
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(WiFiService(bus, 0))

    def add_service(self, service):
        self.services.append(service)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method("org.freedesktop.DBus.ObjectManager", out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = {GATT_SERVICE_IFACE: {'UUID': service.uuid, 'Primary': service.primary}}
            for char in service.characteristics:
                response[char.get_path()] = {GATT_CHRC_IFACE: {'Service': service.get_path(), 'UUID': char.uuid, 'Flags': dbus.Array(char.flags, signature='s')}}
                response[char.descriptor.get_path()] = {GATT_DESC_IFACE: {'Characteristic': char.get_path(), 'UUID': char.descriptor.uuid, 'Flags': dbus.Array(char.descriptor.flags, signature='s')}}
        return response

class BLEAdvertisement(dbus.service.Object):
    PATH_BASE = "/org/bluez/example/advertisement"
    def __init__(self, bus, index, adv_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = adv_type
        self.service_uuids = [SERVICE_UUID]
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            "org.bluez.LEAdvertisement1": {
                "Type": self.ad_type,
                "ServiceUUIDs": dbus.Array(self.service_uuids, signature='s'),
                "LocalName": "TankPi",
                "IncludeTxPower": True
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        return self.get_properties()["org.bluez.LEAdvertisement1"]

    @dbus.service.method("org.bluez.LEAdvertisement1", in_signature="", out_signature="")
    def Release(self):
        print("[BLE] Advertisement released")

def cleanup():
    print("[EXIT] Cleaning up BLE/WiFi processes...")
    subprocess.call(['sudo', 'pkill', '-f', 'wpa_supplicant'])
    subprocess.call(['sudo', 'hciconfig', 'hci0', 'down'])
    subprocess.call(['sudo', 'systemctl', 'restart', 'bluetooth'])
    subprocess.call(['sudo', 'rfkill', 'unblock', 'all'])
    print("[EXIT] Cleanup complete.")

def main():
    print("[DEBUG] Starting BLE main()")

    # --- Clean up from any previous runs ---
    subprocess.call(['sudo', 'pkill', '-f', 'wpa_supplicant'])
    subprocess.call(['sudo', 'pkill', '-f', 'bluetoothd'])
    subprocess.call(['sudo', 'systemctl', 'start', 'bluetooth'])
    subprocess.call(['sudo', 'rfkill', 'unblock', 'all'])
    time.sleep(1)

    # --- Reset Bluetooth adapter cleanly ---
    print("[DEBUG] Resetting Bluetooth adapter (hci0)...")
    for i in range(3):  # up to 3 retries
        try:
            subprocess.call(["sudo", "hciconfig", "hci0", "down"], stderr=subprocess.DEVNULL)
            subprocess.call(["sudo", "hciconfig", "hci0", "reset"], stderr=subprocess.DEVNULL)
            subprocess.call(["sudo", "hciconfig", "hci0", "up"], stderr=subprocess.DEVNULL)
            time.sleep(1)
            # quick check to confirm it's up
            output = subprocess.check_output(["hciconfig", "hci0"], text=True)
            if "UP RUNNING" in output:
                print("[DEBUG] hci0 is up and running ✅")
                break
            else:
                print(f"[WARN] hci0 not ready (attempt {i+1})")
        except subprocess.CalledProcessError:
            print(f"[ERROR] hciconfig failed (attempt {i+1})")
        time.sleep(2)
    else:
        print("[FATAL] Could not initialize hci0 after retries.")
        sys.exit(1)

    # --- BLE setup ---
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    app = Application(bus)

    try:
        gatt_manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, "/org/bluez/hci0"),
            "org.bluez.GattManager1"
        )
    except Exception as e:
        print(f"[ERROR] Could not get GattManager1: {e}")
        cleanup()
        sys.exit(1)

    def gatt_registered():
        print("[DEBUG] GATT service registered")
        try:
            adapter = dbus.Interface(
                bus.get_object(BLUEZ_SERVICE_NAME, "/org/bluez/hci0"),
                "org.bluez.LEAdvertisingManager1"
            )
            advertisement = BLEAdvertisement(bus, 0, "peripheral")

            def adv_error(e):
                print(f"[BLE] Advertisement registration failed: {e}")
                print("[DEBUG] Retrying BLE advertisement...")
                for j in range(3):
                    time.sleep(2)
                    try:
                        adapter.RegisterAdvertisement(
                            advertisement.get_path(), {},
                            reply_handler=lambda: print("[BLE] Advertisement registered ✅"),
                            error_handler=lambda e: print(f"[BLE] Retry {j+1} failed: {e}")
                        )
                        return
                    except Exception as ex:
                        print(f"[BLE] Retry {j+1} exception: {ex}")
                print("[FATAL] Could not register BLE advertisement after retries.")
                sys.exit(1)

            adapter.RegisterAdvertisement(
                advertisement.get_path(), {},
                reply_handler=lambda: print("[BLE] Advertisement registered ✅"),
                error_handler=adv_error
            )

        except Exception as e:
            print(f"[ERROR] Failed to start advertisement: {e}")
            cleanup()
            sys.exit(1)

    try:
        gatt_manager.RegisterApplication(
            app.get_path(), {},
            reply_handler=gatt_registered,
            error_handler=lambda e: print(f"[ERROR] Failed to register GATT: {e}")
        )
    except Exception as e:
        print(f"[ERROR] RegisterApplication exception: {e}")
        cleanup()
        sys.exit(1)

    print("[BLE] WiFi provisioning service running...")
    try:
        GLib.MainLoop().run()
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
