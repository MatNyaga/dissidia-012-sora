"""KH2 Thundaga / Blizzaga looks + spell impact sounds for #33 (Sora) -- notes/kh2-effects.md "Thundaga" / "Blizzaga".

THUNDAGA (Sora's spell = Cloud's Meteorain magi 0x7C4.. fx bit 4 -> FEPA 30-33 -> leaves 26 METEO_APPEAR,
27 METEO_BODY (the falling rock), 28 METEO_HIT, 29 METEO_HIT_LAND):
  1. SIZE-NEUTRAL (a growing effe froze PPSSPP, test171): own TEX o12 (Cloud's lava rock, 128x64; drawn only by
     MDL 41/42/44 = the meteor's own rock/debris meshes) OVERWRITTEN with the KH2 THUNDER_3 bolt (dpd0 tex2 left half:
     white-gold bolt, 128x128 -> 128x64, premultiplied)
  2. MDL 40 (the rock's shell, G0, only leaf 27) -> o12 too
  3. leaf 27 rock nodes (0/1, rotated -90 deg about X, long axis = flight) comp 4 scale (12,15,12) -> (4,70,4) and
     its shell node 2 (15,5,15) -> (6,40,6): a thin glowing rod along the flight path = a flying bolt
  4. colours of leaves 26-29 -> electric yellow-white / blue (THUNDER_COLOURS); the orange fire-puff emitters
     (ANM 3 = o06 fire puffs, shared texture) in 28/29 -> RGBA 0 (hidden)
BLIZZAGA (Sora's spell = copies of Fire's 3-way ball 0x7CB-0x7CD fx bit 1 -> it shows FIRE). Prepared here, active once
spot33_magic gives the Blizzaga magi their own fx bit (ICE_BIT 3; bursts 0x7CE/0x7CF fx 0xFFFF):
  5. FEPA rows 67 (leaf 64 CHOU_V5_HIT), 29 (leaf 25 GARYUU_HIT), 78 (leaf 74 GARYUU_FIN_HIT) := Fire's ball / hit /
     ground-hit rows 20 / 21 / 23 (kind 0 / 1 / 12 and their other fields), magi bits = 1 << ICE_BIT, own res kept.
     (No magi uses bit 3 / 17 / 21 today: these rows were dead.)
  6. SIZE-NEUTRAL: own TEX o09 (Cloud's flames, 128x64) OVERWRITTEN with KH2 BLIZZARD_3 tex0 (the ice SURFACE,
     gradient-mapped to ice blues -> white, solid; tex1 = a sprite sheet that looked black on the meteor mesh). After spot33_firefx moved the Fire meshes off it, o09 is drawn by MDL 80 (leaf 64 = the ice ball
     itself) and only by leaves Sora never plays: Cross-slash marks KYOU_WORDS 49-52 + KYOU_HTM 32 (magi 0x47C-0x47F,
     spawned only by motion 10090, no #33 piece) and CHOU_V5_BOMB 67 (magi bit 19, no reachable magi) -> asserted.
     MDL 37 / 38 (only leaves 25 / 74) -> o09. Colours of 64 / 25 / 74 -> ice blues / white (ICE_COLOURS).
SOUNDS (FXSE = effe member .fxseb: per leaf 16 x 20-B records {u32 base, u32 slot, u32 frame, u32 ?, u32 flags}, played
as base + slot; flags 0 = once at frame, 4 = loop while alive, 2 = other bank). Cloud's FIGA_BALL flying loop is muted (MUTE_LOOPS). Base = 2200000 (before
spot33_soundids) or 21900000 (after): both handled. One-shot records of these leaves -> SLOTS, only if the slot
exists in #33's snd_ bank (an out-of-range slot is never written) -> run AFTER spot33_sfx.py, before spot33_soundids.
Re-runnable (textures written only if different, exact values otherwise); asserts the FEP size never changes.

  python3 -I spot33_magicfx.py ISO [--dry] [--png DIR]
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
MAG = os.path.join(HERE, '..', '..', 'kh2_export/raw/kh2_fifth/original/magic/')
TEX_BOLT, TEX_ICE = 0x12, 0x09                # own slots overwritten (o12 lava rock, o09 flames)
BOLT_MDLS = {44: {'METEO_HIT_LAND'}}           # bolt only on the thunder impact debris now
# Blizzaga's ball (Mat, test191r: "shoots out nothing", only a blow-up on the ground): row 67 drew leaf 64
# CHOU_V5_HIT = a one-shot hit flash, not a projectile body. The ice ball now draws leaf 27 METEO_BODY (the meteor's own
# flying body; Thundaga's row 31 draws CHOU_LIGHT since test188, so 27 is free) retextured with the KH2 ice crystals.
ICE_BODY_LEAF = 'METEO_BODY'
ICE_BODY_MDLS = {40: {'METEO_BODY'}, 41: {'METEO_BODY'}, 42: {'METEO_BODY'}}
ICE_BODY_SCALE = {0: (7.0, 20.0, 7.0), 1: (7.0, 20.0, 7.0), 2: (6.0, 30.0, 6.0)}   # leaf 27 node comp 4: shard along the flight + sheath stretched into a trail
# MDLs allowed to keep drawing a slot we overwrite (Sora never plays these leaves; see the docstring)
SLOT_OK = {TEX_BOLT: {40, 41, 42, 44}, TEX_ICE: {37, 38, 40, 41, 42, 80, 83, 49, 50, 64, 66, 68, 70}}
ICE_MDLS = {37: {'GARYUU_HIT', 'GARYUU_FIN_HIT'}, 38: {'GARYUU_HIT', 'GARYUU_FIN_HIT'}}
THUNDER_LEAVES = ('METEO_APPEAR', 'METEO_HIT', 'METEO_HIT_LAND')
THUNDER_COLOURS = {
    (230, 150, 98): (255, 240, 170), (200, 112, 48): (255, 220, 90), (128, 64, 32): (90, 120, 220),
    (48, 64, 128): (120, 160, 255), (128, 64, 24): (70, 90, 200), (200, 160, 98): (255, 240, 160),
    (64, 180, 200): (160, 220, 255), (128, 128, 0): (230, 230, 120), (200, 150, 128): (220, 230, 255),
    (200, 128, 64): (255, 222, 92)}
ICE_LEAVES = ('CHOU_V5_HIT', 'GARYUU_HIT', 'GARYUU_FIN_HIT', 'METEO_BODY')
ICE_COLOURS = {
    (200, 128, 98): (200, 230, 255), (98, 112, 128): (120, 170, 230), (240, 160, 64): (220, 240, 255),
    (128, 128, 128): (190, 225, 255), (150, 200, 255): (190, 225, 255),   # brighter (Mat: no dark)
    # leaf 27 METEO_BODY: Cloud's meteor colours and the thunder ones of test169-188 -> ice
    (230, 150, 98): (220, 240, 255), (200, 112, 48): (180, 220, 255), (128, 64, 32): (110, 160, 230),
    (255, 240, 170): (225, 242, 255), (255, 220, 90): (185, 222, 255), (90, 120, 220): (112, 162, 232)}
ICE_BIT = 3
# Thundaga's falling body: Mat (test185) "still meteor rain, a bit darker" -> the bolt texture on the rock mesh doesn't
# read. FEPA row 31 (METEO_BODY, fx bit 4, kind 0) draws this leaf instead: CHOU_LIGHT (leaf 48) = the light column of
# the EX-Burst tap phase (KH blue / white after spot33_burstfx, shows at Sora in every burst).
THUNDER_BODY_ROW, THUNDER_BODY_LEAF = 31, None   # row 31 now owned by spot33_lightningfx.py (Lightning's bolt)
ICE_ROWS = {67: 20, 29: 21, 78: 23}            # FEPA row id: Fire row id whose fields it takes
ICE_ROW_RES = {67: ICE_BODY_LEAF}              # row 67 draws the ice body (not its own leaf 64)
# FXSE one-shot sound slots per leaf (KH2 sounds added to #33's snd_ bank by spot33_sfx.py)
SLOTS = {'FIGA_HIT': 76, 'FIGA_HIT_WALL': 76, 'FIGA_HIT_LAND': 76, 'FIGA_HIT_AIR': 76,
         'METEO_HIT': 77, 'METEO_HIT_LAND': 77,
         'GARYUU_HIT': 78, 'GARYUU_FIN_HIT': 78}
BASES = (2200000, 21900000)
for t in (THUNDER_COLOURS, ICE_COLOURS):
    assert not set(t) & set(t.values())


def premult(rgba):
    import numpy as np
    a = np.asarray(rgba).astype(float)
    a[..., :3] *= a[..., 3:4] / 255.0
    a[..., 3] = 255
    return a.astype('uint8')


def bolt_png(path):
    """KH2 THUNDER_3 tex2 (256x128): left half = white-gold bolt -> 128x64, premultiplied"""
    import kh2_pax_dump as K
    from PIL import Image
    d = open(MAG + 'THUNDER_3.mag', 'rb').read()
    pax = next(d[o:o + s] for t, _, _, o, s in K.bar(d) if t == 18)
    _, _, dpxoff = K.pax_elements(pax)
    D = K.dpx_parse(pax[dpxoff:])[1][0]
    info, pix, pal = K.texture(D, K.dpd_lists(D)[1][2])
    rgba = [(pal[4 * i], pal[4 * i + 1], pal[4 * i + 2], min(255, pal[4 * i + 3] * 2)) for i in pix]
    im = Image.new('RGBA', (info['w'], info['h']))
    im.putdata(rgba)
    im = im.crop((0, 0, 128, 128)).resize((128, 64), Image.LANCZOS)
    Image.fromarray(premult(im)).save(path)
    return path


def png_to_clut(path):
    """premultiplied (alpha 255) PNG -> (w, h, indices, RGBA palette) via a 256-colour quantize"""
    from PIL import Image
    im = Image.open(path).convert('RGB').quantize(256)
    rgb = (im.getpalette() or [])[:768]
    pal = b''.join(bytes(rgb[3 * i:3 * i + 3]) + b'\xff' for i in range(len(rgb) // 3))
    return im.size[0], im.size[1], im.tobytes(), pal + b'\0' * (1024 - len(pal))


ICE_GRADIENT = [(0.0, (20, 40, 90)), (0.35, (60, 120, 210)), (0.65, (150, 205, 250)), (0.85, (215, 240, 255)),
                (1.0, (255, 255, 255))]


def ice_tex():
    """KH2 BLIZZARD_3 tex0 = the ICE SURFACE texture (made to wrap meshes), greys gradient-mapped to KH2 ice blues
    -> white, alpha 255 (a solid bright ice shard). test196 used tex1, the crystal SPRITE SHEET: the meteor mesh maps the
    whole sheet -> mostly empty/grey shard masks -> Mat: "all black, and kind of white"."""
    w, h, idx, pal = E.from_kh2(MAG + 'BLIZZARD_3.mag:0:0')
    out = bytearray(pal)
    for i in range(256):
        t = sum(pal[4 * i:4 * i + 3]) / 765
        for (t0, c0), (t1, c1) in zip(ICE_GRADIENT, ICE_GRADIENT[1:]):
            if t <= t1:
                f_ = (t - t0) / (t1 - t0)
                out[4 * i:4 * i + 4] = bytes([int(c0[k] + (c1[k] - c0[k]) * f_) for k in range(3)] + [255])
                break
    return w, h, idx, bytes(out)


def brighten_body(f):
    """MDL 41 (meteor rock, dark vertex colours 2-6/15) -> RGB 15 (alpha kept); MDL 42 (glow sheath, grey fades
    0-8) -> doubled once (skipped when a vertex is already above 8). -> vertices changed"""
    n = 0
    for i, mode in ((41, 'white'), (42, 'double')):
        d = f.resources('MDL')[i][1].data
        verts = []
        for k in range(F.u32(d, 0x34)):
            prim, vtype, stride, _, cnt, off = struct.unpack_from('<6I', d, F.u32(d, 0x38) + 0x18 * k)
            assert (vtype >> 2) & 7 == 6 and stride == 8
            verts += [off + v * stride + 2 for v in range(cnt)]
        cols = [struct.unpack_from('<H', d, o)[0] for o in verts]
        if mode == 'double' and max(c & 15 for c in cols) > 8:
            continue
        for o, c in zip(verts, cols):
            r, g, b = c & 15, c >> 4 & 15, c >> 8 & 15
            if mode == 'white':
                nc = 15 | 15 << 4 | 15 << 8 | (c & 0xF000)
            else:
                nc = min(15, 2 * r) | min(15, 2 * g) << 4 | min(15, 2 * b) << 8 | (c & 0xF000)
            if nc != c:
                struct.pack_into('<H', d, o, nc)
                n += 1
    if n:
        print('  MDL 41/42 (ice body) vertex colours brightened: %d' % n)
    return n


def put_tex(f, index, make):
    """overwrite own TEX `index` in place (same size) with make() -> (w, h, idx, pal); -> its key"""
    key = f.key_base() | index
    rk = F.resource_keys(f.write())
    other = [i for i, ks in enumerate(rk['MDL_tex']) if key in ks and i not in SLOT_OK[index]] + \
            ['ANM %d' % i for i, ks in enumerate(rk['ANM_tex']) if key in ks]
    assert not other, 'TEX %08x is also drawn by %s' % (key, other)
    w, h, idx, pal = make()
    t = E.make_tex(key, w, h, idx, pal)
    rec, blob = f.resources('TEX')[E.res_index(f, 'TEX', '0x%08x' % key)]
    assert F.u32(rec.data, 8) == len(t), 'TEX %08x is %d B, new %d B' % (key, F.u32(rec.data, 8), len(t))
    if bytes(blob.data[:len(t)]) != t:
        E.replace_tex(f, '0x%08x' % key, w, h, idx, pal)
        print('FEP: TEX %08x overwritten (%dx%d)' % (key, w, h))
    else:
        print('FEP: TEX %08x already done' % key)
    return key


def recolour(new, L, rng, names, table):
    for lf in L:
        nm = short(lf['name'])
        if nm not in names:
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
            if k3 in table:
                struct.pack_into('<3f', new, o, *table[k3])
                print('  leaf %d %s @%#x colour %s -> %s' % (lf['i'], nm, o, k3, table[k3]))


def edit_fep(fep_bytes, png_dir):
    f = F.Fep(fep_bytes)
    nk = f.rekey()
    if nk:
        print('FEP: rekey %d fields -> base %08x' % (nk, f.key_base()))
    tmp = os.path.join(png_dir or tempfile.gettempdir(), 'kh2_bolt_128x64.png')
    bolt = f.key_base() | TEX_BOLT        # o12 content: spot33_lightningfx.py (Lightning's thunder texture)
    ice = put_tex(f, TEX_ICE, ice_tex)
    brighten_body(f)
    d0 = f.write()
    L, _ = leaf_ranges(d0)
    users = {}
    for lf in L:
        for n in lf['nodes']:
            for k, i in F.node_resources(d0, n['at']):
                if k == 'MDL':
                    users.setdefault(i, set()).add(short(lf['name']))
    for mdls, key in ((BOLT_MDLS, bolt), (ICE_MDLS, ice), (ICE_BODY_MDLS, ice)):
        for i, only in mdls.items():
            assert users.get(i, set()) <= only, 'MDL %d also drawn by %s' % (i, users[i] - only)
            _, blob = f.resources('MDL')[i]
            if F.u32(blob.data, 0x1c) != key:
                print('  MDL %d (%s) texture %08x -> %08x' % (i, ','.join(sorted(users[i])), F.u32(blob.data, 0x1c), key))
                struct.pack_into('<I', blob.data, 0x1c, key)
    new = bytearray(f.write())
    L, rng = leaf_ranges(bytes(new))
    body = next(x for x in L if short(x['name']) == ICE_BODY_LEAF)
    for k, n in enumerate(body['nodes']):
        for c, _, o in F.node_components(bytes(new), n['at']):
            if c == 4 and o is not None and k in ICE_BODY_SCALE and struct.unpack_from('<3f', new, o + 4) != ICE_BODY_SCALE[k]:
                struct.pack_into('<3f', new, o + 4, *ICE_BODY_SCALE[k])
                print('  leaf %d %s node %d scale -> %s' % (body['i'], ICE_BODY_LEAF, k, ICE_BODY_SCALE[k]))
    for x in L:                                       # hide the orange fire puffs (ANM 3) in the thunder impacts
        if short(x['name']) not in ('METEO_HIT', 'METEO_HIT_LAND'):
            continue
        for k, n in enumerate(x['nodes']):
            if ('ANM', 3) not in F.node_resources(bytes(new), n['at']):
                continue
            for c, _, o in F.node_components(bytes(new), n['at']):
                if c == 7 and o is not None and struct.unpack_from('<4f', new, o + 4) != (0.0, 0.0, 0.0, 0.0):
                    struct.pack_into('<4f', new, o + 4, 0, 0, 0, 0)
                    print('  leaf %d %s node %d (fire puffs) RGBA -> 0 (hidden)' % (x['i'], short(x['name']), k))
    recolour(new, L, rng, THUNDER_LEAVES, THUNDER_COLOURS)
    recolour(new, L, rng, ICE_LEAVES, ICE_COLOURS)
    F.Fep(bytes(new))
    assert len(new) == len(fep_bytes), 'FEP size changed: %d -> %d' % (len(fep_bytes), len(new))
    return None if bytes(new) == bytes(fep_bytes) else bytes(new)


def edit_fepa(feb, body_res=None, ice_res=None):
    feb = bytearray(feb)
    rows = {struct.unpack_from('<I', feb, 16 + 0x104 * i + 0x24)[0]: 16 + 0x104 * i
            for i in range(struct.unpack_from('<I', feb, 12)[0])}
    changed = False
    if body_res is not None:
        o = rows[THUNDER_BODY_ROW]
        if struct.unpack_from('<I', feb, o + 0x28)[0] != body_res:
            print('FEPA: row id %d (Thundaga falling body) leaf %d -> %d (%s)' % (THUNDER_BODY_ROW,
                  struct.unpack_from('<I', feb, o + 0x28)[0], body_res, THUNDER_BODY_LEAF))
            struct.pack_into('<I', feb, o + 0x28, body_res)
            changed = True
    for rid, tpl in ICE_ROWS.items():
        a, b = rows[rid], rows[tpl]
        row = bytearray(feb[b:b + 0x104])
        row[0x24:0x2c] = feb[a + 0x24:a + 0x2c]                 # own id + leaf
        if ice_res and rid in ice_res:
            struct.pack_into('<I', row, 0x28, ice_res[rid])
        struct.pack_into('<I', row, 0x3c, 1 << ICE_BIT)
        if row != feb[a:a + 0x104]:
            feb[a:a + 0x104] = row
            changed = True
            print('FEPA: row id %d (leaf %d) <- fields of Fire row %d, magi bit %d' % (
                rid, struct.unpack_from('<I', row, 0x28)[0], tpl, ICE_BIT))
    return bytes(feb) if changed else None


def snd_count(objx):
    e = next(x for x in E.arc_entries(objx) if x[1] == b'snd_')
    return struct.unpack_from('<I', objx, e[2] + 12)[0]


MUTE_LOOPS = ('FIGA_BALL',)      # Cloud's fireball flying loop (flags 4) on top of our scripted fly sound (slot 75)


def edit_fxse(fx, fep_bytes, nsnd):
    """one-shot records of SLOTS leaves -> their KH2 slot (the first one; further one-shots of the same leaf are
    emptied so the sound doesn't play twice); looping records of MUTE_LOOPS leaves emptied. An empty record = 20 zero
    bytes, exactly like the 1132 unused ones in the table (size-neutral)."""
    fx = bytearray(fx)
    L, _ = leaf_ranges(fep_bytes)
    n = 0
    for lf in L:
        nm = short(lf['name'])
        recs = [16 + lf['i'] * 0x140 + k * 0x14 for k in range(16)]
        if nm in MUTE_LOOPS:
            for o in recs:
                base, s_, fr, _, flags = struct.unpack_from('<5I', fx, o)
                if base in BASES and flags & 4:
                    fx[o:o + 0x14] = bytes(0x14)
                    print('FXSE: leaf %d %s looping record (slot %d) muted' % (lf['i'], nm, s_))
                    n += 1
        slot = SLOTS.get(nm)
        if slot is None:
            continue
        if slot >= nsnd:
            print('FXSE: %s wants slot %d, but #33 snd_ has %d slots -> skipped (add it with spot33_sfx.py)' % (
                nm, slot, nsnd))
            continue
        first = True
        for k, o in enumerate(recs):
            base, s_, fr, _, flags = struct.unpack_from('<5I', fx, o)
            if base not in BASES or flags != 0:
                continue
            if first:
                first = False
                if s_ != slot:
                    struct.pack_into('<I', fx, o + 4, slot)
                    print('FXSE: leaf %d %s record %d (frame %d): slot %d -> %d' % (lf['i'], nm, k, fr, s_, slot))
                    n += 1
            else:
                fx[o:o + 0x14] = bytes(0x14)
                print('FXSE: leaf %d %s record %d (slot %d) emptied (one KH2 sound per hit)' % (lf['i'], nm, k, s_))
                n += 1
    return bytes(fx) if n else None


def main(a):
    iso = a[0]
    png_dir = a[a.index('--png') + 1] if '--png' in a else None
    objx = E.load_objx(iso, FILE)
    ei, effe, name, fep_bytes = E.split(objx)
    changed = False
    new = edit_fep(fep_bytes, png_dir)
    if new is not None:
        objx, changed = E.join(objx, ei, effe, name, new), True
        print('FEP %d -> %d B' % (len(fep_bytes), len(new)))
    from spot33_fx import patch_member
    d_ = E.split(objx)[3]
    lb = [x['i'] for x in leaf_ranges(d_)[0] if THUNDER_BODY_LEAF and THUNDER_BODY_LEAF in x['name']]
    li = {rid: next(x['i'] for x in leaf_ranges(d_)[0] if short(x['name']) == nm) for rid, nm in ICE_ROW_RES.items()}
    feb = edit_fepa(E.mpk_member(objx, 1), lb[0] if lb else None, li)
    if feb is not None:
        objx, changed = patch_member(objx, 1, feb), True
    fx = edit_fxse(E.mpk_member(objx, 2), E.split(objx)[3], snd_count(objx))
    if fx is not None:
        objx, changed = patch_member(objx, 2, fx), True
    if not changed:
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
