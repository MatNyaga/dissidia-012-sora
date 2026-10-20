"""Unpack Dissidia 012 PACKAGE.BIN using PACKAGE_INFO.BIN.

PACKAGE_INFO.BIN layout (worked out 2026-10-11, see notes/package-format.md):
  0x00 u32  version/date 0x20090218
  0x04 char "pack"
  0x08 u32  entry count
  0x0C u32  0
  0x10 entries, 12 bytes each, sorted by hash:
       u32 hash        name hash (algorithm unknown yet)
       u32 sector      offset in PACKAGE.BIN, in 0x800-byte sectors
       u32 size_flags  low 28 bits = size in bytes, top 4 bits = type flag (0-3)

Usage: python3 -I unpack_package.py PACKAGE_INFO.BIN PACKAGE.BIN OUT_DIR
Writes OUT_DIR/<index>_<hash>_t<flag>.<ext> and OUT_DIR/index.tsv.
"""
import os
import struct
import sys
from collections import Counter

SECTOR = 0x800


def read_index(path):
    data = open(path, 'rb').read()
    if data[4:8] != b'pack':
        sys.exit('not a pack index: %s' % path)
    count, = struct.unpack_from('<I', data, 8)
    entries = []
    for i in range(count):
        h, sector, sf = struct.unpack_from('<III', data, 16 + i * 12)
        entries.append((i, h, sector * SECTOR, sf & 0x0FFFFFFF, sf >> 28))
    return entries


def guess_ext(head):
    magic = head[:4]
    if magic == b'\x7fELF':
        return 'elf'
    if magic == b'OMG.':
        return 'gmo'
    if magic == b'MIG.':
        return 'gim'
    if magic == b'RIFF':
        return 'at3'
    if magic == b'PSMF':
        return 'pmf'
    if magic == b'VAGp':
        return 'vag'
    if magic.isalnum() and len(magic) == 4:
        return magic.decode('ascii').lower()
    return 'bin'


def main():
    info, pkg, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    entries = read_index(info)
    exts = Counter()
    with open(pkg, 'rb') as f, open(os.path.join(out, 'index.tsv'), 'w') as idx:
        idx.write('index\thash\toffset\tsize\tflag\text\tfirst16\n')
        for i, h, off, size, flag in entries:
            f.seek(off)
            blob = f.read(size)
            ext = guess_ext(blob[:16])
            exts[(ext, flag)] += 1
            name = '%05d_%08x_t%d.%s' % (i, h, flag, ext)
            with open(os.path.join(out, name), 'wb') as o:
                o.write(blob)
            idx.write('%d\t%08x\t%08x\t%d\t%d\t%s\t%s\n' % (i, h, off, size, flag, ext, blob[:16].hex()))
    for (ext, flag), n in exts.most_common():
        print('%-6s flag %d: %d' % (ext, flag, n))


if __name__ == '__main__':
    main()
