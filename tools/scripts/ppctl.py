"""Drive PPSSPP through its remote debugger: screenshots and button presses.
Usage: python3 -I ppctl.py PORT shot OUT.png
       python3 -I ppctl.py PORT press BUTTON [BUTTON ...]   (cross circle square triangle up down left right start select ltrigger rtrigger)
       env DUR=frames to hold each button (default 6; battle needs >= 12, pause = 20)
"""
import base64
import os
import json
import sys
import time

import websocket


def wait(ws, *events):
    while True:
        r = json.loads(ws.recv())
        if r.get('event') in events + ('error',):
            return r


def shot(ws, out):
    ws.send(json.dumps({'event': 'cpu.stepping'}))
    wait(ws, 'cpu.stepping')
    ws.send(json.dumps({'event': 'gpu.buffer.screenshot', 'type': 'base64'}))
    r = wait(ws, 'gpu.buffer.screenshot')
    ws.send(json.dumps({'event': 'cpu.resume'}))
    data = r.get('base64') or r.get('uri', ',').split(',', 1)[1]
    if not data:
        sys.exit(str(r))
    open(out, 'wb').write(base64.b64decode(data))
    print('saved', out, r.get('width'), r.get('height'))


def press(ws, button):
    ws.send(json.dumps({'event': 'input.buttons.press', 'button': button, 'duration': int(os.environ.get('DUR', 6))}))
    r = wait(ws, 'input.buttons.press')
    if r.get('event') == 'error':
        sys.exit(str(r))
    time.sleep(0.4)


def main():
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % sys.argv[1], timeout=90, suppress_origin=True)
    if sys.argv[2] == 'shot':
        shot(ws, sys.argv[3])
    elif sys.argv[2] == 'press':
        for b in sys.argv[3:]:
            press(ws, b)
        print('pressed', ' '.join(sys.argv[3:]))


if __name__ == '__main__':
    main()
