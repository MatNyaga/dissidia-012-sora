"""Thundaga v2 = KH2 bolts that come DOWN onto a SPOT, with a warning and a dodge window (notes/thunder.md).

v1 (test287, Mat-verified: bolts drop on the foe, no freeze) placed the bolts 9 m above the foe the moment they were
emitted and they fell ~1 m per frame -> ~9 frames after the cast frame = a guaranteed hit. Mat (test294): "I beat the
CPU by spamming thunder". v2 = Garland's own Thundaga structure (p_one200 0x803 -> 0x83c / 0x804 -> 0x86f -> 0x802):
a MARKER is put on the foe's spot (type 11) with a warning effect, it waits, and only then the strike starts from
that LOCKED spot. A dodge / dash during the warning escapes; getting hit cancels the spell (flag 0x40000).

Rows (owner 33, obj/p_sev120.objx magi chunk; ids from spot33_magic):
  0x7C4  GROUND MARKER  spawned by block 98 (motion 10311) f34                 (was: the ground strike)
  0x7C5  GROUND STRIKE  child of 0x7C4 at its death                           (was: a count-0 no-op)
  0x7C9  AIR MARKER     block 101 (motion 10314) f30 now spawns it directly   (was: air strike after launcher 0x7C8)
  0x7CA  AIR STRIKE     child of 0x7C9 at its death                           (was: a count-0 no-op)
  0x7C6 / 0x7C7 landing impacts (HP hit): radius 2.0/2.5 / 2.0 -> IMPACT_R (smaller)
MARKER: type 11 (target's feet, clamp horizontal 0..RANGE, vertical -15..15), speed 0 (K14/K16), life DELAY frames,
  no hit (hit id 0xffff, radius 0, like Garland's 0x83c; flag 0x2 = no ground raycast; NOT 0x200 = that flag skips
  the effect spawns FUN_08ad32a8/08ad3350), flag 0x20 = spawn kid 0 at death, fx 4 at half
  size (K25-27 = bullet scale 0.5) pointing down = a small crackling bolt column standing on the spot = the WARNING
  (leaf 22 has no FXSE sound: silent; leaf 37 was rejected: it carries the Keyblade hit sounds 85/86 of Trinity),
  AI tag 0x14 (+0x3c) = the CPU's projectile check (FUN_08adb8b0 / FUN_08a827ac) sees it at once.
STRIKE: type 5 (= the marker's spot, NOT the foe's current spot), K6 HEIGHT m up, pitch +89.9 (straight down),
  speed 1 m/frame (K14, canonical), b28 0 = no homing (v1 b28 1 = homing for its first frame), BOLTS bolts GAP
  frames apart in a ring (radius 0 / +SPREAD / ..., angle +150 deg), hit 0x1008 HP, fx 4 (Lightning bolt + flashes),
  impacts 0x7C6/0x7C7 on landing, flag 0x40000 (stop if Sora is hit).
End lag (op 0x28 = "can act again"): ground block 98 88 -> END_GROUND, air block 101 59 -> END_AIR (<= op0a 76 and the
  82-frame clip; hitbox-shapes.md section 9).
Units: magi times are 60/s frames (bullet age += 2 per 30 Hz update; canonical 0x7C4 fell ~1.06 m per frame).
Field meanings: notes/thunder.md section 2 + 6 (K14 = speed, K19 = homing turn rate, b28 1 = homing, flags).

Guarded: every row/record must be canonical (test286), v1 (test287..294) or already v2. Re-runnable ("already v2").
No effe/FEP/texture/sound change. Float table may grow (89.9 on a canonical input).

  python3 -I spot33_thundaga.py ISO [--dry] [--out NEW.objx]
  env: THUNDER_WARN_SCALE (0.5) THUNDER_DELAY (26) THUNDER_BOLTS (3) THUNDER_HEIGHT (9.0) THUNDER_GAP (6.0) THUNDER_SPREAD (0.85)
       THUNDER_RANGE (30.0) THUNDER_IMPACT_R (1.3) THUNDER_END_GROUND (96) THUNDER_END_AIR (72)
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
CLEAN = os.path.realpath(os.path.join(HERE, '..', '..', 'dumps', 'ULUS10566.iso'))
E = os.environ.get
DELAY = float(E('THUNDER_DELAY', '26'))
BOLTS = float(E('THUNDER_BOLTS', '3'))
HEIGHT = float(E('THUNDER_HEIGHT', '9.0'))
GAP = float(E('THUNDER_GAP', '6.0'))
SPREAD = float(E('THUNDER_SPREAD', '0.85'))
RANGE = float(E('THUNDER_RANGE', '30.0'))
IMPACT_R = float(E('THUNDER_IMPACT_R', '1.3'))
END_GROUND = int(E('THUNDER_END_GROUND', '96'))
END_AIR = int(E('THUNDER_END_AIR', '72'))
PITCH_DOWN = 89.9
GROUND_MOTION, AIR_MOTION = 10311, 10314
GROUND = dict(marker=0x7C4, strike=0x7C5)
AIR = dict(marker=0x7C9, strike=0x7CA)
IMPACTS = {0x7C6: ((2.0, 2.5), (IMPACT_R, IMPACT_R * 1.25)), 0x7C7: ((2.0, 0.0), (IMPACT_R, 0.0))}
FX_BOLT, HIT = 4, 0x1008
WARN_SCALE = float(E('THUNDER_WARN_SCALE', '0.5'))   # K25-27 = bullet scale (effect size; FUN_08ad46f0 -> +0xb8)
AI_TAG = bytes([0x14, 0xff, 0xff, 0xff])
FLAGS_STRIKE = 0x00040409            # canonical strike flags (0x8 die on ground -> impacts, 0x40000 stop if hit)
FLAGS_MARKER = 0x00040023            # 0x1 | 0x2 no ground raycast | 0x20 kid at death | 0x40000 (NOT 0x200 = no effects)


def chunks(d):
    n, = struct.unpack_from('<I', d, 4)
    return [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]


def close(a, b):
    return abs(a - b) < 1e-3 * max(1.0, abs(b))


class Magi:
    def __init__(self, chunk):
        self.m = bytearray(chunk)
        assert self.m[:4] == b'MAGI', 'not a MAGI chunk'
        self.cnt, nf = struct.unpack_from('<II', self.m, 8)
        self.rows_end = 16 + self.cnt * 204
        self.floats = list(struct.unpack_from('<%df' % nf, self.m, self.rows_end))
        self.extra = bytes(self.m[self.rows_end + 4 * nf:])
        self.nf0 = nf
        self.at = {struct.unpack_from('<H', self.m, 16 + k * 204)[0]: 16 + k * 204 for k in range(self.cnt)}

    def row(self, i):
        return bytes(self.m[self.at[i]:self.at[i] + 204])

    def u16(self, i, off):
        return struct.unpack_from('<H', self.m, self.at[i] + off)[0]

    def triple(self, i, k):
        o = self.at[i] + 0x40 + 3 * k
        return tuple(self.floats[j] for j in self.m[o:o + 3])

    def fidx(self, v):
        for k, x in enumerate(self.floats):
            if close(x, v):
                return k
        self.floats.append(float(v))
        assert len(self.floats) <= 255, 'float table full (u8 indexes)'
        return len(self.floats) - 1

    def build(self, rid, fx, hit, kids, typ, b28, r1, r2, flags, ks):
        """a complete 204-byte row from scratch (every field explicit: same result from any input state)"""
        r = bytearray(204)
        kids = list(kids) + [0xffff] * (8 - len(kids))
        struct.pack_into('<8H', r, 0, rid, 1, fx, 0xffff, 0, hit, 0xffff, kids[0])
        struct.pack_into('<7H', r, 0x10, *kids[1:])
        struct.pack_into('<7H', r, 0x1e, typ, 0, 1, 1, 0, b28, 0)       # type, +20, dir 1, +24 1, +26, b28, +2a
        struct.pack_into('<3fI', r, 0x2c, r1, r2, 1.0, flags)
        r[0x3c:0x40] = AI_TAG
        for k in range(46):
            r[0x40 + 3 * k:0x43 + 3 * k] = bytes(self.fidx(v) for v in ks.get(k, (0.0, 0.0, 0.0)))
        r[0xca] = r[0xcb] = self.fidx(1.0)                               # p138/p139 = 1.0 in every row
        return bytes(r)

    def put(self, rid, data):
        self.m[self.at[rid]:self.at[rid] + 204] = data

    def out(self):
        m = self.m[:self.rows_end] + bytearray(struct.pack('<%df' % len(self.floats), *self.floats)) + self.extra
        struct.pack_into('<I', m, 12, len(self.floats))
        return bytes(m)


def k3(v, d=0.0):
    return (v, v, d)


def strike_row(mg, rid):
    ks = {0: k3(BOLTS), 2: k3(GAP), 3: (0.0, 0.0, SPREAD), 4: (0.0, 0.0, 150.0), 6: k3(HEIGHT), 8: k3(PITCH_DOWN),
          14: k3(1.0), 16: k3(1.0), 21: k3(1.0), 25: k3(1.0), 26: k3(1.0), 27: k3(1.0),
          34: k3(RANGE), 35: k3(-15.0), 36: k3(15.0), 43: k3(30.0), 44: k3(30.0)}
    return mg.build(rid, FX_BOLT, HIT, [0xffff, 0xffff, 0x7C6, 0x7C7], 5, 0, 0.7, 0.0, FLAGS_STRIKE, ks)


def marker_row(mg, rid, strike):
    ks = {0: k3(1.0), 8: k3(PITCH_DOWN), 25: k3(WARN_SCALE), 26: k3(WARN_SCALE), 27: k3(WARN_SCALE),
          34: k3(RANGE), 35: k3(-15.0), 36: k3(15.0), 43: k3(DELAY), 44: k3(9999.0)}   # K44 as Garland's markers
    return mg.build(rid, FX_BOLT, 0xffff, [strike], 11, 2, 0.0, 0.0, FLAGS_MARKER, ks)


def known_state(mg, rid):
    """'canonical' / 'v1' / 'noop' (the count-0 child rows) or None"""
    typ, hit, fx = mg.u16(rid, 0x1e), mg.u16(rid, 0x0a), mg.u16(rid, 0x04)
    if hit != HIT or fx != FX_BOLT:
        return None
    k0, k8 = mg.triple(rid, 0), mg.triple(rid, 8)
    if typ in (0, 5) and close(k0[0], 1) and close(k8[0], 60):
        return 'canonical'
    if typ == 11 and close(k0[0], 3) and close(k8[0], PITCH_DOWN):
        return 'v1'
    if typ == 11 and close(k0[0], -0.5) and close(k0[1], 0.5) and close(k8[0], -89.9):
        return 'noop'
    return None


def block(d, ch, motion):
    i7 = next(k for k, c in enumerate(ch) if c[0] == 7)
    i8 = next(k for k, c in enumerate(ch) if c[0] == 8)
    t7 = d[ch[i7][2]:ch[i7][2] + ch[i7][3]]
    m7, = struct.unpack_from('<I', t7, 4)
    blk = next(struct.unpack_from('<H', t7, 10 + k * 8)[0] for k in range(m7)
               if struct.unpack_from('<H', t7, 8 + k * 8)[0] == motion)
    c8 = d[ch[i8][2]:ch[i8][2] + ch[i8][3]]
    return i8, struct.unpack_from('<I', c8, 8 + 4 * blk)[0]


def records(c8, o):
    """[(kind, offset, frame, op, params)] for the main list ('m') and the one-shot list ('o')"""
    out, k = [], o + 8
    for _ in range(c8[o + 2]):
        n = c8[k + 5]
        out.append(('m', k, struct.unpack_from('<H', c8, k)[0], c8[k + 4], struct.unpack_from('<%dI' % n, c8, k + 12)))
        k += 12 + 4 * n
    k = o + struct.unpack_from('<H', c8, o + 4)[0]
    for _ in range(c8[o + 3]):
        n = c8[k + 3]
        out.append(('o', k, struct.unpack_from('<H', c8, k)[0], c8[k + 2], struct.unpack_from('<%dI' % n, c8, k + 8)))
        k += 8 + 4 * n
    return out


def patch_blocks(d, ch, log):
    i8, _ = block(d, ch, GROUND_MOTION)
    c8 = bytearray(d[ch[i8][2]:ch[i8][2] + ch[i8][3]])
    for motion, old_end, new_end, spawn in ((GROUND_MOTION, 88, END_GROUND, None),
                                            (AIR_MOTION, 59, END_AIR, (0x7C8, AIR['marker']))):
        _, o = block(d, ch, motion)
        recs = records(c8, o)
        ends = [r for r in recs if r[0] == 'm' and r[3] == 0x28]
        assert len(ends) == 1 and ends[0][2] in (old_end, new_end), 'motion %d: op 0x28 not %d/%d' % (
            motion, old_end, new_end)
        if ends[0][2] != new_end:
            struct.pack_into('<H', c8, ends[0][1], new_end)
            log.append('motion %d: end lag op 0x28 %d -> %d' % (motion, old_end, new_end))
        if spawn:
            sp = [r for r in recs if r[0] == 'o' and r[3] == 0x04]
            assert len(sp) == 1 and sp[0][4][0] in spawn, 'motion %d: magi spawn not %x/%x' % ((motion,) + spawn)
            if sp[0][4][0] != spawn[1]:
                struct.pack_into('<I', c8, sp[0][1] + 8, spawn[1])
                log.append('motion %d: f%d spawn magi %x -> %x (air marker directly)' % (motion, sp[0][2], spawn[0],
                                                                                         spawn[1]))
    return i8, bytes(c8)


def patch(d):
    ch = chunks(d)
    mi = next(k for k, c in enumerate(ch) if c[1] == b'magi')
    mg = Magi(d[ch[mi][2]:ch[mi][2] + ch[mi][3]])
    log = []
    for side, s in (('ground', GROUND), ('air', AIR)):
        want_s = strike_row(mg, s['strike'])
        want_m = marker_row(mg, s['marker'], s['strike'])
        for rid, want, name in ((s['marker'], want_m, 'marker'), (s['strike'], want_s, 'strike')):
            assert rid in mg.at, 'magi %x missing (run spot33_magic first)' % rid
            if mg.row(rid) == want:
                continue
            st = known_state(mg, rid)
            if st is None:
                sys.exit('magi %x: not canonical / v1 / v2 -- stopping' % rid)
            mg.put(rid, want)
            log.append('magi %x %s %s: %s -> v2' % (rid, side, name, st))
    for rid, (old, new) in IMPACTS.items():
        o = mg.at[rid] + 0x2c
        cur = struct.unpack_from('<2f', mg.m, o)
        if all(close(a, b) for a, b in zip(cur, new)):
            continue
        assert all(close(a, b) for a, b in zip(cur, old)), 'magi %x radius %s not %s' % (rid, cur, old)
        struct.pack_into('<2f', mg.m, o, *new)
        log.append('magi %x impact radius %s -> %s' % (rid, old, new))
    if len(mg.floats) != mg.nf0:
        log.append('float table %d -> %d (+%s)' % (mg.nf0, len(mg.floats),
                                                 ', '.join('%g' % v for v in mg.floats[mg.nf0:])))
    i8, c8 = patch_blocks(d, ch, log)
    new = {}
    if mg.out() != d[ch[mi][2]:ch[mi][2] + ch[mi][3]]:
        new[mi] = mg.out()
    if c8 != d[ch[i8][2]:ch[i8][2] + ch[i8][3]]:
        new[i8] = c8
    if not new:
        return d, log
    out = rebuild_arc(d, new)
    ch2 = chunks(out)
    assert [(c[0], c[1]) for c in ch] == [(c[0], c[1]) for c in ch2]
    for k, (a, b) in enumerate(zip(ch, ch2)):
        if k not in new:
            assert d[a[2]:a[2] + a[3]] == out[b[2]:b[2] + b[3]], 'chunk %d changed' % k
    return out, log


def main():
    iso = sys.argv[1]
    assert os.path.realpath(iso) != CLEAN, 'never write the clean ISO'
    use_iso(iso)
    st, sz = pkg_offset(FILE)
    with open(iso, 'rb') as f:
        d = read_at(f, st, sz)
    out, log = patch(d)
    print('\n'.join(log))
    again, _ = patch(out)
    assert again == out, 'not idempotent'
    if out == d:
        print('Thundaga already v2 (nothing to do)')
        return
    if '--out' in sys.argv:
        dst = sys.argv[sys.argv.index('--out') + 1]
        assert not dst.lower().endswith('.iso')
        open(dst, 'wb').write(out)
        print('wrote %s (%d B)' % (dst, len(out)))
        return
    if '--dry' in sys.argv:
        print('(dry run: objx %d -> %d B, nothing written)' % (len(d), len(out)))
        return
    with tempfile.TemporaryDirectory() as t:
        path = os.path.join(t, 'f.objx')
        open(path, 'wb').write(out)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, path],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main()
