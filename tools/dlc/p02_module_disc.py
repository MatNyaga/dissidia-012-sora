"""P0.2/P0.3 probe disc: the game loads and STARTS our own code module EXTRA.PRX at boot.

Phase-0 throwaway test disc only (never a release base). docs/PHASE0-DLC-PLAN.md, notes/dlc-phase0.md (P0.2/P0.3).

EBOOT (plain ELF at ISO sector 560), two in-place changes, no free code room used:
 1) Module loader FUN_0886eebc (54 words, 0x0886EEBC-0x0886EF93; only callers: libsuppreacc 0x0886F284 and libfont
    0x08881A94, both pass a2 = 0) re-compiled by hand into 41 words with the SAME behaviour for those callers
    (build path with FUN_08863048, opt {size 0x14, position = (a2 == 1)}, sceKernelLoadModule retried while <= 0,
    sceKernelStartModule, unload + return 0 if start fails, else return the uid) plus one new mode:
    a2 = 2 -> ONE load attempt; a failed load returns the error (<= 0) instead of retrying forever (the vanilla
    loop would hang the boot on a missing/bad file). The 13 freed words hold STUB (9) + "extra.prx" (3) + 1 spare.
 2) Boot init FUN_0893354c: 0x0893361C  jal FUN_08862650 (NP-DRM module + licensee key, no arguments)
    -> jal STUB 0x0886EF60:  loader(_, "extra.prx", 2)  then tail-jump to FUN_08862650 (original call order kept:
    libfont, libsuppreacc, EXTRA.PRX, NP-DRM key). Missing EXTRA.PRX / load error / start error -> boot goes on.
ISO9660: EXTRA.PRX (tools/dlc/probe/extra.prx) appended at the ISO end, record inserted (sorted) into
  /PSP_GAME/USRDIR/DATA/MODULE (1 sector, 218 B used), PVD volume size updated. The loader opens
  disc0:/PSP_GAME/USRDIR/data/module/extra.prx (ISO9660 lookups are case-insensitive).

  tools/dlc/pspenv.sh make -C tools/dlc/probe           # build extra.prx first
  python3 -I tools/dlc/p02_module_disc.py [--dry] [--no-sha] [--no-file] [SRC] [OUT]
     SRC default dumps/ULUS10566-test338-voicesloud.iso, OUT default dumps/ULUS10566-p02-module.iso
     --no-file: negative control, EBOOT patch only (OUT default dumps/ULUS10566-p02-nofile.iso) -> the boot must
     reach the title exactly like test338 (proves a missing/failed EXTRA.PRX is harmless).
Guards: refuses OUT == SRC, OUT == dumps/ULUS10566.iso or an OUT not named ULUS10566-p02*; SRC must hold the vanilla
loader + site words (asserted word by word); an existing OUT must be a p02 disc (vanilla or patched words) or it is
not touched; copies SRC -> OUT (cp --reflink=auto) only when OUT is missing; --dry writes nothing. Re-runnable: a
second run changes nothing; a rebuilt extra.prx replaces the file data (in place when it fits, else re-appended).
"""
import hashlib
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../..'))
sys.path.insert(0, os.path.join(ROOT, 'tools/scripts'))
from mips_asm import asm  # noqa: E402

SECTOR = 0x800
EBOOT_SECTOR = 560
MODULE_DIR = ['PSP_GAME', 'USRDIR', 'DATA', 'MODULE']
DISC_NAME = b'EXTRA.PRX'
DONOR = b'LIBFONT.PRX'
PRX = os.path.join(HERE, 'probe/extra.prx')

LOADER, LOADER_END = 0x0886EEBC, 0x0886EF94          # FUN_0886eebc, 54 words
STUB = 0x0886EF60                                    # = LOADER + 41 words
SITE, SITE_OLD = 0x0893361C, 0x0E218994              # jal 0x08862650 (in FUN_0893354c)
SITE_CTX = {0x08933614: 0x0E21BC8F,                  # jal 0x0886f23c  (libsuppreacc + save sfo)
            0x08933618: 0x8C845FB4,                  # lw a0,0x5fb4(a0)
            0x08933620: 0x00000000,                  # nop (delay slot of the site)
            0x08933628: 0x0E216FFF}                  # jal 0x0885bffc
CALLERS = {0x0886F27C: 0x34060000, 0x0886F284: 0x0E21BBAF,   # li a2,0 / jal loader (libsuppreacc)
           0x08881A8C: 0x34060000, 0x08881A94: 0x0E21BBAF}   # li a2,0 / jal loader (libfont)
PATH_FN, LOADMOD, STARTMOD, UNLOADMOD, DRMKEY = 0x08863048, 0x089C57D8, 0x089C57C8, 0x089C57C0, 0x08862650

