"""Put a KH2 Sora motion (baked by tools/kh2bake/bake) into a Dissidia fighter GMO motion slot.

  python3 -I kh2_retarget.py MODEL.gmo FIT_MAP.json BAKED.bin OUT.gmo DST_MOTION [FRAMES] [KEEP_LEN]

- MODEL.gmo: Sora's GMO (gmo_resize.py skeleton + fit_sora.py skin), FIT_MAP.json: fit_sora.py's sora_fit.map.json.
- DST_MOTION: Dissidia motion to replace, e.g. _000A (idle). FRAMES "a-b" = KH2 frames to take (default all).
  KEEP_LEN=1 time-stretches the KH2 frames onto the old motion's frame range (game logic may expect its length).
- Each driven Cloud bone follows one KH2 bone (DRIVERS): world(t) = K_s(t) · A_s⁻¹ · bind_c, where
  K_s = KH2 skinning matrix (world(t) · rest⁻¹, cm → m) and A_s = the fit map that moved Sora's mesh from KH2's
  bind into Cloud's bind. Local rotations come from the parent's solved world; bone lengths stay the model's.
  The root carries the hip position (per-frame translate). Other skin bones keep their bind pose relative to
  their parent (fingers stay a fist, Keyblade stays in the hand); camera bones are copied from the old motion.
- Curves: rotations 0x84 (per-frame quaternion keys), root translation 0x81, constants 0x80; half floats.
"""
import json
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gmo  # noqa: E402
from gmo_motion import motions  # noqa: E402
from gmo_resize import args_of  # noqa: E402
from kh2anim import kh2_rest, load_baked  # noqa: E402

# Cloud bone -> KH2 Sora bone that drives it (right side mirrored: legs +29, arms +92)
DRIVERS_L = {'hip': 2, 'waist': 66, 'chest': 67, 'neck': 137, 'head': 140,
             'l_clavicle': 75, 'l_uparm': 78, 'l_foarm': 79, 'l_hand': 85,
             'l_femur': 24, 'l_tibia': 12, 'l_foot': 15, 'l_toe': 18}
COPY = ('camera2_include', 'camera_include', 'trans_include')
LOOP_TAIL = 6


def drivers():
    out = dict(DRIVERS_L)
    for k, v in DRIVERS_L.items():
        if k.startswith('l_'):
            out['r_' + k[2:]] = v + (29 if v < 40 else 92)
    return out


