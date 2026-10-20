"""KH2 Firaga / Thundaga / Blizzaga cast sounds in Sora's spell scripts (Mat 2026-10-15: "add the KH2 Firaga sounds").
Appends one-shot op 0x03 [snd id, 0, 0] records to the p_se blocks of the Firaga motions (built by spot33_magic.py):
  cast at the hand (slot 73) 12 frames before the release, cast flash (74) at the release, fireball flying (75) 2 frames
  after it. The explosion sound (76) hangs off the fireball's explosion EFFECT (FXSE, spot33_firefx.py), not a script.
Slots come from spot33_sfx.py. Ids use Cloud's bank base (2200000 + slot) like every other script sound;
spot33_soundids.py (last build step) moves them to Sora's bank. SFX_BASE=21900000 when patching an ISO whose ids were
already moved. Re-runnable (records already there are skipped). Run after spot33_magic.py, before spot33_soundids.py.

  python3 -I spot33_spellsfx.py ISO
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
BASE = int(os.environ.get('SFX_BASE', 2200000))
VBASE = int(os.environ.get('VOICE_BASE', 2210000))
# spell voice (one-shot op 0x15 [voice id]): the copied templates said "FIRE!" (slot 29) for Blizzaga and "LIGHT!"
# (slot 15) for Thundaga; own KH2 lines appended by spot33_voicex.py (Mat: "Sora says fire when he's doing blizzard")
VOICE = {10312: 43, 10315: 43, 10311: 44, 10314: 44}
# motion: (release frame = spot33_magic SPELLS rel, [(frame offset from the release, sound slot)])
FIRE = [(-12, 73), (0, 74), (2, 75)]            # cast at the hand, flash, fireball flying
SPELLS = {10310: (28, FIRE), 10313: (28, FIRE),
          10311: (34, [(-12, 79)]), 10314: (30, [(-12, 79)]),     # Thundaga cast / charge
          10312: (40, [(-12, 80)]), 10315: (36, [(-12, 80)])}     # Blizzaga cast


def main():
    iso = sys.argv[1]
    use_iso(iso)
    st, sz = pkg_offset(FILE)
    with open(iso, 'rb') as f:
        d = read_at(f, st, sz)
    n, = struct.unpack_from('<I', d, 4)
    ch = [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]
    i7 = next(k for k, c in enumerate(ch) if c[0] == 7)
    i8 = next(k for k, c in enumerate(ch) if c[0] == 8)
    t7 = d[ch[i7][2]:ch[i7][2] + ch[i7][3]]
    m7, = struct.unpack_from('<I', t7, 4)
    rows = {struct.unpack_from('<H', t7, 8 + k * 8)[0]: struct.unpack_from('<H', t7, 10 + k * 8)[0] for k in range(m7)}
    c = bytearray(d[ch[i8][2]:ch[i8][2] + ch[i8][3]])
    changed = False
    for mot, (rel, sounds) in SPELLS.items():
        m, = struct.unpack_from('<I', c, 4)
        offs = list(struct.unpack_from('<%dI' % m, c, 8))
        o = offs[rows[mot]]
        size = struct.unpack_from('<H', c, o + 6)[0]
        blk = bytearray(c[o:o + size])
        e1, = struct.unpack_from('<H', blk, 4)
        n0 = blk[3]                                         # records before this run's additions
        have, k = set(), e1
        for _ in range(blk[3]):
            fr, op, npar = struct.unpack_from('<HBB', blk, k)
            if op == 0x03:
                have.add((fr, struct.unpack_from('<I', blk, k + 8)[0]))
            k += 8 + 4 * npar
        add = b''
        for dt, slot in sounds:
            rec = (rel + dt, BASE + slot)
            if rec in have:
                continue
            add += struct.pack('<HBB4sIII', rec[0], 0x03, 3, bytes(4), rec[1], 0, 0)
            blk[3] += 1
            print('motion %d (block %d): sound slot %d at frame %d' % (mot, rows[mot], slot, rec[0]))
        if mot in VOICE:                                    # retarget the spell's voice line (same size)
            k = e1
            for _ in range(n0):
                fr, op, npar = struct.unpack_from('<HBB', blk, k)
                if op == 0x15 and struct.unpack_from('<I', blk, k + 8)[0] != VBASE + VOICE[mot]:
                    struct.pack_into('<I', blk, k + 8, VBASE + VOICE[mot])
                    changed = True
                    print('motion %d: voice -> slot %d' % (mot, VOICE[mot]))
                k += 8 + 4 * npar
        if not add:
            if mot in VOICE:
                c[o:o + size] = blk
            print('motion %d: sounds already there' % mot)
            continue
        blk += add
        struct.pack_into('<H', blk, 6, len(blk))
        c[o:o + size] = blk
        offs = [x + len(add) if x > o else x for x in offs]
        struct.pack_into('<%dI' % m, c, 8, *offs)
        changed = True
    if not changed:
        return
    out = rebuild_arc(d, {i8: bytes(c)})
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'f.objx')
        open(p, 'wb').write(out)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main()
