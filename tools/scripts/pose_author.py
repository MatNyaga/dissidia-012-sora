"""Hand-made animations for Sora: key poses described as "point this bone that way", in-betweens filled in.

  python3 -I pose_author.py POSE_SCRIPT.py MODEL.gmo OUT.gmo SLOT      (e.g. tools/poses/win_light.py … _910A)

A pose script defines build(P) and returns a list of (frame, Pose). P is this module (helpers below).
World axes (model space): +Y up, +Z = the way Sora faces, +X = his LEFT side (his right hand is on -X).
- P.kh2(index, frame, variant=''): a pose taken from a baked KH2 animation (dumps/kh2anim), as a starting point.
- P.kh2_clip(index, variant=''): all frames of a KH2 animation (add them as keys one frame apart to play it).
- pose.hip_height(y): put the hips at height y (m).  LOOP = N in the script: the last N frames loop (default 6).
- pose.aim(bone, direction): turn the bone so it points that way (arm/leg/spine; the bone's children follow).
- pose.aim_keyblade(direction, roll=0): turn the right hand so the Keyblade blade points that way.
- pose.turn(bone, axis, degrees): extra rotation about a world axis (e.g. head tilt).
- pose.move_root(dx, dy, dz): shift the whole body (dy < 0 = crouch lower).
Keys are interpolated with ease-in/out (quaternion slerp per bone). The last key is held to its frame.
A key may be (frame, pose, 'lin'): the segment FROM that key to the next one runs at constant speed (spins: easing every
quarter turn made the intro twirl tick like a clock hand — Mat: "stiff").
"""
import copy
import glob
import importlib.util
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from fit_sora import acc, load_gltf  # noqa: E402
from kh2_retarget import (hierarchy_order, load_fitmap, mat_to_quat, ortho, quat_to_mat, read_skeleton,  # noqa: E402
                          solve_kh2, trs, write_motion)
from kh2anim import load_baked  # noqa: E402

AIM_CHILD = {'r_foot': 'r_toe', 'l_foot': 'l_toe', 'r_uparm': 'r_foarm', 'r_foarm': 'r_hand', 'l_uparm': 'l_foarm', 'l_foarm': 'l_hand',
             'r_femur': 'r_tibia', 'r_tibia': 'r_foot', 'l_femur': 'l_tibia', 'l_tibia': 'l_foot',
             'chest': 'neck', 'neck': 'head', 'waist': 'chest', 'r_clavicle': 'r_uparm', 'l_clavicle': 'l_uparm'}
SKEL = None
A = None
ORDER = None
KB_LOCAL = None          # Keyblade tip direction in r_hand's frame
FIT = os.path.join(ROOT, 'dumps/models/sora/fitn/sora_fit.map.json')
KEYGLTF = os.path.join(ROOT, 'dumps/models/sora/keyn/sora_fit_key.gltf')


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def rot_axis(axis, deg):
    a = unit(axis)
    t = np.radians(deg)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(t) * k + (1 - np.cos(t)) * k @ k


