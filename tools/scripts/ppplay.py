"""Play a fixed input sequence in PPSSPP (remote debugger) and log the fighter's animation ids at the same time
(one debugger connection — PPSSPP serves only one at a time).
Usage: python3 -I ppplay.py PORT OWNER STEP [STEP ...]     (OWNER = fighter to log, e.g. 33; 0 = no log)
STEP = buttons:frames  e.g.  cross:6  rtrigger+cross:8  wait:30  stick=0,-1:60 (run up)   (60 frames = 1 s)
Buttons: cross circle square triangle up down left right start select ltrigger rtrigger
Prints "time step" lines and "time motion ID" whenever the logged fighter's motion id changes.
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
    return base64.b64decode(call(ws, 'memory.read', address=addr, size=size).get('base64', ''))


def find_fighter(ws, owner, skip=None):
    pat = struct.pack('<I', VT)
    for base in range(0x08800000, 0x0A000000, 0x100000):
        blk = read(ws, base, 0x100000)
        i = blk.find(pat)
        while i >= 0:
            if i % 4 == 0:
                f = base + i - 0x544
                obj = struct.unpack('<I', read(ws, f + 0x2F8, 4))[0]
                if 0x08800000 <= obj < 0x0A000000 and read(ws, obj + 6, 1)[0] == owner and f != skip:
                    return f
            i = blk.find(pat, i + 1)
    return None


def main():
    port, owner = sys.argv[1], int(sys.argv[2])
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=90, suppress_origin=True)
    fighter = find_fighter(ws, owner) if owner else None
    t0 = time.time()
    last = [None]

    def poll_for(secs):
        end = time.time() + secs
        while True:
            if fighter:
                mid = struct.unpack('<H', read(ws, fighter + 0x180, 2))[0]
                if mid != last[0]:
                    print('%6.2f motion %d' % (time.time() - t0, mid), flush=True)
                    last[0] = mid
            if time.time() >= end:
                break
            time.sleep(0.02)

    for step in sys.argv[3:]:
        names, frames = step.rsplit(':', 1)
        secs = int(frames) / 60.0
        print('%6.2f %s' % (time.time() - t0, step), flush=True)
        if names.startswith('stick='):                      # stick=X,Y  (left analog, -1..1; Y -1 = up)
            x, y = map(float, names[6:].split(','))
            call(ws, 'input.analog.send', stick='left', x=x, y=y)
            poll_for(secs)
            call(ws, 'input.analog.send', stick='left', x=0, y=0)
        elif names != 'wait':
            btns = names.split('+')
            call(ws, 'input.buttons.send', buttons={b: True for b in btns})
            poll_for(secs)
            call(ws, 'input.buttons.send', buttons={b: False for b in btns})
        else:
            poll_for(secs)
    ws.close()


if __name__ == '__main__':
    main()
