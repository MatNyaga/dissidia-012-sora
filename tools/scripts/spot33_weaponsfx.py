"""Kingdom Key swing + KH2 finisher sounds for #33: replace Cloud's sword-swing sounds in Sora's attack scripts with the KH2 Keyblade
slots 83/84/87 (cycled per hit, start shifted per block so a chain of one-hit moves varies) and 88 (heavy last hit of Ground Rave's finisher / Horizontal Slash finisher).
Logic from Codex's offline adapter (codex/keyblade-audio/review-v4/spot33_weaponsfx_offline.py), without its
hash pins, writing into the ISO. Needs slots 83-88 in the snd_ bank (spot33_sfx.py) → run after spot33_sfx,
before spot33_soundids (works with either bank base).

  python3 -I spot33_weaponsfx.py ISO [--dry]

p_se type 8 = script blocks (header: +2 n main events, +3 n one-shots, +4 u16 end of mains, +6 u16 size;
main event = 12 + 4*e[5] B, one-shot = 8 + 4*e[3] B; +0 u16 tick, +2 op, +4 condition bytes (byte 0 = variant)).
p_se type 7 = rows motion → (block, variant). Template = one-shot op 0x11 [bone 0x33/0x34, sound id, …] with a
Cloud swing id (slot 1-6) — the bone-attached weapon sound. A cue is placed 2 ticks before each hit window
start; old swing one-shots are removed. Rerun-safe (our own 83-88 one-shots are replaced too).
"""
import collections
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fep_edit as E  # noqa: E402
from spot33_combos import rebuild_arc  # noqa: E402
from spot33_soundids import bank_base  # noqa: E402

FILE = 'obj/p_sev120.objx'
# Keyblade CONTACT sounds (Codex's approved roles: option C = contact 85, option D = second layer 86): one-shot FXSE
# records (effe member 2, per leaf 16 x 20 B {base, slot, frame, ?, flags}) of the hit-mark leaves, in record order.
# Leaf 6 HTM (normal hit mark, was Cloud slot 15), 9 HTM_FINISH (finishing hit, 16 + 24), 32 KYOU_HTM (39 @0 + 37
# @10; test 26: "39+37 per hit" on HP hits). Same size (ids only) → effe stays 848640 B.
CONTACT = {'HTM': [85], 'HTM_FINISH': [85, 86], 'KYOU_HTM': [85, 86],
           # EX Burst (Omnislash = CHOU) effects carried Cloud's sounds (Mat, test208: "Ex sounded like Cloud"):
           # every burst hit, the finishing blow (full / incomplete bar) and the tap-phase light. None = record emptied.
           'CHOU_HIT': [85, 86], 'CHOU_HIT_LOSS': [85],
           'CHOU_HIT_FINISH': [89, 88, 91, 86], 'CHOU_HIT_LOSS_FINISH': [89, 88],
           'CHOU_FIRE': [90, None], 'CHOU_LIGHT': [90, None]}
BASES = (2200000, 21900000)
# EX Burst (Codex's approved set; its Trinity cue sheet waits for the Trinity animation import, so cues go on the
# CURRENT burst hits): motion → every old op 0x03/0x11 sound one-shot is removed (Cloud's weapon/EX sounds; voices
# op 0x15 and everything else kept), then 90 charge (Finishing Leap start) at tick 1, swings 83/84/87 2 ticks before
# each hit, last hit = 88 heavy + 89 impact (Guard Break) at the hit.
EX_BURST = {8108, 8500, 8501}       # _812B 9-hit flurry, _812C finish, _812A final blow (blocks 79 / 80 / 78)
MOTIONS = {10000, 10003, 10001, 10004, 10002, 10005, 10007, 10008, 10010, 10011, 10012, 10224, 10020, 10021, 10022,
           10031, 10032, 10050, 10051, 10060, 10316, 10091, 10095, 10300, 10301, 10302, 10303, 10304, 10306, 10307,
           10317, 10309}
HEAVY_LAST = {10005, 10316}          # finisher variants: last hit = heavy slot 88
CYCLE = [83, 84, 87]
PLAIN_OP3 = {88, 89, 93, 96}         # blocks whose swing is a plain op 0x03 (motions 10301/10302/10306/10309)
NEED = 96                            # bank must hold slots 0..95
# KH2 finisher effect sounds (Codex's KH2 PAX schedule; our moves run at KH2's natural speed → same ticks):
# motion: [(tick, slot)] as plain op 0x03 one-shots (condition 0 = every variant)
FINISHERS = {10095: [(30, 89)],                                    # Guard Break (KH2 660, 999005)
             10300: [(2, 90), (28, 91)],                           # Finishing Leap (668, 999038 / 999039)
             10304: [(18, 92), (32, 93), (48, 94), (80, 95)],      # Aerial Finish (776, 999007/008/006/151)
             10306: [(18, 92), (32, 93), (48, 94), (80, 95)]}      # Aerial Finish HP (same sweeps)


