"""Mix two versions of a motion slot: take some bones' local transforms from OTHER.gmo during a frame window.

  python3 -I motion_mix.py MODEL.gmo OTHER.gmo SLOT BONES OUT.gmo [A-B] [RAMP]
    BONES = comma list (e.g. r_wep  or  r_clavicle,r_uparm,r_foarm,r_hand)
    A-B   = animation frames (30/s) where OTHER is used fully (default: whole motion); RAMP = blend frames each side
Both motions are sampled per frame (gmo_fk.sample: steps, linear, quaternion keys) on MODEL's skeleton; the result
is written with kh2_retarget.write_motion (keeps the slot's loop range and camera bones).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gmo_anim2gltf import read_motion  # noqa: E402
from gmo_fk import sample  # noqa: E402
from gmo_motion import motions  # noqa: E402
from kh2_retarget import mat_to_quat, quat_to_mat, read_skeleton, trs, write_motion  # noqa: E402
import pose_author as PA  # noqa: E402


def local_frames(d, slot, skel):
    names, parent, rest_t, rest_r, bind = skel
    m = {n: (o, s) for n, o, s in motions(d)[0]}
    mo = read_motion(d, *m[slot])
    cur = {(names[b], ch): (t, v, i) for b, ch, t, v, i in mo['curves']}
    end = int(mo['frames'][1])
    out = []
    for f in range(end + 1):
        fr = {}
        for n in names:
            t = sample(*cur[(n, 0x48)], f, False) if (n, 0x48) in cur else rest_t[n]
            r = quat_to_mat(sample(*cur[(n, 0x4B)], f, True)) if (n, 0x4B) in cur else rest_r[n]
            fr[n] = trs(np.asarray(t, float), r)
        out.append(fr)
    return out


def main():
    model, other, slot, bones, out = sys.argv[1:6]
    bones = bones.split(',')
    d = open(model, 'rb').read()
    od = open(other, 'rb').read()
    skel = read_skeleton(d)
    mine = local_frames(d, slot, skel)
    theirs = local_frames(od, slot, read_skeleton(od))
    n = len(mine)
    a, b = (map(int, sys.argv[6].split('-')) if len(sys.argv) > 6 else (0, n - 1))
    ramp = int(sys.argv[7]) if len(sys.argv) > 7 else 3
    for f in range(n):
        if a <= f <= b:
            w = 1.0
        elif a - ramp <= f < a:
            w = (f - (a - ramp)) / ramp
        elif b < f <= b + ramp:
            w = 1 - (f - b) / ramp
        else:
            continue
        g = min(f, len(theirs) - 1)
        for nm in bones:
            q = PA.slerp(mat_to_quat(mine[f][nm][:3, :3]), mat_to_quat(theirs[g][nm][:3, :3]), w)
            t = (1 - w) * mine[f][nm][:3, 3] + w * theirs[g][nm][:3, 3]
            mine[f][nm] = trs(t, quat_to_mat(q))
    open(out, 'wb').write(write_motion(d, slot, skel, mine, label='mix'))


if __name__ == '__main__':
    main()
