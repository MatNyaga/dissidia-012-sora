"""PP Catalog entries for Sora (2026-10-17, Mat): buy Sora with PP, a "[KINGDOM HEARTS II] Set of 3" player-icon set
(Sora / Riku / Kairi = icons 414-416), "[Avatar] Sora" (icon 417) and the three KHII tracks. notes/unlocks.md.

PP Catalog = package file `update_list_param.bin` (menu "label" scene; texts text/EN/mess_pk_update_list_0.bin):
  u16 4, u16 counts of the 5 tabs (117, 44, 31, 93, 41), u16 32 (path strings), u16 -1; then 28-byte items back to
  back; then 32 x 64-byte strings. Item: u32 PP cost, s16 name text (group 0; 21 = "%s"), s16 help text (group 3),
  s16 ?, s16 visible-after flag x2 (-1 = always listed), s16 FLAG SET WHEN BOUGHT, s16 "new" flag, s16 message kind
  (2 = "You can now play as %s!"), s16 arg kind, s16 arg (character name = group 2 index, BGM = bgm text id =
  group 6 index), s16 arg-2 kind, s16 arg 2 (same values).
  - characters: tab 0 items 0-14 (flag = the owner's EBOOT unlock-table flag 700+, e.g. Prishe 300 PP / flag 727);
  - player icons: tab 3 (icons are owned when their system.bin "uicn" unlock flag is set; the item sets it);
  - BGM: tab 4 items 16-40 (flag = the bgm_entry row's unlock flag 1047-1071, 150/240 PP).

What this script writes (guarded old/new, re-runnable, --dry writes nothing):
1. Tab 0 item 15 "Chaos (CPU)" (90 PP, flag 925 = Chaos's unlock flag) -> "Sora" character unlock (300 PP like
   Prishe/Gilgamesh, always listed, flag 925). Chaos's unlock row was given to Sora (eboot_plain, test20), so the
   Chaos item did nothing any more; a save that already bought it keeps Sora unlocked.
2. EBOOT unlock row 22 (owner 33): unlock flag -1 (always) -> 925; costume flags 1/1 (spot33_outfits) kept.
   -> Quick Battle grid, Customization, assist list etc. show Sora only after he is bought (or 925 was set).
   UNLOCK=0 env keeps him unlocked from the start (catalog item still there, buying it changes nothing).
3. Tab 3: + "[KINGDOM HEARTS II] Set of 3" (150 PP, flag 1253 = icons 414-416) and "[Avatar] Sora" (150 PP,
   flag 1254 = icon 417), after the last icon item. Icons themselves: spot33_museum.py.
4. Tab 4: + "BGM - KHII - Tension Rising / Working Together / Sinister Shadows" (240 PP, flags 1249/1250/1251;
   bgm_entry rows + Museum records get the same flags in spot33_music.py).
5. Texts: group 0 #169 / #170 (item names), group 2 #63 "Sora", group 6 #132-134 (BGM names = bgm_name 132-134).

  python3 -I spot33_catalog.py ISO [--dry]
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from spot33_museum import decode, encode  # noqa: E402

PARAM = 'update_list_param.bin'
TEXT = 'text/EN/mess_pk_update_list_0.bin'
VAN_HEAD = (4, 117, 44, 31, 93, 41, 32, -1)
REC = '<I12h'
# flags (free: no flag table / no code immediate uses them, notes/unlocks.md)
SORA_FLAG = 925                                       # Chaos's old unlock flag (its item is repurposed)
KH_ICON_FLAG, AVATAR_ICON_FLAG = 1253, 1254           # = spot33_museum ICONS
BGM_FLAGS = (1249, 1250, 1251)                        # = spot33_music UNLOCK_FLAGS
BGM_TEXT = (132, 133, 134)                            # bgm_name ids of the KHII tracks
CHAOS_ITEM = (90, 35, 9, -1, 687, 687, 925, 2263, -1, -1, -1, -1, -1)
SORA_ITEM = (300, 21, 1, 90, -1, -1, SORA_FLAG, 2263, 2, 1, 63, 1, 63)
G0 = 169                                              # first new group-0 text
ICON_ITEMS = [(150, G0, 107, -1, -1, -1, KH_ICON_FLAG, -1, -1, -1, -1, -1, -1),
              (150, G0 + 1, 109, -1, -1, -1, AVATAR_ICON_FLAG, -1, -1, -1, -1, -1, -1)]
BGM_ITEMS = [(240, 111, 33, -1, -1, -1, f, -1, -1, 7, t, 7, t) for f, t in zip(BGM_FLAGS, BGM_TEXT)]
TEXTS = {0: (G0, ['[KINGDOM HEARTS II] Set of 3', '[Avatar] Sora']),
         2: (63, ['Sora']),
         6: (132, ['KHII - Tension Rising', 'KHII - Working Together', 'KHII - Sinister Shadows'])}
EBOOT_ISO = 560 * 0x800
UNLOCK_ROW_VA = 0x089D7BE0 + 22 * 20
UNLOCK_FREE = (33, -1, 1, 1, 3623)                    # spot33_outfits result
UNLOCK_BUY = (33, SORA_FLAG, 1, 1, 3623)


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


def patch_param(d):
    head = struct.unpack_from('<8h', d, 0)
    cnt = list(head[1:6])
    want_cnt = [117, 44, 31, 93 + len(ICON_ITEMS), 41 + len(BGM_ITEMS)]
    assert head[0] == 4 and head[6] == 32 and head[7] == -1 and cnt in ([117, 44, 31, 93, 41], want_cnt), head
    n = sum(cnt)
    assert len(d) == 16 + 28 * n + 32 * 64, len(d)
    items = [struct.unpack_from(REC, d, 16 + 28 * i) for i in range(n)]
    tabs, k = [], 0
    for c in cnt:
        tabs.append(items[k:k + c])
        k += c
    assert tabs[0][15] in (CHAOS_ITEM, SORA_ITEM), tabs[0][15]
    if cnt == want_cnt:
        assert tabs[3][-2:] == ICON_ITEMS and tabs[4][-3:] == BGM_ITEMS, 'catalog extra items are not ours'
    used = {it[6] for it in items if it not in ICON_ITEMS + BGM_ITEMS and it != SORA_ITEM}
    assert not used & ({KH_ICON_FLAG, AVATAR_ICON_FLAG} | set(BGM_FLAGS)), 'catalog flag clash'
    tabs[0][15] = SORA_ITEM
    if cnt != want_cnt:
        tabs[3] = tabs[3] + ICON_ITEMS
        tabs[4] = tabs[4] + BGM_ITEMS
    out = struct.pack('<8h', 4, *want_cnt, 32, -1)
    out += b''.join(struct.pack(REC, *it) for t in tabs for it in t) + d[16 + 28 * n:]
    new_items = [struct.unpack_from(REC, out, 16 + 28 * i) for i in range(sum(want_cnt))]
    keep = [it for i, it in enumerate(items) if i != 15]          # every other vanilla item, in order
    assert [it for it in new_items if it not in ICON_ITEMS + BGM_ITEMS and it != SORA_ITEM] == \
        [it for it in keep if it not in ICON_ITEMS + BGM_ITEMS] and len(out) == 16 + 28 * sum(want_cnt) + 32 * 64
    return out, out != d, new_items


def patch_text(d):
    assert d[:8] == b'mess pak', d[:8]
    ng, = struct.unpack_from('<H', d, 10)
    groups = [struct.unpack_from('<II', d, 0x10 + 8 * i) for i in range(ng)]
    bodies = [d[go:go + gs] for go, gs in groups]
    changed = []
    for gi, (n0, texts) in sorted(TEXTS.items()):
        new = [(t + '\0').encode('utf-16-le') for t in texts]
        raws = decode(bodies[gi])
        e = encode(raws)
        assert e == bodies[gi][:len(e)] and not bodies[gi][len(e):].strip(b'\0'), 'group %d re-encode' % gi
        if len(raws) == n0 + len(new):
            assert raws[n0:] == new, 'group %d entries %d.. exist but differ' % (gi, n0)
            continue
        assert len(raws) == n0, (gi, len(raws), n0)
        bodies[gi] = encode(raws + new)
        changed.append(gi)
    if not changed:
        return d, []
    out = bytearray(d[:groups[0][0]])
    for i, b in enumerate(bodies):
        out += b'\0' * ((-len(out)) % 16)
        struct.pack_into('<II', out, 0x10 + 8 * i, len(out), len(b))
        out += b
    out += b'\0' * ((-len(out)) % 16)
    for i, (go, gs) in enumerate(groups):
        no, ns = struct.unpack_from('<II', out, 0x10 + 8 * i)
        if i in changed:
            n0, texts = TEXTS[i]
            chk = decode(bytes(out[no:no + ns]))
            assert chk[:n0] == decode(d[go:go + gs]) and len(chk) == n0 + len(texts)
        else:
            assert out[no:no + ns] == d[go:go + gs], 'group %d changed' % i
    return bytes(out), changed


def unlock(iso, dry):
    want = UNLOCK_FREE if os.environ.get('UNLOCK', '1') == '0' else UNLOCK_BUY
    at = EBOOT_ISO + 0x1018 + UNLOCK_ROW_VA - 0x8804040
    with open(iso, 'rb') as f:
        f.seek(EBOOT_ISO)
        assert f.read(4) == b'\x7fELF', 'EBOOT is not the plain ELF'
        f.seek(at)
        cur = struct.unpack('<5i', f.read(20))
    seen = cur[4]                            # SEEN/"NEW" flag: 3623, or 3633 after spot33_newtag (kept as is)
    if seen == 3633:
        cur = cur[:4] + (3623,)
    assert cur in (UNLOCK_FREE, UNLOCK_BUY), 'EBOOT unlock row 22 = %s - stop (run spot33_outfits first)' % (cur,)
    print('EBOOT unlock row owner 33: %s -> %s%s' % (cur[:4] + (seen,), want[:4] + (seen,), ' already' if cur == want else ''))
    if cur != want and not dry:
        with open(iso, 'r+b') as f:
            f.seek(at)
            f.write(struct.pack('<5i', *want[:4], seen))


def main():
    iso = [a for a in sys.argv[1:] if not a.startswith('--')][0]
    dry = '--dry' in sys.argv
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the vanilla ISO'
    d = get(iso, PARAM)
    nd, ch, items = patch_param(d)
    print('%s: Sora item (tab 0 #15, %d PP, flag %d), icon items %s, BGM items %s: %s (%d -> %d bytes)' % (
        PARAM, SORA_ITEM[0], SORA_FLAG, [(i[0], i[6]) for i in ICON_ITEMS], [(i[0], i[6]) for i in BGM_ITEMS],
        'written' if ch and not dry else ('to write' if ch else 'already'), len(d), len(nd)))
    if ch and not dry:
        put_file(iso, PARAM, nd)
    t = get(iso, TEXT)
    nt, groups = patch_text(t)
    print('%s: groups changed %s (%d -> %d bytes)' % (TEXT, groups or 'none (already)', len(t), len(nt)))
    if groups and not dry:
        put_file(iso, TEXT, nt)
    unlock(iso, dry)
    print('dry run, nothing written' if dry else 'done')


if __name__ == '__main__':
    main()
