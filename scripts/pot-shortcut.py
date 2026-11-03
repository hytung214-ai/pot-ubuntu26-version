#!/usr/bin/python3
"""Invoke Pot's existing local actions from compositor-managed shortcuts."""
import argparse
from datetime import datetime, timezone
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

ACTIONS = {'selection': '/selection_translate', 'input': '/input_translate',
           'ocr-recognize': '/ocr_recognize', 'ocr-translate': '/ocr_translate'}


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=ACTIONS, nargs='?', default='selection')
    parser.add_argument('--probe', action='store_true', help='Check the local listener without opening windows')
    parser.add_argument('--log', type=Path)
    args = parser.parse_args()
    try:
        port = pot_port()
        if args.probe:
            with socket.create_connection(('127.0.0.1', port), timeout=2):
                pass
            print(f'Pot local listener is reachable on 127.0.0.1:{port}')
            return 0
        try:
            call_action(port, args.action)
        except ConnectionRefusedError:
            # Only retry a connection refusal. Do not repeat requests that timed
            # out after acceptance, which could duplicate paid translations.
            subprocess.Popen(['/usr/bin/pot'], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
            for attempt in range(50):
                time.sleep(.1)
                try:
                    call_action(port, args.action)
                    break
                except ConnectionRefusedError:
                    if attempt == 49:
                        raise
        log_event(args.log, f'{args.action}: accepted by Pot (HTTP 200)')
        return 0
    except Exception as error:
        message = f'{args.action}: {type(error).__name__}: {error}'
        log_event(args.log, message)
        print(message, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
