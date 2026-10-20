"""Battle-intro camera for #33 (Sora) framed for HIS height, not Cloud's (notes/gmo-format.md "Intro camera").

Each fighter file (obj/p_sev120.objx) carries a small CAMERA model: chunk `d_se` type 2, a GMO ("OMG.00.1PSP", 24 KB)
with bones dummy / camera2_include / camera_include and 9 camera motions. The battle-start script picks a camera path
id, the camera manager plays that motion on the fighter's camera model (FUN_08b10210 -> FUN_08b3ae14(.., id, 0, 7)
-> FUN_0880fd34 / FUN_0880fec8) and reads the camera bone (FUN_0886b6bc: position = eye, -Z = look, +Y = up, scale z =
FOV). Intro = _200A (80 frames, with motion 1100) and _203A (68 frames, with 1110: the close-up, FOV down to 16);
_201A/_202A = the shorter intro after Retry.
Sora's camera model is Cloud's copy, so the close-up aimed at Cloud's face height (1.59 m) = over Sora's hair.
Fix: scale every camera POSITION key (value + Hermite tangents) of those motions by S = Sora head / Cloud head height
about the fighter's feet. Rotations and FOV stay, so the shot frames Sora exactly like it framed Cloud.
Re-runnable: works from Cloud's own camera model (obj/p_sev100.objx in the same ISO) every time.

  python3 -I spot33_introcam.py ISO [--dry]
"""
import os
import struct
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from gmo_motion import motions  # noqa: E402
from kh2_retarget import read_motion_raw, read_skeleton  # noqa: E402

S = 1.406 / 1.586                        # Sora / Cloud head bone height (bind poses of the two body models)
SLOTS = ('_010A', '_020A', '_200A', '_201A', '_202A', '_203A')   # + win / loss (results) cameras (Mat 2026-10-15)
CAM_BONES = ('camera_include', 'camera2_include')


def cam_chunk(d):
    n, = struct.unpack_from('<I', d, 4)
    for k in range(n):
        t, tag, o, s = struct.unpack_from('<I4sII', d, 16 + k * 16)
        if t == 2 and tag == b'd_se' and d[o:o + 11] == b'OMG.00.1PSP':
            return o, s
    raise SystemExit('no camera GMO (d_se type 2) found')


def scaled(cam, scale):
    """camera GMO bytes with the translate keys of SLOTS scaled (in place, same size)"""
    out = bytearray(cam)
    names = read_skeleton(cam)[0]
    mo = {n: (o, s) for n, o, s in motions(cam)[0]}
    count = 0
    for slot in SLOTS:
        o, s = mo[slot]
        ents, _, _ = read_motion_raw(cam, o, s)
        # fcurve block offsets inside the motion, in order
        offs, p = [], o + struct.unpack_from('<H', cam, o + 2)[0]
        while p < o + s:
            t, _, sz = struct.unpack_from('<HHI', cam, p)
            if t == 0x0C:
                offs.append(p)
            p += sz
        for b, ch, fi in ents:
            if names[b] not in CAM_BONES or ch != 0x48:
                continue
            fo = offs[fi]
            fmt, dims, n, _ = struct.unpack_from('<IIII', cam, fo + 0x1C)
            assert fmt & 0x80 and dims == 3, (slot, hex(fmt), dims)
            per = {0x80: 4, 0x81: 4, 0x82: 10}[fmt]               # frame + xyz | frame + xyz(value, in, out)
            k = np.frombuffer(cam, '<f2', n * per, fo + 0x2C).astype(np.float64).reshape(n, per)
            k[:, 1:] *= scale                                    # positions and their tangents (frames untouched)
            out[fo + 0x2C:fo + 0x2C + n * per * 2] = k.astype('<f2').tobytes()
            count += 1
    return bytes(out), count


def main():
    iso = sys.argv[1]
    use_iso(iso)
    with open(iso, 'rb') as f:
        st, sz = pkg_offset('obj/p_sev100.objx')
        cloud = read_at(f, st, sz)
        st, sz = pkg_offset('obj/p_sev120.objx')
        sora = read_at(f, st, sz)
    co, cs = cam_chunk(cloud)
    so, ss = cam_chunk(sora)
    new, count = scaled(cloud[co:co + cs], S)
    assert len(new) == ss, 'Sora camera model size differs from Cloud\'s'
    if sora[so:so + ss] == new:
        print('intro camera already scaled (x%.3f)' % S)
        return
    other = scaled(cloud[co:co + cs], 1.0)[0]
    if sora[so:so + ss] != other:
        print('NOTE: Sora\'s camera model was not a plain copy of Cloud\'s; replacing it with Cloud\'s scaled one')
    print('intro camera: %d position curves of %s scaled x%.3f' % (count, ', '.join(SLOTS), S))
    if '--dry' in sys.argv:
        return
    data = bytearray(sora)
    data[so:so + ss] = new
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'f.objx')
        open(p, 'wb').write(data)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, 'obj/p_sev120.objx', p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main()
