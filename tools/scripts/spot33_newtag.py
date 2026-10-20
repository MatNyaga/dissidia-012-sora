"""Yellow "NEW" tag for Sora after he is bought in the PP Catalog (2026-10-18, notes/unlocks.md §5).

How the game decides "NEW" (EBOOT, static):
  unlock table 0x089D7BE0, 5 x i32 per row: owner, unlock flag, costume-2 flag, costume-3 flag, **SEEN flag**
  (vanilla 3601..3632 = 3600 + owner; the old notes called it "text id").
  - FUN_088d5ac8 builds the select list (Quick Battle grid, Customization, ...); entry +4 = FUN_088d60e4(owner)
    = 1 while the row's SEEN flag bit (DAT_089d726c save flags) is clear -> yellow NEW on the cell + series logo.
  - Leaving the grid (menu FUN_08a80c24) clears the bit and FUN_088d61ec -> FUN_088d617c sets every listed row's
    SEEN flag. Buying in the catalog only sets the unlock flag; it never touches the SEEN flag.
  - Row 22 (Chaos's row, owner 33 since test20) kept Chaos's SEEN flag 3623. Sora was always unlocked from test20 to
    test326, so every save that opened the grid then already has 3623 set -> after buying him (test327+) the game
    thinks he was seen before: no NEW. (Garland's 3602 was never set because he was locked until bought.)

Fix (1 EBOOT word): row 22 SEEN flag 3623 -> 3633 (= 3600 + 33, the slot the designers' pattern gives owner 33).
3633 is free: not in any unlock row, catalog item, Museum (collection_param) flag field or code immediate; the
new-game flag init (EBOOT FUN at 0x088b0... DAT_089d726c[0x71]) sets only bits of 3617/3619/3624/3626-3628/3630/3631;
flag area = 0x280 B = flags 0..5119. Result: any save shows NEW once on Sora's cell the first time the grid is opened
with him unlocked, then it clears like the vanilla fighters. Chaos's 3623 is left orphaned (harmless).

Guards: EBOOT is the plain ELF; row 22 = (33, -1|925, 1, 1, 3623|3633) (eboot_plain/spot33_outfits/spot33_catalog
results); the readers FUN_088d60e4 / FUN_088d617c / FUN_088d61ec are byte-identical to the clean EBOOT; no other
row uses 3633; no catalog item / Museum record uses flag 3633. Re-runnable ("already"), --dry writes nothing,
--rollback puts 3623 back.

  python3 -I spot33_newtag.py ISO [--dry] [--rollback]
"""
import hashlib
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402

EBOOT_ISO = 560 * 0x800
TABLE_VA = 0x089D7BE0
ROW = 22
OLD_SEEN, NEW_SEEN = 3623, 3633
# reader / marker functions (clean EBOOT bytes, sha256 of [start, end))
READERS = {
    'FUN_088d60e4 (is NEW)': (0x088D60E4, 0x088D617C, '8ff2f6cc4d68a52a'),
    'FUN_088d617c (mark seen)': (0x088D617C, 0x088D61EC, 'c8faf824fd20c132'),
    'FUN_088d61ec (mark list seen)': (0x088D61EC, 0x088D6254, '2fc09d07a5892044'),
}


def eboot_off(va):
    return EBOOT_ISO + 0x1018 + va - 0x8804040


def table(f):
    rows = []
    for i in range(40):
        f.seek(eboot_off(TABLE_VA + 20 * i))
        r = struct.unpack('<5i', f.read(20))
        if r[0] == -1:
            return rows
        rows.append(r)
    raise AssertionError('unlock table has no -1 end within 40 rows')


def flag_users(iso):
    """-> list of places outside the unlock table that use flag NEW_SEEN"""
    use_iso(iso)
    hits = []
    with open(iso, 'rb') as f:
        st, sz = pkg_offset('update_list_param.bin')
        d = read_at(f, st, sz)
        n = sum(struct.unpack_from('<5h', d, 2))
        for i in range(n):
            it = struct.unpack_from('<I12h', d, 16 + 28 * i)
            if NEW_SEEN in it[4:8]:
                hits.append('catalog item %d %s' % (i, it))
        st, sz = pkg_offset('collection_param.bin')
        d = read_at(f, st, sz)
        hits += ['collection_param.bin +0x%X' % o for o in range(0, len(d) - 1, 2)
                 if struct.unpack_from('<H', d, o)[0] == NEW_SEEN]
    return hits


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    assert len(args) == 1, __doc__
    iso = args[0]
    dry, rollback = '--dry' in sys.argv, '--rollback' in sys.argv
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the vanilla ISO'
    with open(iso, 'rb') as f:
        f.seek(EBOOT_ISO)
        assert f.read(4) == b'\x7fELF', 'EBOOT is not the plain ELF (run eboot_plain first)'
        for name, (a, b, want) in READERS.items():
            f.seek(eboot_off(a))
            got = hashlib.sha256(f.read(b - a)).hexdigest()[:16]
            assert got == want, '%s is not the clean code (%s != %s) - stop' % (name, got, want)
        rows = table(f)
    assert len(rows) > ROW, rows
    cur = rows[ROW]
    assert cur[0] == 33 and cur[1] in (-1, 925) and cur[2:4] == (1, 1) and cur[4] in (OLD_SEEN, NEW_SEEN), \
        'unlock row %d = %s, expected (33, -1|925, 1, 1, %d|%d) - stop (run spot33_outfits/spot33_catalog first)' % (
            ROW, cur, OLD_SEEN, NEW_SEEN)
    others = [(i, r) for i, r in enumerate(rows) if i != ROW and NEW_SEEN in r[1:]]
    assert not others, 'flag %d already used by unlock rows %s - stop' % (NEW_SEEN, others)
    seen = [r[4] for i, r in enumerate(rows) if i != ROW]
    assert seen == [3600 + r[0] for i, r in enumerate(rows) if i != ROW], 'vanilla SEEN flags are not 3600+owner'
    users = flag_users(iso)
    assert not users, 'flag %d is used elsewhere: %s - stop' % (NEW_SEEN, users)
    want = OLD_SEEN if rollback else NEW_SEEN
    print('EBOOT unlock row %d (owner 33) SEEN/"NEW" flag: %d -> %d%s' % (
        ROW, cur[4], want, ' already' if cur[4] == want else (' (dry)' if dry else '')))
    print('  readers FUN_088d60e4/617c/61ec clean; flag %d unused by other rows, catalog items, Museum records' % NEW_SEEN)
    if cur[4] != want and not dry:
        with open(iso, 'r+b') as f:
            f.seek(eboot_off(TABLE_VA + 20 * ROW + 16))
            f.write(struct.pack('<i', want))
        with open(iso, 'rb') as f:
            assert table(f)[ROW] == cur[:4] + (want,)
    print('dry run, nothing written' if dry else 'done')


if __name__ == '__main__':
    main()
