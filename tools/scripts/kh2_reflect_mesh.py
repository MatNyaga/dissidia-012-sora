"""KH2 Reflega meshes + texture -> native Dissidia MDL / TEX blobs (library for spot33_barrier.py; generalises Codex's
codex/inbox/20261016-reflect-gap/build_shell_prototype.py from model 0 to any REFLECT_3.mag model).

Source: kh2_export/raw/kh2_fifth/original/magic/REFLECT_3.mag (sha256 checked), DPD 0 (21 OMD models, 3 textures).
KH2 programs (pdata 0 = ground Reflega, pdata 2 = the full-sphere variant; tools/scripts/kh2_pax_dump.py) draw model
0/4 (ground dome, 256 tris) and 6/10 (full faceted sphere, 448 tris) with TEX0 at model scale 0.58 / 0.56 (element 2
x1.08); KH2 units = cm, -Y = up.

Native MDL (same header family as Sora's MDL 64/68/70, kind-0xc0 mesh nodes): "MDL\\0", 0x80001, self key, 1 texture,
table +0x1c (texture key), +0x34 1 draw row, +0x38 0x68; +0x40 extents xyz (m), +0x4c centre (0), +0x58 UV scale,
+0x60 UV offset; draw row {3 = triangle list, 0x99 = u8 uv + RGBA4444 + s8 xyz, stride 8, 0, n, 0x80}; vertices at
0x80. u8 UVs are normalised at 128 = 1.0 (Cloud's MDLs), so KH2 texel UVs of a 128x64 texture need UV scale (1, 2).
Geometry is centred on its own y-middle (s8 positions are symmetric around 0); spot33_barrier puts the KH2 offset
into the FEPA row (y_mid_m returned here).
Vertex colour = KH2 colour (128 = 1.0) x tint, premultiplied by its alpha (native materials are additive: Cloud's
own textures are alpha 255 on black and fades live in RGB, notes/kh2-effects.md test155).

  python3 -I kh2_reflect_mesh.py --preview OUT.png     side-by-side: KH2 source (model wireframe + TEX0) | native
                                                       decoded blobs rendered additively (dome + sphere)
"""
import hashlib
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SOURCE = os.path.join(ROOT, 'kh2_export/raw/kh2_fifth/original/magic/REFLECT_3.mag')
SOURCE_SHA = 'f41496e0a19cdb926cd10fe71ea03c9b758ecc9bba948af186c22c0c2e6d78da'
HEAD_0C_40 = bytes.fromhex('01000000' '1c000000' '01000000' '34000000' '00000000'
                           '000000000700000000060a0000000000ffffffff010000006800000000000000')


def _dpd():
    import kh2_pax_dump as K
    d = open(SOURCE, 'rb').read()
    assert hashlib.sha256(d).hexdigest() == SOURCE_SHA, 'REFLECT_3.mag changed'
    p = next(d[o:o + s] for t, _, _, o, s in K.bar(d) if t == 18)
    _, _, x = K.pax_elements(p)
    _, ds = K.dpx_parse(p[x:])
    return ds[0], K.dpd_lists(ds[0])


def source_triangles(model):
    """-> list of corners (x, y, z, r, g, b, a, u, v) in KH2 units, 3 per triangle, winding reversed for the Y flip"""
    D, L = _dpd()
    o = L[3][model]
    pa, va = struct.unpack_from('<2I', D, o + 20)
    vc = struct.unpack_from('<H', D, o + 34)[0]
    vs = [struct.unpack_from('<3h', D, o + 16 + va + 6 * j) for j in range(vc)]
    q = o + 16 + pa
    out = []
    while D[q:q + 2] != b'\xff\xff':
        _, ty, n = struct.unpack_from('<BBH', D, q)
        assert ty in (2, 6), 'primitive type %d' % ty
        nv, stride = (3, 32) if ty == 2 else (4, 40)
        q += 16
        for _ in range(n):
            ix = struct.unpack_from('<%dH' % nv, D, q + 4 * nv)
            uv = struct.unpack_from('<%dH' % (2 * nv), D, q + (20 if nv == 3 else 24))
            c = [(*vs[ix[k]], *D[q + 4 * k:q + 4 * k + 4], uv[2 * k], uv[2 * k + 1]) for k in range(nv)]
            for k in ((0, 2, 1) if nv == 3 else (0, 2, 1, 2, 3, 1)):
                out.append(c[k])
            q += stride
    return out


