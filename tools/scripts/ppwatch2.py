"""Like ppwatch.py but also prints u32 at (a0 + OFF) for each hit, to tell callers apart.
Usage: python3 -I ppwatch2.py PORT SECONDS OFF ADDR [ADDR ...]
Set PRESS=circle (any button name) to press it once, 1 s after the breakpoints are set.
"""
import base64
import json
import os
import struct
import sys
import time

import websocket


def wait(ws, ev):
    while True:
        r = json.loads(ws.recv())
        if r.get('event') in (ev, 'error'):
            return r


def main():
    port, secs, off = sys.argv[1], float(sys.argv[2]), int(sys.argv[3], 0)
    addrs = [int(a, 0) for a in sys.argv[4:]]
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=5, suppress_origin=True)
    for a in addrs:
        ws.send(json.dumps({'event': 'cpu.breakpoint.add', 'address': a, 'enabled': True}))
    end = time.time() + secs
    n = 0
    press_at = time.time() + 1 if os.environ.get('PRESS') else None
    try:
        while time.time() < end and n < 40:
            if press_at and time.time() >= press_at:
                ws.send(json.dumps({'event': 'input.buttons.press', 'button': os.environ['PRESS'], 'duration': 12}))
                print('pressed', os.environ['PRESS'], flush=True)
                press_at = None
            try:
                r = json.loads(ws.recv())
            except websocket.WebSocketTimeoutException:
                continue
            if r.get('event') != 'cpu.stepping':
                continue
            ws.send(json.dumps({'event': 'cpu.getAllRegs'}))
            g = wait(ws, 'cpu.getAllRegs')
            reg = dict(zip(g['categories'][0]['registerNames'], g['categories'][0]['uintValues']))
            ws.send(json.dumps({'event': 'memory.read', 'address': reg['a0'] + off, 'size': 4}))
            m = wait(ws, 'memory.read')
            v = struct.unpack('<I', base64.b64decode(m['base64']))[0] if 'base64' in m else -1
            print('hit %08x ra=%08x a0=%08x a1=%08x [a0+%x]=%08x' % (r.get('pc', 0), reg['ra'], reg['a0'], reg['a1'], off, v), flush=True)
            n += 1
            ws.send(json.dumps({'event': 'cpu.resume'}))
    finally:
        for a in addrs:
            ws.send(json.dumps({'event': 'cpu.breakpoint.remove', 'address': a}))
        ws.send(json.dumps({'event': 'cpu.resume'}))
        time.sleep(0.5)


if __name__ == '__main__':
    main()
