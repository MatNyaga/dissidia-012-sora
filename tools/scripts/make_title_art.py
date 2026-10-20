"""Sora's menu pictures in the KH2 opening-menu art style. Default source (Mat, 2026-10-13): the KH2 menu art of
Sora standing in the water, looking back (downloads/menuart/ref_noice.png = Mat's reference, ice cream painted
out). ICECREAM=1 = old version below: (Mat: "use the art style on the KH2 opening menu"):
crops of Nomura's watercolour title illustration kh2_export/raw/kh2_first/remastered/menu/us/title.2ld/
US_title_2ld4.png (1024², Sora in front eating sea-salt ice cream, Roxas behind, orange sky). Edges fade to
transparent (no hard cut-out: the painting has a background). Writes the same files the disc tools read:
  tools/art/sora_face_vs64.png, sora_face_hud128.png, sora_face_eyes.png  (spot33_faces.py)
  tools/art/qb_art.png, qb_icon.png, qb_face.png, qb_face_r.png, qb_arcade.png (spot33_qbpics.py / spot33_faces.py)
All quantised to 256 colours.  python3 -I make_title_art.py
"""
import os

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ART = os.path.join(ROOT, 'tools/art')
SRC = os.path.join(ROOT, 'kh2_export/raw/kh2_first/remastered/menu/us/title.2ld/US_title_2ld4.png')


def crop(img, box, size):
    return img.crop(box).resize(size, Image.LANCZOS)


def fade(img, inner=0.72, shape='ellipse', sides=None):
    """alpha fade towards the edges: ellipse (portraits) or given sides ('l','r','t','b')"""
    a = np.asarray(img).copy()
    h, w = a.shape[:2]
    yy, xx = np.mgrid[:h, :w]
    if shape == 'ellipse':
        r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
        m = np.clip((1 - r) / (1 - inner), 0, 1)
    else:
        m = np.ones((h, w))
        edge = 1 - inner
        for s in sides:
            d = {'l': xx / w, 'r': (w - 1 - xx) / w, 't': yy / h, 'b': (h - 1 - yy) / h}[s]
            m = np.minimum(m, np.clip(d / edge, 0, 1))
    a[..., 3] = (a[..., 3] * m).astype(np.uint8)
    return Image.fromarray(a)


def q(img):
    """256 colours; soft alpha is dithered to fully on/off first (the palette can't hold smooth alpha + colours:
    fades came out in visible steps)"""
    a = np.asarray(img).astype(float).copy()
    al = a[..., 3] / 255.0
    h, w = al.shape
    for y in range(h):                                   # Floyd-Steinberg on alpha only
        for x in range(w):
            o = al[y, x]
            n = 1.0 if o >= 0.5 else 0.0
            al[y, x] = n
            e = o - n
            if x + 1 < w:
                al[y, x + 1] += e * 7 / 16
            if y + 1 < h:
                if x > 0:
                    al[y + 1, x - 1] += e * 3 / 16
                al[y + 1, x] += e * 5 / 16
                if x + 1 < w:
                    al[y + 1, x + 1] += e * 1 / 16
    a[..., 3] = al * 255
    return Image.fromarray(a.astype(np.uint8)).quantize(256, method=2).convert('RGBA')


REF = os.path.join(ROOT, 'downloads/menuart/ref_noice.png')   # Mat's pick: KH2 menu art, middle Sora, ice cream removed


