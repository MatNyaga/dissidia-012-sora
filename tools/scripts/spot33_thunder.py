"""Sora's spell projectiles (magi rows + spawns), run AFTER spot33_magic.py:
- Thundaga strikes STRAIGHT DOWN onto the foe (Mat 2026-10-15: "make Thundaga strike straight down on the foe").
- Blizzaga = ONE fast projectile (Mat: "A single projectile but a lot faster to compensate"): the side balls 0x7CB /
  0x7CD are no-ops (their one-shot op 0x04 spawns in the Blizzaga blocks get magi id -1, which the spawner skips —
  same trick as Magnet Burst's dropped shockwave), the centre ball 0x7CC flies BLIZZ_SPEED (p57/p58; Fire = 3.0).
Runs AFTER spot33_magic.py (which creates the magi rows 0x7C4-0x7CA as copies of Cloud's Meteorain). notes/hp-magic.md
"Thundaga straight down" explains the fields. Every value below is a constant so a live test can bisect them
(tools/scripts/ppmagipatch.py patches the same fields in RAM). Re-runnable: it only SETS fields.

magi row (204 B): +0x1e u16 spawn mode, +0x22 u16 direction mode; bytes +0x40.. = parameter p0..p139, each a u8 index
into the chunk's float table (header +0x0C = float count, floats follow the rows). Parameters are (min, max, change per
frame) triples. Values missing from the table are appended (the chunk grows by 4 bytes each; normally none needed).

Also: the Thundaga pieces 0x1011 / 0x1014 had Meteorain's 7 m MINIMUM distance (plya +0x24) — the only field that
differs from Firaga's working pieces; in test188 Thundaga would not come out at 7-13 m on neutral Square → 0.0.

  python3 -I spot33_thunder.py ISO [--dry]
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from spot33_combos import rebuild_arc  # noqa: E402

FILE = 'obj/p_sev120.objx'
SPAWN_AT_TARGET = 11            # 11 = target +0x80 (feet), 12 = target +0x100; 3/4/8/9 = clamped toward the target
DIRECTION = 0                   # 0 = default axis + pitch/yaw params (Cloud's air spawner 0x7BD points down this way)
HEIGHT = 9.0                    # spawn this high above the target (p3/p4 = offset y min/max)
SPREAD = 0.5                    # random x / z offset +-SPREAD around the target (p0/p1, p6/p7)
PITCH = -89.9                   # straight down (p24/p25)
SPEED = (30.0, 30.0, 9.0)       # p57/p58/p59 (Meteorain strike: 9, 9, 9)  -- guess: speed min / max / change
LIFE = 20.0                     # p129/p130/p132/p133 (Meteorain strike: 30) -- guess: lifetime / range
STRIKES = 3.0                   # spawners' p93/p94 (Meteorain: 2) -- guess: number of strikes per cast
STRIKE_ROWS = (0x7C5, 0x7CA)    # ground strikes / air strikes (air: 0x7C8 -> 0x7C9 -> 0x7CA)
SPAWNER_ROWS = (0x7C4, 0x7C9)
MIN_DIST = {0x1011: 0.0, 0x1014: 0.0}   # HP_THUNDAGA / HP_A_THUNDAGA plya +0x24
BLIZZ_BALL = 0x7CC              # the one projectile left (straight, like Fire's centre ball 0xD6; no homing params known)
BLIZZ_DROP = (0x7CB, 0x7CD)     # Fire's -25 / +25 degree side balls -> not spawned
BLIZZ_MOTIONS = (10312, 10315)  # ground / air Blizzaga blocks (spot33_magic SPELLS)
BLIZZ_SPEED = 9.0               # p57/p58 (Fire 3.0 -> 3x); BLIZZ_LIFE keeps the range: speed x life
BLIZZ_LIFE = 42.0               # p93/p94 + p129/p130 (Fire 42)


def chunks(d):
    n, = struct.unpack_from('<I', d, 4)
    return [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]


def main():
    iso = sys.argv[1]
    use_iso(iso)
    st, sz = pkg_offset(FILE)
    with open(iso, 'rb') as f:
        d = read_at(f, st, sz)
    ch = chunks(d)
    mi = next(k for k, c in enumerate(ch) if c[1] == b'magi')
    pi = next(k for k, c in enumerate(ch) if c[1] == b'plya')
    m = bytearray(d[ch[mi][2]:ch[mi][2] + ch[mi][3]])
    cnt, nf = struct.unpack_from('<II', m, 8)
    rows_end = 16 + cnt * 204
    floats = list(struct.unpack_from('<%df' % nf, m, rows_end))
    extra = bytes(m[rows_end + 4 * nf:])

    def fidx(v):
        for k, x in enumerate(floats):
            if abs(x - v) < 1e-4:
                return k
        floats.append(v)
        assert len(floats) <= 255, 'float table full'
        print('float %g appended (index %d)' % (v, len(floats) - 1))
        return len(floats) - 1
    at = {struct.unpack_from('<h', m, 16 + k * 204)[0] & 0xFFFF: 16 + k * 204 for k in range(cnt)}

    def setp(row, p, v):
        m[at[row] + 0x40 + p] = fidx(v)
    for r in STRIKE_ROWS:
        struct.pack_into('<H', m, at[r] + 0x1e, SPAWN_AT_TARGET)
        struct.pack_into('<H', m, at[r] + 0x22, DIRECTION)
        for p, v in ((0, -SPREAD), (1, SPREAD), (2, 0.0), (3, HEIGHT), (4, HEIGHT), (5, 0.0),
                     (6, -SPREAD), (7, SPREAD), (8, 0.0),
                     (24, PITCH), (25, PITCH), (26, 0.0), (27, 0.0), (28, 0.0), (29, 0.0),
                     (57, SPEED[0]), (58, SPEED[1]), (59, SPEED[2]),
                     (129, LIFE), (130, LIFE), (132, LIFE), (133, LIFE)):
            setp(r, p, v)
        print('magi %x: spawn mode %d (at the target, %.1f m up, +-%.1f), direction %d, pitch %.1f, speed %s, life %.0f'
              % (r, SPAWN_AT_TARGET, HEIGHT, SPREAD, DIRECTION, PITCH, SPEED, LIFE))
    for r in SPAWNER_ROWS:
        setp(r, 93, STRIKES)
        setp(r, 94, STRIKES)
        print('magi %x: strikes per cast %.0f' % (r, STRIKES))
    for p, v in ((57, BLIZZ_SPEED), (58, BLIZZ_SPEED), (93, BLIZZ_LIFE), (94, BLIZZ_LIFE),
                 (129, BLIZZ_LIFE), (130, BLIZZ_LIFE)):
        setp(BLIZZ_BALL, p, v)
    print('magi %x: Blizzaga ball speed %.1f, life %.0f' % (BLIZZ_BALL, BLIZZ_SPEED, BLIZZ_LIFE))
    m = m[:rows_end] + bytearray(struct.pack('<%df' % len(floats), *floats)) + extra
    struct.pack_into('<I', m, 12, len(floats))
    p = bytearray(d[ch[pi][2]:ch[pi][2] + ch[pi][3]])
    npl, = struct.unpack_from('<I', p, 4)
    for k in range(npl):
        o = 8 + k * 116
        pid, = struct.unpack_from('<H', p, o)
        if pid in MIN_DIST:
            struct.pack_into('<f', p, o + 0x24, MIN_DIST[pid])
            print('piece %x: min distance -> %.1f' % (pid, MIN_DIST[pid]))
    # Blizzaga: side-ball spawns -> magi id -1 (one-shot op 0x04 [magi id, 0])
    i7 = next(k for k, c in enumerate(ch) if c[0] == 7)
    i8 = next(k for k, c in enumerate(ch) if c[0] == 8)
    t7 = d[ch[i7][2]:ch[i7][2] + ch[i7][3]]
    m7, = struct.unpack_from('<I', t7, 4)
    rows7 = {struct.unpack_from('<H', t7, 8 + k * 8)[0]: struct.unpack_from('<H', t7, 10 + k * 8)[0] for k in range(m7)}
    c8 = bytearray(d[ch[i8][2]:ch[i8][2] + ch[i8][3]])
    nb, = struct.unpack_from('<I', c8, 4)
    offs = struct.unpack_from('<%dI' % nb, c8, 8)
    for mot in BLIZZ_MOTIONS:
        o = offs[rows7[mot]]
        e1, = struct.unpack_from('<H', c8, o + 4)
        k = o + e1
        for _ in range(c8[o + 3]):
            op, npar = c8[k + 2], c8[k + 3]
            if op == 0x04 and struct.unpack_from('<I', c8, k + 8)[0] in BLIZZ_DROP:
                print('motion %d: frame %d spawn of magi %x dropped' % (mot, struct.unpack_from('<H', c8, k)[0],
                                                                       struct.unpack_from('<I', c8, k + 8)[0]))
                struct.pack_into('<I', c8, k + 8, 0xFFFFFFFF)
            k += 8 + 4 * npar
    new = {mi: bytes(m), pi: bytes(p), i8: bytes(c8)}
    if all(new[k] == d[ch[k][2]:ch[k][2] + ch[k][3]] for k in new):
        print('spell projectiles already set')
        return
    if '--dry' in sys.argv:
        return
    out = rebuild_arc(d, new)
    with tempfile.TemporaryDirectory() as t:
        path = os.path.join(t, 'f.objx')
        open(path, 'wb').write(out)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, path],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main()
