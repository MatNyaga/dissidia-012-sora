"""Log which animation (motion id, e.g. 1 = idle) each fighter plays, live, while someone plays.
Finds fighters by their vtable (0x08B3A9A8 at +0x544), reads owner (objentry+6) and motion id (+0x180).
Usage: python3 -I ppanimlog.py PORT SECONDS [OWNER]      (prints a line whenever the id changes)
"""
import base64
import json
import struct
import sys
import time

import websocket

VT = 0x08B3A9A8


def call(ws, event, **args):
    ws.send(json.dumps(dict(event=event, **args)))
    while True:
        r = json.loads(ws.recv())
        if r.get('event') in (event, 'error'):
            return r


def read(ws, addr, size):
    r = call(ws, 'memory.read', address=addr, size=size)
    return base64.b64decode(r.get('base64', ''))


def find_fighters(ws):
    out = []
    pat = struct.pack('<I', VT)
    for base in range(0x08800000, 0x0A000000, 0x100000):
        blk = read(ws, base, 0x100000)
        i = blk.find(pat)
        while i >= 0:
            if i % 4 == 0:
                f = base + i - 0x544
                obj = struct.unpack('<I', read(ws, f + 0x2F8, 4))[0]
                if 0x08800000 <= obj < 0x0A000000:
                    out.append((f, read(ws, obj + 6, 1)[0]))
            i = blk.find(pat, i + 1)
    return out


def main():
    port, secs = sys.argv[1], float(sys.argv[2])
    want = int(sys.argv[3]) if len(sys.argv) > 3 else None
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=90, suppress_origin=True)
    fighters = find_fighters(ws)
    print('fighters:', [(hex(f), o) for f, o in fighters], flush=True)
    if want is not None:
        fighters = [x for x in fighters if x[1] == want]
    last = {}
    t0 = time.time()
    while time.time() - t0 < secs:
        for f, o in fighters:
            mid = struct.unpack('<H', read(ws, f + 0x180, 2))[0]
            if last.get(f) != mid:
                print('%6.2fs owner %d motion %d' % (time.time() - t0, o, mid), flush=True)
                last[f] = mid
        time.sleep(0.03)


if __name__ == '__main__':
    main()
