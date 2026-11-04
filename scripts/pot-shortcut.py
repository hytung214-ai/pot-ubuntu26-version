#!/usr/bin/python3
"""Invoke Pot's existing local actions from compositor-managed shortcuts."""
import argparse
import ctypes
from datetime import datetime, timezone
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

ACTIONS = {'selection': '/selection_translate', 'input': '/input_translate',
           'ocr-recognize': '/ocr_recognize', 'ocr-translate': '/ocr_translate'}


def activate_translate_window():
    """Ask the WM to activate Pot after this explicit user shortcut action.

    HTTP success alone does not propagate desktop activation to the existing
    XWayland process. Use EWMH instead of changing focus-stealing security policy.
    xprop is provided by Ubuntu's x11-utils; no extra packages are installed here.
    """
    if not os.environ.get('DISPLAY') or not shutil.which('xprop'):
        return False

    def properties(*args):
        return subprocess.run(['xprop', *args], capture_output=True, text=True,
                              timeout=2, check=False).stdout

    target = None
    # New windows can finish mapping shortly after the HTTP response.
    for attempt in range(10):
        time.sleep(.1)
        for xid in re.findall(r'0x[0-9a-fA-F]+', properties('-root', '_NET_CLIENT_LIST')):
            wm_class = properties('-id', xid, 'WM_CLASS')
            if not re.search(r'WM_CLASS.*"pot", "Pot"', wm_class):
                continue
            if '"Translate"' in properties('-id', xid, '_NET_WM_NAME'):
                target = int(xid, 16)
                break
        if target is not None:
            break
    if target is None:
        return False

    class Data(ctypes.Union):
        _fields_ = [('l', ctypes.c_long * 5)]

    class ClientMessage(ctypes.Structure):
        _fields_ = [('type', ctypes.c_int), ('serial', ctypes.c_ulong),
                    ('send_event', ctypes.c_int), ('display', ctypes.c_void_p),
                    ('window', ctypes.c_ulong), ('message_type', ctypes.c_ulong),
                    ('format', ctypes.c_int), ('data', Data)]

    class Event(ctypes.Union):
        _fields_ = [('client', ClientMessage), ('pad', ctypes.c_long * 24)]

    x11 = ctypes.CDLL('libX11.so.6')
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x11.XDefaultRootWindow.restype = ctypes.c_ulong
    x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    x11.XInternAtom.restype = ctypes.c_ulong
    x11.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int,
                               ctypes.c_long, ctypes.POINTER(Event)]
    x11.XFlush.argtypes = [ctypes.c_void_p]
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    display = x11.XOpenDisplay(None)
    if not display:
        return False
    try:
        event = Event()
        event.client.type = 33  # ClientMessage
        event.client.display = display
        event.client.window = target
        event.client.message_type = x11.XInternAtom(display, b'_NET_ACTIVE_WINDOW', 0)
        event.client.format = 32
        # EWMH source 2 includes tools representing direct user actions.
        event.client.data.l[0] = 2
        startup_time = re.search(r'_TIME(\d+)', os.environ.get('DESKTOP_STARTUP_ID', ''))
        event.client.data.l[1] = int(startup_time[1]) if startup_time else 0
        x11.XSendEvent(display, x11.XDefaultRootWindow(display), 0,
                       (1 << 20) | (1 << 19), ctypes.byref(event))
        x11.XFlush(display)
    finally:
        x11.XCloseDisplay(display)
    time.sleep(.1)
    active = properties('-root', '_NET_ACTIVE_WINDOW')
    return any(int(xid, 16) == target for xid in re.findall(r'0x[0-9a-fA-F]+', active))


def pot_port():
    config_home = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    config = config_home / 'com.pot-app.desktop/config.json'
    try:
        value = json.loads(config.read_text()).get('server_port', 60828)
    except FileNotFoundError:
        value = 60828
    if type(value) is not int or not 1 <= value <= 65535:
        raise ValueError('Pot server_port is invalid')
    return value


def log_event(path, message):
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a') as output:
            output.write(datetime.now(timezone.utc).isoformat() + ' ' + message + '\n')


def call_action(port, action):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=8)
    try:
        connection.request('POST', ACTIONS[action], body=b'')
        response = connection.getresponse()
        # Never print or log selected text, translation contents or API keys.
        body = response.read(128)
        if response.status != 200 or body.strip() != b'ok':
            raise RuntimeError(f'Unexpected local Pot response: HTTP {response.status}')
    finally:
        connection.close()


