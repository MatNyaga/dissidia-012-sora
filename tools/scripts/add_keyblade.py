"""Put KH2's Kingdom Key (kingdom_key.glb) into a skin glTF as Cloud's weapon parts (rigid, follow r_wep).

  python3 -I add_keyblade.py SKIN.gltf KEYBLADE.glb OUT_DIR [PARTS] [FLIP]

- SKIN.gltf: e.g. fit_sora.py's output (Cloud skeleton + bind pose, Cloud's wep0/wep1 meshes still inside).
- The Keyblade's grip (its Bone0) goes onto Cloud's sword grip (bone r_wep); its long axis (grip → tip) is turned
  onto the Buster Sword's (wep1) long axis, its flat side onto the sword's flat side (FLIP=1 turns the teeth over).
- PARTS = comma list of Cloud weapon parts to replace (default "wep0,wep1": wep1 = Buster Sword; wep0 = second
  sword part, probably EX Mode's Ultima Weapon). Cloud's meshes for those parts are dropped.
- Build with: REBUILD_WEAPONS=1 NEW_SCALE=1 gltf2gmo.py BASE.gmo OUT_DIR/<name>.gltf OUT.gmo
  (NEW_SCALE needs every weapon part rebuilt; the keychain sticks out of Cloud's model box).
"""
import io
import json
import os
import shutil
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fit_sora import acc, load_gltf, world_mats  # noqa: E402

SCALE = float(os.environ.get('KEY_SCALE', 1.1))   # 1.1 for the Cloud-size fit; 1.0 on a gmo_resize.py skeleton
TEX = (256, 128)
GRIP_SHIFT = float(os.environ.get('GRIP_SHIFT', 0))   # slide the Keyblade along its axis (m)


def frame(P, origin, tip_hint):
    """Orthonormal frame: x = long axis (towards tip_hint), y = 2nd principal axis (blade width), z = x × y."""
    c = P.mean(0)
    _, _, vt = np.linalg.svd(P - c)
    x = vt[0] if np.dot(vt[0], tip_hint - origin) > 0 else -vt[0]
    y = vt[1] - np.dot(vt[1], x) * x
    y /= np.linalg.norm(y)
    return np.stack([x, y, np.cross(x, y)], 1)


