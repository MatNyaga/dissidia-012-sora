"""Log every time the game runs code at ADDR (CPU breakpoint), with a0-a3 / ra, then resume. Own debugger connection,
so it can run next to ppcombo.py. Example: did a spell spawn a projectile? (magi spawn = 0x08AD0978, notes/hp-magic.md)
  python3 -I ppbpwatch.py PORT SECONDS ADDR [ADDR ...]
env DUMP=N: after each hit, dump the 0x130-byte object at v0 (break on the spawn's return address) N times, every
0.05 s, as floats (find where a projectile flies).
SIGTERM / timeout still removes the breakpoints (a breakpoint left behind freezes the game).
"""
import base64
import json
import os
import signal
import struct
import sys
import time

import websocket


def main():
    signal.signal(signal.SIGTERM, lambda *a: sys.exit('stopped'))
    port, secs = sys.argv[1], float(sys.argv[2])
    addrs = [int(a, 0) for a in sys.argv[3:]]
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=90, suppress_origin=True)

    def wait(ev):
        while True:
            r = json.loads(ws.recv())
            if r.get('event') in (ev, 'error'):
                return r
    for a in addrs:
        ws.send(json.dumps({'event': 'cpu.breakpoint.add', 'address': a, 'enabled': True}))
    t0 = time.time()
    ws.settimeout(0.2)
    try:
        while time.time() - t0 < secs:
            try:
                r = json.loads(ws.recv())
            except websocket.WebSocketTimeoutException:
                continue
            if r.get('event') != 'cpu.stepping':
                continue
            ws.settimeout(5)
            ws.send(json.dumps({'event': 'cpu.getAllRegs'}))
            g = wait('cpu.getAllRegs')
            reg = dict(zip(g['categories'][0]['registerNames'], g['categories'][0]['uintValues']))
            print('%6.2f pc %08x a0 %x a1 %x a2 %x a3 %x ra %08x v0 %x' % (time.time() - t0, reg.get('pc', 0), reg['a0'],
                  reg['a1'], reg['a2'], reg['a3'], reg['ra'], reg['v0']), flush=True)
            ws.send(json.dumps({'event': 'cpu.resume'}))
            for k in range(int(os.environ.get('DUMP', 0))):
                ws.send(json.dumps({'event': 'memory.read', 'address': reg['v0'], 'size': 0x130}))
                b = base64.b64decode(wait('memory.read').get('base64', ''))
                fl = struct.unpack('<76f', b)
                print('  %4.2f ' % (time.time() - t0) + ' '.join('%d:%.2f' % (i * 4, v) for i, v in enumerate(fl)
                                                              if v == v and 0.01 < abs(v) < 1000), flush=True)
                time.sleep(0.05)
            ws.settimeout(0.2)
    finally:
        ws.settimeout(5)
        for a in addrs:
            ws.send(json.dumps({'event': 'cpu.breakpoint.remove', 'address': a}))
        ws.send(json.dumps({'event': 'cpu.resume'}))
        time.sleep(0.5)
        ws.close()


if __name__ == '__main__':
    main()
