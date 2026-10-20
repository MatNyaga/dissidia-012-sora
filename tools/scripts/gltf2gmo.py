"""Build a new GMO skin from a glTF, keeping a base GMO's skeleton + animations.

  python3 -I gltf2gmo.py BASE.gmo SKIN.gltf OUT.gmo

- BASE.gmo: a Dissidia fighter GMO (e.g. Cloud's P_SEV100_1P.gmo). Its "_000A" model (bones + 86 motions), its
  model-0 bones and its "TexAnm" eye-animation block are kept byte-for-byte.
- SKIN.gltf: meshes skinned to bones with the SAME NAMES as model-0's bones (as written by gmo2gltf.py),
  vertices in the base's BIND pose (0x8045 matrices, arms at ~45°; gmo2gltf writes them as inverseBindMatrices).
  Mesh palettes index the body's skinning list (0x8044 on the bone that draws part 0, 30 bones for Cloud).
  Mesh name "part|anything" picks the part (p_sev100 = body, wep0 / wep1 = weapons; default = first part).
  Image "name" = texture file name kept in the GMO (eye animation finds textures by it); "uri" = PNG file.
- Weapon parts (wep0, wep1: rigid meshes, no palette; their draw bones attach to r_wep with an offset matrix)
  are copied from the base unless REBUILD_WEAPONS=1 and the glTF has meshes named "wep0|…"/"wep1|…".
  Weapon vertices are in the same bind space gmo2gltf.py exports (r_wep's inverse bind = the offset matrix).
- Writes model-0 again: new position/UV scale args, parts with meshes (≤ 8 bones each, triangle lists),
  vertex arrays (u8 weights, u16 UV, colour 4444 white, s16 position), materials, textures (PNG → GIM index8).
"""
import json
import os
import struct
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gmo  # noqa: E402

MAX_BONES = 8


def chunk(t, name, body):
    """Block chunk. Header u32 #3/#4 = child offset / data offset (both = header size for normal blocks;
    arrays: child offset = total size (no children), data offset = header + 16-byte vertex sub-header)."""
    nm = name.encode() + b'\0'
    nm += b'\0' * ((-len(nm)) % 4)
    hs = 16 + len(nm)
    size = hs + len(body)
    if t == 0x07:
        return struct.pack('<HHIII', t, hs, size, size, hs + 16) + nm + body
    return struct.pack('<HHIII', t, hs, size, hs, hs) + nm + body


def arg(t, data):
    data += b'\0' * ((-len(data)) % 4)
    return struct.pack('<HHI', t, 0, 8 + len(data)) + data


# ---------- glTF reading ----------
class Gltf:
    def __init__(self, path):
        self.dir = os.path.dirname(os.path.abspath(path))
        self.g = json.load(open(path))
        self.bufs = [open(os.path.join(self.dir, b['uri']), 'rb').read() for b in self.g['buffers']]

    def acc(self, i):
        a = self.g['accessors'][i]
        v = self.g['bufferViews'][a['bufferView']]
        n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
        f = {5126: 'f', 5123: 'H', 5121: 'B', 5125: 'I'}[a['componentType']]
        size = struct.calcsize(f) * n
        stride = v.get('byteStride', size)
        base = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        buf = self.bufs[v['buffer']]
        out = [struct.unpack_from('<%d%s' % (n, f), buf, base + k * stride) for k in range(a['count'])]
        if a.get('normalized') and f in 'BH':
            scale = 255.0 if f == 'B' else 65535.0
            out = [tuple(x / scale for x in e) for e in out]
        return out


