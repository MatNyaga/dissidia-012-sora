"""Add a brand-new action to a character's `comb` table, directly inside a Dissidia 012 ISO.

The character file (a PACKAGE.BIN entry, ARC container) is rebuilt with a bigger `comb` chunk.
Every chunk after `comb` moves down by GROW bytes (a multiple of 16, so 16-byte aligned textures
stay aligned). The file is written back in place, so it must fit in the padding before the next
file. PACKAGE_INFO.BIN in the ISO gets the new size.

Usage: python3 -I comb_add.py ISO PKG_INDEX NEW_ID PIECE [PIECE ...]
       pieces in hex or decimal, e.g. 0x5be 0x5bf 0x5c4
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comb_patch import PACKAGE_ISO_SECTOR, SECTOR, pkg_offset, read_at  # noqa: E402

PACKAGE_INFO_ISO_SECTOR = 26000    # from `isoinfo -l`, ULUS10566 only
HERE = os.path.dirname(os.path.abspath(__file__))


def free_room(index):
    info = open(os.path.join(HERE, '../../dumps/extracted/PACKAGE_INFO.BIN'), 'rb').read()
    count, = struct.unpack_from('<I', info, 8)
    starts = sorted(struct.unpack_from('<III', info, 16 + i * 12)[1] * SECTOR for i in range(count))
    start, size = pkg_offset(index)
    start -= PACKAGE_ISO_SECTOR * SECTOR
    nxt = next(s for s in starts if s > start)
    return nxt - start - size


def iso_size_field(f, index):
    """ISO offset of the size field for ORIGINAL package entry INDEX, found by hash: entries added with
    pkg_add.py shift positions in the ISO's PACKAGE_INFO, so position = index is not safe."""
    info = open(os.path.join(HERE, '../../dumps/extracted/PACKAGE_INFO.BIN'), 'rb').read()
    want, = struct.unpack_from('<I', info, 16 + index * 12)
    base = PACKAGE_INFO_ISO_SECTOR * SECTOR
    count, = struct.unpack('<I', read_at(f, base + 8, 4))
    rows = read_at(f, base + 16, count * 12)
    for i in range(count):
        if struct.unpack_from('<I', rows, i * 12)[0] == want:
            return base + 16 + i * 12 + 8
    sys.exit('hash %08x not in the ISO PACKAGE_INFO' % want)


def build_entry(new_id, pieces):
    out = struct.pack('<HHhh', new_id, len(pieces), -1, -1)
    for p in pieces:
        out += struct.pack('<IHBB', p, 0xFFFF, 0, 0)
    return out


def main():
    iso, index, new_id = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    pieces = [int(p, 0) for p in sys.argv[4:]]
    base, size = pkg_offset(index)
    with open(iso, 'r+b') as f:
        data = bytearray(read_at(f, base, size))
        if data[:4] != b'ARC\x01':
            sys.exit('not an ARC')
        count, = struct.unpack_from('<I', data, 4)
        chunks = [list(struct.unpack_from('<I4sII', data, 16 + i * 16)) for i in range(count)]
        ci = next(i for i, c in enumerate(chunks) if c[1] == b'comb')
        _, _, coff, csize = chunks[ci]
        comb = data[coff:coff + csize]
        ver, n = struct.unpack_from('<HH', comb, 0)
        offs = list(struct.unpack_from('<%dI' % n, comb, 4))
        if any(struct.unpack_from('<H', comb, o)[0] == new_id for o in offs):
            sys.exit('action %d already exists' % new_id)
        body = comb[4 + n * 4:]
        entry = build_entry(new_id, pieces)
        new_offs = [o + 4 for o in offs] + [4 + (n + 1) * 4 + len(body)]
        new_comb = struct.pack('<HH', ver, n + 1) + struct.pack('<%dI' % (n + 1), *new_offs) + body + entry
        grow = (len(new_comb) - csize + 15) // 16 * 16
        new_comb += b'\0' * (grow - (len(new_comb) - csize))
        room = free_room(index)
        if grow > room:
            sys.exit('need %d bytes, only %d free after this file' % (grow, room))
        chunks[ci][3] = csize + 4 + len(entry)      # real comb size, padding not counted
        for c in chunks:
            if c[2] > coff:
                c[2] += grow
        out = bytearray(data[:coff]) + new_comb + data[coff + csize:]
        for i, c in enumerate(chunks):
            struct.pack_into('<I4sII', out, 16 + i * 16, *c)
        f.seek(base)
        f.write(out)
        # new size into PACKAGE_INFO.BIN inside the ISO
        info_at = iso_size_field(f, index)
        sf, = struct.unpack('<I', read_at(f, info_at, 4))
        f.seek(info_at)
        f.write(struct.pack('<I', (sf & 0xF0000000) | len(out)))
        print('pkg %d: comb %d -> %d entries, file %d -> %d bytes (+%d, %d free before)' % (
            index, n, n + 1, size, len(out), grow, room))


if __name__ == '__main__':
    main()
