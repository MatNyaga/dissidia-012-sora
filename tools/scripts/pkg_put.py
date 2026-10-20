"""Put a local FILE into the ISO's PACKAGE.BIN under PATH (e.g. obj/P_SEV120_1P.gmo).

- PATH already in the ISO's PACKAGE_INFO and FILE fits in its old sectors → written in place.
- Otherwise FILE is appended at the end of the ISO (like pkg_add.py) and the entry is pointed at it
  (or a new entry is added, kept sorted by hash). PACKAGE.BIN's directory size and the PVD are updated.

Usage: python3 -I pkg_put.py ISO PATH FILE
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comb_add import PACKAGE_INFO_ISO_SECTOR  # noqa: E402
from comb_patch import PACKAGE_ISO_SECTOR, SECTOR, read_at  # noqa: E402
from pkg_add import INFO_MAX, INFO_ROOM, dir_record, set_both  # noqa: E402
from pkghash import pkg_hash  # noqa: E402


def main():
    iso, path, src = sys.argv[1], sys.argv[2], sys.argv[3]
    data = open(src, 'rb').read()
    h = pkg_hash(path)
    with open(iso, 'r+b') as f:
        info_rec, pkg_rec = dir_record(f, b'PACKAGE_INFO.BIN'), dir_record(f, b'PACKAGE.BIN')
        info_size, = struct.unpack('<I', read_at(f, info_rec + 10, 4))
        info = bytearray(read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, info_size))
        count, = struct.unpack_from('<I', info, 8)
        rows = [list(struct.unpack_from('<III', info, 16 + i * 12)) for i in range(count)]
        row = next((r for r in rows if r[0] == h), None)
        pkg = PACKAGE_ISO_SECTOR * SECTOR
        if row and len(data) <= -(-(row[2] & 0x0FFFFFFF) // SECTOR) * SECTOR:
            f.seek(pkg + row[1] * SECTOR)
            f.write(data + b'\0' * (-(-(row[2] & 0x0FFFFFFF) // SECTOR) * SECTOR - len(data)))
            row[2] = (row[2] & 0xF0000000) | len(data)
            how = 'in place at package sector %d' % row[1]
        else:
            f.seek(0, 2)
            end = f.tell()
            start = -(-end // SECTOR) * SECTOR
            f.write(b'\0' * (start - end) + data + b'\0' * ((-len(data)) % SECTOR))
            new_end = f.tell()
            sector = (start - pkg) // SECTOR
            if row:
                row[1], row[2] = sector, (row[2] & 0xF0000000) | len(data)
                how = 'moved to the ISO end (package sector %d)' % sector
            else:
                if 16 + (count + 1) * 12 > min(INFO_MAX, INFO_ROOM):
                    sys.exit('no room for another PACKAGE_INFO entry')
                rows.append([h, sector, 0x10000000 | len(data)])
                rows.sort()
                how = 'added as a new entry at the ISO end (package sector %d)' % sector
            set_both(f, pkg_rec + 10, new_end - pkg)
            set_both(f, 16 * SECTOR + 80, new_end // SECTOR)
        out = info[:16] + b''.join(struct.pack('<III', *r) for r in rows)
        struct.pack_into('<I', out, 8, len(rows))
        f.seek(PACKAGE_INFO_ISO_SECTOR * SECTOR)
        f.write(out)
        set_both(f, info_rec + 10, len(out))
        print('%s (%d bytes): %s' % (path, len(data), how))


if __name__ == '__main__':
    main()