# ---------- GIM writing ----------
def png_to_gim(path):
    im = Image.open(path).convert('RGBA')
    w, h = im.size
    if w & (w - 1) or h & (h - 1) or w > 512 or h > 512:
        raise SystemExit('%s: textures must be power-of-two sizes up to 512 (got %dx%d)' % (path, w, h))
    colors = im.getcolors(256)
    if colors is not None:                              # <= 256 colours: exact palette, no loss
        pal_list = [c for n, c in colors]
        index = {c: k for k, c in enumerate(pal_list)}
        q = Image.new('P', (w, h))
        q.putdata([index[c] for c in im.getdata()])
        pal = [x for c in pal_list for x in c]
    else:                                               # libimagequant (best quality, keeps alpha), dithered
        try:
            q = im.quantize(colors=256, method=3, dither=Image.FLOYDSTEINBERG)
        except Exception:
            q = im.quantize(colors=256, method=2)
        mode, raw = q.palette.mode, bytes(q.palette.palette)
        if mode == 'RGBA':
            pal = list(raw[:256 * 4])
        else:
            pal = []
            for k in range(0, min(len(raw), 256 * 3), 3):
                pal += list(raw[k:k + 3]) + [255]
    pal += [0] * (256 * 4 - len(pal))
    pixels = q.tobytes()                                    # index8, row pitch = w (w >= 16 keeps 16-byte align)
    if w < 16:
        raise SystemExit('%s: width must be at least 16' % path)

    def image_block(bid, fmt, width, height, bpp, data, level_type):
        hdr = struct.pack('<HHHHHHHHHHIIIIIHHHH', 0x30, 0, fmt, 0, width, height, bpp, 16, 1, 2, 0,
                          0x30, 0x40, 0x40 + len(data), 0, level_type, 1, 3, 1)
        hdr += struct.pack('<I', 0x40) + b'\0' * (0x40 - len(hdr) - 4)
        body = hdr + data
        return struct.pack('<HHIII', bid, 0, 16 + len(body), 16 + len(body), 16) + body
    img = image_block(0x04, 5, w, h, 8, pixels, 1)
    palb = image_block(0x05, 3, 256, 1, 32, bytes(pal), 2)
    picture = struct.pack('<HHIII', 0x03, 0, 16 + len(img) + len(palb), 16, 16) + img + palb
    root = struct.pack('<HHIII', 0x02, 0, 16 + len(picture), 16, 16) + picture
    return b'MIG.00.1PSP\0\0\0\0\0' + root