def split_block(blob):
    mains, ones, q = [], [], 8
    for _ in range(blob[2]):
        z = 12 + 4 * blob[q + 5]
        mains.append(blob[q:q + z])
        q += z
    assert q == struct.unpack_from('<H', blob, 4)[0]
    for _ in range(blob[3]):
        z = 8 + 4 * blob[q + 3]
        ones.append(blob[q:q + z])
        q += z
    assert q == struct.unpack_from('<H', blob, 6)[0]
    return mains, ones


def contact_fxse(objx):
    """→ new objx with the hit-mark FXSE records on CONTACT slots, or None if already so"""
    from spot33_burstfx import leaf_ranges, short
    from spot33_fx import patch_member
    fx = bytearray(E.mpk_member(objx, 2))
    n = 0
    for lf in leaf_ranges(E.split(objx)[3])[0]:
        slots = CONTACT.get(short(lf['name']))
        if not slots:
            continue
        k = 0
        for r in range(16):
            o = 16 + lf['i'] * 0x140 + r * 0x14
            base, slot, fr, _, flags = struct.unpack_from('<5I', fx, o)
            if base not in BASES or flags or k >= len(slots):
                continue
            if slots[k] is None:
                fx[o:o + 0x14] = bytes(0x14)
                print('FXSE: leaf %d %s record %d (slot %d) emptied' % (lf['i'], short(lf['name']), r, slot))
                n += 1
            elif slot != slots[k]:
                struct.pack_into('<I', fx, o + 4, slots[k])
                print('FXSE: leaf %d %s record %d (frame %d): slot %d -> %d' % (lf['i'], short(lf['name']), r, fr, slot, slots[k]))
                n += 1
            k += 1
    return patch_member(objx, 2, bytes(fx)) if n else None


