"""Helpers for KH2 motions baked by tools/kh2bake/bake (OpenKH Kh2AnimEmu): load frames, pose Sora's mesh.

  python3 -I kh2anim.py BAKED.bin OUT.obj FRAME     (posed P_EX100 mesh as OBJ, glTF space = 0.01 x KH2)
"""
import json
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fit_sora import acc, load_gltf, world_mats  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
DECODED = os.path.join(ROOT, 'kh2_export/model/P_EX100_decoded.json')
SORA_GLB = os.path.join(ROOT, 'kh2_export/model/sora.glb')


def load_baked(path):
    """-> (frames[F, B, 4, 4] column-convention world matrices in KH2 units, fps, frame_end, frame_loop)"""
    d = open(path, 'rb').read()
    nb, nf, fps, fe, fl = struct.unpack_from('<iifff', d, 0)
    m = np.frombuffer(d, '<f4', nb * nf * 16, 20).reshape(nf, nb, 4, 4).astype(np.float64)
    return m.transpose(0, 1, 3, 2), fps, fe, fl


def kh2_rest():
    """-> [B, 4, 4] rest world matrices (KH2 units) from the decoder"""
    return np.array([np.array(b['matrix']) for b in json.load(open(DECODED))['bones']])


def sora_mesh():
    """-> list of (P[n,3] KH2 units bind, UV, idx, J (bone numbers), W, material)"""
    g, b = load_gltf(SORA_GLB)
    w, _ = world_mats(g)
    sk = g['skins'][0]
    ibm = acc(g, b, sk['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    root = w[sk['joints'][0]] @ ibm[0]
    slot2bone = [int(g['nodes'][j]['name'][4:]) for j in sk['joints']]
    out = []
    for n in g['nodes']:
        if 'mesh' not in n:
            continue
        for p in g['meshes'][n['mesh']]['primitives']:
            at = p['attributes']
            P = acc(g, b, at['POSITION'])
            P = (root @ np.c_[P, np.ones(len(P))].T).T[:, :3] * 100.0
            J = np.vectorize(lambda s: slot2bone[s])(acc(g, b, at['JOINTS_0']).astype(int))
            out.append((P, acc(g, b, at['TEXCOORD_0']), acc(g, b, p['indices']).reshape(-1).astype(int), J,
                        acc(g, b, at['WEIGHTS_0']), p.get('material', 0)))
    return out


def pose(mesh, frame_mats, rest):
    inv = np.linalg.inv(rest)
    skin = frame_mats @ inv
    res = []
    for P, UV, idx, J, W, mat in mesh:
        Q = np.zeros_like(P)
        H = np.c_[P, np.ones(len(P))]
        for c in range(4):
            M = skin[J[:, c]]
            Q += W[:, c:c + 1] * np.einsum('nij,nj->ni', M, H)[:, :3]
        res.append((Q, UV, idx, mat))
    return res


def main():
    frames, fps, fe, fl = load_baked(sys.argv[1])
    f = int(sys.argv[3])
    posed = pose(sora_mesh(), frames[f], kh2_rest())
    with open(sys.argv[2], 'w') as o:
        base = 1
        for Q, UV, idx, mat in posed:
            for q in Q * 0.01:
                o.write('v %f %f %f\n' % tuple(q))
            for t in range(0, len(idx), 3):
                o.write('f %d %d %d\n' % tuple(base + idx[t:t + 3]))
            base += len(Q)
    allq = np.concatenate([q[0] for q in posed]) * 0.01
    print('frame %d: bounds %s .. %s' % (f, allq.min(0).round(3), allq.max(0).round(3)))


if __name__ == '__main__':
    main()
