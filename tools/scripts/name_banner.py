"""Make a fighter name banner (128x32 menu picture) from letters cut out of the game's own banners.

  python3 -I name_banner.py PAK.bin OUT.png TEXT SPEC [SPEC ...]
    PAK.bin = a "menu pak" with p_*_name.tm2 GIMs (e.g. menu/EN/menu_lpk_customize_gim_0.bin)
    SPEC    = LETTER=banner:X0-X1   e.g. S=p_eht100_name:8-17  (pixel columns of that letter's fill)
Find X0-X1 with `letters(img, 230)` (fully opaque runs); outlines touch, so the crop takes 2 px more each side.
The new word is centred like the originals (same baseline/height).
"""
import re
import struct
import sys

from PIL import Image

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import gim  # noqa: E402


PAD, GAP = int(__import__("os").environ.get("PAD", 1)), int(__import__("os").environ.get("GAP", -1))


def banners(d):
    mig = [m.start() for m in re.finditer(rb'MIG\.00\.1PSP', d)]
    out = {}
    for k, i in enumerate(mig):
        m = re.search(rb'([a-z0-9_]{4,40})\.tm2', d[i:mig[k + 1] if k + 1 < len(mig) else len(d)])
        if m:
            out[m.group(1).decode()] = i
    return out


def letters(img, thresh=40):
    a = img.split()[3]
    w, h = img.size
    cols = [any(a.getpixel((x, y)) > thresh for y in range(h)) for x in range(w)]
    out, x = [], 0
    while x < w:
        if cols[x]:
            s = x
            while x < w and cols[x]:
                x += 1
            out.append((s, x))
        else:
            x += 1
    return out


def main():
    pak, out, text = sys.argv[1:4]
    d = open(pak, 'rb').read()
    bn = banners(d)
    spec = {}
    for s in sys.argv[4:]:
        ch, src = s.split('=')
        name, rng = src.split(':')
        a, b = map(int, rng.split('-'))
        spec[ch] = (name, a, b)
    pieces = []
    for ch in text:
        if ch == ' ':
            pieces.append(None)
            continue
        name, x0, x1 = spec[ch]
        img = gim.decode(d, bn[name]).convert('RGBA')
        pieces.append(img.crop((max(0, x0 - PAD), 0, min(img.width, x1 + 1 + PAD), img.height)))
    gap = GAP                                           # crops overlap their outline/halo
    width = sum(p.width + gap if p else 5 for p in pieces) - gap
    ref = gim.decode(d, bn[spec[text[0]][0]])
    banner = Image.new('RGBA', ref.size, (0, 0, 0, 0))
    x = (ref.width - width) // 2
    for p in pieces:
        if p is None:
            x += 5
            continue
        banner.alpha_composite(p, (x, 0))
        x += p.width + gap
    banner.save(out)
    print('wrote %s (%dx%d, text width %d)' % (out, banner.width, banner.height, width))


if __name__ == '__main__':
    main()
