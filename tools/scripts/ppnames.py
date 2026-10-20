"""Log every PACKAGE file path the game looks up (breakpoint on FUN_088713e4, a1 = path string).
Usage: python3 -I ppnames.py PORT SECONDS OUTFILE
       env PRESS=button presses it once after the breakpoint is set (DUR = frames, default 12)
"""
import base64
import json
import os
import sys
import time

import websocket

LOOKUP = 0x088713E4


def wait(ws, ev):
    while True:
        r = json.loads(ws.recv())
        if r.get('event') in (ev, 'error'):
            return r


def main():
    port, secs, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=40, suppress_origin=True)
    ws.settimeout(2)
    ws.send(json.dumps({'event': 'cpu.breakpoint.add', 'address': LOOKUP, 'enabled': True}))
    if os.environ.get('PRESS'):
        ws.send(json.dumps({'event': 'input.buttons.press', 'button': os.environ['PRESS'],
                            'duration': int(os.environ.get('DUR', 12))}))
    seen = []
    end = time.time() + secs
    try:
        with open(out, 'a') as log:
            while time.time() < end:
                try:
                    r = json.loads(ws.recv())
                except websocket.WebSocketTimeoutException:
                    continue
                if r.get('event') != 'cpu.stepping':
                    continue
                ws.send(json.dumps({'event': 'cpu.getAllRegs'}))
                g = wait(ws, 'cpu.getAllRegs')
                reg = dict(zip(g['categories'][0]['registerNames'], g['categories'][0]['uintValues']))
                ws.send(json.dumps({'event': 'memory.read', 'address': reg['a1'], 'size': 80}))
                m = wait(ws, 'memory.read')
                name = base64.b64decode(m.get('base64', '')).split(b'\0')[0].decode('latin1')
                ws.send(json.dumps({'event': 'cpu.resume'}))
                if name not in seen:
                    seen.append(name)
                    log.write(name + '\n')
                    log.flush()
                    print(name, flush=True)
    finally:
        ws.send(json.dumps({'event': 'cpu.breakpoint.remove', 'address': LOOKUP}))
        ws.send(json.dumps({'event': 'cpu.resume'}))
        time.sleep(0.5)


if __name__ == '__main__':
    main()
