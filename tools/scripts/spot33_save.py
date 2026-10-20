"""Give roster spot #33 its own saved fighter record (replaces the "equip" and "learned" cheats).

What it changes (all in place in the ISO; the ISO must already have the plain, decrypted EBOOT of test 20):

EBOOT (code + data):
  1. FUN_088cb3b4 (owner -> record index) rewritten as a short loop that keeps a0/a1 intact.
     Its freed tail (0x088cb3e4..) holds the rest of the "blank record" path.
  2. FUN_088cb164 (get a fighter's record) rewritten: owner 33 -> record at save base + 0xF58 + 0x38040
     (= save blob + 0x38090, inside friend card slot 24, which is now never used). Base is always the real
     save, like the old blank record was always the same global. If that record's owner byte isn't 33 yet,
     it is set up with FUN_088cbbb4(record, 33) = reset + owner + level 1 (chrl) + default preset (eqpm).
  3. Friend card limit 25 -> 24 (FUN_088f520c init loop, FUN_088f526c add) so card slot 24 stays free.
  4. Default preset table 0x089CB7E8[33] = 250.

system.bin (inside general_archive/main/main.bin):
  5. eqpm: new preset 250 for owner 33 = Cloud's preset 7 with his ability indexes mapped to #33's rows
     (Cloud idx 0, 7, 10, 13 -> 0, 1, 2, 3; ablt rows 617-620). The game copies eqpm into a buffer with
     room for exactly one more preset (0x09B59AF8..0x09B5DA00).
  6. chrl: new learning table for owner 33 = Cloud's table without his own (0x0Dxx) abilities.

Usage: python3 -I spot33_save.py ISO     (writes to ISO!)
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, mpk_member, package_entry, read_at  # noqa: E402
from mips_asm import asm  # noqa: E402
from pkg_put import PACKAGE_INFO_ISO_SECTOR  # noqa: E402

EBOOT_ISO = 560 * SECTOR                        # PSP_GAME/SYSDIR/EBOOT.BIN (plain ELF since test 20)
OWNER, PRESET = 33, 250
CLOUD, CLOUD_PRESET = 13, 7
IDX_MAP = {0: 0, 7: 1, 10: 2, 13: 3}             # Cloud ability index -> #33 index (ablt rows 617-620)


def elf_off(va):
    return 0x1018 + va - 0x8804040


LOOKUP = """
    lui t0,0x89d
    addiu t0,t0,-0x4368
    li v0,0x0
L:
    lb t1,0x0(t0)
    beq t1,a0,R
    _addiu t0,t0,0x1
    slti t1,v0,0x1e
    bne t1,zero,L
    _addiu v0,v0,0x1
    li v0,-0x1
R:
    jr ra
    _nop
    bne a0,zero,BL2
    _nop
    sw t0,-0x508(a1)
    jal 0x088cb9e8
    _addiu a0,a1,-0x504
BL2:
    lui v0,0x9af
    j 0x088cb1cc
    _addiu v0,v0,-0x504
    nop
"""

GET_RECORD = """
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
    lb t3,0x0(v0)
    beq t3,t2,END
    _move s0,v0
    move a0,v0
    jal 0x088cbbb4
    _li a1,0x21
    b END
    _move v0,s0
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

# (address, original word, new word or assembly, length in words)
CODE = [
    (0x088cb3b4, 0x27bdfff0, LOOKUP, 21),
    (0x088cb164, 0x27bdfff0, GET_RECORD, 34),
    (0x088f523c, 0x2a440019, 0x2a440018, 1),   # slti a0,s2,0x19 -> 0x18
    (0x088f52a0, 0x28860019, 0x28860018, 1),   # slti a2,a0,0x19 -> 0x18
    (0x089cb7e8 + 4 * OWNER, 0xFFFFFFFF, PRESET & 0xFFFFFFFF, 1),
]


def patch_eboot(f):
    for va, orig, new, n in CODE:
        words = asm(new.strip().split('\n'), va) if isinstance(new, str) else [new]
        assert len(words) == n, (hex(va), len(words), n)
        pos = EBOOT_ISO + elf_off(va)
        cur = struct.unpack('<%dI' % n, read_at(f, pos, 4 * n))
        if list(cur) == words:
            print('EBOOT %08x: already patched' % va)
            continue
        if cur[0] != orig:
            sys.exit('EBOOT %08x: unexpected %08x (wrong ISO?)' % (va, cur[0]))
        f.seek(pos)
        f.write(struct.pack('<%dI' % n, *words))
        print('EBOOT %08x: %d word(s) written' % (va, n))


def arc_split(data):
    count, = struct.unpack_from('<I', data, 4)
    out = []
    for i in range(count):
        one, tag, off, size = struct.unpack_from('<I4sII', data, 16 + i * 16)
        out.append([one, tag, data[off:off + size]])
    return data[:16], out


