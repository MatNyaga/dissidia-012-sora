"""Save safety for Sora's saved record (RR-01 / RR-03, notes/release-save-safety.md). EBOOT code only.

Background (spot33_save.py): owner 33's fighter record (0x778 B) lives inside friend card 24 (save + 0x38F98 =
card list save+0x1FECC + 24*0x10A8 + 0x10C) and the friend-card limit is 25 -> 24. Two gaps:
  RR-01  A save that already holds 25 friend cards (vanilla full list, or a mod save that got a 25th card while it was
         played on the unmodded game) has a real card in slot 24. The first time Sora's record is used, the old code
         re-initialised the record on top of that card -> card 25 turned into garbage (still counted and shown).
  RR-03  Abilities come only from level-ups (FUN_088cbd24(rec, old, new)); the game has no catch-up for saved records.
         A Sora record that is already above a learn level when that move is added (older mod saves, future updates)
         never learns it.

Fix: GET_RECORD (FUN_088cb164, written by spot33_save) hands owner 33's record to SORA_REC, a helper in the dead
function FUN_088cb2c0 (61 words; its only caller was the original FUN_088cb3b4, which spot33_save replaced):
  1. card count >= 25 (list save+0x1FECC, count save+0x39F34):
     a. record already valid (owner byte 33, level 1..100; owner 33 never appears in a vanilla card): the save was used
        with test20..test343 and card 25 is already overwritten -> count = 24 only, Sora's record kept as is.
     b. otherwise: count = 24, then the game's own "receive card" FUN_088f526c(list, card 24): card 25 replaces the
        oldest unlocked card exactly as if it had just been received with a full list (a duplicate is dropped);
        locked cards are never touched. Then the record is set up fresh (the old bytes there were card data).
     (v1 in test344 had the list/count constants wrong - base+0x2FECC/+0x2A068 - so step 1 never matched; superseded.)
  2. record owner byte != 33 -> FUN_088cbbb4(rec, 33) (unchanged behaviour: owner 33, Lv1, preset 250).
  3. record byte +0x777 != MARK -> FUN_088cbd24(rec, 1, level) once (learns every chrl entry for levels 2..level;
     already-known ids are skipped; level-1 row = the only row with a bonus byte is outside the range), then
     +0x777 = MARK. +0x776/+0x777 are never read or written by EBOOT/menu/battle/extra code (immediate scan; the
     record reset FUN_088cba10/FUN_088b7e30 stops at +0x775). Bump MARK when Sora's chrl table changes.
Save size/layout unchanged (blob 0x3ECC8, section table untouched).

Guards: plain ELF; spot33_save's LOOKUP + GET_RECORD present (or ours); friend-card caps = 24; cave = clean bytes of
FUN_088cb2c0 (or ours) and no jal/j into it anywhere in the disc EBOOT; FUN_088cbd24 / FUN_088cbbb4 / FUN_088b6f48 /
FUN_088f56ec clean; FUN_088f526c clean except the cap word; owner 33 chrl: rows above Lv1 have bonus 0 and levels
2..100 hold <= 80 ids (FUN_088b6f48 collects at most 80 per call). Re-runnable ("already"), --dry writes nothing,
--rollback restores spot33_save's GET_RECORD and the clean cave bytes.

  python3 -I spot33_savefix.py ISO [--dry] [--rollback]
"""
import hashlib
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, mpk_member, package_entry, read_at  # noqa: E402
from mips_asm import asm  # noqa: E402
from pkg_put import PACKAGE_INFO_ISO_SECTOR  # noqa: E402
from spot33_save import GET_RECORD, LOOKUP, arc_split  # noqa: E402

EBOOT_ISO = 560 * SECTOR
CLEAN_EBOOT = os.path.join(HERE, '../../dumps/extracted/EBOOT.elf')
GET_VA, LOOKUP_VA = 0x088CB164, 0x088CB3B4
CAVE_VA, CAVE_END = 0x088CB2C0, 0x088CB3B4          # dead FUN_088cb2c0
CAPS = {0x088F523C: 0x2A440018, 0x088F52A0: 0x28860018}   # spot33_save: friend-card limit 24
# v1 cave (test344) computed the card list / count as base+0x2FECC / +0x2A068 (wrong; real 0x1FECC / 0x1A068)
V1_CAVE_SHA = 'be87b3de9cc952fcd788889c9adc32c29e578209f04e696af8039315872c6b65'
MARK = 0xC1                                          # catch-up version byte at record +0x777
CLEAN_FUNCS = {                                      # name: (start, end, sha256[:16] of clean bytes)
    'FUN_088cbd24 learn levels': (0x088CBD24, 0x088CBDDC, None),
    'FUN_088cbbb4 reset record': (0x088CBBB4, 0x088CBCB4, None),
    'FUN_088b6f48 collect chrl ids': (0x088B6F48, 0x088B7060, None),
    'FUN_088f56ec find card': (0x088F56EC, 0x088F5790, None),
}

