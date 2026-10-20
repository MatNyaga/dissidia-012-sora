"""KH2 Magnet Burst / Magnet (Magnega) meshes + texture -> native Dissidia MDL / TEX blobs (library for
spot33_magnet.py; same MDL family as kh2_reflect_mesh.py / spot33_barrier.py). notes/kh2-effects.md "Magnet Burst".

KH2 sources (sha256 checked):
  P_EX100.a.us (KH2FM Sora attack effects) PAX elements 51 (Magnet Burst vortex, motion 788 f8, chest 1.27 m up, loops
  while the motion runs) / 52 (the burst, f31). DPD 3 model 27 = the star-shaped SWIRL DISC (48 verts, 3 rings x 16,
  drawn with DPD 3 tex 5 = the Magnet swirl streaks), model 35 = flat burst ring.
  magic/MAGNET_3.mag (Magnega) element 3 = the gravity orb: model 9 (= model 27, same swirl disc), model 10 = the
  spinning RING BAND (cylinder r 800, h +-97, warm/cool vertex colours alternating), tex 0 = the swirl streaks
  (byte-identical to P_EX100 DPD 3 tex 5).
Native look (static meshes; KH2's billboards / UV scroll / colour keys are not reproducible yet):
  ORB  MDL = two nested spheres wrapped with the KH2 swirl texture (stand-in for KH2's camera-facing orb sprites:
       a billboard always looks round, a sphere does too), inner white-pink core, outer magenta shell.
  RING MDL = KH2 swirl disc (model 27, KH2's own UVs on the KH2 texture) laid flat + KH2 ring band (model 10) at
       its rim = one "vortex ring". spot33_magnet spawns it shrinking (pull-in) and growing (burst).
Both = ONE triangle strip (prim 4) <= 384 vertices (kh2_reflect_mesh.MAX_VERTS). Radius 1 m in the MDL; the FEPA
row scale = radius in metres. Vertex colour = Magnet pink/purple/white, premultiplied (additive materials).

  python3 -I kh2_magnet_mesh.py --preview OUT.png        KH2 source vs native meshes (KH2 texture)
"""
import hashlib
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kh2_reflect_mesh as M  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SRC_EX = (os.path.join(ROOT, 'kh2_export/raw/kh2_sixth/original/obj/P_EX100.a.us'),
          'ddbb877b6d02dedcabb4ae5652b2d18ca9153e333dafe1de427a4b86459b419c')
SRC_MAG = (os.path.join(ROOT, 'kh2_export/raw/kh2_fifth/original/magic/MAGNET_3.mag'),
           '8d98edbd872c92b55ea4ab9556a6af8d9bdc2aee59879c49afaea9cd3952605a')
DISC = (SRC_EX, 3, 27)          # Magnet Burst swirl disc (= MAGNET_3 model 9)
BAND = (SRC_MAG, 0, 10)         # Magnega ring band
TEX = (SRC_MAG, 0, 0)           # Magnet swirl streaks (= P_EX100 DPD 3 tex 5)
MAX_VERTS = M.MAX_VERTS
OPACITY = float(os.environ.get('MAGNET_OPACITY', '1.0'))
# KH2 brightens this dim streak texture with layer colours > 128 and many stacked additive layers; one static native
# layer needs the texels lifted: premultiplied value -> 255 * (v / 255) ** TEX_GAMMA * TEX_GAIN (clamped)
TEX_GAIN, TEX_GAMMA = float(os.environ.get('MAGNET_TEX_GAIN', '1.6')), 0.7
# Magnet colours (0-255, before premultiply). Mat: "purple-pink-white"
CORE, SHELL = (255, 225, 250), (200, 90, 235)          # orb inner / outer sphere
DISC_IN, DISC_OUT = (255, 220, 250), (215, 105, 235)    # swirl disc centre -> rim (rim alpha 0 = KH2's soft edge)
BAND_WARM, BAND_COOL = (255, 130, 215), (150, 110, 255)  # KH2 band alternates warm/cool -> pink/violet
DISC_GAIN, BAND_GAIN, CORE_GAIN, SHELL_GAIN = 0.9, 0.8, 0.85, 0.55
_cache = {}


def _dpd(src, k):
    path, sha = src
    if (path, k) not in _cache:
        import kh2_pax_dump as K
        d = open(path, 'rb').read()
        assert hashlib.sha256(d).hexdigest() == sha, '%s changed' % path
        p = next(d[o:o + s] for t, _, _, o, s in K.bar(d) if t == 18)
        _, _, x = K.pax_elements(p)
        _, ds = K.dpx_parse(p[x:])
        _cache[(path, k)] = (ds[k], K.dpd_lists(ds[k]))
    return _cache[(path, k)]


