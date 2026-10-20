"""Natural hit moments of KH2 attack animations: the N fastest Keyblade-tip peaks (kh2_attack.py impacts), printed in
animation frames (30/s) and SCRIPT frames (60/s), plus the clip length. Used to author #33's own script blocks
(spot33_chain.py AUTHOR) for animations played at their natural speed (build_sora.sh `:nat`).

  python3 -I kh2_hits.py MODEL.gmo IDX:N [IDX:N ...]
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kh2_attack as KA  # noqa: E402
import pose_author as PA  # noqa: E402
from kh2_retarget import solve_kh2  # noqa: E402
from kh2anim import load_baked  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    PA.setup(open(sys.argv[1], 'rb').read())
    for arg in sys.argv[2:]:
        idx, n = (int(x) for x in arg.split(':'))
        b = sorted(glob.glob(os.path.join(HERE, '../../dumps/kh2anim/%03d_????.bin' % idx)))[0]
        frames = solve_kh2(PA.SKEL, PA.A, load_baked(b)[0])
        tr = KA.tip_track(frames)
        peaks, sp = KA.impacts(tr, n)
        print('%d: %d frames (%d script) | hits at frames %s = script %s' %
              (idx, len(frames), 2 * len(frames), peaks, [2 * p for p in peaks]))


if __name__ == '__main__':
    main()
