"""Give roster spot #33 a row in system.bin/grwp, so battles with Sora load on a real PSP / PS Vita (2026-10-19).

grwp (Max CP growth): u32 3, u32 count (32), count x 0x1C-byte rows (u16 index, u16 owner, ..., +0x14 s16 base,
+0x16 s16 growth; Max CP = base + growth * level / 100). Owners 1..32 have rows; #33 had none.
Battle setup FUN_088b5670 -> FUN_088c0a20(owner) -> FUN_088c09ac (linear scan on the owner) returns NULL for 33 ->
FUN_088c0864 `lh a1,0x16(a0)` reads address 0x16. PPSSPP ignores that read by default (Max CP 0, silently); real
hardware crashes (Vita error C1-2858-3 while loading any battle with Sora, player or CPU). Reproduced in PPSSPP with
IgnoreBadMemAccess = False (notes/dlc-phase1.md "Vita test"). The menus use another path (Max CP 379 at Lv42 shown).
RAM: the chunk is copied to 0x09B68B58 (FUN_088c0a44); the next referenced buffer is 0x09B69260 -> room for 64 rows.
New row = Cloud's row (owner 13) with index 32 / owner 33, appended (lookup is a linear scan, order free).

Guards: refuses the clean dump; refuses an ISO PPSSPP has open; checks the chunk header (u32 3, size 8 + n * 0x1C,
owners unique, n < 64). Re-runnable ("already"). --dry writes nothing.
Usage: python3 -I spot33_grwp.py ISO [--dry]
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

OWNER, CLOUD, ROW, MAX_ROWS = 33, 13, 0x1C, 64
CLEAN = os.path.realpath(os.path.join(HERE, '..', '..', 'dumps', 'ULUS10566.iso'))


def rows_of(grwp):
    ver, n = struct.unpack_from('<II', grwp, 0)
    assert ver == 3 and len(grwp) >= 8 + n * ROW and n < MAX_ROWS, 'unexpected grwp header %d/%d/%d' % (ver, n, len(grwp))
    rows = [grwp[8 + i * ROW:8 + (i + 1) * ROW] for i in range(n)]
    owners = [struct.unpack_from('<H', r, 2)[0] for r in rows]
    assert len(set(owners)) == n, 'duplicate owners in grwp'
    return rows, owners


def new_grwp(grwp):
    rows, owners = rows_of(grwp)
    if OWNER in owners:
        return None
    cloud = rows[owners.index(CLOUD)]
    row = struct.pack('<HH', len(rows), OWNER) + cloud[4:]
    head = bytearray(grwp[:8])
    struct.pack_into('<I', head, 4, len(rows) + 1)
    return bytes(head) + b''.join(rows) + row + grwp[8 + len(rows) * ROW:], row


def iso_open_in_ppsspp(iso):
    real = os.path.realpath(iso)
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            for fd in os.listdir('/proc/%s/fd' % pid):
                if os.path.realpath('/proc/%s/fd/%s' % (pid, fd)) == real:
                    return True
        except OSError:
            continue
    return False


def main():
    iso = sys.argv[1]
    dry = '--dry' in sys.argv[2:]
    if os.path.realpath(iso) == CLEAN:
        sys.exit('refusing the clean dump')
    if not dry and iso_open_in_ppsspp(iso):
        sys.exit('refusing: the ISO is open in another program (PPSSPP?)')
    with open(iso, 'rb') as f:
        info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
        pkg = PACKAGE_ISO_SECTOR * SECTOR
        off, size = package_entry(info, 'general_archive/main/main.bin')
        main_bin = read_at(f, pkg + off, size)
        sys_off, sys_size = mpk_member(f, pkg + off, 'system.bin')
        sys_off -= pkg + off
    head, chunks = arc_split(main_bin[sys_off:sys_off + sys_size])
    hit = [c for c in chunks if c[1] == b'grwp']
    assert len(hit) == 1, 'no single grwp chunk in system.bin'
    res = new_grwp(hit[0][2])
    if not res:
        print('grwp: owner %d already has a row' % OWNER)
        return
    print('grwp: row for owner %d = %s (%d -> %d bytes)%s' % (OWNER, res[1].hex(' ', 2), len(hit[0][2]), len(res[0]),
                                                              ' [dry]' if dry else ''))
    if dry:
        return
    hit[0][2] = res[0]
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
