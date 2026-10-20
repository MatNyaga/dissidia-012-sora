"""Decode PSP GIM images ("MIG.00.1PSP") to PNG, and pull every texture out of a GMO model.

GIM: 16-byte header, then blocks: u16 id, u16 0, u32 size, u32 next, u32 data offset.
  0x02 root, 0x03 picture (both contain child blocks at +0x10), 0x04 image, 0x05 palette, 0xFF info.
  Image/palette data (at block + data offset): u16 header size, u16 0, u16 format, u16 pixel order,
  u16 width, u16 height, u16 bpp, u16 pitch align, u16 height align, u16 ?, u32 ?, u32 index start,
  u32 pixels start, u32 pixels end, ...
  Formats: 0 RGBA5650, 1 RGBA5551, 2 RGBA4444, 3 RGBA8888, 4 INDEX4, 5 INDEX8.
  Pixel order 1 = PSP "faster" swizzle (16-byte x 8-row tiles).

Usage: python3 -I gim.py FILE.gim OUT.png
       python3 -I gim.py --gmo MODEL.gmo OUT_DIR     (writes <texture block name>.png for each texture)
"""
import os
import struct
import sys

from PIL import Image


def blocks(d, off, end, out):
    while off + 16 <= end:
        bid, _, size, nxt, dat = struct.unpack_from('<HHIII', d, off)
        if size < 16:
            break
        out.append((bid, off, size, dat))
        if bid in (0x02, 0x03):
            blocks(d, off + 0x10, off + size, out)
        off += size
    return out


def header(d, off):
    (hs, _, fmt, order, w, h, bpp, pitch, halign, _, _, idx_start, px_start, px_end) = \
        struct.unpack_from('<HHHHHHHHHHIIII', d, off)
    return {'fmt': fmt, 'order': order, 'w': w, 'h': h, 'bpp': bpp, 'pitch': pitch,
            'px': off + px_start, 'px_end': off + px_end}


def color(fmt, v):
    if fmt == 0:
        return ((v & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, ((v >> 11) & 31) * 255 // 31, 255)
    if fmt == 1:
        return ((v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, ((v >> 10) & 31) * 255 // 31, 255 if v >> 15 else 0)
    if fmt == 2:
        return tuple(((v >> s) & 15) * 17 for s in (0, 4, 8, 12))
    return (v & 255, (v >> 8) & 255, (v >> 16) & 255, v >> 24)


def unswizzle(data, width_bytes, height):
    out = bytearray(len(data))
    blocks_x = width_bytes // 16
    k = 0
    for by in range(0, height, 8):
        for bx in range(blocks_x):
            for y in range(8):
                row = by + y
                if row >= height:
                    k += 16
                    continue
                dst = row * width_bytes + bx * 16
                out[dst:dst + 16] = data[k:k + 16]
                k += 16
    return bytes(out)


def decode(d, base=0):
    """Decode the first image of a GIM that starts at d[base:]. Returns a PIL image."""
    if d[base:base + 11] != b'MIG.00.1PSP':
        raise ValueError('not a GIM')
    bl = blocks(d, base + 16, len(d), [])
    img = next(b for b in bl if b[0] == 0x04)
    pal = next((b for b in bl if b[0] == 0x05), None)
    h = header(d, img[1] + img[3])
    bits = {0: 16, 1: 16, 2: 16, 3: 32, 4: 4, 5: 8}[h['fmt']]
    pitch_px = h['w']
    align = max(h['pitch'], 16)
    width_bytes = -(-pitch_px * bits // 8 // align) * align
    height = -(-h['h'] // 8) * 8 if h['order'] == 1 else h['h']
    raw = d[h['px']:h['px'] + width_bytes * height]
    if h['order'] == 1:
        raw = unswizzle(raw, width_bytes, height)
    colors = None
    if h['fmt'] in (4, 5):
        p = header(d, pal[1] + pal[3])
        n = p['w']
        psize = 4 if p['fmt'] == 3 else 2
        colors = [color(p['fmt'], int.from_bytes(d[p['px'] + i * psize:p['px'] + (i + 1) * psize], 'little'))
                  for i in range(n)]
    out = Image.new('RGBA', (h['w'], h['h']))
    px = out.load()
    for y in range(h['h']):
        row = raw[y * width_bytes:(y + 1) * width_bytes]
        for x in range(h['w']):
            if h['fmt'] == 5:
                c = colors[row[x]]
            elif h['fmt'] == 4:
                b = row[x // 2]
                c = colors[(b >> 4) if x & 1 else (b & 15)]
            elif h['fmt'] == 3:
                c = color(3, int.from_bytes(row[x * 4:x * 4 + 4], 'little'))
            else:
                c = color(h['fmt'], int.from_bytes(row[x * 2:x * 2 + 2], 'little'))
            px[x, y] = c
    return out


def gmo_textures(path, out_dir):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gmo
    d = open(path, 'rb').read()
    items = []
    gmo.walk(d, 16, len(d), 0, items)
    os.makedirs(out_dir, exist_ok=True)
    for depth, o, t, hs, size, name in items:
        if t != 0x0A or name is None:
            continue
        i = d.find(b'MIG.00.1PSP', o, o + size)
        if i < 0:
            continue
        im = decode(d, i)
        im.save(os.path.join(out_dir, name + '.png'))
        print('%s.png %dx%d' % (name, im.width, im.height))


if __name__ == '__main__':
    if sys.argv[1] == '--gmo':
        gmo_textures(sys.argv[2], sys.argv[3])
    else:
        decode(open(sys.argv[1], 'rb').read()).save(sys.argv[2])
