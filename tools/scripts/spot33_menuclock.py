"""Keep the CPU at 333 MHz in the menus too (test354, 2026-10-20; notes/dlc-phase1.md "Vita menu lag").

Why: on Mat's PS Vita (Adrenaline, "CPU 333") the Sora disc's menus felt "slightly slow, like low fps" next to
the untouched disc; battles were fine. PPSSPP A/B showed the same CPU, GE and file work per menu frame on both discs,
so the difference is on the hardware/firmware side. The game sets its own clock per scene:
  FUN_088e0ad8 (scene flag u16 +6 bit 0) -> FUN_08860e3c = scePower_469989ad(333, 333, 166)   battles
                                         -> FUN_08860e78 = scePower_469989ad(222, 222, 111)   menus / title
(other callers 0x0888C4C8, 0x0888DFA4, 0x088F68E8, 0x0891813C; menu overlay 0x08A20AE8, 0x08A6CCA4; FUN_08860eb0
restores the previous one). So menus run at 222 MHz CPU / 111 MHz bus by design, and the fill-heavy menu screens
are the ones that suffer if a CFW "CPU 333" override reaches one disc and not the other. Fix: FUN_08860e78 passes
333/333/166 as well -> the game never drops the clock (cost: battery only). The state words 0x089D5E80/84 keep their
meaning (0 = "menu clock" requested); nothing else reads them.

Runtime (PPSSPP, test354 first try): between boot and the main menu the game calls the setter NOT AT ALL, so the
title and menus run at whatever clock the firmware/CFW left (PPSSPP default 222); FUN_08860e78 only runs on later
scene changes (e.g. back from a battle). Boot init FUN_0893354c starts with FUN_08860df8, which only reads the current
clock into the state words. So the boot function also becomes "set 333": its first two words tail-jump to the 333
setter FUN_08860e3c (which sets the state words itself and returns to FUN_0893354c); the rest of FUN_08860df8 is dead.

Patch (EBOOT plain ELF, 5 words; the new li words are byte copies of FUN_08860e3c's own):
  0x08860DF8 27BDFFF0 addiu sp,sp,-16 -> 0A21838F j 0x08860E3C   (boot: FUN_08860df8 -> set 333/333/166)
  0x08860DFC AFBF0000 sw ra,0(sp)     -> 00000000 nop            (delay slot; no stack frame any more)
  0x08860E90 340400DE li a0,222 -> 3404014D li a0,333            (menus: FUN_08860e78)
  0x08860E94 340500DE li a1,222 -> 3405014D li a1,333
  0x08860EA0 3406006F li a2,111 -> 340600A6 li a2,166
Guards: refuses the clean dump and an ISO another program (PPSSPP) has open; EBOOT must be the plain ELF; every other
word of FUN_08860df8 + FUN_08860e78 and the 333 setter FUN_08860e3c's immediates must be the clean ones; each patched word must be the
original or our value. Re-runnable ("already"); --dry writes nothing; --rollback puts 222/222/111 back.
Wired into build_sora.sh after spot33_grwp, before spot33_installfix (RC3, 2026-10-20; Vita check on test354 = better).

  python3 -I spot33_menuclock.py ISO [--dry] [--rollback]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLEAN = os.path.realpath(os.path.join(HERE, '..', '..', 'dumps', 'ULUS10566.iso'))
EBOOT_ISO = 560 * 0x800

# FUN_08860e78, clean words (dumps/extracted/EBOOT.elf)
FUNC_VA = 0x08860E78
FUNC_CLEAN = [0x27BDFFF0, 0x3C04089D, 0x8C855E80, 0x3C06089D, 0xACC55E84, 0xAC805E80, 0x340400DE, 0x340500DE,
              0xAFBF0000, 0x0E271600, 0x3406006F, 0x8FBF0000, 0x03E00008, 0x27BD0010]
# FUN_08860df8 (boot clock read), clean words
BOOT_VA = 0x08860DF8
BOOT_CLEAN = [0x27BDFFF0, 0xAFBF0000, 0x0E271606, 0x00000000, 0x284600DF, 0x3C05089D, 0x10C00004, 0x3C04089D,
              0xACA05E80, 0x10000004, 0xAC805E84, 0x34060001, 0xACA65E80, 0xAC865E84, 0x8FBF0000, 0x03E00008,
              0x27BD0010]
PATCH = {0x08860DF8: (0x27BDFFF0, 0x0A21838F), 0x08860DFC: (0xAFBF0000, 0x00000000),
         0x08860E90: (0x340400DE, 0x3404014D), 0x08860E94: (0x340500DE, 0x3405014D),
         0x08860EA0: (0x3406006F, 0x340600A6)}
# FUN_08860e3c's own 333/333/166 words: ours are byte-identical copies of them
SETTER_333 = {0x08860E58: 0x3404014D, 0x08860E5C: 0x3405014D, 0x08860E68: 0x340600A6}


def eboot_off(va):
    return EBOOT_ISO + 0x1018 + va - 0x8804040


def word(f, va):
    f.seek(eboot_off(va))
    return struct.unpack('<I', f.read(4))[0]


def iso_open_elsewhere(iso):
    real = os.path.realpath(iso)
    for pid in os.listdir('/proc'):
        if not pid.isdigit() or int(pid) == os.getpid():
            continue
        try:
            for fd in os.listdir('/proc/%s/fd' % pid):
                if os.path.realpath('/proc/%s/fd/%s' % (pid, fd)) == real:
                    return True
        except OSError:
            continue
    return False


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 1:
        sys.exit(__doc__)
    iso = args[0]
    dry, rollback = '--dry' in sys.argv, '--rollback' in sys.argv
    if os.path.realpath(iso) == CLEAN or os.path.basename(iso) == 'ULUS10566.iso':
        sys.exit('refusing the clean dump')
    if not dry and iso_open_elsewhere(iso):
        sys.exit('refusing: the ISO is open in another program (PPSSPP?)')
    with open(iso, 'rb') as f:
        f.seek(EBOOT_ISO)
        if f.read(4) != b'\x7fELF':
            sys.exit('EBOOT is not the plain ELF (run eboot_plain first) - stop')
        for i, want in enumerate(BOOT_CLEAN + FUNC_CLEAN):
            va = (BOOT_VA + 4 * i) if i < len(BOOT_CLEAN) else (FUNC_VA + 4 * (i - len(BOOT_CLEAN)))
            got = word(f, va)
            ok = (got == want) or (va in PATCH and got == PATCH[va][1])
            if not ok:
                sys.exit('0x%08X = %08X, expected %08X (or ours) - FUN_08860df8/e78 is not the clean code, stop' % (va, got, want))
        for va, want in SETTER_333.items():
            if word(f, va) != want:
                sys.exit('333 setter FUN_08860e3c word 0x%08X = %08X, expected %08X - stop' % (va, word(f, va), want))
        cur = {va: word(f, va) for va in PATCH}
    todo = {}
    for va, (old, new) in PATCH.items():
        want = old if rollback else new
        state = 'already' if cur[va] == want else ('dry' if dry else 'write')
        print('EBOOT 0x%08X %08X -> %08X  %s' % (va, cur[va], want, state))
        if cur[va] != want:
            todo[va] = want
    if not todo:
        print('already: menus keep %s' % ('222/222/111 (vanilla)' if rollback else '333/333/166'))
        return
    if dry:
        print('dry run, nothing written')
        return
    with open(iso, 'r+b') as f:
        for va, w in todo.items():
            f.seek(eboot_off(va))
            f.write(struct.pack('<I', w))
    with open(iso, 'rb') as f:
        for va, w in todo.items():
            assert word(f, va) == w, 'read-back failed at 0x%08X' % va
    print('done: %s' % ('vanilla clock code back (boot read, menus 222/222/111)' if rollback else 'boot + menus set 333/333/166'))


if __name__ == '__main__':
    main()
