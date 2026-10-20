"""Burst-camera zoom fix: the EX Burst camera bones (0 camera2_include, 1 camera_include) keep the FIELD OF VIEW in the
Z component of their SCALE channel (0x4d): Cloud/old Sora clips use z = 11-67 (degrees), x = y = 1. Codex's Trinity v5
_812A and continuous _812C came with scale (1, 1, 1) = a 1-degree view -> "it's just a brown screen, I can hear the
hits" (Mat, test259). This rewrites, in place (same size), every scale key of those bones whose z is 1.0 to z = FOV.

  python3 -I gmo_camfov.py IN.gmo OUT.gmo MOTION[=FOV] [...]       (FOV default 45; re-running = no change)

FIX 2026-10-16 (EX controller helper): GMO motions SHARE fcurves between entries — Codex's clips use ONE constant
(1, 1, 1) scale fcurve for all 54 bones — so the first version (editing that fcurve in place) set z = 45 on EVERY bone:
the whole body was stretched 45x along local Z = the screen-filling skin/shorts polygons of test262 (not the camera
position). Now a camera scale entry whose fcurve is shared gets its OWN copy (appended, entry repointed; the motion and
its parents grow by that block), a camera-only fcurve is still edited in place. Body/weapon fcurves stay untouched.
"""
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gmo_motion import motions  # noqa: E402

CAM_BONES = (0, 1)
SCALE = 0x4D


def fix(d, name, fov):
    """-> (new GMO bytes, number of keys set); never edits an fcurve another (non-camera / other channel) entry uses"""
    from gmo_camcopy import fcurve, keys_of, parse
    mots, fo, mo = motions(d)
    o, s = next((o, s) for nm, o, s in mots if nm == name)
    head, subs, ents, fcs = parse(d, o, s)
    users = {}
    for _, b, ch, fi in ents:
        users.setdefault(fi, []).append((b, ch))
    n = 0
    for si, b, ch, fi in ents:
        if b not in CAM_BONES or ch != SCALE:
            continue
        fmt, dims, z, k = keys_of(subs[fcs[fi]])
        assert dims == 3, (b, fmt, dims)
        hit = k[:, 3] == 1.0
        if not hit.any():
            continue
        k[hit, 3] = fov
        n += int(hit.sum())
        if len(users[fi]) == 1:
            subs[fcs[fi]] = fcurve(fi, fmt, dims, z, k)
        else:
            nfi = len(fcs)
            subs.append(fcurve(nfi, fmt, dims, z, k))
            fcs.append(len(subs) - 1)
            struct.pack_into('<H', subs[si], 20, nfi)
            users[fi].remove((b, ch))
            users[nfi] = [(b, ch)]
    new = head + b''.join(subs)
    struct.pack_into('<I', new, 4, len(new))
    delta = len(new) - s
    d = bytearray(d[:o] + bytes(new) + d[o + s:])
    for blk in (fo, mo):
        struct.pack_into('<I', d, blk + 4, struct.unpack_from('<I', d, blk + 4)[0] + delta)
    return bytes(d), n


def main():
    src, dst, specs = sys.argv[1], sys.argv[2], sys.argv[3:]
    d = open(src, 'rb').read()
    for spec in specs:
        name, _, f = spec.partition('=')
        d, n = fix(d, name, float(f or 45))
        print('%s: %d camera scale keys -> FOV %s' % (name, n, f or 45) if n else '%s: camera FOV already set' % name)
    open(dst, 'wb').write(d)


if __name__ == '__main__':
    main()
