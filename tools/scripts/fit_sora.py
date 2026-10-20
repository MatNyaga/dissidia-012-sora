"""Fit KH2 Sora (sora.glb from kh2_export) onto Cloud's Dissidia skeleton → glTF for gltf2gmo.py.

  python3 -I fit_sora.py SORA.glb CLOUD.gltf OUT_DIR [TEX_SIZE]

- CLOUD.gltf = gmo2gltf.py export of Cloud's P_SEV100_1P.gmo (bind pose: arms ~45° down, ~1.8 tall).
- Cloud's animations also set bone lengths, so Sora's mesh is bent/stretched so that his joints land on
  Cloud's joints (shoulder, elbow, wrist, hip, knee, ankle, neck, head). Each Sora bone gets an affine map from a
  segment table (Sora joint A→B onto Cloud joint A→B: rotate, stretch along the bone, `perp` across it); the mesh
  is moved with Sora's own skin weights (smooth joints), then re-weighted to Cloud's bones (BONE_MAP).
- Output: OUT_DIR/sora_fit.gltf (+ .bin, PNGs). Cloud's meshes, materials 0-3 and images are kept (copied weapon
  parts and the TexAnm eye animation refer to them); Sora's meshes are "p_sev100|sora_*" with new materials 4+
  (extras.base_material = 2, Cloud's body material) and textures downscaled to TEX_SIZE (default 256).
"""
import json
import os
import shutil
import struct
import sys

import numpy as np
from PIL import Image


# ---------- glTF reading ----------
def load_gltf(path):
    if path.endswith('.glb'):
        d = open(path, 'rb').read()
        n = struct.unpack_from('<I', d, 12)[0]
        g = json.loads(d[20:20 + n])
        o = 20 + n
        bn = struct.unpack_from('<I', d, o)[0]
        bufs = [d[o + 8:o + 8 + bn]]
    else:
        g = json.load(open(path))
        bufs = [open(os.path.join(os.path.dirname(path), b['uri']), 'rb').read() for b in g['buffers']]
    return g, bufs


def acc(g, bufs, i):
    a = g['accessors'][i]
    bv = g['bufferViews'][a['bufferView']]
    n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
    dt = {5126: np.float32, 5123: np.uint16, 5121: np.uint8, 5125: np.uint32}[a['componentType']]
    stride = bv.get('byteStride', 0)
    off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    item = np.dtype(dt).itemsize * n
    buf = bufs[bv['buffer']]
    if stride and stride != item:
        rows = [np.frombuffer(buf, dt, n, off + k * stride) for k in range(a['count'])]
        out = np.array(rows)
    else:
        out = np.frombuffer(buf, dt, n * a['count'], off).reshape(a['count'], n)
    if a.get('normalized') and dt != np.float32:
        out = out / np.iinfo(dt).max
    return out.astype(np.float64) if dt == np.float32 or a.get('normalized') else out


def trs(n):
    m = np.eye(4)
    if 'matrix' in n:
        return np.array(n['matrix']).reshape(4, 4).T
    x, y, z, w = n.get('rotation', [0, 0, 0, 1])
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m[:3, :3] = r * np.array(n.get('scale', [1, 1, 1]))
    m[:3, 3] = n.get('translation', [0, 0, 0])
    return m


def world_mats(g):
    parent = {}
    for i, n in enumerate(g['nodes']):
        for c in n.get('children', []):
            parent[c] = i
    cache = {}

    def w(i):
        if i not in cache:
            cache[i] = (w(parent[i]) if i in parent else np.eye(4)) @ trs(g['nodes'][i])
        return cache[i]
    return [w(i) for i in range(len(g['nodes']))], parent


# ---------- the fit ----------
# Sora bone ids (KH2 P_EX100): left side listed; right side = +29 (legs, Bone10..34) / +92 (arms, Bone74..135)
def mirror(b):
    if 10 <= b <= 34:
        return b + 29
    if 74 <= b <= 135:
        return b + 92
    return b


