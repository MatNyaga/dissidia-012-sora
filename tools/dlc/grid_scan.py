"""Read-only scan of the shared character-select grid (menu overlay) in an ISO: P0.5 evidence.

  python3 -I tools/dlc/grid_scan.py ISO

Prints, for the ISO given:
  1. the Quick Battle row table 0x08A864D0 (33 rows x 12 B) and what follows it (mode table 0x08A8665C),
  2. the last-row centring table (s16 at 0x08A85BF8 + 2*n, n = cells in the grid) and the cell -> slot map,
  3. for every scene that uses the grid object (FUN_08a80d8c callers), its sprite list: which seq the 34 cell
     sprites (list base+2 .. base+35), the marker (base+36) and the locator (base+37) use, resolved against the
     scene's seq packs on the disc, and the locator anim 5 (38 points) = the on-screen cell positions,
  4. every slti/sltiu bound check (immediate 0x1F..0x29) in the grid code 0x08A7EB00..0x08A86760.
Never writes. Python -I. Overlay = OVL_MENU_APP.ELF at ISO sector 185056 (file off = VA - 0x089DD4C0 + 0x54).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../scripts'))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from seq_dump import parse  # noqa: E402

SECTOR = 0x800
MENU_SECTOR, MENU_VA, MENU_OFF, MENU_SIZE = 185056, 0x089DD4C0, 0x54, 1556096
QB_TABLE, QB_ROWS, MODE_TABLE = 0x08A864D0, 33, 0x08A8665C
LASTROW_TABLE = 0x08A85BF8

# (scene, group, sprite list VA, cfg base (cfg+6), seq packs (EN replaces JP))
SCENES = [
    ('Quick Battle chara select (FUN_08aa0d48, list A)', 0x1D, 0x08AA3964, 0,
     ['menu/menu_pk_free_battle_seq_0.bin', 'menu/EN/menu_lpk_free_battle_seq_0.bin']),
    ('Quick Battle chara select (list B, base 20)', 0x1D, 0x08AA3A60, 20,
     ['menu/menu_pk_free_battle_seq_0.bin', 'menu/EN/menu_lpk_free_battle_seq_0.bin']),
    ('Main-menu chara select (Customization etc., FUN_08a8799c)', 0x22, 0x08A87C82, 0,
     ['menu/menu_pk_upper_chara_select_seq_0.bin', 'menu/EN/menu_lpk_upper_chara_select_seq_0.bin']),
    ('group 0x1A grid (FUN_08a5b9d0 / FUN_08a69e28)', 0x1A, 0x08A5BEE0, 0, None),
    ('party_setting (group 0x19, list 0x08B29A16)', 0x19, 0x08B29A16, None,
     ['menu/menu_pk_party_setting_seq_0.bin', 'menu/EN/menu_lpk_party_setting_seq_0.bin']),
    ('party_setting (group 0x19, list 0x08B29B8A)', 0x19, 0x08B29B8A, None,
     ['menu/menu_pk_party_setting_seq_0.bin', 'menu/EN/menu_lpk_party_setting_seq_0.bin']),
]
ALL_SEQ_PACKS = [  # every seq pack named in the overlay (for scenes whose pack list is not known)
    'title', 'upper_start_menu', 'arcade', 'colosseum', 'network', 'label', 'collection', 'creation_room',
    'original_quest', 'multi_lobby', 'upper_chara_select', 'upper_story_mode', 'free_battle', 'option',
    'calendar', 'customize', 'shop', 'md_list', 'exmode', 'level_adjust', 'party_setting', 'party_arrange']

def menu_bytes(iso):
    with open(iso, 'rb') as f:
        return read_at(f, MENU_SECTOR * SECTOR, MENU_SIZE)


def at(ovl, va, n):
    o = va - MENU_VA + MENU_OFF
    return ovl[o:o + n]


def sprite_list(ovl, va):
    out, i = [], 0
    while True:
        a, c = struct.unpack('<hh', at(ovl, va + 4 * i, 4))
        if a == -1 or i > 300:
            return out
        out.append((a, c))
        i += 1


def load_pack(iso, path):
    try:
        st, sz = pkg_offset(path)
    except SystemExit:
        return None
    with open(iso, 'rb') as f:
        d = read_at(f, st, sz)
    if d[:8] != b'menu pak':
        return None
    cnt, base = struct.unpack_from('<HH', d, 10)
    return path, base, cnt, d


def seq_by_id(packs, sid):
    for path, base, cnt, d in packs:
        if base <= sid < base + cnt:
            off, size = struct.unpack_from('<II', d, 16 + 8 * (sid - base))
            if size:
                return path, sid - base, d[off:off + size]
    return None


def mips_scan(ovl, lo, hi):
    """every slti/sltiu with a small immediate in [lo, hi) (bound checks), as (VA, word, text)"""
    out = []
    R = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3', 't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
         's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']
    for va in range(lo, hi, 4):
        w, = struct.unpack('<I', at(ovl, va, 4))
        op = w >> 26
        if op in (0x0A, 0x0B):
            imm = w & 0xFFFF
            if imm in (0x1F, 0x20, 0x21, 0x22, 0x23, 0x27, 0x28, 0x29):
                out.append((va, w, '%s %s,%s,0x%x' % ('slti' if op == 0x0A else 'sltiu',
                                                      R[(w >> 16) & 31], R[(w >> 21) & 31], imm)))
    return out


def main():
    iso = sys.argv[1]
    use_iso(iso)
    ovl = menu_bytes(iso)
    print('== Quick Battle row table 0x%08X (i16 pic, i16 name_pic, i16 logo, i16 owner, i32 owner)' % QB_TABLE)
    for r in range(QB_ROWS):
        print('  row %2d' % r, struct.unpack('<hhhhi', at(ovl, QB_TABLE + 12 * r, 12)))
    end = QB_TABLE + 12 * QB_ROWS
    print('  table ends 0x%08X; mode table starts 0x%08X (gap %d bytes)' % (end, MODE_TABLE, MODE_TABLE - end))
    print('== mode table 0x%08X (variant -> s16 mode, ?, anim, anim, ...; 0x14 B rows)' % MODE_TABLE)
    for v in range(13):
        print('  variant %2d' % v, struct.unpack('<10h', at(ovl, MODE_TABLE + 0x14 * v, 0x14)))
    print('== last-row start offset T[n] (s16 at 0x%08X + 2n) and resulting cells' % LASTROW_TABLE)
    for n in range(0, 37):
        t, = struct.unpack('<h', at(ovl, LASTROW_TABLE + 2 * n, 2))
        full = 0 if n < 7 else 6 if n < 17 else 16 if n < 27 else 26
        last = n - full
        slots = list(range(full)) + [t + full + k for k in range(last)]
        cells = [s + 2 if s <= 5 else s + 4 if s <= 25 else s + 6 for s in slots]
        bad = [c for c in cells if c > 39]
        print('  n=%2d T=%d last-row slots %s%s' % (n, t, slots[full:], '  OVERFLOW cells %s' % bad if bad else ''))
    packs_all = [p for p in (load_pack(iso, 'menu/menu_pk_%s_seq_0.bin' % n) for n in ALL_SEQ_PACKS) if p]
    packs_all += [p for p in (load_pack(iso, 'menu/EN/menu_lpk_%s_seq_0.bin' % n) for n in ALL_SEQ_PACKS) if p]
    for name, group, lva, base, paths in SCENES:
        lst = sprite_list(ovl, lva)
        packs = [p for p in (load_pack(iso, x) for x in paths) if p] if paths else packs_all
        print('== %s: group 0x%X, list 0x%08X, %d sprites' % (name, group, lva, len(lst)))
        if base is None:   # find the 34-long run of one seq id = the cells
            ids = [a for a, _ in lst]
            for i in range(len(ids) - 33):
                if len(set(ids[i:i + 34])) == 1:
                    base = i - 2
                    break
            print('  cell run found -> cfg base %s' % base)
        if base is None or base + 37 >= len(lst):
            print('  no 34-cell run')
            continue
        cells = lst[base + 2:base + 36]
        print('  cell sprites base+2..base+35: seq %s, %d sprites, default textures %s' % (
            sorted(set(a for a, _ in cells)), len(cells), [c for _, c in cells]))
        for k, label in ((36, 'marker'), (37, 'locator')):
            sid, tex = lst[base + k]
            r = seq_by_id(packs, sid)
            print('  base+%d %s: seq %d tex %d -> %s' % (k, label, sid, tex, (r[0], r[1]) if r else 'not found'))
            if label == 'locator' and r:
                s = parse(r[2])
                a5 = s['anims'][5] if len(s['anims']) > 5 else None
                if a5 is None:
                    print('   no anim 5')
                    continue
                nt = len(a5['tracks'])
                pts = [a5['tracks'][nt - 1 - (37 - slot)][1][0]['xy'] if 0 <= nt - 1 - (37 - slot) < nt else None
                       for slot in range(38)]
                print('   anim 5: %d locator tracks; slot -> (x,y):' % nt)
                for row, (a, b) in enumerate(((0, 6), (6, 16), (16, 26), (26, 34), (34, 38))):
                    print('    %s slots %d..%d: %s' % ('row %d' % row if row < 4 else 'extra', a, b - 1, pts[a:b]))
    print('== bound checks (slti/sltiu 0x1F..0x29) in the grid code 0x08A7EB00..0x08A86760')
    for va, w, txt in mips_scan(ovl, 0x08A7EB00, 0x08A86760):
        print('  0x%08X %08X %s' % (va, w, txt))


if __name__ == '__main__':
    main()
