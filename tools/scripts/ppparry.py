"""Parry test: keep #33 (OWNER) next to the opponent and block (hold R 1.2 s, release 0.3 s) for SECONDS; log both
fighters' motions and count what the opponent does within 0.8 s after each block start (S470): recoil 911,
hit 5xx, blown away 7xx. Usage: python3 -I ppparry.py PORT OWNER OPP SECONDS"""
import base64
import json
import os
import struct
import sys
import time

import websocket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppplay import find_fighter  # noqa: E402


def main():
    port, owner, opp, secs = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=10, suppress_origin=True)

    def call(ev, **a):
        ws.send(json.dumps(dict(event=ev, **a)))
        while True:
            r = json.loads(ws.recv())
            if r.get('event') in (ev, 'error'):
                return r

    def read(a, n):
        return base64.b64decode(call('memory.read', address=a, size=n).get('base64', ''))

    def write(a, b):
        call('memory.write', address=a, base64=base64.b64encode(b).decode())
    fs, fo = find_fighter(ws, owner), find_fighter(ws, opp)
    log, last, t0 = [], {}, time.time()

    def poll(sec):
        end = time.time() + sec
        while time.time() < end:
            for nm, f in (('S', fs), ('O', fo)):
                m = struct.unpack('<H', read(f + 0x180, 2))[0]
                if last.get(nm) != m:
                    log.append((time.time() - t0, nm, m))
                    last[nm] = m
            time.sleep(0.03)
    end = time.time() + secs
    while time.time() < end:
        if struct.unpack('<H', read(fs + 0x180, 2))[0] in (1200, 1210):
            break
        ox, oy, oz = struct.unpack('<3f', read(fo + 0x80, 12))
        sx, sy, sz = struct.unpack('<3f', read(fs + 0x80, 12))
        dx, dz = ox - sx, oz - sz
        n = max((dx * dx + dz * dz) ** .5, 1e-3)
        if n > 3:
            write(fs + 0x80, struct.pack('<3f', ox - dx / n * 1.8, oy, oz - dz / n * 1.8))
        write(fs + 0x90, struct.pack('<3f', dx / n, 0, dz / n))
        call('input.buttons.send', buttons={'rtrigger': True})
        poll(1.2)
        call('input.buttons.send', buttons={'rtrigger': False})
        poll(0.3)
    blocks = [t for t, nm, m in log if nm == 'S' and m == 470]
    after = {'recoil 911': 0, 'hit 5xx': 0, 'blown 7xx': 0}
    for t in blocks:
        for t2, nm, m in log:
            if nm == 'O' and t < t2 <= t + 0.8:
                if m == 911:
                    after['recoil 911'] += 1
                elif 500 <= m < 600:
                    after['hit 5xx'] += 1
                elif 700 <= m < 800:
                    after['blown 7xx'] += 1
    print('blocks', len(blocks), after)
    print(' '.join('%.1f %s%d' % x for x in log))


if __name__ == '__main__':
    main()