def kh2_model(spec):
    """-> (vertices [(x, y, z) KH2 cm, -Y up], quads [((i0, i1, i2, i3) strip order, [(u, v)] * 4 (0..1 texture),
    [(r, g, b, a) 128 = 1.0] * 4)])"""
    src, k, m = spec
    D, L = _dpd(src, k)
    o = L[3][m]
    pa, va = struct.unpack_from('<2I', D, o + 20)
    vc = struct.unpack_from('<H', D, o + 34)[0]
    vs = [struct.unpack_from('<3h', D, o + 16 + va + 6 * j) for j in range(vc)]
    q, quads = o + 16 + pa, []
    while D[q:q + 2] != b'\xff\xff':
        _, ty, n = struct.unpack_from('<BBH', D, q)
        assert ty == 6, 'model %d: primitive type %d (quads only)' % (m, ty)
        q += 16
        for _ in range(n):
            ix = struct.unpack_from('<4H', D, q + 16)
            uv = struct.unpack_from('<8H', D, q + 24)
            quads.append((ix, [((uv[2 * j] - 4096) / 4096.0, (uv[2 * j + 1] - 4096) / 4096.0) for j in range(4)],
                          [tuple(D[q + 4 * j:q + 4 * j + 4]) for j in range(4)]))
            q += 40
    return vs, quads


def texture():
    """-> (w, h, linear indices, premultiplied palette) = KH2 Magnet swirl streaks (128x64 CLUT8)"""
    import fep_edit as E
    src, k, t = TEX
    _dpd(src, k)                                      # sha check
    w, h, idx, pal = E.from_kh2('%s:%d:%d' % (src[0], k, t))
    assert (w, h) == (128, 64)
    p = bytearray(E.premultiply(pal))
    for i in range(256):
        for c in range(3):
            p[4 * i + c] = min(255, round(255 * (p[4 * i + c] / 255.0) ** TEX_GAMMA * TEX_GAIN))
    return w, h, idx, bytes(p)


def _bands(quads):
    """split a KH2 quad list (quad-strip ordered) into bands = runs of quads sharing an edge (kh2_reflect_mesh logic)"""
    fs = [q[0] for q in quads]
    bands, prev = [[0]], None
    for j in range(1, len(fs)):
        sh = set(fs[j - 1]) & set(fs[j])
        if len(sh) == 2 and not (prev and prev & sh):
            bands[-1].append(j)
            prev = sh
        else:
            bands.append([j])
            prev = None
    return bands


def _vertex_uv(quads):
    uv = {}
    for ix, uvs, _ in quads:
        for i, t in zip(ix, uvs):
            assert uv.setdefault(i, t) == t, 'vertex %d has two UVs' % i
    return uv


def _vertex_col(quads):
    col = {}
    for ix, _, cs in quads:
        for i, c in zip(ix, cs):
            col.setdefault(i, c)
    return col


def _lerp(a, b, t):
    return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))


def disc_part(radius=1.0):
    """KH2 swirl disc (model 27) flat in x/z, KH2 UVs; -> strip [(xyz m, (u, v), (r, g, b, alpha 0..1))]"""
    vs, quads = kh2_model(DISC)
    uv, col = _vertex_uv(quads), _vertex_col(quads)
    rmax = max(math.hypot(v[0], v[1]) for v in vs)
    out = []
    for band in _bands(quads):
        edges = M.band_rails([quads[j][0] for j in band])
        part = []
        for a, b in edges:
            for i in (a, b):
                x, y, _ = vs[i]
                r = math.hypot(x, y) / rmax
                al = col[i][3] / 128.0                # KH2 alpha: rim 0 (soft edge), inner 0.5-1
                rgb = _lerp(DISC_IN, DISC_OUT, min(1.0, r * 1.25))
                part.append(((x / rmax * radius, 0.0, -y / rmax * radius), uv[i], rgb, min(1.0, al) * DISC_GAIN))
        out.append(part)
    return out


def band_part(radius=1.0, height=None, repeat=1.0):
    """KH2 ring band (model 10) at the disc rim; UV u = around (repeat), v = across; KH2 warm/cool alternation"""
    vs, quads = kh2_model(BAND)
    col = _vertex_col(quads)
    rmax = max(math.hypot(v[0], v[2]) for v in vs)
    ymax = max(abs(v[1]) for v in vs)
    h = height if height is not None else ymax / rmax * radius
    out = []
    for band in _bands(quads):
        edges = M.band_rails([quads[j][0] for j in band])
        part = []
        for j, (a, b) in enumerate(edges):
            for i in (a, b):
                x, y, z = vs[i]
                warm = col[i][0] > col[i][2]
                rgb = BAND_WARM if warm else BAND_COOL
                edge = abs(y) / ymax                   # 0 middle row, 1 top/bottom rows
                al = (1.0 - 0.65 * edge) * BAND_GAIN
                part.append(((x / rmax * radius, -y / ymax * h, z / rmax * radius),
                             (j / (len(edges) - 1) * repeat, 0.5 - 0.5 * (-y / ymax)), rgb, al))
        out.append(part)
    return out


