"""KH2 Fire/Firaga look for #33's (Sora's) Firaga -- notes/kh2-effects.md "Firaga" (2026-10-15).

Sora's Firaga = Cloud's Fire magi ball (0xD5-0xD7) + effects FIGA_START (id 19), FIGA_BALL (20, magi fx bit 1),
FIGA_HIT (21), FIGA_HIT_WALL (22), FIGA_HIT_LAND (23), FIGA_HIT_AIR (73): leaves 15-19 and 70 of Sora's FEP.
KH2 Firaga (kh2_fifth/original/magic/FIRE_3.mag, PAX "fire3", 1 DPD): ONE 128x64 greyscale texture (left: soft
fire blob, right: cellular fire shell) coloured per layer: deep red-orange core (183,35,19), yellow-white highlights
(196,151,89)/(231,184,101), dark red (65,20,18), smoke (58,35,21).
Changes (Sora's files only; Cloud vs Sora safe after the rekey):
  1. rekey (same as spot33_fx.py; no-op if done)
  2. SIZE-NEUTRAL (a growing effe chunk froze PPSSPP: test171, +27.9 KB): own TEX o0f (128x128, Cloud's Blade
     Beam texture: only leaves 22 HAKOU_BODY / 39 HAKOU_BG_HTM via ANM 10, and Blade Beam's magi 0xCD is spawned
     only by block 60 = motion 10040, which no #33 piece plays -> dead for Sora) is OVERWRITTEN with the KH2 FIRE_3
     texture (128x64, rows doubled to 128x128), palette gradient-mapped to KH2 fire colours (black -> dark red ->
     red-orange -> orange -> yellow-white), premultiplied (the fire meshes are additive). o09 is not touched here.
  3. Fire-only meshes -> the new texture: MDL 15 (flame mesh of every FIGA leaf), MDL 21 (ball flames),
     MDL 20 (the ball's spinning shell, was G0 cells) -- exclusivity asserted at run time
  4. FIGA leaves' colour values (FF7 orange/peach) -> KH2 fire reds / yellow-whites (COLOURS)
  5. SWIRL (test206, test210): FIGA_BALL made one-shot (LOOP_OFF); 8 inner rows = two KH2-style comets racing round
     Sora at chest height, 6 outer rows = the ring flying out, + a small burst; schedule = op 0x19 one-shots in the
     Firaga blocks (motions 10310/10313; replaces spot33_magic's FIRE_RING_FX one-shots)
Re-runnable (texture written only if different; colours are exact old-value matches); asserts the FEP size.
Run AFTER spot33_effects.py (Sora's own FEP id). Order vs spot33_fx / spot33_burstfx doesn't matter.

  python3 -I spot33_firefx.py ISO [--dry] [--png OUT.png]
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fep as F  # noqa: E402
import fep_edit as E  # noqa: E402
from spot33_burstfx import leaf_ranges, scan, short  # noqa: E402

FILE = 'obj/p_sev120.objx'
KH2_FIRE = os.path.join(HERE, '..', '..', 'kh2_export/raw/kh2_fifth/original/magic/FIRE_3.mag') + ':0:0'
TEX_SLOT = 0x0f                               # own texture o0f (Blade Beam; dead for Sora)
SLOT_USERS = {'ANM': {10}}                    # what may draw o0f besides our fire meshes (dead Blade Beam ANM)
FIRE_LEAVES = ('FIGA_START', 'FIGA_BALL', 'FIGA_HIT', 'FIGA_HIT_WALL', 'FIGA_HIT_LAND', 'FIGA_HIT_AIR')
MDLS = (15, 21, 20, 19)                       # 19 = FIGA_BALL's Ge glow mesh (fire-only) -> KH2 texture too (test210)
# KH2 Fire = flames swirling AROUND Sora, no projectile (Mat). Effect rows for the coordinator's spell scripts
# (op 0x19 [id, 0]), body-anchored like spot33_fx ANCHOR (strlen(model) > 0 -> attached to the bone; flags 0x80 + slot
# _000A like row 8 SWORD_LIGHT). Rows 53/54 = Cloud's Cross-slash marks KYOU_WORDS_1/2 (magi bits 10/11; their magi
# 0x47C-0x47F are spawned only by motion 10090 = dead for Sora; ids not in any EBOOT hard-coded list) -> free.
#   53 FLURRY: leaf 15 FIGA_START (the fire charge: KH2-fire flame meshes MDL 15 + light rings + flash; one-shot,
#      74 frames = 1.2 s, ends by itself) x2.2 at the hip
#   54 BURST:  leaf 18 FIGA_HIT_WALL (the fire explosion, KH2 fire colours) x1.5 at the hip
# anchor = root + y < 0 (up) like Cloud's own body rows (CHOU_FIRE/LIGHT root (0,-1/-1.4,0), FIGA_START row 19 root):
# 'hip' at (0,0,0) did not show in game (test196, Mat), while Cloud's root/r_wep anchors do.
# (row 53 = test202's fire ring at his feet, Mat: not it -> now an OUTER swirl row, see below)
SPELL_ROWS = {54: ('FIGA_HIT_WALL', 'root', (0.0, -1.0, 0.0), 0.8)}    # end burst (test210: x1.5 filled the screen -> x0.8)
# SWIRL (test206, Mat 2026-10-15 evening: "the fire effects are still not done" -> KH2 Fire = flames CIRCLING Sora):
# 8 FEPA rows = the KH2-textured fireball leaf FIGA_BALL placed on a rising circle around Sora (root-anchored like
# 53/54, so they follow him), spawned one after another every SWIRL_STEP frames (op 0x19 one-shots written into the
# Firaga blocks by this script) -> the fire runs around him, lap after lap; the start offset (+0x30) skips the
# start of each fireball's 30-34 frame life so only the newest few burn = a rotating arc, not a static ring.
# Rows = Cloud's Cross-slash rows bound to slot _700A (stubbed for #33, never played; ids 10-18 in no script);
# row 15 (ROT_HTM, magi fx 15 = live) is skipped. New ids 9100+ so no copied script can hit them.
# test210 (Mat on test208: "the balls of fire are around him and don't leave, also the look should look like the KH2"):
# - "don't leave": FIGA_BALL's tree +0 = 2 = LOOP (every persistent body has it: trails, Blade Beam / Meteor bodies,
#   EX auras) -> a fireball spawned by op 0x19 (no magi to kill it) burned forever. LOOP_OFF sets it to 0 (one-shot,
#   tree duration 50 frames); FIGA_BALL is not drawn by any live magi for Sora (Firaga has no projectile, Blizzaga's
#   balls use ice rows on fx bit 3, FEPA 20 = fx bit 1 unused).
# - KH2 Fire (FIRE_3.mag: two fireballs on Sora's sp3 / sp4 orbit bones, each with a flame trail): TWO comets 180 deg
#   apart race around him at chest height (8 angles, one step every SWIRL_STEP frames = 16 frames a lap, ~2 laps); each
#   fireball shows only its last SWIRL_LIFE frames (start offset = 50 - life) -> head + short trail, no full ring.
# - then the ring FLIES OUT: OUTER rows at a wider radius, all at once (OUTER_FRAME), short-lived, + a small burst.
SWIRL_ROWS = (10, 11, 12, 13, 14, 16, 17, 18)  # FEPA row INDEXES (= Cloud ids), one per angle
SWIRL_ID0 = 9100                               # ids 9100..9107
SWIRL_LEAF = 'FIGA_BALL'
SWIRL_DUR = 50                                 # FIGA_BALL tree duration (frames)
SWIRL_RADIUS = 1.0                             # m from Sora's centre (root bone space: x/z horizontal, y < 0 = up)
SWIRL_HEIGHT = (1.3, 1.3)                      # m, first -> last angle (level ring at the chest, like KH2; 1.0 showed at the legs, test211)
SWIRL_SCALE = 1.6                              # 0.75 = small dark puffs in game (test211)
SWIRL_LIFE = 5                                 # frames each fireball is visible (8 lit the whole ring: preview)
SWIRL_START = SWIRL_DUR - SWIRL_LIFE           # FEPA +0x30: frames skipped at the start of each fireball
SWIRL_STEP = 2                                 # frames between two steps (2 comets per step)
SWIRL_FRAMES = (16, 46)                        # first / last step frame (hold hits 24-45, finisher 48-56)
# OUTER ring = rows of dead Blade Beam (24/25 HAKOU_APPEAR/SHOT on stub slot _702A, 26/27/43 magi fx bit 2 = magi
# 0xCD, spawned only by motion 10040 = no #33 piece) + 53 (test202 feet ring, no longer used); ids 9108+ (no script
# uses 24-27/43/53, not in the EBOOT hard-coded id lists).
OUTER_ROWS = (24, 25, 26, 27, 43, 53)
OUTER_ID0 = 9108
OUTER_RADIUS, OUTER_HEIGHT, OUTER_SCALE, OUTER_LIFE = 2.2, 1.3, 1.8, 12
OUTER_FRAME = 47
BURST = None                                   # test211: FIGA_HIT_WALL = Cloud's big orange smoky explosion, hid everything -> no burst (the outer ring is the finish)
LOOP_OFF = ('FIGA_BALL',)
SPELL_MOTIONS = (10310, 10313)                 # ground / air Firaga blocks (spot33_magic SPELLS)
OLD_IDS = {53, 54}                                 # earlier schedule ids removed from those blocks (53 = fire ring at the feet)


def swirl_schedule():
    """-> [(frame, FEPA id)] for the Firaga blocks: two comets racing round, the ring flying out, the end burst"""
    n = len(SWIRL_ROWS)
    out = []
    for k, fr in enumerate(range(SWIRL_FRAMES[0], SWIRL_FRAMES[1] + 1, SWIRL_STEP)):
        out += [(fr, SWIRL_ID0 + k % n), (fr, SWIRL_ID0 + (k + n // 2) % n)]
    out += [(OUTER_FRAME, OUTER_ID0 + k) for k in range(len(OUTER_ROWS))]
    return out + ([BURST] if BURST else [])


TEMPLATE_ROW = 22            # base fields (kind 0, world, radius 4) -- then anchored
ATTACH_MODEL, ATTACH_FLAGS, ATTACH_SLOT = 'p_sev100_1p', 0x80, '_000A'
GRADIENT = [(0.0, (0, 0, 0)), (0.25, (90, 12, 6)), (0.5, (190, 45, 16)), (0.7, (235, 110, 35)),
            (0.85, (245, 180, 90)), (1.0, (255, 240, 200))]
BOOST = 1.3                                   # KH2's texture is dim on its own (layer colours brighten it)
COLOURS = {  # Cloud (FF7) RGB -> KH2 Firaga RGB, 128 = 1.0
    (200, 112, 48): (220, 80, 30),      # orange -> red-orange
    (240, 98, 64): (240, 70, 30),
    (200, 64, 12): (190, 40, 16),       # -> deep red (KH2 core 183,35,19)
    (128, 64, 24): (120, 32, 16),       # -> dark red (KH2 65,20,18 x2)
    (200, 130, 72): (230, 150, 80),     # -> warm yellow-orange (KH2 196,151,89)
    (240, 128, 64): (240, 110, 40),
    (240, 160, 128): (255, 200, 120),   # peach -> yellow-white (KH2 231,184,101)
    (220, 160, 48): (240, 190, 90),
    (48, 64, 128): (250, 150, 50),      # bluish smoke -> bright flame (test211: the KH2 smoke brown read as dark puffs)
    (60, 36, 22): (250, 150, 50),       # (test206-210 value)
}
assert not set(COLOURS) & set(COLOURS.values())
# FIGA_BALL only (test213; in game the deep reds read as dark puffs): KH2 Firaga orbs are bright orange-yellow
BALL_COLOURS = {(220, 80, 30): (255, 170, 60), (240, 70, 30): (255, 150, 50), (190, 40, 16): (255, 125, 35),
                (120, 32, 16): (235, 110, 40)}
assert not set(BALL_COLOURS) & set(BALL_COLOURS.values())


def kh2_fire_texture():
    """-> (w, h, linear indices, RGBA palette): KH2 FIRE_3 tex 0, palette greys gradient-mapped, premultiplied"""
    w, h, idx, pal = E.from_kh2(KH2_FIRE)
    out = bytearray(pal)
    for i in range(256):
        r, g, b, a = pal[4 * i:4 * i + 4]
        t = min(1.0, (r + g + b) / 765 * BOOST)
        for (t0, c0), (t1, c1) in zip(GRADIENT, GRADIENT[1:]):
            if t <= t1:
                f = (t - t0) / (t1 - t0) if t1 > t0 else 0
                rgb = [c0[k] + (c1[k] - c0[k]) * f for k in range(3)]
                break
        out[4 * i:4 * i + 4] = bytes([int(rgb[0] * a / 255), int(rgb[1] * a / 255), int(rgb[2] * a / 255), 255])
    return w, h, idx, bytes(out)


def edit_fep(fep_bytes):
    f = F.Fep(fep_bytes)
    nk = f.rekey()
    if nk:
        print('FEP: rekey %d fields -> base %08x' % (nk, f.key_base()))
    key = f.key_base() | TEX_SLOT
    rk = F.resource_keys(f.write())
    other = [('MDL', i) for i, ks in enumerate(rk['MDL_tex']) if key in ks and i not in MDLS] + \
            [('ANM', i) for i, ks in enumerate(rk['ANM_tex']) if key in ks and i not in SLOT_USERS['ANM']]
    assert not other, 'o0f is also drawn by %s' % other
    w, h, idx, pal = kh2_fire_texture()
    idx2 = b''.join(idx[r * w:(r + 1) * w] * 2 for r in range(h))          # 128x64 -> 128x128 (rows doubled)
    t = E.make_tex(key, w, 2 * h, idx2, pal)
    i = E.res_index(f, 'TEX', '0x%08x' % key)
    rec, blob = f.resources('TEX')[i]
    assert F.u32(rec.data, 8) == len(t), 'o0f is %d B, new texture %d B' % (F.u32(rec.data, 8), len(t))
    if bytes(blob.data[:len(t)]) != t:
        E.replace_tex(f, '0x%08x' % key, w, 2 * h, idx2, pal)
        print('FEP: TEX %08x (o0f, Blade Beam, dead for Sora) <- KH2 FIRE_3 texture (128x64 rows doubled)' % key)
    else:
        print('FEP: TEX %08x already holds the KH2 fire texture' % key)
    d0 = f.write()
    L, _ = leaf_ranges(d0)
    users = {}
    for lf in L:
        for n in lf['nodes']:
            for k, i in F.node_resources(d0, n['at']):
                if k == 'MDL':
                    users.setdefault(i, set()).add(short(lf['name']))
    for i in MDLS:
        assert users.get(i, set()) <= set(FIRE_LEAVES), 'MDL %d is also drawn by %s' % (i, users[i] - set(FIRE_LEAVES))
        _, blob = f.resources('MDL')[i]
        if F.u32(blob.data, 0x1c) != key:
            print('  MDL %d (%s) texture %08x -> %08x' % (i, ','.join(sorted(users[i])), F.u32(blob.data, 0x1c), key))
            struct.pack_into('<I', blob.data, 0x1c, key)
    new = bytearray(f.write())
    L, rng = leaf_ranges(bytes(new))
    for lf in L:                                   # LOOP_OFF: tree +0 = 2 (loop) -> 0 (one-shot)
        if short(lf['name']) in LOOP_OFF:
            leaf = F.u32(new, F.u32(new, 0x28) + 4 * lf['i'])
            t = F.u32(new, F.u32(new, 0x2c) + 4 * F.u16(new, leaf + 4))
            if F.u32(new, t) == 2:
                struct.pack_into('<I', new, t, 0)
                print('  leaf %d %s: tree loop flag 2 -> 0 (one-shot, %d frames)' % (lf['i'], short(lf['name']), F.u32(new, t + 4)))
    for lf in L:
        nm = short(lf['name'])
        if nm not in FIRE_LEAVES:
            continue
        hit = set()
        for o in scan(rng[lf['i']]):
            if not (new[o - 4:o] == b'\xcd' * 4 or o - 16 in hit):
                continue
            rgba = struct.unpack_from('<4f', new, o)
            if not all(0 <= v <= 255 and v == int(v) for v in rgba):
                continue
            k3 = tuple(int(v) for v in rgba[:3])
            hit.add(o)
            to = COLOURS.get(k3, k3)
            if nm == 'FIGA_BALL':
                to = BALL_COLOURS.get(to, to)
            if to != k3:
                struct.pack_into('<3f', new, o, *to)
                print('  leaf %d %s @%#x colour %s -> %s' % (lf['i'], nm, o, k3, to))
    F.Fep(bytes(new))                              # re-parse check
    assert len(new) == len(fep_bytes), 'FEP size changed: %d -> %d' % (len(fep_bytes), len(new))
    return None if bytes(new) == bytes(fep_bytes) else bytes(new)


def edit_fepa(feb, fep_bytes):
    """SPELL_ROWS: row := TEMPLATE_ROW's fields + own id, leaf by name, scale, bone anchor; magi bits 0"""
    from spot33_burstfx import leaf_ranges as LR
    L, _ = LR(fep_bytes)
    leaf = {short(x['name']): x['i'] for x in L}
    feb = bytearray(feb)
    rows = {struct.unpack_from('<I', feb, 16 + 0x104 * i + 0x24)[0]: 16 + 0x104 * i
            for i in range(struct.unpack_from('<I', feb, 12)[0])}
    changed = False
    for rid, (name, node, pos, scale) in SPELL_ROWS.items():
        a, b = rows[rid], rows[TEMPLATE_ROW]
        row = bytearray(feb[b:b + 0x104])
        struct.pack_into('<II', row, 0x24, rid, leaf[name])
        struct.pack_into('<I', row, 0x3c, 0)
        struct.pack_into('<3f', row, 0x00, *pos)
        struct.pack_into('<3f', row, 0x18, scale, scale, scale)
        struct.pack_into('<I', row, 0x7c, ATTACH_FLAGS)
        row[0x88:0xa8] = ATTACH_MODEL.encode().ljust(32, b'\0')
        row[0xa8:0xc8] = node.encode().ljust(32, b'\0')
        row[0xc8:0xe8] = ATTACH_SLOT.encode().ljust(32, b'\0')
        if row != feb[a:a + 0x104]:
            feb[a:a + 0x104] = row
            changed = True
            print('FEPA: row id %d -> leaf %d %s x%.1f at %s %s' % (rid, leaf[name], name, scale, node, pos))
    import math
    b = rows[TEMPLATE_ROW]
    sets = [(k, ri, SWIRL_ID0 + k, SWIRL_RADIUS, SWIRL_HEIGHT[0] + (SWIRL_HEIGHT[1] - SWIRL_HEIGHT[0]) * k / (len(SWIRL_ROWS) - 1),
             SWIRL_SCALE, SWIRL_START, len(SWIRL_ROWS), 0.0) for k, ri in enumerate(SWIRL_ROWS)]
    sets += [(k, ri, OUTER_ID0 + k, OUTER_RADIUS, OUTER_HEIGHT, OUTER_SCALE, SWIRL_DUR - OUTER_LIFE, len(OUTER_ROWS),
              math.pi / len(OUTER_ROWS)) for k, ri in enumerate(OUTER_ROWS)]
    for k, ri, rid, rad, h, sc, start, cnt, off in sets:
        a = 16 + 0x104 * ri
        ang = 2 * math.pi * k / cnt + off
        pos = (rad * math.cos(ang), -h, rad * math.sin(ang))
        row = bytearray(feb[b:b + 0x104])
        struct.pack_into('<II', row, 0x24, rid, leaf[SWIRL_LEAF])
        struct.pack_into('<I', row, 0x30, start)
        struct.pack_into('<I', row, 0x3c, 0)
        struct.pack_into('<3f', row, 0x00, *pos)
        struct.pack_into('<3f', row, 0x18, sc, sc, sc)
        struct.pack_into('<I', row, 0x7c, ATTACH_FLAGS)
        row[0x88:0xa8] = ATTACH_MODEL.encode().ljust(32, b'\0')
        row[0xa8:0xc8] = b'root'.ljust(32, b'\0')
        row[0xc8:0xe8] = ATTACH_SLOT.encode().ljust(32, b'\0')
        if row != feb[a:a + 0x104]:
            feb[a:a + 0x104] = row
            changed = True
            print('FEPA: row %d -> id %d %s x%.2f start %d at root (%.2f, %.2f, %.2f)'
                  % (ri, rid, SWIRL_LEAF, sc, start, *pos))
    return bytes(feb) if changed else None