def read_wayland_selection():
    """Receive the primary offer on a focused native Wayland GTK surface."""
    os.environ['GDK_BACKEND'] = 'wayland'
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, Gdk, GLib
    ok, _ = Gtk.init_check([])
    if not ok or type(Gdk.Display.get_default()).__name__ != 'GdkWaylandDisplay':
        raise RuntimeError('Native Wayland display unavailable')
    window = Gtk.Window(title='Pot selection reader')
    window.set_decorated(False)
    window.set_default_size(2, 2)
    window.set_skip_taskbar_hint(True)
    window.set_skip_pager_hint(True)
    window.set_opacity(.01)
    if os.environ.get('DESKTOP_STARTUP_ID'):
        window.set_startup_id(os.environ['DESKTOP_STARTUP_ID'])
    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
    result = []
    requested = [False]

    def received(_clipboard, value, _data):
        if value and value.strip():
            result.append(value)
            Gtk.main_quit()

    def request():
        clipboard.request_text(received, None)
        return False

    def focused(_window, _event):
        if not requested[0]:
            requested[0] = True
            GLib.timeout_add(150, request)
        return False

    window.connect('focus-in-event', focused)
    window.show_all()
    window.present()
    GLib.timeout_add(2500, lambda: Gtk.main_quit() or False)
    Gtk.main()
    window.destroy()
    if not result:
        raise RuntimeError('No native Wayland primary selection received')
    return result[0]


def native_selection():
    # Keep GTK's Wayland backend isolated from the X11 activation code.
    env = dict(os.environ, GDK_BACKEND='wayland')
    child = subprocess.run(['/usr/bin/python3', str(Path(__file__).resolve()),
                            '--read-wayland-selection'], env=env, capture_output=True,
                           text=True, timeout=5)
    if child.returncode != 0 or not child.stdout.strip():
        raise RuntimeError('Native Wayland selection unavailable; no X11 fallback was used')
    return child.stdout


def send_text(port, text):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=8)
    try:
        connection.request('POST', '/translate', body=text.encode('utf-8'),
                           headers={'Content-Type': 'text/plain; charset=utf-8'})
        response = connection.getresponse()
        if response.status != 200 or response.read(128).strip() != b'ok':
            raise RuntimeError(f'Unexpected local Pot response: HTTP {response.status}')
    finally:
        connection.close()


def invoke_action(port, action, selection_text=None):
    if action == 'selection' and os.environ.get('XDG_SESSION_TYPE') == 'wayland':
        if selection_text is None:
            raise RuntimeError('Current selection must be captured before invoking Pot')
        send_text(port, selection_text)
    else:
        call_action(port, action)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=ACTIONS, nargs='?', default='selection')
    parser.add_argument('--probe', action='store_true', help='Check the local listener without opening windows')
    parser.add_argument('--log', type=Path)
    parser.add_argument('--read-wayland-selection', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.read_wayland_selection:
            sys.stdout.write(read_wayland_selection())
            return 0
        port = pot_port()
        if args.probe:
            with socket.create_connection(('127.0.0.1', port), timeout=2):
                pass
            print(f'Pot local listener is reachable on 127.0.0.1:{port}')
            return 0
        selection_text = None
        if args.action == 'selection' and os.environ.get('XDG_SESSION_TYPE') == 'wayland':
            selection_text = native_selection()
            log_event(args.log, 'selection source: focused native Wayland surface')
        try:
            invoke_action(port, args.action, selection_text)
        except ConnectionRefusedError:
            # Only retry a connection refusal. Do not repeat requests that timed
            # out after acceptance, which could duplicate paid translations.
            subprocess.Popen(['/usr/bin/pot'], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
            for attempt in range(50):
                time.sleep(.1)
                try:
                    invoke_action(port, args.action, selection_text)
                    break
                except ConnectionRefusedError:
                    if attempt == 49:
                        raise
        log_event(args.log, f'{args.action}: accepted by Pot (HTTP 200)')
        if args.action in ('selection', 'input'):
            try:
                activated = activate_translate_window()
                log_event(args.log, 'window activation: ' + ('verified' if activated else 'not verified'))
            except Exception as error:
                # Do not retry the translation when only window activation fails.
                log_event(args.log, f'window activation: {type(error).__name__}')
        return 0
    except Exception as error:
        message = f'{args.action}: {type(error).__name__}: {error}'
        log_event(args.log, message)
        print(message, file=sys.stderr)
        if not args.read_wayland_selection and args.action == 'selection' and shutil.which('notify-send'):
            subprocess.run(['notify-send', '--app-name=Pot', 'Pot 划词调用失败',
                            '请重新选择文字后重试；Zotero PDF 请按住 Alt 拖选。'], timeout=3, check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
