"""KH2 magic as HP attacks for #33 (Firaga / Thundaga / Blizzaga, ground + air). DRY RUN: never writes an ISO.
notes/hp-magic.md explains every field.

  python3 -I spot33_magic.py ISO CLEAN_ISO [--out NEW.objx]

ISO       = current build (obj/p_sev120.objx is read from it)
CLEAN_ISO = dumps/ULUS10566.iso. Every template (atkp / magi / plya rows, script blocks) comes from Cloud's UNTOUCHED
            obj/p_sev100.objx there: #33's LAND_LONG1-4 rows and blocks 65/68 are re-authored, and test ISOs carry
            an older edit of Cloud's own file too.
--out     = write the patched file copy (put it in with pkg_put.py, before spot33_soundids.py / spot33_effects.py).

What it adds (all appended; rerun-safe: things that already exist are skipped):
  atkp  NEW_HITS    HP hits = copies of LAND_FINISH2_3 (Meteorain's meteor: kind 3 = HP ranged, flags 0x92), with
                    the knock-back of another hit (+0x05 and +0x14..+0x33)
  magi  NEW_MAGI    copies of Cloud's projectile rows with own id (> 0x7C0, sorted), hit ids and children remapped
  plya  NEW_PIECES  copies of Cloud's ORIGINAL HP pieces (LAND_FINISH2 ground / HP_A_METEO1 air) with own id, motion,
                    banner and name
  p_se  SPELLS      new type-8 block (copy of a template block) + type-7 row per motion. Frames are re-timed:
                    0 → 0, template release → KH2 release, template end → new end (piecewise linear, like AUTHOR).
                    The template's magi spawns (one-shot op 4) are dropped and the spell's own are added.
  comb  ACTIONS     one single-step action per spell (the ablt row comes from spot33_moves.py MOVES)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from spot33_combos import rebuild_arc  # noqa: E402

FILE, CLOUD = 'obj/p_sev120.objx', 'obj/p_sev100.objx'
# new hit id: (template hit, knock-back from, name)
NEW_HITS = {0x1007: ('LAND_FINISH2_3', 'LAND_FINISH1_3', 'FIRAGA'),       # HP, blow away (Cross-slash finish)
            0x1008: ('LAND_FINISH2_3', 'LAND_FINISH2_3', 'THUNDAGA'),     # HP, Meteorain push
            0x1009: ('LAND_FINISH2_3', 'AIR_FINISH1_3', 'BLIZZAGA')}      # HP, blow away (Braver shockwave)
# new magi id: (Cloud row, hit id for +0x0a/+0x0c, {old child: new child}, fx or None = keep)
NEW_MAGI = {
    # Firaga: Fire's centre ball (0xD6: straight, life 42, bursts into 0x52D / 0x124 r 2.5) → HP everywhere
    0x7C1: (0xD6, 0x1007, {0x52D: 0x7C2, 0x124: 0x7C3}, None),
    0x7C2: (0x52D, 0x1007, {}, None),
    0x7C3: (0x124, 0x1007, {}, None),
    # Thundaga: Meteorain's falling strikes (0x233 → 0x2DB ×n → impacts 0x2C7 / 0x52E), own hit; air = 0x7BD tree
    0x7C4: (0x233, 0x1008, {0x2DB: 0x7C5, 0x2C7: 0x7C6, 0x52E: 0x7C7}, None),
    0x7C5: (0x2DB, 0x1008, {0x2C7: 0x7C6, 0x52E: 0x7C7}, None),
    0x7C6: (0x2C7, 0x1008, {}, None),
    0x7C7: (0x52E, 0x1008, {}, None),
    0x7C8: (0x7BD, 0x1008, {0x7BE: 0x7C9}, None),
    0x7C9: (0x7BE, 0x1008, {0x7C0: 0x7CA, 0x2C7: 0x7C6, 0x52E: 0x7C7}, None),
    0x7CA: (0x7C0, 0x1008, {0x2C7: 0x7C6, 0x52E: 0x7C7}, None),
    # Blizzaga: Fire's 3-way spread (0xD5 −25°, 0xD6 0°, 0xD7 +25°) as ice shards (still Cloud's fire visuals)
    0x7CB: (0xD5, 0x1009, {0x52D: 0x7CE, 0x124: 0x7CF}, 3),      # +4 effect bit 3 = KH2 ice rows (spot33_magicfx.py)
    0x7CC: (0xD6, 0x1009, {0x52D: 0x7CE, 0x124: 0x7CF}, 3),
    0x7CD: (0xD7, 0x1009, {0x52D: 0x7CE, 0x124: 0x7CF}, 3),
    0x7CE: (0x52D, 0x1009, {}, 0xFFFF),                         # bursts: no (fire) effect
    0x7CF: (0x124, 0x1009, {}, 0xFFFF),
}
# per-row byte overrides after copying the template: Blizzaga's balls copied Fire's +0x1e = 6 (spawn at the caster's
# live effect 19 = the FIRE charge → a fire flare on cast) → 0 = at the fighter, like Thundaga (effects helper)
MAGI_SET = {0x7CB: {0x1e: 0}, 0x7CC: {0x1e: 0}, 0x7CD: {0x1e: 0}}
# new piece id: (Cloud piece row, motion, banner text index (entry - 1) or -1, name)
NEW_PIECES = {0x1010: ('LAND_FINISH2', 10310, 13, 'HP_FIRAGA'),
              0x1011: ('LAND_FINISH2', 10311, 14, 'HP_THUNDAGA'),
              0x1012: ('LAND_FINISH2', 10312, 15, 'HP_BLIZZAGA'),
              0x1013: ('HP_A_METEO1', 10313, 13, 'HP_A_FIRAGA'),
              0x1014: ('HP_A_METEO1', 10314, 14, 'HP_A_THUNDAGA'),
              0x1015: ('HP_A_METEO1', 10315, 15, 'HP_A_BLIZZAGA')}
MIN_DIST = {0x1010: 0.0, 0x1012: 0.0, 0x1013: 0.0, 0x1015: 0.0}   # Meteorain rows say 7 m (CPU use; player skips it)
# motion: dict(block, tpl = Cloud template motion, rel_t = template frame that becomes the release (default: its first
#              magi spawn; Meteorain: 80 ground / 66 air = the meteor spawn, not the rising orb 0x9 at 20),
#              rel = KH2 release (script frames, KH2 trigger type 17/31),
#              end = new end (op 0x28 / os 0x02), anim = KH2 clip length in script frames, magi = [(frame, id)])
# fx = [(frame, FEPA id)]: Fire's balls (magi type +0x1e = 6) START AT a live effect of id row+0x20 = 19
# (FIGA_START) of the caster (FUN_08ad5d70 → FUN_08ad3c24 → FUN_088aa350). Cloud gets it from the FEPA row bound to
# slot _701A frame 24; Sora's new slots don't have it → the bullet's init fails and it is deleted at once
# (Mat, test 149: "firaga produces nothing"). So the spell block spawns id 19 itself, 2 frames before the release.
# (frame, FEPA effect id) one-shots for Firaga's flame ring around Sora — ids from the effects helper (spot33_firefx.py)
FIRE_RING_FX = [(22, 53), (48, 54)]   # 53 = KH2 flame flurry around Sora (74 frames), 54 = end burst at the HP hit
SPELLS = {
    # Firaga = KH2 Fire: a FLURRY OF FLAMES AROUND SORA, no projectile (Mat 2026-10-15: "it uses cloud's fireball
    # instead of a flurry of flames around you like KH2"). Body-centred area hits (shape 0x06, r 2.5): 4 hold hits
    # (0x1006, keep the foe in the flames) then the HP blow-away (0x1007 FIRAGA). Look = FIRE_RING_FX (spot33_firefx).
    10310: dict(block=97, tpl=10041, rel=28, end=90, anim=100, magi=[], fx=[(f, i) for f, i in FIRE_RING_FX],
                hits=[(24, 27, 0x1006, 0x06), (30, 33, 0x1006, 0x06), (36, 39, 0x1006, 0x06), (42, 45, 0x1006, 0x06),
                      (48, 56, 0x1007, 0x06)]),                                                   # KH2 228 FIRE_FINISH
    10311: dict(block=98, tpl=10095, rel_t=80, rel=34, end=88, anim=98, magi=[(34, 0x7C4)]),           # KH2 252 THUNDER_FINISH
    10312: dict(block=99, tpl=10041, rel=40, end=82, anim=92, magi=[(40, 0x7CB), (40, 0x7CC), (40, 0x7CD)]),  # 240 (no fire charge 19: Blizzaga spawns at the fighter, MAGI_SET)
    10313: dict(block=100, tpl=10098, rel_t=66, rel=28, end=76, anim=84, magi=[], fx=[(f, i) for f, i in FIRE_RING_FX],
                hits=[(24, 27, 0x1006, 0x06), (30, 33, 0x1006, 0x06), (36, 39, 0x1006, 0x06), (42, 45, 0x1006, 0x06),
                      (48, 56, 0x1007, 0x06)]),                                                   # KH2 232 FIRE_AIR
    10314: dict(block=101, tpl=10098, rel_t=66, rel=30, end=74, anim=82, magi=[(30, 0x7C8)]),          # KH2 256 THUNDER_AIR
    10315: dict(block=102, tpl=10098, rel_t=66, rel=36, end=68, anim=76, magi=[(36, 0x7CB), (36, 0x7CC), (36, 0x7CD)]),  # 244
}
ACTIONS = {1021: [0x1010], 1022: [0x1011], 1023: [0x1012], 1024: [0x1013], 1025: [0x1014], 1026: [0x1015]}


def arc_chunks(d):
    n, = struct.unpack_from('<I', d, 4)
    return [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]


def chunk(d, ch, typ, tag=b'p_se'):
    k = next(i for i, c in enumerate(ch) if c[0] == typ and c[1] == tag)
    return k, bytearray(d[ch[k][2]:ch[k][2] + ch[k][3]])


def block_of(t7, t8, motion):
    m7, = struct.unpack_from('<I', t7, 4)
    blk = next(struct.unpack_from('<H', t7, 10 + k * 8)[0] for k in range(m7)
               if struct.unpack_from('<H', t7, 8 + k * 8)[0] == motion)
    o = struct.unpack_from('<I', t8, 8 + 4 * blk)[0]
    return bytes(t8[o:o + struct.unpack_from('<H', t8, o + 6)[0]])


def retime(src, spec, blk):
    mains, k = [], 8
    for _ in range(src[2]):
        n = 12 + 4 * src[k + 5]
        mains.append(bytearray(src[k:k + n]))
        k += n
    e1, = struct.unpack_from('<H', src, 4)
    ones, k = [], e1
    for _ in range(src[3]):
        n = 8 + 4 * src[k + 3]
        ones.append(bytearray(src[k:k + n]))
        k += n
    rel_t = spec.get('rel_t') or min(struct.unpack_from('<H', e, 0)[0] for e in ones if e[2] == 4)
    ends = [struct.unpack_from('<H', e, 0)[0] for e in mains if e[4] == 0x28] + \
           [struct.unpack_from('<H', e, 0)[0] for e in ones if e[2] == 0x02]
    E = max(ends)
    kx, ky = [0, rel_t, E], [0, spec['rel'], spec['end']]

    def remap(f):
        if f == 0xFFFF:
            return f
        if f >= E:
            return f - E + spec['end']
        i = 0 if f <= rel_t else 1
        return int(round(ky[i] + (f - kx[i]) * (ky[i + 1] - ky[i]) / max(1, kx[i + 1] - kx[i])))
    for e in mains:
        fr, to = struct.unpack_from('<HH', e, 0)
        struct.pack_into('<HH', e, 0, remap(fr), to if to == 0xFFFF else max(remap(fr), remap(to)))
    ones = [e for e in ones if e[2] != 4]                    # template spell spawns out
    for e in ones:
        struct.pack_into('<H', e, 0, remap(struct.unpack_from('<H', e, 0)[0]))
    for fr, mid in spec['magi']:
        ones.append(bytearray(struct.pack('<HBB4sII', fr, 4, 2, bytes(4), mid, 0)))
    for fr, fid in spec.get('fx', []):                       # one-shot op 0x19 = FEPA effect by id
        ones.append(bytearray(struct.pack('<HBB4sII', fr, 0x19, 2, bytes(4), fid, 0)))
    for fr, to, hid, shape in spec.get('hits', []):          # own hitbox events (op 0x00 [hit id, shape])
        mains.append(bytearray(struct.pack('<HHBB6sII', fr, to, 0, 2, bytes(6), hid, shape)))
    last = max([struct.unpack_from('<H', e, 2)[0] for e in mains if e[4] == 0x0A and
                struct.unpack_from('<H', e, 2)[0] != 0xFFFF] +
               [struct.unpack_from('<H', e, 0)[0] for e in ones if e[2] == 0x02] +
               [struct.unpack_from('<H', e, 0)[0] for e in mains if e[4] == 0x28])
    assert last <= spec['anim'], 'block outlasts the animation (hitbox-shapes.md §9): %d > %d' % (last, spec['anim'])
    body = b''.join(mains)
    new = bytearray(src[:8])
    new[0] = blk
    new[2], new[3] = len(mains), len(ones)
    struct.pack_into('<HH', new, 4, 8 + len(body), 8 + len(body) + sum(map(len, ones)))
    return bytes(new + body + b''.join(ones)), rel_t, E


def main():
    iso, clean = sys.argv[1], sys.argv[2]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    use_iso(clean)
    cs, cz = pkg_offset(CLOUD)
    with open(clean, 'rb') as f:
        cd = read_at(f, cs, cz)
    use_iso(iso)
    st, sz = pkg_offset(FILE)
    with open(iso, 'rb') as f:
        d = read_at(f, st, sz)
    ch, cch = arc_chunks(d), arc_chunks(cd)
    new_chunks = {}
    # atkp
    ai, atkp = chunk(d, ch, 1, b'atkp')
    _, catkp = chunk(cd, cch, 1, b'atkp')
    crow = {catkp[8 + k * 68 + 0x34:8 + k * 68 + 0x44].split(b'\0')[0].decode(): bytes(catkp[8 + k * 68:8 + k * 68 + 68])
            for k in range(struct.unpack_from('<I', catkp, 4)[0])}
    na, = struct.unpack_from('<I', atkp, 4)
    have = {struct.unpack_from('<I', atkp, 8 + k * 68)[0] for k in range(na)}
    for hid, (tpl, kb, name) in sorted(NEW_HITS.items()):
        if hid in have:
            continue
        assert hid > max(have), 'atkp ids are binary-searched: new ids must be the biggest'
        row = bytearray(crow[tpl])
        struct.pack_into('<I', row, 0, hid)
        row[5] = crow[kb][5]
        row[0x14:0x34] = crow[kb][0x14:0x34]
        row[0x34:0x44] = name.encode().ljust(16, b'\0')
        atkp[8 + na * 68:8 + na * 68] = row
        na += 1
        have.add(hid)
        print('atkp %x %-9s <- %s, knock-back of %s (kind %d, flags %02x)' % (hid, name, tpl, kb, row[4], row[8]))
    struct.pack_into('<I', atkp, 4, na)
    new_chunks[ai] = bytes(atkp)
    # magi
    mi, magi = chunk(d, ch, 1, b'magi')
    _, cmagi = chunk(cd, cch, 1, b'magi')
    cn, = struct.unpack_from('<I', cmagi, 8)
    cm = {struct.unpack_from('<h', cmagi, 16 + k * 204)[0]: bytes(cmagi[16 + k * 204:16 + (k + 1) * 204]) for k in range(cn)}
    n, = struct.unpack_from('<I', magi, 8)
    rows = [bytes(magi[16 + k * 204:16 + (k + 1) * 204]) for k in range(n)]
    tail = bytes(magi[16 + n * 204:])
    ids = {struct.unpack_from('<h', r, 0)[0] for r in rows}
    for mid, (tpl, hit, kids, fx) in sorted(NEW_MAGI.items()):
        if mid in ids:
            continue
        r = bytearray(cm[tpl])
        struct.pack_into('<h', r, 0, mid)
        for off in (0x0A, 0x0C):
            if struct.unpack_from('<H', r, off)[0] != 0xFFFF:
                struct.pack_into('<H', r, off, hit)
        for off in range(0x0E, 0x1E, 2):
            v, = struct.unpack_from('<H', r, off)
            if v in kids:
                struct.pack_into('<H', r, off, kids[v])
        if fx is not None:
            struct.pack_into('<H', r, 4, fx)
        for off, val in MAGI_SET.get(mid, {}).items():
            r[off] = val
        rows.append(bytes(r))
        ids.add(mid)
        print('magi %x <- %x (hit %x, children %s, fx %d)' % (mid, tpl, hit, {hex(a): hex(b) for a, b in kids.items()},
                                                             struct.unpack_from('<H', r, 4)[0]))
    rows.sort(key=lambda r: struct.unpack_from('<h', r, 0)[0])
    for mid, (tpl, hit, kids, fx) in NEW_MAGI.items():          # every child must exist
        for v in kids.values():
            assert v in ids, hex(v)
    new_chunks[mi] = bytes(magi[:8]) + struct.pack('<I', len(rows)) + bytes(magi[12:16]) + b''.join(rows) + tail
    # plya
    pi, plya = chunk(d, ch, 1, b'plya')
    _, cplya = chunk(cd, cch, 1, b'plya')
    cp = {cplya[8 + k * 116 + 0x64:8 + k * 116 + 0x74].split(b'\0')[0].decode(): bytes(cplya[8 + k * 116:8 + (k + 1) * 116])
          for k in range(struct.unpack_from('<I', cplya, 4)[0])}
    npl, = struct.unpack_from('<I', plya, 4)
    pids = {struct.unpack_from('<H', plya, 8 + k * 116)[0] for k in range(npl)}
    for pid, (tpl, motion, banner, name) in NEW_PIECES.items():
        if pid in pids:
            continue
        r = bytearray(cp[tpl])
        struct.pack_into('<H', r, 0, pid)
        struct.pack_into('<H', r, 0x1C, motion)
        r[0x21] = banner & 0xFF
        if pid in MIN_DIST:
            struct.pack_into('<f', r, 0x24, MIN_DIST[pid])
        r[0x64:0x74] = name.encode().ljust(16, b'\0')
        plya += r
        npl += 1
        print('piece %x %-13s <- %s (role %d, +5 %d, kind %d, flags %08x), motion %d' %
              (pid, name, tpl, r[3], r[5], r[0x0E], struct.unpack_from('<I', r, 0x18)[0], motion))
    struct.pack_into('<I', plya, 4, npl)
    new_chunks[pi] = bytes(plya)
    # p_se type 7 / 8
    i7, t7 = chunk(d, ch, 7)
    i8, t8 = chunk(d, ch, 8)
    _, c7 = chunk(cd, cch, 7)
    _, c8 = chunk(cd, cch, 8)
    m7, = struct.unpack_from('<I', t7, 4)
    have7 = {struct.unpack_from('<H', t7, 8 + k * 8)[0] for k in range(m7)}
    for mot, spec in sorted(SPELLS.items()):
        if mot in have7:
            print('motion %d: already there' % mot)
            continue
        m, = struct.unpack_from('<I', t8, 4)
        assert spec['block'] == m, 'blocks must be added in order: next is %d' % m
        blk, rel_t, E = retime(block_of(c7, c8, spec['tpl']), spec, m)
        offs = list(struct.unpack_from('<%dI' % m, t8, 8))
        body = bytes(t8[8 + 4 * m:])
        body += b'\0' * ((-len(body)) % 4)
        offs = [o + 4 for o in offs] + [8 + 4 * (m + 1) + len(body)]
        t8 = bytearray(struct.pack('<II', struct.unpack_from('<I', t8, 0)[0], m + 1) +
                       struct.pack('<%dI' % (m + 1), *offs) + body + blk)
        m7, = struct.unpack_from('<I', t7, 4)
        rr = [bytes(t7[8 + k * 8:16 + k * 8]) for k in range(m7)] + [struct.pack('<HHHH', mot, m, 0, 0)]
        rr.sort(key=lambda r: struct.unpack_from('<H', r)[0])
        t7 = bytearray(t7[:4]) + struct.pack('<I', m7 + 1) + b''.join(rr) + t7[8 + m7 * 8:]
        print('motion %d -> block %d: copy of motion %d, release %d -> %d, end %d -> %d, magi %s (%d bytes)' %
              (mot, m, spec['tpl'], rel_t, spec['rel'], E, spec['end'], [(f, hex(i)) for f, i in spec['magi']], len(blk)))
    new_chunks[i7], new_chunks[i8] = bytes(t7), bytes(t8)
    # comb
    ci, comb = chunk(d, ch, 1, b'comb')
    ver, cnt = struct.unpack_from('<HH', comb, 0)
    offs = struct.unpack_from('<%dI' % cnt, comb, 4)
    acts = []
    for o in offs:
        aid, ns = struct.unpack_from('<HH', comb, o)
        acts.append(bytes(comb[o:o + 8 + 8 * ns]))
    have_a = {struct.unpack_from('<H', a, 0)[0] for a in acts}
    tpl_step = acts[0][8:16]
    for aid, pieces in ACTIONS.items():
        if aid in have_a:
            continue
        acts.append(struct.pack('<HHhh', aid, len(pieces), -1, -1) +
                    b''.join(struct.pack('<I', p) + tpl_step[4:] for p in pieces))
        print('comb action %d = %s' % (aid, [hex(p) for p in pieces]))
    assert len(acts) <= 256, 'FUN_08ab7f40 enables at most 256 comb entries'
    head = 4 + 4 * len(acts)
    nc = bytearray(struct.pack('<HH', ver, len(acts)))
    pos = head
    for a in acts:
        nc += struct.pack('<I', pos)
        pos += len(a)
    new_chunks[ci] = bytes(nc + b''.join(acts))
    res = rebuild_arc(d, new_chunks)
    print('file %d -> %d bytes' % (len(d), len(res)))
    if out:
        open(out, 'wb').write(res)
        print('written to', out, '(pkg_put.py ISO %s %s)' % (FILE, out))


if __name__ == '__main__':
    main()
