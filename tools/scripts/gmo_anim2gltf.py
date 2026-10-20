"""Add a GMO's motions (animations) to a gmo2gltf.py skin export, as glTF animations (preview in Blender).

  python3 -I gmo_anim2gltf.py MODEL.gmo SKIN.gltf OUT.gltf MOTION [MOTION ...]     (e.g. _910A _000A)

- SKIN.gltf: gmo2gltf.py output (node i = bone i). OUT.gltf is written next to SKIN.gltf (shares its .bin/PNGs).
- Motion = 0x80B1 frame range, 0x80B2 fps, 0x80B3 entries (bone, channel 0x48 T / 0x4B R / 0x4D S, fcurve index),
  fcurve = u32 format (0x80 half floats; low bits: 0 = step/1 key, 1 = linear, 4 = quaternion slerp), u32 dims,
  u32 key count, u32 0, keys = half frame + dims × half. Rotations are quaternions (x, y, z, w).
"""
import json
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gmo_motion import motions  # noqa: E402


def read_motion(d, o, s):
    """-> dict(frames=(f0, f1), fps, curves=[(bone, channel, times[], values[n, dims], interp)])"""
    _, hs, _ = struct.unpack_from('<HHI', d, o)
    p = o + hs
    ents, fcs = [], []
    frames, fps = (0, 0), 30.0
    while p < o + s:
        t, h2, sz = struct.unpack_from('<HHI', d, p)
        if t == 0x80B1:
            frames = struct.unpack_from('<ff', d, p + 8)
        elif t == 0x80B2:
            fps = struct.unpack_from('<f', d, p + 8)[0]
        elif t == 0x80B3:
            for q in range(p + 8, p + sz, 16):
                ref, ch, _, fi = struct.unpack_from('<IIIH', d, q)
                ents.append((ref & 0xFFF, ch, fi))
        elif t == 0x0C:
            fcs.append((p, h2))
        p += sz
    curves = []
    for b, ch, fi in ents:
        fp, h2 = fcs[fi]
        fmt, dims, nk, _ = struct.unpack_from('<IIII', d, fp + h2)
        if not fmt & 0x80:
            raise SystemExit('fcurve format %#x not handled' % fmt)
        raw = np.frombuffer(d, '<f2', nk * (1 + dims), fp + h2 + 16).reshape(nk, 1 + dims).astype(np.float64)
        curves.append((b, ch, raw[:, 0], raw[:, 1:], fmt & 0xF))
    return {'frames': frames, 'fps': fps, 'curves': curves}


def main():
    gmo_path, skin_path, out_path = sys.argv[1:4]
    want = sys.argv[4:]
    d = open(gmo_path, 'rb').read()
    mots = {n: (o, s) for n, o, s in motions(d)[0]}
    g = json.load(open(skin_path))
    out = bytearray()
    bi = len(g['buffers'])

    def add(arr, typ, minmax=False):
        arr = np.ascontiguousarray(arr, np.float32)
        while len(out) % 4:
            out.append(0)
        g['bufferViews'].append({'buffer': bi, 'byteOffset': len(out), 'byteLength': arr.nbytes})
        out.extend(arr.tobytes())
        a = {'bufferView': len(g['bufferViews']) - 1, 'componentType': 5126, 'count': len(arr), 'type': typ}
        if minmax:
            a['min'], a['max'] = [float(arr.min())], [float(arr.max())]
        g['accessors'].append(a)
        return len(g['accessors']) - 1
    g.setdefault('animations', [])
    for name in want:
        m = read_motion(d, *mots[name])
        samplers, channels = [], []
        for b, ch, times, vals, interp in m['curves']:
            path = {0x48: 'translation', 0x4B: 'rotation', 0x4D: 'scale'}[ch]
            t = times / m['fps']                  # keys are absolute frames (the 0x80B1 range is only the loop part)
            if len(t) == 1:                       # constant: two keys so every importer keeps it
                t = np.array([0.0, max(m['frames'][1] / m['fps'], 1 / 30)])
                vals = np.repeat(vals, 2, 0)
            if path == 'rotation':
                vals = vals / np.linalg.norm(vals, axis=1, keepdims=True)
            samplers.append({'input': add(t, 'SCALAR', True), 'output': add(vals, 'VEC4' if path == 'rotation'
                                                                             else 'VEC3'),
                             'interpolation': 'STEP' if interp == 0 and len(times) > 1 else 'LINEAR'})
            channels.append({'sampler': len(samplers) - 1, 'target': {'node': b, 'path': path}})
        g['animations'].append({'name': name, 'samplers': samplers, 'channels': channels})
        print('%s: frames %g-%g @ %g fps, %d curves' % (name, m['frames'][0], m['frames'][1], m['fps'],
                                                      len(m['curves'])))
    binname = os.path.splitext(os.path.basename(out_path))[0] + '_anim.bin'
    open(os.path.join(os.path.dirname(out_path), binname), 'wb').write(bytes(out))
    g['buffers'].append({'byteLength': len(out), 'uri': binname})
    json.dump(g, open(out_path, 'w'))
    print('wrote', out_path)


if __name__ == '__main__':
    main()