# vanilla FUN_0886eebc (clean dump == test338), 54 words
LOADER_OLD = [
    0x27BDFED0, 0xAFB00114, 0x30D000FF, 0x00A02025, 0xAFB10118, 0xAFB2011C, 0xAFBF0120, 0x00802825,
    0x02008825, 0x0E218C12, 0x03A02025, 0x27B00100, 0x34120014, 0x02002025, 0x00002825, 0x0E24D60A,
    0x34060014, 0xAFB20100, 0x3A240001, 0xAFA00104, 0x2C840001, 0xA3A40110, 0x03A02025, 0x00002825,
    0x0E2715F6, 0x02003025, 0x00408825, 0x1A200005, 0x00000000, 0x1E200005, 0x00000000, 0x10000010,
    0x02201025, 0x1000FFF4, 0x00000000, 0x02202025, 0x00002825, 0x00003025, 0x00003825, 0x0E2715F2,
    0x00004025, 0x04400003, 0x00000000, 0x10000004, 0x02201025, 0x0E2715F0, 0x02202025, 0x00001025,
    0x8FB00114, 0x8FB10118, 0x8FB2011C, 0x8FBF0120, 0x03E00008, 0x27BD0130]

SRC_ASM = """
LOADER:                         # int loader(heap_unused, const char *name, char mode)
    addiu sp,sp,-304
    sw s1,280(sp)
    sw ra,288(sp)
    andi s1,a2,0xff
    sw s1,284(sp)               # mode: 0 = vanilla (retry while load <= 0), 2 = one try (EXTRA.PRX)
    jal 0x%(PATH_FN)08x         # sp = "disc0:/PSP_GAME/USRDIR/data/module/<name>" (a1 = name)
    move a0,sp
    li v0,0x14
    sw v0,256(sp)               # SceKernelLMOption.size = 0x14
    sw zero,260(sp)             # mpidtext
    sw zero,264(sp)             # mpiddata
    sw zero,268(sp)             # flags
    xori a0,s1,1
    sltiu a0,a0,1
    sw a0,272(sp)               # position = (mode == 1), access = 0, reserved = 0
RETRY:
    move a0,sp
    move a1,zero
    jal 0x%(LOADMOD)08x         # sceKernelLoadModule(path, 0, &opt)
    addiu a2,sp,256
    bgtz v0,START
    move s1,v0
    lw v0,284(sp)
    beq v0,zero,RETRY           # vanilla callers: retry forever (original behaviour)
    nop
    b OUT
    move v0,s1                  # mode != 0: give up, return the error (<= 0)
START:
    move a0,s1
    move a1,zero
    move a2,zero
    move a3,zero
    jal 0x%(STARTMOD)08x        # sceKernelStartModule(uid, 0, 0, 0, 0)
    move t0,zero
    bgez v0,OUT
    move v0,s1                  # started: return the uid
    jal 0x%(UNLOADMOD)08x       # start failed: sceKernelUnloadModule(uid), return 0
    move a0,s1
    move v0,zero
OUT:
    lw s1,280(sp)
    lw ra,288(sp)
    jr ra
    addiu sp,sp,304
STUB:                           # boot init 0x0893361C jal here instead of FUN_08862650 (no arguments)
    addiu sp,sp,-16
    sw ra,0(sp)
    lui a1,0x%(NAME_HI)04x
    addiu a1,a1,%(NAME_LO)d
    jal LOADER
    li a2,2                     # one try; result ignored (missing/failed module = boot continues)
    lw ra,0(sp)
    j 0x%(DRMKEY)08x            # original call
    addiu sp,sp,16
NAME:
    .word 0x72747865            # "extr"
    .word 0x72702E61            # "a.pr"
    .word 0x00000078            # "x\\0\\0\\0"
    .word 0                     # spare (54th word)
"""


def eboot_off(va):
    return EBOOT_SECTOR * SECTOR + 0x1018 + va - 0x08804040


def build_loader():
    name = STUB + 9 * 4
    hi, lo = (name + 0x8000) >> 16, name - (((name + 0x8000) >> 16) << 16)
    src = SRC_ASM % dict(PATH_FN=PATH_FN, LOADMOD=LOADMOD, STARTMOD=STARTMOD, UNLOADMOD=UNLOADMOD,
                         DRMKEY=DRMKEY, NAME_HI=hi, NAME_LO=lo)
    words = asm(src.splitlines(), LOADER)
    assert len(words) == len(LOADER_OLD) == (LOADER_END - LOADER) // 4, len(words)
    assert LOADER + 41 * 4 == STUB and words[41] == 0x27BDFFF0      # STUB label where the site jumps
    assert struct.pack('<3I', *words[50:53]) == b'extra.prx\0\0\0'
    return words


