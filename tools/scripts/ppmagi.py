"""Record what a spell's projectile does: put #33 at DIST m facing the opponent, press BUTTONS (like ppcombo.py), then
snapshot a RAM range (the magi object pool) + both fighters' positions every ~2 frames for SECONDS. One debugger
connection, no breakpoints. Output: pickle with [(t, sora_pos, opp_pos, sora_motion, opp_motion, bytes)].
  python3 -I ppmagi.py PORT DIST BUTTONS SECONDS START SIZE OUT.pkl    (BUTTONS e.g. fwd+square; env FY/FX/LEAD)
"""
import base64
import json
import os
import pickle
import struct
import sys
import time

import websocket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppplay import find_fighter  # noqa: E402


def main():
    port, dist, buttons, secs = sys.argv[1], float(sys.argv[2]), sys.argv[3], float(sys.argv[4])
    start, size, out = int(sys.argv[5], 0), int(sys.argv[6], 0), sys.argv[7]
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=90, suppress_origin=True)
    ws.settimeout(10)

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

    def motion(f):
        return struct.unpack('<H', read(f + 0x180, 2))[0]
    try:
        fs = find_fighter(ws, 33)
        fo = find_fighter(ws, 33, skip=fs)
        call('input.analog.send', stick='left', x=1, y=0)        # the player is the one that runs (ppcombo.py)
        time.sleep(0.4)
        mo = motion(fo)
        call('input.analog.send', stick='left', x=0, y=0)
        if mo == 2:
            fs, fo = fo, fs
        for k in range(60):
            if motion(fs) == 1 and motion(fo) == 1:
                break
            time.sleep(0.1)
        ox, oy, oz = struct.unpack('<3f', read(fo + 0x80, 12))
        sx, sy, sz = struct.unpack('<3f', read(fs + 0x80, 12))
        dx, dz = ox - sx, oz - sz
        n = max((dx * dx + dz * dz) ** 0.5, 1e-3)
        write(fs + 0x80, struct.pack('<3f', ox - dx / n * dist, oy, oz - dz / n * dist))
        write(fs + 0x90, struct.pack('<3f', dx / n, 0, dz / n))
        bs = [x for x in buttons.split('+') if x != 'fwd']
        if 'fwd' in buttons.split('+'):
            call('input.analog.send', stick='left', x=float(os.environ.get('FX', 0)), y=float(os.environ.get('FY', 1)))
            time.sleep(float(os.environ.get('LEAD', 8)) / 60)
        t0 = time.time()
        call('input.buttons.send', buttons={x: True for x in bs})
        time.sleep(10 / 60)
        call('input.buttons.send', buttons={x: False for x in bs})
        call('input.analog.send', stick='left', x=0, y=0)
        snaps = []
        while time.time() - t0 < secs:
            snaps.append((time.time() - t0, struct.unpack('<3f', read(fs + 0x80, 12)),
                          struct.unpack('<3f', read(fo + 0x80, 12)), motion(fs), motion(fo), read(start, size)))
        pickle.dump(snaps, open(out, 'wb'))
        print('%d snaps; Sora motions %s; opp motions %s' % (
            len(snaps), sorted(set(s[3] for s in snaps)), sorted(set(s[4] for s in snaps))))
    finally:
        ws.close()


if __name__ == '__main__':
    main()
