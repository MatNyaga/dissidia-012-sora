"""#33's name on the VS / loading / encounter screens (they still said "Cloud"): two standalone index8 GIMs.

- menu/EN/common/chara_name/p_sev120_name.gim (128x32, "Cloud Strife" font) <- BANNER.png (same font as the
  Customization header made by name_banner.py, e.g. tools/art/sora_name_banner.png)
- menu/EN/battle/encount/encount_text_tim2/encount_sev120.gim (256x64, big glowing "Cloud") <- a word glued from
  letters cut out of other fighters' encount pictures (LETTERS below; X0-X1 = the letter's bright fill columns,
  found with a mask alpha >= 250 and R+G+B > 420). Words start at x = 10 like the originals; glows overlap with
  "keep the stronger alpha".

  python3 -I spot33_vsname.py ISO BANNER.png [OUT_PREVIEW.png]
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gim as gimlib  # noqa: E402
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from gim_put import put  # noqa: E402
from gim_markers import keep  # noqa: E402

NAME = 'menu/EN/common/chara_name/p_sev120_name.gim'
ENC = 'menu/EN/battle/encount/encount_text_tim2/encount_%s.gim'
LETTERS = [('eht100', 11, 28), ('sev100', 47, 64), ('one200', 59, 72), ('one200', 38, 54)]    # S o r a
GAP, X0 = 6, 10


def get(iso, path):
    st, sz = pkg_offset(path)
    with open(iso, 'rb') as f:
        return read_at(f, st, sz)


def decode(gim_bytes):
    with tempfile.TemporaryDirectory() as t:
        open(os.path.join(t, 'a.gim'), 'wb').write(gim_bytes)
        subprocess.run([sys.executable, '-I', gimlib.__file__, os.path.join(t, 'a.gim'), os.path.join(t, 'a.png')],
                       check=True, capture_output=True)
        return np.asarray(Image.open(os.path.join(t, 'a.png')).convert('RGBA')).copy()


def own_pixels(pic, a, b, radius=9):
    """mask of the pixels that belong to the letter whose fill is in columns a..b: nearer to its fill than to any
    other letter's fill (so neighbours' outlines/glow stay out), and within RADIUS of it"""
    fill = (pic[:, :, 3] >= 250) & (pic[:, :, :3].astype(int).sum(2) > 420)
    ys, xs = np.nonzero(fill)
    mine = (xs >= a) & (xs <= b)
    gy, gx = np.mgrid[:pic.shape[0], :pic.shape[1]]
    pts = np.stack([gy.ravel(), gx.ravel()], 1)

    def dist(sel):
        d = np.full(len(pts), 1e9)
        for k in range(0, int(sel.sum()), 256):
            q = np.stack([ys[sel][k:k + 256], xs[sel][k:k + 256]], 1)
            d = np.minimum(d, np.sqrt(((pts[:, None, :] - q[None]) ** 2).sum(2)).min(1))
        return d
    dm, do = dist(mine), dist(~mine)
    return ((dm < do) & (dm <= radius)).reshape(pic.shape[:2])


def word(iso):
    pics = {}
    out = np.zeros((64, 256, 4), np.uint8)
    x = X0
    for key, a, b in LETTERS:
        if key not in pics:
            pics[key] = decode(get(iso, ENC % key))
        pic = pics[key]
        m = own_pixels(pic, a, b)
        cols = np.nonzero(m.any(0))[0]
        c0, c1 = cols.min(), cols.max() + 1
        src, msk = pic[:, c0:c1], m[:, c0:c1]
        dx = x - (a - c0)                                  # fill starts at x
        dst = out[:, dx:dx + (c1 - c0)]
        take = msk & (src[:, :, 3] > dst[:, :, 3])
        dst[take] = src[take]
        x += (b - a + 1) + GAP
    return Image.fromarray(out)

def main():
    iso, banner = sys.argv[1:3]
    use_iso(iso)
    big = word(iso)
    if len(sys.argv) > 3:
        big.save(sys.argv[3])
    for path, img in ((NAME, Image.open(banner)), (ENC % 'sev120', big)):
        img, _ = keep(get(iso, path.replace('sev120', 'sev100')), img)   # Cloud's grey band marker texels
        new = put(get(iso, path), img)
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, 'x.gim')
            open(p, 'wb').write(new)
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                               check=True, capture_output=True, text=True)
            print(r.stdout.strip())


if __name__ == '__main__':
    main()
