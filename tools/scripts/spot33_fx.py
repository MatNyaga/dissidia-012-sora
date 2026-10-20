"""KH2-looking Explosion burst for #33 (Sora) -- notes/kh2-effects.md "Stage B" (2026-10-14 night).

Turns Cloud's unused magic-burst leaf 65 CHOU_V5_TOSSIN_HIT (FEPA id 68: G5 orb emitters + G3 ring arcs + swirl band
+ flash, 100 frames) into a KH2 Explosion look, all size-neutral, and makes Explosion's scripts spawn it:
  1. rekey Sora's own TEX/MDL/ANM keys (0x98011cNN -> 0x980128NN) so Cloud vs Sora never share edited resources
  2. own TEX o14 (clouds; only the conditional EX-Burst smoke leaf 47 draws it) <- KH2 dpd3 tex6 (light streak line,
     premultiplied: the swirl material is additive like the old smoke band)
  3. MDL 82 (swirl band, only leaf 65) -> texture o14  => light streaks circling Sora (KH2 element 48 layer L4)
  4. MDL 81 (G3 ring arc, only leaf 65) vertex colours -> KH2 ring blue-white (117,124,160) (layer L8)
     MDL 82 vertex colours -> KH2 streak white (141,134,125)
  5. leaf 65 orb emitters (kind 0x8e nodes, comp 7 = RGBA, 128 = 1.0; values > 128 brighten, Cloud's own data uses
     up to 255) -> bright white-pink, comp 4 sprite scale 100 % -> 280 % (test160: orbs were tiny blue dots; Mat:
     "KH2 style bigger"); leaf 65 warm orange flash/streak colours -> white-pink (LEAF_COLOURS)
  6. leaf 65 node 8 (MDL 83 = orange flame ring, MDL shared with Firaga leaves -> can't retexture) draws MDL 82
     (a second streak swirl) instead of fire
  7. FEPA rows 68 (and 57, below) made like row 22 (the Firaga blast that DOES show when spawned by op 0x19 at Sora): kind +0x38 0,
     +0x48 2, +0x50 0, rotation 0, culling radius +0xf4 4.0, magi fx bits +0x3c 0 (no magi/hit spawns it). Only
     +0x24 id / +0x28 res stay; scale +0x18 xyz from ROW_SCALE (68: 1.4 = bigger burst, 57: 2.2).
  8. strike = BRIGHT WHITE LIGHT (Mat: "shouldn't be an orange Firaga blast but a bright white light"): unused leaf
     53 CHOU_HIT_LOSS (FEPA 57: flash G83, light lines G8, glow G5/G86, colour-only meshes) recoloured white.
     Effect 22 itself is not touched (Sora's Firaga uses it).
  9. p_se blocks of motions 10305 / 10308 (Explosion): FIRST one-shot op 0x19 (orb start, KH2 element 48 at f34)
     -> id 68 (orb burst), later ones (the strike) -> id 57 (white flash)
Re-runnable: rekey/texture/tint run once (skipped when MDL 82 already draws o14); everything else is absolute.
Run AFTER spot33_chain.py (authors 10305/10308 with id 22) and spot33_effects.py (Sora's own FEP id 0x31280000).

  python3 -I spot33_fx.py ISO [--dry]
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
from fep_dump import leaves, resources  # noqa: E402
from spot33_burstfx import leaf_ranges, scan  # noqa: E402

FILE = 'obj/p_sev120.objx'
KH2_STREAK = os.path.join(HERE, '..', '..', E.KH2_DEFAULT) + ':3:6'
LEAF = 'CHOU_V5_TOSSIN_HIT_LEAF'
TEX_SLOT = 0x14                       # own texture index bits (o14)
MDL_SWIRL, MDL_RING, MDL_FIRE = 82, 81, 83
# --- orb look = test185 (Mat: flash shows). NOTE comp 4 on the 0x8e emitters is the emitter TRANSFORM scale, not the
#     sprite size: 280 % (test164-182) spread the orbs ~4x out of view. Bigger orbs need the particle-size field (open).
ORB_RGB = (255.0, 150.0, 220.0)           # white-pink (the G5 orb sprites lean blue: R needs > 1.0); test160 128,80,112
ORB_ALPHA = 128.0
ORB_SPRITE_PCT = 100.0                    # emitter transform %, Cloud's 100 (280 = orbs off screen)
ORB_BURST_SCALE = 1.0                     # FEPA row 68 scale
ORB_RGBA = ORB_RGB + (ORB_ALPHA,)
ORB_SCALE = (ORB_SPRITE_PCT,) * 3
# --- strike flash: leaf 55 CHOU_HIT_FINISH (EX-Burst finish flash; shows in game, test185). Leaf 53 (test164-182)
#     never showed (node kinds 0xCE/0xDE nobody else uses) and is no longer touched.
FLASH = 'CHOU_HIT_FINISH_LEAF'
FLASH_SCALE = 0.5                         # Mat: 1.3 'too bright', 0.8 (test195) 'still a little too bright' -> 0.5; leaf 55 is shared with the burst, so no recolour
# colour values (RGB floats right after a 0xcdcdcdcd pad, or the 2nd quad of such a start/end pair): old -> new
LEAF_COLOURS = {LEAF: {(200, 130, 72): (240, 210, 245), (200, 140, 98): (245, 220, 245),
                       (200, 128, 64): (235, 190, 235), (240, 160, 98): (255, 225, 250)}}
ROW_SCALE = {68: ORB_BURST_SCALE, 57: FLASH_SCALE}
# --- ANCHOR (test185: the flash appeared "away from the camera, a little behind" = rows copied from 22 have no model
#     name -> not attached, placed in the world). FUN_088a68fc attaches when strlen(row +0x88 model name) > 0 to the
#     spawner's bone named at +0xa8, with the row offset +0x00 (bone space; r_wep x = along the blade, root y < 0 = up)
#     -- like Cloud's body/blade rows. Flags +0x7c 0x80 = never auto-spawn from a slot; slot +0xc8 '_000A' exactly
#     like row 8 SWORD_LIGHT (0x80 + _000A, works at Sora) -- an empty slot name was never seen in Cloud's rows.
ATTACH_MODEL = 'p_sev100_1p'
ANCHOR = {68: ('root', (0.0, -1.0, 0.0)),       # orbs around the body (root, y < 0 = up, like Cloud's CHOU_* body rows; 'hip' at 0,0,0 did not show)
          57: ('r_wep', (1.0, 0.0, 0.0))}        # flash at the Keyblade tip = the strike point
ANCHOR_FLAGS = 0x80
ANCHOR_SLOT = '_000A'
RING_RGB, SWIRL_RGB = (117, 124, 160), (141, 134, 125)     # KH2 layer colours, 128 = 1.0
EXPLOSION_MOTIONS = (10305, 10308)
OLD_ID, NEW_ID, STRIKE_ID = 22, 68, 57


def tint_mdl(blob, rgb):
    """tint every RGBA4444 vertex colour of an MDL by RGB (128 = 1.0): each channel scaled, alpha kept, so the
    model's own fades (grey 0/4/8/b/9 vertices, additive material) survive. Run once (main() guards re-runs).
    Draw list: u32 count +0x34, table +0x38, 0x18-B rows {prim, vtype, stride, ?, n, data offset}."""
    d = blob.data
    n = 0
    for k in range(F.u32(d, 0x34)):
        prim, vtype, stride, _, cnt, off = struct.unpack_from('<6I', d, F.u32(d, 0x38) + 0x18 * k)
        assert (vtype >> 2) & 7 == 6 and stride == 8 and vtype & 3 == 1, 'unexpected vertex type %x' % vtype
        for v in range(cnt):
            o = off + v * stride + 2                      # u8 u, u8 v, u16 colour, s8 x y z, pad
            c, = struct.unpack_from('<H', d, o)
            r, g, b = (min(15, round((c >> s & 15) * x / 128)) for s, x in zip((0, 4, 8), rgb))
            struct.pack_into('<H', d, o, r | g << 4 | b << 8 | (c & 0xF000))
            n += 1
    return n


def edit_fep(fep_bytes):
    f = F.Fep(fep_bytes)
    nk = f.rekey()
    base = f.key_base()
    tex_key = base | TEX_SLOT
    swirl_rec, swirl = f.resources('MDL')[MDL_SWIRL]
    if F.u32(swirl.data, 0x1c) == tex_key:
        print('FEP: rekey/texture/tint already done (MDL %d draws %08x)' % (MDL_SWIRL, tex_key))
    else:
        print('FEP: rekey %d fields -> base %08x' % (nk, base))
        w, h, idx, pal = E.from_kh2(KH2_STREAK)
        E.replace_tex(f, '0x%08x' % tex_key, w, h, idx, E.premultiply(pal))
        print('  MDL %d texture %08x -> %08x' % (MDL_SWIRL, F.u32(swirl.data, 0x1c), tex_key))
        struct.pack_into('<I', swirl.data, 0x1c, tex_key)
        print('  MDL %d vertex colours -> %s (%d)' % (MDL_SWIRL, SWIRL_RGB, tint_mdl(swirl, SWIRL_RGB)))
        print('  MDL %d vertex colours -> %s (%d)' % (MDL_RING, RING_RGB,
                                                      tint_mdl(f.resources('MDL')[MDL_RING][1], RING_RGB)))
    new = bytearray(f.write())
    assert len(new) == len(fep_bytes), 'size changed'
    L = leaves(bytes(new), resources(bytes(new)))
    lf = next(x for x in L if LEAF in x['name'])
    for k, nd in enumerate(x['at'] for x in lf['nodes']):
        kind = F.u16(new, nd + 2)
        for c, _, o in F.node_components(bytes(new), nd):
            if c == 7 and kind == 0x8e and o is not None and struct.unpack_from('<4f', new, o + 4) != ORB_RGBA:
                struct.pack_into('<4f', new, o + 4, *ORB_RGBA)
                print('  leaf %d node %d (orb emitter) RGBA -> %s' % (lf['i'], k, ORB_RGBA))
            if c == 4 and kind == 0x8e and o is not None and struct.unpack_from('<3f', new, o + 4) != ORB_SCALE:
                struct.pack_into('<3f', new, o + 4, *ORB_SCALE)
                print('  leaf %d node %d (orb emitter) sprite scale -> %s %%' % (lf['i'], k, ORB_SCALE[0]))
            if c in (0x0b, 0x14) and o is not None and F.u16(new, o) == MDL_FIRE:
                struct.pack_into('<H', new, o, MDL_SWIRL)
                print('  leaf %d node %d MDL %d (fire ring) -> %d (streak swirl)' % (lf['i'], k, MDL_FIRE, MDL_SWIRL))
    starts = sorted((x['nodes'][0]['at'], x['i']) for x in L if x['nodes'])
    for name, table in LEAF_COLOURS.items():
        assert not set(table) & set(table.values())
        x = next(x for x in L if name in x['name'])
        hit = set()
        for o in scan(leaf_ranges(bytes(new))[1][x['i']]):   # the leaf's own tree data (robust to transplants)
            if not (new[o - 4:o] == b'\xcd' * 4 or o - 16 in hit):
                continue
            rgba = struct.unpack_from('<4f', new, o)
            if not all(0 <= v <= 255 and v == int(v) for v in rgba):
                continue
            key = tuple(int(v) for v in rgba[:3])
            if key in table:
                struct.pack_into('<3f', new, o, *table[key])
                hit.add(o)
                print('  leaf %d %s @%#x colour %s -> %s' % (x['i'], name[:-5], o, key, table[key]))
            elif key in table.values():
                hit.add(o)                                 # already recoloured (re-run): keep the pair rule working
    F.Fep(bytes(new))                                      # re-parse check
    return None if bytes(new) == bytes(fep_bytes) else bytes(new)


def edit_fepa(feb, flash_res=None):
    """rows NEW_ID / STRIKE_ID := row OLD_ID's fields, keeping their own id (+0x24) and leaf (+0x28); magi fx bits
    (+0x3c) 0; scale (+0x18 xyz) from ROW_SCALE"""
    feb = bytearray(feb)
    rows = {struct.unpack_from('<I', feb, 16 + 0x104 * i + 0x24)[0]: 16 + 0x104 * i
            for i in range(struct.unpack_from('<I', feb, 12)[0])}
    b = rows[OLD_ID]
    changed = False
    for rid in (NEW_ID, STRIKE_ID):
        a = rows[rid]
        row = bytearray(feb[b:b + 0x104])
        row[0x24:0x2c] = feb[a + 0x24:a + 0x2c]
        if rid == STRIKE_ID and flash_res is not None:
            struct.pack_into('<I', row, 0x28, flash_res)          # strike row -> the safe flash leaf
        struct.pack_into('<I', row, 0x3c, 0)
        struct.pack_into('<3f', row, 0x18, *(ROW_SCALE[rid],) * 3)
        if rid in ANCHOR:                                         # attach to Sora's bone (see ANCHOR)
            node, pos = ANCHOR[rid]
            struct.pack_into('<3f', row, 0x00, *pos)
            struct.pack_into('<I', row, 0x7c, ANCHOR_FLAGS)
            row[0x88:0xa8] = ATTACH_MODEL.encode().ljust(32, b'\0')
            row[0xa8:0xc8] = node.encode().ljust(32, b'\0')
            row[0xc8:0xe8] = ANCHOR_SLOT.encode().ljust(32, b'\0')
        if row == feb[a:a + 0x104]:
            print('FEPA: row id %d already done' % rid)
            continue
        feb[a:a + 0x104] = row
        changed = True
        print('FEPA: row id %d (leaf %d) <- fields of row id %d (kind 0, no rotation, no magi bits), scale %.1f' % (
            rid, struct.unpack_from('<I', row, 0x28)[0], OLD_ID, ROW_SCALE[rid]))
    return bytes(feb) if changed else None


def edit_scripts(objx):
    ents = E.arc_entries(objx)
    i7 = next(k for k, e in enumerate(ents) if e[0] == 7 and e[1] == b'p_se')
    i8 = next(k for k, e in enumerate(ents) if e[0] == 8 and e[1] == b'p_se')
    t7 = objx[ents[i7][2]:ents[i7][2] + ents[i7][3]]
    m7, = struct.unpack_from('<I', t7, 4)
    rows = {struct.unpack_from('<H', t7, 8 + k * 8)[0]: struct.unpack_from('<H', t7, 10 + k * 8)[0] for k in range(m7)}
    out = bytearray(objx)
    base8 = ents[i8][2]
    n = 0
    for mid in EXPLOSION_MOTIONS:
        blk = rows[mid]
        o = base8 + struct.unpack_from('<I', out, base8 + 8 + 4 * blk)[0]
        e1, = struct.unpack_from('<H', out, o + 4)
        k, spawns = o + e1, []
        for _ in range(out[o + 3]):
            fr, = struct.unpack_from('<H', out, k)
            op, cnt = out[k + 2], out[k + 3]
            if op == 0x19 and cnt and struct.unpack_from('<I', out, k + 8)[0] in (OLD_ID, NEW_ID, STRIKE_ID):
                spawns.append((fr, k))
            k += 8 + 4 * cnt
        for j, (fr, k) in enumerate(sorted(spawns)):
            want = NEW_ID if j == 0 else STRIKE_ID
            if struct.unpack_from('<I', out, k + 8)[0] != want:
                struct.pack_into('<I', out, k + 8, want)
                print('  motion %d (block %d) frame %d: effect id -> %d' % (mid, blk, fr, want))
                n += 1
    return bytes(out), n


def patch_member(objx, i, data):
    """same-size MPK member i of the effe chunk -> patched in place"""
    ei, effe, _, _ = E.split(objx)
    name, o, sz = list(E.mpk.entries(effe))[i]
    assert len(data) == sz
    at = E.arc_entries(objx)[ei][2] + o
    return objx[:at] + data + objx[at + sz:]


def main(a):
    iso = a[0]
    objx = E.load_objx(iso, FILE)
    ei, effe, name, fep_bytes = E.split(objx)
    changed = False
    new_fep = edit_fep(fep_bytes)
    if new_fep is not None:
        objx, changed = E.join(objx, ei, effe, name, new_fep), True
    fl = [x for x in leaves(E.split(objx)[3], resources(E.split(objx)[3])) if FLASH in x['name']]
    new_feb = edit_fepa(E.mpk_member(objx, 1), fl[0]['i'] if fl else None)
    if new_feb is not None:
        objx, changed = patch_member(objx, 1, new_feb), True
    objx, n = edit_scripts(objx)
    if not changed and not n:
        print('nothing to do')
        return
    if '--dry' in a:
        print('dry run: nothing written')
        return
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'f.objx')
        open(p, 'wb').write(objx)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main(sys.argv[1:])