def cutout(path):
    """middle panel (x 215..425) of the reference, background removed cleanly:
    - background = near-white pixels CONNECTED to the panel border (flood fill), so white highlights inside stay
    - edge pixels: alpha from how far they are from paper white, colour un-mixed from white (no white halo)
    - alpha blurred by 1 px and tiny specks dropped (JPEG noise made a speckled outline before)"""
    from collections import deque
    a = np.asarray(Image.open(path).convert('RGB')).astype(float)[:, 215:425]
    h, w = a.shape[:2]
    near = a.min(2) > 200
    bg = np.zeros((h, w), bool)
    dq = deque([(y, x) for y in range(h) for x in (0, w - 1)] + [(0, x) for x in range(w)])
    while dq:
        y, x = dq.popleft()
        if 0 <= y < h and 0 <= x < w and near[y, x] and not bg[y, x]:
            bg[y, x] = True
            dq.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))
    # Mat (2026-10-14): "outline a bit pixelated … around the nose I see the background": pale skin at the profile
    # edge was flood-filled as background. Close the figure mask (fills nicks at nose / lips / chin, up to ~3 px),
    # then fill holes from the border again, so only real paper stays background.
    fg = Image.fromarray((~bg * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))
    fgc = np.asarray(fg) > 127
    bg2 = np.zeros((h, w), bool)
    dq = deque([(y, x) for y in range(h) for x in (0, w - 1)] + [(0, x) for x in range(w)])
    while dq:
        y, x = dq.popleft()
        if 0 <= y < h and 0 <= x < w and not fgc[y, x] and not bg2[y, x]:
            bg2[y, x] = True
            dq.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))
    filled = bg & ~bg2                                         # candidate gaps closed by the mask closing
    # keep only gaps next to SKIN (nose / lips / chin); gaps between hair spikes stay background (white wedges)
    skin = (a[..., 0] > 170) & (a[..., 0] > a[..., 1] + 8) & (a[..., 1] > a[..., 2] + 8)
    near_skin = np.asarray(Image.fromarray((skin * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))) > 127
    filled &= near_skin
    bg = bg & ~filled
    # alpha: 0 in the background, soft ramp on pixels next to it, 1 inside
    soft = np.clip((255 - a.min(2)) / 70.0, 0, 1)
    soft[filled] = 1.0
    alpha = np.where(bg, 0.0, 1.0)
    edge = np.zeros_like(bg)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            edge |= np.roll(np.roll(bg, dy, 0), dx, 1)
    edge &= ~bg
    alpha[edge] = soft[edge]
    img = Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9))
    alpha = np.asarray(img).astype(float) / 255
    alpha[bg & (alpha < 0.5)] = 0
    al = np.maximum(alpha, 1e-3)[..., None]
    col = np.clip((a - (1 - al) * 255) / al, 0, 255)          # un-mix the white
    col = np.where(al > 0.98, a, col)
    return Image.fromarray(np.dstack([col, alpha * 255]).astype(np.uint8))


def quant256(img, iters=12):
    """256-colour RGBA palette by k-means on premultiplied colour + alpha (Pillow's octree posterised the soft edge
    alpha -> jagged outlines; no libimagequant here). Exact when the image has <= 256 colours."""
    a = np.asarray(img.convert('RGBA')).reshape(-1, 4).astype(float)
    u, inv = np.unique(a, axis=0, return_inverse=True)
    if len(u) <= 256:
        return img.convert('RGBA')
    w = np.bincount(inv.ravel()).astype(float)
    f = np.hstack([u[:, :3] * u[:, 3:] / 255.0, u[:, 3:] * 1.5])    # premultiplied RGB, alpha weighted up
    rng = np.random.default_rng(0)
    c = f[rng.choice(len(f), 256, replace=False, p=w / w.sum())]
    for _ in range(iters):
        d = ((f[:, None, :] - c[None, :, :]) ** 2).sum(2) if len(f) * 256 < 4e7 else None
        lab = d.argmin(1) if d is not None else np.concatenate([((f[i:i + 20000, None, :] - c[None]) ** 2).sum(2).argmin(1)
                                                                for i in range(0, len(f), 20000)])
        for j in range(256):
            m = lab == j
            if m.any():
                c[j] = (f[m] * w[m, None]).sum(0) / w[m].sum()
    al = np.clip(c[:, 3] / 1.5, 0, 255)
    rgb = np.where(al[:, None] > 0, c[:, :3] * 255.0 / np.maximum(al[:, None], 1e-6), 0)
    pal = np.hstack([np.clip(rgb, 0, 255), al[:, None]]).round().astype(np.uint8)
    pal[al < 1] = 0
    out = pal[lab][inv.ravel()].reshape(np.asarray(img).shape[:2] + (4,))
    return Image.fromarray(out, 'RGBA')


FACES = ('sora_face_vs64', 'sora_face_hud128', 'sora_face_eyes', 'qb_face', 'qb_face_r', 'qb_custface', 'qb_icon', 'qb_art')
DEEPEN = (1.45, 0.88, 0.90)      # gamma (darker mid-tones), brightness, green scale (gold -> deeper amber)


