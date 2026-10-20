"""Runtime check for spot33_exspeed.py: hold the stick, measure Sora's ground run speed (PPSSPP remote debugger, one
connection). Run it 3 times on the same stage spot: normal, EX Mode, normal again (enter EX with R+Square between).

  python3 -I ppexspeed.py PORT LABEL [SECONDS=4] [STICK=1,0]   -> one line + CSV rows appended to dumps/exspeed_runs.csv

Reads (owner 33 fighter): position +0x80 (x,y,z), frame counter +0x324, motion u16 +0x180, run scalar +0xbc,
move-speed factor +0x3d4, EX flag (+0x5b2 & 4), spec pointer +0x39c. Speed = horizontal distance / frame delta over
the part of the run where motion == 2 (first 0.5 s skipped = acceleration). Expected with EXSPEED_MULT 1.10:
EX run ~1.10 x normal, normal-after == normal-before, +0xbc in EX ~1.10 x +0xbc normal, +0x3d4 unchanged.
Releases the stick at the end. No writes to game memory.
"""
import csv
import math
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppplay import call, find_fighter, read  # noqa: E402
import websocket  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../dumps/exspeed_runs.csv')


def sample(ws, f):
    b = read(ws, f, 0x5c0)
    x, y, z = struct.unpack_from('<3f', b, 0x80)
    return dict(frame=struct.unpack_from('<I', b, 0x324)[0], x=x, y=y, z=z,
                motion=struct.unpack_from('<H', b, 0x180)[0], bc=struct.unpack_from('<f', b, 0xbc)[0],
                f3d4=struct.unpack_from('<f', b, 0x3d4)[0], ex=int(b[0x5b2] & 4 != 0),
                spec=struct.unpack_from('<I', b, 0x39c)[0], t=time.time())


def main():
    port, label = sys.argv[1], sys.argv[2]
    secs = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0
    sx, sy = map(float, (sys.argv[4] if len(sys.argv) > 4 else '1,0').split(','))
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=90, suppress_origin=True)
    f = find_fighter(ws, 33)
    if not f:
        sys.exit('owner-33 fighter not found (in battle?)')
    rows = []
    call(ws, 'input.analog.send', stick='left', x=sx, y=sy)
    t0 = time.time()
    try:
        while time.time() - t0 < secs:
            rows.append(sample(ws, f))
            time.sleep(0.01)
    finally:
        call(ws, 'input.analog.send', stick='left', x=0, y=0)
        ws.close()
    run = [r for r in rows if r['t'] - t0 >= 0.5 and r['motion'] == 2]
    if len(run) < 2 or run[-1]['frame'] == run[0]['frame']:
        sys.exit('not enough motion-2 samples (%d); motions seen %s' % (len(run), sorted({r['motion'] for r in rows})))
    a, b = run[0], run[-1]
    dist = math.hypot(b['x'] - a['x'], b['z'] - a['z'])
    frames = (b['frame'] - a['frame']) & 0xFFFFFFFF
    bcs = sorted(r['bc'] for r in run)
    wall = (b['t'] - a['t']) * 60.0                    # fallback if +0x324 is not a plain frame counter
    print('%s: ex=%s  %.5f units/frame over %d frames (%.5f per 1/60 s wall clock, %d samples)  bc median %.5f  '
          '3d4 %.4f  dy %.4f  motions %s' % (
        label, sorted({r['ex'] for r in run}), dist / frames, frames, dist / wall, len(run), bcs[len(bcs) // 2],
        run[0]['f3d4'], b['y'] - a['y'], sorted({r['motion'] for r in rows})))
    new = not os.path.exists(OUT)
    with open(OUT, 'a', newline='') as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(['label', 'frame', 'x', 'y', 'z', 'motion', 'bc', 'f3d4', 'ex', 'spec'])
        for r in rows:
            w.writerow([label, r['frame'], r['x'], r['y'], r['z'], r['motion'], r['bc'], r['f3d4'], r['ex'],
                        '%08x' % r['spec']])


if __name__ == '__main__':
    main()
