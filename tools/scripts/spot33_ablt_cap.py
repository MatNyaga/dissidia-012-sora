"""Raise the runtime ability-table buffer from 808 to 832 rows (Sora's new moves need > 808 ablt rows).
FUN_088b1cc0 allocates chunk size + (0x328 - row count) * 0x28 and copies the whole ablt chunk in: with more than
0x328 rows the block is too small. EBOOT VA 0x088B1CF0 `ori a1,zero,0x328` (34050328) → 0x340 (+960 B heap).
(notes/abilities-owner33.md §2, notes/hp-magic.md §4). Re-runnable; checks the old bytes first.

  python3 -I spot33_ablt_cap.py ISO
"""
import sys

AT, OLD, NEW = 0x1C6CC8, bytes.fromhex('28030534'), bytes.fromhex('40030534')


def main():
    with open(sys.argv[1], 'r+b') as f:
        f.seek(AT)
        cur = f.read(4)
        if cur == NEW:
            print('ablt row cap already 832')
            return
        assert cur == OLD, 'unexpected bytes %s at ISO 0x%X' % (cur.hex(), AT)
        f.seek(AT)
        f.write(NEW)
        print('ablt row cap 808 -> 832 (EBOOT 0x088B1CF0)')


if __name__ == '__main__':
    main()
