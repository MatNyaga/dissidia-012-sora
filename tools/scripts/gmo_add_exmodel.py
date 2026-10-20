"""EXPERIMENT: add a second model block "model-0-0000" to a fighter GMO (like Terra's Trance model), as a copy of
model-0 whose paletted textures are turned silver-grey — to see whether the game draws it in EX Mode.

GMO block header: u16 type, u16 header size, u32 block size, u32 child offset (= header size), u32 same, name
(zero padded to the header size). Terra: model-0 header 0x18, model-0-0000 header 0x20.

  python3 -I gmo_add_exmodel.py IN.gmo OUT.gmo
"""
import re
import struct
import sys


def find_block(d, start, end, btype, name):
    o = start
    while o < end:
        t, hs, size = struct.unpack_from('<HHI', d, o)
        nm = d[o + 16:o + hs].split(b'\0')[0].decode('latin1')
        if t == btype and nm == name:
            return o, hs, size
        o += size
    raise KeyError(name)


def silver_palettes(blob):
    out = bytearray(blob)
    n = 0
    for m in re.finditer(rb'MIG\.00\.1PSP', bytes(blob)):
        g = m.start()
        ih = g + 0x40
        fmt, = struct.unpack_from('<H', out, ih + 4)
        if fmt not in (4, 5):
            continue
        nxt, = struct.unpack_from('<I', out, g + 0x30 + 8)
        ph = g + 0x30 + nxt + 0x10
        pfmt, _, pw = struct.unpack_from('<HHH', out, ph + 4)
        if pfmt != 3:
            continue
        pal = ph + struct.unpack_from('<I', out, ph + 0x1C)[0]
        for k in range(pw):
            r, gg, b, a = out[pal + 4 * k:pal + 4 * k + 4]
            y = int(0.3 * r + 0.59 * gg + 0.11 * b)
            out[pal + 4 * k:pal + 4 * k + 3] = bytes((min(255, y + 30), min(255, y + 34), min(255, y + 44)))
        n += 1
    return bytes(out), n


def main():
    src, dst = sys.argv[1:3]
    d = bytearray(open(src, 'rb').read())
    fo = 0x10
    ft, fhs, fsize = struct.unpack_from('<HHI', d, fo)
    mo, mhs, msize = find_block(d, fo + fhs, fo + fsize, 3, 'model-0')
    body, n = silver_palettes(d[mo + mhs:mo + msize])
    hdr = struct.pack('<HHIII', 3, 0x20, 0x20 + len(body), 0x20, 0x20) + b'model-0-0000'.ljust(16, b'\0')
    new = hdr + body
    at = mo + msize
    d[at:at] = new
    struct.pack_into('<I', d, fo + 4, fsize + len(new))
    open(dst, 'wb').write(bytes(d))
    print('model-0-0000 added (%d bytes, %d palettes silvered) -> %s' % (len(new), n, dst))


if __name__ == '__main__':
    main()
