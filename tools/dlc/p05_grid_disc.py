"""P0.5 runtime probe disc: make the character-select grid show an 8th cell in the bottom row (slot 33).

Phase-0 throwaway test disc only (never a release base). One overlay word, nothing else:
  menu overlay FUN_08a84fd4 (grid builder), mode-0 branch
  0x08A85184  bne a0,a1,0x08A8522C (14850029)  ->  nop (00000000)
  = "add the -3 cell (icon_delete) even when obj+0xC != 1". In every mode-0 grid (Quick Battle player side,
  main-menu character select variants 1/3, ...) the list then holds 32 fighters + random(-2) + (-3) = 34 entries
  -> bottom row = slots 26..33 = 8 cells, the 8th at locator (316, 230) (column 9). The delay-slot instruction
  (addu s7,s6,s6 at 0x08A85188) still runs, so the list bookkeeping is unchanged.
What it proves at runtime: the 34th cell sprite draws at column 9, the cursor reaches it (and wraps), nothing else in
the screen moves. Do NOT press X on the new cell (a -3 entry in a mode-0 grid is not a fighter; hover only).

  python3 -I tools/dlc/p05_grid_disc.py [--dry] [SRC] [OUT]
     SRC default dumps/ULUS10566-test338-voicesloud.iso, OUT default dumps/ULUS10566-p05-grid.iso
Guards: refuses OUT == SRC, OUT == dumps/ULUS10566.iso, or an OUT that exists and is not already a p05 disc;
copies SRC -> OUT (cp --reflink=auto) only when OUT is missing; asserts the original word (or the patched word on
re-run) and the surrounding words before writing; --dry writes nothing. Re-runnable.
"""
import os
import struct
import subprocess
import sys

SECTOR = 0x800
MENU_SECTOR, MENU_VA, MENU_OFF = 185056, 0x089DD4C0, 0x54
SITE = 0x08A85184
OLD, NEW = 0x14850029, 0x00000000
CONTEXT = {0x08A85180: 0x8E64000C,   # lw a0,12(s3)      (obj+0xC)
           0x08A85188: 0x02D6B821,   # addu s7,s6,s6     (delay slot, still executed)
           0x08A8518C: 0x8E640028,   # lw a0,40(s3)
           0x08A85190: 0x2405FFFD}   # addiu a1,zero,-3
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))


def iso_off(va):
    return MENU_SECTOR * SECTOR + va - MENU_VA + MENU_OFF


def word(f, va):
    f.seek(iso_off(va))
    return struct.unpack('<I', f.read(4))[0]


def main():
    args = [a for a in sys.argv[1:] if a != '--dry']
    dry = '--dry' in sys.argv
    src = os.path.abspath(args[0] if args else os.path.join(ROOT, 'dumps/ULUS10566-test338-voicesloud.iso'))
    out = os.path.abspath(args[1] if len(args) > 1 else os.path.join(ROOT, 'dumps/ULUS10566-p05-grid.iso'))
    clean = os.path.join(ROOT, 'dumps/ULUS10566.iso')
    if out in (src, clean) or not os.path.basename(out).startswith('ULUS10566-p05'):
        sys.exit('refusing to write %s (must be a new ULUS10566-p05*.iso, not the source or the clean dump)' % out)
    with open(src, 'rb') as f:
        w = word(f, SITE)
        ctx = {va: word(f, va) for va in CONTEXT}
    if w != OLD or ctx != CONTEXT:
        sys.exit('source %s: site word %08X / context %s not the expected original' % (src, w, ctx))
    if os.path.exists(out):
        with open(out, 'rb') as f:
            w2 = word(f, SITE)
            ctx2 = {va: word(f, va) for va in CONTEXT}
        if ctx2 != CONTEXT or w2 not in (OLD, NEW):
            sys.exit('%s exists and is not a p05 grid disc (word %08X); not touching it' % (out, w2))
        if w2 == NEW:
            print('%s: already patched (0x%08X = %08X)' % (out, SITE, NEW))
            return
    elif dry:
        print('[dry] would copy %s -> %s' % (src, out))
    else:
        subprocess.run(['cp', '--reflink=auto', src, out], check=True)
        print('copied %s -> %s' % (src, out))
    if dry:
        print('[dry] would write 0x%08X: %08X -> %08X at ISO offset 0x%X' % (SITE, OLD, NEW, iso_off(SITE)))
        return
    with open(out, 'r+b') as f:
        assert word(f, SITE) == OLD
        f.seek(iso_off(SITE))
        f.write(struct.pack('<I', NEW))
    with open(out, 'rb') as f:
        assert word(f, SITE) == NEW
    print('%s: 0x%08X %08X -> %08X (grid builder always adds the -3 cell in mode 0)' % (out, SITE, OLD, NEW))


if __name__ == '__main__':
    main()