def jal(t):
    return 3 << 26 | (t >> 2) & 0x3FFFFFF


def read_at(f, off, n):
    f.seek(off)
    return f.read(n)


def words_at(f, va, n):
    return list(struct.unpack('<%dI' % n, read_at(f, eboot_off(va), 4 * n)))


# ---------- ISO9660 (from tools/scripts/spot33_music.py) ----------
def set_both32(buf, at, v):
    struct.pack_into('<I', buf, at, v)
    struct.pack_into('>I', buf, at + 4, v)


def rec_name(r):
    return bytes(r[33:33 + r[32]])


def read_dir(f, sector, size):
    raw = read_at(f, sector * SECTOR, size)
    recs = []
    for s in range(0, size, SECTOR):
        o = s
        while o < s + SECTOR and raw[o]:
            recs.append(bytes(raw[o:o + raw[o]]))
            o += raw[o]
        assert not any(raw[o:s + SECTOR]), 'junk after the last record in a directory sector'
    return recs


def pack_dir(recs, size):
    out, cur = bytearray(), bytearray()
    for r in recs:
        if len(cur) + len(r) > SECTOR:
            out += cur + b'\0' * (SECTOR - len(cur))
            cur = bytearray()
        cur += r
    out += cur + b'\0' * (SECTOR - len(cur))
    return bytes(out) if len(out) <= size else None


def find_dir(f, path):
    pvd = read_at(f, 16 * SECTOR, SECTOR)
    assert pvd[1:6] == b'CD001' and pvd[0] == 1
    rec = pvd[156:156 + 34]
    for part in path:
        sec, size = struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0]
        rec = next((r for r in read_dir(f, sec, size) if rec_name(r) == part.encode() and r[25] & 2), None)
        assert rec, 'directory %s not found' % part
    return struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0]


def new_record(donor, name, sector, size):
    nl = len(name)
    head = 33 + nl + (33 + nl) % 2
    su = donor[33 + donor[32] + (33 + donor[32]) % 2:]
    r = bytearray(head + len(su))
    r[1:33] = donor[1:33]
    r[0], r[32] = len(r), nl
    set_both32(r, 2, sector)
    set_both32(r, 10, size)
    r[33:33 + nl] = name
    r[head:] = su
    return bytes(r)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def disc_state(f, new_loader):
    """'vanilla' | 'patched' | None (anything else)."""
    lw = words_at(f, LOADER, len(LOADER_OLD))
    site = words_at(f, SITE, 1)[0]
    ctx_ok = all(words_at(f, va, 1)[0] == w for va, w in {**SITE_CTX, **CALLERS}.items())
    if not ctx_ok:
        return None
    if lw == LOADER_OLD and site == SITE_OLD:
        return 'vanilla'
    if lw == new_loader and site == jal(STUB):
        return 'patched'
    return None