def texture(index=0, premultiply=True):
    """-> (w, h, linear indices, RGBA palette) of KH2 TEX index (alpha x2 once, like fep_edit.from_kh2)"""
    import fep_edit as E
    w, h, idx, pal = E.from_kh2(SOURCE + ':0:%d' % index)
    return w, h, idx, (E.premultiply(pal) if premultiply else pal)


def facet_uvs(model):
    """-> per corner (u, v) in 0..1: every source face (quad = 6 corners, triangle = 3) spans the whole texture"""
    D, L = _dpd()
    o = L[3][model]
    pa = struct.unpack_from('<I', D, o + 20)[0]
    q, sizes = o + 16 + pa, []
    while D[q:q + 2] != b'\xff\xff':
        _, ty, n = struct.unpack_from('<BBH', D, q)
        sizes += [3 if ty == 2 else 6] * n
        q += 16 + n * (32 if ty == 2 else 40)
    corners, out, k = source_triangles(model), [], 0
    for z in sizes:
        f = corners[k:k + z]
        lo = [min(c[7 + a] for c in f) for a in range(2)]
        hi = [max(c[7 + a] for c in f) for a in range(2)]
        out += [tuple((c[7 + a] - lo[a]) / ((hi[a] - lo[a]) or 1) for a in range(2)) for c in f]
        k += z
    assert k == len(corners)
    return out


