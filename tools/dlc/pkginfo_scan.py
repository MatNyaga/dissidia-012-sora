"""Read-only P0.7 scan: how full is the disc file index (PACKAGE_INFO.BIN), how is it ordered, and which game code
reads the in-RAM copy of it (so an extra index can be added safely).

  python3 -I tools/dlc/pkginfo_scan.py                                    # test338 vs the clean index
  python3 -I tools/dlc/pkginfo_scan.py dumps/ULUS10566-p02-module.iso
  python3 -I tools/dlc/pkginfo_scan.py --info some/PACKAGE_INFO.BIN       # a loose index file (no code scan)

Never writes anything. Facts used (notes/dlc.md appendix B, notes/dlc-phase0.md P0.7):
- PACKAGE_INFO.BIN at ISO sector 26000; header u32 date, "pack", u32 count, u32 0; rows of 12 B (hash, sector,
  size|flag<<28), sorted by hash = CRC-32/BZIP2 of the lower-cased path (tools/scripts/pkghash.py).
- The game loads it into 0x09B26BC0, buffer 0x20F8C B (FUN_08871938) -> max (0x20F8C-16)/12 = 11,253 rows.
- Readers use (sector & 0xFFFFF) << 11 from PACKAGE.BIN's start (ISO sector 186624) and size & 0x0FFFFFFF.
- EBOOT.BIN = plain ELF at ISO sector 560 (VA = off + 0x08803028); menu overlay ISO sector 185056, battle overlay
  185824 (VA = off - 0x54 + 0x089DD4C0).
"""
import os
import struct
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '../..')
SECTOR = 0x800
INFO_SECTOR, PKG_SECTOR = 26000, 186624
TABLE, BUF = 0x09B26BC0, 0x20F8C
MAX_ROWS = (BUF - 16) // 12
LOOKUP = 0x088713E4
ACCESSORS = {0x088713E4: 'lookup by name (bsearch)', 0x08871674: 'count', 0x08871684: 'row by index',
             0x088716C8: 'size(entry)', 0x088716F0: 'size(entry) #2', 0x088714F4: 'sync read by name',
             0x088715BC: 'async read by name', 0x08871718: 'async read(entry)', 0x08871818: 'stream read(name, off)',
             0x08871644: 'size by name', 0x0886FB98: 'Data Install: entry -> install row'}
IMAGES = [('EBOOT', 560, 0x08803028, 0x1D9380 + 0x1018),
          ('menu overlay', 185056, 0x089DD4C0 - 0x54, 0x17BD98 + 0x54),
          ('battle overlay', 185824, 0x089DD4C0 - 0x54, 0x185AB0 + 0x54)]


def rows_of(info):
    n, = struct.unpack_from('<I', info, 8)
    return [struct.unpack_from('<III', info, 16 + i * 12) for i in range(n)]


