"""Chain several KH2 animations into one Dissidia slot and time every swing to the game's hit frames.

  python3 -I kh2_combo.py MODEL.gmo OUT.gmo SLOT CLIPS HITS
    CLIPS = comma list of KH2 indexes (dumps/kh2anim; baked if missing), e.g. 604,608,612,616,620; kNNN = Limit Form
            (P_EX100_KH1F.mset, dumps/kh2anim_kh1f), e.g. k888,k892
    HITS  = comma list of SCRIPT hit frames (60 Hz; middles of the hitbox windows), e.g. 36,48,60
The clips are joined (each starts where the previous ended: KH2 attacks start/end in the same stance), the N fastest
Keyblade-tip moments (N = number of hits, at least MIN_GAP frames apart) are found and the timeline is warped so
they land on HITS in order, and the end lands on the slot's old last frame.
MATCH=1 / FOLLOW=1: as in kh2_attack.py (weapon chain at the hits / root placement from the slot).
NATURAL=1: no warp at all — the KH2 frames as they are (clips joined, root pinned), slot length = clip length; script
blocks are then authored to KH2's own hit moments (kh2_hits.py, spot33_chain.py AUTHOR).
CLIPS may be a single clip; HITS may be '-' (no hits: the clip is just stretched to the slot's length).
"""
import glob
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pose_author as PA  # noqa: E402
from gmo_motion import motions  # noqa: E402
from kh2_attack import follow_root, match_chain, tip_track, warp  # noqa: E402
from kh2_retarget import read_motion_raw, solve_kh2, write_motion  # noqa: E402
from kh2anim import load_baked  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
MIN_GAP = 4


def baked(idx):
    """idx = KH2 P_EX100.mset index (int), or 'kNNN' = Limit Form P_EX100_KH1F.mset index (Sonic Rave / Ars Arcanum /
    Strike Raid / Ragnarok, notes/kh2-limit.md; baked with P_EX100.mdlx = same 228 bones) in dumps/kh2anim_kh1f."""
    kh1f = str(idx).startswith('k')
    n = int(str(idx).lstrip('k'))
    sub, mset = ('dumps/kh2anim_kh1f', 'P_EX100_KH1F.mset') if kh1f else ('dumps/kh2anim', 'P_EX100.mset')
    pat = os.path.join(ROOT, sub, '%03d_????.bin' % n)
    if not glob.glob(pat):
        env = dict(os.environ, DOTNET_ROOT=os.path.join(ROOT, 'tools/dotnet-sdk'), DOTNET_ROLL_FORWARD='Major')
        os.makedirs(os.path.join(ROOT, sub), exist_ok=True)
        subprocess.run([os.path.join(ROOT, 'tools/dotnet-sdk/dotnet'), os.path.join(ROOT, 'tools/kh2bake/bake/out/bake.dll'),
                        os.path.join(ROOT, 'kh2_export/model/P_EX100.mdlx'),
                        os.path.join(ROOT, 'kh2_export/raw/kh2_sixth/original/obj', mset),
                        os.path.join(ROOT, sub), str(n)], env=env, check=True, capture_output=True)
    return sorted(glob.glob(pat))[0]


def pin_root(frames):
    """KH2 attacks travel forward inside the animation (up to 3 m); the game moves the fighter itself, so keep the
    hips over the start point: root X/Z fixed to the first frame (height and all rotations kept)."""
    x0, z0 = frames[0]['root'][0, 3], frames[0]['root'][2, 3]
    for fr in frames:
        fr['root'] = fr['root'].copy()
        fr['root'][0, 3], fr['root'][2, 3] = x0, z0
    return frames


def main():
    model, out, slot = sys.argv[1:4]
    # a clip may be IDX/A-B = only KH2 frames A..B (e.g. 772/0-22: Horizontal Slash without its recovery), IDX/rev
    clips = [x for x in sys.argv[4].split(',')]
    hits = [] if sys.argv[5] == '-' else [float(x) / 2 for x in sys.argv[5].split(',')]  # 60 Hz ticks -> 30 Hz
    d = open(model, 'rb').read()
    PA.setup(d)
    frames = []
    for k, c in enumerate(clips):
        idx, rng = (c.split('/') + [None])[:2]
        f = solve_kh2(PA.SKEL, PA.A, load_baked(baked(idx if idx.startswith('k') else int(idx)))[0])
        if rng == 'rev':                                    # IDX/rev = played backwards (e.g. a backward roll)
            f = f[::-1]
        elif rng:
            a, b = (int(x) for x in rng.split('-'))
            f = f[a:b + 1]
        frames += f if k == 0 else f[1:]
    if os.environ.get('NATURAL'):
        new = pin_root(frames)
        print('%s: clips %s at natural speed, %d frames (%d script)' % (slot, clips, len(new), 2 * len(new)))
        open(out, 'wb').write(write_motion(d, slot, PA.SKEL, new, label='natural'))
        return
    track = tip_track(frames)
    sp = np.r_[0, np.linalg.norm(np.diff(track, axis=0), axis=1)]
    sp = np.convolve(sp, [0.25, 0.5, 0.25], 'same')
    cand = sorted(range(2, len(sp) - 1), key=lambda i: -sp[i])
    peaks = []
    for i in cand:
        if sp[i] >= sp[i - 1] and sp[i] >= sp[i + 1] and all(abs(i - p) >= MIN_GAP for p in peaks):
            peaks.append(i)
        if len(peaks) >= len(hits):
            break
    peaks = sorted(peaks[:len(hits)])
    hits = hits[:len(peaks)]
    mo = {n: (o, s) for n, o, s in motions(d)[0]}
    _, _, old_frames = read_motion_raw(d, *mo[slot])
    end = int(old_frames[1])
    src = [0] + peaks + [len(frames) - 1]
    dst = [0] + hits + [end]
    new = pin_root(warp(frames, src, dst, end + 1))
    if os.environ.get('MATCH') or os.environ.get('FOLLOW'):        # same switches as kh2_attack.py
        from motion_mix import local_frames
        orig = local_frames(d, slot, PA.SKEL)
        if os.environ.get('FOLLOW'):
            follow_root(new, orig)
        if os.environ.get('MATCH'):
            match_chain(new, orig, hits, slot)
    print('%s: clips %s (%d frames), impacts %s -> hits %s, end %d' % (slot, clips, len(frames), peaks,
                                                                      [int(h) for h in hits], end))
    open(out, 'wb').write(write_motion(d, slot, PA.SKEL, new, label='combo'))


if __name__ == '__main__':
    main()
