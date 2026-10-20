"""Move (ability) names shown in battle banners and menus: ability.bin inside package file
general_archive/... (pkg 7683, an MPK: common.bin, pause_menu.bin, ability.bin, accessory.bin, item.bin, ...).

ability.bin: u16 offset[count] (in 2-byte units from the file start; count = offset[0]), entries at offset*2:
u16 byte length (UTF-16LE text + NUL), then the text XOR-scrambled like the subtitles:
byte j of entry L ^= KEY[(2*L + 18 + j) % 32] (KEY from voice_text.py; subtitles use +20).

Usage:
  python3 -I ability_text.py dump ABILITY.bin                     id<TAB>text
  python3 -I ability_text.py set ABILITY.bin OUT.bin ID=TEXT ...   change texts (patched in place or appended)
  python3 -I ability_text.py add ABILITY.bin OUT.bin TEXT ...      append new texts, prints their GAME text ids
Game text id (ablt +2 name, +4 description) = entry index - 1 (entry 0 is not a string).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from voice_text import KEY  # noqa: E402


def decode(b):
    count = struct.unpack_from('<H', b, 0)[0]
    offs = struct.unpack_from('<%dH' % count, b, 0)
    out = []
    for lid, o in enumerate(offs):
        p = o * 2
        ln = struct.unpack_from('<H', b, p)[0]
        raw = bytes(c ^ KEY[(2 * lid + 18 + j) % 32] for j, c in enumerate(b[p + 2:p + 2 + ln]))
        out.append(raw.decode('utf-16-le', 'surrogatepass'))      # exact, incl. the trailing NUL
    return out


def encode(texts):
    count = len(texts)
    head = bytearray(count * 2)
    body = bytearray()
    for lid, t in enumerate(texts):
        raw = t.encode('utf-16-le', 'surrogatepass')
        pos = len(head) + len(body)
        if pos % 2:
            body.append(0)
            pos += 1
        struct.pack_into('<H', head, lid * 2, pos // 2)
        body += struct.pack('<H', len(raw)) + bytes(c ^ KEY[(2 * lid + 18 + j) % 32] for j, c in enumerate(raw))
    return bytes(head + body)


def set_texts(b, changes):
    """patch entries in place (new text <= old byte length) or append them at the end; everything else untouched"""
    b = bytearray(b)
    for lid, text in changes.items():
        raw = (text + '\0').encode('utf-16-le', 'surrogatepass')
        enc = bytes(c ^ KEY[(2 * lid + 18 + j) % 32] for j, c in enumerate(raw))
        o = struct.unpack_from('<H', b, lid * 2)[0] * 2
        old = struct.unpack_from('<H', b, o)[0]
        if len(raw) <= old:
            b[o:o + 2 + len(raw)] = struct.pack('<H', len(raw)) + enc
        else:
            if len(b) % 2:
                b.append(0)
            if len(b) // 2 > 0xFFFF:
                raise SystemExit('ability.bin too big for 16-bit offsets')
            struct.pack_into('<H', b, lid * 2, len(b) // 2)
            b += struct.pack('<H', len(raw)) + enc
    return bytes(b)


def add_texts(b, new):
    """append entries; returns (data, first new GAME text id). Game text id = entry index - 1."""
    count = struct.unpack_from('<H', b, 0)[0]
    offs = list(struct.unpack_from('<%dH' % count, b, 0))
    k = len(new)
    head = bytearray(2 * (count + k))
    body = bytearray(b[2 * count:])
    for i, o in enumerate(offs):
        struct.pack_into('<H', head, 2 * i, o + k)
    for n, text in enumerate(new):
        lid = count + n
        if (len(head) + len(body)) % 2:
            body.append(0)
        struct.pack_into('<H', head, 2 * lid, (len(head) + len(body)) // 2)
        raw = (text + '\0').encode('utf-16-le', 'surrogatepass')
        body += struct.pack('<H', len(raw)) + bytes(c ^ KEY[(2 * lid + 18 + j) % 32] for j, c in enumerate(raw))
    return bytes(head + body), count - 1


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    data = open(path, 'rb').read()
    texts = decode(data)
    if cmd == 'dump':
        for i, t in enumerate(texts[1:], 1):          # entry 0 is not a string (its length overlaps the file)
            print('%d\t%s' % (i, t.rstrip('\0').replace('\n', '\\n')))
    elif cmd == 'add':
        out, first = add_texts(data, sys.argv[4:])
        open(sys.argv[3], 'wb').write(out)
        print('added %d texts: game text ids %d..%d' % (len(sys.argv[4:]), first, first + len(sys.argv[4:]) - 1))
    elif cmd == 'set':
        changes = {}
        for a in sys.argv[4:]:
            i, _, t = a.partition('=')
            changes[int(i)] = t
        open(sys.argv[3], 'wb').write(set_texts(data, changes))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
