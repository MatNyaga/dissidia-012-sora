"""Thin animation keys to save model memory: in the named motions keep every STEP-th key (plus the last) of the
interpolated fcurves (0x81 linear vec3, 0x84 quaternion); 0x80 step curves stay as they are.

Why (2026-10-15, test215): Codex's EX Burst motions grew P_SEV120_1P.gmo 2,506,640 → 2,523,344 B and the game crashed
at battle start (Invalid Memory Access PC 0885c8a0 in FUN_0885c6cc = model heap budget, like keychain v1).
Default target: _719A, the win-CAMERA hook (copy of _910A; the game only takes the results camera from motion 86).

  python3 -I gmo_thin.py IN.gmo OUT.gmo MOTION[:STEP] [...]      (STEP default 2; re-running thins again)

fcurve block (type 0x0C): header (hs bytes incl. name), u32 format, u32 dims, u32 key count, u32 0, keys =
(half frame, dims x half), block padded to 4 bytes.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gmo_motion import blocks, motions  # noqa: E402


def thin_motion(d, o, s, step):
    _, hs, _ = struct.unpack_from('<HHI', d, o)
    out = bytearray(d[o:o + hs])
    before = after = 0
    for bo, t, bh, bs in blocks(d, o + hs, o + s):
        blk = d[bo:bo + bs]
        if t == 0x0C:
            fmt, dims, nk, z = struct.unpack_from('<IIII', blk, bh)
            if fmt in (0x81, 0x84) and nk > 2:
                ksz = 2 * (1 + dims)
                keys = [blk[bh + 16 + k * ksz:bh + 16 + (k + 1) * ksz] for k in range(nk)]
                keep = keys[::step]
                if (nk - 1) % step:
                    keep.append(keys[-1])
                body = bytearray(blk[:bh]) + struct.pack('<IIII', fmt, dims, len(keep), z) + b''.join(keep)
                while len(body) % 4:
                    body.append(0)
                struct.pack_into('<I', body, 4, len(body))
                before, after = before + nk, after + len(keep)
                blk = bytes(body)
        out += blk
    struct.pack_into('<I', out, 4, len(out))
    return bytes(out), before, after


def main():
    src, dst, specs = sys.argv[1], sys.argv[2], sys.argv[3:]
    d = open(src, 'rb').read()
    for spec in specs:
        name, _, st = spec.partition(':')
        step = int(st or 2)
        mots, fo, mo = motions(d)
        o, s = next((o, s) for n, o, s in mots if n == name)
        new, kb, ka = thin_motion(d, o, s, step)
        delta = len(new) - s
        d = bytearray(d[:o] + new + d[o + s:])
        for b in (fo, mo):
            struct.pack_into('<I', d, b + 4, struct.unpack_from('<I', d, b + 4)[0] + delta)
        d = bytes(d)
        print('%s: keys %d -> %d, %+d bytes' % (name, kb, ka, delta))
    open(dst, 'wb').write(d)
    print('wrote', dst, len(d), 'bytes')


if __name__ == '__main__':
    main()
