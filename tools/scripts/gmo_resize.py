"""Give a fighter GMO Sora's body proportions: change bone LENGTHS in the skeleton + every motion, in place.

  python3 -I gmo_resize.py BASE.gmo SORA.glb OUT.gmo

Cloud's motions key bone translations as constants (1 key, = bone length in the parent's frame) for every bone
except camera2_include/camera_include/root/r_wep/trans_include (real movement) and belt/shldarmor (tiny).
So a bone b gets ratio r_b = Sora segment / Cloud segment (RATIO table) and we scale:
  - its 0x8048 rest translation in both models (_000A and model-0), DISTANCE (0x80F1) of its parent,
  - its translate fcurve values in every motion (half floats, same size → nothing moves in the file),
  - the inverse bind matrices (0x8045) of skinned bones: joint positions re-chained with the new lengths,
and the hip height: root's translate Y (+ rest) gets DELTA so Sora's feet stay on the floor; the draw bones
p_sev100/wep0/wep1 (rest (0, -1.085, 0) under root) get -DELTA. Prints the new joint table.
"""
import json
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gmo  # noqa: E402
from fit_sora import acc, load_gltf  # noqa: E402

# Cloud bone -> (Sora joint A, Sora joint B, Cloud joint A, Cloud joint B): r = |SB - SA| / |CB - CA|
# (Sora joints = KH2 bone numbers; right side mirrored: legs +29, arms +92)
RATIO_L = {
    'l_femur_c': (2, 11, 'hip', 'l_femur'),
    'l_femur': (2, 11, 'hip', 'l_femur'),
    'l_tibia': (11, 12, 'l_femur', 'l_tibia'),
    'l_foot': (12, 15, 'l_tibia', 'l_foot'),
    'l_toe': (15, 18, 'l_foot', 'l_toe'),
    'chest': (2, 67, 'waist', 'chest'),
    'l_clavicle': (67, 75, 'chest', 'l_clavicle'),
    'shldarmor': (67, 75, 'chest', 'l_clavicle'),
    'l_uparm_c': (75, 78, 'l_clavicle', 'l_uparm'),
    'l_uparm': (75, 78, 'l_clavicle', 'l_uparm'),
    'l_arm_help': (75, 78, 'l_clavicle', 'l_uparm'),
    'l_foarm': (78, 79, 'l_uparm', 'l_foarm'),
    'l_hand': (79, 85, 'l_foarm', 'l_hand'),
    'l_fing1a': (85, 98, 'l_hand', 'l_fing3b'),
    'l_fing3b': (85, 98, 'l_hand', 'l_fing3b'),
    'neck': (67, 137, 'chest', 'neck'),
    'head': (137, 140, 'neck', 'head'),
}
DRAW_BONES = ('p_sev100', 'wep0', 'wep1')


def mirror_tbl(t):
    out = dict(t)
    for k, (sa, sb, ca, cb) in t.items():
        if k.startswith('l_') or k == 'shldarmor':
            m = lambda j: j + 29 if 10 <= j <= 34 else j + 92 if 74 <= j <= 135 else j  # noqa: E731
            if k.startswith('l_'):
                out['r_' + k[2:]] = (m(sa), m(sb), ca.replace('l_', 'r_'), cb.replace('l_', 'r_'))
    return out


def args_of(d, o, hs, size):
    return {at: (ao, asz) for ao, at, ahs, asz in gmo.chunks(d, o + hs, o + size)}


