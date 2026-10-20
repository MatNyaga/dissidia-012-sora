"""Put a KH2 attack animation into a Dissidia attack slot, retimed so the swing lands on the game's hitbox.

  python3 -I kh2_attack.py MODEL.gmo BAKED.bin OUT.gmo SLOT HIT_TICK [HIT2_TICK]

HIT_TICK = SCRIPT frame (60 per second) = 2 × animation frame (30 per second) — verified against Cloud's own swings.

- The game's hit frames come from the fighter file's scripts (op 0x00/0x43 windows; table in notes/gmo-format.md
  "Attacks"). HIT_FRAME = middle of the first hit window (HIT2_FRAME = middle of a second one, optional).
- KH2 impact frame(s) = where the Keyblade tip moves fastest (tip = the fitted Keyblade's far end, carried by
  r_hand in the solved Dissidia pose). Time is warped piecewise-linearly so impact → HIT_FRAME (and the second
  fastest, later peak → HIT2_FRAME), and the KH2 end → the slot's old last frame (combo timing stays the game's).
- In-betweens: quaternion slerp per bone, root translation lerp.
- MATCH=1: around the hit frames the root->weapon chain is blended to the slot's original motion (hitbox = weapon).
- MATCH_AT=20/40/60 (script frames to match at), MATCH_SCALE=2 (reference frame = 2 x new frame).
- END=41: new last frame (default: the slot's old length).
- MATCH_SLOT=_630A [MATCH_MODEL=cloud.gmo]: match to another slot's motion (copied script blocks).
- FOLLOW=1: root X/Z + facing from the slot's original motion (EX Burst shots place the fighter with the root).
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pose_author as PA  # noqa: E402
from gmo_motion import motions  # noqa: E402
from kh2_retarget import mat_to_quat, quat_to_mat, read_motion_raw, solve_kh2, trs, write_motion  # noqa: E402
from kh2anim import load_baked  # noqa: E402


CHAIN = ['root', 'hip', 'waist', 'chest', 'r_clavicle', 'r_uparm_c', 'r_uparm', 'r_foarm', 'r_hand', 'r_wep']
MIN_GAP = 6                                          # KH2 frames between two separate swings


def tip_track(frames):
    """world position of the Keyblade tip per frame"""
    names, parent = PA.SKEL[0], PA.SKEL[1]
    g, b = PA.load_gltf(PA.KEYGLTF)
    V = np.concatenate([PA.acc(g, b, p['attributes']['POSITION']) for m in g['meshes']
                        if m['name'].startswith('wep1|') for p in m['primitives']])
    grip = np.array(json.load(open(PA.FIT.replace('.map.json', '.grip.json')))['grip'])
    tip = V[np.argmax(np.linalg.norm(V - grip, axis=1))]
    local = np.linalg.inv(PA.SKEL[4]['r_hand']) @ np.r_[tip, 1]
    out = []
    for fr in frames:
        w = PA.Pose(fr).world()
        out.append((w['r_hand'] @ local)[:3])
    return np.array(out)


def impacts(track, n=2):
    sp = np.r_[0, np.linalg.norm(np.diff(track, axis=0), axis=1)]
    sp = np.convolve(sp, [0.25, 0.5, 0.25], 'same')
    peaks = [i for i in range(2, len(sp) - 1) if sp[i] >= sp[i - 1] and sp[i] >= sp[i + 1]]
    peaks.sort(key=lambda i: -sp[i])
    return sorted(peaks[:n]), sp


def warp(frames, src_keys, dst_keys, n_out):
    """piecewise-linear time map dst->src through matching key lists, then slerp"""
    out = []
    for t in range(n_out):
        s = float(np.interp(t, dst_keys, src_keys))
        a = int(np.floor(s))
        b2 = min(a + 1, len(frames) - 1)
        u = s - a
        fa, fb = frames[a], frames[b2]
        cur = {}
        for nm in fa:
            q0, q1 = mat_to_quat(fa[nm][:3, :3]), mat_to_quat(fb[nm][:3, :3])
            cur[nm] = trs((1 - u) * fa[nm][:3, 3] + u * fb[nm][:3, 3], quat_to_mat(PA.slerp(q0, q1, u)))
        out.append(cur)
    return out


def pin_root(frames):
    """KH2 attacks travel forward inside the animation (up to 3 m); the game moves the fighter itself, so keep the
    hips over the start point: root X/Z fixed to the first frame (height and all rotations kept)."""
    x0, z0 = frames[0]['root'][0, 3], frames[0]['root'][2, 3]
    for fr in frames:
        fr['root'] = fr['root'].copy()
        fr['root'][0, 3], fr['root'][2, 3] = x0, z0
    return frames


def match_chain(new, orig, hits, slot, ramp=4, shift=0.0, scale=1.0):
    """the game's hitbox follows the weapon's world position: around each hit frame, blend the root->weapon chain to
    the slot's original (Cloud) motion so the Keyblade is where Cloud's sword was (rest stays KH2)"""
    for h in hits:
        a, b = int(h) - 2, int(h) + 3
        for f in range(len(new)):
            w = 1.0 if a <= f <= b else (f - (a - ramp)) / ramp if a - ramp <= f < a else \
                1 - (f - b) / ramp if b < f <= b + ramp else 0
            if w <= 0:
                continue
            # shift = original hit − new hit (frames); scale = original frames per new frame (sped-up copied blocks)
            g = min(max(int(round(f * scale + shift)), 0), len(orig) - 1)
            for nm in CHAIN:
                q = PA.slerp(mat_to_quat(new[f][nm][:3, :3]), mat_to_quat(orig[g][nm][:3, :3]), w)
                t = (1 - w) * new[f][nm][:3, 3] + w * orig[g][nm][:3, 3]
                new[f][nm] = trs(t, quat_to_mat(q))
        print('%s: weapon chain matched to the original motion on frames %d-%d' % (slot, a, b))


def _yaw(r, v):
    w = r @ v
    return np.arctan2(w[0], w[2])


def follow_root(new, orig):
    """EX Burst shots place the fighter with the root bone (Cloud dashes metres around the enemy). Keep the slot's
    root X/Z and facing (yaw), add KH2's own height change (crouch / jump) on top of the slot's height."""
    rest_y = PA.SKEL[2]['root'][1]
    r0 = new[0]['root'][:3, :3]
    v = min(np.eye(3), key=lambda a: abs((r0 @ a)[1]))               # local axis that lies flattest in KH2 frame 0
    prev = None
    for f, fr in enumerate(new):
        o = orig[min(f, len(orig) - 1)]['root']
        dy = _yaw(o[:3, :3], v) - _yaw(fr['root'][:3, :3], v)
        if prev is not None:                                            # unwrap: no 360-degree flips between frames
            dy = prev + (dy - prev + np.pi) % (2 * np.pi) - np.pi
        prev = dy
        c, s_ = np.cos(dy), np.sin(dy)
        ry = np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]])
        t = o[:3, 3].copy()
        t[1] += fr['root'][1, 3] - rest_y
        fr['root'] = trs(t, ry @ fr['root'][:3, :3])
    return new


def main():
    model, baked, out, slot = sys.argv[1:5]
    hits = [float(x) / 2 for x in sys.argv[5:7]]           # script frames are 60 Hz, motion frames 30 Hz
    d = open(model, 'rb').read()
    PA.setup(d)
    frames = solve_kh2(PA.SKEL, PA.A, load_baked(baked)[0])
    track = tip_track(frames)
    peaks, sp = impacts(track, len(hits))
    if len(peaks) < len(hits) or (len(peaks) == 2 and peaks[1] - peaks[0] < MIN_GAP):
        peaks, hits = impacts(track, 1)[0], hits[:1]       # two peaks of one swing: time the first hit only
    mo = {n: (o, s) for n, o, s in motions(d)[0]}
    _, _, old_frames = read_motion_raw(d, *mo[slot])
    end = int(os.environ.get('END') or old_frames[1])     # END=frames: new length (copied/scaled script blocks)
    src = [0] + peaks[:len(hits)] + [len(frames) - 1]
    dst = [0] + hits + [end]
    if any(b <= a for a, b in zip(src, src[1:])) or any(b <= a for a, b in zip(dst, dst[1:])):
        src, dst = [0, peaks[0], len(frames) - 1], [0, hits[0], end]          # fall back to one key
    new = pin_root(warp(frames, src, dst, end + 1))
    if os.environ.get('MATCH') or os.environ.get('FOLLOW'):
        from motion_mix import local_frames
        # MATCH_SLOT (+ MATCH_MODEL): take the reference motion from another slot / model — for a slot whose script
        # block is a COPY of another move's (spot33_chain.py COPY), match the weapon to THAT move's original swing
        ref_slot = os.environ.get('MATCH_SLOT', slot)
        ref = open(os.environ['MATCH_MODEL'], 'rb').read() if os.environ.get('MATCH_MODEL') else d
        orig = local_frames(ref, ref_slot, PA.SKEL)
        if os.environ.get('FOLLOW'):
            follow_root(new, orig)
        if os.environ.get('MATCH'):
            mf = os.environ.get('MATCH_FROM')                # script frame of the slot's ORIGINAL hit (hits moved earlier)
            # MATCH_AT=20/40/60: match at these SCRIPT frames instead of the timing hits (all hits of a multi-hit move);
            # MATCH_SCALE=2: the reference motion runs 2x longer (block copied with spot33_chain SCALE 0.5)
            at = [float(x) / 2 for x in os.environ['MATCH_AT'].split('/')] if os.environ.get('MATCH_AT') else hits
            match_chain(new, orig, at, slot, shift=(float(mf) / 2 - hits[0]) if mf else 0.0,
                        scale=float(os.environ.get('MATCH_SCALE', 1)))
    print('%s: KH2 impacts %s -> animation frames %s, %d -> %d frames' % (slot, src[1:-1], dst[1:-1],
                                                                          len(frames), end + 1))
    open(out, 'wb').write(write_motion(d, slot, PA.SKEL, new, label=os.path.basename(baked)))


if __name__ == '__main__':
    main()
