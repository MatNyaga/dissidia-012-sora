"""Give #33 (Sora) his own move names + descriptions in menus (Customize, ability lists).

  python3 -I spot33_movenames.py ISO

- general_archive/main/EN/main_lang.bin (MPK) -> ability.bin: unused placeholder entries 392-399 ("Firion08".. —
  no ablt row uses them) get the new texts (ability_text.set_texts: text appended, entry pointer moved; the table
  size stays the same — growing the table made the game garble the entries around the old end of the file),
  MPK rebuilt (mpk.replace), put back with pkg_put.py.
- system.bin/ablt rows 617-620 (#33's four moves): +2 name id, +4 description id -> the new texts.
Idempotent: if the names are already there (ability.bin ends with them), only the ablt rows are (re)written.
The in-battle move banner is a different text (fighter file 'text' chunk, battle-font codes) — not changed here.
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ability_text  # noqa: E402
import mpk  # noqa: E402
from ablt_patch import locate_ablt, package_entry, read_at, PACKAGE_ISO_SECTOR, SECTOR, ROW  # noqa: E402
from pkg_put import PACKAGE_INFO_ISO_SECTOR  # noqa: E402

LANG = 'general_archive/main/EN/main_lang.bin'
ENTRY0 = 392                         # first of 8 unused placeholder entries (Firion08..Firion15)
ROWS = [617, 618, 619, 620]          # ground Bravery, air Bravery, ground HP, air HP
NAMES = ['Combo Plus', 'Air Combo Plus', 'Explosion', 'Aerial Finish']   # Mat 2026-10-14: no Cross-slash/Braver
DESCS = ['A long Keyblade combo that launches your foe into the air.',
         'A long Keyblade combo in midair.',
         'Plant the Keyblade: a magic blast hits all around.',
         'Five full Keyblade sweeps in midair.']


def main():
    iso = sys.argv[1]
    with open(iso, 'rb') as f:
        info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
        off, size = package_entry(info, LANG)
        lang = read_at(f, PACKAGE_ISO_SECTOR * SECTOR + off, size)
    member = [e for e in mpk.entries(lang) if e[0] == 'ability.bin'][0]
    ab = lang[member[1]:member[1] + member[2]]
    texts = ability_text.decode(ab)
    want = NAMES + DESCS
    first = ENTRY0 - 1                                     # game text id = entry index - 1
    if [t.rstrip('\0') for t in texts[ENTRY0:ENTRY0 + len(want)]] == want:
        print('names already present (game ids %d..%d)' % (first, first + len(want) - 1))
    else:
        ab = ability_text.set_texts(ab, {ENTRY0 + k: t for k, t in enumerate(want)})
        new_lang = mpk.replace(lang, 'ability.bin', ab)
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'main_lang.bin')
            open(p, 'wb').write(new_lang)
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, LANG, p],
                               check=True, capture_output=True, text=True)
            print(r.stdout.strip())
        print('names/descriptions written: game ids %d..%d' % (first, first + len(want) - 1))
    with open(iso, 'r+b') as f:
        ablt, count = locate_ablt(f, info)
        for k, row in enumerate(ROWS):
            at = ablt + 16 + row * ROW
            f.seek(at + 2)
            f.write(struct.pack('<HH', first + k, first + len(NAMES) + k))
            print('ablt row %d: name %d "%s", description %d' % (row, first + k, NAMES[k], first + len(NAMES) + k))


if __name__ == '__main__':
    main()
