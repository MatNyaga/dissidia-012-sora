"""Keep the game's grey marker texels when replacing a menu picture. Menu sprites (e.g. the blue/red band behind a
fighter name) sample a tiny exactly-(128,128,128,255) block in a corner of the picture and tint it; a transparent
corner = invisible band (Sora's name, 2026-10-13, notes/qb-grid-pictures.md). keep(template_gim_bytes, new_img)
copies every exactly-128-grey template pixel within 8 px of the left/right edge and 4 px of the top/bottom edge."""
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))


def decode(gim_bytes):
    with tempfile.TemporaryDirectory() as t:
        open(os.path.join(t, 'a.gim'), 'wb').write(gim_bytes)
        subprocess.run([sys.executable, '-I', os.path.join(HERE, 'gim.py'), os.path.join(t, 'a.gim'),
                        os.path.join(t, 'a.png')], check=True, capture_output=True)
        return np.asarray(Image.open(os.path.join(t, 'a.png')).convert('RGBA')).copy()


def keep(template_gim, img):
    t = decode(template_gim)
    a = np.asarray(img.convert('RGBA')).copy()
    h, w = t.shape[:2]
    yy, xx = np.mgrid[:h, :w]
    near = ((xx < 8) | (xx >= w - 8)) & ((yy < 4) | (yy >= h - 4))
    m = near & np.all(t == (128, 128, 128, 255), axis=2)
    a[m] = (128, 128, 128, 255)
    return Image.fromarray(a), int(m.sum())
