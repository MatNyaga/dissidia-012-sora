"""Museum > Character Files > View Character: let Sora's viewer list outfits 4-6 (Valor / Wisdom / Final) too.

RR-09 (static, 2026-10-18, notes/release-rr-static-b.md). How the viewer picks costumes (OVL_MENU_APP):
  FUN_08a34df0 fills obj+0x17c[0..12] (13 x s16, memset -1): [0] 1P = record +12, [1] 2P = +14 if flag +20 is set,
  [2] 3P = +16 if flag +22 is set, [3] manikin = +18, [4..12] = "DLC costumes" from FUN_08a32284: bit k set when
  FUN_088470dc(owner, k, 0) finds an objentry row (owner, costume k, kind 0). FUN_08a32028 loads slot >= 4 through
  the same owner. The owner comes from FUN_08a3200c = s16 table 0x08A358FC[record index] - 34 entries (records
  0..33). Sora's record is index 34 (spot33_museum) -> it reads 0x08A35940, a live u32 (8) used by other code ->
  owner 8 -> no rows -> Sora's viewer shows outfits 1-3 only, although objentry has P_SEV120_4P/5P/6P (owner 33,
  costume 4/5/6; spot33_outfits) and battle offers all six.

Fix (2 functions rewritten in place, same size; no table move - the bytes after the table are used):
  FUN_08a3200c (7 words): same lookup, then `j TAIL; xori a1,v1,0x22`.
  FUN_08a32284 (31 words): same loop, compacted (constant 1 no longer kept in s0) -> 3 free words hold TAIL:
  `addiu a0,zero,0x21; jr ra; movz v0,a0,a1` -> record index 34 returns owner 33, every other index unchanged.
  Only callers: jal 0x08a3200c at 0x08a320a4 / 0x08a3229c / 0x08a3230c, jal 0x08a32284 at 0x08a34f24 (scanned:
  nothing else branches into either function). v1/a0/a1 are caller-saved temporaries.
Guards: both functions = clean words or ours; table 0x08A358FC = clean 34 entries + 8 at 0x08A35940; collection_param
record 34 = Sora (picture p_sev120_1p, 1P model 1187); objentry has owner-33 kind-0 rows for costumes 4..6;
refuses an ISO PPSSPP has open. --dry writes nothing, --rollback restores the clean words. Re-runnable ("already").

  python3 -I spot33_viewer.py ISO [--dry] [--rollback]
"""
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from roster_patch import MENU_FILEOFF, MENU_ISO_SECTOR, MENU_VADDR  # noqa: E402
from mips_asm import asm  # noqa: E402
import mpk  # noqa: E402

SECTOR = 0x800
LOOKUP_VA, LOOP_VA = 0x08A3200C, 0x08A32284
TABLE_VA, TABLE_N = 0x08A358FC, 34
CLEAN_TABLE = (31, 30, 27, 28, 24, 26, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
               22, 29, 25, 0, 23, 0, 0)
CLEAN_LOOKUP = [0x8C840044, 0x3C0508A3, 0x00842021, 0x24A558FC, 0x00852021, 0x03E00008, 0x84820000]
CLEAN_LOOP = [0x27BDFFE0, 0xAFB00000, 0xAFB10004, 0xAFB20008, 0xAFB3000C, 0xAFBF0010, 0x0E28C803, 0x34130000,
              0x00409025, 0x34110004, 0x34100001, 0x02402025, 0x02202825, 0x0E211C37, 0x00003025, 0x10400003,
              0x00000000, 0x02302004, 0x02649825, 0x26310001, 0x2A24000D, 0x1480FFF5, 0x00000000, 0x02601025,
              0x8FB00000, 0x8FB10004, 0x8FB20008, 0x8FB3000C, 0x8FBF0010, 0x03E00008, 0x27BD0020]
SORA_RECORD, SORA_OWNER = 34, 33
TAIL_VA = LOOP_VA + 28 * 4
SLLV_A0_A0_S1 = 17 << 21 | 4 << 16 | 4 << 11 | 4          # sllv a0,a0,s1 (mips_asm has no sllv)


def ours():
    lookup = asm(['lw v1,0x44(a0)', 'lui a1,0x8a3', 'addu a0,v1,v1', 'addu a0,a0,a1', 'lh v0,0x58fc(a0)',
                  'j 0x%08x' % TAIL_VA, 'xori a1,v1,0x22'], LOOKUP_VA)
    loop = asm(['addiu sp,sp,-0x20', 'sw s1,0x4(sp)', 'sw s2,0x8(sp)', 'sw s3,0xc(sp)', 'sw ra,0x10(sp)',
                'jal 0x%08x' % LOOKUP_VA, 'ori s3,zero,0x0', 'or s2,v0,zero', 'ori s1,zero,0x4',
                'L:', 'or a0,s2,zero', 'or a1,s1,zero', 'jal 0x088470dc', 'or a2,zero,zero',
                'beq v0,zero,SKIP', 'ori a0,zero,0x1', '.word 0x%08x' % SLLV_A0_A0_S1, 'or s3,s3,a0',
                'SKIP:', 'addiu s1,s1,0x1', 'slti a0,s1,0xd', 'bne a0,zero,L', 'nop',
                'or v0,s3,zero', 'lw s1,0x4(sp)', 'lw s2,0x8(sp)', 'lw s3,0xc(sp)', 'lw ra,0x10(sp)',
                'jr ra', 'addiu sp,sp,0x20',
                'TAIL:', 'addiu a0,zero,0x%x' % SORA_OWNER, 'jr ra', 'movz v0,a0,a1'], LOOP_VA)
    assert len(lookup) == len(CLEAN_LOOKUP) and len(loop) == len(CLEAN_LOOP), (len(lookup), len(loop))
    return lookup, loop