NEW_GET = """
    addiu sp,sp,-0x10
    sw s0,0x0(sp)
    move s0,a0
    sw ra,0x4(sp)
    jal 0x088cb3b4
    _move a0,a1
    bgez v0,MUL
    _li t2,0x21
    bne a1,t2,BLANK
    _lui t3,0x89d
    lw s0,0x712c(t3)
    lui t3,0x4
    addiu t3,t3,-0x7068
    addu v0,s0,t3
    move a0,v0
    jal 0x088cb2c0
    _move s0,v0
    b END
    _move v0,s0
    nop
    nop
    nop
MUL:
    li t0,0x778
    mult v0,t0
    mflo t0
    addu v0,s0,t0
END:
    lw s0,0x0(sp)
    lw ra,0x4(sp)
    jr ra
    _addiu sp,sp,0x10
BLANK:
    lui a1,0x9af
    lw a0,-0x508(a1)
    j 0x088cb3e4
    _li t0,0x1
"""

SORA_REC = """
    addiu sp,sp,-0x10
    sw ra,0x0(sp)
    sw s1,0x4(sp)
    move s1,a0
    lui t0,0x89d
    lw a0,0x712c(t0)
    lui t0,0x2
    addiu t0,t0,-0x134
    addu a0,a0,t0
    lui t0,0x2
    addiu t0,t0,-0x5f98
    addu t0,a0,t0
    lw t1,0x0(t0)
    slti t1,t1,0x19
    bne t1,zero,OWN
    _li t1,0x18
    lb t3,0x0(s1)
    li t2,0x21
    bne t3,t2,EVICT
    _lbu t3,0x1(s1)
    addiu t3,t3,-0x1
    sltiu t3,t3,0x64
    beq t3,zero,EVICT
    _nop
    b HAVE
    _sw t1,0x0(t0)
EVICT:
    sw t1,0x0(t0)
    lui a1,0x1
    ori a1,a1,0x8fc0
    jal 0x088f526c
    _addu a1,a0,a1
    b INIT
    _nop
OWN:
    lb t3,0x0(s1)
    li t2,0x21
    beq t3,t2,HAVE
    _nop
INIT:
    move a0,s1
    jal 0x088cbbb4
    _li a1,0x21
HAVE:
    lbu t3,0x777(s1)
    li t2,%d
    beq t3,t2,DONE
    _move a0,s1
    li a1,0x1
    jal 0x088cbd24
    _lbu a2,0x1(s1)
    li t2,%d
    sb t2,0x777(s1)
DONE:
    move v0,s1
    lw ra,0x0(sp)
    lw s1,0x4(sp)
    jr ra
    _addiu sp,sp,0x10
""" % (MARK, MARK)


def lines(src):
    return src.strip().split('\n')


def eoff(va):
    return 0x1018 + va - 0x8804040


def words(f, va, n):
    f.seek(EBOOT_ISO + eoff(va))
    return list(struct.unpack('<%dI' % n, f.read(4 * n)))


def sha(b):
    return hashlib.sha256(b).hexdigest()[:16]