def sphere_part(radius, rgb, alpha, seg=12, rings=6, u_repeat=1.0):
    """UV sphere as one strip (latitude bands joined by degenerates); KH2 swirl texture wrapped around"""
    out = []
    for i in range(rings):
        part = []
        for s in range(seg + 1):
            for la in (i, i + 1):
                th, ph = math.pi * la / rings, 2 * math.pi * s / seg
                p = (radius * math.sin(th) * math.cos(ph), radius * math.cos(th), radius * math.sin(th) * math.sin(ph))
                part.append((p, (s / seg * u_repeat, la / rings), rgb, alpha))
        out.append(part)
    return out


def join(parts):
    strip = []
    for p in parts:
        if strip:
            strip += [strip[-1], p[0]]
        strip += p
    return strip


def encode(strip, self_key, tex_key):
    """strip [(xyz m, (u, v) 0..~2, rgb 0-255, alpha 0..1)] -> MDL bytes (header family of kh2_reflect_mesh)"""
    assert len(strip) <= MAX_VERTS, 'strip has %d vertices > %d' % (len(strip), MAX_VERTS)
    ext = [max(abs(v[0][k]) for v in strip) or 1.0 for k in range(3)]
    head = bytearray(b'MDL\0' + struct.pack('<II', 0x80001, self_key)) + M.HEAD_0C_40
    struct.pack_into('<I', head, 0x1c, tex_key)
    head += struct.pack('<10f', *ext, 0, 0, 0, 1.0, 1.0, 0, 0)
    head += struct.pack('<6I', 4, 0x99, 8, 0, len(strip), 0x80)
    assert len(head) == 0x80
    body = bytearray()
    for p, (u, v), rgb, al in strip:
        a = max(0.0, min(1.0, al * OPACITY))
        c = [min(15, round(rgb[k] * a / 17)) for k in range(3)] + [min(15, round(a * 15))]
        uu, vv = round(u * 128), round(v * 128)
        assert 0 <= uu <= 255 and 0 <= vv <= 255, 'UV out of u8 range'
        xyz = [max(-127, min(127, round(p[k] / ext[k] * 127))) for k in range(3)]
        body += struct.pack('<BBHbbbB', uu, vv, sum(x << (4 * k) for k, x in enumerate(c)), *xyz, 0)
    return bytes(head + body)


def ring_mdl(self_key=0, tex_key=0):
    parts = disc_part(1.0) + band_part(1.0)
    strip = join(parts)
    return encode(strip, self_key, tex_key), dict(vertices=len(strip), parts=len(parts),
                                                  kh2='P_EX100 DPD3 model 27 disc + MAGNET_3 model 10 band')


def orb_mdl(self_key=0, tex_key=0):
    parts = sphere_part(0.55, CORE, CORE_GAIN) + sphere_part(1.0, SHELL, SHELL_GAIN)
    strip = join(parts)
    return encode(strip, self_key, tex_key), dict(vertices=len(strip), parts=len(parts),
                                                  kh2='2 nested spheres, KH2 Magnet swirl texture')


def source_tris(spec):
    """KH2 model as render triangles (KH2 UVs + KH2 vertex colours) for previews"""
    vs, quads = kh2_model(spec)
    tris = []
    for ix, uvs, cs in quads:
        c = [((vs[i][0] / 100, -vs[i][1] / 100, vs[i][2] / 100), uvs[j], tuple(min(255, x * 2) for x in cs[j]))
             for j, i in enumerate(ix)]
        tris += [[c[0], c[1], c[2]], [c[1], c[3], c[2]]]
    return tris


def preview(out):
    from PIL import Image, ImageDraw
    tex = texture()
    cell = 320
    rows = [('KH2 Magnet Burst disc (P_EX100 3/27)', source_tris(DISC), 0),
            ('KH2 Magnega band (MAGNET_3 0/10)', source_tris(BAND), 0),
            ('native RING mdl (disc + band)', M.decode_mdl(ring_mdl()[0]), 1),
            ('native ORB mdl (2 swirl spheres)', M.decode_mdl(orb_mdl()[0]), 1)]
    sheet = Image.new('RGB', (cell * len(rows), cell + 24), (8, 10, 14))
    dr = ImageDraw.Draw(sheet)
    for k, (label, tris, _) in enumerate(rows):
        sheet.paste(M.render(tris, tex, cell, yaw=30, pitch=35), (k * cell, 24))
        dr.text((k * cell + 4, 28), label, fill='white')
    dr.text((4, 6), 'Offline preview, KH2 Magnet swirl texture, additive. No game shader/animation.', fill='white')
    sheet.save(out)
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    if '--preview' in a:
        print(preview(a[a.index('--preview') + 1]))
    else:
        print('ring', ring_mdl()[1])
        print('orb', orb_mdl()[1])