def menu_off(va):
    return MENU_ISO_SECTOR * SECTOR + va - MENU_VADDR + MENU_FILEOFF


def words(f, va, n):
    f.seek(menu_off(va))
    return list(struct.unpack('<%dI' % n, f.read(4 * n)))


def check_data(iso):
    use_iso(iso)
    with open(iso, 'rb') as f:
        f.seek(menu_off(TABLE_VA))
        tab = struct.unpack('<%dh' % (TABLE_N + 2), f.read(2 * (TABLE_N + 2)))
        st, sz = pkg_offset('collection_param.bin')
        cp = read_at(f, st, sz)
        st, sz = pkg_offset('general_archive/main/main.bin')
        main = read_at(f, st, sz)
    assert tab[:TABLE_N] == CLEAN_TABLE, 'viewer owner table 0x%08X is not the clean one - stop' % TABLE_VA
    assert tab[TABLE_N:] == (8, 0), 'word after the table (0x08A35940) is not the clean 8 - stop'
    _, nsec = struct.unpack_from('<HH', cp, 0)
    counts = struct.unpack_from('<%dH' % nsec, cp, 4)
    base = 4 + 4 * nsec
    assert counts[0] == SORA_RECORD + 1, 'collection_param section 0 has %d records, expected %d (run spot33_museum)' % (
        counts[0], SORA_RECORD + 1)
    rec = cp[base + 48 * SORA_RECORD: base + 48 * (SORA_RECORD + 1)]
    assert rec[32:48].split(b'\0')[0] == b'p_sev120_1p' and struct.unpack_from('<h', rec, 12)[0] == 1187, \
        'Character Files record %d is not Sora - stop' % SORA_RECORD
    ob = dict((n, main[o:o + s]) for n, o, s in mpk.entries(main))['objentry.bin']
    _, n = struct.unpack_from('<II', ob, 0)
    costumes = sorted(ob[8 + 68 * i + 7] for i in range(n)
                      if ob[8 + 68 * i + 6] == SORA_OWNER and ob[8 + 68 * i + 8] & 8 == 0
                      and ob[8 + 68 * i + 0x24:8 + 68 * i + 0x44].split(b'\0')[0].endswith(b'P'))
    extra = [k for k in costumes if 4 <= k <= 12]
    assert extra, 'no owner-33 objentry rows for costumes 4..12 (run spot33_outfits) - nothing to show'
    return costumes, extra


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    assert len(args) == 1, __doc__
    iso = args[0]
    dry, rollback = '--dry' in sys.argv, '--rollback' in sys.argv
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the vanilla ISO'
    if not dry:
        r = subprocess.run(['pgrep', '-a', '-x', 'PPSSPPSDL'], capture_output=True, text=True)
        assert os.path.abspath(iso) not in r.stdout and os.path.basename(iso) not in r.stdout, \
            'PPSSPP has this ISO open - stop'
    costumes, extra = check_data(iso)
    lookup, loop = ours()
    with open(iso, 'rb') as f:
        cur_lookup, cur_loop = words(f, LOOKUP_VA, 7), words(f, LOOP_VA, 31)
    assert cur_lookup in (CLEAN_LOOKUP, lookup), 'FUN_08a3200c is neither clean nor ours - stop'
    assert cur_loop in (CLEAN_LOOP, loop), 'FUN_08a32284 is neither clean nor ours - stop'
    want_lookup, want_loop = (CLEAN_LOOKUP, CLEAN_LOOP) if rollback else (lookup, loop)
    state = 'already' if (cur_lookup, cur_loop) == (want_lookup, want_loop) else ('dry' if dry else 'written')
    print('owner-33 battle costumes in objentry: %s -> viewer extra outfits %s' % (costumes, extra))
    print('OVL_MENU_APP Museum viewer owner lookup (record %d -> owner %d): FUN_08a3200c 7 + FUN_08a32284 31 words '
          '%s: %s' % (SORA_RECORD, SORA_OWNER, 'rollback' if rollback else 'fix', state))
    if state == 'written':
        with open(iso, 'r+b') as f:
            f.seek(menu_off(LOOKUP_VA))
            f.write(struct.pack('<7I', *want_lookup))
            f.seek(menu_off(LOOP_VA))
            f.write(struct.pack('<31I', *want_loop))
        with open(iso, 'rb') as f:
            assert words(f, LOOKUP_VA, 7) == want_lookup and words(f, LOOP_VA, 31) == want_loop
    print('dry run, nothing written' if dry else 'done')


if __name__ == '__main__':
    main()