def edit_scripts(objx):
    """Firaga blocks (SPELL_MOTIONS): drop every op 0x19 one-shot with an old / swirl / burst id, add swirl_schedule()
    -> new objx or None. Block layout: notes/hitbox-shapes.md section 6."""
    ents = E.arc_entries(objx)
    i8 = next(i for i, e in enumerate(ents) if e[0] == 8 and e[1] == b'p_se')
    t7 = next(objx[e[2]:e[2] + e[3]] for e in ents if e[0] == 7 and e[1] == b'p_se')
    c = objx[ents[i8][2]:ents[i8][2] + ents[i8][3]]
    rows = {struct.unpack_from('<H', t7, 8 + 8 * j)[0]: struct.unpack_from('<H', t7, 10 + 8 * j)[0]
            for j in range(struct.unpack_from('<I', t7, 4)[0])}
    n, = struct.unpack_from('<I', c, 4)
    offs = list(struct.unpack_from('<%dI' % n, c, 8))
    ours = OLD_IDS | {SWIRL_ID0 + k for k in range(len(SWIRL_ROWS))} | {OUTER_ID0 + k for k in range(len(OUTER_ROWS))}
    sched = swirl_schedule()
    changes = {}
    for m in SPELL_MOTIONS:
        b = rows[m]
        o = offs[b]
        size, = struct.unpack_from('<H', c, o + 6)
        blob = c[o:o + size]
        q, mains, ones = 8, [], []
        for _ in range(blob[2]):
            z = 12 + 4 * blob[q + 5]
            mains.append(blob[q:q + z])
            q += z
        for _ in range(blob[3]):
            z = 8 + 4 * blob[q + 3]
            ones.append(blob[q:q + z])
            q += z
        keep = [e for e in ones if not (e[2] == 0x19 and struct.unpack_from('<I', e, 8)[0] in ours)]
        add = [struct.pack('<HBB4sII', fr, 0x19, 2, bytes(4), i, 0) for fr, i in sched]
        newones = keep + add
        assert len(newones) < 256
        h = bytearray(blob[:8])
        h[3] = len(newones)
        body = b''.join(mains)
        struct.pack_into('<HH', h, 4, 8 + len(body), 8 + len(body) + sum(map(len, newones)))
        new = bytes(h) + body + b''.join(newones)
        if new != blob:
            changes[b] = new
            print('p_se: block %d (motion %d): %d effect one-shots -> swirl %s' % (b, m, len(ones) - len(keep), sched))
    if not changes:
        return None
    nc = bytearray(c)
    for b in sorted(changes, key=lambda b: offs[b], reverse=True):
        o = offs[b]
        z, = struct.unpack_from('<H', c, o + 6)
        nc[o:o + z] = changes[b]
    newoff = [o + sum(len(changes[b]) - struct.unpack_from('<H', c, offs[b] + 6)[0] for b in changes if offs[b] < o)
              for o in offs]
    struct.pack_into('<%dI' % n, nc, 8, *newoff)
    from spot33_combos import rebuild_arc
    return rebuild_arc(objx, {i8: bytes(nc)})


