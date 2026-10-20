"""Sora's EX Burst = KH2 solo Trinity Limit (Codex v5, Mat: "I love it, ship it") — the script (p_se type 8) side.

Rewrites the two post-charge burst blocks of owner 33 (obj/p_sev120.objx) to the approved event contract
(codex/inbox/20261016-trinity-battle-stance-v5/reference-output/event-contract.json, sha256 8f2d9ec5…):
  8501 -> block 78 (GMO _812A, 85 frames = 168 ticks): INCOMPLETE (grades 0-3): exactly three Bravery hits
          0x3CF / group 33 at ticks 16-31, 35-39, 51-58. No HP hit, no 4th hit, no finisher.
  8500 -> block 80 (GMO _812C, 138 frames = 274 ticks): FULL (grade 4): ten A870 source windows, nine Bravery 0x3CF
          (16-31 ... 153-166) and the final HP 0x709 (LIMIT_ATK06) at 213-223 = A870's own last attack.
Both blocks keep the native burst events (camera op 0x0C [5,0,0], 0x06 busy, 0x0A, 0x13, 0x16 x2, face op 0x14,
voices) and get: one-shot op 0x21 [100] at 0 (victim visible again), Keyblade light/trail ops 0x2A over the swings,
KH2 swing/hit sounds (op 0x03, same slots/scheme as spot33_weaponsfx: 90 at 1, 83/84/87 cycling 2 ticks before each
window, heavy 88 + 89 on the full route's final HP hit; the incomplete route ends on an ordinary swing).
Removed from the old Cloud-timed blocks: the 116-126 HP windows, 0x708, slow-motion op 0x26 windows (victim keeps
normal time; 8501 had a 0-126 victim FREEZE), and the 124-tick flash (moved to the final hit at 213).
The motion end is the GMO length (168 / 274 ticks); no op 0x02 is added. The burst ends there (manager 85xx rule),
the incomplete route then lands in battle stance (spot33_reflect TRINITY_CTL grounded exit), the full route keeps 8600.

Re-runnable (writes nothing when both blocks already match). Blocks already retimed by Codex's patch_events.py (ready
gesture, all windows +24 ticks) are left alone, so a re-run can never undo that step. Asserts the type-7 rows (8500 -> 80, 8501 -> 78, one
row each, blocks not shared) before writing. Sound ids use the current bank base (2200000 before spot33_soundids,
21900000 after), so the step works in build_sora.sh (after spot33_weaponsfx) and on finished discs.

  python3 -I spot33_trinity.py ISO [--dry]
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
from spot33_soundids import bank_base  # noqa: E402

FILE = 'obj/p_sev120.objx'
BRV, HP, GROUP = 0x3CF, 0x709, 33
VOICE_A, VOICE_B = 21910032, 21910033          # Sora's burst voices (already in the old blocks; owner-33 bank ids)
FULL = dict(motion=8500, block=80, ticks=274,
            hits=[(16, 31), (35, 39), (51, 58), (64, 73), (85, 90), (99, 111), (117, 126), (129, 139), (153, 166),
                  (213, 223)], last_hp=True, face=[(0, 65535, 2)], voice_at=211, flash_at=213)
INCOMPLETE = dict(motion=8501, block=78, ticks=168, hits=[(16, 31), (35, 39), (51, 58)], last_hp=False,
                  face=[(0, 14, 2), (14, 60, 5), (60, 65535, 2)], voice_at=16, flash_at=None)
CYCLE = [83, 84, 87]
READY_SHIFT = 24                               # Codex patch_events.py (+24-tick ready gesture); never undo it


def main_ev(a, b, op, params=(), cond=b'\0' * 6):
    return struct.pack('<HHBB6s', a, b, op, len(params), cond) + b''.join(
        struct.pack('<f', p) if isinstance(p, float) else struct.pack('<i', p) for p in params)


def one_ev(t, op, params=(), cond=b'\0' * 4):
    return struct.pack('<HBB4s', t, op, len(params), cond) + b''.join(
        struct.pack('<f', p) if isinstance(p, float) else struct.pack('<i', p) for p in params)


def build(spec, head2, base):
    hits = spec['hits']
    last = len(hits) - 1
    mains = []
    for i, (a, b) in enumerate(hits):                               # hit windows (op 0x00 = hitbox [atkp id, group])
        mains.append(main_ev(a, b, 0x00, (HP if spec['last_hp'] and i == last else BRV, GROUP)))
    t_end = spec['ticks'] - 12
    s0, s1 = max(0, hits[0][0] - 2), hits[-1][1] + 2
    for _ in range(2):                                              # blade light (8888) + swing trail (9999), as Cloud's
        mains.append(main_ev(0, t_end, 0x2A, (0, 8888, 1, 0)))
        mains.append(main_ev(s0, s1, 0x2A, (1, 9999, 3, 0)))
    mains += [main_ev(0, 65535, 0x0C, (5, 0, 0)),                   # burst bone camera (camr 5, camera_include)
              main_ev(0, 65535, 0x13), main_ev(0, 65535, 0x0A), main_ev(0, 65535, 0x06),
              main_ev(0, 65535, 0x16, (0, 180)), main_ev(0, 65535, 0x16, (1, 180))]
    mains += [main_ev(a, b, 0x14, (0, f)) for a, b, f in spec['face']]
    ones = [one_ev(0, 0x21, (100,)),                               # victim visible (8101 hid him)
            one_ev(0, 0x15, (VOICE_B, 0, 0), b'\x01\0\0\0'),        # (kept from the old block, condition 1)
            one_ev(spec['voice_at'], 0x15, (VOICE_A, 0, 0))]
    if spec['flash_at'] is not None:
        ones.append(one_ev(spec['flash_at'], 0x1B, (56, 0, 60, 0, 0)))
    cues = [(1, 90)]
    for i, (a, b) in enumerate(hits):
        if spec['last_hp'] and i == last:
            cues += [(max(0, a - 2), 88), (a, 89)]
        else:
            cues.append((max(0, a - 2), CYCLE[i % 3]))
    ones += [one_ev(t, 0x03, (base + sl, 0, 0)) for t, sl in cues]
    body = b''.join(mains)
    h = bytearray(head2) + bytes([len(mains), len(ones)]) + struct.pack('<HH', 8 + len(body),
                                                                         8 + len(body) + sum(map(len, ones)))
    return bytes(h) + body + b''.join(ones)


def main():
    iso, dry = sys.argv[1], '--dry' in sys.argv
    use_iso(iso)
    st, sz = pkg_offset(FILE)
    with open(iso, 'rb') as f:
        d = read_at(f, st, sz)
    n, = struct.unpack_from('<I', d, 4)
    ch = [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]
    i7 = next(k for k, c in enumerate(ch) if c[0] == 7)
    i8 = next(k for k, c in enumerate(ch) if c[0] == 8)
    isnd = next(k for k, c in enumerate(ch) if c[1] == b'snd_')
    base = bank_base(d[ch[isnd][2]:ch[isnd][2] + ch[isnd][3]])
    assert base in (2200000, 21900000), 'unexpected sound bank base %d' % base
    t7 = d[ch[i7][2]:ch[i7][2] + ch[i7][3]]
    m7, = struct.unpack_from('<I', t7, 4)
    rows = [struct.unpack_from('<HH', t7, 8 + k * 8) for k in range(m7)]
    c = bytearray(d[ch[i8][2]:ch[i8][2] + ch[i8][3]])
    m, = struct.unpack_from('<I', c, 4)
    offs = list(struct.unpack_from('<%dI' % m, c, 8))
    changed = False
    for spec in (INCOMPLETE, FULL):
        users = [mid for mid, blk in rows if blk == spec['block']]
        mine = [blk for mid, blk in rows if mid == spec['motion']]
        assert mine == [spec['block']], 'motion %d rows %s (expected block %d)' % (spec['motion'], mine, spec['block'])
        assert users == [spec['motion']], 'block %d shared: %s' % (spec['block'], users)
        o = offs[spec['block']]
        size, = struct.unpack_from('<H', c, o + 6)
        old = bytes(c[o:o + size])
        new = build(spec, old[:2], base)
        hits = []
        q = o + 8
        for _ in range(old[2]):
            if c[q + 4] == 0x00:
                hits.append(struct.unpack_from('<HH', c, q))
            q += 12 + 4 * c[q + 5]
        if hits == [(a + READY_SHIFT, b + READY_SHIFT) for a, b in spec['hits']]:
            print('motion %d (block %d): Codex ready timing (+%d, patch_events.py) already applied - left alone'
                  % (spec['motion'], spec['block'], READY_SHIFT))
            continue
        if new == old:
            print('motion %d (block %d): already the Trinity contract' % (spec['motion'], spec['block']))
            continue
        c[o:o + size] = new
        offs = [x + len(new) - size if x > o else x for x in offs]
        struct.pack_into('<%dI' % m, c, 8, *offs)
        print('motion %d (block %d): %d hits %s, %d -> %d B' % (spec['motion'], spec['block'], len(spec['hits']),
              ' '.join('%d-%d%s' % (a, b, ' HP' if spec['last_hp'] and k == len(spec['hits']) - 1 else '')
                       for k, (a, b) in enumerate(spec['hits'])), size, len(new)))
        changed = True
    if not changed or dry:
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
