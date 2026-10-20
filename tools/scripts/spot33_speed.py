"""Make the later hits of #33's long combo come out faster (Mat: "easy to break out after the fourth hit").
Shifts every event of a move's script block (p_se type 8) earlier by DELTA script frames (60/s): hitboxes (op 0x00),
cancel window (op 0x22), end (op 0x28), effects/sounds — so the whole move plays sooner. In place (same sizes).
The animation slots are retimed to the new hit frames in build_sora.sh (AIR list).

  python3 -I spot33_speed.py ISO
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402

FILE = 'obj/p_sev120.objx'
# motion id → frames earlier: every combo hit starts at script frame 10 (KH2 pace; Mat: CPU escapes on lowest level)
SHIFT = {10000: 6, 10001: 6, 10050: 10, 10002: 20, 10224: 16, 10021: 18, 10022: 16, 10061: 6,
         10020: 10}       # AIR_NEAR1 (air opener): hits 18/34, next piece only from 42 → AN2 came 0.9 s late (test 130)
# continue window (op 0x01) moved without moving the hit: launcher LAND_MIDDLE2 window 32-62 → 18-48
# Slide Dash 10010 (hits 24-38 + 36-42, window was 42-72): 0.6 s gap before the next hit → CPU escaped (Mat) →
# open it during the 2nd hit
OP01 = {10011: (16, 46), 10010: (34, 72),
        10020: (28, 62)}                 # air opener: AN2 may start during its 2nd hit (test 131: AN2 often too late)


def main():
    iso = sys.argv[1]
    use_iso(iso)
    st, sz = pkg_offset(FILE)
    with open(iso, 'r+b') as f:
        d = bytearray(read_at(f, st, sz))
        n, = struct.unpack_from('<I', d, 4)
        ch = [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]
        t7 = next(c for c in ch if c[0] == 7)
        t8 = next(c for c in ch if c[0] == 8)
        m7, = struct.unpack_from('<I', d, t7[2] + 4)
        rows = {struct.unpack_from('<H', d, t7[2] + 8 + k * 8)[0]: struct.unpack_from('<H', d, t7[2] + 10 + k * 8)[0]
                for k in range(m7)}
        m8, = struct.unpack_from('<I', d, t8[2] + 4)
        offs = struct.unpack_from('<%dI' % m8, d, t8[2] + 8)
        done = set()
        for mid, delta in SHIFT.items():
            blk = rows[mid]
            if blk in done:
                continue
            done.add(blk)
            o = t8[2] + offs[blk]
            ev = d[o + 2]
            k = o + 8
            moved = 0
            for _ in range(ev):
                fr, to = struct.unpack_from('<HH', d, k)
                npar = d[k + 5]
                if fr > 0:
                    nfr = max(0, fr - delta)
                    nto = to if to == 0xFFFF else max(nfr, to - delta)
                    struct.pack_into('<HH', d, k, nfr, nto)
                    moved += 1
                k += 12 + 4 * npar
            print('motion %d (block %d): %d events %d frames earlier' % (mid, blk, moved, delta))
        for mid, (fr, to) in OP01.items():
            blk = rows[mid]
            o = t8[2] + offs[blk]
            k = o + 8
            for _ in range(d[o + 2]):
                if d[k + 4] == 1:
                    struct.pack_into('<HH', d, k, fr, to)
                    print('motion %d (block %d): continue window -> %d-%d' % (mid, blk, fr, to))
                k += 12 + 4 * d[k + 5]
        f.seek(st)
        f.write(d)


if __name__ == '__main__':
    main()
