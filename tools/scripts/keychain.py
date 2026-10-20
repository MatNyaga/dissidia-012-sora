"""Kingdom Key keychain hanging and swinging (Mat 2026-10-15: "have a helper look at the keychain bones so that it's
not part of the rigid keyblade"). notes/gmo-format.md "Keychain bones".

History: v1 appended 4 bones (58) → game crashed at battle start (heap allocation failed: model memory budget).
v2 re-used 4 free bones (belt/shldarmor/hair/r_arm_help, indices 28-45) under r_wep (50) → no crash, but the chain
was invisible: the engine evaluates bones in LIST ORDER, so a child must come after its parent (dumps/models/keychain/
keychain_v2_4bones.py). Only wep0 (51), wep1 (52), trans_include (53) come after r_wep.
v3 (this): wep0 = ONE pendulum bone under r_wep. wep0 is the Keyblade part's draw bone, but no mesh is skinned to it
(the blade is drawn through its skinning list [r_wep]), so its own transform should not move the blade.
  - wep0 (both models): parent root -> r_wep, rest translate = the pommel (in r_wep's frame), rotation identity.
  - the chain + Mickey token leave the rigid wep0 part and become BODY-part meshes (p_sev100) rigid on wep0 via the
    body skinning list slot of 'belt' (no Sora mesh uses it): entry + inverse bind rewritten in place, count unchanged.
  - wep0 part: blade without the token, chain mesh dropped, blade array compacted.
  - every motion: wep0's translate curve -> the pommel offset (in place); MOTIONS get a baked verlet chain
    simulation (4 links) whose pivot->end direction becomes wep0's rotation keys (every KEY_STEP frames).
    Other motions: rest = straight chain (old look).
Bone count, skinning-list counts: unchanged.

  python3 -I keychain.py IN.gmo OUT.gmo [MOTION ...]      (default motions: _000A _900A _902A _910A _911A)
  env: KEY_STEP=3  GRAVITY=9.8 (m/s^2)  DAMP=0.96  ALL=1 (simulate every motion)
"""
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gmo  # noqa: E402
from gmo_anim2gltf import read_motion  # noqa: E402
from gmo_motion import motions  # noqa: E402
from kh2_retarget import fcurve_block, mat_to_quat, quat_to_mat, read_skeleton  # noqa: E402

BONE = 'wep0'                       # the pendulum bone (must come AFTER r_wep in the bone list)
SLOT_OF = 'belt'                    # its body skinning-list slot (no Sora mesh uses belt)
DEFAULT_MOTIONS = ['_000A', '_900A', '_902A', '_910A', '_911A']
KEY_STEP = int(os.environ.get('KEY_STEP', 3))
GRAVITY = float(os.environ.get('GRAVITY', 9.8))
DAMP = float(os.environ.get('DAMP', 0.96))
SUB = 4                                   # verlet substeps per frame


def items_of(d):
    it = []
    gmo.walk(d, 16, len(d), 0, it)
    return it


def args_of(d, o, hs, size):
    return {t: (ao, sz) for ao, t, h, sz in gmo.chunks(d, o + hs, o + size)}


def arg(t, data):
    data += b'\0' * ((-len(data)) % 4)
    return struct.pack('<HHI', t, 0, 8 + len(data)) + data


def block(t, name, body, array=False):
    nm = name.encode() + b'\0'
    nm += b'\0' * ((-len(nm)) % 4)
    hs = 16 + len(nm)
    size = hs + len(body)
    if array:
        return struct.pack('<HHIII', t, hs, size, size, hs + 16) + nm + body
    return struct.pack('<HHIII', t, hs, size, hs, hs) + nm + body


def bone_block(name, parent, t, q):
    body = arg(0x8041, struct.pack('<I', 0x00041000 | parent)) + arg(0x8048, struct.pack('<3f', *t)) + \
        arg(0x804B, struct.pack('<4f', *q))
    return block(0x04, name, body)


