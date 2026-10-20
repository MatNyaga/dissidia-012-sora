"""Evaluate a GMO motion (forward kinematics) and report where a weapon tip moves fastest.

  python3 -I gmo_fk.py MODEL.gmo MOTION [BONE]        (default bone r_wep; prints the speed peaks per frame)

Uses model-0's skeleton (rest translations/rotations) and the motion's curves: 0x80 constant / step, 0x81 linear
vec3, 0x84 quaternion keys (slerp). Tip = 1 m along the bone's local -Y... no: the point 1 m from the bone in the
direction its children/weapon point is unknown, so speed is measured for the bone origin and for a point 1 m along
each local axis; the largest is reported.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gmo_anim2gltf import read_motion  # noqa: E402
from gmo_motion import motions  # noqa: E402
from kh2_retarget import hierarchy_order, quat_to_mat, read_skeleton, trs  # noqa: E402


def sample(times, vals, interp, t, quat):
    if len(times) == 1 or t <= times[0]:
        v = vals[0]
    elif t >= times[-1]:
        v = vals[-1]
    else:
        i = np.searchsorted(times, t) - 1
        u = (t - times[i]) / (times[i + 1] - times[i])
        if interp == 0:
            v = vals[i]
        elif quat:
            a, b = vals[i], vals[i + 1]
            if np.dot(a, b) < 0:
                b = -b
            v = (1 - u) * a + u * b
        else:
            v = (1 - u) * vals[i] + u * vals[i + 1]
    if quat:
        v = v / np.linalg.norm(v)
    return v


def world_track(d, motion, bone):
    names, parent, rest_t, rest_r, bind = read_skeleton(d)
    order = hierarchy_order(names, parent)
    m = {n: (o, s) for n, o, s in motions(d)[0]}
    mo = read_motion(d, *m[motion])
    cur = {}
    for b, ch, t, v, i in mo['curves']:
        cur[(names[b], ch)] = (t, v, i)
    end = int(mo['frames'][1])
    pts = []
    for f in range(end + 1):
        w = {}
        for n in order:
            t = sample(*cur[(n, 0x48)][:2], cur[(n, 0x48)][2], f, False) if (n, 0x48) in cur else rest_t[n]
            r = quat_to_mat(sample(*cur[(n, 0x4B)][:2], cur[(n, 0x4B)][2], f, True)) if (n, 0x4B) in cur else rest_r[n]
            p = parent[n]
            w[n] = (w[p] if p else np.eye(4)) @ trs(t, r)
        pts.append([(w[bone] @ np.r_[off, 1])[:3] for off in ([0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1],
                                                              [-1, 0, 0], [0, -1, 0], [0, 0, -1])])
    return np.array(pts)


def main():
    d = open(sys.argv[1], 'rb').read()
    bone = sys.argv[3] if len(sys.argv) > 3 else 'r_wep'
    P = world_track(d, sys.argv[2], bone)
    sp = np.linalg.norm(np.diff(P, axis=0), axis=2).max(1)
    order = np.argsort(-sp)
    peaks = []
    for i in order:
        if all(abs(i - p) > 3 for p in peaks):
            peaks.append(int(i))
        if len(peaks) == 4:
            break
    print('%s: %d frames, fastest frames %s' % (sys.argv[2], len(P), sorted(peaks)))


if __name__ == '__main__':
    main()
