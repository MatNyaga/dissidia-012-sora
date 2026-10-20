"""Offline EX Burst camera check: draw what the burst camera (bone 1 camera_include of the attacker's motion) sees.

Model space = the attacker's burst anchor (the victim's reference point, 0.9 m above the victim's feet; measured in
game, notes/ex-burst-controller.md §15). Camera bone: translate = eye, local -Z = look, +Y = up, scale z = FOV in
degrees (taken as vertical FOV, 480x272 screen). Attacker = skeleton of the motion (blue, weapon bones orange);
victim = the same skeleton in idle (_000A frame 0) at (0, -0.9, 0) facing the attacker (red); floor grid at y = -0.9.
Stick figures only (no skin): enough to see whether both fighters are in frame and how big.

  python3 -I gmo_camview.py MODEL.gmo MOTION OUT.png [FRAME,FRAME,...] [--fov-default 45]
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gmo_anim2gltf import read_motion  # noqa: E402
from gmo_fk import sample  # noqa: E402
from gmo_motion import motions  # noqa: E402
from kh2_retarget import hierarchy_order, quat_to_mat, read_skeleton, trs  # noqa: E402

W, H = 480, 272
ANCHOR_Y = 0.9
LOOK = float(os.environ.get("CAM_LOOK", "-1"))    # -1: look = bone matrix * (0,0,-1) (FUN_0886b6bc), checked on Cloud's own _812A/_812C


def pose(d, sk, motion, f):
    names, parent, rest_t, rest_r, _ = sk
    m = {n: (o, s) for n, o, s in motions(d)[0]}
    mo = read_motion(d, *m[motion])
    cur = {(names[b], ch): (t, v, i) for b, ch, t, v, i in mo['curves'] if b < len(names)}
    w, scl = {}, {}
    for n in hierarchy_order(names, parent):
        t = sample(*cur[(n, 0x48)], f, False) if (n, 0x48) in cur else rest_t[n]
        r = quat_to_mat(sample(*cur[(n, 0x4B)], f, True)) if (n, 0x4B) in cur else rest_r[n]
        scl[n] = sample(*cur[(n, 0x4D)], f, False) if (n, 0x4D) in cur else np.ones(3)
        p = parent[n]
        w[n] = (w[p] if p else np.eye(4)) @ trs(t, r)
    return w, scl, mo


def draw(d, motion, frames, fov_default):
    sk = read_skeleton(d)
    names, parent = sk[0], sk[1]
    vic, _, _ = pose(d, sk, '_000A', 0)
    flip = np.diag([-1.0, 1, -1, 1])
    flip[1, 3] = -ANCHOR_Y
    tiles = []
    for f in frames:
        w, scl, mo = pose(d, sk, motion, f)
        cam = w['camera_include']
        fov = scl['camera_include'][2]
        if fov <= 2:
            fov = fov_default
        eye, fwd, up = cam[:3, 3], LOOK * cam[:3, 2], cam[:3, 1]
        fwd = fwd / np.linalg.norm(fwd)
        right = np.cross(fwd, up)
        right /= np.linalg.norm(right)
        up = np.cross(right, fwd)
        foc = (H / 2) / np.tan(np.radians(fov) / 2)

        def proj(p):
            v = p - eye
            z = v @ fwd
            if z < 0.05:
                return None
            return (W / 2 + foc * (v @ right) / z, H / 2 - foc * (v @ up) / z)
        img = Image.new('RGB', (W, H), (24, 24, 32))
        g = ImageDraw.Draw(img)
        for k in range(-6, 7):                                     # floor grid, 1 m
            for a, b in (((k, -ANCHOR_Y, -6), (k, -ANCHOR_Y, 6)), ((-6, -ANCHOR_Y, k), (6, -ANCHOR_Y, k))):
                pa, pb = proj(np.array(a, float)), proj(np.array(b, float))
                if pa and pb:
                    g.line([pa, pb], fill=(60, 60, 70))
        for mats, col, wcol in ((vic, (220, 70, 70), (220, 70, 70)), (w, (90, 150, 255), (255, 170, 40))):
            for n in names:
                p = parent[n]
                if not p or 'camera' in n or n == 'root' or p == 'root' and 'hip' not in n:
                    continue
                m1, m2 = mats[n], mats[p]
                if mats is vic:
                    m1, m2 = flip @ m1, flip @ m2
                a, b = proj(m1[:3, 3]), proj(m2[:3, 3])
                if a and b:
                    g.line([a, b], fill=wcol if 'wep' in n or 'wep' in p else col, width=2)
        g.text((4, 4), '%s f%d  fov %.1f  eye (%.1f %.1f %.1f)' % (motion, f, fov, *eye), fill=(230, 230, 230))
        tiles.append(img)
    sheet = Image.new('RGB', (W * min(3, len(tiles)), H * ((len(tiles) + 2) // 3)), (0, 0, 0))
    for i, t in enumerate(tiles):
        sheet.paste(t, (W * (i % 3), H * (i // 3)))
    return sheet


def main():
    model, motion, out = sys.argv[1:4]
    d = open(model, 'rb').read()
    rng = [n for n, o, s in motions(d)[0] if n == motion]
    assert rng, motion
    frames = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 and not sys.argv[4].startswith('--') else \
        [0, 15, 30, 45, 60, 80]
    fd = float(sys.argv[sys.argv.index('--fov-default') + 1]) if '--fov-default' in sys.argv else 45.0
    draw(d, motion, frames, fd).save(out)
    print(out)


if __name__ == '__main__':
    main()
