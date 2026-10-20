"""Roster edits, written in place inside a Dissidia 012 ISO (ULUS10566). See notes/roster.md.

Owners are the character numbers used everywhere (ablt +1, chrp +0, objentry +6): Cloud = 13, Aerith = 33.

Usage:
  python3 -I roster_patch.py ISO copy-chrp SRC_OWNER DST_OWNER
        system.bin/chrp: DST's 144-byte row becomes a copy of SRC's (byte 0, the owner, stays DST).
  python3 -I roster_patch.py ISO copy-objentry SRC_OWNER SRC_MODEL DST_OWNER DST_MODEL
        objentry.bin: every DST row using model DST_MODEL copies bytes +2..+0x44 from the SRC row with
        model SRC_MODEL and the same player byte (+7) and kind byte (+8); +0 (object id) and +6 (owner) stay.
  python3 -I roster_patch.py ISO select-swap OLD_OWNER NEW_OWNER
        select screen list (OVL_MENU_APP.ELF, 0x08B0119C): OLD becomes NEW. (Not the Quick Battle grid.)
  python3 -I roster_patch.py ISO set-model OWNER OLD_MODEL NEW_MODEL
        objentry.bin: rows of OWNER whose model (+0x34) is OLD_MODEL get NEW_MODEL (file = obj/<model>.objx).
  python3 -I roster_patch.py ISO set-name OWNER OLD_NAME NEW_NAME
        objentry.bin: rows of OWNER named OLD_NAME (+0x24) get NEW_NAME. Model/costume/portrait files are
        obj/<NAME>.gmo, .cosx, .exex and menu/JP/battle/chara_image/<NAME>.gim.
  python3 -I roster_patch.py ISO qb-row OLD_OWNER NEW_OWNER PICTURE GAME
        Quick Battle grid table (OVL_MENU_APP.ELF, 0x08A864D0, 12-byte rows: u16 picture, u16 picture,
        u16 game logo, u16 owner, i32 owner): the OLD row becomes NEW. Grid shows rows whose owner is unlocked.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, arc_chunk, mpk_member, package_entry, read_at  # noqa: E402

MENU_ISO_SECTOR = 185056          # OVL_MENU_APP.ELF, from `isoinfo -l`
MENU_VADDR, MENU_FILEOFF = 0x089DD4C0, 0x54
SELECT_LIST = 0x08B0119C          # u32 owners, -1 terminated (read by FUN_08aff218)
QB_TABLE = 0x08A864D0             # Quick Battle grid rows (returned by FUN_08a85ecc)
HERE = os.path.dirname(os.path.abspath(__file__))


def main_member(f, name):
    info = open(os.path.join(HERE, '../../dumps/extracted/PACKAGE_INFO.BIN'), 'rb').read()
    off, _ = package_entry(info, 'general_archive/main/main.bin')
    return mpk_member(f, PACKAGE_ISO_SECTOR * SECTOR + off, name)


def copy_chrp(f, src, dst):
    sysbin, _ = main_member(f, 'system.bin')
    chrp, _ = arc_chunk(f, sysbin, 'chrp')
    _, count = struct.unpack('<II', read_at(f, chrp, 8))
    rows = {read_at(f, chrp + 8 + i * 144, 1)[0]: chrp + 8 + i * 144 for i in range(count)}
    row = bytearray(read_at(f, rows[src], 144))
    row[0] = dst
    f.seek(rows[dst])
    f.write(row)
    print('chrp owner %d <- copy of owner %d (%s)' % (dst, src, row[0x74:0x84].split(b'\0')[0].decode()))


def copy_objentry(f, src, src_model, dst, dst_model):
    obj, _ = main_member(f, 'objentry.bin')
    _, count = struct.unpack('<II', read_at(f, obj, 8))
    rows = [(obj + 8 + i * 68, bytearray(read_at(f, obj + 8 + i * 68, 68))) for i in range(count)]
    model = lambda r: r[0x34:0x44].split(b'\0')[0].decode()  # noqa: E731
    for at, r in rows:
        if r[6] != dst or model(r) != dst_model:
            continue
        tpl = [t for _, t in rows if t[6] == src and model(t) == src_model and t[7] == r[7] and t[8] == r[8]]
        if not tpl:
            print('  no template for %s (player %d kind %d), left alone' % (r[0x24:0x34].split(b'\0')[0].decode(), r[7], r[8]))
            continue
        new = bytearray(r[:2]) + tpl[0][2:]
        new[6] = dst
        f.seek(at)
        f.write(new)
        print('  %s -> copy of %s' % (r[0x24:0x34].split(b'\0')[0].decode(), tpl[0][0x24:0x34].split(b'\0')[0].decode()))


def select_swap(f, old, new):
    base = MENU_ISO_SECTOR * SECTOR + SELECT_LIST - MENU_VADDR + MENU_FILEOFF
    for i in range(40):
        v, = struct.unpack('<i', read_at(f, base + i * 4, 4))
        if v == -1:
            break
        if v == old:
            f.seek(base + i * 4)
            f.write(struct.pack('<i', new))
            print('select list slot %d: owner %d -> %d' % (i, old, new))
            return
    sys.exit('owner %d not in the select list' % old)


def set_model(f, owner, old, new):
    obj, _ = main_member(f, 'objentry.bin')
    _, count = struct.unpack('<II', read_at(f, obj, 8))
    for i in range(count):
        at = obj + 8 + i * 68
        r = read_at(f, at, 68)
        if r[6] == owner and r[0x34:0x44].split(b'\0')[0].decode() == old:
            f.seek(at + 0x34)
            f.write(new.encode().ljust(16, b'\0'))
            print('  %s: model %s -> %s' % (r[0x24:0x34].split(b'\0')[0].decode(), old, new))


def set_name(f, owner, old, new):
    obj, _ = main_member(f, 'objentry.bin')
    _, count = struct.unpack('<II', read_at(f, obj, 8))
    n = 0
    for i in range(count):
        at = obj + 8 + i * 68
        r = read_at(f, at, 68)
        if r[6] == owner and r[0x24:0x34].split(b'\0')[0].decode() == old and n == 0:
            f.seek(at + 0x24)
            f.write(new.encode().ljust(16, b'\0'))
            print('  row %d (obj id %d): name %s -> %s' % (i, struct.unpack_from('<H', r, 0)[0], old, new))
            n += 1
    if not n:
        sys.exit('no row of owner %d named %s' % (owner, old))


def qb_row(f, old, new, picture, game):
    base = MENU_ISO_SECTOR * SECTOR + QB_TABLE - MENU_VADDR + MENU_FILEOFF
    for i in range(40):
        row = read_at(f, base + i * 12, 12)
        owner, = struct.unpack_from('<i', row, 8)
        if owner == old:
            f.seek(base + i * 12)
            f.write(struct.pack('<4Hi', picture, picture, game, new, new))
            print('quick battle row %d: owner %d -> %d (picture %d, game %d)' % (i, old, new, picture, game))
            return
        if owner <= 0:
            break
    sys.exit('owner %d not in the quick battle table' % old)


def main():
    iso, cmd = sys.argv[1], sys.argv[2]
    a = sys.argv[3:]
    with open(iso, 'r+b') as f:
        if cmd == 'copy-chrp':
            copy_chrp(f, int(a[0]), int(a[1]))
        elif cmd == 'copy-objentry':
            copy_objentry(f, int(a[0]), a[1], int(a[2]), a[3])
        elif cmd == 'set-model':
            set_model(f, int(a[0]), a[1], a[2])
        elif cmd == 'set-name':
            set_name(f, int(a[0]), a[1], a[2])
        elif cmd == 'qb-row':
            qb_row(f, int(a[0]), int(a[1]), int(a[2]), int(a[3]))
        elif cmd == 'select-swap':
            select_swap(f, int(a[0]), int(a[1]))
        else:
            sys.exit(__doc__)


if __name__ == '__main__':
    main()
