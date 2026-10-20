"""Copy the EX Burst CAMERA (bones 0 camera2_include / 1 camera_include: translate 0x48, rotate 0x4B, scale 0x4D whose z
= field of view in degrees) from a donor motion into a motion of another GMO, retimed linearly onto the target clip.

Why (2026-10-16, Q-20261015-CODEX-004): Codex's Trinity _812A/_812C came with a placeholder camera (scale 1 = 1-degree
view -> "brown screen", test259). gmo_camfov.py then set z = 45 in the SCALE FCURVE of bones 0/1 — but GMO motions SHARE
fcurves between entries (Codex's clips: one constant (1,1,1) scale curve for all 54 bones), so every bone got z x 45
-> giant stretched skin/shorts polygons filled the screen (test262). This tool never edits a shared fcurve: a camera
entry whose fcurve is used by any other entry gets a NEW fcurve appended (entry repointed); a camera-only fcurve is
replaced in place. Body/weapon fcurves and entries stay byte-identical. Re-running gives the same file.

Retiming: donor key frames t -> t * (target span / donor span); donor span = last camera key of the donor motion,
target span = last key of the target motion (all curves). Constant curves stay constant. A camera channel the donor
does not animate is left as it is in the target (the donor then used the bone's rest pose).

  python3 -I gmo_camcopy.py DONOR IN.gmo OUT.gmo MOTION[=DONOR_MOTION] [...]
      DONOR = a .gmo, or a directory with NAME.motion files (raw motion blocks, e.g. dumps/models/camdonor/)
"""
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gmo_motion import blocks, motions  # noqa: E402

CAM_BONES = (0, 1)
CHANNELS = (0x48, 0x4B, 0x4D)


def parse(d, o, s):
    """-> header bytes, [sub-block bytearrays], entries [(sub index, bone, ch, fcurve index)], fcurve sub indexes"""
    _, hs, _ = struct.unpack_from('<HHI', d, o)
    subs, ents, fcs = [], [], []
    for bo, t, bh, bs in blocks(d, o + hs, o + s):
        if t == 0x80B3:
            assert bs == 0x18, 'multi-entry 0x80B3 block not handled'
            ref, ch, _, fi = struct.unpack_from('<IIIH', d, bo + 8)
            ents.append((len(subs), ref & 0xFFF, ch, fi))
        elif t == 0x0C:
            fcs.append(len(subs))
        subs.append(bytearray(d[bo:bo + bs]))
    return bytearray(d[o:o + hs]), subs, ents, fcs


def keys_of(blk):
    hs = struct.unpack_from('<H', blk, 2)[0]
    fmt, dims, nk, z = struct.unpack_from('<IIII', blk, hs)
    assert fmt & 0x80, 'fcurve format %#x' % fmt
    k = np.frombuffer(bytes(blk[hs + 16:hs + 16 + nk * 2 * (1 + dims)]), '<f2').reshape(nk, 1 + dims).copy()
    return fmt, dims, z, k


def fcurve(name_idx, fmt, dims, z, keys):
    data = struct.pack('<IIII', fmt, dims, len(keys), z) + keys.astype('<f2').tobytes()
    data += b'\0' * ((-len(data)) % 4)
    hs = 0x1C
    size = hs + len(data)
    return bytearray(struct.pack('<HHIII', 0x0C, hs, size, size, hs + 16) +
                     ('fcurve-%d' % name_idx).encode()[:11].ljust(12, b'\0') + data)


def last_key(subs, fcs, ents, bones=None):
    return max(float(keys_of(subs[fcs[fi]])[3][:, 0].max()) for _, b, ch, fi in ents if bones is None or b in bones)


def copy_camera(donor_mot, d, name):
    mots, fo, mo = motions(d)
    o, s = next((o, s) for n, o, s in mots if n == name)
    head, subs, ents, fcs = parse(d, o, s)
    dh, dsubs, dents, dfcs = parse(donor_mot, 0, len(donor_mot))
    src = {(b, ch): fi for _, b, ch, fi in dents if b in CAM_BONES}
    assert src, 'donor motion has no camera curves'
    dspan = last_key(dsubs, dfcs, dents, CAM_BONES)
    tspan = last_key(subs, fcs, ents)
    scale = tspan / dspan if dspan > 0 else 1.0
    users = {}
    for _, b, ch, fi in ents:
        users.setdefault(fi, []).append((b, ch))
    report = []
    for si, b, ch, fi in ents:
        if b not in CAM_BONES or (b, ch) not in src:
            continue
        fmt, dims, z, k = keys_of(dsubs[dfcs[src[(b, ch)]]])
        k[:, 0] = np.round(k[:, 0].astype(np.float64) * scale, 3)
        if len(users[fi]) == 1:                                      # camera-only fcurve: replace in place
            new = fcurve(fi, fmt, dims, z, k)
            subs[fcs[fi]] = new
            report.append('bone %d %#x: fcurve %d replaced (%d keys)' % (b, ch, fi, len(k)))
        else:                                                        # shared with other bones: append + repoint
            nfi = len(fcs)
            subs.append(fcurve(nfi, fmt, dims, z, k))
            fcs.append(len(subs) - 1)
            struct.pack_into('<H', subs[si], 20, nfi)
            users[fi].remove((b, ch))
            users[nfi] = [(b, ch)]
            report.append('bone %d %#x: shared fcurve %d left alone, new fcurve %d (%d keys)' % (b, ch, fi, nfi, len(k)))
    new = head + b''.join(subs)
    struct.pack_into('<I', new, 4, len(new))
    delta = len(new) - s
    d = bytearray(d[:o] + bytes(new) + d[o + s:])
    for blk in (fo, mo):
        struct.pack_into('<I', d, blk + 4, struct.unpack_from('<I', d, blk + 4)[0] + delta)
    print('%s: camera from donor (span %g -> %g frames), %+d bytes' % (name, dspan, tspan, delta))
    for r in report:
        print('   ' + r)
    return bytes(d)


def donor_motion(donor, name):
    if os.path.isdir(donor):
        return open(os.path.join(donor, name + '.motion'), 'rb').read()
    dd = open(donor, 'rb').read()
    o, s = next((o, s) for n, o, s in motions(dd)[0] if n == name)
    return dd[o:o + s]


def main():
    donor, src, dst, specs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
    d = open(src, 'rb').read()
    for spec in specs:
        name, _, dname = spec.partition('=')
        d = copy_camera(donor_motion(donor, dname or name), d, name)
    open(dst, 'wb').write(d)


if __name__ == '__main__':
    main()
