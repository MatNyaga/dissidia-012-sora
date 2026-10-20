"""Give roster spot #33 a row in system.bin/amas, so Customization -> Abilities opens instead of freezing.

amas ("AMAS"): 16-byte header (u32 count at +8), count x 16-byte rows (u32 owner, u32 entry count, u32 data offset
from the chunk start, 0), data = 8-byte entries (u16 ability id, u16 1, u16 ability id, u16 0xFFFF; ability id =
owner << 8 | index). Owners 1-32 have rows (no 23); #33 had none -> the menu (FUN_08ad0d48, menu overlay) looked up
NULL and looped over garbage. Same layout as chrl (see spot33_save.py).
New row for 33 = Cloud's entries without Cloud's own (0x0Dxx) abilities, appended at the end.

Usage: python3 -I spot33_amas.py ISO     (writes to ISO; idempotent)
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, mpk_member, package_entry, read_at  # noqa: E402
from pkg_put import PACKAGE_INFO_ISO_SECTOR  # noqa: E402
from spot33_save import arc_join, arc_split  # noqa: E402

OWNER, CLOUD = 33, 13


def new_amas(amas):
    count, = struct.unpack_from('<I', amas, 8)
    ents = [list(struct.unpack_from('<IIII', amas, 16 + i * 16)) for i in range(count)]
    if any(e[0] == OWNER for e in ents):
        return None
    cloud = next(e for e in ents if e[0] == CLOUD)
    rows = []
    for r in range(cloud[1]):
        a, one, b, end = struct.unpack_from('<HHHH', amas, cloud[2] + r * 8)
        if a >> 8 == CLOUD or b >> 8 == CLOUD:
            continue
        rows.append(struct.pack('<HHHH', a, one, b, end))
    for e in ents:
        e[2] += 16
    ents.append([OWNER, len(rows), len(amas) + 16, 0])
    ents.sort(key=lambda e: e[0])                       # looked up by binary search on the owner
    head = bytearray(amas[:16])
    struct.pack_into('<I', head, 8, count + 1)
    return (bytes(head) + b''.join(struct.pack('<IIII', *e) for e in ents)
            + amas[16 + count * 16:] + b''.join(rows)), len(rows)


def main():
    iso = sys.argv[1]
    with open(iso, 'r+b') as f:
        info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
        pkg = PACKAGE_ISO_SECTOR * SECTOR
        off, size = package_entry(info, 'general_archive/main/main.bin')
        main_bin = read_at(f, pkg + off, size)
        sys_off, sys_size = mpk_member(f, pkg + off, 'system.bin')
        sys_off -= pkg + off
    head, chunks = arc_split(main_bin[sys_off:sys_off + sys_size])
    for c in chunks:
        if c[1] == b'amas':
            res = new_amas(c[2])
            if not res:
                print('amas: owner %d already has a row' % OWNER)
                return
            print('amas: row for owner %d added (%d entries; %d -> %d bytes)' % (OWNER, res[1], len(c[2]),
                                                                                  len(res[0])))
            c[2] = res[0]
    sysbin = arc_join(head, chunks)
    delta = -(-(len(sysbin) - sys_size) // 16) * 16
    count, = struct.unpack_from('<I', main_bin, 8)
    out = bytearray(main_bin[:sys_off]) + sysbin + b'\0' * (delta - (len(sysbin) - sys_size))
    out += main_bin[sys_off + sys_size:]
    for i in range(count):
        noff, doff, msize, z = struct.unpack_from('<IIII', out, 16 + i * 16)
        if doff == sys_off:
            struct.pack_into('<I', out, 16 + i * 16 + 8, len(sysbin))
        elif doff > sys_off:
            struct.pack_into('<I', out, 16 + i * 16 + 4, doff + delta)
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, 'main.bin')
        open(p, 'wb').write(out)
        subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso,
                        'general_archive/main/main.bin', p], check=True)


if __name__ == '__main__':
    main()
