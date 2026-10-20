"""Read or patch a character's `comb` action table directly inside a Dissidia 012 ISO.

Character files are PACKAGE.BIN entries (by index) holding an ARC with a `comb` chunk.
comb: u16 version, u16 count, u32 offsets[count]; entry = u16 id, u16 n, i16 alt, i16 parent,
      then n x 8-byte steps: u32 piece id, u16 0xFFFF, u8 flag, u8 0.
See notes/character-file.md.

Usage:
  python3 -I comb_patch.py ISO list PKG_INDEX
  python3 -I comb_patch.py ISO set-pieces PKG_INDEX ACTION_ID PIECE   (every step of ACTION_ID -> PIECE; writes!)
"""
import os
import struct
import sys

SECTOR = 0x800
PACKAGE_ISO_SECTOR = 186624        # ULUS10566 only
HERE = os.path.dirname(os.path.abspath(__file__))


def pkg_offset(index):
    """INDEX = original package index (int), or a path like 'obj/p_sev120.objx' (looked up by hash in the
    ISO set with use_iso(); needed for files added by pkg_add.py)."""
    if isinstance(index, str) and not index.isdigit():
        return pkg_offset_by_path(index)
    info = open(os.path.join(HERE, '../../dumps/extracted/PACKAGE_INFO.BIN'), 'rb').read()
    _, sector, sf = struct.unpack_from('<III', info, 16 + int(index) * 12)
    return PACKAGE_ISO_SECTOR * SECTOR + sector * SECTOR, sf & 0x0FFFFFFF


_ISO = []


def use_iso(path):
    _ISO[:] = [path]


def pkg_offset_by_path(path):
    from pkghash import pkg_hash
    want = pkg_hash(path)
    with open(_ISO[0], 'rb') as f:
        base = 26000 * SECTOR                       # PACKAGE_INFO.BIN sector in the ISO
        count, = struct.unpack('<I', read_at(f, base + 8, 4))
        rows = read_at(f, base + 16, count * 12)
    for i in range(count):
        h, sector, sf = struct.unpack_from('<III', rows, i * 12)
        if h == want:
            return PACKAGE_ISO_SECTOR * SECTOR + sector * SECTOR, sf & 0x0FFFFFFF
    sys.exit('%s not in the ISO PACKAGE_INFO' % path)


def read_at(f, off, n):
    f.seek(off)
    return f.read(n)


def comb_base(f, index):
    base, _ = pkg_offset(index)
    head = read_at(f, base, 16)
    if head[:4] != b'ARC\x01':
        sys.exit('package entry %d is not an ARC' % index)
    count, = struct.unpack_from('<I', head, 4)
    for i in range(count):
        _, tag, off, size = struct.unpack_from('<I4sII', read_at(f, base + 16 + i * 16, 16))
        if tag == b'comb':
            return base + off, size
    sys.exit('no comb chunk in entry %d' % index)


def entries(f, comb, size):
    _, count = struct.unpack('<HH', read_at(f, comb, 4))
    offs = struct.unpack('<%dI' % count, read_at(f, comb + 4, count * 4))
    for o in offs:
        aid, n, alt, parent = struct.unpack('<HHhh', read_at(f, comb + o, 8))
        steps = [struct.unpack('<IHBB', read_at(f, comb + o + 8 + k * 8, 8)) for k in range(n)]
        yield comb + o, aid, alt, parent, steps


def main():
    iso, cmd, index = sys.argv[1], sys.argv[2], int(sys.argv[3])
    with open(iso, 'rb' if cmd == 'list' else 'r+b') as f:
        comb, size = comb_base(f, index)
        print('comb at ISO offset 0x%x (%d bytes)' % (comb, size))
        if cmd == 'list':
            for at, aid, alt, parent, steps in entries(f, comb, size):
                print('action %4d alt %4d parent %4d  pieces %s' % (
                    aid, alt, parent, ' '.join('0x%x/%d' % (p, fl) for p, _, fl, _ in steps)))
        elif cmd == 'set-pieces':
            want, piece = int(sys.argv[4]), int(sys.argv[5], 0)
            for at, aid, alt, parent, steps in entries(f, comb, size):
                if aid == want:
                    for k in range(len(steps)):
                        f.seek(at + 8 + k * 8)
                        f.write(struct.pack('<I', piece))
                    print('action %d: %d steps -> piece 0x%x' % (aid, len(steps), piece))


if __name__ == '__main__':
    main()
