"""P0.6 probe disc: the game's own DLC loader reads PLAIN (unencrypted) files from the memory stick.

Phase-0 throwaway test disc only (never a release base). docs/PHASE0-DLC-PLAN.md, notes/dlc-phase0.md (P0.6).

Why a vanilla disc rejects a plain DLC file on a real PSP (EBOOT VA = ELF off - 0x1018 + 0x08804040, ISO sector 560):
every DLC file is opened with flags 0x40000001 (PSP_O_RDONLY | PSP_O_NPDRM) and, right after the open,
sceNpDrmEdataSetupKey(fd) (import stub 0x089C5D50, NID 0x08D98894) must return >= 0, otherwise the file is closed and
treated as missing. A plain file has no EDAT/PGD header, so the real NP-DRM driver fails the setup -> "no DLC".
(PPSSPP 1.20.4 is lenient: SetupKey returns 0 for a non-EDAT file and reads it plain, so on PPSSPP the vanilla disc
already accepts a plain file; this patch is what a real PSP needs.)

7 EBOOT words, plain-only (a real EDAT would then be read raw = garbage; keep EDATs off the stick with this disc):
  open flags  FUN_0886453c (sync open, vtable +0xC4)   0x08864570 lui s3,0x4000 -> lui s3,0  (flags 0x40000001 -> 1)
              FUN_0886465c (async open, vtable +0xDC)  0x088646A4 lui s6,0x4000 -> lui s6,0  (same; next word adds 1)
  key setup   jal sceNpDrmEdataSetupKey -> move v0,zero (= "setup OK"; the delay-slot word then runs as a plain
              instruction, it only loads a0) at
              0x08861DA0 FUN_08861d7c  DLC list loader (obj/bgm/bgm-text open callback)
              0x08863A9C FUN_08863a4c  async read-by-name open callback (only when the DRM byte +0x149 == 1)
              0x08863F88 FUN_08863f24  sync read-by-name (ms0 costume gmo/cosx/exex when objentry +9 != 0)
              0x0889FE38, 0x088A0204   DLC BGM streaming (DRM path only)
  These are ALL calls of the stub in EBOOT + the 3 overlays; every one sits behind the DLC/DRM flag, so disc reads are
  untouched. SetLicenseeKey (0x08862664) is left alone (harmless without EDATs).

  python3 -I tools/dlc/p06_plaindlc_disc.py [--dry] [--no-sha] [SRC] [OUT]
     SRC default dumps/ULUS10566-test338-voicesloud.iso, OUT default dumps/ULUS10566-p06-plaindlc.iso
Guards: refuses OUT == SRC, OUT == dumps/ULUS10566.iso or an OUT not named ULUS10566-p06*; SRC must hold the vanilla
words + context (asserted word by word); an existing OUT must be a p06 disc (vanilla or patched words) or it is not
touched; copies SRC -> OUT (cp --reflink=auto) only when OUT is missing; --dry writes nothing. Re-runnable.
"""
import hashlib
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../..'))
SECTOR = 0x800
EBOOT_SECTOR = 560
MOVE_V0_ZERO = 0x00001025
JAL_SETUPKEY = 0x0E271754                     # jal 0x089C5D50 (sceNpDrmEdataSetupKey stub)

# va: (vanilla word, patched word)
PATCH = {
    0x08864570: (0x3C134000, 0x3C130000),     # lui s3,0x4000 -> lui s3,0   (FUN_0886453c open flags)
    0x088646A4: (0x3C164000, 0x3C160000),     # lui s6,0x4000 -> lui s6,0   (FUN_0886465c open flags)
    0x08861DA0: (JAL_SETUPKEY, MOVE_V0_ZERO),
    0x08863A9C: (JAL_SETUPKEY, MOVE_V0_ZERO),
    0x08863F88: (JAL_SETUPKEY, MOVE_V0_ZERO),
    0x0889FE38: (JAL_SETUPKEY, MOVE_V0_ZERO),
    0x088A0204: (JAL_SETUPKEY, MOVE_V0_ZERO),
}
# unchanged neighbours that must match (structure guard)
CONTEXT = {
    0x08864568: 0x16920003, 0x0886456C: 0x00A08025, 0x08864574: 0x26730001,   # bne s4,s2 / move s0,a1 / addiu s3,s3,1
    0x0886458C: 0x0E2717AA,                                                   # jal sceIoOpen 0x089C5EA8
    0x0886469C: 0x16F50003, 0x088646A0: 0x00E08025, 0x088646A8: 0x26D60001,   # bne s7,s5 / move s0,a3 / addiu s6,s6,1
    0x088646C0: 0x0E271794,                                                   # jal sceIoOpenAsync 0x089C5E50
    0x08861DA4: 0x8E040004, 0x08861DA8: 0x0440000E,                           # lw a0,4(s0) / bltz v0
    0x08863AA0: 0x8E24001C, 0x08863AA4: 0x04410002,                           # lw a0,28(s1) / bgez v0
    0x08863F8C: 0x02802025, 0x08863F90: 0x0441000A,                           # move a0,s4 / bgez v0
    0x0889FE3C: 0x8C846C3C, 0x0889FE40: 0x0441000A,                           # lw a0,0x6c3c(a0) / bgez v0
    0x088A0208: 0x00000000, 0x088A020C: 0x04410009,                           # nop / bgez v0
    0x08862664: 0x0E271756,                                                   # jal SetLicenseeKey (kept)
}


