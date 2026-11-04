#!/usr/bin/python3
"""Load the add-on in an isolated real Zotero profile and test XPCOM PRIMARY."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / 'plugins/zotero-primary-bridge'
IDENTIFIER = 'pot-primary-bridge@local.invalid'
MARKER = 'Pot runtime PRIMARY 测试'
BASELINE = 'Pot runtime CLIPBOARD baseline'


def main():
    directory = ROOT / 'work/zotero-primary-runtime' / str(time.time_ns())
    profile = directory / 'profile'
    data = directory / 'library'
    for path in (profile / 'extensions', data, directory / 'run'):
        path.mkdir(parents=True, mode=0o700)
    preferences = {
        'extensions.zotero.dataDir': str(data), 'extensions.zotero.useDataDir': True,
        'extensions.zotero.firstRun2': False, 'extensions.zotero.sync.autoSync': False,
        'extensions.autoDisableScopes': 0, 'extensions.enabledScopes': 15,
        'extensions.startupScanScopes': 15, 'extensions.update.enabled': False,
        'app.update.auto': False,
    }
    (profile / 'user.js').write_text(''.join(
        f'user_pref({json.dumps(k)}, {json.dumps(v)});\n' for k, v in preferences.items()))
    harness = '''
var originalStartup = startup;
startup = async function(data) {
    await originalStartup(data);
    const entries = Zotero.Reader._registeredListeners.filter(x => x.pluginID === data.id);
    if (entries.length !== 1) throw new Error('reader event did not register');
    const helper = Components.classes['@mozilla.org/widget/clipboardhelper;1']
        .getService(Components.interfaces.nsIClipboardHelper);
    helper.copyStringToClipboard(BASELINE, Components.interfaces.nsIClipboard.kGlobalClipboard);
    entries[0].handler({params: {annotation: {text: MARKER}}});
    dump('POT_PRIMARY_RUNTIME_READY\\n');
};
'''.replace('BASELINE', json.dumps(BASELINE)).replace('MARKER', json.dumps(MARKER))
    with zipfile.ZipFile(profile / 'extensions' / (IDENTIFIER + '.xpi'), 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json', (ADDON / 'manifest.json').read_bytes())
        z.writestr('bootstrap.js', (ADDON / 'bootstrap.js').read_text() + harness)
    bus_config = directory / 'bus.conf'
    bus_config.write_text('''<busconfig><type>session</type>
<listen>unix:tmpdir=/tmp</listen><auth>EXTERNAL</auth><apparmor mode="disabled"/>
<policy context="default"><allow own="*"/><allow send_destination="*"/>
<allow receive_sender="*"/></policy></busconfig>''')
    env = dict(os.environ, GDK_BACKEND='x11', XDG_SESSION_TYPE='x11',
               GSETTINGS_BACKEND='memory', GIO_USE_VFS='local', NO_AT_BRIDGE='1',
               XDG_RUNTIME_DIR=str(directory / 'run'), MOZ_NO_REMOTE='1')
    env.pop('WAYLAND_DISPLAY', None)
    for key, folder in (('XDG_CONFIG_HOME', 'config'), ('XDG_CACHE_HOME', 'cache'),
                        ('XDG_DATA_HOME', 'data')):
        (directory / folder).mkdir()
        env[key] = str(directory / folder)
    processes = []
    try:
        bus = subprocess.Popen(['dbus-daemon', '--config-file=' + str(bus_config),
                                 '--print-address=1', '--nofork'], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True, start_new_session=True)
        processes.append(bus)
        env['DBUS_SESSION_BUS_ADDRESS'] = bus.stdout.readline().strip()
        xvfb_env = dict(env, LD_LIBRARY_PATH=str(ROOT / 'work/gui/usr/lib/x86_64-linux-gnu'))
        xvfb = subprocess.Popen([str(ROOT / 'work/gui/usr/bin/Xvfb'), '-displayfd', '1',
                                  '-screen', '0', '1024x768x24', '-extension', 'GLX', '-nolisten', 'tcp'],
                                 env=xvfb_env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 text=True, start_new_session=True)
        processes.append(xvfb)
        env['DISPLAY'] = ':' + xvfb.stdout.readline().strip()
        log = directory / 'zotero.log'
        with log.open('w') as output:
            app = subprocess.Popen(['/opt/zotero/zotero', '-no-remote', '-profile',
                                     str(profile), '-ZoteroDebugText'], env=env,
                                    stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            processes.append(app)
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if 'POT_PRIMARY_RUNTIME_READY' in log.read_text(errors='replace'):
                    break
                if app.poll() is not None:
                    raise RuntimeError(f'Isolated Zotero exited: {app.returncode}; log: {log}')
                time.sleep(.25)
            else:
                raise RuntimeError(f'Add-on did not become ready; log: {log}')
            probe = '''import gi,json
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk
Gtk.init([])
p=Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY).wait_for_text()
c=Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).wait_for_text()
print(json.dumps([p,c]))
'''
            actual = json.loads(subprocess.check_output(['/usr/bin/python3', '-c', probe],
                                                         env=env, text=True, timeout=8))
            assert actual == [MARKER, BASELINE], 'PRIMARY or CLIPBOARD contract failed'
            result = {'addon_loaded': True, 'primary_round_trip': True,
                      'normal_clipboard_preserved': True, 'zotero': '10.0.7',
                      'profile_isolated': True}
            (directory / 'result.json').write_text(json.dumps(result, indent=2))
            print(json.dumps(result))
            print('Evidence:', directory)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()


if __name__ == '__main__':
    main()