# ---------- building model-0 ----------
def build(base_path, gltf_path, out_path):
    d = open(base_path, 'rb').read()
    items = []
    gmo.walk(d, 16, len(d), 0, items)
    file_c = next(i for i in items if i[2] == 0x02)
    m0 = next(i for i in items if i[2] == 0x03 and i[5] == 'model-0')
    m0_items = [i for i in items if m0[1] < i[1] < m0[1] + m0[4] and i[0] == m0[0] + 1]
    bones_raw = b''.join(d[o:o + size] for depth, o, t, hs, size, name in m0_items if t == 0x04)
    blind_raw = b''.join(d[o:o + size] for depth, o, t, hs, size, name in m0_items if t == 0x0F)
    bone_names = [name for depth, o, t, hs, size, name in m0_items if t == 0x04]
    parts = [name for depth, o, t, hs, size, name in m0_items if t == 0x05]
    base_mats = [d[o:o + size] for depth, o, t, hs, size, name in m0_items if t == 0x08]

    # body skinning list: bone that draws part 0 has 0x8044 = skin bones (mesh palettes index THIS list)
    skin_refs = None
    for depth, o, t, hs, size, name in m0_items:
        if t != 0x04:
            continue
        a = {at: d[ao + 8:ao + asz] for ao, at, ahs, asz in gmo.chunks(d, o + hs, o + size)}
        if 0x804E in a and struct.unpack('<I', a[0x804E])[0] & 0xFFF == 0 and 0x8044 in a:
            n = struct.unpack_from('<I', a[0x8044])[0]
            skin_refs = [r & 0xFFF for r in struct.unpack_from('<%dI' % n, a[0x8044], 4)]
    if skin_refs is None:
        raise SystemExit('base has no skinning list for the body part')

    G = Gltf(gltf_path)
    g = G.g
    skin = g['skins'][0]
    joint_names = [g['nodes'][j]['name'] for j in skin['joints']]
    # glTF joint -> index in the body skinning list; bones outside the list fall back to their nearest
    # ancestor that is in it (e.g. root/p_sev100 -> hip)
    parents = {}
    for depth, o, t, hs, size, name in m0_items:
        if t == 0x04:
            a = {at: d[ao + 8:ao + asz] for ao, at, ahs, asz in gmo.chunks(d, o + hs, o + size)}
            parents[len(parents)] = struct.unpack('<I', a[0x8041])[0] & 0xFFF if 0x8041 in a else -1
    jmap = []
    for n in joint_names:
        if n not in bone_names:
            raise SystemExit('glTF bone %r is not in the base skeleton' % n)
        b = bone_names.index(n)
        while b >= 0 and b not in skin_refs:
            b = parents.get(b, -1)
        jmap.append(skin_refs.index(b) if b >= 0 else skin_refs.index(bone_names.index('hip')))

    # gather triangles per part
    per_part = {p: [] for p in parts}
    allpos, alluv = [], []
    for mesh in g['meshes']:
        part = mesh['name'].split('|')[0] if mesh['name'].split('|')[0] in parts else parts[0]
        for prim in mesh['primitives']:
            if prim.get('mode', 4) != 4:
                continue
            at = prim['attributes']
            P = G.acc(at['POSITION'])
            UV = G.acc(at['TEXCOORD_0']) if 'TEXCOORD_0' in at else [(0, 0)] * len(P)
            J = G.acc(at['JOINTS_0']) if 'JOINTS_0' in at else [(0, 0, 0, 0)] * len(P)
            W = G.acc(at['WEIGHTS_0']) if 'WEIGHTS_0' in at else [(1, 0, 0, 0)] * len(P)
            idx = [i[0] for i in G.acc(prim['indices'])] if 'indices' in prim else list(range(len(P)))
            verts = []
            for k in range(len(P)):
                infl = sorted(((W[k][c], jmap[J[k][c]]) for c in range(4) if W[k][c] > 0.004), reverse=True)[:4]
                tot = sum(w for w, b in infl) or 1
                verts.append((P[k], UV[k], [(w / tot, b) for w, b in infl] or [(1.0, jmap[0])]))
            allpos += [v[0] for v in verts]
            alluv += [v[1] for v in verts]
            tris = [idx[i:i + 3] for i in range(0, len(idx) - 2, 3)]
            per_part[part].append((prim.get('material', 0), verts, tris))

    # reuse the base model's 0x8015 position/UV scale: required when weapon parts are copied from the base,
    # because their raw vertices are decoded with the same model-level scale
    keep = not os.environ.get('NEW_SCALE')          # default: base scale (copied weapon parts depend on it)
    base_pos = base_uv = None
    for ao, at, ahs, asz in gmo.chunks(d, m0[1] + m0[3], m0[1] + m0[4]):
        if at == 0x8015:
            mask, = struct.unpack_from('<I', d, ao + 8)
            fl = struct.unpack_from('<%df' % ((asz - 12) // 4), d, ao + 12)
            if mask & 0x180:
                base_pos = fl
            elif mask & 0x3:
                base_uv = fl
    lo = [min(p[c] for p in allpos) for c in range(3)]
    hi = [max(p[c] for p in allpos) for c in range(3)]
    off = [(a + b) / 2 for a, b in zip(lo, hi)]
    sc = max(max((b - a) / 2 for a, b in zip(lo, hi)), 1e-6) * 1.0001
    ulo = [min(u[c] for u in alluv) for c in range(2)]
    uhi = [max(u[c] for u in alluv) for c in range(2)]
    uoff = ulo
    usc = [max((b - a) / 1.99, 1e-6) for a, b in zip(ulo, uhi)]
    if keep and base_pos and base_uv:
        off, sc = list(base_pos[0:3]), base_pos[3]
        uoff, usc = list(base_uv[0:2]), list(base_uv[2:4])

    clamped = [0]

    def enc_pos(p):
        raw = [round((p[c] - off[c]) / sc * 32768) for c in range(3)]
        if any(r < -32768 or r > 32767 for r in raw):
            clamped[0] += 1
        return [max(-32768, min(32767, r)) for r in raw]

    def enc_uv(u):
        return [max(0, min(65535, round((u[c] - uoff[c]) / usc[c] * 32768))) for c in range(2)]

    part_chunks = []
    total_meshes = 0
    base_parts = {name: d[o:o + size] for depth, o, t, hs, size, name in m0_items if t == 0x05}
    rebuild_weapons = os.environ.get('REBUILD_WEAPONS')
    for p_i, part in enumerate(parts):
        if p_i > 0 and (not rebuild_weapons or not per_part[part]):
            # weapons are rigid meshes in their own bone space (wep0/wep1 attached to r_wep): keep the base's
            part_chunks.append(base_parts[part])
            continue
        mesh_chunks, array_chunks = [], []
        rigid = p_i > 0                        # weapon parts: rigid, no palette, follow r_wep via the draw bone
        for mat, verts, tris in per_part[part]:
            if rigid:
                groups = [(tris, set())]
            else:
                # split into groups of <= MAX_BONES bones
                groups, cur, cur_b = [], [], set()
                for tri in tris:
                    bs = {b for v in tri for w, b in verts[v][2]}
                    if len(cur_b | bs) > MAX_BONES and cur:
                        groups.append((cur, cur_b))
                        cur, cur_b = [], set()
                    cur.append(tri)
                    cur_b |= bs
                if cur:
                    groups.append((cur, cur_b))
            for tris_g, bones_g in groups:
                pal = [0] if rigid else sorted(bones_g)
                used = sorted({v for t in tris_g for v in t})
                remap = {v: k for k, v in enumerate(used)}
                nw = len(pal)                       # GE: weight k goes to palette bone k
                vt = 0x131A | ((nw - 1) << 14)
                comps, real = gmo.ge_layout(vt)
                vt |= real << 24                    # high byte = vertex size, as in the game's GMOs
                vdata = bytearray()
                for v in used:
                    pos, uv, infl = verts[v]
                    rec = bytearray(real)
                    full = [0] * nw
                    if rigid:
                        full[0] = 128
                    else:
                        ws = [round(w * 128) for w, b in infl]
                        ws[0] += 128 - sum(ws)
                        for k, (w, b) in enumerate(infl):
                            full[pal.index(b)] += ws[k]
                    for name, o, n, fmt in comps:
                        if name == 'weight':
                            struct.pack_into('<%dB' % n, rec, o, *[max(0, min(255, x)) for x in full])
                        elif name == 'uv':
                            struct.pack_into('<2H', rec, o, *enc_uv(uv))
                        elif name == 'color':
                            struct.pack_into('<H', rec, o, 0xFFFF)
                        elif name == 'pos':
                            struct.pack_into('<3h', rec, o, *enc_pos(pos))
                    vdata += rec
                a_local = len(array_chunks)
                adata = struct.pack('<IIII', vt, len(used), 1, 0) + bytes(vdata)
                adata += b'\0' * ((-len(adata)) % 4)
                array_chunks.append(chunk(0x07, 'arrays-%d-%04d' % (total_meshes, 0), adata))
                ind = [remap[v] for t in tris_g for v in t]
                draw = struct.pack('<4I', 0x00071000 | a_local, 3, len(ind), 1) + struct.pack('<%dH' % len(ind), *ind)
                body = arg(0x8061, struct.pack('<I', 0x00082000 | mat))
                if not rigid:
                    body += arg(0x8062, struct.pack('<I', len(pal)) + struct.pack('<%dI' % len(pal), *pal))
                body += arg(0x8066, draw)
                mesh_chunks.append(chunk(0x06, 'mesh-%d' % total_meshes, body))
                total_meshes += 1
        part_chunks.append(chunk(0x05, part, b''.join(mesh_chunks) + b''.join(array_chunks)))

    # materials + textures
    mats, texs = [], []
    for k, mtl in enumerate(g.get('materials', [])):
        tex = mtl.get('pbrMetallicRoughness', {}).get('baseColorTexture', {}).get('index', 0)
        tpl = mtl.get('extras', {}).get('base_material', k)        # extras.base_material: template to copy
        m = bytearray(base_mats[min(tpl, len(base_mats) - 1)])   # keep the base's material settings
        name = mtl.get('name', 'material%d' % k)
        # rebuild header with the new name, keep the template's args/layer, point layer at texture tex
        o_hs = struct.unpack_from('<H', m, 2)[0]
        body = bytes(m[o_hs:])
        i = body.find(struct.pack('<HHI', 0x8091, 0, 12))
        if i >= 0:
            body = body[:i + 8] + struct.pack('<I', 0x000A2000 | tex) + body[i + 12:]
        mats.append(chunk(0x08, name, body))
    base_tex = {}                                       # file name -> (chunk bytes, decoded RGBA)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gim as gimlib
    for depth, o, t, hs, size, name in m0_items:
        if t == 0x0A:
            fn = None
            for ao, at, ahs, asz in gmo.chunks(d, o + hs, o + size):
                if at == 0x8012:
                    fn = d[ao + 8:ao + asz].split(b'\0')[0].decode('latin1')
            gi = d.find(b'MIG.00.1PSP', o, o + size)
            if fn and gi >= 0:
                base_tex[fn] = (d[o:o + size], gimlib.decode(d, gi).tobytes())
    reused = 0
    for k, img in enumerate(g.get('images', [])):
        fn = img.get('name')
        png = Image.open(os.path.join(G.dir, img['uri'])).convert('RGBA')
        if fn in base_tex and png.tobytes() == base_tex[fn][1]:
            texs.append(base_tex[fn][0])                # unchanged texture: keep the game's original bytes
            reused += 1
            continue
        gim = png_to_gim(os.path.join(G.dir, img['uri']))
        fname = img.get('name', os.path.splitext(img['uri'])[0] + '.tga').encode() + b'\0'
        body = arg(0x8012, fname) + arg(0x8013, struct.pack('<I', len(gim)) + gim)
        texs.append(chunk(0x0A, os.path.splitext(img['uri'])[0], body))

    args = arg(0x8015, struct.pack('<I6f', 0x180, *off, sc, sc, sc))
    args += arg(0x8015, struct.pack('<I4f', 0x003, *uoff, *usc))
    model0 = chunk(0x03, 'model-0', args + bones_raw + b''.join(part_chunks) + b''.join(mats) + b''.join(texs) + blind_raw)
    before = d[file_c[1] + file_c[3]:m0[1]]                       # _000A and anything else before model-0
    after = d[m0[1] + m0[4]:file_c[1] + file_c[4]]
    filec = chunk(0x02, 'file-0', before + model0 + after)
    out = d[:16] + filec
    open(out_path, 'wb').write(out)
    if clamped[0]:
        print('WARNING: %d vertices lie outside the base model box and were squashed onto its edge '
              '(shrink/move the mesh, or NEW_SCALE=1 with all parts rebuilt)' % clamped[0])
    print('textures: %d kept from the base unchanged, %d converted from PNG' % (reused, len(texs) - reused))
    print('wrote %s: %d bytes; model-0 %d bytes, %d meshes, %d materials, %d textures; pos offset %s scale %.4f' % (
        out_path, len(out), len(model0), total_meshes, len(mats), len(texs),
        ['%.3f' % x for x in off], sc))


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], sys.argv[3])