def eboot_off(va):
    return EBOOT_SECTOR * SECTOR + 0x1018 + va - 0x08804040


def word(f, va):
    f.seek(eboot_off(va))
    return struct.unpack('<I', f.read(4))[0]


def disc_state(f):
    """'vanilla' | 'patched' | None (anything else)."""
    f.seek(EBOOT_SECTOR * SECTOR)
    if f.read(4) != b'\x7fELF':
        return None
    if any(word(f, va) != w for va, w in CONTEXT.items()):
        return None
    cur = [word(f, va) for va in PATCH]
    if cur == [v[0] for v in PATCH.values()]:
        return 'vanilla'
    if cur == [v[1] for v in PATCH.values()]:
        return 'patched'
    return None


def setupkey_calls(f):
    """Every jal to the SetupKey stub left in the EBOOT image (should be [] after patching)."""
    f.seek(EBOOT_SECTOR * SECTOR + 0x1018)
    img = f.read(1938304)
    return [0x08804040 + i for i in range(0, len(img), 4) if struct.unpack_from('<I', img, i)[0] == JAL_SETUPKEY]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def main():
    dry = '--dry' in sys.argv
    nosha = '--no-sha' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    src = os.path.abspath(args[0] if args else os.path.join(ROOT, 'dumps/ULUS10566-test338-voicesloud.iso'))
    out = os.path.abspath(args[1] if len(args) > 1 else os.path.join(ROOT, 'dumps/ULUS10566-p06-plaindlc.iso'))
    clean = os.path.join(ROOT, 'dumps/ULUS10566.iso')
    if out in (src, clean) or not os.path.basename(out).startswith('ULUS10566-p06'):
        sys.exit('refusing to write %s (must be a new ULUS10566-p06*.iso, not the source or the clean dump)' % out)
    with open(src, 'rb') as f:
        if disc_state(f) != 'vanilla':
            sys.exit('source %s: DLC open/key-setup words are not the expected vanilla ones' % src)
        calls = setupkey_calls(f)
    assert calls == sorted(va for va, (old, _) in PATCH.items() if old == JAL_SETUPKEY), [hex(c) for c in calls]
    print('source %s: vanilla; SetupKey calls %s' % (src, ' '.join('0x%08X' % c for c in calls)))
    if os.path.exists(out):
        with open(out, 'rb') as f:
            st = disc_state(f)
        if st is None:
            sys.exit('%s exists and is not a p06 disc; not touching it' % out)
        print('%s exists (%s)' % (out, st))
    elif dry:
        st = 'vanilla'
        print('[dry] would copy %s -> %s' % (src, out))
    else:
        subprocess.run(['cp', '--reflink=auto', src, out], check=True)
        print('copied %s -> %s' % (src, out))
        st = 'vanilla'
    for va, (old, new) in PATCH.items():
        print('  0x%08X  %08X -> %08X%s' % (va, old, new, '  (already)' if st == 'patched' else ''))
    if dry:
        print('[dry] nothing written')
        return
    if st != 'patched':
        with open(out, 'r+b') as f:
            assert disc_state(f) == 'vanilla'
            for va, (_, new) in PATCH.items():
                f.seek(eboot_off(va))
                f.write(struct.pack('<I', new))
    with open(out, 'rb') as f:
        assert disc_state(f) == 'patched'
        assert setupkey_calls(f) == []
        f.seek(0, 2)
        size = f.tell()
    print('%s: done (%d bytes)' % (out, size))
    if not nosha:
        print('sha256 %s' % sha256_file(out))


if __name__ == '__main__':
    main()
