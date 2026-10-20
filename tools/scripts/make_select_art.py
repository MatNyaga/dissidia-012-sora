"""Sora's Quick Battle select-screen pictures (sizes = Cloud's): writes tools/art/qb_*.png
  art    256x256  big picture: 3D render of the win pose (dumps/renders/portrait/win_20.png, tools/blender/
                  render_portrait.py) with a white outline + soft shadow like Dissidia's Nomura art
  icon   32x64    grid cell: KH2 Jiminy's Journal face (jmface_ex0)
  face   128x32   eye strip, left-aligned (faded to the right); face_r = right-aligned (= sora_face_eyes)
  logo   128x64   KINGDOM HEARTS II logo on a white 89x50 card (pieces from KH2's title screen texture)
  name   128x32   "Sora" (tools/art/sora_name_banner.png)
  arcade 512x512  arcade-mode picture (480x272 used): render left, big faded journal face right
  python3 -I make_select_art.py
"""
import os
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ART = os.path.join(ROOT, 'tools/art')
RENDER = os.path.join(ROOT, 'dumps/renders/portrait/win_20.png')
JM = os.path.join(ROOT, 'kh2_export/raw/kh2_fifth/remastered/menu/jmface_ex0.imd/-0.dds')
TITLE = os.path.join(ROOT, 'kh2_export/raw/kh2_first/remastered/menu/us/title.2ld/US_title_2ld7.png')


def dds(path):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'a.png')
        subprocess.run(['convert', path, p], check=True)
        return Image.open(p).convert('RGBA')


def crop_alpha(img, box=None, thr=8):
    if box:
        img = img.crop(box)
    a = np.asarray(img)[..., 3]
    ys, xs = np.nonzero(a > thr)
    return img.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def outline(img, width=2, glow=5):
    """white rim + soft dark shadow behind a cut-out (Dissidia menu art style)"""
    a = img.split()[3]
    rim = a.filter(ImageFilter.MaxFilter(2 * width + 1))
    shadow = rim.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(glow))
    out = Image.new('RGBA', img.size, (0, 0, 0, 0))
    out.paste(Image.new('RGBA', img.size, (60, 60, 80, 255)), (0, 0), shadow.point(lambda v: int(v * 0.55)))
    out.paste(Image.new('RGBA', img.size, (255, 255, 255, 255)), (0, 0), rim)
    out.alpha_composite(img)
    return out


def art():
    body = crop_alpha(Image.open(RENDER).convert('RGBA'))
    h = 300                                              # taller than the picture: cut at the shins like Cloud's
    body = body.resize((round(body.width * h / body.height), h), Image.LANCZOS)
    pad = 12
    canvas = Image.new('RGBA', (body.width + 2 * pad, body.height + 2 * pad), (0, 0, 0, 0))
    canvas.alpha_composite(body, (pad, pad))
    canvas = outline(canvas)
    out = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    out.alpha_composite(canvas.crop((0, 0, canvas.width, min(canvas.height, 256 + 4))).crop((0, 4, canvas.width, 260)),
                        (150 - canvas.width // 2, 0))
    return out


def icon(jm):
    """the grid cell shows only about the top 32x35 of the 32x64 icon: whole face there, collar below"""
    out = Image.new('RGBA', (32, 64), (0, 0, 0, 0))
    out.alpha_composite(jm.crop((28, 8, 228, 256)).resize((32, 40), Image.LANCZOS), (0, 0))
    return out


def strip(jm, right):
    band = jm.crop((20, 120, 256, 200)).resize((94, 32), Image.LANCZOS)
    a = np.asarray(band).copy()
    ramp = np.clip(np.arange(94) / 14.0, 0, 1)
    a[..., 3] = (a[..., 3] * (ramp if right else ramp[::-1])[None, :]).astype(np.uint8)
    out = Image.new('RGBA', (128, 32), (0, 0, 0, 0))
    out.alpha_composite(Image.fromarray(a), (34, 0) if right else (0, 0))
    return out


def logo():
    t = Image.open(TITLE).convert('RGBA')
    word = crop_alpha(t, (40, 540, 720, 760))
    heart = crop_alpha(t, (640, 60, 1010, 480))
    W, H = 890, 500
    card = Image.new('RGBA', (W, H), (255, 255, 255, 255))
    hh = 400
    heart = heart.resize((round(heart.width * hh / heart.height), hh), Image.LANCZOS)
    card.alpha_composite(heart, (W - heart.width - 20, 20))
    ww = 850
    word = word.resize((ww, round(word.height * ww / word.width)), Image.LANCZOS)
    card.alpha_composite(word, (15, H - word.height - 40))
    out = Image.new('RGBA', (128, 64), (0, 0, 0, 0))
    out.paste(card.resize((89, 50), Image.LANCZOS), (0, 0))
    return out


def arcade(jm):
    """512x512 texture, used part 480x272 like Cloud's: soft background, big faded face right, full body left"""
    W, H = 480, 272
    y = np.linspace(0, 1, H)[:, None, None]
    bg = (np.array([214, 200, 172]) * (1 - y) + np.array([238, 232, 220]) * y) * np.ones((1, W, 1))
    out = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    out.paste(Image.fromarray(np.concatenate([bg, np.full((H, W, 1), 255)], 2).astype(np.uint8)), (0, 0))
    face = jm.resize((300, 300), Image.LANCZOS)
    a = np.asarray(face).copy()
    a[..., 3] = (a[..., 3] * np.clip(np.arange(300) / 110.0, 0, 1)[None, :] * 0.85).astype(np.uint8)
    out.alpha_composite(Image.fromarray(a), (W - 300 + 10, -10))
    body = crop_alpha(Image.open(RENDER).convert('RGBA'))
    body = body.resize((round(body.width * 250 / body.height), 250), Image.LANCZOS)
    pad = 10
    c = Image.new('RGBA', (body.width + 2 * pad, body.height + 2 * pad), (0, 0, 0, 0))
    c.alpha_composite(body, (pad, pad))
    out.alpha_composite(outline(c), (40, 2))
    return out


def main():
    jm = dds(JM)
    pics = {'art': art(), 'icon': icon(jm), 'face': strip(jm, False), 'face_r': strip(jm, True), 'logo': logo(),
            'name': Image.open(os.path.join(ART, 'sora_name_banner.png')).convert('RGBA'), 'arcade': arcade(jm)}
    for k, im in pics.items():
        im = im.quantize(256, method=2).convert('RGBA')   # good 256-colour palette (gim_put keeps it exactly)
        im.save(os.path.join(ART, 'qb_%s.png' % k))
        print(k, im.size)


if __name__ == '__main__':
    main()
