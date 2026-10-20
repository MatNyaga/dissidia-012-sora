"""Add equippable moves for #33 (Sora): one ablt row each (+ name/description text + learned at a level via chrl).
Recipe: notes/abilities-owner33.md. Each move switches on an action id in obj/p_sev120.objx `comb` (built by
spot33_combos.py). Text goes into unused placeholder entries of ability.bin ("Kefka57"… = entries 1042+).
Abilities are learned on LEVEL-UP (chrl), so an existing Lv N record learns moves listed at levels > N.
Idempotent: rows already present (same id) are rewritten, not duplicated.

  python3 -I spot33_moves.py ISO
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
from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, mpk_member, package_entry, read_at  # noqa: E402
from pkg_put import PACKAGE_INFO_ISO_SECTOR  # noqa: E402
from spot33_save import arc_join, arc_split  # noqa: E402

OWNER = 33
LANG = 'general_archive/main/EN/main_lang.bin'
TEXT0 = 1042                     # first free placeholder entry ("Kefka57"); game text id = entry - 1
# idx, name, description, type (0 Bravery / 1 HP), ground/air (0/1), action id, template Cloud row idx, learn level
MOVES = [
    (4, 'Slide Dash', 'Dash at a distant foe and strike with your Keyblade.', 0, 0, 316, 2, 11),
    # chain abilities (Brv → HP links, Cloud idx 12/14 style): +6 = parent ability, +23 = 0xFF (follow-up)
    (5, 'Combo Plus > Upper Slash', 'End your combo with a rising slash that launches foes.', 1, 0xFF, 315, 12, 12,
     0x2100),
    (6, 'Air Combo > Retaliating Slash', 'A spinning counter of Keyblade strikes in midair.', 1, 0xFF, 323, 14, 12,
     0x2101),
    (7, 'Slide Dash > Upper Slash', 'Follow Slide Dash with a launching upward slash.', 1, 0xFF, 313, 12, 12,
     0x2104),
    # new starters flow into a full long combo (Mat 2026-10-14: "I want long combos like this")
    (8, 'Aerial Spiral', 'Spiral up at a foe above you, then chain air strikes.', 0, 1, 324, 9, 13),
    # KH2 finishers on Square, branching at other hits than Spin Finish / Aerial Flurry (spot33_combos.py)
    (9, 'Combo Plus > Guard Break', 'A spinning lunge that smashes through and sends foes flying.', 1, 0xFF, 314, 12, 13,
     0x2100),
    (10, 'Slide Dash > Guard Break', 'A spinning lunge that smashes through and sends foes flying.', 1, 0xFF, 317, 12, 13,
     0x2104),
    (11, 'Air Combo > Magnet Burst', 'Whirl and raise your Keyblade in a burst of power.', 1, 0xFF, 927, 14, 13,
     0x2101),
    # air moveset (Mat: "Sora has additional air combos e.g. horizontal slash")
    (12, 'Aerial Dive', 'Dive at a foe below you, then chain air strikes.', 0, 1, 325, 8, 14),
    (13, 'Air Combo > Horizontal Slash', 'A flurry of horizontal slashes in midair.', 1, 0xFF, 318, 14, 14, 0x2101),
    (14, 'Air Combo > Aerial Sweep', 'A whirling midair spin that sends foes flying.', 1, 0xFF, 319, 14, 14, 0x2101),
    (15, 'Dodge Slash', 'A spinning flurry that flows into a long combo.', 0, 0, 327, 2, 15),
    (16, 'Dodge Slash > Explosion', 'Plant the Keyblade: a magic blast hits all around.', 1, 0xFF, 320, 12, 15, 0x210f),
    # KH2 magic as HP attacks (spot33_magic.py: actions 1021-1026; Cloud's projectiles as the technical base)
    (17, 'Firaga', 'Hurl a blazing fireball at your foe.', 1, 0, 1021, 11, 18),
    (18, 'Thundaga', 'Call down strikes of thunder on your foe.', 1, 0, 1022, 11, 18),
    (19, 'Blizzaga', 'Fire a spread of ice shards.', 1, 0, 1023, 11, 18),
    (20, 'Aerial Firaga', 'Hurl a blazing fireball from midair.', 1, 1, 1024, 18, 18),
    (21, 'Aerial Thundaga', 'Call down thunder from midair.', 1, 1, 1025, 18, 18),
    (22, 'Aerial Blizzaga', 'Fire ice shards from midair.', 1, 1, 1026, 18, 18),
]


def put_member(iso, path, data):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, os.path.basename(path))
        open(p, 'wb').write(data)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


def texts(iso):
    with open(iso, 'rb') as f:
        info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
        off, size = package_entry(info, LANG)
        lang = read_at(f, PACKAGE_ISO_SECTOR * SECTOR + off, size)
    m = [e for e in mpk.entries(lang) if e[0] == 'ability.bin'][0]
    ab = lang[m[1]:m[1] + m[2]]
    want, ids = {}, {}
    for k, mv in enumerate(MOVES):
        want[TEXT0 + 2 * k], want[TEXT0 + 2 * k + 1] = mv[1], mv[2]
        ids[mv[0]] = (TEXT0 + 2 * k - 1, TEXT0 + 2 * k)          # game ids (entry - 1)
    ab = ability_text.set_texts(ab, want)
    put_member(iso, LANG, mpk.replace(lang, 'ability.bin', ab))
    return ids


def ablt_rows(ablt, ids):
    count, = struct.unpack_from('<I', ablt, 8)
    rows = [bytearray(ablt[16 + i * 40:16 + (i + 1) * 40]) for i in range(count)]
    tail = ablt[16 + count * 40:]
    byid = {struct.unpack_from('<H', r, 0)[0]: r for r in rows}
    for mv in MOVES:
        idx, name, desc, typ, air, action, tpl_idx, lvl = mv[:8]
        parent = mv[8] if len(mv) > 8 else None
        aid = OWNER << 8 | idx
        row = bytearray(byid[13 << 8 | tpl_idx])                 # Cloud's row as template
        row[0], row[1], row[27] = idx, OWNER, OWNER
        struct.pack_into('<HH', row, 2, *ids[idx])
        row[6:12] = b'\xff' * 6
        if parent is not None:
            struct.pack_into('<H', row, 6, parent)
        struct.pack_into('<H', row, 12, action)
        row[22], row[23] = typ, air
        if aid in byid:
            byid[aid][:] = row
        else:
            rows.append(row)
            byid[aid] = row
        print('ablt %04x %-12s action %d %s %s, learned at Lv%d' % (aid, name, action, 'HP' if typ else 'Brv',
                                                                    'air' if air else 'ground', lvl))
    rows.sort(key=lambda r: struct.unpack_from('<H', r, 0)[0])
    assert len(rows) <= 832, 'runtime ablt buffer holds 832 rows (spot33_ablt_cap.py raises it from 808)'
    head = bytearray(ablt[:16])
    struct.pack_into('<I', head, 8, len(rows))
    return bytes(head) + b''.join(bytes(r) for r in rows) + tail


def chrl_add(chrl):
    count, = struct.unpack_from('<I', chrl, 8)
    ents = [struct.unpack_from('<IIII', chrl, 16 + i * 16) for i in range(count)]
    e = next(x for x in ents if x[0] == OWNER)
    c = bytearray(chrl)
    have = set()
    for r in range(e[1]):
        at = e[2] + r * 8
        have.update(struct.unpack_from('<3H', c, at + 2))
    for mv in MOVES:
        idx, name, lvl = mv[0], mv[1], mv[7]
        aid = OWNER << 8 | idx
        if aid in have:
            continue
        for r in range(e[1]):
            at = e[2] + r * 8
            if c[at] != lvl:
                continue
            ids = list(struct.unpack_from('<3H', c, at + 2))
            if 0xFFFF in ids:
                ids[ids.index(0xFFFF)] = aid
                struct.pack_into('<3H', c, at + 2, *ids)
                print('chrl: %s learned at Lv%d' % (name, lvl))
                break
        else:
            # no row for that level: move the next higher row with a free slot down to it (keeps level order;
            # that row's general abilities just come a few levels earlier)
            for r in range(e[1]):
                at = e[2] + r * 8
                ids = list(struct.unpack_from('<3H', c, at + 2))
                if c[at] > lvl and 0xFFFF in ids:
                    print('chrl: row Lv%d -> Lv%d' % (c[at], lvl))
                    c[at] = lvl
                    ids[ids.index(0xFFFF)] = aid
                    struct.pack_into('<3H', c, at + 2, *ids)
                    print('chrl: %s learned at Lv%d' % (name, lvl))
                    break
            else:
                sys.exit('chrl: no free slot for level %d' % lvl)
    return bytes(c)


def main():
    iso = sys.argv[1]
    ids = texts(iso)
    with open(iso, 'rb') as f:
        info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
        pkg = PACKAGE_ISO_SECTOR * SECTOR
        off, size = package_entry(info, 'general_archive/main/main.bin')
        main_bin = read_at(f, pkg + off, size)
        sys_off, sys_size = mpk_member(f, pkg + off, 'system.bin')
        sys_off -= pkg + off
    head, chunks = arc_split(main_bin[sys_off:sys_off + sys_size])
    for c in chunks:
        if c[1] == b'ablt':
            c[2] = ablt_rows(c[2], ids)
        elif c[1] == b'chrl':
            c[2] = chrl_add(c[2])
    sysbin = arc_join(head, chunks)
    put_member(iso, 'general_archive/main/main.bin', mpk.replace(main_bin, 'system.bin', sysbin))


if __name__ == '__main__':
    main()
