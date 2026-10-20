"""Give roster spot #33 its name key "sev120" in the menu and its own menu pictures.

The game turns an owner number into a short name key ("sev100" = Cloud) with tables of string pointers.
EBOOT, the battle overlay and two tables in the menu overlay already map owner 33 -> "sev120" (Aerith's old key),
but the menu overlay's third table (file 0x17ab50, VA 0x08B57FBC) stops at owner 32 -> the loading screen asked for
menu/EN/common/chara_name/p_(null)_name.gim. This points its entry 33 at the "sev120" string of the first menu
table (same overlay), then adds #33's pictures under that key (copies of Cloud's for now; Sora's later).

Usage: python3 -I spot33_names.py ISO [SRC_KEY]      (writes to ISO!  SRC_KEY = whose pictures to copy, default sev100)
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, package_entry, read_at  # noqa: E402
from pkg_add import dir_record  # noqa: E402
from pkg_put import PACKAGE_INFO_ISO_SECTOR  # noqa: E402

MENU_BASE = 0x089DD4C0 - 0x54                  # OVL_MENU_APP.ELF file offset -> address
ENTRY33 = 0x17ab50 + 32 * 4                    # table starts at owner 1
SEV120_STR = 0x089EA1F0 + 32 * 8               # "sev120" in the first menu table's strings
KEY = 'sev120'
PICTURES = [
    'menu/EN/common/chara_name/p_%s_name.gim',             # name banner (loading screen, menus)
    'menu/JP/story_mode/chara2/p_%s_1p.gim',
    'menu/JP/character_select/chara2/p_%s_1p.gim',
    'menu/EN/battle/encount/encount_text_tim2/encount_%s.gim',
    'menu/JP/arcademode/arcade_last_chara_tim2/arcade_last_%s.gim',
]


def main():
    iso = sys.argv[1]
    src_key = sys.argv[2] if len(sys.argv) > 2 else 'sev100'
    with open(iso, 'r+b') as f:
        rec = dir_record(f, b'OVL_MENU_APP.ELF')
        ovl = struct.unpack('<I', read_at(f, rec + 2, 4))[0] * SECTOR
        s = SEV120_STR - MENU_BASE
        assert read_at(f, ovl + s, 7) == b'sev120\0', 'menu overlay layout differs'
        cur, = struct.unpack('<I', read_at(f, ovl + ENTRY33, 4))
        if cur == SEV120_STR:
            print('menu name table: already patched')
        else:
            assert cur == 0, 'entry 33 = %08x, expected 0' % cur
            prev, = struct.unpack('<I', read_at(f, ovl + ENTRY33 - 4, 4))
            assert read_at(f, ovl + prev - MENU_BASE, 7) == b'org210\0', 'entry 32 is not org210'
            f.seek(ovl + ENTRY33)
            f.write(struct.pack('<I', SEV120_STR))
            print('menu name table: owner 33 -> "sev120"')
        info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
        files = []
        for pattern in PICTURES:
            off, size = package_entry(info, pattern % src_key)
            files.append((pattern % KEY, read_at(f, PACKAGE_ISO_SECTOR * SECTOR + off, size)))
    with tempfile.TemporaryDirectory() as tmp:
        for path, data in files:
            p = os.path.join(tmp, os.path.basename(path))
            open(p, 'wb').write(data)
            subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p], check=True)


if __name__ == '__main__':
    main()
