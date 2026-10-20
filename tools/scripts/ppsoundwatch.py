"""Which sound plays from which SSCF bank, live: CPU breakpoint in the sound play code (0x08991A70,
"lw a0,0x8(s0)", s0 = the bank entry being played), while pressing inputs — all on ONE debugger connection.
Usage: python3 -I ppsoundwatch.py PORT SECONDS [INPUT_EVERY_S] [BUTTON]   (default: circle every 1.5 s; BUTTON none = press nothing)
Banks are found by scanning RAM for "SSCF"; each hit prints bank address/size and slot number.
env OWNER=33: also print that fighter's motion id (e.g. 500 hit, 56x air hit, 70x blown away) with each sound.
"""
import base64
import json
import signal
import os
import struct
import sys
import time

import websocket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PC = 0x08991A70


def main():
    # a kill (e.g. `timeout`) must still run the finally below: a breakpoint left behind freezes the game on every
    # sound (2026-10-14: test 116 "crashed at the main menu")
    signal.signal(signal.SIGTERM, lambda *a: sys.exit('stopped'))
    port, secs = sys.argv[1], float(sys.argv[2])
    every = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
    button = sys.argv[4] if len(sys.argv) > 4 else 'circle'
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=1, suppress_origin=True)

    def wait(ev):
        while True:
            r = json.loads(ws.recv())
            if r.get('event') in (ev, 'error'):
                return r

    def read(a, n):
        ws.send(json.dumps({'event': 'memory.read', 'address': a, 'size': n}))
        return base64.b64decode(wait('memory.read').get('base64', ''))
    ws.settimeout(10)
    banks = []
    for base in range(0x08800000, 0x0A000000, 0x100000):
        blk = read(base, 0x100000 + 16)
        i = blk.find(b'SSCF')
        while i >= 0:
            banks.append((base + i, struct.unpack_from('<I', blk, i + 8)[0]))
            i = blk.find(b'SSCF', i + 1)
    fighter = None
    if os.environ.get('OWNER'):
        from ppplay import find_fighter
        fighter = find_fighter(ws, int(os.environ['OWNER']))
    print('banks:', ', '.join('%x(%d)' % b for b in banks), flush=True)
    ws.settimeout(0.2)
    ws.send(json.dumps({'event': 'cpu.breakpoint.add', 'address': PC, 'enabled': True}))
    t0 = time.time()
    next_press = t0 + 0.5
    try:
        while time.time() - t0 < secs:
            if button != 'none' and time.time() >= next_press:     # BUTTON none = only listen (Mat plays)
                if '+' in button:                           # chord, e.g. rtrigger+triangle
                    ws.send(json.dumps({'event': 'input.buttons.send', 'buttons': {b: True for b in button.split('+')}}))
                    time.sleep(0.2)
                    ws.send(json.dumps({'event': 'input.buttons.send', 'buttons': {b: False for b in button.split('+')}}))
                else:
                    ws.send(json.dumps({'event': 'input.buttons.press', 'button': button, 'duration': 12}))
                next_press += every
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
            s0 = reg['s0']
            where = '?'
            for a, size in banks:
                if a <= s0 < a + size:
                    where = 'bank %x(%d) slot %d' % (a, size, (s0 - a - 0x20) // 32)
            if fighter:
                where += '  motion %d' % struct.unpack('<H', read(fighter + 0x180, 2))[0]
            print('%6.2f %s' % (time.time() - t0, where), flush=True)
            ws.send(json.dumps({'event': 'cpu.resume'}))
            ws.settimeout(0.2)
    finally:
        ws.settimeout(5)
        ws.send(json.dumps({'event': 'cpu.breakpoint.remove', 'address': PC}))
        ws.send(json.dumps({'event': 'cpu.resume'}))
        time.sleep(0.5)


if __name__ == '__main__':
    main()