def plan_file(f, prx):
    dsec, dsize = find_dir(f, MODULE_DIR)
    recs = read_dir(f, dsec, dsize)
    f.seek(0, 2)
    iso_end = f.tell()
    vol, = struct.unpack_from('<I', read_at(f, 16 * SECTOR + 80, 4))
    assert vol * SECTOR == iso_end, 'PVD volume size != ISO size'
    names = [rec_name(r) for r in recs]
    assert names[:2] == [b'\0', b'\1'] and DONOR in names, names
    cur = next((r for r in recs if rec_name(r) == DISC_NAME), None)
    if cur is not None:
        s, z = struct.unpack_from('<I', cur, 2)[0], struct.unpack_from('<I', cur, 10)[0]
        if z == len(prx) and read_at(f, s * SECTOR, z) == prx:
            return dict(action='same', sector=s, dsec=dsec)
        if -(-len(prx) // SECTOR) <= -(-z // SECTOR):
            pos, end = s * SECTOR, iso_end                         # overwrite in place (fits the old sectors)
        else:
            pos = end = -(-iso_end // SECTOR) * SECTOR              # append again
        newrecs = [new_record(cur, DISC_NAME, pos // SECTOR, len(prx)) if rec_name(r) == DISC_NAME else r
                   for r in recs]
        action = 'replace'
    else:
        pos = end = -(-iso_end // SECTOR) * SECTOR
        r = new_record(recs[names.index(DONOR)], DISC_NAME, pos // SECTOR, len(prx))
        i = next(i for i in range(2, len(recs) + 1) if i == len(recs) or rec_name(recs[i]) > DISC_NAME)
        newrecs = recs[:i] + [r] + recs[i:]
        action = 'add'
    data = pack_dir(newrecs, dsize)
    assert data is not None, 'MODULE directory full'
    new_end = max(iso_end, pos + -(-len(prx) // SECTOR) * SECTOR)
    return dict(action=action, dsec=dsec, data=data, pos=pos, iso_end=iso_end, end=end, new_end=new_end,
                used=sum(map(len, newrecs)))


def main():
    dry = '--dry' in sys.argv
    nosha = '--no-sha' in sys.argv
    nofile = '--no-file' in sys.argv                        # negative control: EBOOT patch only, no EXTRA.PRX
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    src = os.path.abspath(args[0] if args else os.path.join(ROOT, 'dumps/ULUS10566-test338-voicesloud.iso'))
    out = os.path.abspath(args[1] if len(args) > 1 else os.path.join(
        ROOT, 'dumps/ULUS10566-p02-nofile.iso' if nofile else 'dumps/ULUS10566-p02-module.iso'))
    clean = os.path.join(ROOT, 'dumps/ULUS10566.iso')
    if out in (src, clean) or not os.path.basename(out).startswith('ULUS10566-p02'):
        sys.exit('refusing to write %s (must be a new ULUS10566-p02*.iso, not the source or the clean dump)' % out)
    if not os.path.exists(PRX):
        sys.exit('%s missing: run  tools/dlc/pspenv.sh make -C tools/dlc/probe' % PRX)
    prx = open(PRX, 'rb').read()
    assert prx[:4] == b'\x7fELF' and struct.unpack_from('<H', prx, 16)[0] == 0xFFA0, 'extra.prx is not a plain PRX'
    new_loader = build_loader()
    print('EXTRA.PRX %d B sha256 %s' % (len(prx), hashlib.sha256(prx).hexdigest()))
    with open(src, 'rb') as f:
        if disc_state(f, new_loader) != 'vanilla':
            sys.exit('source %s: loader/site words are not the expected vanilla ones' % src)
    if os.path.exists(out):
        with open(out, 'rb') as f:
            st = disc_state(f, new_loader)
        if st is None:
            sys.exit('%s exists and is not a p02 disc; not touching it' % out)
        print('%s exists (%s)' % (out, st))
    elif dry:
        print('[dry] would copy %s -> %s' % (src, out))
    else:
        subprocess.run(['cp', '--reflink=auto', src, out], check=True)
        print('copied %s -> %s' % (src, out))
    target = out if os.path.exists(out) else src           # dry run without OUT: plan against SRC
    with open(target, 'rb') as f:
        st = disc_state(f, new_loader)
        fp = plan_file(f, prx)
    if nofile:
        if fp['action'] == 'same' or fp['action'] == 'replace':
            sys.exit('--no-file but %s already has EXTRA.PRX' % target)
        fp = dict(action='skip')
    print('EBOOT: loader 0x%08X-0x%08X %s; site 0x%08X jal 0x%08X -> jal STUB 0x%08X' % (
        LOADER, LOADER_END - 1, 'already patched' if st == 'patched' else 'vanilla -> rewrite (54 words)',
        SITE, DRMKEY, STUB))
    if fp['action'] == 'skip':
        print('MODULE/EXTRA.PRX: NOT added (--no-file negative control: boot must go on without it)')
    elif fp['action'] == 'same':
        print('MODULE/EXTRA.PRX: already on disc, identical (sector %d)' % fp['sector'])
    else:
        print('MODULE/EXTRA.PRX: %s at sector %d; directory sector %d use %d/2048 B; ISO %d -> %d bytes' % (
            fp['action'], fp['pos'] // SECTOR, fp['dsec'], fp['used'], fp['iso_end'], fp['new_end']))
    if dry:
        print('[dry] nothing written')
        return
    with open(out, 'r+b') as f:
        assert disc_state(f, new_loader) in ('vanilla', 'patched')
        if st != 'patched':
            f.seek(eboot_off(LOADER))
            f.write(struct.pack('<%dI' % len(new_loader), *new_loader))
            f.seek(eboot_off(SITE))
            f.write(struct.pack('<I', jal(STUB)))
        if fp['action'] not in ('same', 'skip'):
            f.seek(fp['iso_end'])
            f.write(b'\0' * (fp['end'] - fp['iso_end']))
            f.seek(fp['pos'])
            f.write(prx + b'\0' * ((-len(prx)) % SECTOR))
            f.seek(fp['dsec'] * SECTOR)
            f.write(fp['data'])
            pv = bytearray(8)
            set_both32(pv, 0, fp['new_end'] // SECTOR)
            f.seek(16 * SECTOR + 80)
            f.write(pv)
    with open(out, 'rb') as f:
        assert disc_state(f, new_loader) == 'patched'
        again = plan_file(f, prx)
        assert again['action'] == ('add' if nofile else 'same'), again
        f.seek(0, 2)
        size = f.tell()
    print('%s: done (%d bytes)' % (out, size))
    if not nosha:
        print('sha256 %s' % sha256_file(out))


if __name__ == '__main__':
    main()
