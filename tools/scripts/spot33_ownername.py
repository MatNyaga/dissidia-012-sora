"""Sora's NAME wherever a menu shows a character name by owner number (Mat, 2026-10-17: Records battle-time entry
without a name; Friend Card Settings icon / Ghost character picker without a name). notes/unlocks.md §4.

The game turns an owner number into a "name index" into the 63-entry character-name list that several text files
carry (WoL 0 .. Jecht 19, Chaos 20, Shantotto 21, Gabranth 22, manikins 23-44, Kain 45 .. Feral Chaos 62):
- EBOOT FUN_088d6254(owner): `owner < 0 || owner >= 35 -> 0`, else u32 table 0x089CC020[owner] — the table only has
  owners 0..32; owner 33 reads string bytes after it (795699042) -> no name. Used by Records (collection scene
  FUN_08a3eb78 -> text/EN/mess_pk_collection_0 group 3), and menu FUN_089ef21c / FUN_089f46e8 / FUN_089f4a4c and an
  EBOOT caller (all.c 491108).
- menu FUN_08a1d7f8 (network scene: Friend Card favourite character / Ghost character): u16 table 0x08A23ACC[owner-1]
  (32 owners) -> owner 33 reads the next table (97) -> no name (mess_pk_network group 3).
- EBOOT 0x089CF350 + 4*owner (u16 name, u16 manikin name; owners 1..31): owner 33's slot 0x089CF3D4 is zero padding
  before the table at 0x089CF3DC (no reference to 0x089CF3D0..DB) -> "Warrior of Light". Used by EBOOT 0x08911DBC
  (scenario character) and the Labyrinth (menu 0x08B4E414 / 0x08B4E688).
Fix: owner 33 -> name index 63 in all three, and "Sora" appended as entry 63 to every name-list group
(collection 3, colosseum 1, creation_room 1, dungeon 2, loading 1, md_list 4, network 3, worldmap 1; update_list 2
is done by spot33_catalog.py). Guarded old/new words, re-runnable, --dry writes nothing.

  python3 -I spot33_ownername.py ISO [--dry]
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from mips_asm import asm  # noqa: E402
from roster_patch import MENU_FILEOFF, MENU_ISO_SECTOR, MENU_VADDR  # noqa: E402
from spot33_museum import decode, encode  # noqa: E402

SECTOR = 0x800
EBOOT_ISO = 560 * SECTOR
NAME_INDEX = 63
EBOOT_SITES = [
    (0x088D6254, '04800003 28850023 14a00002 00000000 34040000 3c05089d 00042080 24a5c020 00852021 03e00008 8c820000',
     ['sltiu a1,a0,35', 'movz a0,zero,a1',          # owner < 0 or >= 35 -> owner 0 (as before)
      'xori a1,a0,33', 'beq a1,zero,0x088D6278', 'lui a1,0x89d',
      '.word 0x00042080',                             # sll a0,a0,2
      'addu a0,a0,a1', 'jr ra', 'lw v0,-0x3fe0(a0)',
      'jr ra', 'ori v0,zero,%d' % NAME_INDEX]),        # owner 33 -> "Sora"
]
MENU_SITES = [
    (0x08A1D7FC, '00052c00 00052c03 3c0608a2 00a52821 24c63aca 00a62821 94a70000 34050003 00003025 00004025 afbf0000 '
                 '0e287518 00004825',
     ['lui a2,0x8a2', 'addu a3,a1,a1', 'addu a3,a3,a2', 'lhu a3,0x3aca(a3)',      # table[owner-1]
      'xori t0,a1,33', 'addiu a2,zero,%d' % NAME_INDEX, 'movz a3,a2,t0',        # owner 33 -> "Sora"
      'ori a1,zero,3', 'or a2,zero,zero', 'or t0,zero,zero', 'sw ra,0(sp)', 'jal 0x08a1d460', 'or t1,zero,zero']),
]
EBOOT_DATA = [(0x089CF3D4, struct.pack('<HH', 0, 0), struct.pack('<HH', NAME_INDEX, NAME_INDEX))]
TEXTS = {'text/EN/mess_pk_collection_0.bin': 3, 'text/EN/mess_pk_colosseum_0.bin': 1,
         'text/EN/mess_pk_creation_room_0.bin': 1, 'text/EN/mess_pk_dungeon_0.bin': 2,
         'text/EN/mess_pk_loading_0.bin': 1, 'text/EN/mess_pk_md_list_0.bin': 4,
         'text/EN/mess_pk_network_0.bin': 3, 'text/EN/mess_pk_worldmap_0.bin': 1}
SORA = ('Sora\0').encode('utf-16-le')


def eboot_off(va):
    return EBOOT_ISO + 0x1018 + va - 0x8804040


def menu_off(va):
    return MENU_ISO_SECTOR * SECTOR + va - MENU_VADDR + MENU_FILEOFF


def get(iso, path):
    use_iso(iso)
    st, sz = pkg_offset(path)
    with open(iso, 'rb') as f:
        return read_at(f, st, sz)


def put_file(iso, path, data):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'x.bin')
        open(p, 'wb').write(data)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                           check=True, capture_output=True, text=True)
        print('   ', r.stdout.strip())


def code(iso, dry):
    plan = []
    with open(iso, 'rb') as f:
        f.seek(EBOOT_ISO)
        assert f.read(4) == b'\x7fELF', 'EBOOT is not the plain ELF'
        for sites, off in ((EBOOT_SITES, eboot_off), (MENU_SITES, menu_off)):
            for va, old, lines in sites:
                old = [int(x, 16) for x in old.split()]
                new = asm(lines, va)
                assert len(new) == len(old), (hex(va), len(new), len(old))
                f.seek(off(va))
                cur = list(struct.unpack('<%dI' % len(old), f.read(4 * len(old))))
                assert cur in (old, new), 'code at %08x is neither original nor ours' % va
                plan.append((off(va), va, struct.pack('<%dI' % len(new), *new), cur == new))
        for va, old, new in EBOOT_DATA:
            f.seek(eboot_off(va))
            cur = f.read(len(old))
            assert cur in (old, new), 'data at %08x = %s' % (va, cur.hex())
            plan.append((eboot_off(va), va, new, cur == new))
    for at, va, data, done in plan:
        print('  %08x: %s' % (va, 'already' if done else 'patch (%d bytes)' % len(data)))
    if not dry:
        with open(iso, 'r+b') as f:
            for at, va, data, done in plan:
                if not done:
                    f.seek(at)
                    f.write(data)


def texts(iso, dry):
    for path, gi in TEXTS.items():
        d = get(iso, path)
        assert d[:8] == b'mess pak', d[:8]
        ng, = struct.unpack_from('<H', d, 10)
        groups = [struct.unpack_from('<II', d, 0x10 + 8 * i) for i in range(ng)]
        bodies = [d[go:go + gs] for go, gs in groups]
        raws = decode(bodies[gi])
        e = encode(raws)
        assert e == bodies[gi][:len(e)] and not bodies[gi][len(e):].strip(b'\0'), path
        assert raws[0] == ('Warrior of Light\0').encode('utf-16-le') and 'Feral' in raws[62].decode('utf-16-le')
        if len(raws) == NAME_INDEX + 1:
            assert raws[NAME_INDEX] == SORA, '%s group %d entry 63 is not "Sora"' % (path, gi)
            print('  %s group %d: already "Sora" at 63' % (path, gi))
            continue
        assert len(raws) == NAME_INDEX, (path, len(raws))
        bodies[gi] = encode(raws + [SORA])
        out = bytearray(d[:groups[0][0]])
        for i, b in enumerate(bodies):
            out += b'\0' * ((-len(out)) % 16)
            struct.pack_into('<II', out, 0x10 + 8 * i, len(out), len(b))
            out += b
        out += b'\0' * ((-len(out)) % 16)
        for i, (go, gs) in enumerate(groups):
            no, ns = struct.unpack_from('<II', out, 0x10 + 8 * i)
            if i == gi:
                chk = decode(bytes(out[no:no + ns]))
                assert chk[:NAME_INDEX] == raws and chk[NAME_INDEX] == SORA
            else:
                assert out[no:no + ns] == d[go:go + gs]
        print('  %s group %d: + "Sora" at 63 (%d -> %d bytes)' % (path, gi, len(d), len(out)))
        if not dry:
            put_file(iso, path, bytes(out))


def main():
    iso = [a for a in sys.argv[1:] if not a.startswith('--')][0]
    dry = '--dry' in sys.argv
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the vanilla ISO'
    code(iso, dry)
    texts(iso, dry)
    print('dry run, nothing written' if dry else 'done')


if __name__ == '__main__':
    main()
