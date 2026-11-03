#!/usr/bin/python3
"""Install or undo a single user-owned GNOME shortcut, preserving other bindings."""
import argparse
import json
from pathlib import Path
import shlex
from gi.repository import Gio

SCHEMA = 'org.gnome.settings-daemon.plugins.media-keys'
BINDING_PATH = '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/pot-translation-selection/'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--helper', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--remove', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    parent = Gio.Settings.new(SCHEMA)
    child = Gio.Settings.new_with_path(SCHEMA + '.custom-keybinding', BINDING_PATH)
    paths = list(parent.get_strv('custom-keybindings'))
    fields = ('name', 'command', 'binding')
    state_file = args.state / 'gnome-before.json'
    desired = {
        'name': 'Pot 划词翻译',
        'command': shlex.join(['/usr/bin/python3', str(args.helper.resolve()), 'selection',
                               '--log', str((args.state / 'invocations.log').resolve())]),
        'binding': '<Primary>t',
    }
    if args.dry_run:
        print(json.dumps({'existing_paths': paths, 'path': BINDING_PATH,
                          'desired': desired}, ensure_ascii=False, indent=2))
        return
    if args.remove:
        saved = json.loads(state_file.read_text())
        # Refuse to undo a binding someone has subsequently edited.
        if any(child.get_string(key) != value for key, value in saved['installed'].items()):
            raise RuntimeError('Binding changed since installation; refusing to overwrite it')
        if not saved['existed']:
            parent.set_strv('custom-keybindings', [p for p in paths if p != BINDING_PATH])
        child.delay()
        for key, value in saved['values'].items():
            child.set_string(key, value)
        child.apply()
    else:
        if not args.helper.is_file():
            raise RuntimeError('Helper does not exist')
        for path in paths:
            other = Gio.Settings.new_with_path(SCHEMA + '.custom-keybinding', path)
            if path != BINDING_PATH and other.get_string('binding').lower() in ('<primary>t', '<control>t', '<ctrl>t'):
                raise RuntimeError('Another custom shortcut already uses Ctrl+T')
        args.state.mkdir(parents=True, exist_ok=True)
        if not state_file.exists():
            state = {'existed': BINDING_PATH in paths,
                     'values': {key: child.get_string(key) for key in fields},
                     'installed': desired}
            with state_file.open('x') as output:
                json.dump(state, output, ensure_ascii=False, indent=2)
        elif json.loads(state_file.read_text())['installed'] != desired:
            raise RuntimeError('Existing backup is for a different installation')
        child.delay()
        for key, value in desired.items():
            child.set_string(key, value)
        child.apply()
        if BINDING_PATH not in paths:
            parent.set_strv('custom-keybindings', paths + [BINDING_PATH])
    Gio.Settings.sync()
    # Read back using a separate process as well when validating installation.
    print('Removed' if args.remove else 'Installed', BINDING_PATH)


if __name__ == '__main__':
    main()