def main():
    base, sora, out = sys.argv[1:4]
    d = bytearray(open(base, 'rb').read())
    items = []
    gmo.walk(d, 16, len(d), 0, items)
    models = [i for i in items if i[2] == 0x03]
    # bones per model (name -> chunk), model-0's skin lists
    bones = {}
    for m in models:
        bones[m[5]] = [(i[5], i) for i in items if i[2] == 0x04 and m[1] < i[1] < m[1] + m[4]]
    m0 = bones['model-0']
    names = [n for n, _ in m0]
    parent = {}
    for n, it in m0:
        a = args_of(d, it[1], it[3], it[4])
        parent[n] = names[struct.unpack_from('<I', d, a[0x8041][0] + 8)[0] & 0xFFF] if 0x8041 in a else None
    # Cloud bind joints from the inverse bind matrices
    ibm_at = {}            # bone name -> list of (file offset of the 4x4, owner)
    bind = {}
    for n, it in m0:
        a = args_of(d, it[1], it[3], it[4])
        if 0x8044 in a and 0x8045 in a:
            cnt = struct.unpack_from('<I', d, a[0x8044][0] + 8)[0]
            refs = [r & 0xFFF for r in struct.unpack_from('<%dI' % cnt, d, a[0x8044][0] + 12)]
            for k, r in enumerate(refs):
                off = a[0x8045][0] + 12 + 64 * k
                mtx = np.array(struct.unpack_from('<16f', d, off)).reshape(4, 4).T
                bind[names[r]] = np.linalg.inv(mtx)
                ibm_at.setdefault(names[r], []).append(off)

    def CJ(n):
        return bind[n][:3, 3]

    # Sora joints (scene coordinates = same Y-up space as the GMO)
    sg, sb = load_gltf(sora)
    sk = sg['skins'][0]
    sibm = acc(sg, sb, sk['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    from fit_sora import world_mats
    sw, _ = world_mats(sg)
    root_w = sw[sk['joints'][0]] @ sibm[0]
    sj = {sg['nodes'][j]['name']: (root_w @ np.linalg.inv(sibm[k]))[:3, 3] for k, j in enumerate(sk['joints'])}

    def SJ(i):
        return sj['Bone%d' % i]

    ratio = {}
    for b, (sa, sb_, ca, cb) in mirror_tbl(RATIO_L).items():
        ratio[b] = np.linalg.norm(SJ(sb_) - SJ(sa)) / np.linalg.norm(CJ(cb) - CJ(ca))

    # new bind joints: chain from hip with the new lengths (same world rotations)
    order = []

    def visit(n):
        order.append(n)
        for c in names:
            if parent[c] == n:
                visit(c)
    for n in names:
        if parent[n] is None:
            visit(n)
    # hip height: drop so the new ankle lands on Sora's ankle height
    leg = ['l_femur', 'l_tibia', 'l_foot']
    new_ankle = CJ('hip')[1] + sum(ratio[b] * (CJ(b)[1] - CJ(p)[1]) for b, p in zip(leg, ['hip'] + leg[:-1]))
    delta = SJ(15)[1] - new_ankle
    newj = {}
    for n in order:
        if n not in bind:
            continue
        a = parent[n]
        while a is not None and a not in bind:
            a = parent[a]
        if a is None:
            newj[n] = CJ(n) + np.array([0, delta, 0])
        else:
            newj[n] = newj[a] + ratio.get(n, 1.0) * (CJ(n) - CJ(a))

    # 1) inverse bind matrices
    for n, offs in ibm_at.items():
        w = bind[n].copy()
        w[:3, 3] = newj[n]
        ibm = np.linalg.inv(w)
        for off in offs:
            struct.pack_into('<16f', d, off, *ibm.T.reshape(-1))

    # 2) rest translations + DISTANCE in both models
    def scale_bone_args(model):
        for n, it in bones[model]:
            a = args_of(d, it[1], it[3], it[4])
            if 0x8048 in a:
                o = a[0x8048][0] + 8
                t = np.array(struct.unpack_from('<3f', d, o))
                if n in ratio:
                    t = t * ratio[n]
                elif n == 'root':
                    t = t + [0, delta, 0]
                elif n in DRAW_BONES:
                    t = t - [0, delta, 0]
                struct.pack_into('<3f', d, o, *t)
            if 0x80F1 in a:
                o, sz = a[0x80F1]
                raw = bytes(d[o + 8:o + sz])
                if raw.startswith(b'DISTANCE'):
                    kids = [c for c, _ in bones[model] if parent.get(c) == n and c in ratio]
                    if kids:
                        fo = o + sz - 4
                        v = struct.unpack_from('<f', d, fo)[0]
                        struct.pack_into('<f', d, fo, v * ratio[kids[0]])
    for model in bones:
        scale_bone_args(model)

    # 3) motions: translate fcurves
    from gmo_motion import motions
    mots, _, _ = motions(bytes(d))
    hits = 0
    for mname, o, s in mots:
        _, hs, _ = struct.unpack_from('<HHI', d, o)
        p = o + hs
        ents, fcs = [], []
        while p < o + s:
            t, h2, sz = struct.unpack_from('<HHI', d, p)
            if t == 0x80B3:
                for q in range(p + 8, p + sz, 16):
                    ref, ch, _, fi = struct.unpack_from('<IIIH', d, q)
                    ents.append((ref & 0xFFF, ch, fi))
            elif t == 0x0C:
                fcs.append((p, h2))
            p += sz
        for b, ch, fi in ents:
            if ch != 0x48:
                continue
            n = names[b]
            if n not in ratio and n != 'root' and n not in DRAW_BONES:
                continue
            fp, h2 = fcs[fi]
            fmt, dims, nk, _ = struct.unpack_from('<IIII', d, fp + h2)
            vo = fp + h2 + 16
            arr = np.frombuffer(bytes(d[vo:vo + nk * (1 + dims) * 2]), '<f2').reshape(nk, 1 + dims).astype(np.float64)
            if n in ratio:
                arr[:, 1:] *= ratio[n]
            elif n == 'root':
                arr[:, 2] += delta
            else:
                arr[:, 2] -= delta
            d[vo:vo + arr.size * 2] = arr.astype('<f2').tobytes()
            hits += 1
    open(out, 'wb').write(bytes(d))
    print('hip delta %.3f; %d translate curves changed' % (delta, hits))
    for n in sorted(ratio, key=names.index):
        if n.startswith('r_'):
            continue
        print('  %-11s x%.2f' % (n, ratio[n]))
    print('new joints:', {n: [round(x, 3) for x in newj[n]] for n in ('hip', 'l_femur', 'l_tibia', 'l_foot',
                                                                      'l_uparm', 'l_hand', 'neck', 'head')})
    json.dump({n: list(map(float, v)) for n, v in newj.items()}, open(out + '.joints.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