def build_mdl(model, model_scale, tint=(1.0, 1.0, 1.0), tex_w=128, tex_h=64, self_key=0, tex_key=0, uv='source'):
    """-> (MDL bytes, info dict). model_scale = KH2 program scale (x element scale); output in metres.
    uv='source': KH2 texel UVs (KH2 scrolls them over time: static they light only the facets under the TEX0 streak);
    uv='facet': each source face mapped once over the whole texture (used with TEX1 = KH2's cyan panel gradient)"""
    corners = source_triangles(model)
    fuv = facet_uvs(model) if uv == 'facet' else None
    s = model_scale * 0.01
    pts = [(c[0] * s, -c[1] * s, c[2] * s) for c in corners]
    ymid = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
    pts = [(x, y - ymid, z) for x, y, z in pts]
    ext = [max(abs(p[a]) for p in pts) or 1.0 for a in range(3)]
    periods = (tex_w * 16, tex_h * 16)
    base = [min(c[7 + a] for c in corners) // periods[a] * periods[a] for a in range(2)]
    div = [1, 1]                                       # texel UVs beyond u8 -> store texel / k, UV scale x k
    for a in range(2):
        while max((c[7 + a] - base[a]) / 16 for c in corners) / div[a] > 255:
            div[a] *= 2
    head = bytearray(b'MDL\0' + struct.pack('<II', 0x80001, self_key)) + HEAD_0C_40
    struct.pack_into('<I', head, 0x1c, tex_key)
    if fuv:
        div = [tex_w / 128.0, tex_h / 128.0]           # u8 128 = 1.0 -> UV scale 1
    head += struct.pack('<10f', *ext, 0, 0, 0, 128.0 / tex_w * div[0], 128.0 / tex_h * div[1], 0, 0)
    head += struct.pack('<6I', 3, 0x99, 8, 0, len(corners), 0x80)
    head += b'\0' * 0                                  # header ends at 0x80
    assert len(head) == 0x80
    body = bytearray()
    err = 0.0
    for j, (c, p) in enumerate(zip(corners, pts)):
        uv = ([round(fuv[j][a] * 128) for a in range(2)] if fuv else
              [round((c[7 + a] - base[a]) / 16 / div[a]) for a in range(2)])
        assert all(0 <= t <= 255 for t in uv), 'UV out of u8 range %s' % uv
        a = min(255, c[6] * 2) / 255.0
        rgb = [min(255, c[3 + k] * 2) * tint[k] * a for k in range(3)]
        col = [min(15, round(v / 17)) for v in rgb] + [min(15, round(a * 255 / 17))]
        xyz = [max(-127, min(127, round(p[k] / ext[k] * 127))) for k in range(3)]
        err = max(err, max(abs(p[k] - xyz[k] / 127 * ext[k]) for k in range(3)))
        body += struct.pack('<BBHbbbB', uv[0], uv[1], sum(v << (4 * k) for k, v in enumerate(col)), *xyz, 0)
    mdl = bytes(head + body)
    assert len(mdl) == 0x80 + 8 * len(corners)
    return mdl, dict(model=model, triangles=len(corners) // 3, bytes=len(mdl), extents_m=ext, y_mid_m=ymid,
                     max_quant_err_m=err, uv_base=base, uv_div=div, uv=uv)


MAX_VERTS = 384      # hard budget per MDL (test250-252 froze with 768/1344-vertex lists; every original Sora MDL
#                      is <= 454 vertices, the largest triangle LIST 384 = MDL 41) -- notes/kh2-effects.md "Vertex budget"


def source_bands(model):
    """-> (positions [(x, y, z) KH2 units], bands [[quad (i0, i1, i2, i3) strip order], ...]): the KH2 quad list is
    already in quad-strip order; a band = a maximal run of consecutive quads sharing an edge"""
    D, L = _dpd()
    o = L[3][model]
    pa, va = struct.unpack_from('<2I', D, o + 20)
    vc = struct.unpack_from('<H', D, o + 34)[0]
    vs = [struct.unpack_from('<3h', D, o + 16 + va + 6 * j) for j in range(vc)]
    q, quads = o + 16 + pa, []
    while D[q:q + 2] != b'\xff\xff':
        _, ty, n = struct.unpack_from('<BBH', D, q)
        assert ty == 6, 'model %d: primitive type %d (strip builder needs quads)' % (model, ty)
        q += 16
        for _ in range(n):
            quads.append(struct.unpack_from('<4H', D, q + 16))
            q += 40
    bands, prev = [[quads[0]]], None
    for a, b in zip(quads, quads[1:]):
        sh = set(a) & set(b)
        if len(sh) == 2 and not (prev and prev & sh):   # continues straight through quad a
            bands[-1].append(b)
            prev = sh
        else:                                            # no shared edge, or the run turns inside quad a
            bands.append([b])
            prev = None
    return vs, bands


def band_rails(band):
    """-> edges [(rail A vertex, rail B vertex)] * (len(band) + 1) walking the band quad by quad"""
    per = lambda f: [f[0], f[1], f[3], f[2]]           # strip order -> perimeter
    nb = lambda p, x, other: next(v for v in (p[(p.index(x) + 1) % 4], p[p.index(x) - 1]) if v != other)
    p0 = per(band[0])
    if len(band) > 1:
        x, y = sorted(set(band[0]) & set(band[1]), key=p0.index)
    else:
        x, y = p0[0], p0[1]
    a0, b0 = nb(p0, x, y), nb(p0, y, x)                 # edge opposite the exit edge, rails kept
    edges, cur = [(a0, b0)], (a0, b0)
    for k, f in enumerate(band):
        p = per(f)
        a, b = cur
        cur = (nb(p, a, b), nb(p, b, a))
        if k + 1 < len(band):
            assert set(cur) == set(band[k]) & set(band[k + 1]), 'band walk lost the shared edge'
        edges.append(cur)
    return edges


def boundary_loops(bands):
    """-> closed loops [[vertex index, ...]] of the edges used by exactly one facet of these bands"""
    import collections
    cnt = collections.Counter()
    for b in bands:
        for f in b:
            p = [f[0], f[1], f[3], f[2]]
            for k in range(4):
                cnt[frozenset((p[k], p[(k + 1) % 4]))] += 1
    nb = collections.defaultdict(list)
    for e, c in cnt.items():
        if c == 1:
            x, y = tuple(e)
            nb[x].append(y)
            nb[y].append(x)
    assert all(len(v) == 2 for v in nb.values()), 'boundary is not a set of simple loops'
    loops, seen = [], set()
    for st in nb:
        if st in seen:
            continue
        loop, prev, cur = [st], None, st
        seen.add(st)
        while True:
            nxt = next(v for v in nb[cur] if v != prev)
            if nxt == st:
                break
            loop.append(nxt)
            seen.add(nxt)
            prev, cur = cur, nxt
        loops.append(loop)
    return loops


def cap_strip(vs, loop, pole, mode='full'):
    """pole cap over one boundary loop = a FAN around a new pole vertex (index `pole`, < 0): the KH2 holes are
    16-pointed stars (tips and notches alternate in radius), which a zigzag would fold over; a fan around the axis is
    exact for a star. Strip encoding of a fan (no duplicated triangles): L0 P L1 L2 | L2 P L3 L4 | L4 P L5 L6 ...
    (one triangle per loop edge + 2 degenerate per 2 edges = ~2 vertices per loop vertex). mode 'tips': fan over the
    outer tips only (half the vertices): still covers the whole hole in projection, the notch facets sit just inside.
    UV = planar x/z over the whole texture, pole at the centre. -> [(vertex index, u, v)]"""
    import math
    rad = lambda i: math.hypot(vs[i][0], vs[i][2])
    if mode == 'tips':
        n = len(loop)
        loop = [loop[k] for k in range(n) if rad(loop[k]) >= max(rad(loop[k - 1]), rad(loop[(k + 1) % n]))]
        assert len(loop) * 2 == n, 'loop is not an alternating star (%d tips of %d)' % (len(loop), n)
    xs, zs = [vs[i][0] for i in loop], [vs[i][2] for i in loop]
    uv = lambda i: (64, 64) if i < 0 else (round((vs[i][0] - min(xs)) / ((max(xs) - min(xs)) or 1) * 128),
                                           round((vs[i][2] - min(zs)) / ((max(zs) - min(zs)) or 1) * 128))
    L = loop + loop[:1]
    seq = [L[0], pole, L[1]]
    for k in range(1, len(L) - 1):
        seq += [L[k + 1]] if k % 2 else [L[k], pole, L[k + 1]]
    want = {frozenset((pole, L[k], L[k + 1])) for k in range(len(L) - 1)}
    got = [frozenset(seq[k:k + 3]) for k in range(len(seq) - 2) if len(set(seq[k:k + 3])) == 3]
    assert set(got) == want and len(got) == len(want), 'fan strip'
    return [(i,) + uv(i) for i in seq], loop


def build_strip_mdl(model, model_scale, tint=(1.0, 1.0, 1.0), self_key=0, tex_key=0, min_band_y=None,
                    max_verts=MAX_VERTS, caps=()):
    """-> (MDL bytes, info): ONE triangle strip (prim 4, like Sora's original MDLs) over the KH2 quad bands, bands
    joined by degenerate pairs (the part's cull flag is 0, so winding does not matter). UVs: every facet spans the
    whole texture (KH2 maps each facet separately too); u alternates 0/1 per edge along a band (mirrored facets) so
    neighbouring facets share their vertices. min_band_y (KH2 units, up): drop bands whose mean height is below it.
    caps = {'top': 'full' | 'tips', 'bottom': ...}: close the highest / lowest boundary loop of the kept facets with a
    pole fan (cap_strip; the KH2 sphere itself is open at both poles: KH2 hides the holes with other layers, at Dissidia
    scale x4 they show). The poles sit on the sphere (radius = farthest model vertex) -> shallow cones."""
    vs, bands = source_bands(model)
    s = model_scale * 0.01
    up = lambda i: -vs[i][1]
    ymid_k = (min(up(i) for i in range(len(vs))) + max(up(i) for i in range(len(vs)))) / 2   # full model: KH2 place
    kept, dropped = [], []
    for b in bands:
        my = sum(up(i) for f in b for i in f) / (4 * len(b))
        (kept if min_band_y is None or my >= min_band_y else dropped).append(b)
    def band_strip(b, exact):
        """facet j between edges e_j and e_(j+1): emitted in orientation o (0 = rail A first) the strip splits it
        along (second of e_j) - (first of e_(j+1)); KH2 splits along i1 - i2. exact: repeat the second-last vertex to
        flip the orientation wherever KH2's diagonal changes (one degenerate triangle each); else one orientation for
        the whole band (the one matching most facets). -> (strip part, facets with KH2's diagonal)"""
        e = band_rails(b)
        ab = lambda j, o: (e[j][o], e[j][1 - o])
        want = lambda j, o: {ab(j, o)[1], ab(j + 1, o)[0]} == {b[j][1], b[j][2]}
        uvs = lambda j, o: [(ab(j, o)[k], (j % 2) * 128, (o ^ k) * 128) for k in range(2)]   # v by rail, u by edge
        if exact:
            o = 0 if want(0, 0) else 1
        else:
            o = max((0, 1), key=lambda oo: sum(want(j, oo) for j in range(len(b))))
        part, ok = uvs(0, o), 0
        for j in range(len(b)):
            if exact and not want(j, o):
                part.append(part[-2])
                o ^= 1
            ok += want(j, o)
            part += uvs(j + 1, o)
        return part, ok
    import math
    caps = {k: 'full' for k in caps} if isinstance(caps, (tuple, list)) else dict(caps)
    assert set(caps) <= {'top', 'bottom'} and set(caps.values()) <= {'full', 'tips'}, caps
    loops = sorted(boundary_loops(kept), key=lambda lp: sum(up(i) for i in lp) / len(lp))
    radius = max(math.sqrt(x * x + y * y + z * z) for x, y, z in vs)
    poles = {-1: (0, -radius, 0), -2: (0, radius, 0)}  # KH2 -Y = up: -1 = top pole, -2 = bottom pole
    cap_loops, cap_parts = [], []
    for name, lp, pole in (('top', loops[-1], -1), ('bottom', loops[0], -2)):
        if name in caps:
            part, used = cap_strip(vs, lp, pole, caps[name])
            cap_loops.append((name, caps[name], used))
            cap_parts.append(part)
    vsx = lambda i: poles[i] if i < 0 else vs[i]
    plans = {id(b): band_strip(b, False) for b in kept}
    total = lambda: (sum(len(plans[id(b)][0]) for b in kept) + sum(map(len, cap_parts))
                     + 2 * (len(kept) + len(cap_parts) - 1))
    for b in sorted(kept, key=lambda bb: -sum(up(i) for f in bb for i in f) / len(bb)):   # top bands first
        old = plans[id(b)]
        plans[id(b)] = band_strip(b, True)
        if total() > max_verts:
            plans[id(b)] = old
    real = lambda seq: [frozenset(x[0] for x in seq[k:k + 3]) for k in range(len(seq) - 2)
                        if len({x[0] for x in seq[k:k + 3]}) == 3]
    quads = {frozenset(f) for bb in kept for f in bb}
    ring_tris = [t for b in kept for t in real(plans[id(b)][0])]
    covered = {q for q in quads for t in ring_tris if t <= q}
    assert covered == quads and len(ring_tris) == 2 * len(quads), 'model %d strip: %d of %d facets, %d triangles' % (
        model, len(covered), len(quads), len(ring_tris))
    for b in kept:                                       # every facet triangle spans one facet's full texture
        part = plans[id(b)][0]
        for k in range(len(part) - 2):
            t = part[k:k + 3]
            if len({x[0] for x in t}) == 3:
                assert {x[1] for x in t} == {0, 128} and {x[2] for x in t} == {0, 128}, 'facet UV'
    for (_, _, used), part in zip(cap_loops, cap_parts):
        assert len(real(part)) == len(used), 'cap'
    strip, diag_ok, diag_all = [], 0, 0                  # (vertex index, u, v)
    for part, ok, nq in [plans[id(b)] + (len(b),) for b in kept] + [(c, 0, 0) for c in cap_parts]:
        diag_ok, diag_all = diag_ok + ok, diag_all + nq
        if strip:
            strip += [strip[-1], part[0]]
        strip += part
    assert len(strip) <= max_verts, 'model %d strip has %d vertices > budget %d' % (model, len(strip), max_verts)
    assert len(real(strip)) >= len(ring_tris) + sum(len(u) for _, _, u in cap_loops)
    pts = {i: (vsx(i)[0] * s, (-vsx(i)[1] - ymid_k) * s, vsx(i)[2] * s) for i, _, _ in strip}
    ext = [max(abs(p[a]) for p in pts.values()) or 1.0 for a in range(3)]
    head = bytearray(b'MDL\0' + struct.pack('<II', 0x80001, self_key)) + HEAD_0C_40
    struct.pack_into('<I', head, 0x1c, tex_key)
    head += struct.pack('<10f', *ext, 0, 0, 0, 1.0, 1.0, 0, 0)
    head += struct.pack('<6I', 4, 0x99, 8, 0, len(strip), 0x80)
    assert len(head) == 0x80
    rgb = [min(255, 255 * tint[k]) for k in range(3)]   # KH2 vertex colour 128 (= 1.0) on every corner, alpha 1
    col = sum(v << (4 * k) for k, v in enumerate([min(15, round(c / 17)) for c in rgb] + [15]))
    body, err = bytearray(), 0.0
    for i, u, v in strip:
        p = pts[i]
        xyz = [max(-127, min(127, round(p[k] / ext[k] * 127))) for k in range(3)]
        err = max(err, max(abs(p[k] - xyz[k] / 127 * ext[k]) for k in range(3)))
        body += struct.pack('<BBHbbbB', u, v, col, *xyz, 0)
    mdl = bytes(head + body)
    return mdl, dict(model=model, quads=sum(len(b) for b in kept), quads_dropped=sum(len(b) for b in dropped),
                     bands=len(kept), vertices=len(strip), bytes=len(mdl), extents_m=ext,
                     kh2_diagonals='%d/%d' % (diag_ok, diag_all),
                     caps=[(nm, md, len(u), len(pt)) for (nm, md, u), pt in zip(cap_loops, cap_parts)],
                     open_loops=len(loops) - len(cap_loops),
                     y_mid_m=ymid_k * s, max_quant_err_m=err)


def decode_mdl(mdl):
    """-> (triangles [(xyz, uv, rgba)*3], uv scale, uv offset) of a native MDL (for previews / checks)"""
    ext = struct.unpack_from('<3f', mdl, 0x40)
    us = struct.unpack_from('<2f', mdl, 0x58)
    uo = struct.unpack_from('<2f', mdl, 0x60)
    tris = []
    for k in range(struct.unpack_from('<I', mdl, 0x34)[0]):
        prim, vt, st, _, n, off = struct.unpack_from('<6I', mdl, struct.unpack_from('<I', mdl, 0x38)[0] + 0x18 * k)
        vs = []
        for j in range(n):
            u, v, c, x, y, z = struct.unpack_from('<BBHbbb', mdl, off + st * j)
            vs.append(((x / 127 * ext[0], y / 127 * ext[1], z / 127 * ext[2]),
                       (u / 128 * us[0] + uo[0], v / 128 * us[1] + uo[1]),
                       tuple(((c >> (4 * i)) & 15) * 17 for i in range(4))))
        if prim == 3:
            tris += [vs[i:i + 3] for i in range(0, n - 2, 3)]
        else:
            tris += [vs[i:i + 3] for i in range(n - 2)]
    return tris


def render(tris, tex, size=360, yaw=30.0, pitch=15.0, scale=None, wire=False, centre=(0.0, 0.0), marker=None):
    """tiny additive rasteriser (per-pixel interpolated UV, wrapped texture x vertex colour) -> PIL image.
    centre = (x, y) of the view centre in metres; marker = (height m, x m): a vertical white bar (Sora's height)"""
    from PIL import Image, ImageDraw
    w, h, idx, pal = tex
    im = Image.new('RGB', (size, size), (12, 16, 24))
    acc = [[0.0, 0.0, 0.0] for _ in range(size * size)]
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    allp = [p for t in tris for p, _, _ in t]
    r = scale or max(max(abs(c) for c in p) for p in allp) * 1.15

    def proj(p):
        x, y, z = p[0], p[1], p[2]
        x, z = x * cy - z * sy, x * sy + z * cy
        y, z = y * cp - z * sp, y * sp + z * cp
        return (size / 2 + (x - centre[0]) / r * size / 2, size / 2 - (y - centre[1]) / r * size / 2)
    dr = ImageDraw.Draw(im)
    if wire:
        for t in tris:
            q = [proj(p) for p, _, _ in t]
            dr.line(q + [q[0]], fill=(90, 200, 230), width=1)
        return im
    for t in tris:
        q = [proj(p) for p, _, _ in t]
        (ax, ay), (bx, by), (qx, qy) = q
        den = (by - qy) * (ax - qx) + (qx - bx) * (ay - qy)
        if abs(den) < 1e-9:
            continue
        vc = [sum(x[2][k] for x in t) / 3 / 255 for k in range(3)]
        xs, ys = [a for a, _ in q], [b for _, b in q]
        x0, x1 = int(max(0, min(xs))), int(min(size - 1, max(xs)))
        y0, y1 = int(max(0, min(ys))), int(min(size - 1, max(ys)))
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                l1 = ((by - qy) * (xx - qx) + (qx - bx) * (yy - qy)) / den
                l2 = ((qy - ay) * (xx - qx) + (ax - qx) * (yy - qy)) / den
                l3 = 1 - l1 - l2
                if l1 >= 0 and l2 >= 0 and l3 >= 0:
                    u = (l1 * t[0][1][0] + l2 * t[1][1][0] + l3 * t[2][1][0]) % 1.0
                    v = (l1 * t[0][1][1] + l2 * t[1][1][1] + l3 * t[2][1][1]) % 1.0
                    ti = idx[min(h - 1, int(v * h)) * w + min(w - 1, int(u * w))]
                    a = acc[yy * size + xx]
                    for k in range(3):
                        a[k] += pal[4 * ti + k] * vc[k] * 0.45
    px = im.load()
    for yy in range(size):
        for xx in range(size):
            a = acc[yy * size + xx]
            if a[0] or a[1] or a[2]:
                b = px[xx, yy]
                px[xx, yy] = tuple(min(255, int(b[k] + a[k])) for k in range(3))
    if marker:
        hgt, mx = marker
        p0, p1 = proj((mx, 0.0, 0.0)), proj((mx, hgt, 0.0))
        dr.line([p0, p1], fill=(255, 255, 255), width=3)
        dr.line([proj((-50, 0.0, 0.0)), proj((50, 0.0, 0.0))], fill=(120, 90, 60), width=1)   # floor
    return im


def disc_texture(iso, index):
    """-> (w, h, linear indices, palette) of Sora's own FEP texture INDEX on a disc (what the shells draw with when
    no TEX 21 is added)"""
    import fep as F
    import fep_edit as E
    from fep_dump import unswizzle
    f = F.Fep(E.split(E.load_objx(iso, 'obj/p_sev120.objx'))[3])
    rec, blob = f.resources('TEX')[index]
    x = bytes(blob.data[:F.u32(rec.data, 8)])
    w, h = struct.unpack_from('<II', x, 0x1c)
    return w, h, unswizzle(x[0x30:0x30 + w * h], w, h), x[0x30 + w * h + 0x10:0x30 + w * h + 0x410]


def preview(out, layers, tex_index=1, row_scale=1.0, root_h=0.85, tex=None, tex_label=None):
    """layers = [(label, model, MDL bytes, info, row offset (m))] -> sheet per layer: KH2 source wireframe | native
    strip (decoded, textured, additive) | side view at game scale (row scale, offset; floor line + 1.5 m bar)"""
    from PIL import Image, ImageDraw
    tex = tex or texture(tex_index, premultiply=True)
    tex_label = tex_label or 'KH2 TEX%d per facet' % tex_index
    cell = 360
    sheet = Image.new('RGB', (cell * 3, cell * len(layers) + 30), (8, 10, 14))
    dr = ImageDraw.Draw(sheet)
    for row, (label, model, mdl, info, pos) in enumerate(layers):
        src = source_triangles(model)
        st = [[((c[0], -c[1], c[2]), (0, 0), (255,) * 4) for c in src[i:i + 3]] for i in range(0, len(src), 3)]
        tris = decode_mdl(mdl)
        sheet.paste(render(st, tex, cell, wire=True), (0, 30 + row * cell))
        sheet.paste(render(tris, tex, cell), (cell, 30 + row * cell))
        y0 = root_h + pos[1]                            # model origin above the feet
        game = [[((p[0] * row_scale, p[1] * row_scale + y0, p[2] * row_scale), uv, c) for p, uv, c in t] for t in tris]
        top = max(p[1] for t in game for p, _, _ in t)
        bot = min(0.0, min(p[1] for t in game for p, _, _ in t))
        half = max(max(abs(p[0]) for t in game for p, _, _ in t), (top - bot) / 2) * 1.1
        sheet.paste(render(game, tex, cell, yaw=0, pitch=0, scale=half, centre=(0.0, (top + bot) / 2),
                           marker=(1.5, 0.0)), (2 * cell, 30 + row * cell))
        dr.text((6, 34 + row * cell), 'KH2 source model %d (all %d facets)' % (model, len(src) // 6), fill='white')
        dr.text((cell + 6, 34 + row * cell), '%s: %d facets+%d cap(s), strip %d verts' % (
            label, info['quads'], len(info.get('caps', ())), info['vertices']), fill='white')
        dr.text((2 * cell + 6, 34 + row * cell), 'side view x%.1f, floor + 1.5 m bar (Sora)' % row_scale, fill='white')
    dr.text((6, 8), 'Offline preview (%s, additive). No game shader/refraction/animation/runtime check.'
            % tex_label, fill='white')
    sheet.save(out)
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    if '--preview' in a:
        import spot33_barrier as B
        ls = []
        for name, spec in B.LAYERS.items():
            mdl, info = B.layer_mdl(spec)
            ls.append((name, spec['model'], mdl, info, B.row_pos(spec, info)))
        i = a.index('--preview')
        iso = a[i + 2] if len(a) > i + 2 else None        # disc: draw with its TEX 9 (in-game texture, no TEX 21)
        tex = None if (B.NEW_TEX_ON or not iso) else disc_texture(iso, 9)
        print(preview(a[i + 1], ls, B.SHELL_TEX, B.ROW_SCALE, B.ROOT_H, tex,
                      None if tex is None else 'disc TEX 9 per facet (no TEX 21)'))
    else:
        import spot33_barrier as B
        for name, spec in B.LAYERS.items():
            print(name, B.layer_mdl(spec)[1])
