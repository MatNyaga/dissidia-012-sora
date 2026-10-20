"""Live-patch #33's magi (projectile) rows in PPSSPP RAM (every copy of Sora's MAGI chunk), for quick tests.
  python3 -I ppmagipatch.py PORT 'ROW:KIND:OFF=VAL,...' [...]
KIND: h = u16 field at byte OFF (e.g. 0x1e spawn mode, 0x22 direction mode), p = parameter byte index (row byte
0x40 + OFF) set to the float-table INDEX whose value is VAL (must already exist in the table).
Example: ppmagipatch.py 40057 '7c5:h:0x1e=3' '7c5:p:3=9.0,4=9.0,24=-89.9,25=-89.9'
"""
import base64
import json
import struct
import sys

import websocket


def main():
    port = sys.argv[1]
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=90, suppress_origin=True)
    ws.settimeout(15)

    def call(ev, **a):
        ws.send(json.dumps(dict(event=ev, **a)))
        while True:
            r = json.loads(ws.recv())
            if r.get('event') in (ev, 'error'):
                return r

    def rd(a, n):
        return base64.b64decode(call('memory.read', address=a, size=n).get('base64', ''))

    def wr(a, b):
        call('memory.write', address=a, base64=base64.b64encode(b).decode())
    hits = []
    for base in range(0x08800000, 0x0A000000, 0x100000):
        blk = rd(base, 0x100000 + 64)
        i = blk.find(b'MAGI')
        while i >= 0:
            cnt, = struct.unpack_from('<I', blk, i + 8)
            if 0 < cnt < 200:
                hits.append(base + i)
            i = blk.find(b'MAGI', i + 1)
    for h in sorted(set(hits)):
        hdr = rd(h, 16)
        cnt, = struct.unpack_from('<I', hdr, 8)
        rows = rd(h + 16, cnt * 204)
        ids = {struct.unpack_from('<h', rows, k * 204)[0] & 0xFFFF: h + 16 + k * 204 for k in range(cnt)}
        if 0x7C5 not in ids:
            continue
        nf, = struct.unpack_from('<I', hdr, 12)
        fl = struct.unpack('<%df' % nf, rd(h + 16 + cnt * 204, nf * 4))
        print('MAGI at %08x (%d rows, %d floats)' % (h, cnt, nf))
        for spec in sys.argv[2:]:
            row, kind, items = spec.split(':')
            at = ids[int(row, 16)]
            for it in items.split(','):
                off, val = it.split('=')
                off = int(off, 0)
                if kind == 'h':
                    wr(at + off, struct.pack('<H', int(val, 0)))
                else:
                    v = float(val)
                    idx = min(range(nf), key=lambda k: abs(fl[k] - v))
                    assert abs(fl[idx] - v) < 1e-3, 'value %s not in the float table' % val
                    wr(at + 0x40 + off, bytes([idx]))
            print('  %s patched' % spec)
    ws.close()


if __name__ == '__main__':
    main()
