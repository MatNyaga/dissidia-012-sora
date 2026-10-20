"""Read or patch the ability table (system.bin/ablt) directly inside a Dissidia 012 ISO.

Path to the table: ISO -> PACKAGE.BIN -> general_archive/main/main.bin (MPK)
                   -> system.bin (ARC) -> ablt chunk.
ablt: 16-byte header ("ABI ", date, u32 count, 0) then 40-byte rows.
Row fields we know (2026-10-11):
  +0  u8  index within owner     +1  u8  owner (character number, 0x40 = general skills)
  +2  u16 name text id           +4  u16 description text id
  +12 u16 action id (the move; 0xFFFF for passive skills)
  +22 u8  attack type: 0 = Bravery, 1 = HP
  +23 u8  usable: 0 = ground, 1 = air, 0xFF = both

Sizes never change, so patches are written in place.

Usage:
  python3 -I ablt_patch.py ISO list [OWNER]
  python3 -I ablt_patch.py ISO swap-action ROW_A ROW_B     (writes to ISO!)
  python3 -I ablt_patch.py ISO set-action ROW ACTION       (writes to ISO!)
  python3 -I ablt_patch.py ISO copy-row SRC DST OWNER IDX   (writes! DST = copy of SRC; +0 idx, +1 and +27 owner)
        Keep the table sorted by (owner, idx): it is binary-searched.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pkghash import pkg_hash  # noqa: E402

SECTOR = 0x800
PACKAGE_ISO_SECTOR = 186624        # from `isoinfo -l`, ULUS10566 only
PACKAGE_INFO_ISO_PATH = '/PSP_GAME/USRDIR/DATA/PACKAGE_INFO.BIN'
ROW = 40


def read_at(f, off, n):
    f.seek(off)
    return f.read(n)


def package_entry(info, name):
    want = pkg_hash(name)
    count, = struct.unpack_from('<I', info, 8)
    for i in range(count):
        h, sector, sf = struct.unpack_from('<III', info, 16 + i * 12)
        if h == want:
            return sector * SECTOR, sf & 0x0FFFFFFF
    raise KeyError(name)


def mpk_member(f, base, name):
    count, = struct.unpack_from('<I', read_at(f, base, 16), 8)
    for i in range(count):
        noff, doff, size, _ = struct.unpack_from('<IIII', read_at(f, base + 16 + i * 16, 16))
        member = read_at(f, base + noff, 64).split(b'\0')[0].decode()
        if member == name:
            return base + doff, size
    raise KeyError(name)


def arc_chunk(f, base, tag):
    count, = struct.unpack_from('<I', read_at(f, base, 16), 4)
    for i in range(count):
        _, t, off, size = struct.unpack_from('<I4sII', read_at(f, base + 16 + i * 16, 16))
        if t == tag.encode():
            return base + off, size
    raise KeyError(tag)


def locate_ablt(f, info):
    pkg = PACKAGE_ISO_SECTOR * SECTOR
    off, _ = package_entry(info, 'general_archive/main/main.bin')
    sysbin, _ = mpk_member(f, pkg + off, 'system.bin')
    ablt, size = arc_chunk(f, sysbin, 'ablt')
    head = read_at(f, ablt, 16)
    if head[:4] != b'ABI ':
        sys.exit('ablt header not found — wrong ISO or region?')
    return ablt, struct.unpack_from('<I', head, 8)[0]


def main():
    iso, cmd = sys.argv[1], sys.argv[2]
    info = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             '../../dumps/extracted/PACKAGE_INFO.BIN'), 'rb').read()
    with open(iso, 'rb' if cmd == 'list' else 'r+b') as f:
        ablt, count = locate_ablt(f, info)
        print('ablt at ISO offset 0x%x, %d rows' % (ablt, count))
        rows = lambda i: ablt + 16 + i * ROW  # noqa: E731
        if cmd == 'list':
            owner = int(sys.argv[3], 0) if len(sys.argv) > 3 else None
            for i in range(count):
                r = read_at(f, rows(i), ROW)
                if owner is None or r[1] == owner:
                    act, = struct.unpack_from('<H', r, 12)
                    print('row %3d  owner %2d  idx %2d  action %5d  %s' % (i, r[1], r[0], act, r.hex(' ')))
        elif cmd == 'swap-action':
            a, b = int(sys.argv[3]), int(sys.argv[4])
            act_a = read_at(f, rows(a) + 12, 2)
            act_b = read_at(f, rows(b) + 12, 2)
            f.seek(rows(a) + 12); f.write(act_b)
            f.seek(rows(b) + 12); f.write(act_a)
            print('row %d action %d -> %d' % (a, struct.unpack('<H', act_a)[0], struct.unpack('<H', act_b)[0]))
            print('row %d action %d -> %d' % (b, struct.unpack('<H', act_b)[0], struct.unpack('<H', act_a)[0]))
        elif cmd == 'copy-row':
            src, dst, owner, idx = (int(x, 0) for x in sys.argv[3:7])
            r = bytearray(read_at(f, rows(src), ROW))
            r[0], r[1], r[27] = idx, owner, owner
            f.seek(rows(dst)); f.write(r)
            print('row %d <- copy of row %d (action %d) as owner %d idx %d' % (
                dst, src, struct.unpack_from('<H', r, 12)[0], owner, idx))
        elif cmd == 'set-action':
            row, act = int(sys.argv[3]), int(sys.argv[4])
            old, = struct.unpack('<H', read_at(f, rows(row) + 12, 2))
            f.seek(rows(row) + 12); f.write(struct.pack('<H', act))
            print('row %d action %d -> %d' % (row, old, act))


if __name__ == '__main__':
    main()