def rot_between(a, b):
    a, b = unit(a), unit(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-9:
        if c > 0:
            return np.eye(3)
        perp = unit(np.cross(a, [1, 0, 0] if abs(a[0]) < 0.9 else [0, 1, 0]))
        return rot_axis(perp, 180)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


class Pose:
    def __init__(self, locs):
        self.loc = {k: v.copy() for k, v in locs.items()}

    def copy(self):
        return Pose(self.loc)

    def world(self):
        names, parent = SKEL[0], SKEL[1]
        w = {}
        for n in ORDER:
            p = parent[n]
            w[n] = (w[p] if p else np.eye(4)) @ self.loc[n]
        return w

    def _set_world_rot(self, bone, R):
        w = self.world()
        p = SKEL[1][bone]
        pr = w[p][:3, :3] if p else np.eye(3)
        self.loc[bone][:3, :3] = ortho(pr.T @ R)

    def turn(self, bone, axis, deg):
        w = self.world()
        self._set_world_rot(bone, rot_axis(axis, deg) @ w[bone][:3, :3])
        return self

    def aim(self, bone, direction):
        w = self.world()
        cur = w[AIM_CHILD[bone]][:3, 3] - w[bone][:3, 3]
        self._set_world_rot(bone, rot_between(cur, direction) @ w[bone][:3, :3])
        return self

    def keyblade_dir(self):
        return self.world()['r_hand'][:3, :3] @ KB_LOCAL

    def aim_keyblade(self, direction, roll=0):
        w = self.world()
        R = rot_between(self.keyblade_dir(), direction) @ w['r_hand'][:3, :3]
        R = rot_axis(direction, roll) @ R
        self._set_world_rot('r_hand', R)
        return self

    def move_root(self, dx=0, dy=0, dz=0):
        self.loc['root'][:3, 3] += [dx, dy, dz]
        return self

    def hip_height(self, y):
        self.loc['root'][1, 3] = y
        return self


_baked = {}


def _frames(index, variant):
    if (index, variant) not in _baked:
        pat = '%03d_????%s.bin' % (index, variant)
        path = sorted(glob.glob(os.path.join(ROOT, 'dumps/kh2anim', pat)))[0]
        _baked[(index, variant)] = load_baked(path)[0]
    return _baked[(index, variant)]


def kh2(index, frame, variant=''):
    """one pose from a baked KH2 animation; variant = file suffix, e.g. '_s0.5' or '_v0.5x1_1x0.4'"""
    fr = _frames(index, variant)
    f = min(frame, len(fr) - 1)
    return Pose(solve_kh2(SKEL, A, fr[f:f + 1])[0])


def kh2_clip(index, variant=''):
    """every frame of a baked KH2 animation as poses (use as consecutive keys to play it inside a pose script)"""
    return [Pose(p) for p in solve_kh2(SKEL, A, _frames(index, variant))]


def ease(t):
    return t * t * (3 - 2 * t)


def slerp(q0, q1, t):
    if np.dot(q0, q1) < 0:
        q1 = -q1
    d = np.clip(np.dot(q0, q1), -1, 1)
    if d > 0.9995:
        q = q0 + t * (q1 - q0)
        return q / np.linalg.norm(q)
    th = np.arccos(d)
    return (np.sin((1 - t) * th) * q0 + np.sin(t * th) * q1) / np.sin(th)


def interpolate(keys):
    keys = sorted(keys, key=lambda k: k[0])
    frames = []
    for f in range(keys[-1][0] + 1):
        i = max(k for k in range(len(keys)) if keys[k][0] <= f)
        if i == len(keys) - 1:
            frames.append(copy.deepcopy(keys[i][1].loc))
            continue
        (fa, pa), (fb, pb) = keys[i][:2], keys[i + 1][:2]
        t = (f - fa) / (fb - fa)
        if 'lin' not in keys[i][2:]:
            t = ease(t)
        out = {}
        for n in pa.loc:
            q = slerp(mat_to_quat(pa.loc[n][:3, :3]), mat_to_quat(pb.loc[n][:3, :3]), t)
            out[n] = trs((1 - t) * pa.loc[n][:3, 3] + t * pb.loc[n][:3, 3], quat_to_mat(q))
        frames.append(out)
    return frames


def setup(model_bytes):
    global SKEL, A, ORDER, KB_LOCAL
    SKEL = read_skeleton(model_bytes)
    A = load_fitmap(FIT)
    ORDER = hierarchy_order(SKEL[0], SKEL[1])
    import json
    g, b = load_gltf(KEYGLTF)
    V = np.concatenate([acc(g, b, p['attributes']['POSITION']) for m in g['meshes'] if m['name'].startswith('wep1|')
                        for p in m['primitives']])
    grip = np.array(json.load(open(FIT.replace('.map.json', '.grip.json')))['grip'])
    tip = V[np.argmax(np.linalg.norm(V - grip, axis=1))]          # blade tip is the farthest point
    KB_LOCAL = SKEL[4]['r_hand'][:3, :3].T @ unit(tip - grip)


def main():
    script, model, out, slot = sys.argv[1:5]
    d = open(model, 'rb').read()
    setup(d)
    spec = importlib.util.spec_from_file_location('pose_script', script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    keys = mod.build(sys.modules[__name__])
    frames = interpolate(keys)
    open(out, 'wb').write(write_motion(d, slot, SKEL, frames, label=os.path.basename(script),
                                       loop_tail=getattr(mod, 'LOOP', None)))


if __name__ == '__main__':
    main()
