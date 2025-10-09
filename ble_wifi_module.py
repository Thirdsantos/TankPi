#!/usr/bin/env python3
import dbus
import dbus.mainloop.glib
import dbus.service
import json
import os
import subprocess
import time
from gi.repository import GLib
import sys

# ---------- UUIDs ----------
SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"
CHAR_USER_DESC_UUID = "2901"

WPA_SUPPLICANT_FILE = "/etc/wpa_supplicant/wpa_supplicant.conf"

# ---------- WiFi Handling ----------
def connect_to_wifi(ssid, password):
    try:
        config = f"""
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={{
    ssid="{ssid}"
    psk="{password}"
}}
"""
        with open(WPA_SUPPLICANT_FILE, "w") as f:
            f.write(config)
        print(f"[WiFi] Updated config for SSID: {ssid}")
        subprocess.run(["sudo", "wpa_cli", "-i", "wlan0", "reconfigure"], check=True)
        ip = subprocess.check_output("hostname -I", shell=True).decode().strip()
        print(f"[WiFi] Connected. IPs: {ip}")
    except Exception as e:
        print(f"[WiFi] Failed to connect: {e}")

# ---------- BLE GATT Classes ----------
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
        self.descriptor_path = self.path + "/desc0"
        self.descriptor = WiFiDescriptor(bus, 0, CHAR_USER_DESC_UUID, ["read"], self, "Wi-Fi Credential Write")

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
            connect_to_wifi(ssid, password)
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
        return {"org.bluez.LEAdvertisement1": {"Type": self.ad_type, "ServiceUUIDs": dbus.Array(self.service_uuids, signature='s'), "LocalName": "TankPi-1234", "IncludeTxPower": True}}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != "org.bluez.LEAdvertisement1":
            raise dbus.exceptions.DBusException("Invalid interface")
        return self.get_properties()["org.bluez.LEAdvertisement1"]

    @dbus.service.method("org.bluez.LEAdvertisement1", in_signature="", out_signature="")
    def Release(self):
        print("[BLE] Advertisement released")

def register_advertisement(adapter, advertisement, retries=3):
    for i in range(retries):
        try:
            adapter.RegisterAdvertisement(advertisement.get_path(), {},
                                          reply_handler=lambda: print("[BLE] Advertisement registered"),
                                          error_handler=lambda e: print(f"[BLE] Failed to register: {e}"))
            return
        except Exception as e:
            print(f"[BLE] Retry {i+1} failed: {e}")
            time.sleep(1)
    print("[BLE] Could not register advertisement after retries")
    sys.exit(1)

def main():
    print("[DEBUG] Starting BLE main()")
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    # Bring up adapter
    subprocess.call(['sudo', 'rfkill', 'unblock', 'bluetooth'])
    subprocess.call(['sudo', 'hciconfig', 'hci0', 'up'])

    # Register GATT app
    app = Application(bus)

    try:
        gatt_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, "/org/bluez/hci0"), "org.bluez.GattManager1")
    except Exception as e:
        print(f"[ERROR] Could not get GattManager1: {e}")
        sys.exit(1)

    def gatt_registered():
        print("[DEBUG] GATT service registered")
        try:
            adapter = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, "/org/bluez/hci0"), "org.bluez.LEAdvertisingManager1")
            advertisement = BLEAdvertisement(bus, 0, "peripheral")
            register_advertisement(adapter, advertisement)
        except Exception as e:
            print(f"[ERROR] Failed to start advertisement: {e}")
            sys.exit(1)

    try:
        gatt_manager.RegisterApplication(app.get_path(), {}, reply_handler=gatt_registered,
                                         error_handler=lambda e: print(f"[ERROR] Failed to register GATT: {e}"))
    except Exception as e:
        print(f"[ERROR] RegisterApplication exception: {e}")
        sys.exit(1)

    print("[BLE] WiFi provisioning service running...")
    try:
        GLib.MainLoop().run()
    except KeyboardInterrupt:
        print("[EXIT] KeyboardInterrupt")

if __name__ == "__main__":
    main()
