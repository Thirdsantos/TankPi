#!/usr/bin/env python3
# ble_wifi_module_fixed.py
# BLE Wi-Fi provisioning for TankPi with proper adapter wait, sync registration, and cleanup

import os
import sys
import time
import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
import subprocess
from gi.repository import GLib
import json

# -----------------------------
# BLE Constants
# -----------------------------
SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHARACTERISTIC_UUID = "12345678-1234-5678-1234-56789abcdef1"
ADVERTISING_NAME = "TankPi"
TIMEOUT_SECONDS = 300  # 5 minutes

# D-Bus constants
BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
AGENT_MANAGER_IFACE = 'org.bluez.AgentManager1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'

# -----------------------------
# GATT Application
# -----------------------------
class Application(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/app'

    def __init__(self, bus):
        self.path = self.PATH_BASE
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(WiFiService(bus, 0))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        managed_objects = {}
        for service in self.services:
            managed_objects[service.get_path()] = service.get_properties()
            for charac in service.characteristics:
                managed_objects[charac.get_path()] = charac.get_properties()
        return managed_objects

class WiFiService(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/service'

    def __init__(self, bus, index):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = SERVICE_UUID
        self.primary = True
        self.characteristics = [WiFiCharacteristic(bus, 0, self)]
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {'org.bluez.GattService1': {'UUID': self.uuid, 'Primary': self.primary}}

    def get_path(self):
        return dbus.ObjectPath(self.path)

class WiFiCharacteristic(dbus.service.Object):
    def __init__(self, bus, index, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = CHARACTERISTIC_UUID
        self.service = service
        self.flags = ['write-without-response']
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {'org.bluez.GattCharacteristic1': {'UUID': self.uuid,
                                                  'Service': self.service.get_path(),
                                                  'Flags': self.flags}}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method('org.bluez.GattCharacteristic1',
                         in_signature='aya{sv}', out_signature='')
    def WriteValue(self, value, options):
        try:
            data = bytes(value).decode('utf-8')
            print(f"[BLE] Received Wi-Fi credentials: {data}")
            handle_wifi_credentials(data)
        except Exception as e:
            print(f"[BLE] WriteValue error: {e}")

# -----------------------------
# BLE Advertisement
# -----------------------------
class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/advertisement'

    def __init__(self, bus, index):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.type = 'peripheral'
        self.service_uuids = [SERVICE_UUID]
        self.local_name = ADVERTISING_NAME
        self.include_tx_power = True
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {'org.bluez.LEAdvertisement1': {'Type': self.type,
                                               'ServiceUUIDs': self.service_uuids,
                                               'LocalName': self.local_name,
                                               'IncludeTxPower': dbus.Boolean(self.include_tx_power)}}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method('org.freedesktop.DBus.Properties',
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != 'org.bluez.LEAdvertisement1':
            raise dbus.exceptions.DBusException('Invalid interface')
        return self.get_properties()['org.bluez.LEAdvertisement1']

    @dbus.service.method('org.bluez.LEAdvertisement1')
    def Release(self):
        print("[BLE] Advertisement released")

# -----------------------------
# NoInputNoOutput Agent
# -----------------------------
class NoInputNoOutputAgent(dbus.service.Object):
    AGENT_PATH = "/org/bluez/agent_no_input_no_output"

    def __init__(self, bus):
        dbus.service.Object.__init__(self, bus, self.AGENT_PATH)

    @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
    def Release(self):
        pass

# -----------------------------
# Wi-Fi Handler
# -----------------------------
def handle_wifi_credentials(data):
    try:
        creds = json.loads(data)
        ssid = creds.get("ssid")
        password = creds.get("password")
        if ssid:
            print(f"[Wi-Fi] Connecting to SSID: {ssid}")
            subprocess.call(["nmcli", "dev", "wifi", "connect", ssid, "password", password])
            time.sleep(2)
            ip_output = subprocess.getoutput("hostname -I")
            print(f"[Wi-Fi] Connected ✅  IP: {ip_output}")
        else:
            print("[Wi-Fi] Invalid data")
    except Exception as e:
        print(f"[Wi-Fi] Error: {e}")

# -----------------------------
# Main BLE Logic
# -----------------------------
def main():
    print("[BLE] Starting BLE provisioning service...")

    # --- Power up Bluetooth controller ---
    subprocess.call(['sudo', 'rfkill', 'unblock', 'bluetooth'])
    subprocess.call(['sudo', 'hciconfig', 'hci0', 'up'])
    time.sleep(1)

    # --- Initialize D-Bus ---
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    # --- Wait for BlueZ adapter ---
    adapter_path = "/org/bluez/hci0"
    max_retries = 6
    for i in range(max_retries):
        try:
            bus.get_object(BLUEZ_SERVICE_NAME, adapter_path)
            print("[BLE] BlueZ adapter detected ✅")
            break
        except dbus.exceptions.DBusException:
            print(f"[BLE] Waiting for adapter... ({i+1}/{max_retries})")
            time.sleep(1)
    else:
        print("[BLE] Adapter not found ❌")
        return

    # --- Register NoInputNoOutput agent ---
    agent = NoInputNoOutputAgent(bus)
    manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, "/org/bluez"),
                             AGENT_MANAGER_IFACE)
    manager.RegisterAgent(agent.AGENT_PATH, "NoInputNoOutput")
    manager.RequestDefaultAgent(agent.AGENT_PATH)
    print("[BLE] Agent registered ✅")

    # --- Register GATT application and advertisement synchronously ---
    adapter = bus.get_object(BLUEZ_SERVICE_NAME, adapter_path)
    gatt_manager = dbus.Interface(adapter, GATT_MANAGER_IFACE)
    ad_manager = dbus.Interface(adapter, LE_ADVERTISING_MANAGER_IFACE)

    app = Application(bus)
    adv = Advertisement(bus, 0)

    # Register app
    try:
        gatt_manager.RegisterApplication(app.get_path(), {},
                                         reply_handler=lambda: print("[BLE] GATT app registered ✅"),
                                         error_handler=lambda e: print(f"[BLE] GATT register failed: {e}"))
    except Exception as e:
        print(f"[BLE] RegisterApplication error: {e}")
        return

    # Register advertisement
    try:
        ad_manager.RegisterAdvertisement(adv.get_path(), {},
                                         reply_handler=lambda: print("[BLE] Advertisement registered ✅"),
                                         error_handler=lambda e: print(f"[BLE] Adv register failed: {e}"))
    except Exception as e:
        print(f"[BLE] RegisterAdvertisement error: {e}")
        return

    # --- Run main loop with timeout ---
    mainloop = GLib.MainLoop()

    def timeout():
        print("[BLE] Timeout reached → stopping BLE")
        try:
            ad_manager.UnregisterAdvertisement(adv.get_path())
            print("[BLE] Advertisement unregistered ✅")
        except Exception:
            pass
        try:
            subprocess.call(['sudo', 'bluetoothctl', 'power', 'off'])
            subprocess.call(['sudo', 'hciconfig', 'hci0', 'down'])
        except Exception as e:
            print(f"[BLE] Stop error: {e}")
        mainloop.quit()
        return False

    GLib.timeout_add_seconds(TIMEOUT_SECONDS, timeout)
    print(f"[BLE] Wi-Fi provisioning active for {TIMEOUT_SECONDS // 60} minutes…")
    mainloop.run()

if __name__ == '__main__':
    main()
