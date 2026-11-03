#!/usr/bin/python3
"""Isolated StatusNotifierWatcher for the real AppIndicator integration test."""
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
name = dbus.service.BusName("org.kde.StatusNotifierWatcher", bus)


class Watcher(dbus.service.Object):
    def __init__(self):
        super().__init__(bus, "/StatusNotifierWatcher")
        self.items = []

    @dbus.service.method("org.kde.StatusNotifierWatcher", in_signature="s", out_signature="", sender_keyword="sender")
    def RegisterStatusNotifierItem(self, service, sender=None):
        item = (sender + service) if service.startswith("/") else service + "/StatusNotifierItem"
        self.items.append(item)
        print("Registered:", item, flush=True)
        self.StatusNotifierItemRegistered(item)

    @dbus.service.method("org.kde.StatusNotifierWatcher", in_signature="s", out_signature="")
    def RegisterStatusNotifierHost(self, service):
        pass

    @dbus.service.signal("org.kde.StatusNotifierWatcher", signature="s")
    def StatusNotifierItemRegistered(self, item):
        pass

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature="ss", out_signature="v")
    def Get(self, interface, prop):
        return self.GetAll(interface)[prop]

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        return {"RegisteredStatusNotifierItems": dbus.Array(self.items, signature="s"),
                "IsStatusNotifierHostRegistered": dbus.Boolean(True), "ProtocolVersion": dbus.Int32(0)}


watcher = Watcher()
GLib.MainLoop().run()
