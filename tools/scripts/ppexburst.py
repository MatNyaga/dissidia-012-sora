"""Trigger an EX Burst for fighter OWNER: fill EX gauge, R+Square (EX Mode), teleport next to the opponent, HP attack,
then mash Circle while logging both fighters' motion ids. Usage: [TRIES=n] [SHOTS=dir] [MASH=frames] python3 -I ppexburst.py PORT OWNER OPP SECONDS"""
import base64
import json
import os
import subprocess
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
    mash = int(os.environ.get('MASH', 4))
    shots, win = os.environ.get('SHOTS'), None
    if shots:
        os.makedirs(shots, exist_ok=True)
        tree = subprocess.run(['xwininfo', '-root', '-tree'], capture_output=True, text=True).stdout
        win = next(ln.split()[0] for ln in tree.splitlines() if 'duodecim' in ln.lower())
    over = []                                                    # battle ended: win/loss pose -> stop pressing

    def ended():
        return over or any(struct.unpack('<H', read(f + 0x180, 2))[0] in (1200, 1210) for f in (fs, fo))

    def poll(sec):
        end = time.time() + sec
        while time.time() < end:
            for nm, f in (('S', fs), ('O', fo)):
                m = struct.unpack('<H', read(f + 0x180, 2))[0]
                if last.get(nm) != m:
                    log.append('%.2f %s%d' % (time.time() - t0, nm, m))
                    last[nm] = m
                    if shots and nm == 'S':                      # SHOTS=dir: picture of the game window per motion
                        name = '%s/%05.2f_S%d' % (shots, time.time() - t0, m)
                        subprocess.Popen(['import', '-window', win, '-resize', '50%', name + '.png'])
                        subprocess.Popen(['sh', '-c', 'sleep 0.5; import -window %s -resize 50%% %s_b.png'
                                          % (win, name)])            # banners appear a moment later
                if m in (1200, 1210):
                    over.append(1)
            time.sleep(0.02)

    def press(btns, fr=12):
        if ended():
            return
        call('input.buttons.send', buttons={b: True for b in btns})
        poll(fr / 60)
        call('input.buttons.send', buttons={b: False for b in btns})
    for attempt in range(int(os.environ.get('TRIES', 1))):
        for k in range(600):                  # wait (max 60 s) until the battle runs (idle preferred, any fight motion ok
            m = struct.unpack('<H', read(fs + 0x180, 2))[0]   # after 3 s: the CPU may keep #33 busy getting hit)
            if m == 1 or (k > 30 and m not in (0xFFFF, 1100, 1110, 1200, 1210)):
                break
            time.sleep(0.1)
        else:
            print('not in battle (no idle motion) - nothing pressed')
            return
        ex = struct.unpack('<I', read(fs + 0x52C, 4))[0] + 0x18
        print('EX gauge before', struct.unpack('<f', read(ex, 4))[0])
        write(ex, struct.pack('<f', 10000.0))
        poll(1.0)
        print('EX gauge after write', struct.unpack('<f', read(ex, 4))[0])
        press(['rtrigger', 'square'], 24)
        if shots:                                                # EX Mode banner
            subprocess.Popen(['sh', '-c', 'sleep 0.3; import -window %s -resize 50%% %s/%05.2f_exmode.png'
                              % (win, shots, time.time() - t0)])
        poll(3.0)
        print('EX gauge after R+Square (drains in EX Mode)', struct.unpack('<f', read(ex, 4))[0])
        ox, oy, oz = struct.unpack('<3f', read(fo + 0x80, 12))
        sx, sy, sz = struct.unpack('<3f', read(fs + 0x80, 12))
        dx, dz = ox - sx, oz - sz
        n = max((dx * dx + dz * dz) ** 0.5, 1e-3)
        write(fs + 0x80, struct.pack('<3f', ox - dx / n * 1.5, oy, oz - dz / n * 1.5))
        write(fs + 0x90, struct.pack('<3f', dx / n, 0, dz / n))
        poll(0.1)
        press(['square'])
        for k in range(10):                                      # EX Burst prompt: R+Square while the HP attack hits
            poll(0.15)
            press(['rtrigger', 'square'], 8)
        end = time.time() + secs
        while time.time() < end and not ended():
            press(['circle'], mash)                      # MASH=frames per tap (fewer = faster tapping)
            poll(mash / 120)
        if any(' S8' in x for x in log) or ended():
            break
    print(' '.join(log))
    if over:
        print('battle ended (win/loss pose) - stopped pressing buttons')


if __name__ == '__main__':
    main()