def stats(rows, label, pkg_size=None):
    n = len(rows)
    hashes = [r[0] for r in rows]
    print('== %s' % label)
    print('rows %d / max %d in the 0x%X-byte RAM buffer -> %d free' % (n, MAX_ROWS, BUF, MAX_ROWS - n))
    print('hash order: %s; duplicate hashes: %d' % (
        'strictly ascending (bsearch-ready)' if all(a < b for a, b in zip(hashes, hashes[1:])) else 'NOT sorted',
        n - len(set(hashes))))
    secs = [r[1] for r in rows]
    asc = sum(1 for a, b in zip(secs, secs[1:]) if b > a)
    print('sector vs index: %d/%d neighbours ascending (index order = hash order, not disc order)' % (asc, n - 1))
    hi = Counter(r[1] >> 20 for r in rows)
    print('sector word bits 20-31 (ignored by the readers, & 0xFFFFF): %s' % dict(hi))
    flags = Counter(r[2] >> 28 for r in rows)
    print('flag (size >> 28, Data Install level 1..3, 0 = never installed): %s' % dict(sorted(flags.items())))
    end = max(((r[1] & 0xFFFFF) * SECTOR + (r[2] & 0x0FFFFFFF), r[1] & 0xFFFFF) for r in rows)
    print('max sector %d (0x%X) of 0xFFFFF; furthest file end at package offset 0x%X = %.1f MB '
          '(20-bit limit 2048 MB from PACKAGE.BIN start -> %.1f MB headroom)' % (
              max(secs) & 0xFFFFF, max(secs) & 0xFFFFF, end[0], end[0] / 2 ** 20, 2048 - end[0] / 2 ** 20))
    big = max(r[2] & 0x0FFFFFFF for r in rows)
    print('largest file %d B (size field 28 bits = 256 MB max)' % big)
    if pkg_size:
        past = [r for r in rows if (r[1] & 0xFFFFF) * SECTOR >= pkg_size]
        live = sum(-(-(r[2] & 0x0FFFFFFF) // SECTOR) * SECTOR for r in past)
        span = max([(r[1] & 0xFFFFF) * SECTOR + (r[2] & 0x0FFFFFFF) for r in past] or [pkg_size]) - pkg_size
        print('rows past the clean PACKAGE.BIN end (%d B; appended at the ISO end): %d, live data %.1f MB of a '
              '%.1f MB span (rest = dead older copies / other appended files)' % (
                  pkg_size, len(past), live / 2 ** 20, span / 2 ** 20))
    return set(hashes)


def scan_code(iso):
    """Every instruction pair `lui rX,0x09B2` + imm in 0x6BC0..0x6BDB (same rX, within 8 words), and jal counts
    to the index accessors, in EBOOT and both overlays."""
    for name, sector, base, size in IMAGES:
        iso.seek(sector * SECTOR)
        d = iso.read(size)
        words = struct.unpack('<%dI' % (len(d) // 4), d[:len(d) // 4 * 4])
        sites, jals = [], Counter()
        for i, w in enumerate(words):
            if w >> 26 == 3:
                t = (w & 0x03FFFFFF) << 2 | 0x08000000
                if t in ACCESSORS:
                    jals[t] += 1
            if w >> 26 == 0x0F and w & 0xFFFF == 0x09B2:
                rx = (w >> 16) & 31
                for j in range(i + 1, min(i + 9, len(words))):
                    v = words[j]
                    if (v >> 21) & 31 == rx and 0x6BC0 <= v & 0xFFFF <= 0x6BDB and v >> 26 in (0x09, 0x23, 0x2B):
                        sites.append((base + i * 4, base + j * 4, v & 0xFFFF, {0x09: 'addiu', 0x23: 'lw', 0x2B: 'sw'}[v >> 26]))
        print('== %s: lui 0x09B2 + table offset sites: %d' % (name, len(sites)))
        for lui, use, imm, op in sites:
            print('   lui @0x%08X  %s 0x%04X @0x%08X  (-> 0x%08X)' % (lui, op, imm, use, 0x09B20000 + imm - 0x10000 * (imm >= 0x8000)))
        print('   jal to index accessors: %s' % (', '.join('%s %08X x%d' % (ACCESSORS[t], t, c) for t, c in sorted(jals.items())) or 'none'))


def main():
    a = sys.argv[1:]
    clean = open(os.path.join(ROOT, 'dumps/extracted/PACKAGE_INFO.BIN'), 'rb').read()
    clean_pkg = os.path.getsize(os.path.join(ROOT, 'dumps/extracted/PACKAGE.BIN')) if os.path.exists(
        os.path.join(ROOT, 'dumps/extracted/PACKAGE.BIN')) else None
    base = stats(rows_of(clean), 'clean dumps/extracted/PACKAGE_INFO.BIN', clean_pkg)
    if a and a[0] == '--info':
        stats(rows_of(open(a[1], 'rb').read()), a[1], clean_pkg)
        return
    iso_path = a[0] if a else os.path.join(ROOT, 'dumps/ULUS10566-test338-voicesloud.iso')
    with open(iso_path, 'rb') as iso:
        iso.seek(INFO_SECTOR * SECTOR)
        head = iso.read(16)
        n, = struct.unpack_from('<I', head, 8)
        iso.seek(INFO_SECTOR * SECTOR)
        info = iso.read(16 + n * 12)
        mine = stats(rows_of(info), iso_path, clean_pkg)
        print('vs clean: %d rows added, %d removed' % (len(mine - base), len(base - mine)))
        rows = rows_of(info)
        cl = {r[0]: r for r in rows_of(clean)}
        changed = sum(1 for r in rows if r[0] in cl and r != cl[r[0]])
        print('vs clean: %d existing rows repointed/resized (files replaced by the mod)' % changed)
        crow = rows_of(clean)
        shift = next((i for i, r in enumerate(rows) if i >= len(crow) or crow[i][0] != r[0]), None)
        print('first index whose hash differs from the clean index at the same position: %s '
              '(every later index has shifted -> Data Install rows, keyed by u16 index, no longer match)' % shift)
        scan_code(iso)


if __name__ == '__main__':
    main()
