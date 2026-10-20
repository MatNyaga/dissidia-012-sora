"""Write a PNG over an index8 GIM (format 5, linear, RGBA8888 palette of 256) of the SAME size, in place.

  python3 -I gim_put.py CONTAINER.bin GIM_NAME IN.png OUT.bin     (GIM found by its "NAME.tm2" tag, e.g. p_sev120_name)

Layout (GIM block headers 16 bytes): image block at +0x30 -> image header +0x40 (u16 hdr 0x30, format 5, order 0,
width, height, bpp 8 ...; pixel start at hdr+0x1C) ; palette block follows (format 3 = RGBA8888, 256 x 1).
The container keeps its size (pack offsets stay valid).
"""
import os
import struct
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from name_banner import banners  # noqa: E402


def to_index8(img):
    """-> (index bytes, 1024-byte RGBA palette); exact if <= 256 colours, else nearest of the 256 most common"""
    a = np.asarray(img, dtype=np.uint8).reshape(-1, 4)
    cols, inv, cnt = np.unique(a, axis=0, return_inverse=True, return_counts=True)
    if len(cols) > 256:
        keep = cols[np.argsort(-cnt)[:256]].astype(np.int32)
        d = ((a[:, None, :].astype(np.int32) - keep[None, :, :]) ** 2).sum(2)
        inv = d.argmin(1)
        cols = keep.astype(np.uint8)
    pal = np.zeros((256, 4), np.uint8)
    pal[:len(cols)] = cols
    return inv.astype(np.uint8).tobytes(), pal.tobytes()


def put(gim, img):
    ih = 0x40
    hdr, _, fmt, order, w, h = struct.unpack_from('<HHHHHH', gim, ih)
    assert fmt == 5 and order == 0, 'only linear index8 GIMs'
    assert img.size == (w, h), 'PNG must be %dx%d' % (w, h)
    pix = ih + struct.unpack_from('<I', gim, ih + 0x1C)[0]
    nxt = struct.unpack_from('<I', gim, 0x30 + 8)[0]
    pb = 0x30 + nxt
    ph = pb + 0x10
    pfmt, _, pw = struct.unpack_from('<HHH', gim, ph + 4)
    assert pfmt == 3 and pw == 256, 'palette must be RGBA8888 x 256'
    pal_at = ph + struct.unpack_from('<I', gim, ph + 0x1C)[0]
    idx, pal = to_index8(img.convert('RGBA'))
    out = bytearray(gim)
    out[pix:pix + w * h] = idx
    out[pal_at:pal_at + 1024] = pal
    return bytes(out)


def main():
    cont, name, png, outp = sys.argv[1:5]
    d = bytearray(open(cont, 'rb').read())
    at = banners(bytes(d))[name]
    size = struct.unpack_from('<I', d, at + 0x10 + 4)[0] + 0x10      # root block size + file header
    new = put(bytes(d[at:at + size]), Image.open(png))
    d[at:at + size] = new
    open(outp, 'wb').write(bytes(d))
    print('%s: %s replaced in place (%d bytes)' % (outp, name, size))


if __name__ == '__main__':
    main()
