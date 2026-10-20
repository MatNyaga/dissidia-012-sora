"""Export the skin ("model-0") of a Dissidia 012 GMO to glTF 2.0 (.gltf + .bin), with skeleton and skin weights,
so it opens in Blender (File > Import > glTF 2.0).

What is exported: model-0 bones (bind pose), every mesh as a skinned primitive (positions, UVs, weights),
materials (texture file names; textures themselves come from gim2png.py if present as <texture>.png).
Positions/UVs are de-normalized with the model's 0x8015 args (mask 0x180 = position offset[3] + scale[3],
mask 0x003 = UV offset[2] + scale[2]). Triangle strips (prim 4) are turned into triangles.

Usage: python3 -I gmo2gltf.py MODEL.gmo OUT_DIR
"""
import base64
import json
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gmo  # noqa: E402


def quat_to_mat(q):
    x, y, z, w = q
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0],
            [0, 0, 0, 1]]


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def local_matrix(t, q, s):
    m = quat_to_mat(q)
    for i in range(3):
        for j in range(3):
            m[i][j] *= s[j]
        m[i][3] = t[i]
    return m


def invert_rigid(m):
    """Inverse of a rotation(+uniform scale) + translation matrix."""
    sx = math.sqrt(m[0][0] ** 2 + m[1][0] ** 2 + m[2][0] ** 2) or 1.0
    r = [[m[j][i] / (sx * sx) for j in range(3)] for i in range(3)]
    t = [-sum(r[i][k] * m[k][3] for k in range(3)) for i in range(3)]
    return [r[0] + [t[0]], r[1] + [t[1]], r[2] + [t[2]], [0, 0, 0, 1]]


def strip_to_tris(idx):
    tris = []
    for k in range(len(idx) - 2):
        a, b, c = idx[k], idx[k + 1], idx[k + 2]
        if a == b or b == c or a == c:
            continue
        tris += [a, b, c] if k % 2 == 0 else [b, a, c]
    return tris


