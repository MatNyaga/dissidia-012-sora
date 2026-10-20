"""Data Install fix (P0.9, notes/dlc-phase0.md): PACKAGE_INFO rows the mod ADDED (hash not in the clean disc's index)
get install-tier flag 0, so the game's Data Install copies exactly the vanilla set (size 3 used to need 4,169 files >
the 4,050 limit on the Sora ISO -> install silently ignored). Repointed vanilla rows keep their tier. Re-runnable.

  python3 -I spot33_installfix.py ISO [--dry]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import read_at  # noqa: E402

SECTOR = 0x800
INFO_SECTOR = 26000                        # PACKAGE_INFO.BIN in the ISO (comb_patch.pkg_offset_by_path)


def main():
    iso, dry = sys.argv[1], '--dry' in sys.argv
    clean = open(os.path.join(HERE, '../../dumps/extracted/PACKAGE_INFO.BIN'), 'rb').read()
    cn, = struct.unpack_from('<I', clean, 8)
    vanilla = {struct.unpack_from('<I', clean, 16 + i * 12)[0] for i in range(cn)}
    with open(iso, 'rb') as f:
        head = read_at(f, INFO_SECTOR * SECTOR, 16)
        n, = struct.unpack_from('<I', head, 8)
        info = bytearray(read_at(f, INFO_SECTOR * SECTOR, 16 + n * 12))
    changed = 0
    for i in range(n):
        h, sec, sf = struct.unpack_from('<III', info, 16 + i * 12)
        if h not in vanilla and sf & 0xF0000000:
            struct.pack_into('<I', info, 16 + i * 12 + 8, sf & 0x0FFFFFFF)
            changed += 1
    added = sum(1 for i in range(n) if struct.unpack_from('<I', info, 16 + i * 12)[0] not in vanilla)
    print('PACKAGE_INFO: %d rows (%d added by the mod); %s' % (n, added, '%d added rows had an install tier -> 0' % changed
                                                               if changed else 'already: no added row has a tier'))
    if changed and not dry:
        with open(iso, 'r+b') as f:
            f.seek(INFO_SECTOR * SECTOR)
            f.write(info)
    elif changed:
        print('--dry: nothing written')


if __name__ == '__main__':
    main()