# Sora bone -> Cloud bone (others inherit from their parent)
BONE_MAP_L = {0: 'hip', 2: 'hip', 64: 'waist', 66: 'waist', 67: 'chest', 68: 'chest',
              74: 'l_clavicle', 116: 'l_clavicle', 121: 'l_clavicle',
              76: 'l_uparm', 79: 'l_foarm', 83: 'l_hand', 87: 'l_fing1a', 93: 'l_fing3b', 97: 'l_fing3b',
              101: 'l_fing3b', 105: 'l_fing3b', 109: 'l_uparm',
              136: 'neck', 164: 'neck', 138: 'head',
              10: 'l_femur', 12: 'l_tibia', 13: 'l_foot', 16: 'l_toe'}
# Sora bone -> fit segment (others inherit)
SEG_OF_L = {0: 'pelvis', 64: 'spine', 74: 'l_clav', 116: 'l_clav', 121: 'l_clav', 76: 'l_up', 109: 'l_up',
            79: 'l_fore', 83: 'l_hand', 136: 'neck', 164: 'neck', 138: 'head', 10: 'l_thigh', 12: 'l_shin',
            13: 'l_foot'}

PERP = {'pelvis': 1.1, 'spine': 1.2, 'l_up': 1.1, 'l_fore': 1.1, 'l_thigh': 1.1, 'l_shin': 1.05, 'neck': 1.1}
HEAD_SCALE = 1.0
HAND_SCALE = 0.95
if os.environ.get('NATURAL'):      # skeleton already resized to Sora (gmo_resize.py): keep his own thickness
    PERP = {k: 1.0 for k in PERP}
    HAND_SCALE = 1.0


def both(table):
    out = {}
    for b, v in table.items():
        out[b] = v
        m = mirror(b)
        if m != b:
            out[m] = v.replace('l_', 'r_')
    return out


def rot_between(a, b):
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def seg_affine(sa, sb, ca, cb, perp, axial=None):
    """x -> ca + R D (x - sa): sa->ca, direction sa->sb onto ca->cb, stretch along it (axial; default fits cb)."""
    u = (sb - sa) / np.linalg.norm(sb - sa)
    k = axial if axial is not None else np.linalg.norm(cb - ca) / np.linalg.norm(sb - sa)
    D = perp * np.eye(3) + (k - perp) * np.outer(u, u)
    M = np.eye(4)
    M[:3, :3] = rot_between(sb - sa, cb - ca) @ D
    M[:3, 3] = ca - M[:3, :3] @ sa
    return M


def apply(M, p):
    return M[:3, :3] @ p + M[:3, 3]


# Hand pose baked into the mesh before fitting: KH2's bind hands are open; Cloud's animations expect the right hand
# closed around the grip. Finger chains (left; right = +92): joints whose heads are the bend points.
FINGERS_L = [(94, 95, 96), (98, 99, 100), (102, 103, 104), (106, 107, 108)]     # index .. little
THUMB_L = (91, 92)
CURL = {'r': (85, 100, 65), 'l': (75, 95, 60)}        # degrees at knuckle / middle / end joint (left clenched too: Mat 2026-10-15 "his fist should be clenched" in the intro; was 25/35/20 = open-looking)
THUMB_CURL = {'r': (50, 55), 'l': (45, 50)}


def rot_about(point, axis, deg):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    t = np.radians(deg)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R = np.eye(3) + np.sin(t) * k + (1 - np.cos(t)) * k @ k
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = point - R @ point
    return M


