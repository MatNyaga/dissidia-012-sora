"""Move a motion onto another frame range: key times are remapped linearly from the motion's current range [a, b] to
[START, END] and the range arg (0x80B1) is rewritten. Use it when the game addresses a clip by ABSOLUTE frame
numbers of Cloud's original (e.g. Cloud's _400A / _410A run 45-73; ours came out 2-8 / 7-13, and the EX FINAL BLOW
scene then showed the victim in the rest pose = "Sora just stands there", Mat test211/test220).

  python3 -I gmo_retime.py IN.gmo OUT.gmo MOTION=START-END [...]          (re-running with the same range = no change)

Motion block: args 0x80B1 frame range (2 floats) …; fcurve blocks (type 0x0C): header, u32 format, u32 dims,
u32 key count, u32 0, keys = (half frame, dims x half) — format 0x80/0x81/0x84 all store a half-float frame per key.
"""
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gmo_motion import blocks, motions  # noqa: E402


def half(x):
    return np.array([x], dtype=np.float16).tobytes()


def unhalf(b):
    return float(np.frombuffer(b, dtype=np.float16)[0])


def retime(d, o, s, start, end):
    d = bytearray(d)
    _, hs, _ = struct.unpack_from('<HHI', d, o)
    rng = None
    for bo, t, bh, bs in blocks(d, o + hs, o + s):          # args are small blocks before the fcurves
        if t == 0x80B1:
            rng = bo + 8                                    # arg block: u16 type, u16 0, u32 16, 2 floats
    assert rng is not None, 'no frame range arg'
    a, b = struct.unpack_from('<2f', d, rng)
    if (a, b) == (float(start), float(end)):
        return bytes(d), (a, b), 0
    scale = (end - start) / (b - a) if b > a else 1.0
    n = 0
    for bo, t, bh, bs in blocks(d, o + hs, o + s):
        if t != 0x0C:
            continue
        fmt, dims, nk, _ = struct.unpack_from('<IIII', d, bo + bh)
        ksz = 2 * (1 + dims)
        for k in range(nk):
            p = bo + bh + 16 + k * ksz
            f = unhalf(bytes(d[p:p + 2]))
            d[p:p + 2] = half(start + (f - a) * scale)
            n += 1
    struct.pack_into('<2f', d, rng, float(start), float(end))
    return bytes(d), (a, b), n


def main():
    src, dst, specs = sys.argv[1], sys.argv[2], sys.argv[3:]
    d = open(src, 'rb').read()
    for spec in specs:
        name, r = spec.split('=')
        start, end = (int(x) for x in r.split('-'))
        o, s = next((o, s) for n, o, s in motions(d)[0] if n == name)
        d, old, n = retime(d, o, s, start, end)
        print('%s: frames %g-%g -> %d-%d (%d keys)' % (name, old[0], old[1], start, end, n) if n else
              '%s: already %d-%d' % (name, start, end))
    open(dst, 'wb').write(d)


if __name__ == '__main__':
    main()