def main():
    iso, dry = sys.argv[1], '--dry' in sys.argv
    d = E.load_objx(iso, FILE)
    ent = E.arc_entries(d)

    def ix(tag, t=None):
        return next(i for i, c in enumerate(ent) if c[1] == tag and (t is None or c[0] == t))

    def get(i):
        return d[ent[i][2]:ent[i][2] + ent[i][3]]

    i8 = ix(b'p_se', 8)
    c, t7, bank = get(i8), get(ix(b'p_se', 7)), get(ix(b'snd_'))
    base = bank_base(bank)
    count, = struct.unpack_from('<I', bank, 12)
    if count < NEED:
        sys.exit('snd_ bank has %d slots; run spot33_sfx.py first (needs 83-88)' % count)
    swing_ids = [base + x for x in list(range(1, 7)) + list(range(83, 89))]
    own_ids = range(base + 83, base + 89)
    rows = collections.defaultdict(list)
    for j in range(struct.unpack_from('<I', t7, 4)[0]):
        m, b, v, _ = struct.unpack_from('<4H', t7, 8 + 8 * j)
        rows[b].append((m, v))
    n, = struct.unpack_from('<I', c, 4)
    offs = list(struct.unpack_from('<%dI' % n, c, 8))
    changes = {}
    for b, users in sorted(rows.items()):
        if len(users) == 1 and users[0][0] in EX_BURST:
            o = offs[b]
            size, = struct.unpack_from('<H', c, o + 6)
            mains, ones = split_block(c[o:o + size])
            keep = [e for e in ones if e[2] not in (0x03, 0x11)]
            hits = sorted(set(struct.unpack_from('<H', e, 0)[0] for e in mains if e[4] in (0, 0x43)))
            cues = [(1, 90)] + [(max(0, t - 2), CYCLE[i % 3]) for i, t in enumerate(hits[:-1])]
            if hits:
                cues += [(max(0, hits[-1] - 2), 88), (hits[-1], 89)]
            newones = keep + [struct.pack('<HBB4B3I', t, 3, 3, 0, 0, 0, 0, base + sl, 0, 0) for t, sl in cues]
            h = bytearray(c[o:o + 8])
            h[3] = len(newones)
            body = b''.join(mains)
            struct.pack_into('<HH', h, 4, 8 + len(body), 8 + len(body) + sum(map(len, newones)))
            changes[b] = bytes(h) + body + b''.join(newones)
            print('block %d EX motion %d: %d hits, removed %d old sounds → %s' % (
                b, users[0][0], len(hits), len(ones) - len(keep), ' '.join('%d@%d' % (sl, t) for t, sl in cues)))
            continue
        if not any(m in MOTIONS for m, v in users):
            continue
        if not all(m in MOTIONS for m, v in users):
            print('block %d: skipped (shared with other motions %s)' % (b, users))
            continue
        o = offs[b]
        size, = struct.unpack_from('<H', c, o + 6)
        blob = c[o:o + size]
        mains, ones = split_block(blob)
        templates = [e for e in ones if e[2] == 0x11 and e[3] == 3 and struct.unpack_from('<I', e, 8)[0] in (0x33, 0x34)
                     and struct.unpack_from('<I', e, 12)[0] in swing_ids]
        if b in PLAIN_OP3 and set(m for m, v in users) <= {10301, 10302, 10306, 10309}:
            templates += [e for e in ones if e[2] == 3 and e[3] == 3 and e[12:20] == bytes(8)
                          and struct.unpack_from('<I', e, 8)[0] in [base + 20] + list(own_ids)]
        fin_ids = [base + x for x in range(89, 96)]
        finisher = [e for e in ones if e[2] == 3 and e[3] == 3 and struct.unpack_from('<I', e, 8)[0] in fin_ids]
        if not templates and not any(m in FINISHERS for m, v in users):
            print('block %d: no weapon-sound template, left alone' % b)
            continue
        keep = [e for e in ones if e not in templates and e not in finisher]
        add, log = [], []
        for motion, var in users:
            for tick, slot in FINISHERS.get(motion, []):
                add.append(struct.pack('<HBB4B3I', tick, 3, 3, 0, 0, 0, 0, base + slot, 0, 0))
                log.append('fx%d@%d' % (slot, tick))
        for motion, var in users:
            hits = sorted(set(struct.unpack_from('<H', e, 0)[0] for e in mains if e[4] in (0, 0x43) and e[6] in (0, var)))
            emitters = {}
            for e in templates:
                if e[4] in (0, var):
                    emitters.setdefault((e[2], e[8:12] if e[2] == 0x11 else b'', e[5:8], e[16:20]), e)
            for hi, tick in enumerate(hits):
                slot = 88 if motion in HEAVY_LAST and hi == len(hits) - 1 else CYCLE[(b + hi) % 3]
                for t in emitters.values():
                    e = bytearray(t)
                    struct.pack_into('<H', e, 0, max(0, tick - 2))
                    e[4] = var
                    struct.pack_into('<I', e, 12 if e[2] == 0x11 else 8, base + slot)
                    add.append(bytes(e))
                log.append('%d@%d' % (slot, max(0, tick - 2)))
            print('block %d motion %d v%d: %d hits → %s' % (b, motion, var, len(hits), ' '.join(log)))
            log = []
        newones = keep + add
        assert len(newones) < 256
        h = bytearray(blob[:8])
        h[3] = len(newones)
        body = b''.join(mains)
        struct.pack_into('<HH', h, 4, 8 + len(body), 8 + len(body) + sum(map(len, newones)))
        changes[b] = bytes(h) + body + b''.join(newones)
    nc = bytearray(c)
    for b in sorted(changes, key=lambda b: offs[b], reverse=True):
        o = offs[b]
        z, = struct.unpack_from('<H', c, o + 6)
        nc[o:o + z] = changes[b]
    newoff = [o + sum(len(changes[b]) - struct.unpack_from('<H', c, offs[b] + 6)[0] for b in changes if offs[b] < o)
              for o in offs]
    struct.pack_into('<%dI' % n, nc, 8, *newoff)
    res = rebuild_arc(d, {i8: bytes(nc)}) if changes else d
    new = contact_fxse(res)
    res = new if new is not None else res
    if res == d:
        print('nothing to change')
        return
    assert len(E.split(res)[1]) == 848640, 'effe size changed'
    print('%d blocks changed, file %d -> %d bytes' % (len(changes), len(d), len(res)))
    if dry:
        return
    fd, tmp = tempfile.mkstemp(suffix='.objx')
    os.write(fd, res)
    os.close(fd)
    import subprocess
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, tmp], check=True)
    os.unlink(tmp)


if __name__ == '__main__':
    main()