def quat_to_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mat_to_quat(m):
    t = np.trace(m)
    if t > 0:
        s = np.sqrt(t + 1) * 2
        q = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, s / 4]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = [s / 4, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = [(m[0, 1] + m[1, 0]) / s, s / 4, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]
    else:
        s = np.sqrt(1 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = [(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, s / 4, (m[1, 0] - m[0, 1]) / s]
    q = np.array(q)
    return q / np.linalg.norm(q)


def ortho(m):
    u, _, vt = np.linalg.svd(m)
    r = u @ vt
    if np.linalg.det(r) < 0:
        u[:, -1] *= -1
        r = u @ vt
    return r


def trs(t, r):
    m = np.eye(4)
    m[:3, :3] = r
    m[:3, 3] = t
    return m


def read_skeleton(d):
    items = []
    gmo.walk(d, 16, len(d), 0, items)
    m0 = next(i for i in items if i[2] == 0x03 and i[5] == 'model-0')
    bones = [i for i in items if i[2] == 0x04 and m0[1] < i[1] < m0[1] + m0[4]]
    names = [b[5] for b in bones]
    parent, rest_t, rest_r, bind = {}, {}, {}, {}
    for b in bones:
        a = args_of(d, b[1], b[3], b[4])
        n = b[5]
        parent[n] = names[struct.unpack_from('<I', d, a[0x8041][0] + 8)[0] & 0xFFF] if 0x8041 in a else None
        rest_t[n] = np.array(struct.unpack_from('<3f', d, a[0x8048][0] + 8)) if 0x8048 in a else np.zeros(3)
        rest_r[n] = quat_to_mat(struct.unpack_from('<4f', d, a[0x804B][0] + 8)) if 0x804B in a else np.eye(3)
        if 0x8044 in a and 0x8045 in a:
            cnt = struct.unpack_from('<I', d, a[0x8044][0] + 8)[0]
            refs = [r & 0xFFF for r in struct.unpack_from('<%dI' % cnt, d, a[0x8044][0] + 12)]
            for k, r in enumerate(refs):
                mtx = np.array(struct.unpack_from('<16f', d, a[0x8045][0] + 12 + 64 * k)).reshape(4, 4).T
                bind[names[r]] = np.linalg.inv(mtx)
    return names, parent, rest_t, rest_r, bind


def read_motion_raw(d, o, s):
    """-> (entries [(bone, ch, fcurve index)], fcurve blobs [bytes of the 0x0C block])"""
    _, hs, _ = struct.unpack_from('<HHI', d, o)
    p = o + hs
    ents, fcs = [], []
    frames = None
    while p < o + s:
        t, h2, sz = struct.unpack_from('<HHI', d, p)
        if t == 0x80B1:
            frames = struct.unpack_from('<ff', d, p + 8)
        if t == 0x80B3:
            ref, ch, _, fi = struct.unpack_from('<IIIH', d, p + 8)
            ents.append((ref & 0xFFF, ch, fi))
        elif t == 0x0C:
            fcs.append(d[p:p + sz])
        p += sz
    return ents, fcs, frames


def fcurve_block(idx, fmt, keys):
    """keys: array [n, 1 + dims] (frame, values...)"""
    keys = np.asarray(keys, np.float64)
    data = struct.pack('<IIII', fmt, keys.shape[1] - 1, len(keys), 0) + keys.astype('<f2').tobytes()
    data += b'\0' * ((-len(data)) % 4)
    name = ('fcurve-%d' % idx).encode()[:11].ljust(12, b'\0')
    hs = 0x1C
    size = hs + len(data)
    return struct.pack('<HHIII', 0x0C, hs, size, size, hs + 16) + name + data


def hierarchy_order(names, parent):
    order = []

    def visit(n):
        order.append(n)
        for c in names:
            if parent[c] == n:
                visit(c)
    for n in names:
        if parent[n] is None:
            visit(n)
    return order


def load_fitmap(path):
    fm = json.load(open(path))
    segs = {k: np.array(v) for k, v in fm['segs'].items()}
    fpose = {int(k): np.array(v) for k, v in fm['fpose'].items()}
    bone_seg = {int(k): v for k, v in fm['bone_seg'].items()}
    return lambda s: segs[bone_seg[s]] @ fpose.get(s, np.eye(4))


def solve_kh2(skel, A, frames_kh2):
    """KH2 baked frames -> per frame: {bone: 4x4 local} (Dissidia skeleton, bone lengths kept)"""
    names, parent, rest_t, rest_r, bind = skel
    rest_kh2_inv = np.linalg.inv(kh2_rest())
    C = np.diag([0.01, 0.01, 0.01, 1.0])
    Ci = np.diag([100.0, 100.0, 100.0, 1.0])
    drv = drivers()
    order = hierarchy_order(names, parent)
    out = []
    for W in frames_kh2:
        target = {}
        for c, s in drv.items():
            K = C @ W[s] @ rest_kh2_inv[s] @ Ci
            Wc = K @ np.linalg.inv(A(s)) @ bind[c]
            target[c] = trs(Wc[:3, 3], ortho(Wc[:3, :3]))
        world, locs = {}, {}
        for n in order:
            p = parent[n]
            pw = world[p] if p else np.eye(4)
            if n == 'root':
                hip = target['hip']
                r = hip[:3, :3] @ rest_r['hip'].T
                local = trs(hip[:3, 3] - r @ rest_t['hip'], r)
            elif n in target:
                local = trs(rest_t[n], pw[:3, :3].T @ target[n][:3, :3])
            elif n in bind and p and p in bind:
                rel = np.linalg.inv(bind[p]) @ bind[n]                # keep the bind pose relative to the parent
                local = trs(rest_t[n], ortho(rel[:3, :3]))
            else:
                local = trs(rest_t[n], rest_r[n])
            world[n] = pw @ local
            locs[n] = local
        out.append(locs)
    return out


def write_motion(d, dst, skel, frames, keep_len=False, label='', loop_tail=None):
    """frames: list of {bone: 4x4 local}; root translation is animated, other bones keep their rest length.
    Returns the new GMO bytes with motion DST replaced."""
    names, parent, rest_t, rest_r, bind = skel
    nf = len(frames)
    mots, fo, mo = motions(d)
    mo_by = {n: (o, s) for n, o, s in mots}
    o, s = mo_by[dst]
    old_ents, old_fcs, old_frames = read_motion_raw(d, o, s)
    # 0x80B4 = 1 on looping motions (idle, run…), 0 on one-shots (attacks, hits, win/loss). Writing 1 on an attack
    # made combo finishers miss (tests 51-58).
    old_b4, p = None, o + struct.unpack_from('<H', d, o + 2)[0]
    while p < o + s:
        t, h2, sz = struct.unpack_from('<HHI', d, p)
        if t == 0x80B4:
            old_b4 = struct.unpack_from('<I', d, p + 8)[0]
        if t == 0x0C:
            break
        p += sz
    if keep_len:
        f0, f1 = old_frames
        times = np.linspace(f0, f1, nf)
    else:
        # keys always start at frame 0 (camera curves copied below are timed from 0 too). The play range
        # (0x80B1) is the part that LOOPS: the game plays from 0 to its end once, then repeats the range.
        # Motions whose old range started later (win poses: Cloud's _910A = 111-175 of 0-175) get only their
        # last LOOP_TAIL frames looped, so the final pose is held instead of the whole animation repeating.
        times = np.arange(nf, dtype=np.float64)
        f1 = float(nf - 1)
        env_loop = os.environ.get('LOOP')
        if env_loop:                                         # build_sora.sh SLOT=…#N  (all = loop everything)
            loop_tail = f1 if env_loop == 'all' else float(env_loop)
        if loop_tail:                                        # the pose script asked for a loop length
            f0 = max(0.0, f1 - loop_tail)
        else:
            f0 = max(0.0, f1 - LOOP_TAIL) if old_frames and old_frames[0] > 0 else 0.0
    fcs, ents = [], []

    def add_curve(blob_fn):
        fcs.append(blob_fn(len(fcs)))
        return len(fcs) - 1
    scale_one = add_curve(lambda i: fcurve_block(i, 0x80, [[0, 1, 1, 1]]))
    copied = {}
    for n in names:
        b = names.index(n)
        if n in COPY:
            for ob, ch, fi in old_ents:
                if ob == b:
                    if fi not in copied:
                        copied[fi] = len(fcs)
                        fcs.append(bytes(old_fcs[fi]))
                    ents.append((b, ch, copied[fi]))
            continue
        if n == 'root':
            rt = np.array([fr['root'][:3, 3] for fr in frames])
            ents.append((b, 0x48, add_curve(lambda i, rt=rt: fcurve_block(i, 0x81, np.c_[times, rt]))))
        else:
            tr = np.array([fr[n][:3, 3] for fr in frames])
            if np.allclose(tr, rest_t[n], atol=1e-4):
                ents.append((b, 0x48, add_curve(lambda i, n=n: fcurve_block(i, 0x80, [[0, *rest_t[n]]]))))
            else:                                       # bone that moves (e.g. r_wep taken from Cloud)
                ents.append((b, 0x48, add_curve(lambda i, tr=tr: fcurve_block(i, 0x81, np.c_[times, tr]))))
        q = np.array([mat_to_quat(fr[n][:3, :3]) for fr in frames])
        for k in range(1, len(q)):                                  # keep quaternion signs continuous
            if np.dot(q[k], q[k - 1]) < 0:
                q[k] = -q[k]
        if np.allclose(q, q[0], atol=1e-4):
            ents.append((b, 0x4B, add_curve(lambda i, q=q: fcurve_block(i, 0x80, [[0, *q[0]]]))))
        else:
            ents.append((b, 0x4B, add_curve(lambda i, q=q: fcurve_block(i, 0x84, np.c_[times, q]))))
        ents.append((b, 0x4D, scale_one))
    hdr_name = d[o + 16:o + 24]
    body = struct.pack('<HHIff', 0x80B1, 0, 16, f0, f1)
    body += struct.pack('<HHIf', 0x80B2, 0, 12, 30.0)
    if old_b4 is not None:                                           # keep the slot's own flag (or none)
        body += struct.pack('<HHII', 0x80B4, 0, 12, old_b4)
    for b, ch, fi in ents:
        body += struct.pack('<HHIIIIHH', 0x80B3, 0, 24, 0x00041000 | b, ch, 0, fi, 0x0C)
    body += b''.join(fcs)
    new = struct.pack('<HHIII', 0x0B, 0x18, 0x18 + len(body), 0x18, 0x18) + hdr_name + body
    delta = len(new) - s
    out_d = bytearray(d[:o] + new + d[o + s:])
    for blk in (fo, mo):
        struct.pack_into('<I', out_d, blk + 4, struct.unpack_from('<I', out_d, blk + 4)[0] + delta)
    print('%s <- %s: %d frames (%g-%g), %d curves, %+d bytes' % (dst, label, nf, f0, f1, len(fcs), delta))
    return bytes(out_d)


def main():
    model, fitmap, baked, out, dst = sys.argv[1:6]
    rng = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] != '-' else None
    keep_len = len(sys.argv) > 7 and sys.argv[7] == '1'
    d = open(model, 'rb').read()
    skel = read_skeleton(d)
    frames_kh2, fps, fe, fl = load_baked(baked)
    if rng:
        a, b = map(int, rng.split('-'))
        frames_kh2 = frames_kh2[a:b + 1]
    frames = solve_kh2(skel, load_fitmap(fitmap), frames_kh2)
    open(out, 'wb').write(write_motion(d, dst, skel, frames, keep_len, os.path.basename(baked)))


if __name__ == '__main__':
    main()