def hand_pose(SJ):
    """-> {sora bone: 4x4 pose matrix} curling the fingers (glTF space: fingers along ±X, palm down, front +Z),
    plus the right fist's grip point / axis for the Keyblade."""
    P = {}
    out = {}
    for side, o, sgn in (('l', 0, 1), ('r', 92, -1)):
        z = np.array([0, 0, 1.0])
        for chain in FINGERS_L:
            M = np.eye(4)
            for b, deg in zip(chain, CURL[side]):
                M = M @ rot_about(SJ(b + o), -sgn * z, deg)      # fingertip (±X) turns down (-Y) to the palm
                P[b + o] = M
        M = np.eye(4)
        for b, deg in zip(THUMB_L, THUMB_CURL[side]):
            M = M @ rot_about(SJ(b + o), np.array([1.0, 0, 0]), deg)          # thumb tip (front, +Z) turns down
            P[b + o] = M
        if side == 'r':
            pts = []
            for chain in FINGERS_L:
                j = [SJ(b + o) for b in chain]
                tip = j[2] + (j[2] - j[1])
                pts += [j[0], (P[chain[0] + o] @ np.r_[j[1], 1])[:3], (P[chain[1] + o] @ np.r_[j[2], 1])[:3],
                        (P[chain[2] + o] @ np.r_[tip, 1])[:3]]
            out['grip'] = np.mean(pts, 0)
            out['axis'] = SJ(94 + o) - SJ(106 + o)                 # little finger -> index finger
    return P, out