def load_model(path, model_name='model-0'):
    d = open(path, 'rb').read()
    items = []
    gmo.walk(d, 16, len(d), 0, items)
    m = next(i for i in items if i[2] == 0x03 and i[5] == model_name)
    sub = [i for i in items if m[1] < i[1] < m[1] + m[4]]
    model = {'bones': [], 'meshes': [], 'arrays': [], 'materials': [], 'textures': [],
             'pos_xform': ((0, 0, 0), (1, 1, 1)), 'uv_xform': ((0, 0), (1, 1))}
    for ao, at, ahs, asz in gmo.chunks(d, m[1] + m[3], m[1] + m[4]):
        if at == 0x8015:
            mask, = struct.unpack_from('<I', d, ao + 8)
            f = struct.unpack_from('<%df' % ((asz - 12) // 4), d, ao + 12)
            if mask & 0x180:
                model['pos_xform'] = (f[0:3], f[3:6])
            elif mask & 0x3:
                model['uv_xform'] = (f[0:2], f[2:4])
    part = -1
    for depth, o, t, hs, size, name in sub:
        if name is None:
            continue
        if t == 0x05:
            part += 1
            model.setdefault('parts', []).append(name)
        args = {}
        if t not in (0x07, 0x0A):
            for ao, at, ahs, asz in gmo.chunks(d, o + hs, o + size):
                if at & 0x8000:
                    args.setdefault(at, []).append(d[ao + 8:ao + asz])
        if t == 0x04:
            parent = struct.unpack('<I', args[0x8041][0])[0] & 0xFFF if 0x8041 in args else -1
            tr = struct.unpack('<3f', args[0x8048][0]) if 0x8048 in args else (0, 0, 0)
            rq = struct.unpack('<4f', args[0x804B][0]) if 0x804B in args else (0, 0, 0, 1)
            sc = struct.unpack('<3f', args[0x8049][0]) if 0x8049 in args else (1, 1, 1)
            skin = None
            if 0x8044 in args and 0x8045 in args:        # skinning bones of the part this bone draws + bind matrices
                n = struct.unpack_from('<I', args[0x8044][0])[0]
                refs = [r & 0xFFF for r in struct.unpack_from('<%dI' % n, args[0x8044][0], 4)]
                mats = [struct.unpack_from('<16f', args[0x8045][0], 4 + k * 64) for k in range(n)]
                skin = (refs, mats)
            model['bones'].append({'name': name, 'parent': parent, 't': tr, 'r': rq, 's': sc, 'skin': skin,
                                   'draw': struct.unpack('<I', args[0x804E][0])[0] & 0xFFF if 0x804E in args else None})
        elif t == 0x06:
            mat = struct.unpack('<I', args[0x8061][0])[0] & 0xFFF
            if 0x8062 in args:
                blob = args[0x8062][0]
                pal = list(struct.unpack_from('<%dI' % struct.unpack_from('<I', blob)[0], blob, 4))
            else:
                pal = None                              # rigid: follows the bone that draws this part
            draws = []
            for blob in args.get(0x8066, []):
                ref, prim, per, n = struct.unpack_from('<4I', blob)
                idx = struct.unpack_from('<%dH' % (per * n), blob, 16)
                draws.append((ref & 0xFFF, prim, [idx[k * per:(k + 1) * per] for k in range(n)]))
            model['meshes'].append({'name': name, 'material': mat, 'palette': pal, 'draws': draws, 'part': part})
        elif t == 0x07:
            model['arrays'].append((part, name))
        elif t == 0x08:
            model['materials'].append({'name': name, 'texture': None})
        elif t == 0x09 and model['materials'] and 0x8091 in args:
            model['materials'][-1]['texture'] = struct.unpack('<I', args[0x8091][0])[0] & 0xFFF
        elif t == 0x0A:
            tex = {'name': name, 'file': None}
            for ao, at, ahs, asz in gmo.chunks(d, o + hs, o + size):
                if at == 0x8012:
                    tex['file'] = d[ao + 8:ao + asz].split(b'\0')[0].decode('latin1')
            model['textures'].append(tex)
    data = [verts for name, vt, verts in gmo.arrays(d, sub)]   # names repeat per part: keep order
    # array refs in meshes are PART-local: global index = arrays of earlier parts + local index
    first = {}
    for k, (p, _) in enumerate(model['arrays']):
        first.setdefault(p, k)
    model['array_data'] = data
    for mesh in model['meshes']:
        mesh['draws'] = [(first.get(mesh['part'], 0) + a, prim, lists) for a, prim, lists in mesh['draws']]
    return model


def export(path, out_dir):
    model = load_model(path)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(path))[0]
    bones = model['bones']
    world = []
    for b in bones:
        loc = local_matrix(b['t'], b['r'], b['s'])
        world.append(matmul(world[b['parent']], loc) if b['parent'] >= 0 else loc)
    (po, ps), (uo, us) = model['pos_xform'], model['uv_xform']
    buf = bytearray()
    views, accessors, meshes_out = [], [], []

    def add(data, comp, typ, count, target=None, minmax=None):
        while len(buf) % 4:
            buf.append(0)
        views.append({'buffer': 0, 'byteOffset': len(buf), 'byteLength': len(data), **({'target': target} if target else {})})
        buf.extend(data)
        acc = {'bufferView': len(views) - 1, 'componentType': comp, 'count': count, 'type': typ}
        if minmax:
            acc['min'], acc['max'] = minmax
        accessors.append(acc)
        return len(accessors) - 1

    # palette index -> skinning bone list (0x8044) of the bone that draws the mesh's part; 0x8045 = bind matrices
    part_skin = {b['draw']: b['skin'] for b in bones if b['draw'] is not None and b['skin']}
    ibm_rows = [None] * len(bones)
    for refs, mats in part_skin.values():
        for r, mtx in zip(refs, mats):
            ibm_rows[r] = mtx
    for mesh in model['meshes']:
        refs = part_skin.get(mesh['part'], ([0], None))[0]
        if mesh['palette'] is None:                 # rigid (weapons): follows the part's single skin bone
            mesh['palette'] = [0]
        mesh['joints'] = [refs[p] if p < len(refs) else 0 for p in mesh['palette']]
        prims = []
        for arr_i, prim, lists in mesh['draws']:
            verts = model['array_data'][arr_i]
            tris = []
            for lst in lists:
                tris += strip_to_tris(list(lst)) if prim == 4 else list(lst)
            if not tris:
                continue
            used = sorted(set(tris))
            remap = {v: k for k, v in enumerate(used)}
            pos, uv, jnt, wgt = bytearray(), bytearray(), bytearray(), bytearray()
            lo, hi = [1e9] * 3, [-1e9] * 3
            for vi in used:
                v = verts[vi]
                p = [v['pos'][k] / 32768.0 * ps[k] + po[k] for k in range(3)]
                lo, hi = [min(a, b) for a, b in zip(lo, p)], [max(a, b) for a, b in zip(hi, p)]
                pos += struct.pack('<3f', *p)
                u = v.get('uv', (0, 0))
                uv += struct.pack('<2f', u[0] / 32768.0 * us[0] + uo[0], u[1] / 32768.0 * us[1] + uo[1])
                w = list(v.get('weight', (128,)))
                top = sorted(range(len(w)), key=lambda k: -w[k])[:4]     # palettes hold up to 8: keep the 4 largest
                j = [mesh['joints'][k] if k < len(mesh['joints']) and w[k] else 0 for k in top] + [0] * (4 - len(top))
                w = [w[k] for k in top] + [0] * (4 - len(top))
                tot = sum(w) or 1
                jnt += struct.pack('<4H', *j)
                wgt += struct.pack('<4f', *[x / tot for x in w])
            idx = struct.pack('<%dH' % len(tris), *[remap[t] for t in tris])
            prims.append({'attributes': {'POSITION': add(pos, 5126, 'VEC3', len(used), 34962, (lo, hi)),
                                         'TEXCOORD_0': add(uv, 5126, 'VEC2', len(used), 34962),
                                         'JOINTS_0': add(jnt, 5123, 'VEC4', len(used), 34962),
                                         'WEIGHTS_0': add(wgt, 5126, 'VEC4', len(used), 34962)},
                          'indices': add(idx, 5123, 'SCALAR', len(tris), 34963),
                          'material': mesh['material']})
        if prims:
            meshes_out.append({'name': '%s|%s' % (model['parts'][mesh['part']], mesh['name']), 'primitives': prims})

    ibm = bytearray()
    for k, w in enumerate(world):
        if ibm_rows[k] is not None:                 # true bind pose from 0x8045 (already column-major)
            ibm += struct.pack('<16f', *ibm_rows[k])
        else:
            inv = invert_rigid(w)
            ibm += struct.pack('<16f', *[inv[r][c] for c in range(4) for r in range(4)])   # column-major
    ibm_acc = add(ibm, 5126, 'MAT4', len(bones))
    nodes = []
    for i, b in enumerate(bones):
        node = {'name': b['name'], 'translation': list(b['t']), 'rotation': list(b['r']), 'scale': list(b['s'])}
        kids = [k for k, c in enumerate(bones) if c['parent'] == i]
        if kids:
            node['children'] = kids
        nodes.append(node)
    roots = [i for i, b in enumerate(bones) if b['parent'] < 0]
    mesh_nodes = []
    for k in range(len(meshes_out)):
        nodes.append({'name': meshes_out[k]['name'], 'mesh': k, 'skin': 0})
        mesh_nodes.append(len(nodes) - 1)
    images, textures = [], []
    for t in model['textures']:
        images.append({'uri': t['name'] + '.png', 'name': t['file'] or t['name']})
        textures.append({'source': len(images) - 1})
    materials = []
    for mtl in model['materials']:
        m = {'name': mtl['name'], 'doubleSided': True}
        if mtl['texture'] is not None and mtl['texture'] < len(textures):
            m['pbrMetallicRoughness'] = {'baseColorTexture': {'index': mtl['texture']}, 'metallicFactor': 0}
        materials.append(m)
    gltf = {'asset': {'version': '2.0', 'generator': 'dissidia-012-sora gmo2gltf.py'},
            'scene': 0, 'scenes': [{'nodes': roots + mesh_nodes}], 'nodes': nodes, 'meshes': meshes_out,
            'skins': [{'joints': list(range(len(bones))), 'inverseBindMatrices': ibm_acc}],
            'materials': materials, 'textures': textures, 'images': images,
            'buffers': [{'byteLength': len(buf), 'uri': base + '.bin'}], 'bufferViews': views, 'accessors': accessors}
    open(os.path.join(out_dir, base + '.bin'), 'wb').write(buf)
    json.dump(gltf, open(os.path.join(out_dir, base + '.gltf'), 'w'), indent=1)
    print('wrote %s: %d bones, %d meshes, %d materials, %d textures, %d bytes of data' % (
        os.path.join(out_dir, base + '.gltf'), len(bones), len(meshes_out), len(materials), len(images), len(buf)))
    return model, world


if __name__ == '__main__':
    export(sys.argv[1], sys.argv[2])