def deepen(img):
    """darker, deeper gold for the small face pictures (the menu painting is sunlit gold; on the HUD it read blond)"""
    g, k, gs = DEEPEN
    a = np.asarray(img).astype(float)
    rgb = np.clip((a[..., :3] / 255.0) ** g * k, 0, 1)
    rgb[..., 1] *= gs
    rgb[..., 2] *= gs ** 1.5
    return Image.fromarray(np.dstack([rgb * 255, a[..., 3]]).astype(np.uint8))


def main_ref():
    sora = cutout(REF)                                          # 210 x 640
    out = {}
    head = sora.crop((10, 0, 200, 190))                         # head + shoulders (profile)
    out['sora_face_vs64'] = sora.crop((58, 40, 156, 138)).resize((64, 64), Image.LANCZOS)   # face fills the square (eye at x85 y85, nose x70 y107, chin y123)
    # battle HUD: game heads fill x 38-86, y 46-100 (Cloud/Squall/Lightning), face close-up, rounded bottom
    face = sora.crop((35, 10, 175, 150))                       # face close-up centred on the eye (x ~70, y ~85)
    bb = face.getbbox()
    face = face.crop(bb).resize((46, round(46 * (bb[3] - bb[1]) / (bb[2] - bb[0]))), Image.LANCZOS)
    ha = np.asarray(face).copy()
    fh = ha.shape[0]
    yy, xx = np.mgrid[:fh, :46]
    ha[..., 3] = (ha[..., 3] * np.clip((1 - np.hypot((xx - 23) / 23.0, (yy - fh / 2) / (fh / 2.0))) * 8, 0, 1)).astype(np.uint8)   # soft oval
    hud = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    hud.alpha_composite(Image.fromarray(ha), (44, 100 - fh))   # Mat: slightly right
    out['sora_face_hud128'] = hud
    band = sora.crop((58, 68, 152, 103)).resize((86, 32), Image.LANCZOS)   # eye + cheek (profile faces left)
    r = Image.new('RGBA', (128, 32), (0, 0, 0, 0)); r.alpha_composite(fade(band, 0.88, 'sides', 'l'), (42, 0))
    lft = Image.new('RGBA', (128, 32), (0, 0, 0, 0)); lft.alpha_composite(fade(band, 0.88, 'sides', 'r'), (0, 0))
    out['sora_face_eyes'] = r
    out['qb_face_r'] = r
    out['qb_face'] = lft
    # Customization header strip (customize pack entry 74): whole face forehead→chin like Cloud's, left-aligned
    cf = sora.crop((44, 50, 188, 122)).resize((64, 32), Image.LANCZOS)   # eye x85 y85, nose x70 y107, chin y123
    cust = Image.new('RGBA', (128, 32), (0, 0, 0, 0))
    cust.alpha_composite(fade(cf, 0.8, 'sides', 'r'), (0, 0))
    out['qb_custface'] = cust
    icon = Image.new('RGBA', (32, 64), (0, 0, 0, 0))
    icon.alpha_composite(sora.crop((50, 26, 144, 167)).resize((32, 48), Image.LANCZOS), (0, 0))   # tight face like the others
    out['qb_icon'] = icon
    body = sora.crop((0, 0, 210, 560))                         # whole figure down to the water
    big = sora.crop((0, 0, 210, 400)).resize((134, 256), Image.LANCZOS)   # select art: head to thighs like Cloud's
    art = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    art.alpha_composite(dissidia_style(big), (62, 0))          # less empty space on the left (Mat, vs Vaan)
    out['qb_art'] = art
    arc = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    bg = Image.new('RGBA', (480, 272), (255, 255, 255, 255))
    full = body.resize((round(210 * 272 / 560), 272), Image.LANCZOS)
    bg.alpha_composite(full, (60, 0))
    face = fade(head.resize((300, 300), Image.LANCZOS), 0.7)
    fa = np.asarray(face).copy(); fa[..., 3] = (fa[..., 3] * 0.55).astype(np.uint8)
    bg.alpha_composite(Image.fromarray(fa), (190, -20))
    arc.alpha_composite(bg, (0, 0))
    out['qb_arcade'] = arc
    for k in FACES:                                             # Mat (2026-10-14): "the gold tint needs to be darker"
        out[k] = deepen(out[k])
    for k, im in out.items():
        quant256(im).save(os.path.join(ART, k + '.png'))
        print(k, im.size)