# ---------------------------------------------------------------- geometry
def pos_scale(d, m0):
    for ao, at, ahs, asz in gmo.chunks(d, m0[1] + m0[3], m0[1] + m0[4]):
        if at == 0x8015:
            mask, = struct.unpack_from('<I', d, ao + 8)
            fl = struct.unpack_from('<%df' % ((asz - 12) // 4), d, ao + 12)
            if mask & 0x180:
                return np.array(fl[0:3]), fl[3]


def read_array(d, a):
    vt, count, _, _ = struct.unpack_from('<IIII', d, a[1] + a[3])
    comps, vsize = gmo.ge_layout(vt & 0xFFFFFF)
    base = a[1] + a[3] + 16
    lay = {c[0]: c for c in comps}
    verts = []
    for k in range(count):
        v = {}
        for name, co, n, fmt in comps:
            v[name] = struct.unpack_from('<%d%s' % (n, fmt), d, base + k * vsize + co)
        verts.append(v)
    return vt, verts, lay


def array_bytes(name, verts, nw):
    """vertices (dicts with uv, color, pos raw + 'w' list of nw u8 weights) -> array block"""
    vt = 0x131A | ((nw - 1) << 14)
    comps, real = gmo.ge_layout(vt)
    vt |= real << 24
    out = bytearray()
    for v in verts:
        rec = bytearray(real)
        for cname, o, n, fmt in comps:
            if cname == 'weight':
                struct.pack_into('<%dB' % n, rec, o, *v['w'])
            elif cname == 'uv':
                struct.pack_into('<2H', rec, o, *v['uv'])
            elif cname == 'color':
                struct.pack_into('<H', rec, o, *v['color'])
            elif cname == 'pos':
                struct.pack_into('<3h', rec, o, *v['pos'])
        out += rec
    data = struct.pack('<IIII', vt, len(verts), 1, 0) + bytes(out)
    data += b'\0' * ((-len(data)) % 4)
    return block(0x07, name, data, array=True)


def mesh_bytes(name, d, m, palette, draw_ref, idx):
    """mesh block: the original mesh's args (material etc.) with palette 0x8062 and a new draw list"""
    body = b''
    for ao, at, ahs, asz in gmo.chunks(d, m[1] + m[3], m[1] + m[4]):
        if at in (0x8062, 0x8066):
            continue
        body += d[ao:ao + asz]
        if at == 0x8061 and palette is not None:
            body += arg(0x8062, struct.pack('<I', len(palette)) + struct.pack('<%dI' % len(palette), *palette))
    body += arg(0x8066, struct.pack('<4I', 0x00071000 | draw_ref, 3, len(idx), 1) + struct.pack('<%dH' % len(idx), *idx))
    return block(0x06, name, body)


# ---------------------------------------------------------------- motion sampling + chain simulation
def sample(curve, f):
    b, ch, times, vals, interp = curve
    if len(times) == 1 or f <= times[0]:
        return vals[0]
    if f >= times[-1]:
        return vals[-1]
    k = np.searchsorted(times, f) - 1
    t0, t1 = times[k], times[k + 1]
    u = (f - t0) / (t1 - t0) if t1 > t0 else 0.0
    if interp == 0:
        return vals[k]
    a, c = vals[k], vals[k + 1]
    if ch == 0x4B:
        if np.dot(a, c) < 0:
            c = -c
        q = (1 - u) * a + u * c
        return q / np.linalg.norm(q)
    return (1 - u) * a + u * c


def world_track(d, mot, skel, bone):
    """world 4x4 of `bone` per frame of motion mot=(o, s), from its curves (missing channels = rest)"""
    names, parent, rest_t, rest_r, _ = skel
    m = read_motion(d, *mot)
    nf = int(round(m['frames'][1])) + 1
    by = {}
    for c in m['curves']:
        by[(c[0], c[1])] = c
    chain = []
    b = bone
    while b is not None:
        chain.append(b)
        b = parent[b]
    out = []
    for f in range(nf):
        W = np.eye(4)
        for n in reversed(chain):
            i = names.index(n)
            T = np.eye(4)
            T[:3, :3] = quat_to_mat(sample(by[(i, 0x4B)], f)) if (i, 0x4B) in by else rest_r[n]
            T[:3, 3] = sample(by[(i, 0x48)], f) if (i, 0x48) in by else rest_t[n]
            if (i, 0x4D) in by:
                T[:3, :3] = T[:3, :3] @ np.diag(sample(by[(i, 0x4D)], f))
            W = W @ T
        out.append(W)
    return out, m


def rot_between(a, b):
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if c < -0.9999:
        p = np.cross(a, [1, 0, 0])
        if np.linalg.norm(p) < 1e-6:
            p = np.cross(a, [0, 1, 0])
        p /= np.linalg.norm(p)
        return 2 * np.outer(p, p) - np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def simulate(grip, local_pts, loop):
    """grip: per-frame world 4x4 of r_wep; local_pts: chain points in r_wep space (rest). -> world points per frame"""
    seg = [np.linalg.norm(local_pts[k + 1] - local_pts[k]) for k in range(len(local_pts) - 1)]
    rest = lambda W: [(W @ np.r_[p, 1])[:3] for p in local_pts]  # noqa: E731
    x = rest(grip[0])
    prev = [p.copy() for p in x]
    g = np.array([0, -GRAVITY, 0]) * (1.0 / (30 * SUB)) ** 2
    seq = [grip[0]] * 45 + list(grip) * (2 if loop else 1)    # settle on the first pose; loops run twice
    out = []
    for fi, W in enumerate(seq):
        W0 = seq[fi - 1] if fi else W
        for s in range(1, SUB + 1):
            u = s / SUB
            anchor = (1 - u) * (W0 @ np.r_[local_pts[0], 1])[:3] + u * (W @ np.r_[local_pts[0], 1])[:3]
            for k in range(1, len(x)):
                v = (x[k] - prev[k]) * DAMP
                prev[k] = x[k].copy()
                x[k] = x[k] + v + g
            x[0] = anchor
            prev[0] = anchor
            for _ in range(6):                     # keep the link lengths
                for k in range(len(seg)):
                    a, b = x[k], x[k + 1]
                    dv = b - a
                    L = np.linalg.norm(dv) or 1e-9
                    corr = dv * (1 - seg[k] / L)
                    if k == 0:
                        x[k + 1] = b - corr
                    else:
                        x[k] = a + corr * 0.5
                        x[k + 1] = b - corr * 0.5
        out.append([p.copy() for p in x])
    return out[-len(grip):]


def chain_rotations(grip, pts, rest_dirs):
    """-> per frame, local rotation matrices of kchain1..4 (kchain4 continues the last link's direction)"""
    res = []
    for W, P in zip(grip, pts):
        Rp = W[:3, :3]
        rots = []
        for k in range(4):
            d_rest = rest_dirs[k]                       # child direction in the bone's own (rest) frame
            want = P[k + 1] - P[k]                      # point 4 = end of the token
            cur = Rp @ d_rest
            Rw = rot_between(cur, want) @ Rp
            rots.append(Rp.T @ Rw)
            Rp = Rw
        res.append(rots)
    return res


# ---------------------------------------------------------------- main (v3: wep0 pendulum)
def half(vals):
    return np.asarray(vals, '<f2').tobytes()


def motion_layout(d, o, s):
    """-> entries [(rec_offset, bone, ch, fi)], fcurves [(offset, size, fmt, dims, nkeys, hs)], first fcurve offset"""
    _, hs, _ = struct.unpack_from('<HHI', d, o)
    p = o + hs
    ents, fcs, first = [], [], None
    while p < o + s:
        t, h2, sz = struct.unpack_from('<HHI', d, p)
        if t == 0x80B3:
            for q in range(p + 8, p + sz, 16):
                ref, ch, _, fi = struct.unpack_from('<IIIH', d, q)
                ents.append((q, ref & 0xFFF, ch, fi))
        elif t == 0x0C:
            if first is None:
                first = p
            fmt, dims, nk, _ = struct.unpack_from('<IIII', d, p + h2)
            fcs.append((p, sz, fmt, dims, nk, h2))
        p += sz
    return ents, fcs, first


def main():
    src, dst = sys.argv[1], sys.argv[2]
    want = sys.argv[3:] or DEFAULT_MOTIONS
    d = open(src, 'rb').read()
    it = items_of(d)
    file_b = next(i for i in it if i[2] == 0x02)
    models = [i for i in it if i[2] == 0x03 and i[5] is not None]
    m_anim = next(m for m in models if m[5] != 'model-0')
    m0 = next(m for m in models if m[5] == 'model-0')
    kids = lambda m: [i for i in it if i[0] == m[0] + 1 and m[1] < i[1] < m[1] + m[4]]  # noqa: E731
    skel = read_skeleton(d)
    names, parent, rest_t, rest_r, bind = skel
    if 'kchain1' in names or parent.get('belt') == 'r_wep':
        sys.exit('keychain: %s has an older keychain (v1/v2) — rebuild from a clean model' % src)
    if parent[BONE] == 'r_wep':
        print('keychain: %s already has the keychain (%s under r_wep) — nothing to do' % (src, BONE))
        if src != dst:
            open(dst, 'wb').write(d)
        return
    ib = names.index(BONE)
    i_rwep = names.index('r_wep')
    assert ib > i_rwep, 'the pendulum bone must come after r_wep in the bone list'
    if os.environ.get('ALL'):
        want = [n for n, o, s in motions(d)[0]]

    # --- chain geometry (bind space) from the wep0 meshes
    off, sc = pos_scale(d, m0)
    wpart = next(i for i in kids(m0) if i[2] == 0x05 and i[5] == 'wep0')
    pk = [i for i in it if i[0] == wpart[0] + 1 and wpart[1] < i[1] < wpart[1] + wpart[4]]
    meshes = [i for i in pk if i[2] == 0x06]
    arrays = [i for i in pk if i[2] == 0x07]
    G = bind['r_wep']
    g = G[:3, 3]
    mesh_info = []
    for m in meshes:
        a = args_of(d, m[1], m[3], m[4])
        ao, asz = a[0x8066]
        aref, prim, nidx, _ = struct.unpack_from('<4I', d, ao + 8)
        idx = list(struct.unpack_from('<%dH' % nidx, d, ao + 24))
        vt, verts, lay = read_array(d, arrays[aref & 0xFFF])
        P = np.array([[v['pos'][c] / 32768 * sc + off[c] for c in range(3)] for v in verts])
        mesh_info.append(dict(m=m, aref=aref & 0xFFF, idx=idx, verts=verts, P=P))
    assert len({mi['aref'] for mi in mesh_info}) == len(mesh_info) == len(arrays)
    A = np.concatenate([mi['P'] for mi in mesh_info])
    tip = A[np.argmax(np.linalg.norm(A - g, axis=1))]
    ax = (tip - g) / np.linalg.norm(tip - g)
    tvals = [(mi['P'] - g) @ ax for mi in mesh_info]
    chain_mesh = min(range(len(mesh_info)), key=lambda k: tvals[k].max())
    blade_mesh = [k for k in range(len(mesh_info)) if k != chain_mesh][0]
    t0 = tvals[chain_mesh].max()
    tb = np.sort(tvals[blade_mesh])
    behind = tb[tb < t0]
    cut = t0
    if len(behind) > 1:
        gi = int(np.argmax(np.diff(behind)))
        cut = (behind[gi] + behind[gi + 1]) / 2
    tmin = min(tvals[chain_mesh].min(), tvals[blade_mesh].min())
    pivot = g + ax * t0
    Rg = G[:3, :3]
    loc0 = Rg.T @ (pivot - g)                                     # pommel in r_wep's frame
    bind_c = G.copy()
    bind_c[:3, 3] = pivot                                         # wep0 at rest: r_wep's orientation, at the pommel
    rest_dir = Rg.T @ (-ax)                                       # chain direction in wep0's (rest) frame
    print('keychain v3: chain %.3f-%.3f m behind the grip, %d chain + %d token vertices, rigid on %s (index %d)' % (
        -t0, -tmin, len(mesh_info[chain_mesh]['verts']), int((tvals[blade_mesh] < cut).sum()), BONE, ib))

    out = bytearray(d)
    splices = []

    # --- wep0 bone (both models): parent r_wep, rest translate = pommel, no rotation arg (= identity)
    for m in (m0, m_anim):
        b = next(i for i in kids(m) if i[2] == 0x04 and i[5] == BONE)
        a = args_of(d, b[1], b[3], b[4])
        struct.pack_into('<I', out, a[0x8041][0] + 8, 0x00041000 | i_rwep)
        struct.pack_into('<3f', out, a[0x8048][0] + 8, *loc0)
        if 0x804B in a:
            struct.pack_into('<4f', out, a[0x804B][0] + 8, 0, 0, 0, 1)
    # --- body skinning list: slot of SLOT_OF -> wep0 (+ inverse bind), in place
    slot = None
    for m in (m0, m_anim):
        for b in [i for i in kids(m) if i[2] == 0x04 and i[5] == 'p_sev100']:
            a = args_of(d, b[1], b[3], b[4])
            if 0x8044 not in a or 0x8045 not in a:
                continue
            cnt, = struct.unpack_from('<I', d, a[0x8044][0] + 8)
            refs = [r & 0xFFF for r in struct.unpack_from('<%dI' % cnt, d, a[0x8044][0] + 12)]
            j = refs.index(names.index(SLOT_OF))
            struct.pack_into('<I', out, a[0x8044][0] + 12 + 4 * j, 0x00041000 | ib)
            struct.pack_into('<16f', out, a[0x8045][0] + 12 + 64 * j, *np.linalg.inv(bind_c).T.reshape(-1))
            if m is m0:
                slot = j
    # make sure no body mesh uses that slot
    bpart = next(i for i in kids(m0) if i[2] == 0x05 and i[5] == 'p_sev100')
    bk = [i for i in it if i[0] == bpart[0] + 1 and bpart[1] < i[1] < bpart[1] + bpart[4]]
    b_meshes = [i for i in bk if i[2] == 0x06]
    b_arrays = [i for i in bk if i[2] == 0x07]
    for m in b_meshes:
        a = args_of(d, m[1], m[3], m[4])
        if 0x8062 in a:
            n_, = struct.unpack_from('<I', d, a[0x8062][0] + 8)
            assert slot not in struct.unpack_from('<%dI' % n_, d, a[0x8062][0] + 12), 'a body mesh uses the %s slot' % SLOT_OF

    # --- body part: + chain mesh + token mesh, both rigid on the slot
    cm, bm = mesh_info[chain_mesh], mesh_info[blade_mesh]
    cverts = [dict(uv=v['uv'], color=v['color'], pos=v['pos'], w=[128]) for v in cm['verts']]
    tok = set(np.nonzero(tvals[blade_mesh] < cut)[0].tolist())
    tris = [bm['idx'][i:i + 3] for i in range(0, len(bm['idx']), 3)]
    tok_tris = [t for t in tris if all(v in tok for v in t)]
    keep_tris = [t for t in tris if not all(v in tok for v in t)]
    used = sorted({v for t in tok_tris for v in t})
    remap = {v: k for k, v in enumerate(used)}
    tverts = [dict(uv=bm['verts'][v]['uv'], color=bm['verts'][v]['color'], pos=bm['verts'][v]['pos'], w=[128])
              for v in used]
    na = len(b_arrays)
    new_m = [mesh_bytes('mesh-kc0', d, cm['m'], [slot], na, cm['idx']),
             mesh_bytes('mesh-kc1', d, bm['m'], [slot], na + 1, [remap[v] for t in tok_tris for v in t])]
    new_a = [array_bytes('arrays-kc-0', cverts, 1), array_bytes('arrays-kc-1', tverts, 1)]
    body = b''.join(d[i[1]:i[1] + i[4]] for i in b_meshes) + b''.join(new_m) + \
        b''.join(d[i[1]:i[1] + i[4]] for i in b_arrays) + b''.join(new_a)
    hdr = bytearray(d[bpart[1]:bpart[1] + bpart[3]])
    struct.pack_into('<I', hdr, 4, bpart[3] + len(body))
    splices.append((bpart[1], bpart[4], bytes(hdr) + body, [m0[1], file_b[1]]))
    # --- wep0 part: blade without the token (array compacted), chain mesh dropped
    wm, wa = [], []
    for k, mi in enumerate(mesh_info):
        if k == chain_mesh:
            continue
        if k == blade_mesh:
            kv = sorted({v for t in keep_tris for v in t})
            rmp = {v: j for j, v in enumerate(kv)}
            vt_b = struct.unpack_from('<I', d, arrays[mi['aref']][1] + arrays[mi['aref']][3])[0]
            assert vt_b & 0xFFFFFF == 0x131A, 'blade mesh is not a plain rigid weapon mesh'
            wa.append(array_bytes(arrays[mi['aref']][5], [dict(mi['verts'][v], w=[128]) for v in kv], 1))
            wm.append(mesh_bytes(mi['m'][5], d, mi['m'], None, len(wa) - 1, [rmp[v] for t in keep_tris for v in t]))
        else:
            wa.append(d[arrays[mi['aref']][1]:arrays[mi['aref']][1] + arrays[mi['aref']][4]])
            wm.append(mesh_bytes(mi['m'][5], d, mi['m'], None, len(wa) - 1, mi['idx']))
    body = b''.join(wm) + b''.join(wa)
    hdr = bytearray(d[wpart[1]:wpart[1] + wpart[3]])
    struct.pack_into('<I', hdr, 4, wpart[3] + len(body))
    splices.append((wpart[1], wpart[4], bytes(hdr) + body, [m0[1], file_b[1]]))

    # --- motions
    seg = (t0 - tmin) / 4
    lp = [loc0 + rest_dir * seg * k for k in range(5)]           # 4 links in r_wep's frame
    loops = {'_000A', '_902A', '_010A', '_020A', '_021A', '_022A'}
    grow, inplace, repoint = 0, 0, 0
    for name, o, s in motions(d)[0]:
        ents, fcs, first = motion_layout(d, o, s)
        users = {}
        for q, b, ch, fi in ents:
            users.setdefault(fi, set()).add((b, ch))
        app, new_recs = [], []
        const_idx = {}

        def appended(key, fn):
            if key not in const_idx:
                const_idx[key] = len(fcs) + len(app)
                app.append(fn(const_idx[key]))
            return const_idx[key]
        sim = name in want
        if sim:
            grip, _ = world_track(d, (o, s), skel, 'r_wep')
            pts = simulate(grip, lp, name in loops)
            nf = len(grip)
            frames = list(range(0, nf, KEY_STEP))
            if frames[-1] != nf - 1:
                frames.append(nf - 1)
            q = []
            for f in frames:
                Rw = grip[f][:3, :3]
                want_dir = pts[f][4] - pts[f][0]
                Rl = Rw.T @ rot_between(Rw @ rest_dir, want_dir) @ Rw
                q.append(mat_to_quat(Rl))
            q = np.array(q)
            for j in range(1, len(q)):
                if np.dot(q[j], q[j - 1]) < 0:
                    q[j] = -q[j]
        for ch in (0x48, 0x4B):
            if sim and ch == 0x4B:
                fi_new = appended('sim', lambda i: fcurve_block(i, 0x84, np.c_[frames, q]))
                target = None
            else:
                target = loc0 if ch == 0x48 else np.array([0, 0, 0, 1.0])
                fi_new = None
            recs = [(q_, fi) for q_, b, c, fi in ents if b == ib and c == ch]
            if not recs:
                if fi_new is None:
                    fi_new = appended(('c', ch), lambda i, v=target: fcurve_block(i, 0x80, [[0, *v]]))
                new_recs.append((ib, ch, fi_new))
                continue
            for q_, fi in recs:
                p_, sz, fmt, dims, nk, h2 = fcs[fi]
                if fi_new is None and users[fi] == {(ib, ch)} and nk == 1 and dims == len(target):
                    out[p_ + h2 + 16:p_ + h2 + 16 + 2 * (1 + dims)] = half([0, *target])
                    inplace += 1
                else:
                    f_ = fi_new if fi_new is not None else appended(
                        ('c', ch), lambda i, v=target: fcurve_block(i, 0x80, [[0, *v]]))
                    struct.pack_into('<H', out, q_ + 12, f_)
                    repoint += 1
        if not app and not new_recs:
            continue
        ents2, fcs2, first2 = motion_layout(out, o, s)
        used_fi = {fi for q_, b, c, fi in ents2} | {f_ for b, c, f_ in new_recs}
        keep = [i for i in range(len(fcs2)) if i in used_fi]
        ren = {old_i: k for k, old_i in enumerate(keep)}
        for j in range(len(app)):
            ren[len(fcs2) + j] = len(keep) + j
        head = bytearray(out[o:first2])
        for q_, b, c, fi in ents2:
            struct.pack_into('<H', head, q_ - o + 12, ren[fi])
        recs_b = b''.join(struct.pack('<HHIIIIHH', 0x80B3, 0, 24, 0x00041000 | b, c, 0, ren[f_], 0x0C)
                          for b, c, f_ in new_recs)
        kept = b''.join(bytes(out[fcs2[i][0]:fcs2[i][0] + fcs2[i][1]]) for i in keep)
        tail = bytes(out[fcs2[-1][0] + fcs2[-1][1]:o + s]) if fcs2 else b''
        blk = head + recs_b + kept + b''.join(app) + tail
        struct.pack_into('<I', blk, 4, len(blk))
        splices.append((o, s, bytes(blk), [m_anim[1], file_b[1]]))
        grow += len(blk) - s
        if sim:
            print('  %s: %d frames simulated, %d keys, %+d bytes' % (name, nf, len(frames), len(blk) - s))
    print('keychain v3: wep0 curves %d rewritten in place, %d re-pointed; motions %+d bytes' % (inplace, repoint, grow))

    for off_, old, new, anc in sorted(splices, key=lambda e: (-e[0], e[1] == 0)):
        out[off_:off_ + old] = new
        delta = len(new) - old
        for a_ in anc:
            struct.pack_into('<I', out, a_ + 4, struct.unpack_from('<I', out, a_ + 4)[0] + delta)
    open(dst, 'wb').write(bytes(out))
    print('keychain v3: wrote %s (%d -> %d bytes, %+d); bones %d (unchanged)' % (dst, len(d), len(out), len(out) - len(d),
                                                                              len(names)))


if __name__ == '__main__':
    main()