def main(a):
    if '--png' in a:                               # preview of the new texture only
        from PIL import Image
        w, h, idx, pal = kh2_fire_texture()
        im = Image.new('RGB', (w, h))
        im.putdata([tuple(pal[4 * i:4 * i + 3]) for i in idx])
        im.save(a[a.index('--png') + 1])
        print('texture preview ->', a[a.index('--png') + 1])
        return
    iso = a[0]
    objx = E.load_objx(iso, FILE)
    ei, effe, name, fep_bytes = E.split(objx)
    new = edit_fep(fep_bytes)
    objx2 = objx if new is None else E.join(objx, ei, effe, name, new)
    from spot33_fx import patch_member
    feb = edit_fepa(E.mpk_member(objx2, 1), E.split(objx2)[3])
    if feb is not None:
        objx2 = patch_member(objx2, 1, feb)
    scr = edit_scripts(objx2)
    if scr is not None:
        objx2 = scr
    if new is None and feb is None and scr is None:
        print('nothing to do')
        return
    print('FEP %d -> %d B, objx %d -> %d B' % (len(fep_bytes), len(new or fep_bytes), len(objx), len(objx2)))
    if '--dry' in a:
        print('dry run: nothing written')
        return
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'f.objx')
        open(p, 'wb').write(objx2)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main(sys.argv[1:])