def arc_join(head, chunks):
    """Chunks start 4-byte aligned, like the original; no padding after the last one."""
    table, body, pos = b'', b'', 16 + 16 * len(chunks)
    for i, (one, tag, blob) in enumerate(chunks):
        table += struct.pack('<I4sII', one, tag, pos, len(blob))
        pad = (-len(blob)) % 4 if i < len(chunks) - 1 else 0
        body += blob + b'\0' * pad
        pos += len(blob) + pad
    return head + table + body


def new_eqpm(eqpm):
    one, count = struct.unpack_from('<II', eqpm, 0)
    rows = [eqpm[8 + i * 126:8 + (i + 1) * 126] for i in range(count)]
    keys = [struct.unpack_from('<h', r)[0] for r in rows]
    if PRESET in keys:
        return None
    src = bytearray(rows[keys.index(CLOUD_PRESET)])
    assert struct.unpack_from('<h', src, 2)[0] == CLOUD
    struct.pack_into('<hh', src, 0, PRESET, OWNER)
    for s in range(3):                          # 3 sets x 0x1E bytes of ability indexes (0xFF = empty)
        for k in range(0x1E):
            b = src[4 + s * 0x1E + k]
            if b != 0xFF:
                src[4 + s * 0x1E + k] = IDX_MAP.get(b, 0xFF)
    rows.append(bytes(src))
    rows.sort(key=lambda r: struct.unpack_from('<h', r)[0])
    return struct.pack('<II', one, count + 1) + b''.join(rows)


def new_chrl(chrl):
    count, = struct.unpack_from('<I', chrl, 8)
    ents = [list(struct.unpack_from('<IIII', chrl, 16 + i * 16)) for i in range(count)]
    if any(e[0] == OWNER for e in ents):
        return None
    cloud = next(e for e in ents if e[0] == CLOUD)
    rows = bytearray(chrl[cloud[2]:cloud[2] + cloud[1] * 8])
    for r in range(cloud[1]):
        for k in range(3):
            v, = struct.unpack_from('<H', rows, r * 8 + 2 + k * 2)
            if v >> 8 == CLOUD:
                struct.pack_into('<H', rows, r * 8 + 2 + k * 2, 0xFFFF)
    for e in ents:
        e[2] += 16
    ents.append([OWNER, cloud[1], len(chrl) + 16, 0])
    head = bytearray(chrl[:16])
    struct.pack_into('<I', head, 8, count + 1)
    return (bytes(head) + b''.join(struct.pack('<IIII', *e) for e in ents)
            + chrl[16 + count * 16:] + bytes(rows))


def patch_mainbin(f, iso):
    info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
    pkg = PACKAGE_ISO_SECTOR * SECTOR
    off, size = package_entry(info, 'general_archive/main/main.bin')
    main = read_at(f, pkg + off, size)
    sys_off, sys_size = mpk_member(f, pkg + off, 'system.bin')
    sys_off -= pkg + off
    head, chunks = arc_split(main[sys_off:sys_off + sys_size])
    changed = False
    for c in chunks:
        if c[1] == b'eqpm':
            n = new_eqpm(c[2])
            if n:
                print('eqpm: preset %d added (%d -> %d bytes)' % (PRESET, len(c[2]), len(n)))
                assert len(n) <= 0x09B5DA00 - 0x09B59AF8, 'eqpm buffer too small'
                c[2], changed = n, True
        if c[1] == b'chrl':
            n = new_chrl(c[2])
            if n:
                print('chrl: table for owner %d added (%d -> %d bytes)' % (OWNER, len(c[2]), len(n)))
                c[2], changed = n, True
    if not changed:
        print('main.bin: already patched')
        return
    sysbin = arc_join(head, chunks)
    delta = -(-(len(sysbin) - sys_size) // 16) * 16
    count, = struct.unpack_from('<I', main, 8)
    out = bytearray(main[:sys_off]) + sysbin + b'\0' * (delta - (len(sysbin) - sys_size))
    out += main[sys_off + sys_size:]
    for i in range(count):
        noff, doff, msize, z = struct.unpack_from('<IIII', out, 16 + i * 16)
        if doff == sys_off:
            struct.pack_into('<I', out, 16 + i * 16 + 8, len(sysbin))
        elif doff > sys_off:
            struct.pack_into('<I', out, 16 + i * 16 + 4, doff + delta)
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, 'main.bin')
        open(p, 'wb').write(out)
        f.flush()
        subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso,
                        'general_archive/main/main.bin', p], check=True)


def main():
    iso = sys.argv[1]
    with open(iso, 'r+b') as f:
        patch_eboot(f)
        patch_mainbin(f, iso)


if __name__ == '__main__':
    main()
