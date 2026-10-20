"""Combo hit test: put fighter OWNER at DIST metres in front of the opponent, face it, press a button sequence, and
log both fighters' motion ids (opponent's 5xx/7xx = it got hit). Usage:
  python3 -I ppcombo.py PORT OWNER OPP DIST REPEATS BUTTONS   (BUTTONS e.g. circle,circle,circle  or  cross,circle  or  up+circle, fwd+circle = analog stick up + Circle, w0.5 = wait, u10060 = wait until Sora's motion is 10060, m10060 = mash Circle until then, s8 = 8 screenshots into SHOTDIR)
Positions: fighter +0x80 (x, y, z, 1), facing unit vector +0x90 (notes/adjustables.md).
"""
import base64
import json
import struct
import sys
import time

import websocket

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from ppplay import find_fighter  # noqa: E402


def main():
    port, owner, opp, dist, reps = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5])
    buttons = sys.argv[6].split(',')
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=90, suppress_origin=True)
    ws.settimeout(60)

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
    fs = find_fighter(ws, owner)
    fo = find_fighter(ws, opp, skip=fs if opp == owner else None)
    if opp == owner:                                         # mirror match (#33 vs CPU #33): the player is the one
        call('input.analog.send', stick='left', x=1, y=0)    # that starts running when the stick moves
        time.sleep(0.4)
        mo = struct.unpack('<H', base64.b64decode(call('memory.read', address=fo + 0x180, size=2)['base64']))[0]
        call('input.analog.send', stick='left', x=0, y=0)
        if mo == 2:
            fs, fo = fo, fs
        time.sleep(0.5)
    log, last, t0 = [], {}, time.time()

    def poll(sec):
        end = time.time() + sec
        while time.time() < end:
            for nm, f in (('S', fs), ('O', fo)):
                m = struct.unpack('<H', read(f + 0x180, 2))[0]
                if last.get(nm) != m:
                    extra = ''
                    if __import__('os').environ.get('POS'):          # POS=1: distance / height gap at each change
                        a, b = struct.unpack('<3f', read(fs + 0x80, 12)), struct.unpack('<3f', read(fo + 0x80, 12))
                        extra = '[d%.1f h%+.1f]' % (((a[0] - b[0]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5, b[1] - a[1])
                    log.append('%.2f %s%d%s' % (time.time() - t0, nm, m, extra))
                    last[nm] = m
            time.sleep(0.02)
    hits = 0
    def over():
        return any(struct.unpack('<H', read(f + 0x180, 2))[0] in (1200, 1210, 0xFFFF) for f in (fs, fo))
    for r in range(reps):
        if over():                                           # battle ended: never press on the results screen
            log.append('-- battle over, stopped')            # (Square there = Save Replay dialog)
            break
        for k in range(60):                                  # wait until both stand idle
            if struct.unpack('<H', read(fs + 0x180, 2))[0] == 1 and struct.unpack('<H', read(fo + 0x180, 2))[0] == 1:
                break
            time.sleep(0.1)
        ox, oy, oz = struct.unpack('<3f', read(fo + 0x80, 12))
        sx, sy, sz = struct.unpack('<3f', read(fs + 0x80, 12))
        dx, dz = ox - sx, oz - sz
        n = max((dx * dx + dz * dz) ** 0.5, 1e-3)
        nx, nz = sx if False else ox - dx / n * dist, oz - dz / n * dist
        env = __import__('os').environ
        write(fs + 0x80, struct.pack('<3f', nx, oy + float(env.get('SY', 0)), nz))   # SY / OY: height offsets (m)
        if env.get('OY'):
            write(fo + 0x80, struct.pack('<3f', ox, oy + float(env['OY']), oz))
        write(fs + 0x90, struct.pack('<3f', dx / n, 0, dz / n))
        log.append('-- try %d' % r)
        before = len(log)
        for b in buttons:
            if over():
                break
            if b.startswith('w'):                               # w0.5 = wait 0.5 s before the next press
                poll(float(b[1:]))
                continue
            if b.startswith('s') and b[1:].isdigit():          # s8 = 8 screenshots (every ~0.1 s) into env SHOTDIR
                os = __import__('os')
                for n in range(int(b[1:])):
                    call('cpu.stepping')
                    r = call('gpu.buffer.screenshot', type='base64')
                    call('cpu.resume')
                    data = r.get('base64') or r.get('uri', ',').split(',', 1)[1]
                    open(os.path.join(os.environ.get('SHOTDIR', '.'), 'shot_%.2f.png' % (time.time() - t0)),
                         'wb').write(base64.b64decode(data))
                    poll(0.1)
                continue
            if b.startswith('m'):                               # m10060 = mash Circle until Sora plays motion 10060
                end = time.time() + 8
                while time.time() < end and struct.unpack('<H', read(fs + 0x180, 2))[0] != int(b[1:]):
                    call('input.buttons.send', buttons={'circle': True})
                    poll(10 / 60)
                    call('input.buttons.send', buttons={'circle': False})
                    poll(float(__import__("os").environ.get("GAP", 0.3)))
                continue
            if b.startswith('u'):                               # u10060 = wait (max 4 s) until Sora plays motion 10060
                end = time.time() + 4
                while time.time() < end and struct.unpack('<H', read(fs + 0x180, 2))[0] != int(b[1:]):
                    poll(0.03)
                continue
            bs = [x for x in b.split('+') if x != 'fwd']                         # up+circle = together
            if 'fwd' in b.split('+'):                                            # fwd = left analog stick up
                call('input.analog.send', stick='left', x=float(__import__('os').environ.get('FX', 0)), y=float(__import__('os').environ.get('FY', -1)))
                poll(float(__import__('os').environ.get('LEAD', 4)) / 60)    # env LEAD = frames held before
            call('input.buttons.send', buttons={x: True for x in bs})
            poll(10 / 60)
            call('input.buttons.send', buttons={x: False for x in bs})
            call('input.analog.send', stick='left', x=0, y=0)
            poll(float(__import__("os").environ.get("GAP", 0.3)))
        poll(1.5)
        got = [x for x in log[before:] if ' O5' in x or ' O7' in x]
        hits += bool(got)
    print(' '.join(log))
    print('tries with the opponent hit:', hits, '/', reps)
    ws.close()                                               # leave the debugger free for the next tool


if __name__ == '__main__':
    main()
