"""Which sound slot plays for which action: press a scripted input sequence and log every sound played (CPU breakpoint
in the sound play code 0x08991A70, s0 = bank entry; see ppsoundwatch.py), with the step label it happened in.

  [EXFILL=1] python3 -I ppsoundseq.py PORT STEP [STEP ...]
  STEP = buttons:seconds (hold) e.g. rtrigger:1.0  rtrigger+square:0.3  wait:2
EXFILL=1 fills #33's EX gauge first (float at *(fighter+0x52C)+0x18).
"""
import base64
import json
import os
import struct
import sys
import time

import websocket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppplay import find_fighter  # noqa: E402

PC = 0x08991A70


def main():
    port, steps = sys.argv[1], sys.argv[2:]
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=10, suppress_origin=True)

    def call(ev, **a):
        ws.send(json.dumps(dict(event=ev, **a)))
        while True:
            r = json.loads(ws.recv())
            if r.get('event') in (ev, 'error'):
                return r

    def read(a, n):
        return base64.b64decode(call('memory.read', address=a, size=n).get('base64', ''))
    banks = []
    for base in range(0x08800000, 0x0A000000, 0x100000):
        blk = read(base, 0x100000 + 16)
        i = blk.find(b'SSCF')
        while i >= 0:
            # bank id = u16 +0x12, or u32 +0x14 when +0x12 is 0 (012 newcomers, #33 after spot33_soundids.py)
            banks.append((base + i, struct.unpack_from('<I', blk, i + 8)[0],
                          struct.unpack_from('<H', blk, i + 0x12)[0] or struct.unpack_from('<I', blk, i + 0x14)[0]))
            i = blk.find(b'SSCF', i + 1)
    print('banks:', ', '.join('%x(size %d, id %d)' % b for b in banks), flush=True)
    if os.environ.get('EXFILL'):
        fs = find_fighter(ws, 33)
        ex = struct.unpack('<I', read(fs + 0x52C, 4))[0] + 0x18
        call('memory.write', address=ex, base64=base64.b64encode(struct.pack('<f', 10000.0)).decode())
    ws.send(json.dumps({'event': 'cpu.breakpoint.add', 'address': PC, 'enabled': True}))   # no wait (a stepping event can come first)
    ws.settimeout(0.05)
    t0 = time.time()
    try:
        for st in steps:
            btns, secs = st.rsplit(':', 1)
            press = [] if btns == 'wait' else btns.split('+')
            if press:
                ws.send(json.dumps({'event': 'input.buttons.send', 'buttons': {b: True for b in press}}))
            end = time.time() + float(secs)
            released = not press
            while time.time() < end or not released:
                if not released and time.time() >= end:
                    ws.send(json.dumps({'event': 'input.buttons.send', 'buttons': {b: False for b in press}}))
                    released = True
                    end = time.time() + 0.3
                try:
                    r = json.loads(ws.recv())
                except websocket.WebSocketTimeoutException:
                    continue
                if r.get('event') != 'cpu.stepping':
                    continue
                ws.settimeout(5)
                ws.send(json.dumps({'event': 'cpu.getAllRegs'}))
                while True:
                    g = json.loads(ws.recv())
                    if g.get('event') == 'cpu.getAllRegs':
                        break
                reg = dict(zip(g['categories'][0]['registerNames'], g['categories'][0]['uintValues']))
                s0 = reg['s0']
                where = '?'
                for a, size, bid in banks:
                    if a <= s0 < a + size:
                        where = 'bank id %d slot %d' % (bid, (s0 - a - 0x20) // 32)
                print('%6.2f [%s] %s' % (time.time() - t0, st, where), flush=True)
                ws.send(json.dumps({'event': 'cpu.resume'}))
                ws.settimeout(0.05)
    finally:
        ws.settimeout(5)
        ws.send(json.dumps({'event': 'cpu.breakpoint.remove', 'address': PC}))
        ws.send(json.dumps({'event': 'cpu.resume'}))
        time.sleep(0.5)


if __name__ == '__main__':
    main()
