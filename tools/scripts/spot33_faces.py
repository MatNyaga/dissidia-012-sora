"""#33's small face pictures from KH2's Jiminy's Journal portrait of Sora (HD remaster, 256x256, see-through bg):
kh2_export/raw/kh2_fifth/remastered/menu/jmface_ex0.imd/-0.dds (ex1 = smiling).

- menu/JP/story_mode/chara2/p_sev120_1p.gim            64x64   VS screen face (tight crop)
- menu/JP/battle/chara_image/P_SEV120_1P.gim         128x128  battle HUD head (small head, see-through around)
- menu/JP/common/chara_face_in_name_r/p_sev120_face_in_name_r.gim  128x32  eye strip next to the name
  (Customization header; was Aerith's) — right-aligned, faded to the left like the originals
All are linear index8 GIMs: the PNG is quantised to 256 colours (with alpha) and written in place (gim_put.put),
then put into the ISO with pkg_put.py. Previews go to tools/art/sora_face_*.png.
Also FILES: arcade-mode picture + character_select art from make_select_art.py (tools/art/qb_arcade/qb_art.png).

  python3 -I spot33_faces.py ISO
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from gim_put import put  # noqa: E402
from gim_markers import keep  # noqa: E402

SRC = os.path.join(ROOT, 'kh2_export/raw/kh2_fifth/remastered/menu/jmface_ex0.imd/-0.dds')
ART = os.path.join(ROOT, 'tools/art')


def load():
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'f.png')
        subprocess.run(['convert', SRC, p], check=True)
        return Image.open(p).convert('RGBA')


def quant(img):
    """<= 256 RGBA colours (gim_put keeps them exactly); method 2 = fast octree (keeps alpha; old Pillow)"""
    return img.quantize(256, method=2).convert('RGBA')


def vs64(src):
    return src.crop((30, 60, 222, 252)).resize((64, 64), Image.LANCZOS)


def hud128(src):
    out = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    head = src.resize((62, 62), Image.LANCZOS)
    a = np.asarray(head).copy()                          # round off the shoulders like Cloud's bust
    yy, xx = np.mgrid[:62, :62]
    a[..., 3] = (a[..., 3] * np.clip((31 - np.hypot(xx - 31, (yy - 26) * 0.9)) / 4 + 1, 0, 1)).astype(np.uint8)
    out.alpha_composite(Image.fromarray(a), (34, 44))
    return out


def eyes(src):
    band = src.crop((20, 120, 256, 200)).resize((94, 32), Image.LANCZOS)
    a = np.asarray(band).copy()
    a[..., 3] = (a[..., 3] * np.clip(np.arange(94) / 14.0, 0, 1)[None, :]).astype(np.uint8)
    out = Image.new('RGBA', (128, 32), (0, 0, 0, 0))
    out.alpha_composite(Image.fromarray(a), (34, 0))
    return out


PICS = [('menu/JP/story_mode/chara2/p_sev120_1p.gim', vs64, 'vs64'),
        ('menu/JP/battle/chara_image/P_SEV120_1P.gim', hud128, 'hud128'),
        ('menu/JP/common/chara_face_in_name_r/p_sev120_face_in_name_r.gim', eyes, 'eyes')]


# finished pictures from make_select_art.py (also loaded by file name)
FILES = [('menu/JP/arcademode/arcade_last_chara_tim2/arcade_last_sev120.gim', 'qb_arcade.png'),   # 512x512
         ('menu/JP/character_select/chara2/p_sev120_1p.gim', 'qb_art.png')]                       # 256x256


def main():
    iso = sys.argv[1]
    use_iso(iso)
    src = load()
    # pictures come from make_title_art.py (KH2 title-art style, Mat) when present, else the journal-face crops
    todo = [(path, Image.open(os.path.join(ART, 'sora_face_%s.png' % tag)).convert('RGBA')
             if os.path.exists(os.path.join(ART, 'sora_face_%s.png' % tag)) and os.environ.get('JOURNAL') is None
             else quant(make(src)), None) for path, make, tag in PICS]
    todo += [(path, Image.open(os.path.join(ART, png)).convert('RGBA'), None) for path, png in FILES]
    for path, img, tag in todo:
        if tag:
            img.save(os.path.join(ART, 'sora_face_%s.png' % tag))
        st, sz = pkg_offset(path)
        with open(iso, 'rb') as f:
            tpl = read_at(f, st, sz)
            cst, csz = pkg_offset(path.replace('sev120', 'sev100').replace('SEV120', 'SEV100'))
            img, _ = keep(read_at(f, cst, csz), img)              # Cloud's grey marker texels
            new = put(tpl, img)
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, 'x.gim')
            open(p, 'wb').write(new)
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                               check=True, capture_output=True, text=True)
            print(r.stdout.strip())


if __name__ == '__main__':
    main()
