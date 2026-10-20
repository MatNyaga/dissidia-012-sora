"""P0.9: what the game's Data Install would copy for an ISO, and whether the result would be VALID (read-only).

  python3 -I tools/dlc/install_plan.py ISO_OR_PACKAGE_INFO.BIN

Rules (EBOOT + OVL_EXTRA_APP, see notes/dlc-phase0.md P0.9):
- level L (menu choice 1..3) copies every PACKAGE_INFO row whose top-4-bit flag f is 1 <= f <= L;
- a file is skipped if its 8 KB-aligned size > 0x280000 (install work buffer);
- at most 4050 (0xFD2) entries are written (header 0x80 + 4050 * 0x1C = 0x1BB78 bytes);
- at boot the install is only used if the header count == number of flagged rows (1..L) AND the stored raw size
  total == their size sum (FUN_0886f7a8). Skipped/over-limit files therefore make the WHOLE install invalid.
Never writes anything.
"""
import struct
import sys

SECTOR = 0x800
CAP = 0x280000
MAX_ENTRIES = 0xFD2
HEADER_ALIGNED = 0x1C000          # 0x1BB78 rounded up to 8 KB


def iso_file(f, path):
    f.seek(16 * SECTOR)
    pvd = f.read(SECTOR)
    assert pvd[1:6] == b'CD001', 'not an ISO9660 image'
    ext, size = struct.unpack_from('<I', pvd, 156 + 2)[0], struct.unpack_from('<I', pvd, 156 + 10)[0]
    for part in path.strip('/').split('/'):
        f.seek(ext * SECTOR)
        data = f.read(size)
        pos, found = 0, None
        while pos < len(data):
            ln = data[pos]
            if ln == 0:
                pos = (pos // SECTOR + 1) * SECTOR
                continue
            name = data[pos + 33:pos + 33 + data[pos + 32]].decode('ascii', 'replace').split(';')[0]
            if name.upper() == part.upper():
                found = struct.unpack_from('<I', data, pos + 2)[0], struct.unpack_from('<I', data, pos + 10)[0]
                break
            pos += ln
        if not found:
            sys.exit('%s not found in ISO' % path)
        ext, size = found
    f.seek(ext * SECTOR)
    return f.read(size)


def main():
    src = sys.argv[1]
    with open(src, 'rb') as f:
        head = f.read(8)
        f.seek(0)
        info = f.read() if head[4:8] == b'pack' else iso_file(f, '/PSP_GAME/USRDIR/DATA/PACKAGE_INFO.BIN')
    count = struct.unpack_from('<I', info, 8)[0]
    rows = [struct.unpack_from('<3I', info, 16 + 12 * i) for i in range(count)]
    per = {k: sum(1 for r in rows if r[2] >> 28 == k) for k in range(16)}
    print('%s: %d index rows; flag counts %s' % (src, count, {k: v for k, v in per.items() if v}))
    for level in (1, 2, 3):
        sel = [r for r in rows if 0 < (r[2] >> 28) <= level]
        sizes = [r[2] & 0x0FFFFFFF for r in sel]
        al = [(s + 0x1FFF) & ~0x1FFF for s in sizes]
        fit = [i for i, a in enumerate(al) if a <= CAP]
        written = fit[:MAX_ENTRIES]
        biggest = max(sizes) if sizes else 0
        dat = HEADER_ALIGNED + sum(al[i] for i in written)
        ok = len(written) == len(sel)
        why = []
        if len(fit) < len(sel):
            why.append('%d file(s) > 0x280000 aligned' % (len(sel) - len(fit)))
        if len(fit) > MAX_ENTRIES:
            why.append('%d entries > 4050 limit' % len(fit))
        print('  level %d: %4d files, raw %.1f MB, DISSINST.DAT ~%.1f MB, largest %d B (cap %d), %s%s' % (
            level, len(sel), sum(sizes) / 2**20, dat / 2**20, biggest, CAP,
            'VALID' if ok else 'INVALID', '' if ok else ' (' + '; '.join(why) + ')'))
        if level == 3:
            print('  level 3 entry headroom: %d' % (MAX_ENTRIES - len(sel)))


if __name__ == '__main__':
    main()
