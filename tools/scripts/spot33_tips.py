"""Battle Tips for #33 (Sora): Customization → Battle Tips → "◇Character Info: KINGDOM HEARTS II" (7 pages).

How Battle Tips work (static, 2026-10-17): the menu's help viewer (EBOOT FUN_088fd928, called by menu FUN_08af73d4
with id 0x10, pack = text/EN/mess_pk_customize_common_0.bin, group 2) lists the rows of **manual_param.bin**
(member of general_archive/main/main.bin, loader FUN_088fc938) whose category = 0x10:
  "MANU" 05 01 11 20 + 8×FF; +0x10 s16 categories (28), +0x12 s16 rows (201); categories × 8 B; rows × 22 B:
  +0 s8 category (16 = Battle Tips), +1 u8 sub-list (16: 0 = TIPs, 1 = Character Info), +2 s16 row id,
  +4 s16 unlock flag (−1 = always listed), +6 / +8 / +10 s16 "new"/read flags (−1 = none), +0xc u8 title text,
  +0xd 9 × u8 page texts (0xFF = end). Texts = group 2 of the pak (u16 table like spot33_desc's group 0).
  Rows are listed in file order, filtered by category (FUN_088fd4c4). The loader allocates the file + room for
  0x1C categories and 0xCD (205) rows, so up to 4 rows can be appended with no code change.
Character Info is per SERIES (FF I … XIII + Secrets) with no owner index → Sora simply had no row. Sora's row is
appended at the end (row id 201, sub-list 1, no unlock / new flags) → shown after "Secrets (part 3)".
Texts: group-2 entries appended after the vanilla 178 (title + pages), every other entry/group byte-identical.

  python3 -I spot33_tips.py ISO [--dry] [-v]
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mpk  # noqa: E402
from comb_patch import SECTOR, pkg_offset, read_at, use_iso  # noqa: E402
from spot33_desc import decode as t_decode, encode as t_encode  # noqa: E402

PAK = 'text/EN/mess_pk_customize_common_0.bin'
MAIN = 'general_archive/main/main.bin'
MEMBER = 'manual_param.bin'
VANILLA_ROWS, VANILLA_TEXTS, ROW_CAP = 201, 178, 0xCD
CAT_TIPS, SUB_CHARINFO = 16, 1

SP = '　'                                     # full-width space (vanilla indents)
HEAD = lambda t: '\x10膁！' + t + '\x1b'  # noqa: E731  orange heading "◆Cloud"
HI = '\x10脁ﾁ'                           # highlighted block start (vanilla "★Push enemies…"), ends at \x1b
CIRCLE, SQUARE = '\x1e⼁', '\x1e、'      # ◯ / □ button glyphs
I3 = SP * 3

TITLE = '◇Character Info: KINGDOM HEARTS II'
PAGES = [
    '\n'.join([HEAD('◆Sora'),
               SP + '★Profile',
               I3 + 'A Keyblade wielder who strings long, flashy',
               I3 + 'combos together, then finishes them with a',
               I3 + SQUARE + ' attack. His magic covers every distance!',
               '',
               I3 + "He came all the way from another world! He's",
               I3 + "so cheerful, I'd love to go on an adventure",
               I3 + 'with him and his friends.']),
    '\n'.join([SP + '★Equipment',
               I3 + 'Weapons: swords, daggers, greatswords, katana,',
               I3 + SP * 4 + ' axes',
               I3 + 'Armor: shields, gauntlets, large shields, helms,',
               I3 + SP * 3 + ' light armor, heavy armor, chestplates',
               '',
               SP + '★Attack Abilities',
               I3 + 'Bravery: Long combos from every starter',
               I3 + 'HP: Finishers branching from combos, and magic']),
    '\n'.join([HEAD('◆Combos'),
               'Every bravery attack starts a long combo. Keep',
               'tapping ' + CIRCLE + ' and it flows all the way to a finisher!',
               HI,
               SP + '★Combo Plus: 12 hits without leaving the ground',
               SP + '★Slide Dash: dash in from afar, launch the foe',
               SP + SP + 'and rave in midair (19 hits!)',
               SP + '★Dodge Slash: spin in, end with Finishing Leap',
               SP + '★Air Combo Plus, Aerial Spiral, Aerial Dive:',
               SP + SP + 'three different endings in midair\x1b']),
    '\n'.join(['Equip the ' + SQUARE + ' abilities that branch from a combo,',
               'then press ' + SQUARE + ' in the middle of it for HP damage!',
               HI,
               SP + '★Combo Plus ⇒ Upper Slash / Guard Break',
               SP + '★Slide Dash ⇒ Upper Slash / Guard Break',
               SP + '★Dodge Slash ⇒ Explosion',
               SP + '★Air Combo Plus ⇒ Aerial Sweep / Magnet Burst /',
               SP + SP + 'Retaliating Slash / Horizontal Slash\x1b',
               '',
               'They branch at different hits, so equip them all!']),
    '\n'.join([HEAD('◆Magic'),
               SP + '★Firaga: a burst of flames all around Sora.',
               I3 + 'It only reaches foes right next to him!',
               SP + "★Thundaga: sparks mark the foe's spot, then",
               I3 + 'three bolts strike there. Foes can dash out',
               I3 + "of the way, so cast it when they can't!",
               SP + '★Blizzaga: a spread of three ice shards that',
               I3 + 'flies far. Great at long range.',
               'All three spells work in midair, too.']),
    '\n'.join([HEAD('◆EX Mode'),
               'In EX Mode the Kingdom Key becomes Ultima Weapon!',
               HI,
               SP + '★Ultima Weapon: the higher his HP, the stronger',
               SP + SP + 'it gets, and bravery attacks get a 50% bonus',
               SP + '★Reflect: blocking sends attacks, spells, even',
               SP + SP + 'HP attacks back! Reflecting an HP attack',
               SP + SP + 'refills the EX Gauge',
               SP + '★Haste: runs 40% faster on the ground\x1b']),
    '\n'.join([HEAD('◆Trinity Limit'),
               'His EX Burst calls on the light of his friends.',
               HI + SP + '★Tap ' + CIRCLE + ' again and again to fill the gauge!\x1b',
               # RR-17 (2026-10-18): TRI is two-way (19+ taps = full storm 8500, fewer = 3-hit 8501), and all four
               # Sora-only items (678-681) exist now; the old page said "fuller = longer" and listed only two
               'Fill it all the way for the full storm of strikes!',
               '',
               HEAD('◆Sora-only Gear'),
               SP + '★Kingdom Key: connected combo hits build EX',
               SP + '★Protect Belt: blocked hits fill the EX Gauge',
               SP + '★Save the King: reflected bravery hits +50%',
               SP + '★Crown Pendant: EX Mode lasts 30% longer']),
]


def manual_split(d):
    assert d[:4] == b'MANU', d[:4]
    nc, nr = struct.unpack_from('<hh', d, 0x10)
    base = 0x18 + nc * 8
    assert len(d) == base + nr * 22, 'manual_param.bin size %d != header %d' % (len(d), base + nr * 22)
    return d[:base], [d[base + i * 22:base + i * 22 + 22] for i in range(nr)]


def main():
    iso = sys.argv[1]
    dry = '--dry' in sys.argv
    use_iso(iso)
    with open(iso, 'rb') as f:
        mst, msz = pkg_offset(MAIN)
        main_bin = read_at(f, mst, msz)
        pst, psz = pkg_offset(PAK)
        pak = read_at(f, pst, psz)
    member = [e for e in mpk.entries(main_bin) if e[0] == MEMBER]
    assert len(member) == 1, 'manual_param.bin not in main.bin'
    man = main_bin[member[0][1]:member[0][1] + member[0][2]]
    head, rows = manual_split(man)
    assert struct.unpack_from('<h', head, 0x10)[0] == 28, 'expected 28 categories'
    vanilla = rows[:VANILLA_ROWS]
    assert all(struct.unpack_from('<h', r, 2)[0] == i for i, r in enumerate(vanilla)), 'row ids moved'
    assert all(r[0] != CAT_TIPS or r[12] < VANILLA_TEXTS for r in vanilla)
    extra = rows[VANILLA_ROWS:]
    assert len(extra) <= 1, 'unexpected extra manual rows (another script?)'

    # --- text pak, group 2 ---
    assert pak[:8] == b'mess pak', pak[:8]
    ng, = struct.unpack_from('<H', pak, 10)
    assert ng == 4, ng
    groups = [struct.unpack_from('<II', pak, 0x10 + 8 * i) for i in range(ng)]
    g2 = pak[groups[2][0]:groups[2][0] + groups[2][1]]
    t2 = t_decode(g2)
    e2 = t_encode(t2)
    assert e2 == g2[:len(e2)] and not g2[len(e2):].strip(b'\0'), 'group 2 does not re-encode exactly'
    assert len(t2) >= VANILLA_TEXTS
    assert t2[0] == 'Battle Tips\0'.encode('utf-16-le') and t2[41].decode('utf-16-le').startswith('◇Character Info')
    if extra:
        r = extra[0]
        own = {r[12]} | {x for x in r[13:22] if x != 0xFF}
        assert r[0] == CAT_TIPS and own == set(range(VANILLA_TEXTS, len(t2))), 'group 2 tail is not ours'
    else:
        assert len(t2) == VANILLA_TEXTS, 'group 2 has extra entries but no Sora row'

    texts = [TITLE] + PAGES
    assert len(PAGES) <= 9 and VANILLA_TEXTS + len(texts) <= 0xFF
    for p in PAGES:
        lines = p.split('\n')
        assert len(lines) <= 10 and max(len(x.replace(CIRCLE, 'O').replace(SQUARE, 'O').replace(HI, '')
                                          .replace('\x1b', '')) for x in lines) <= 56, p
    new_t2 = t2[:VANILLA_TEXTS] + [(t + '\0').encode('utf-16-le') for t in texts]
    new_g2 = t_encode(new_t2)
    assert len(new_g2) < 131070, 'group 2 too big for u16 offsets'
    out = bytearray(pak[:0x10 + 8 * ng])
    for i in range(ng):
        b = new_g2 if i == 2 else pak[groups[i][0]:groups[i][0] + groups[i][1]]
        out += b'\0' * ((-len(out)) % 16)
        struct.pack_into('<II', out, 0x10 + 8 * i, len(out), len(b))
        out += b
    out += b'\0' * ((-len(out)) % 16)
    out = bytes(out)
    chk = [struct.unpack_from('<II', out, 0x10 + 8 * i) for i in range(ng)]
    for i in (0, 1, 3):
        assert out[chk[i][0]:chk[i][0] + chk[i][1]] == pak[groups[i][0]:groups[i][0] + groups[i][1]]
    assert t_decode(out[chk[2][0]:chk[2][0] + chk[2][1]])[:VANILLA_TEXTS] == t2[:VANILLA_TEXTS]

    # --- manual row ---
    row = struct.pack('<bBhhhhhB', CAT_TIPS, SUB_CHARINFO, VANILLA_ROWS, -1, -1, -1, -1, VANILLA_TEXTS)
    pages = list(range(VANILLA_TEXTS + 1, VANILLA_TEXTS + len(texts)))
    row += bytes(pages + [0xFF] * (9 - len(pages)))
    assert len(row) == 22 and VANILLA_ROWS + 1 <= ROW_CAP
    new_head = bytearray(head)
    struct.pack_into('<h', new_head, 0x12, VANILLA_ROWS + 1)
    new_man = bytes(new_head) + b''.join(vanilla) + row
    new_main = main_bin if new_man == man else mpk.replace(main_bin, MEMBER, new_man)
    for name, o, s in mpk.entries(new_main):          # every other member byte-identical
        if name != MEMBER:
            oo = [e for e in mpk.entries(main_bin) if e[0] == name][0]
            assert new_main[o:o + s] == main_bin[oo[1]:oo[1] + oo[2]], name

    print('Battle Tips: row %d (category %d, Character Info), title text %d, pages %s'
          % (VANILLA_ROWS, CAT_TIPS, VANILLA_TEXTS, pages))
    print('%s: %d -> %d B; main.bin %d -> %d B; %s %d -> %d B (group 2 %d -> %d)'
          % (MEMBER, len(man), len(new_man), msz, len(new_main), PAK, psz, len(out), len(g2), len(new_g2)))
    if '-v' in sys.argv:
        for t in texts:
            print('-' * 40)
            print(t.replace(CIRCLE, '◯').replace(SQUARE, '□').replace(HI, '').replace('\x1b', '')
                  .replace('\x10膁！', ''))
    if new_main == main_bin and out == pak:
        print('no change')
        return
    if dry:
        print('--dry: nothing written')
        return
    with tempfile.TemporaryDirectory() as t:
        for path, data, old in ((MAIN, new_main, main_bin), (PAK, out, pak)):
            if data == old:
                continue
            p = os.path.join(t, os.path.basename(path))
            open(p, 'wb').write(data)
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                               check=True, capture_output=True, text=True)
            print(r.stdout.strip())


if __name__ == '__main__':
    main()