def main():
    skin_path, key_path, out_dir = sys.argv[1:4]
    parts = (sys.argv[4] if len(sys.argv) > 4 else 'wep0,wep1').split(',')
    flip = len(sys.argv) > 5 and sys.argv[5] == '1'
    os.makedirs(out_dir, exist_ok=True)
    g, bufs = load_gltf(skin_path)
    src_dir = os.path.dirname(skin_path)

    # Cloud's sword: grip = r_wep bind position, frame from the Buster Sword's vertices
    names = [g['nodes'][j]['name'] for j in g['skins'][0]['joints']]
    ibm = acc(g, bufs, g['skins'][0]['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    r_wep = np.linalg.inv(ibm[names.index('r_wep')])[:3, 3]
    sword = np.concatenate([acc(g, bufs, p['attributes']['POSITION']) for m in g['meshes']
                            if m['name'].startswith('wep1|') for p in m['primitives']])
    far = sword[np.argmax(np.linalg.norm(sword - r_wep, axis=1))]
    Fc = frame(sword, r_wep, far)
    # fit_sora.py's closed right fist: grip there, long axis through the fist (blade side as the sword's)
    gj = os.path.splitext(skin_path)[0] + '.grip.json'
    if not os.path.exists(gj) and os.environ.get('GRIP_JSON'):
        gj = os.environ['GRIP_JSON']
    fingers = None
    palm = None
    if os.path.exists(gj):
        gd = json.load(open(gj))
        r_wep = np.array(gd['grip'])
        x = np.array(gd['axis'])
        x = x if np.dot(x, Fc[:, 0]) > 0 else -x
        y = Fc[:, 1] - np.dot(Fc[:, 1], x) * x
        y /= np.linalg.norm(y)
        Fc = np.stack([x, y, np.cross(x, y)], 1)
        print('using the fist grip from', gj)
        fingers = np.array(gd['fingers']) if 'fingers' in gd else None
        palm = np.array(gd['palm_normal']) if 'palm_normal' in gd else None

    # Keyblade: grip = Bone0, tip = farthest vertex from the grip on the blade side (the chain hangs the other way)
    kg, kb = load_gltf(key_path)
    kw, _ = world_mats(kg)
    ks = kg['skins'][0]
    kibm = acc(kg, kb, ks['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    kroot = kw[ks['joints'][0]] @ kibm[0]
    grip = (kroot @ np.linalg.inv(kibm[0]))[:3, 3]
    chain_end = (kroot @ np.linalg.inv(kibm[-1]))[:3, 3]
    kprims = []
    for n in kg['nodes']:
        if 'mesh' in n:
            for p in kg['meshes'][n['mesh']]['primitives']:
                P = acc(kg, kb, p['attributes']['POSITION'])
                P = (kroot @ np.c_[P, np.ones(len(P))].T).T[:, :3]
                kprims.append((P, acc(kg, kb, p['attributes']['TEXCOORD_0']),
                               acc(kg, kb, p['indices']).reshape(-1).astype(np.uint32), p.get('material', 0)))
    allk = np.concatenate([k[0] for k in kprims])
    Fk = frame(allk, grip, grip + (grip - chain_end))
    if flip:
        Fk[:, 1:] *= -1
    R = Fc @ Fk.T
    place = lambda P: ((P - grip) * SCALE) @ R.T + r_wep + GRIP_SHIFT * Fc[:, 0]  # noqa: E731
    if fingers is not None:
        # roll the Keyblade about its axis so the guard loop wraps the curled fingers (not the wrist)
        base_place = place
        allp = base_place(allk)
        ax = Fc[:, 0]
        off = allp - r_wep
        tt = off @ ax
        perp = off - np.outer(tt, ax)
        guard = perp[(np.abs(tt) < 0.12) & (np.linalg.norm(perp, axis=1) > 0.06)].mean(0)
        # the guard loop goes on the palm side (the fingers wrap the handle from there); the finger centroid is only
        # a fallback — with a tight fist it sits almost on the handle and gives a random direction
        want = palm if palm is not None else fingers - r_wep
        want = want - np.dot(want, ax) * ax
        g1, w1 = guard / np.linalg.norm(guard), want / np.linalg.norm(want)
        ang = np.arctan2(np.dot(np.cross(g1, w1), ax), np.dot(g1, w1)) + np.radians(float(os.environ.get('KEY_ROLL', 0)))
        k = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
        Rr = np.eye(3) + np.sin(ang) * k + (1 - np.cos(ang)) * k @ k
        place = lambda P: (base_place(P) - r_wep) @ Rr.T + r_wep  # noqa: E731
        print('Keyblade rolled %.0f deg so the guard covers the fingers' % np.degrees(ang))
    mp = os.path.splitext(skin_path)[0] + '.map.json'
    if os.environ.get('KH2_ATTACH', '178') != 'off' and os.path.exists(mp):
        # KH2's own grip: the Keyblade's root bone sits on Sora's right palm bone (178); its stored bone-0
        # transform is only a display placement. Bind = fit map of that bone ∘ palm bind ∘ inverse(bone 0).
        import json as _j
        from kh2anim import kh2_rest
        fm = _j.load(open(mp))
        att = int(os.environ.get('KH2_ATTACH', '178'))
        Aatt = np.array(fm['segs'][fm['bone_seg'][str(att)]])
        meta = _j.load(open(os.path.join(os.path.dirname(key_path), 'metadata.json')))
        b0 = meta['bones'][0]
        rx, ry, rz = b0['rotation']
        cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
        Rk = (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
              @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]))
        KB0 = np.eye(4)
        KB0[:3, :3] = Rk
        KB0[:3, 3] = b0['translation']
        M = Aatt @ np.diag([0.01, 0.01, 0.01, 1]) @ kh2_rest()[att] @ np.linalg.inv(KB0) @ np.diag([100, 100, 100, 1.0])
        place = lambda P: (np.c_[P, np.ones(len(P))] @ M.T)[:, :3]  # noqa: E731
        print('Keyblade attached the KH2 way (Sora bone %d)' % att)

    # drop Cloud's meshes for the replaced parts
    kept = [i for i, m in enumerate(g['meshes']) if m['name'].split('|')[0] not in parts]
    new_index = {old: k for k, old in enumerate(kept)}
    g['meshes'] = [g['meshes'][i] for i in kept]
    for n in g['nodes']:
        if 'mesh' in n:
            if n['mesh'] in new_index:
                n['mesh'] = new_index[n['mesh']]
            else:
                n.pop('mesh')
                n.pop('skin', None)

    # texture + material (template: Cloud's sword material = 1)
    img = kg['images'][kg['textures'][kg['materials'][kprims[0][3]]['pbrMetallicRoughness']['baseColorTexture']
                                      ['index']]['source']]
    if 'uri' in img:
        im = Image.open(os.path.join(os.path.dirname(key_path), img['uri']))
    else:
        bv = kg['bufferViews'][img['bufferView']]
        o = bv.get('byteOffset', 0)
        im = Image.open(io.BytesIO(kb[0][o:o + bv['byteLength']]))
    im = im.convert('RGBA').resize(TEX, Image.LANCZOS)
    kname = os.path.splitext(os.path.basename(key_path))[0]          # e.g. kingdom_key, ultima_weapon
    im.save(os.path.join(out_dir, kname + '.png'))
    tex_no = sum(1 for i in g['images'] if i.get('name', '').startswith('p_sev120_key')) + 1
    g['images'].append({'uri': kname + '.png', 'name': 'p_sev120_key%02d.tga' % tex_no})
    g['textures'].append({'source': len(g['images']) - 1})
    g['materials'].append({'name': kname, 'doubleSided': True,
                           'pbrMetallicRoughness': {'baseColorTexture': {'index': len(g['textures']) - 1},
                                                    'metallicFactor': 0}, 'extras': {'base_material': 1}})
    mat = len(g['materials']) - 1

    # new buffer with the Keyblade meshes (one per part), 100% r_wep
    out = bytearray()
    bi = len(g['buffers'])

    def add(arr, ctype, typ, minmax=False):
        arr = np.ascontiguousarray(arr)
        while len(out) % 4:
            out.append(0)
        g['bufferViews'].append({'buffer': bi, 'byteOffset': len(out), 'byteLength': arr.nbytes})
        out.extend(arr.tobytes())
        a = {'bufferView': len(g['bufferViews']) - 1, 'componentType': ctype, 'count': len(arr), 'type': typ}
        if minmax:
            a['min'], a['max'] = arr.min(0).tolist(), arr.max(0).tolist()
        g['accessors'].append(a)
        return len(g['accessors']) - 1
    jw = names.index('r_wep')
    for part in parts:
        prims = []
        for P, UV, idx, _ in kprims:
            Q = place(P).astype(np.float32)
            J = np.zeros((len(Q), 4), np.uint16)
            J[:, 0] = jw
            W = np.zeros((len(Q), 4), np.float32)
            W[:, 0] = 1
            prims.append({'attributes': {'POSITION': add(Q, 5126, 'VEC3', True), 'TEXCOORD_0': add(
                UV.astype(np.float32), 5126, 'VEC2'), 'JOINTS_0': add(J, 5123, 'VEC4'),
                'WEIGHTS_0': add(W, 5126, 'VEC4')}, 'indices': add(idx, 5125, 'SCALAR'), 'material': mat})
        g['meshes'].append({'name': '%s|%s' % (part, kname), 'primitives': prims})
        g['nodes'].append({'name': '%s|%s' % (part, kname), 'mesh': len(g['meshes']) - 1, 'skin': 0})
        g['scenes'][0]['nodes'].append(len(g['nodes']) - 1)
    name = os.path.splitext(os.path.basename(skin_path))[0] + '_key'
    open(os.path.join(out_dir, name + '.bin'), 'wb').write(bytes(out))
    g['buffers'].append({'byteLength': len(out), 'uri': name + '.bin'})
    for f in [b['uri'] for b in g['buffers'][:-1]] + [i['uri'] for i in g['images'][:-1]]:
        if os.path.abspath(os.path.join(src_dir, f)) != os.path.abspath(os.path.join(out_dir, f)):
            shutil.copy(os.path.join(src_dir, f), out_dir)
    json.dump(g, open(os.path.join(out_dir, name + '.gltf'), 'w'))
    tipk = place(allk)
    print('grip -> r_wep %s; Keyblade bounds %s .. %s' % (r_wep.round(3), tipk.min(0).round(3), tipk.max(0).round(3)))
    print('wrote', os.path.join(out_dir, name + '.gltf'))


if __name__ == '__main__':
    main()
