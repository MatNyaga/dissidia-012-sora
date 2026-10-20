"""In-battle move-name banners for #33 (Sora): the `text` chunk ("mlng") of obj/p_sev120.objx.

Format (cracked 2026-10-13 by comparing the disc chunk with its decoded copy in RAM):
  "mlng", u32 n (6 languages), u32 offset[n], u32 size[n], blocks. The US game uses block 0 (English).
  Block: u16 offset[count] (2-byte units, count = offset[0]); entry 0 = u16 end of the data (2-byte units; the game
  needs it), entries 1.. = u16 byte length,
  then the bytes XOR KEY[(2*L + 18 + j) % 32] (L = entry index, KEY = subtitle key; same as ability.bin).
  Decoded entry: 1c 00, then font codes as LEB128 (code >= 0x80 -> 2 bytes), 00 end, padded to an even length.
  Font codes: space 0x20, '0'-'9' = ASCII + 0x26, 'A'-'Z' = ASCII + 0x1F, 'a'-'z' = ASCII + 0x19, '-' 0x159,
  '!' 0x12D, 0x1E 00 01 2F = the Circle button icon (kept as raw bytes).
Cloud's (English): 1 Omnislash (EX Burst banner), 2 LIMIT BREAK, 3 Rapidly tap (o)!, 4 Cross-Slash (ground HP),
  5 Meteorain, 6 Finishing Touch, 7 Braver (air HP), 8 Omnislash Version 5, 9 Equipped Ultima Weapon!,
  10 The power of mako! (EX Mode).

Usage: python3 -I spot33_battlenames.py ISO [dump]      (without "dump": writes NAMES below into the ISO)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from voice_text import KEY  # noqa: E402

FILE = 'obj/p_sev120.objx'
# banner = text entry (plya +0x21 of the attack piece) + 1 (notes/hitbox-shapes.md §8): 5 Guard Break (0x5c9),
# 6 Upper Slash (LF3 0x5ce; was Spin Finish until 2026-10-14), 8 Aerial Flurry (AF3 0x5cf), 11 Magnet Burst (0xb32 +0x21 = 10, NEW entry)
NAMES = {1: 'TRINITY LIMIT', 2: 'TRINITY LIMIT', 4: 'Explosion', 5: 'Guard Break', 6: 'Upper Slash', 7: 'Aerial Finish', 8: 'Retaliating Slash',
         9: 'My friends are my power!', 10: 'My friends are my power!', 11: 'Magnet Burst', 12: 'Horizontal Slash', 13: 'Aerial Sweep',
         14: 'Firaga', 15: 'Thundaga', 16: 'Blizzaga'}
PUNCT = {' ': 0x20, '-': 0x159, '!': 0x12D}


def code(ch):
    if ch in PUNCT:
        return PUNCT[ch]
    if ch.isdigit():
        return ord(ch) + 0x26
    if 'A' <= ch <= 'Z':
        return ord(ch) + 0x1F
    if 'a' <= ch <= 'z':
        return ord(ch) + 0x19
    sys.exit('no font code known for %r' % ch)


def char(v):
    for k, c in PUNCT.items():
        if v == c:
            return k
    for lo, hi, d in ((0x56, 0x60, 0x26), (0x60, 0x7A, 0x1F), (0x7A, 0x94, 0x19)):
        if lo <= v < hi:
            return chr(v - d)
    return '{%x}' % v


def xor(raw, lid):
    return bytes(x ^ KEY[(2 * lid + 18 + j) % 32] for j, x in enumerate(raw))


def parse_block(b):
    count, = struct.unpack_from('<H', b, 0)
    offs = struct.unpack_from('<%dH' % count, b, 0)
    raws = [None]
    for lid in range(1, count):
        p = offs[lid] * 2
        ln, = struct.unpack_from('<H', b, p)
        raws.append(xor(b[p + 2:p + 2 + ln], lid))
    return raws


def text_of(raw):
    out, k = [], 2
    while k < len(raw):
        v = raw[k]
        k += 1
        if v & 0x80:
            v = (v & 0x7F) | (raw[k] << 7)
            k += 1
        if v == 0:
            break
        if v == 0x1E:                                    # button icon: 1e 00 01 2f
            out.append('(o)')
            k += 3
            continue
        out.append(char(v))
    return ''.join(out)


def encode(text):
    raw = bytearray(b'\x1c\x00')
    for ch in text:
        v = code(ch)
        raw += bytes([v]) if v < 0x80 else bytes([0x80 | (v & 0x7F), v >> 7])
    raw += b'\0'
    if len(raw) % 2:
        raw += b'\0'
    return bytes(raw)


def build_block(raws):
    """offset table (offset[0] = count = position of entry 0), entry 0 = u16 end of the data (2-byte units), then
    the entries (u16 length + scrambled bytes)"""
    count = len(raws)
    head = 2 * count + 2
    body = bytearray()
    offs = [count]
    for lid in range(1, count):
        offs.append((head + len(body)) // 2)
        body += struct.pack('<H', len(raws[lid])) + xor(raws[lid], lid)
    end = (head + len(body)) // 2
    return struct.pack('<%dH' % count, *offs) + struct.pack('<H', end) + bytes(body)

def main():
    iso = sys.argv[1]
    dump = len(sys.argv) > 2 and sys.argv[2] == 'dump'
    use_iso(iso)
    start, size = pkg_offset(FILE)                       # p_sev120.objx was appended at the end of the ISO
    with open(iso, 'rb' if dump else 'r+b') as f:
        data = read_at(f, start, size)
        assert data[:4] == b'ARC\x01', data[:4]
        count, = struct.unpack_from('<I', data, 4)
        chunks = [struct.unpack_from('<I4sII', data, 16 + k * 16) for k in range(count)]
        _, _, coff, csize = next(ch for ch in chunks if ch[1] == b'text')
        c = data[coff:coff + csize]
        assert c[:4] == b'mlng', c[:4]
        n, = struct.unpack_from('<I', c, 4)
        offs = list(struct.unpack_from('<%dI' % n, c, 8))
        sizes = list(struct.unpack_from('<%dI' % n, c, 8 + 4 * n))
        blocks = [bytes(c[o:o + s]) for o, s in zip(offs, sizes)]
        raws = parse_block(blocks[0])
        for lid in range(1, len(raws)):
            print(lid, text_of(raws[lid]))
        if dump:
            return
        for lid, t in NAMES.items():
            while len(raws) <= lid:                       # new entries (the chunk has ~40 B of padding)
                raws.append(encode(''))
            raws[lid] = encode(t)
            assert text_of(raws[lid]) == t
        blocks[0] = build_block(raws)
        pos = 8 + 8 * n
        out = bytearray(c[:pos])
        for k, b in enumerate(blocks):
            struct.pack_into('<I', out, 8 + 4 * k, len(out))
            struct.pack_into('<I', out, 8 + 4 * n + 4 * k, len(b))
            out += b
        if len(out) > csize:                              # grows: rebuild the ARC, put the file back (pkg_put)
            import subprocess
            import tempfile
            from spot33_combos import rebuild_arc
            ti = next(k for k, ch in enumerate(chunks) if ch[1] == b'text')
            new = rebuild_arc(data, {ti: bytes(out) + b'\0' * ((-len(out)) % 16)})
            with tempfile.TemporaryDirectory() as t:
                p = os.path.join(t, 'f.objx')
                open(p, 'wb').write(new)
                f.close()
                r = subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'pkg_put.py'), iso, FILE, p], check=True, capture_output=True, text=True)
                print(r.stdout.strip())
        else:
            out += b'\0' * (csize - len(out))
            f.seek(start + coff)
            f.write(out)
        print('battle names written (%d of %d bytes):' % (pos + sum(map(len, blocks)), csize),
              ', '.join('%d %s' % kv for kv in NAMES.items()))

if __name__ == '__main__':
    main()
