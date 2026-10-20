"""Original Quest editor: Sora counts as "has a saved record" (RR-18, 2026-10-18, static; notes/release-rr-static-b.md).

Why (EBOOT + OVL_MENU_APP, static):
  FUN_089293dc(owner) = 1..34 and FUN_088cb1ec(records, owner) -> "this fighter has a saved record". FUN_088cb1ec looks
  the owner up in the saved-record owner list 0x089CBC98 (1..22, 24..32), so owner 33 (Sora) -> 0, although
  spot33_save's GET_RECORD (FUN_088cb164) serves Sora's real record (save base + 0x38F98). FUN_089293dc has exactly two
  callers, both in the Original Quest editor (OVL_MENU_APP):
    FUN_08a5a88c (character entry commit): if 1 -> rebuilds the entry's ghost/loadout data from the saved record
      (FUN_088f5ba4 with the record's costume, same builder the Friend Card ghost uses) -> for Sora it was skipped,
      so a "use my own character" (kind 5) Sora entry kept stale/zero ghost data;
    FUN_08a6c3ec (entry panel): if 1 and kind 5 -> shows the record's level / mastered state -> for Sora nothing.
Fix (21 words in place, same function, no cave, no new calls): owner 33 -> 1, every other owner exactly as before
(1..34 range check, then FUN_088cb1ec). Other FUN_088cb1ec callers (ghost/card code) are NOT changed.

  new code:  addiu sp,-16 ; sw ra ; ori a1,0x21 ; beq a0,a1,RET ; _ori v0,1 ; blez a0,RET ; _or v0,0 ;
             slti a1,a0,0x23 ; beq a1,zero,RET ; _lui a1,0x89d ; lw a2,0x712c(a1) ; or a1,a0 ; jal 0x088cb1ec ;
             _addiu a0,a2,0xf58 ; sltu v0,zero,v0 ; RET: lw ra ; jr ra ; _addiu sp,16 ; nop x3

Guards: plain ELF; the function is the clean EBOOT words (also checked against dumps/extracted/EBOOT.elf) or ours; GET_RECORD (FUN_088cb164) is not the
clean code (= spot33_save applied, so Sora's record really exists); exactly the two known OVL_MENU_APP jal sites call
it; refuses an ISO PPSSPP has open; never the clean dump. --dry writes nothing, --rollback restores the clean words.

  python3 -I spot33_oqrecord.py ISO [--dry] [--rollback]
"""
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mips_asm import asm  # noqa: E402
from roster_patch import MENU_FILEOFF, MENU_ISO_SECTOR, MENU_VADDR  # noqa: E402

EBOOT_ISO = 560 * 0x800
FUNC_VA, NWORDS = 0x089293DC, 21
CLEAN = [0x27BDFFF0, 0xAFBF0000, 0x1880000C, 0x28850023, 0x10A0000A, 0x00000000, 0x3C05089D, 0x8CA6712C,
         0x00802825, 0x0E232C7B, 0x24C40F58, 0x14400005, 0x00000000, 0x10000004, 0x00001025, 0x10000002,
         0x00001025, 0x34020001, 0x8FBF0000, 0x03E00008, 0x27BD0010]
GET_RECORD_VA = 0x088CB164
CLEAN_ELF = os.path.join(HERE, '../../dumps/extracted/EBOOT.elf')
JAL = 0x0C000000 | (FUNC_VA >> 2) & 0x3FFFFFF
MENU_SIZE = 1556096
SRC = """
    addiu sp,sp,-0x10
    sw ra,0x0(sp)
    ori a1,zero,0x21
    beq a0,a1,RET
    ori v0,zero,0x1
    blez a0,RET
    or v0,zero,zero
    slti a1,a0,0x23
    beq a1,zero,RET
    lui a1,0x89d
    lw a2,0x712c(a1)
    or a1,a0,zero
    jal 0x088cb1ec
    addiu a0,a2,0xf58
    sltu v0,zero,v0
RET:
    lw ra,0x0(sp)
    jr ra
    addiu sp,sp,0x10
    nop
    nop
    nop
"""


def eboot_off(va):
    return EBOOT_ISO + 0x1018 + va - 0x8804040


def words(f, off, n):
    f.seek(off)
    return list(struct.unpack('<%dI' % n, f.read(4 * n)))


def find_callers(f):
    """jal FUNC_VA sites in OVL_MENU_APP (whole file) -> list of VAs"""
    f.seek(MENU_ISO_SECTOR * 0x800)
    d = f.read(MENU_SIZE)
    out = []
    for o in range(0, len(d) - 3, 4):
        if struct.unpack_from('<I', d, o)[0] == JAL:
            out.append(o - MENU_FILEOFF + MENU_VADDR)
    return out


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
    ours = asm(SRC.strip().splitlines(), FUNC_VA)
    assert len(ours) == NWORDS, len(ours)
    with open(iso, 'rb') as f:
        f.seek(EBOOT_ISO)
        assert f.read(4) == b'\x7fELF', 'EBOOT is not the plain ELF (run eboot_plain first)'
        cur = words(f, eboot_off(FUNC_VA), NWORDS)
        gr = words(f, eboot_off(GET_RECORD_VA), 34)
        callers = find_callers(f)
    assert cur in (CLEAN, ours), 'FUN_089293dc is neither clean nor ours - stop'
    with open(CLEAN_ELF, 'rb') as c:
        gr_clean = words(c, 0x1018 + GET_RECORD_VA - 0x8804040, 34)
        assert words(c, 0x1018 + FUNC_VA - 0x8804040, NWORDS) == CLEAN, 'clean EBOOT.elf mismatch'
    assert gr != gr_clean, 'FUN_088cb164 is still the clean code (spot33_save missing) - stop'
    assert len(callers) == 2 and all(0x08A50000 <= c < 0x08A70000 for c in callers), \
        'unexpected OVL_MENU_APP callers of FUN_089293dc: %s - stop' % [hex(c) for c in callers]
    want = CLEAN if rollback else ours
    state = 'already' if cur == want else ('to write (dry)' if dry else 'written')
    print('EBOOT FUN_089293dc (Original Quest "has record"): owner 33 -> %s: %s; menu callers %s' % (
        'record check (vanilla)' if rollback else 'yes', state, [hex(c) for c in callers]))
    if cur != want and not dry:
        with open(iso, 'r+b') as f:
            f.seek(eboot_off(FUNC_VA))
            f.write(struct.pack('<%dI' % NWORDS, *want))
        with open(iso, 'rb') as f:
            assert words(f, eboot_off(FUNC_VA), NWORDS) == want
    print('dry run, nothing written' if dry else 'done')


if __name__ == '__main__':
    main()
