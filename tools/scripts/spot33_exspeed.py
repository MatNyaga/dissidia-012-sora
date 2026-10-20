"""EX-only run speed for Sora (owner 33): while he is in EX Mode and plays his free-run motion, his horizontal run speed
is multiplied by EXSPEED_MULT (default 1.40 = Mat 2026-10-17 "40% faster"; allowed 1.0-1.5). Everybody else, normal mode, attacks, dodges, air
moves, jumps, the animation rate (+0x3bc) and the shared spec row are untouched. notes/ex-equipment.md §1.

Where the run speed comes from (static, battle overlay; Codex Q-20261016-CODEX-003 lead, checked here):
  FUN_08b2d2cc(fighter) is called once per input update from FUN_08b36d2c (its only caller, jal at 0x08b372a0) and
  computes fighter+0xbc = spec+0x18 (or +0x1c when +0x384 bit 0) * fighter+0x3d4 (gear/ability move-speed factor)
  * fighter+0xbc (fresh stick magnitude: w of (+0xb0 + input vector +0x550)), stores it at 0x08b2d380, then (when
  FUN_088374b0) multiplies by spec+0x64.
Hook (one 2-word site, battle overlay, in place - the overlay keeps its size):
  0x08b2d380  swc1 f12,0xbc(s0) / jal 0x088374b0   ->   jal EXRUN / swc1 f12,0xbc(s0)   (store runs in the delay slot)
  EXRUN (EBOOT, proven-dead function 0x089a8b14-0x089a8f0c, notes/ex-burst-controller.md §21; sub-range
  0x089a8b24-0x089a8b94 owned by THIS script; the first 4 words stay original = probe hook):
      owner byte *(*(s0+0x2f8)+6) == 33  and  motion u16 s0+0x180 == 2 (free run, grounded only)  and
      FUN_08b34378(s0) (native EX Mode predicate, also false during an EX Burst)  ->  +0xbc *= EXSPEED_MULT
      then tail-jumps to FUN_088374b0(s0) with the original return address, so the rest of FUN_08b2d2cc is unchanged.
  The multiply is applied to the freshly computed value every call (never compounded: the native code rebuilds +0xbc
  from the stick before each call), so leaving EX Mode or stopping the run returns to the native value at once.

  python3 -I spot33_exspeed.py ISO [--dry]
  env EXSPEED=0         -> exact rollback (site + EBOOT sub-range back to the clean bytes)
  env EXSPEED_MULT=1.15 -> other multiplier (1.0 .. 1.5)
Re-runnable: a second run changes nothing; another multiplier replaces only the 2 constant words.
"""
import hashlib
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mips_asm import asm  # noqa: E402

SECTOR = 2048
EBOOT_ISO = 560 * SECTOR                        # PSP_GAME/SYSDIR/EBOOT.BIN (plain ELF)
OVL_SECTOR, OVL_BASE, OVL_DATA = 185824, 0x089DD4C0, 0x54     # OVL_BATTLE_APP.ELF
DATA_DIR_SECTOR = 27
CLEAN_EBOOT = os.path.join(HERE, '../../dumps/extracted/EBOOT.elf')
CLEAN_OVL = os.path.join(HERE, '../../dumps/extracted/OVL_BATTLE_APP.ELF')
CLEAN_ISO = os.path.realpath(os.path.join(HERE, '../../dumps/ULUS10566.iso'))

DEAD_LO, DEAD_HI = 0x089A8B14, 0x089A8F0C       # whole dead function (probe test272p PASS)
DEAD_SHA = '1345b9e14727260640786f74c5a0da3f87f96bc420433447e145e240f01dd10e'
LO, HI = 0x089A8B24, 0x089A8B94                 # THIS script's sub-range (28 words)
SITE = 0x08B2D380
SITE_ORIG = (0xE60C00BC, 0x0E20DD2C)            # swc1 f12,0xbc(s0) / jal 0x088374b0
EX_PRED, AFTER = 0x08B34378, 0x088374B0

ON = os.environ.get('EXSPEED', '1') == '1'
MULT = float(os.environ.get('EXSPEED_MULT', '1.40'))


def elf_off(va):
    return 0x1018 + va - 0x8804040


def mul_s(fd, fs, ft):
    return 0x11 << 26 | 16 << 21 | ft << 16 | fs << 11 | fd << 6 | 2