def chrl_check(f):
    info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
    pkg = PACKAGE_ISO_SECTOR * SECTOR
    off, size = package_entry(info, 'general_archive/main/main.bin')
    main = read_at(f, pkg + off, size)
    so, ss = mpk_member(f, pkg + off, 'system.bin')
    so -= pkg + off
    chrl = [c[2] for c in arc_split(main[so:so + ss])[1] if c[1] == b'chrl'][0]
    count, = struct.unpack_from('<I', chrl, 8)
    for i in range(count):
        own, n, at, _ = struct.unpack_from('<IIII', chrl, 16 + i * 16)
        if own != 33:
            continue
        rows = [struct.unpack_from('<bb3H', chrl, at + r * 8) for r in range(n)]
        lv = [r[0] for r in rows]
        assert lv == sorted(lv), 'owner 33 chrl rows not in level order: %s' % lv
        bonus = [(r[0], r[1]) for r in rows if r[0] >= 2 and r[1]]
        assert not bonus, 'owner 33 chrl rows above Lv1 carry a bonus byte %s (catch-up would add it again)' % bonus
        ids = [x for r in rows if r[0] >= 2 for x in r[2:] if x != 0xFFFF]
        ids_all = [x for r in rows for x in r[2:] if x != 0xFFFF]
        assert len(ids_all) <= 80, 'owner 33 chrl has %d ids (> 80 per FUN_088b6f48 call)' % len(ids_all)
        return len(ids), len(ids_all)
    raise AssertionError('owner 33 has no chrl table (run spot33_save / spot33_moves first)')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    assert len(args) == 1, __doc__
    iso = args[0]
    dry, rollback = '--dry' in sys.argv, '--rollback' in sys.argv
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the vanilla ISO'
    clean = open(CLEAN_EBOOT, 'rb').read()
    old_get, new_get = asm(lines(GET_RECORD), GET_VA), asm(lines(NEW_GET), GET_VA)
    cave_new = asm(lines(SORA_REC), CAVE_VA)
    assert len(old_get) == len(new_get) == 34, (len(old_get), len(new_get))
    assert len(cave_new) <= (CAVE_END - CAVE_VA) // 4, len(cave_new)
    n = len(cave_new)
    cave_clean = list(struct.unpack_from('<%dI' % n, clean, eoff(CAVE_VA)))
    with open(iso, 'rb') as f:
        f.seek(EBOOT_ISO)
        assert f.read(4) == b'\x7fELF', 'EBOOT is not the plain ELF (run eboot_plain first)'
        f.seek(EBOOT_ISO)
        ebo = f.read(len(clean) + 0x40000)
        lk = asm(lines(LOOKUP), LOOKUP_VA)
        assert words(f, LOOKUP_VA, len(lk)) == lk, 'FUN_088cb3b4 is not spot33_save LOOKUP - stop (run spot33_save)'
        for va, w in CAPS.items():
            assert words(f, va, 1) == [w], 'friend-card cap at %08x is not 24 - stop (run spot33_save)' % va
        for name, (a, b, _) in CLEAN_FUNCS.items():
            assert ebo[eoff(a):eoff(b)] == clean[eoff(a):eoff(b)], '%s differs from the clean EBOOT - stop' % name
        a, b = eoff(0x088F526C), eoff(0x088F53F4)
        diff = [i for i in range(a, b, 4) if ebo[i:i + 4] != clean[i:i + 4]]
        assert diff == [eoff(0x088F52A0)], 'FUN_088f526c differs from clean beyond the cap word: %s' % diff
        lo, hi = CAVE_VA >> 2 & 0x3FFFFFF, (CAVE_END >> 2 & 0x3FFFFFF)
        callers = []
        for i in range(0, len(ebo) - 3, 4):
            w, = struct.unpack_from('<I', ebo, i)
            if w >> 26 in (2, 3) and lo <= (w & 0x3FFFFFF) < hi:
                callers.append(0x8804040 + i - 0x1018)
        get_cur = words(f, GET_VA, 34)
        cave_cur = words(f, CAVE_VA, n)
        v1_cur = words(f, CAVE_VA, 44)
        ids_lv2, ids_all = chrl_check(f)
    assert get_cur in (old_get, new_get), 'GET_RECORD (FUN_088cb164) is neither spot33_save\'s nor ours - stop'
    v1 = hashlib.sha256(struct.pack('<44I', *v1_cur)).hexdigest() == V1_CAVE_SHA
    if v1:
        print('cave holds the v1 SORA_REC from test344 (wrong card-list address) -> replaced')
    assert cave_cur in (cave_clean, cave_new) or v1, 'cave 0x%08x is neither clean FUN_088cb2c0 nor ours - stop' % CAVE_VA
    ours = [hex(c) for c in callers if not (get_cur == new_get and c == GET_VA + 15 * 4)]
    assert not ours, 'something already calls into dead FUN_088cb2c0: %s - stop' % ours
    want_get, want_cave = (old_get, cave_clean) if rollback else (new_get, cave_new)
    print('owner 33 chrl: %d ids at Lv2..100 (%d incl. Lv1), bonus only on Lv1 -> one catch-up call learns all'
          % (ids_lv2, ids_all))
    print('cave FUN_088cb2c0 (dead, %d/%d words): %s' % (n, (CAVE_END - CAVE_VA) // 4,
          'already' if cave_cur == want_cave else ('write' + (' (dry)' if dry else ''))))
    print('GET_RECORD 0x%08x owner-33 branch -> %s: %s' % (GET_VA, 'spot33_save original' if rollback else 'SORA_REC',
          'already' if get_cur == want_get else ('write' + (' (dry)' if dry else ''))))
    if dry:
        print('dry run, nothing written')
        return
    with open(iso, 'r+b') as f:
        if rollback:          # unhook first, then restore the cave
            order = ((GET_VA, get_cur, want_get), (CAVE_VA, cave_cur, want_cave))
        else:                 # cave first, then hook
            order = ((CAVE_VA, cave_cur, want_cave), (GET_VA, get_cur, want_get))
        for va, cur, want in order:
            if cur != want:
                f.seek(EBOOT_ISO + eoff(va))
                f.write(struct.pack('<%dI' % len(want), *want))
    with open(iso, 'rb') as f:
        assert words(f, GET_VA, 34) == want_get and words(f, CAVE_VA, n) == want_cave, 'read-back mismatch'
    print('done')


if __name__ == '__main__':
    main()
