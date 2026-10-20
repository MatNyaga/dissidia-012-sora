"""SAFE VERSION (2026-10-15, tested in PPSSPP): Lightning's TREES are NOT transplanted any more. Bisect on test201
(record in notes/kh2-effects.md): her THUNDER_BODY tree in Sora's leaf 22 FREEZES the game on the first Bravery swing
(variant D), while her texture + flipbook + meshes alone (variant B) and emptying leaves 49/50 (variant C) do not.
Her nodes use kinds Sora's FEP never has (0x150 bolt mesh, 0xD0 arcs, 0x64) -> they need code only Lightning runs.
Now: her bolt TEXTURE (o06 -> Sora o12) and spark flipbook (ANM 4 -> Sora ANM 10) are drawn by Cloud's own Blade Beam
leaves 22 (wave body: its own MDL 30/31 -> o12) / 23 (hit), recoloured electric white-blue; FEPA 31 -> 22, 32/33 -> 23,
30 -> 49 (emptied). The tree-transplant description below is kept for the record (TREES = {} now).

Lightning's own Thunder effect for Sora's Thundaga -- notes/kh2-effects.md "Lightning's thunder in Sora".

Mat (test195): the CHOU_LIGHT columns look like "a bunch of cones" -> "Lightning has thunder as one of her spells".
Lightning = owner 31, obj/p_gst130.objx (clean ISO). Her THUNDER_BODY (leaf 47: her bolt texture o06 on MDL 57,
untextured arc meshes 10/12/58/59 (global), G82/G8a flashes, G5 sparks) and THUNDER_HIT (leaf 48) are copied into
Sora's FEP, SIZE-NEUTRAL (a growing effe froze PPSSPP), Sora's keys, into leaves/slots Sora never plays:
  trees:  her 47 THUNDER_BODY -> Sora leaf 22 (HAKOU_BODY, Blade Beam: magi 0xCD only from dead motion 10040)
          her 48 THUNDER_HIT  -> Sora leaf 23 (HAKOU_HIT)
  MDL:    her own 2 / 13 / 57 / 60 -> Sora 63 / 64 / 65 / 66 (Cross-slash mark meshes, leaves 49-52, dead)
          her global 10 / 12 / 59 -> Sora's own records of the same global keys (71 / 13 / 72)
          her global 58 (f000010b, Sora has none) -> Sora slot 67 turned into a global-key record (size 0)
  ANM:    her own 4 (G5 sparks) -> Sora ANM 10 (Blade Beam flipbook; leaves 22/39 only); globals 9 / 10 -> Sora 19 / 7
  TEX:    her own o06 (bolt, 128x64) -> Sora o12 (128x64; MDL 44 = thunder impact debris + the new MDL 64/65)
  FEPA:   Thundaga rows: 31 (falling strike, kind 0) -> leaf 22 x0.8 (her row's scale), 32 (hit, kind 1) / 33
          (ground hit, kind 12) -> leaf 23 x0.5, 30 (appear: Cloud's meteor portal) -> leaf 49 (gutted = nothing;
          Lightning's own THUNDER_APPER is empty too)
  FXSE:   leaf 22 records emptied (Cloud's Blade Beam sounds), leaf 23: first one-shot -> slot 77 (KH2 thunder
          strike, if the bank has it), the rest emptied
  size:   dead leaves 49-52, 38, 39, 64, 66-68 get empty trees (copies of her empty THUNDER_APPER tree) until the FEP
          is not bigger than before, then an unreferenced pad blob makes it EXACTLY the old size (asserted).
Re-runnable: skips the transplant when leaf 22 already has her node layout; resources/rows/FXSE are absolute.
Run after spot33_magicfx.py (FXSE slot 77 needs spot33_sfx's slots) and before spot33_soundids.py.

  python3 -I spot33_lightningfx.py ISO CLEAN_ISO [--dry]
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
import fep_transplant as T  # noqa: E402

FILE, LIGHT = 'obj/p_sev120.objx', 'obj/p_gst130.objx'
TREES = {}                                   # Sora leaf <- Lightning leaf: DISABLED (foreign node kinds freeze the game)
EMPTY_SRC = 46                               # Lightning THUNDER_APPER: 0 nodes
GUT = []                                     # nothing emptied any more (row 30 -> the electric burst instead)
MDL_OWN = {}                                 # (her meshes only served the transplanted trees)
MDL_GLOBAL = {}
BOLT_MDLS = {30, 31}                         # Blade Beam wave meshes (only leaf 22) -> her bolt texture in o12
LEAF_COLOURS = {22: {(128, 128, 128): (200, 225, 255), (128, 72, 48): (205, 220, 255), (48, 64, 128): (150, 190, 255)},
                23: {(128, 128, 128): (200, 225, 255)}}
ANM_OWN = {}                                 # NOT installed: Sora's ANM 10 is also drawn by hit-mark leaf 39 -> Explosion froze (test202)
# leaf 22's own nodes: ANM 10 (Blade Beam flipbook on o0f = fire now) -> 1 (G5 orbs); test210: the strike's sprite
# emitters 8 (G80) / 9 -> the GLOBAL electric flipbooks Lightning's THUNDER_BODY draws (her ANM 10 = G82 = Sora 7, her
# ANM 9 = G8a = Sora 19); leaf 23 (impact) flash sprites 1 / 0 -> G82 / G8a. Index edits only (no data changes).
LEAF_ANM_REMAP = {22: {10: 1, 8: 7, 9: 19}, 23: {1: 7, 0: 19}}
ANM_GLOBAL = {9: 19, 10: 7}
TEX_OWN = {6: 0x12}                          # her TEX index 6 (o06) -> Sora own TEX key index 0x12
# FEPA row id: (leaf, scale or (x, y, z)); 30 = flash in the sky. 31 = the falling strike: stretched along its local
# z (= the ribbon's long axis, see RIBBONS) so the bolt is a long streak from the sky (test206).
BOLT_SCALE = (1.2, 1.2, 2.0)
ROWS = {31: (22, BOLT_SCALE), 32: (23, 1.4), 33: (23, 1.4), 30: (23, 0.6)}
# BOLT SHAPE (test206, Mat 2026-10-15 evening: "the thunder effects are still not done"; test202's bolt texture on the
# Blade Beam CRESCENT read as a big flat slab). Leaf 22's own meshes (exclusive, asserted) are rewritten in place,
# same vertex count (size-neutral): MDL 30 / 31 -> crossed vertical RIBBONS along local z (the falling strike's
# flight axis, straight down since spot33_thunder) with the bolt texture o12 running along them (bolt = texture u);
# MDL 33 (Ge crescent glow) -> collapsed to one point (zero-area triangles = invisible).
# env BOLT_AXIS=y builds the ribbons along local y instead (bisect switch if z is not the flight axis in game).
RIBBONS = {}                                 # test206 straight ribbons (Mat, test208: "does not look like thunder") -> off
COLLAPSE = (33,)
# test210 (Mat: "Lightning from FF13 has thunder so you don't have to look far"): Lightning's REAL bolt mesh = her MDL 57
# (one 198-vertex strip: a jagged forked bolt along her local y, her bolt texture o06 = Sora o12 already) is written
# into MDL 30 (drawn by leaf 22 node 5, a Sora-native kind-0x100 mesh node -> no foreign node kinds), axes swapped
# y <-> z so the bolt's long axis is the strike's flight axis z (straight down since spot33_thunder), extents (MDL
# +0x40/44/48) scaled by BOLT_EXTENT. It is 640 B bigger than MDL 30 -> MDL 31 (test206 glow ribbon, leaf 22 node 7
# only) SHRUNK to one degenerate triangle; the FEP is padded back to its exact size (asserted).
# Why not her whole THUNDER_BODY tree (test199/200 froze): the only non-native piece in it is node 2 = this bolt,
# node kind 0x150 + component 0x19 (Sora's FEP has neither; component 0x19 = vtable 0x089dc608, a data-only component
# whose init returns 1 -> read by another component's draw code). Bisect pending (needs PPSSPP).
BOLT_SRC, BOLT_DST, BOLT_SHRINK = 57, 30, 31
BOLT_EXTENT = (1.5, 1.5, 2.9)                # x, y, z multipliers of her extents after the swap (z = length)
RIBBON_SEGMENTS = 4
FXSE = {22: None, 23: 77}                    # leaf: slot for the first one-shot (None = all emptied)
BASES = (2200000, 21900000)


def rekey_mdl(data, self_key, keymap):
    d = bytearray(data)
    struct.pack_into('<I', d, 8, self_key)
    for k in range(F.u32(d, 0xc)):
        o = F.u32(d, 0x10) + 0x18 * k
        v = F.u32(d, o)
        struct.pack_into('<I', d, o, keymap.get(v, v))
    return bytes(d)


def rekey_anm(data, self_key, keymap):
    d = bytearray(data)
    struct.pack_into('<I', d, 4, self_key)
    for k in range(F.u32(d, 0x20)):
        o = F.u32(d, 0x30) + 8 * k
        v = F.u32(d, o)
        struct.pack_into('<I', d, o, keymap.get(v, v))
    return bytes(d)


def ribbon_vertices(n, planes, w, col, axis='z'):
    """-> n vertices (u, v, colour, x, y, z) of ONE triangle strip: per plane a quad strip along the long axis
    (-127..127, texture u 0..128), width +-w across (texture v 0..128) at the plane's angle; planes joined by
    degenerate triangles, the rest padded with the last vertex (zero-area)"""
    import math
    out = []
    for deg in planes:
        c, sn = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        strip = []
        for k in range(RIBBON_SEGMENTS + 1):
            t = k / RIBBON_SEGMENTS
            ln, u = max(-127, min(127, round(-127 + 254 * t))), round(128 * t)
            for side, v in ((-1, 0), (1, 128)):
                a, b = round(side * w * c), round(side * w * sn)
                strip.append((u, v, col) + ((a, b, ln) if axis == 'z' else (a, ln, b)))
        if out:
            out += [out[-1], strip[0]]
        out += strip
    assert len(out) <= n, 'ribbon needs %d vertices, MDL has %d' % (len(out), n)
    return out + [out[-1]] * (n - len(out))


def reshape_mdl(blob, idx):
    """RIBBONS / COLLAPSE on one MDL data blob (draw list: u32 count +0x34, table +0x38, rows {prim, vtype, stride,
    ?, n, offset}; vertex = u8 u, u8 v, u16 RGBA4444, s8 x y z, pad). -> True if changed"""
    d = blob.data
    old = bytes(d)
    axis = os.environ.get('BOLT_AXIS', 'z')
    for k in range(F.u32(d, 0x34)):
        prim, vtype, stride, _, cnt, off = struct.unpack_from('<6I', d, F.u32(d, 0x38) + 0x18 * k)
        assert vtype == 0x99 and stride == 8, 'MDL %d: unexpected vertex type %x/%d' % (idx, vtype, stride)
        if idx in RIBBONS and prim == 4:
            vs = ribbon_vertices(cnt, axis=axis, **RIBBONS[idx])
        else:                                       # collapsed MDL, or a triangle list beside the ribbon strip
            vs = [(0, 0, 0, 0, 0, 0)] * cnt
        for j, (u, v, c, x, y, z) in enumerate(vs):
            struct.pack_into('<BBHbbb', d, off + j * stride, u, v, c, x, y, z)
    return bytes(d) != old


def node_kinds(d, leaf):
    t = F.u32(d, F.u32(d, 0x2c) + 4 * T.leaf_tree_index(d, leaf))
    nl = F.u32(d, t + 0x20)
    return [F.u16(d, F.u32(d, nl + 4 * k) + 2) if F.u32(d, nl + 4 * k) else None for k in range(F.u16(d, t + 0x12))]


def edit_fep(sd, ld):
    S, L = F.Fep(sd), F.Fep(ld)
    S.rekey()
    size0 = len(sd)
    base = S.key_base()
    lrec = {k: [F.u32(r.data, 4) for r, _ in L.resources(k)] for k in ('TEX', 'MDL', 'ANM')}
    srec = {k: [F.u32(r.data, 4) for r, _ in S.resources(k)] for k in ('TEX', 'MDL', 'ANM')}
    keymap = {lrec['TEX'][i]: base | j for i, j in TEX_OWN.items()}
    # resources (absolute -> re-runnable)
    for i, j in TEX_OWN.items():
        lt = bytes(L.resources('TEX')[i][1].data[:F.u32(L.resources('TEX')[i][0].data, 8)])
        t = bytearray(lt)
        struct.pack_into('<I', t, 4, base | j)
        k = E.res_index(S, 'TEX', '0x%08x' % (base | j))
        rec, blob = S.resources('TEX')[k]
        assert F.u32(rec.data, 8) == len(t), 'TEX sizes differ'
        if bytes(blob.data[:len(t)]) != bytes(t):
            T.put_resource(S, 'TEX', k, t)
            print('FEP: TEX %08x <- Lightning TEX %d %08x' % (base | j, i, lrec['TEX'][i]))
    for i, j in MDL_OWN.items():
        ld_ = bytes(L.resources('MDL')[i][1].data[:F.u32(L.resources('MDL')[i][0].data, 8)])
        new = rekey_mdl(ld_, srec['MDL'][j], keymap)
        rec, blob = S.resources('MDL')[j]
        if bytes(blob.data[:F.u32(rec.data, 8)]) != new or F.u32(rec.data, 8) != len(new):
            T.put_resource(S, 'MDL', j, new)
            print('FEP: MDL %d (%08x) <- Lightning MDL %d (%d B)' % (j, srec['MDL'][j], i, len(new)))
    for i, j in MDL_GLOBAL.items():
        rec, _ = S.resources('MDL')[j]
        if F.u32(rec.data, 4) != lrec['MDL'][i]:
            struct.pack_into('<II', rec.data, 4, lrec['MDL'][i], 0)
            print('FEP: MDL %d record -> global key %08x (Lightning MDL %d)' % (j, lrec['MDL'][i], i))
    for i, j in ANM_OWN.items():
        la = bytes(L.resources('ANM')[i][1].data[:F.u32(L.resources('ANM')[i][0].data, 8)])
        new = rekey_anm(la, srec['ANM'][j], keymap)
        rec, blob = S.resources('ANM')[j]
        if bytes(blob.data[:F.u32(rec.data, 8)]) != new or F.u32(rec.data, 8) != len(new):
            T.put_resource(S, 'ANM', j, new)
            print('FEP: ANM %d (%08x) <- Lightning ANM %d' % (j, srec['ANM'][j], i))
    for i, j in ANM_GLOBAL.items():
        assert srec['ANM'][j] == lrec['ANM'][i], 'ANM global key mismatch %d/%d' % (i, j)
    # Blade Beam wave meshes -> her bolt texture (exclusive to leaf 22, asserted)
    import collections
    from fep_dump import leaves, resources
    cur = S.write()
    Ls = leaves(cur, resources(cur))
    users = collections.defaultdict(set)
    for lf in Ls:
        for n in lf['nodes']:
            for k, i in F.node_resources(cur, n['at']):
                users[(k, i)].add(lf['i'])
    for i in sorted(BOLT_MDLS):
        assert users[('MDL', i)] <= {22}, 'MDL %d also drawn by %s' % (i, users[('MDL', i)])
        _, blob = S.resources('MDL')[i]
        if F.u32(blob.data, 0x1c) != base | 0x12:
            print('FEP: MDL %d texture %08x -> %08x (Lightning bolt)' % (i, F.u32(blob.data, 0x1c), base | 0x12))
            struct.pack_into('<I', blob.data, 0x1c, base | 0x12)
    # Lightning's bolt mesh -> MDL 30 (axes y <-> z), MDL 31 shrunk (test210)
    if BOLT_SRC is not None:
        assert users[('MDL', BOLT_DST)] <= {22} and users[('MDL', BOLT_SHRINK)] <= {22}
        lb = bytes(L.resources('MDL')[BOLT_SRC][1].data[:F.u32(L.resources('MDL')[BOLT_SRC][0].data, 8)])
        nb = bytearray(rekey_mdl(lb, srec['MDL'][BOLT_DST], keymap))
        assert F.u32(nb, 0x34) == 1
        prim, vtype, stride, _, cnt, off = struct.unpack_from('<6I', nb, F.u32(nb, 0x38))
        assert prim == 4 and vtype == 0x99 and stride == 8
        for j in range(cnt):
            u, v, c, x, y, z = struct.unpack_from('<BBHbbb', nb, off + 8 * j)
            struct.pack_into('<BBHbbb', nb, off + 8 * j, u, v, c, x, z, y)
        ex, ey, ez = struct.unpack_from('<3f', nb, 0x40)
        struct.pack_into('<3f', nb, 0x40, ex * BOLT_EXTENT[0], ez * BOLT_EXTENT[1], ey * BOLT_EXTENT[2])
        rec, blob = S.resources('MDL')[BOLT_DST]
        if bytes(blob.data[:F.u32(rec.data, 8)]) != bytes(nb) or F.u32(rec.data, 8) != len(nb):
            T.put_resource(S, 'MDL', BOLT_DST, bytes(nb))
            print('FEP: MDL %d <- Lightning bolt MDL %d (%d vertices, y<->z, extents x%s, %d B)' % (BOLT_DST, BOLT_SRC, cnt, BOLT_EXTENT, len(nb)))
        rec, blob = S.resources('MDL')[BOLT_SHRINK]
        d31 = bytes(blob.data[:F.u32(rec.data, 8)])
        rows31 = [struct.unpack_from('<6I', d31, F.u32(d31, 0x38) + 0x18 * k) for k in range(F.u32(d31, 0x34))]
        if not (len(rows31) == 1 and rows31[0][4] == 3):
            first = min(r[5] for r in rows31)
            sb = bytearray(d31[:first])                 # header + draw table, vertex data dropped
            struct.pack_into('<I', sb, 0x34, 1)
            struct.pack_into('<6I', sb, F.u32(sb, 0x38), 4, 0x99, 8, 0, 3, first)
            sb += bytes(24)                             # 3 identical vertices = zero-area = invisible
            T.put_resource(S, 'MDL', BOLT_SHRINK, bytes(sb))
            print('FEP: MDL %d shrunk %d -> %d B (one degenerate triangle)' % (BOLT_SHRINK, len(d31), len(sb)))
    for i in sorted(set(RIBBONS) | set(COLLAPSE)):
        assert users[('MDL', i)] <= {22}, 'MDL %d also drawn by %s' % (i, users[('MDL', i)])
        if reshape_mdl(S.resources('MDL')[i][1], i):
            print('FEP: MDL %d -> %s' % (i, 'bolt ribbon %s' % (RIBBONS[i],) if i in RIBBONS else 'collapsed (hidden)'))
    cur = S.write()
    Ls = leaves(cur, resources(cur))
    patched = bytearray(cur)
    for li, remap in LEAF_ANM_REMAP.items():                # per-leaf: only this leaf's own node components
        for n in Ls[li]['nodes']:
            for c, _, o in F.node_components(cur, n['at']):
                if c in (0x0a, 0x15) and o is not None and F.u16(cur, o) in remap:
                    print('FEP: leaf %d node @%#x ANM %d -> %d' % (li, n['at'], F.u16(cur, o), remap[F.u16(cur, o)]))
                    struct.pack_into('<H', patched, o, remap[F.u16(cur, o)])
    if bytes(patched) != cur:
        S = F.Fep(bytes(patched))
    for g in GUT:                                       # empty trees (copies of her 0-node THUNDER_APPER tree)
        if [n for n in leaves(S.write(), resources(S.write()))[g]['nodes']]:
            print('FEP: leaf %d emptied, saved %d B' % (g, T.gut(S, S.write(), g, L, ld, EMPTY_SRC)))
    if len(S.write()) != size0:
        T.pad_to(S, size0)
    new = bytearray(S.write())
    from spot33_burstfx import leaf_ranges, scan
    _, rng = leaf_ranges(bytes(new))
    for li, table in LEAF_COLOURS.items():
        hit = set()
        for o in scan(rng[li]):
            if not (new[o - 4:o] == b'\xcd' * 4 or o - 16 in hit):
                continue
            q = struct.unpack_from('<4f', new, o)
            if not all(0 <= v <= 255 and v == int(v) for v in q):
                continue
            hit.add(o)
            k3 = tuple(int(v) for v in q[:3])
            if k3 in table:
                struct.pack_into('<3f', new, o, *table[k3])
                print('  leaf %d @%#x colour %s -> %s' % (li, o, k3, table[k3]))
    new = bytes(new)
    F.Fep(new)
    assert len(new) == size0, 'FEP size %d != %d' % (len(new), size0)
    return None if new == sd else new


def edit_fepa(feb):
    feb = bytearray(feb)
    rows = {struct.unpack_from('<I', feb, 16 + 0x104 * i + 0x24)[0]: 16 + 0x104 * i
            for i in range(struct.unpack_from('<I', feb, 12)[0])}
    ch = False
    for rid, (leaf, scale) in ROWS.items():
        o = rows[rid]
        xyz = tuple(scale) if isinstance(scale, tuple) else (scale,) * 3
        f32 = struct.unpack('<3f', struct.pack('<3f', *xyz))            # compare as float32 (0.8 != 0.8f)
        if struct.unpack_from('<I', feb, o + 0x28)[0] != leaf or struct.unpack_from('<3f', feb, o + 0x18) != f32:
            struct.pack_into('<I', feb, o + 0x28, leaf)
            struct.pack_into('<3f', feb, o + 0x18, *xyz)
            print('FEPA: row id %d -> leaf %d x%s' % (rid, leaf, xyz))
            ch = True
    return bytes(feb) if ch else None


def edit_fxse(fx, nsnd):
    fx = bytearray(fx)
    ch = False
    for leaf, slot in FXSE.items():
        first = True
        for k in range(16):
            o = 16 + leaf * 0x140 + k * 0x14
            base, s_, fr, _, flags = struct.unpack_from('<5I', fx, o)
            if not base:
                continue
            if slot is not None and first and base in BASES and flags == 0 and slot < nsnd:
                first = False
                if s_ != slot:
                    struct.pack_into('<I', fx, o + 4, slot)
                    print('FXSE: leaf %d record %d slot %d -> %d' % (leaf, k, s_, slot))
                    ch = True
                continue
            fx[o:o + 0x14] = bytes(0x14)
            print('FXSE: leaf %d record %d (base %d slot %d) emptied' % (leaf, k, base, s_))
            ch = True
    return bytes(fx) if ch else None


def main(a):
    iso, clean = a[0], a[1]
    objx = E.load_objx(iso, FILE)
    lobjx = E.load_objx(clean, LIGHT)
    ei, effe, name, sd = E.split(objx)
    ld = E.split(lobjx)[3]
    changed = False
    new = edit_fep(sd, ld)
    if new is not None:
        objx, changed = E.join(objx, ei, effe, name, new), True
    from spot33_fx import patch_member
    from spot33_magicfx import snd_count
    feb = edit_fepa(E.mpk_member(objx, 1))
    if feb is not None:
        objx, changed = patch_member(objx, 1, feb), True
    fx = edit_fxse(E.mpk_member(objx, 2), snd_count(objx))
    if fx is not None:
        objx, changed = patch_member(objx, 2, fx), True
    eff = next(e for e in E.arc_entries(objx) if e[1] == b'effe')
    print('effe chunk %d B' % eff[3])
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