def centre_in_fist(pts, c0, ax):
    """Move the grip point to the middle of the hole the curled fingers make: in the slab across the fist, the
    point (near c0, surrounded on all sides by hand vertices) farthest from any vertex."""
    u = np.cross(ax, [0, 1, 0])
    u /= np.linalg.norm(u)
    v = np.cross(ax, u)
    sl = pts[np.abs((pts - c0) @ ax) < 0.03]
    q = np.c_[(sl - c0) @ u, (sl - c0) @ v]
    best = (0, 0.0, 0.0)
    for x in np.linspace(-0.04, 0.04, 81):
        for y in np.linspace(-0.04, 0.04, 81):
            d = np.linalg.norm(q - [x, y], axis=1)
            near = d < 0.05
            ang = np.arctan2(q[near, 1] - y, q[near, 0] - x)
            if len(set(((ang + np.pi) // (np.pi / 4)).astype(int))) < 8:
                continue
            if d.min() > best[0]:
                best = (d.min(), x, y)
    print('fist hole radius %.3f m, grip moved by %.3f m' % (best[0], np.hypot(best[1], best[2])))
    return c0 + best[1] * u + best[2] * v


def build_segments(SJ, CJ):
    """SJ(i) = Sora joint i bind position, CJ(name) = Cloud joint. Coordinates: glTF (Y up, front +Z)."""
    S = {}
    mid = lambda a, b: (a + b) / 2  # noqa: E731
    crotch_s = SJ(3)
    crotch_c = mid(CJ('l_femur'), CJ('r_femur'))
    S['pelvis'] = seg_affine(crotch_s, SJ(2), crotch_c, CJ('hip'), PERP['pelvis'])
    sh_s = mid(SJ(78), SJ(170))
    sh_c = mid(CJ('l_uparm'), CJ('r_uparm'))
    S['spine'] = seg_affine(SJ(2), sh_s, CJ('hip'), sh_c, PERP['spine'])
    for side, o in (('l', 0), ('r', 92)):
        clav0 = SJ(75 + o)
        S[side + '_clav'] = seg_affine(clav0, SJ(78 + o), apply(S['spine'], clav0), CJ(side + '_uparm'),
                                       PERP['spine'])
        S[side + '_up'] = seg_affine(SJ(78 + o), SJ(79 + o), CJ(side + '_uparm'), CJ(side + '_foarm'), PERP['l_up'])
        S[side + '_fore'] = seg_affine(SJ(79 + o), SJ(85 + o), CJ(side + '_foarm'), CJ(side + '_hand'),
                                       PERP['l_fore'])
        S[side + '_hand'] = seg_affine(SJ(85 + o), SJ(98 + o), CJ(side + '_hand'), CJ(side + '_fing3b'),
                                       HAND_SCALE, axial=HAND_SCALE)
    for side, o in (('l', 0), ('r', 29)):
        S[side + '_thigh'] = seg_affine(SJ(11 + o), SJ(12 + o), CJ(side + '_femur'), CJ(side + '_tibia'),
                                        PERP['l_thigh'])
        S[side + '_shin'] = seg_affine(SJ(12 + o), SJ(15 + o), CJ(side + '_tibia'), CJ(side + '_foot'),
                                       PERP['l_shin'])
        a, c = SJ(15 + o), CJ(side + '_foot')
        M = np.eye(4)
        M[:3, :3] = np.diag([1.0, c[1] / a[1], 1.0])        # squash the shoe so the sole stays on the floor
        M[:3, 3] = c - M[:3, :3] @ a
        S[side + '_foot'] = M
    neck0 = SJ(137)
    S['neck'] = seg_affine(neck0, SJ(140), apply(S['spine'], neck0), CJ('head'), PERP['neck'])
    M = np.eye(4)
    M[:3, :3] *= HEAD_SCALE
    M[:3, 3] = CJ('head') - HEAD_SCALE * SJ(140)
    S['head'] = M
    return S


def main():
    sora_path, cloud_path, out_dir = sys.argv[1:4]
    tex_size = int(sys.argv[4]) if len(sys.argv) > 4 else 256
    os.makedirs(out_dir, exist_ok=True)

    sg, sb = load_gltf(sora_path)
    sw, sparent = world_mats(sg)
    sskin = sg['skins'][0]
    sjoints = sskin['joints']
    sibm = acc(sg, sb, sskin['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    sname = {sg['nodes'][j]['name']: k for k, j in enumerate(sjoints)}       # 'BoneN' -> joint slot
    # joint world (bind) matrices: the skeleton's world transform at bind = inverse IBM (in mesh space),
    # then the skinned mesh node's world transform puts everything in scene space
    mesh_nodes = [i for i, n in enumerate(sg['nodes']) if 'mesh' in n]
    root_w = sw[sjoints[0]] @ sibm[0]          # = mesh-space -> scene-space at bind (same for every joint)
    sj_world = np.array([root_w @ np.linalg.inv(m) for m in sibm])

    def SJ(i):
        return sj_world[sname['Bone%d' % i]][:3, 3]

    cg, cb = load_gltf(cloud_path)
    cskin = cg['skins'][0]
    cibm = acc(cg, cb, cskin['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    cnames = [cg['nodes'][j]['name'] for j in cskin['joints']]

    def CJ(n):
        return np.linalg.inv(cibm[cnames.index(n)])[:3, 3]

    segs = build_segments(SJ, CJ)
    fpose, grip = hand_pose(SJ)
    bone_map, seg_of = both(BONE_MAP_L), both(SEG_OF_L)
    # resolve every Sora joint slot to (segment, Cloud bone) by walking up the hierarchy
    node_of_slot = {k: j for k, j in enumerate(sjoints)}
    slot_of_node = {j: k for k, j in enumerate(sjoints)}

    def resolve(slot, table):
        node = node_of_slot[slot]
        while True:
            b = int(sg['nodes'][node]['name'][4:])
            if b in table:
                return table[b]
            node = sparent[node]
            if node not in slot_of_node:
                raise SystemExit('no mapping for Bone%d' % b)
    slot_seg = [resolve(k, seg_of) for k in range(len(sjoints))]
    slot_cloud = [cnames.index(resolve(k, bone_map)) for k in range(len(sjoints))]

    # ----- new meshes -----
    out_bin = bytearray()
    views, accs, meshes = [], [], []

    def add(arr, ctype, typ, target=None, minmax=False):
        arr = np.ascontiguousarray(arr)
        while len(out_bin) % 4:
            out_bin.append(0)
        views.append({'buffer': 1, 'byteOffset': len(out_bin), 'byteLength': arr.nbytes})
        out_bin.extend(arr.tobytes())
        a = {'bufferView': None, 'componentType': ctype, 'count': len(arr), 'type': typ}
        if minmax:
            a['min'] = arr.min(0).tolist()
            a['max'] = arr.max(0).tolist()
        accs.append(a)
        return len(accs) - 1

    n_mat0 = len(cg['materials'])
    sora_mats = {}
    hand_pts = []
    finger_pts = []
    report = {}
    for ni in mesh_nodes:
        node = sg['nodes'][ni]
        mesh = sg['meshes'][node['mesh']]
        prims = []
        for p in mesh['primitives']:
            at = p['attributes']
            P = acc(sg, sb, at['POSITION'])
            UV = acc(sg, sb, at['TEXCOORD_0'])
            J = acc(sg, sb, at['JOINTS_0']).astype(int)
            W = acc(sg, sb, at['WEIGHTS_0'])
            idx = acc(sg, sb, p['indices']).reshape(-1).astype(np.uint32)
            # skinned meshes ignore their node transform: bind pose in scene space = root_w @ P
            Pw =(root_w @ np.c_[P, np.ones(len(P))].T).T[:, :3]
            newP = np.zeros_like(Pw)
            newJ = np.zeros((len(P), 4), np.uint16)
            newW = np.zeros((len(P), 4), np.float32)
            for v in range(len(P)):
                acc_w = {}
                tot = 0.0
                for c in range(4):
                    w = W[v, c]
                    if w <= 0:
                        continue
                    bname = int(sg['nodes'][node_of_slot[J[v, c]]]['name'][4:])
                    pv = apply(fpose[bname], Pw[v]) if bname in fpose else Pw[v]
                    newP[v] += w * apply(segs[slot_seg[J[v, c]]], pv)
                    tot += w
                    cbn = slot_cloud[J[v, c]]
                    acc_w[cbn] = acc_w.get(cbn, 0) + w
                newP[v] /= tot or 1
                top = sorted(acc_w.items(), key=lambda kv: -kv[1])[:4]
                s = sum(w for b, w in top) or 1
                for c, (b, w) in enumerate(top):
                    newJ[v, c] = b
                    newW[v, c] = w / s
                for b, w in top:
                    report[cnames[b]] = report.get(cnames[b], 0) + w / s
                if top and cnames[top[0][0]] in ('r_hand', 'r_fing1a', 'r_fing3b'):
                    hand_pts.append(newP[v].copy())
                if top and cnames[top[0][0]] == 'r_fing3b':
                    finger_pts.append(newP[v].copy())
            mi = p.get('material', 0)
            if mi not in sora_mats:
                sora_mats[mi] = n_mat0 + len(sora_mats)
            prims.append({'attributes': {
                'POSITION': add(newP.astype(np.float32), 5126, 'VEC3', minmax=True),
                'TEXCOORD_0': add(UV.astype(np.float32), 5126, 'VEC2'),
                'JOINTS_0': add(newJ, 5123, 'VEC4'),
                'WEIGHTS_0': add(newW, 5126, 'VEC4')},
                'indices': add(idx, 5125, 'SCALAR'), 'material': sora_mats[mi]})
        meshes.append({'name': 'p_sev100|sora_%s' % node['name'], 'primitives': prims})

    # ----- assemble: Cloud's glTF minus its body meshes, plus Sora's -----
    g = json.loads(json.dumps(cg))
    for f in cg.get('images', []):
        shutil.copy(os.path.join(os.path.dirname(cloud_path), f['uri']), out_dir)
    # drop Cloud's body meshes (gltf2gmo.py reads every mesh, not just the ones nodes use)
    kept = [i for i, m in enumerate(g['meshes']) if not m['name'].startswith('p_sev100|')]
    new_index = {old: k for k, old in enumerate(kept)}
    g['meshes'] = [g['meshes'][i] for i in kept]
    for n in g['nodes']:
        if 'mesh' in n:
            if n['mesh'] in new_index:
                n['mesh'] = new_index[n['mesh']]
            else:
                n.pop('mesh')
                n.pop('skin', None)
                n['name'] += '_removed'
    nb = len(g['bufferViews'])
    na = len(g['accessors'])
    for a in accs:
        a['bufferView'] = nb + accs.index(a)
    for m in meshes:
        for p in m['primitives']:
            p['attributes'] = {k: v + na for k, v in p['attributes'].items()}
            p['indices'] += na
    g['bufferViews'] += views
    g['accessors'] += accs
    base_mesh = len(g['meshes'])
    g['meshes'] += meshes
    for k in range(len(meshes)):
        g['nodes'].append({'name': meshes[k]['name'], 'mesh': base_mesh + k, 'skin': 0})
        g['scenes'][0]['nodes'].append(len(g['nodes']) - 1)
    # materials + textures
    for smi, new_i in sorted(sora_mats.items(), key=lambda kv: kv[1]):
        sm = sg['materials'][smi]
        stex = sm['pbrMetallicRoughness']['baseColorTexture']['index']
        simg = sg['images'][sg['textures'][stex]['source']]
        bv = sg['bufferViews'][simg['bufferView']]
        import io
        im = Image.open(io.BytesIO(sb[0][bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']]))
        im = im.convert('RGBA').resize((tex_size, tex_size), Image.LANCZOS)
        fn = 'sora_tex%d.png' % smi
        im.save(os.path.join(out_dir, fn))
        g['images'].append({'uri': fn, 'name': 'p_sev120_sora%d.tga' % smi})
        g['textures'].append({'source': len(g['images']) - 1})
        g['materials'].append({'name': 'sora%d' % smi, 'doubleSided': True,
                               'pbrMetallicRoughness': {'baseColorTexture': {'index': len(g['textures']) - 1},
                                                        'metallicFactor': 0},
                               'extras': {'base_material': 2}})
    base = 'sora_fit'
    open(os.path.join(out_dir, base + '.bin'), 'wb').write(bytes(out_bin))
    g['buffers'].append({'byteLength': len(out_bin), 'uri': base + '.bin'})
    g['asset']['generator'] = 'dissidia-012-sora fit_sora.py'
    json.dump(g, open(os.path.join(out_dir, base + '.gltf'), 'w'))
    for b in g['buffers'][:1]:
        shutil.copy(os.path.join(os.path.dirname(cloud_path), b['uri']), out_dir)
    allp = np.concatenate([acc(g, [cb[0], bytes(out_bin)], m['primitives'][0]['attributes']['POSITION'])
                           for m in meshes])
    print('Sora joints (scene): hip %s shoulder L %s head %s' % (SJ(2).round(3), SJ(78).round(3), SJ(140).round(3)))
    print('fitted bounds', allp.min(0).round(3), allp.max(0).round(3))
    print('weights per Cloud bone:', {k: round(v) for k, v in sorted(report.items(), key=lambda kv: -kv[1])})
    hs = segs['r_hand']
    gp = apply(hs, grip['grip'])
    ga = hs[:3, :3] @ grip['axis']
    gp = centre_in_fist(np.array(hand_pts), gp, ga / np.linalg.norm(ga))
    # per Sora bone: the map applied to its vertices (segment ∘ hand pose) and its Cloud bone, for kh2_retarget.py
    bone_seg, bone_cloud = {}, {}
    for k, j in node_of_slot.items():
        bn = int(sg['nodes'][j]['name'][4:])
        bone_seg[bn] = slot_seg[k]
        bone_cloud[bn] = cnames[slot_cloud[k]]
    json.dump({'segs': {k: v.tolist() for k, v in segs.items()}, 'bone_seg': bone_seg, 'bone_cloud': bone_cloud,
               'fpose': {b: m.tolist() for b, m in fpose.items()}},
              open(os.path.join(out_dir, base + '.map.json'), 'w'))
    # palm normal: KH2 bind hands are palm-down (-Y); through the right hand's fit map → where the guard should go
    pn = hs[:3, :3] @ np.array([0.0, -1.0, 0.0])
    json.dump({'grip': gp.tolist(), 'axis': (ga / np.linalg.norm(ga)).tolist(),
               'fingers': np.mean(finger_pts, 0).tolist(), 'palm_normal': (pn / np.linalg.norm(pn)).tolist()},
              open(os.path.join(out_dir, base + '.grip.json'), 'w'))
    print('right fist grip (bind) %s axis %s' % (gp.round(3), (ga / np.linalg.norm(ga)).round(3)))
    print('wrote', os.path.join(out_dir, base + '.gltf'))


if __name__ == '__main__':
    main()
