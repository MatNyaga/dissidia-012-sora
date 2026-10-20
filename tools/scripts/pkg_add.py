"""Add a NEW file to PACKAGE.BIN inside a Dissidia 012 ISO (ULUS10566), as a copy of an existing entry.

PACKAGE.BIN is packed tight and the ISO is full, so the new file is appended at the END of the ISO image.
PACKAGE.BIN's directory size is then stretched to reach it (ISO9660 files are just extent + size; the
movies that now sit "inside" PACKAGE.BIN's range don't matter, the game only reads what PACKAGE_INFO points
at). PACKAGE_INFO.BIN gets a new 12-byte entry, kept sorted by hash (binary-searched); the game loads it into
a fixed 0x20F8C-byte buffer (FUN_08871938), so about 210 entries fit. The volume size in the PVD is updated.

Usage: python3 -I pkg_add.py ISO NEW_PATH SRC_INDEX        (SRC_INDEX = index in the ORIGINAL PACKAGE_INFO)
       python3 -I pkg_add.py ISO --replace DST_INDEX SRC_INDEX  (overwrite DST's data with SRC's, sizes must match)
   e.g. python3 -I pkg_add.py X.iso obj/p_sev120.objx 3394
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comb_add import PACKAGE_INFO_ISO_SECTOR  # noqa: E402
from comb_patch import PACKAGE_ISO_SECTOR, SECTOR, read_at  # noqa: E402
from pkghash import pkg_hash  # noqa: E402

INFO_MAX = 0x20F8C
INFO_ROOM = (26080 - 26000) * 0x800   # PACKAGE_INFO.BIN's free sectors on disc (next file U_12JIYUU.AT3 at 26080; gap is zeros)


def dir_record(f, name):
    """Find the directory record of NAME (e.g. b'PACKAGE.BIN', stored without ';1' on this disc) in the first 400 sectors."""
    head = read_at(f, 0, 400 * SECTOR)
    i = head.find(name)
    if i < 33 or head[i - 1] != len(name):
        sys.exit('directory record for %s not found' % name)
    return i - 33


def set_both(f, at, value):
    f.seek(at)
    f.write(struct.pack('<I', value) + struct.pack('>I', value))


def replace(iso, dst, src):
    from comb_patch import pkg_offset
    (d_at, d_size), (s_at, s_size) = pkg_offset(dst), pkg_offset(src)
    if d_size != s_size:
        sys.exit('sizes differ (%d vs %d)' % (d_size, s_size))
    with open(iso, 'r+b') as f:
        data = read_at(f, s_at, s_size)
        f.seek(d_at)
        f.write(data)
    print('pkg %d <- data of pkg %d (%d bytes)' % (dst, src, s_size))


def main():
    if sys.argv[2] == '--replace':
        return replace(sys.argv[1], int(sys.argv[3]), int(sys.argv[4]))
    iso, new_path, src = sys.argv[1], sys.argv[2], int(sys.argv[3])
    h = pkg_hash(new_path)
    with open(iso, 'r+b') as f:
        info_rec, pkg_rec = dir_record(f, b'PACKAGE_INFO.BIN'), dir_record(f, b'PACKAGE.BIN')
        info_size, = struct.unpack('<I', read_at(f, info_rec + 10, 4))
        info = bytearray(read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, info_size))
        count, = struct.unpack_from('<I', info, 8)
        rows = [list(struct.unpack_from('<III', info, 16 + i * 12)) for i in range(count)]
        if any(r[0] == h for r in rows):
            sys.exit('%s (hash %08x) is already in PACKAGE_INFO' % (new_path, h))
        if 16 + (count + 1) * 12 > min(INFO_MAX, INFO_ROOM):
            sys.exit('no room for another PACKAGE_INFO entry')
        orig = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 '../../dumps/extracted/PACKAGE_INFO.BIN'), 'rb').read()
        want, = struct.unpack_from('<I', orig, 16 + src * 12)      # SRC = ORIGINAL index (positions shift)
        src_hash, src_sector, src_sf = next(r for r in rows if r[0] == want)
        data = read_at(f, PACKAGE_ISO_SECTOR * SECTOR + src_sector * SECTOR, src_sf & 0x0FFFFFFF)

        f.seek(0, 2)
        end = f.tell()
        start = -(-end // SECTOR) * SECTOR
        f.write(b'\0' * (start - end) + data + b'\0' * ((-len(data)) % SECTOR))
        new_end = f.tell()
        sector = (start - PACKAGE_ISO_SECTOR * SECTOR) // SECTOR

        # flag (top 4 bits) = Data Install tier; added files get 0 so the game's install keeps its vanilla file count
        # (P0.9: with tier 1 the 136 Sora files pushed install size 3 over its 4,050-file limit -> install ignored)
        rows.append([h, sector, len(data)])
        rows.sort()
        out = info[:16] + b''.join(struct.pack('<III', *r) for r in rows)
        struct.pack_into('<I', out, 8, count + 1)
        f.seek(PACKAGE_INFO_ISO_SECTOR * SECTOR)
        f.write(out)
        set_both(f, info_rec + 10, len(out))
        set_both(f, pkg_rec + 10, new_end - PACKAGE_ISO_SECTOR * SECTOR)
        set_both(f, 16 * SECTOR + 80, new_end // SECTOR)       # PVD volume space size
        print('%s: hash %08x, copy of pkg %d (%d bytes) at ISO 0x%x = package sector %d; index %d -> %d entries;'
              ' ISO %d -> %d bytes' % (new_path, h, src, len(data), start, sector, count, count + 1, end, new_end))
        print('NOTE: package indexes after the insert point shift by one (index = position in sorted PACKAGE_INFO).')


if __name__ == '__main__':
    main()