def dissidia_style(img, dark=0.80, rim=1):
    """make a cut-out sit with Dissidia's menu art (Mat: outline noisy, art should be darker): colours darkened and
    a bit more contrast, alpha edge cleaned (hard threshold + 1 px soften), smooth white rim + faint shadow behind"""
    from PIL import ImageFilter
    a = np.asarray(img).astype(float)
    rgb = a[..., :3] / 255.0
    rgb = np.clip(((rgb - 0.5) * 1.12 + 0.5) * dark, 0, 1)          # contrast up, darker
    al = (a[..., 3] > 110).astype(float)                             # clean edge (no speckled half-alpha pixels)
    al = np.asarray(Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.5))) / 255.0
    pad = rim + 4
    h, w = al.shape
    A = np.zeros((h + 2 * pad, w + 2 * pad))
    A[pad:pad + h, pad:pad + w] = al
    m = Image.fromarray((A * 255).astype(np.uint8))
    rim_m = m.filter(ImageFilter.MaxFilter(2 * rim + 1)).filter(ImageFilter.GaussianBlur(0.7))
    sh = m.filter(ImageFilter.MaxFilter(2 * rim + 3)).filter(ImageFilter.GaussianBlur(3))
    out = Image.new('RGBA', m.size, (0, 0, 0, 0))
    out.paste(Image.new('RGBA', m.size, (40, 40, 60, 255)), (0, 0), sh.point(lambda v: int(v * 0.3)))
    out.paste(Image.new('RGBA', m.size, (255, 255, 255, 255)), (0, 0), rim_m)
    fig = np.zeros((h + 2 * pad, w + 2 * pad, 4))
    fig[pad:pad + h, pad:pad + w, :3] = rgb * 255
    fig[pad:pad + h, pad:pad + w, 3] = al * 255
    out.alpha_composite(Image.fromarray(fig.astype(np.uint8)))
    return out.crop((pad, pad, pad + w, pad + h))


def q_bg(img):
    """small square pictures: put on white paper (like the art) instead of see-through"""
    bg = Image.new('RGBA', img.size, (255, 255, 255, 255))
    bg.alpha_composite(img)
    return bg


def main():
    if os.path.exists(REF) and not os.environ.get('ICECREAM'):
        return main_ref()
    src = Image.open(SRC).convert('RGBA')
    out = {}
    out['sora_face_vs64'] = crop(src, (752, 172, 882, 302), (64, 64))                       # VS screen: full square
    head = fade(crop(src, (728, 158, 908, 338), (72, 72)), 0.6)
    hud = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    hud.alpha_composite(head, (28, 40))
    out['sora_face_hud128'] = hud                                                          # battle HUD head
    band = crop(src, (735, 228, 905, 288), (91, 32))                                       # eyes band
    r = Image.new('RGBA', (128, 32), (0, 0, 0, 0))
    r.alpha_composite(fade(band, 0.75, 'sides', 'l'), (37, 0))
    out['sora_face_eyes'] = r
    out['qb_face_r'] = r
    lft = Image.new('RGBA', (128, 32), (0, 0, 0, 0))
    lft.alpha_composite(fade(band, 0.75, 'sides', 'r'), (0, 0))
    out['qb_face'] = lft
    # Customization header strip (customize pack entry 74): whole face forehead→chin like Cloud's, left-aligned
    cf = sora.crop((44, 50, 188, 122)).resize((64, 32), Image.LANCZOS)   # eye x85 y85, nose x70 y107, chin y123
    cust = Image.new('RGBA', (128, 32), (0, 0, 0, 0))
    cust.alpha_composite(fade(cf, 0.8, 'sides', 'r'), (0, 0))
    out['qb_custface'] = cust
    icon = Image.new('RGBA', (32, 64), (0, 0, 0, 0))
    icon.alpha_composite(crop(src, (760, 165, 872, 305), (32, 40)), (0, 0))                # grid shows the top 32x35
    out['qb_icon'] = icon
    art = fade(crop(src, (640, 150, 1010, 520), (256, 256)), 0.8, 'sides', 'lbt')         # select screen big art
    out['qb_art'] = art
    arc = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    arc.alpha_composite(crop(src, (450, 140, 1020, 463), (480, 272)), (0, 0))              # arcade picture (480x272 used)
    out['qb_arcade'] = arc
    for k, im in out.items():
        q(im).save(os.path.join(ART, k + '.png'))
        print(k, im.size)


if __name__ == '__main__':
    main()