def plan(mult):
    assert 1.0 <= mult <= 1.5, 'EXSPEED_MULT must be 1.0 .. 1.5'
    bits, = struct.unpack('<I', struct.pack('<f', mult))
    src = """
EXRUN:
    lw t0,0x2f8(s0)
    beq t0,zero,ER_OUT
    nop
    lbu t0,0x6(t0)
    xori t0,t0,0x21
    bne t0,zero,ER_OUT
    lhu t0,0x180(s0)
    xori t0,t0,0x2
    bne t0,zero,ER_OUT
    nop
    addiu sp,sp,-0x10
    sw ra,0x0(sp)
    jal 0x%08x
    move a0,s0
    lw ra,0x0(sp)
    beq v0,zero,ER_OUT
    addiu sp,sp,0x10
    lui t0,0x%x
    ori t0,t0,0x%x
    mtc1 t0,f1
    lwc1 f0,0xbc(s0)
    .word 0x%08x
    swc1 f0,0xbc(s0)
ER_OUT:
    j 0x%08x
    move a0,s0
""" % (EX_PRED, bits >> 16, bits & 0xFFFF, mul_s(0, 0, 1), AFTER)
    words = asm(src.strip().split('\n'), LO)
    assert LO + 4 * len(words) <= HI, 'EXRUN does not fit its sub-range'
    code = b''.join(struct.pack('<I', w) for w in words)
    site = asm(['jal 0x%08x' % LO, 'swc1 f12,0xbc(s0)'], SITE)
    return code, site, len(words)


def ovl_extent(f):
    f.seek(DATA_DIR_SECTOR * SECTOR)
    d = f.read(SECTOR)
    k = 0
    while k < len(d) and d[k]:
        n = d[k + 32]
        if d[k + 33:k + 33 + n].split(b';')[0] == b'OVL_BATTLE_APP.ELF':
            return struct.unpack_from('<I', d, k + 2)[0]
        k += d[k]
    sys.exit('OVL_BATTLE_APP.ELF not found')


def main():
    iso = sys.argv[1]
    dry = '--dry' in sys.argv
    if os.path.realpath(iso) == CLEAN_ISO:
        sys.exit('refusing to write the clean dump')
    clean_eb = open(CLEAN_EBOOT, 'rb').read()
    dead = clean_eb[elf_off(DEAD_LO):elf_off(DEAD_HI)]
    assert hashlib.sha256(dead).hexdigest() == DEAD_SHA, 'dumps/extracted/EBOOT.elf is not the clean one'
    clean = clean_eb[elf_off(LO):elf_off(HI)]
    clean_ovl = open(CLEAN_OVL, 'rb').read()
    assert struct.unpack_from('<2I', clean_ovl, OVL_DATA + SITE - OVL_BASE) == SITE_ORIG
    code, site, n = plan(MULT)
    mine = code + clean[len(code):]
    print('EXSPEED %s, multiplier %.4f: EXRUN %d words at 0x%08x (sub-range 0x%08x-0x%08x)' %
          ('ON' if ON else 'off (rollback)', MULT, n, LO, LO, HI))
    with open(iso, 'rb' if dry else 'r+b') as f:
        assert ovl_extent(f) == OVL_SECTOR, 'battle overlay moved'
        # --- check everything before any write
        f.seek(EBOOT_ISO + elf_off(DEAD_LO))
        head = f.read(LO - DEAD_LO)
        assert head == dead[:LO - DEAD_LO], 'dead function head 0x%08x changed: not ours' % DEAD_LO
        f.seek(EBOOT_ISO + elf_off(LO))
        cur = f.read(HI - LO)
        any_mult = cur[:17 * 4] == mine[:17 * 4] and cur[19 * 4:] == mine[19 * 4:]      # ours, other constant
        assert cur == clean or any_mult, 'EBOOT 0x%08x-0x%08x is neither original nor EXRUN: not ours' % (LO, HI)
        so = OVL_SECTOR * SECTOR + OVL_DATA + SITE - OVL_BASE
        f.seek(so)
        cs = struct.unpack('<2I', f.read(8))
        assert cs in (SITE_ORIG, tuple(site)), 'site 0x%08x: unexpected %08x %08x' % (SITE, cs[0], cs[1])
        want_r, want_s = (mine, tuple(site)) if ON else (clean, SITE_ORIG)
        print('EBOOT sub-range: %s -> %s' % ('original' if cur == clean else 'EXRUN', 'EXRUN' if ON else 'original'))
        print('site 0x%08x: %08x %08x -> %08x %08x' % (SITE, cs[0], cs[1], want_s[0], want_s[1]))
        if cur == want_r and cs == want_s:
            print('already done: no change')
            return
        if dry:
            print('--dry: nothing written')
            return
        if cur != want_r:
            f.seek(EBOOT_ISO + elf_off(LO))
            f.write(want_r)
        if cs != want_s:
            f.seek(so)
            f.write(struct.pack('<2I', *want_s))
        print('written')


if __name__ == '__main__':
    main()
