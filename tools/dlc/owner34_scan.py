"""Read-only P0.4 scan: what does OWNER 34 (Cosmos's number, P_ORG800) hold today in every per-owner table, and could
it become a second playable slot like owner 33 (Sora)?

  python3 -I tools/dlc/owner34_scan.py dumps/ULUS10566-test338-voicesloud.iso
  python3 -I tools/dlc/owner34_scan.py dumps/ULUS10566.iso            # clean disc (EBOOT is encrypted there:
                                                                       # the EBOOT part reads dumps/extracted/EBOOT.elf)
Optional: --owner N (default 34) to print the same checklist for another owner number.

Prints one line per table: name | where | row size | owners covered | entry for OWNER today | verdict.
Never writes anything (opens files read-only). Addresses: EBOOT VA -> ELF off 0x1018 + VA - 0x08804040, EBOOT.BIN at ISO
sector 560 (plain ELF since test20); menu overlay ISO sector 185056, battle overlay 185824, both off = VA - 0x089DD4C0 + 0x54.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../scripts'))
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from ablt_patch import mpk_member  # noqa: E402

SECTOR = 0x800
ROOT = os.path.join(HERE, '../..')
R = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3', 't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
     's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']


def imm_text(w):
    op, rs, rt, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
    name = {0x0A: 'slti', 0x0B: 'sltiu', 0x0D: 'ori', 0x09: 'addiu', 0x0E: 'xori'}.get(op, 'op%02x' % op)
    return '%s %s,%s,0x%x' % (name, R[rt], R[rs], imm)


class Img:
    def __init__(self, data, base, off):
        self.d, self.base, self.off = data, base, off

    def at(self, va, n):
        o = va - self.base + self.off
        return self.d[o:o + n]

    def u(self, fmt, va):
        return struct.unpack(fmt, self.at(va, struct.calcsize(fmt)))


def load(iso):
    with open(iso, 'rb') as f:
        e = read_at(f, 560 * SECTOR, 4640948)
        menu = read_at(f, 185056 * SECTOR, 1556096)
        bat = read_at(f, 185824 * SECTOR, 0x185B98 + 0x200)
    src = 'ISO'
    if e[:4] != b'\x7fELF':
        e = open(os.path.join(ROOT, 'dumps/extracted/EBOOT.elf'), 'rb').read()
        src = 'dumps/extracted/EBOOT.elf (ISO EBOOT encrypted = clean disc)'
    eb = Img(e, 0x08804040, 0x1018)
    return eb, Img(menu, 0x089DD4C0, 0x54), Img(bat, 0x089DD4C0, 0x54), src


def main_bin(iso):
    use_iso(iso)
    st, _ = pkg_offset('general_archive/main/main.bin')
    out = {}
    with open(iso, 'rb') as f:
        for name in ('objentry.bin', 'system.bin', 'assist.bin', 'bgm_entry.bin'):
            o, n = mpk_member(f, st, name)
            out[name] = read_at(f, o, n)
    sb = out['system.bin']
    n, = struct.unpack_from('<I', sb, 4)
    for i in range(n):
        _, t, o, z = struct.unpack_from('<I4sII', sb, 16 + 16 * i)
        out[t.decode()] = sb[o:o + z]
    return out


def row(table, where, size, covers, today, verdict):
    print('| %s | %s | %s | %s | %s | %s |' % (table, where, size, covers, today, verdict))


def main():
    a = sys.argv[1:]
    own = 34
    if '--owner' in a:
        i = a.index('--owner'); own = int(a[i + 1]); del a[i:i + 2]
    iso = a[0]
    eb, mn, bt, src = load(iso)
    M = main_bin(iso)
    print('# owner %d checklist for %s (EBOOT from %s)' % (own, iso, src))
    print('| table | where | row | owners covered | owner %d today | verdict |' % own)
    print('|---|---|---|---|---|---|')

    # ---------------------------------------------------------------- EBOOT
    rows, va = [], 0x089D7BE0
    while True:
        r = eb.u('<5i', va)
        if r[0] == -1:
            break
        rows.append(r); va += 20
    term = va
    free = 0
    while eb.u('<I', term + 4 + free)[0] == 0 and free < 64:
        free += 4
    hit = [r for r in rows if r[0] == own]
    # 0x089D7E78 is a runtime pointer (DAT_089d7e78 = &DAT_08b85100, all.c ~64480): zero on disc but NOT free
    room = min(free, 0x089D7E78 - (term + 4))
    row('unlock table', 'EBOOT 0x089D7BE0 (FUN_088d5ac8/5ce8)', '5 x i32', '%d rows, -1 at 0x%08X, %d free bytes after '
        '(0x089D7E78 = runtime ptr)' % (len(rows), term, room), hit[0] if hit else 'no row',
        ('34 OK' if hit else 'needs 1 row: fits exactly (row at the old -1, new -1 ends at 0x089D7E78); a 2nd extra '
         'owner needs relocation') if room >= 20 or hit else 'needs relocation')
    row('unlock / owner bit masks', 'FUN_088d5ce8, item elig FUN_088c1ae8/FUN_088c1234/menu FUN_08af3b64, acit',
        '32-bit', 'bit (owner-1)&31', 'bit %d = owner %d (%s)' % ((own - 1) & 31, ((own - 1) & 31) + 1,
                                                                  'Garland' if own == 34 else '?'),
        'needs owner-table checks where an alias matters (unlock list = from unlock table rows, OK)')
    keys = [eb.u('<I', 0x089D6CA8 + 4 * i)[0] for i in range(36)]
    row('name key ptrs (voice_load_p_%s.bin)', 'EBOOT 0x089D6CA8, FUN_088a3a94 loop < 0x23', 'u32 ptr', '0..34 (index = owner)',
        '0x%08X' % keys[own] if own < 36 else '-', '34 OK: slot exists (NULL) -> needs key string + pointer' if own == 34 and keys[34] == 0 else '?')
    names = [eb.u('<I', 0x089CC020 + 4 * i)[0] for i in range(36)]
    ws6 = [eb.u('<I', 0x088D6254 + 4 * k)[0] for k in range(4)]
    w = next((x for x in ws6 if x >> 26 in (0x0A, 0x0B)), ws6[1])
    row('name index (FUN_088d6254)', 'EBOOT 0x089CC020', 'u32', 'table 0..32 (+33 by code), bound %s' % imm_text(w),
        '0x%08X (= string bytes after the table)' % names[own], 'needs code (like owner 33 -> 63)')
    sc = eb.u('<HH', 0x089CF350 + 4 * own)
    row('scenario/Labyrinth names', 'EBOOT 0x089CF350 (FUN_08911d68)', 'u16 name,u16 manikin', '1..31 (+33 patched)',
        sc, '34 OK: zero padding before 0x089CF3DC -> write (name, name)' if sc == (0, 0) else 'check')
    sav = list(eb.at(0x089CBC98, 32))
    row('save record owner list', 'EBOOT 0x089CBC98 (FUN_088cb3b4/FUN_088cb164)', 'u8', '%d owners %s' % (sav.index(0), 'no 23'),
        'not listed -> shared blank record', 'needs record slot (Sora uses friend card 24 via spot33_save; next = card 23, limit 24->23)')
    pre = eb.u('<i', 0x089CB7E8 + 4 * own)[0]
    row('start preset per owner', 'EBOOT 0x089CB7E8 (FUN_088b97d0)', 'i32', '0..34 (35th word = 0)', pre,
        'needs preset id (+ eqpm room)' if pre == -1 else 'set')
    ws = {va: eb.u('<I', va)[0] for va in (0x088F9CA4, 0x088F6C04, 0x08929060)}
    row('assist "drop owner 33 unless Aerith"', 'EBOOT 0x088F9CA4/0x088F6C04/0x08929060', 'code', 'owner 33 only',
        ', '.join(imm_text(x) for x in ws.values()), '34 OK (never special-cased; 33 now 0x7f)')
    cap = eb.u('<I', 0x088B1CF0)[0]
    ab = M['ablt']
    na, = struct.unpack_from('<I', ab, 8)
    mine = [i for i in range(na) if ab[16 + 40 * i + 1] == own]
    row('ablt rows + runtime cap', 'system.bin ablt; cap EBOOT 0x088B1CF0', '40 B', '%d rows, cap %d (%s)' % (na, cap & 0xFFFF, imm_text(cap)),
        'rows %s (ids %s)' % (mine, [hex(struct.unpack_from('<H', ab, 16 + 40 * i)[0]) for i in mine]),
        'needs ~20 rows + cap raise; Cosmos keeps its id 0x2200 row (idx 0 of owner 34) -> new ids from 0x2201 or renumber')

    # ---------------------------------------------------------------- main.bin data
    ob = M['objentry.bin']
    _, no = struct.unpack_from('<II', ob, 0)
    cos = []
    for i in range(no):
        r = ob[8 + 68 * i:8 + 68 * i + 68]
        if r[6] == own:
            cos.append((i, struct.unpack_from('<H', r, 0)[0], r[7], r[8], r[0x24:0x34].split(b'\0')[0].decode()))
    ids = set(struct.unpack_from('<H', ob, 8 + 68 * i)[0] for i in range(no))
    cos.append('free ids < 1338: %d' % len([i for i in range(1, 1338) if i not in ids]))
    row('objentry rows', 'main.bin objentry.bin (RAM buffer 0x13D30 = 1194 rows)', '68 B', '%d rows (%d free)' % (no, 1194 - no),
        cos, 'COLLIDES: FUN_08846ccc(owner,costume,assist) returns the FIRST row (id order) with +6 owner, +7 costume, '
        '!(+8&8), name P_* not *_W -> Cosmos P_ORG800_1P (id 1338, costume 1, kind 0) answers owner 34 costume 1; '
        'new fighter needs ids < 1338 or Cosmos row re-pointed (story check)')
    ch = M['chrp']
    cnt, nr = struct.unpack_from('<II', ch, 0)
    cr = [ch[8 + 144 * i:8 + 144 * i + 144] for i in range(nr) if ch[8 + 144 * i] == own]
    if cr:
        c = cr[0]
        desc = 'lvl %d, +5 %d, burst +6/+7 %d/%d, key %s' % (c[1], c[5], c[6], c[7], c[0x74:0x7C].split(b'\0')[0].decode())
    row('chrp (character params)', 'system.bin chrp', '144 B', '%d rows (hdr %d)' % (nr, cnt), desc if cr else 'no row',
        '34 OK: row exists -> overwrite in place (owner 35+ needs a bigger table)')
    for tag in ('chrl', 'amas', 'acab'):
        b = M[tag]
        n, = struct.unpack_from('<I', b, 8)
        if tag == 'acab':
            owners = [struct.unpack_from('<h', b, 16 + 8 * i)[0] for i in range(n)]
        else:
            owners = [struct.unpack_from('<I', b, 16 + 16 * i)[0] for i in range(n)]
        row(tag, 'system.bin ' + tag, 'index rows', '%d owners, max %d' % (n, max(owners)), 'present' if own in owners else 'absent',
            'append row (reader = count + search; amas missing = menu freeze, see spot33_amas)')
    e = M['eqpm']
    row('eqpm presets', 'system.bin eqpm (RAM 0x09B59AF8..0x09B5DA00 = 16136 B)', 'preset', '%d B now' % len(e),
        'no preset', 'needs buffer move or reuse a preset (room was exactly 1, used by Sora)')
    u = M['uicn']
    row('uicn player icons', 'system.bin uicn (RAM 0xD24 = 420 rows)', '8 B', '%d rows' % struct.unpack_from('<H', u, 2)[0],
        '-', 'append (3 left)')
    asb = M['assist.bin']
    n, = struct.unpack_from('<I', asb, 4)
    aown = [struct.unpack_from('<I', asb, 8 + 104 * i)[0] for i in range(n)]
    row('assist.bin', 'main.bin assist.bin', '104 B', '%d rows, owners %d..%d' % (n, min(aown), max(aown)),
        'present' if own in aown else 'absent', 'append row for an assist version (+ eqaa, _a.objx)')
    bg = M['bgm_entry.bin']
    n, = struct.unpack_from('<I', bg, 8)
    bit = [i for i in range(n) if struct.unpack_from('<Q', bg, 16 + 44 * i + 16)[0] >> own & 1]
    row('BGM owner mask', 'main.bin bgm_entry.bin +16 (64-bit)', '44 B', 'bits 0..63', 'rows with bit %d: %s' % (own, bit),
        '34 OK (fine to owner 63)')

    # ---------------------------------------------------------------- menu overlay
    sel = []
    va = 0x08B0119C
    while mn.u('<i', va)[0] != -1:
        sel.append(mn.u('<i', va)[0]); va += 4
    row('select/panel owner list', 'menu 0x08B0119C (FUN_08aff218)', 'u32', '%d owners, -1 then cell table' % len(sel),
        'listed' if own in sel else 'absent', 'needs relocation + sprite (no room; panel sprites only owners 1..32)')
    qb = [mn.u('<hhhhi', 0x08A864D0 + 12 * i) for i in range(33)]
    row('QB/chara-select grid rows', 'menu 0x08A864D0 (getter FUN_08a85ecc)', '12 B', '33 rows (32 fighters + random 0x20), '
        'mode table follows at 0x08A8665C', 'row' if any(r[4] == own for r in qb) else 'no row', 'needs a 34th row = P0.5 (table move + bounds)')
    gb = [(v, mn.u('<I', v)[0]) for v in (0x08A8032C, 0x08A80438, 0x08A804C8, 0x08A816F0, 0x08A81760)]
    row('grid owner bounds', 'menu FUN_08a80304/08a80428/08a804b8/08a816e0/08a81740', 'code', 'owner 1..34',
        '; '.join('%08X %s' % (v, imm_text(w)) for v, w in gb), '34 OK (owner 35 would fail)')
    pf = mn.u('<H', 0x08B2D168 + 2 * (own - 1))[0]
    row('party frame', 'menu 0x08B2D168[owner-1]', 'u16', '1..31 (33 by spot33_menuart code)', '%d (next table)' % pf,
        'needs code (owner-1 remap like 33)')
    lab = mn.u('<HHh', 0x08B4173C + 6 * own)
    row('Labyrinth face', 'menu 0x08B4173C[owner]', '6 B', '1..32 (+33 patched)', lab,
        '34 OK: zero padding row -> icon id (+ wm GIM)' if lab == (0, 0, -1) else 'check')
    ri = mn.u('<I', 0x08A40720 + 4 * own)[0]
    row('Records icon', 'menu 0x08A40720[owner]', 'u32', '0..32 (+33 in padding)', '0x%X (next data)' % ri,
        'needs code/relocation; Records array is 32 x 0x10C (obj+0x4B8) -> grows only with code')
    nn = mn.u('<H', 0x08A23ACC + 2 * (own - 1))[0]
    row('network names', 'menu 0x08A23ACC[owner-1] (FUN_08a1d7f8)', 'u16', '1..32 (+33 by code)', '%d (next table)' % nn,
        'needs code (extend the owner-33 remap)')
    bf = mn.u('<5h', 0x08AA8864 + 10 * (own - 1))
    row('setup banner frames', 'menu 0x08AA8864[owner-1] (FUN_08aa6148)', '10 B', '1..32 (+33 by FRAME_PATCH)', bf,
        'needs code (FRAME_PATCH generalised)')
    mv = []
    va = 0x08A358FC
    while mn.u('<h', va)[0] != 0:
        mv.append(mn.u('<h', va)[0]); va += 2
    row('Museum viewer owner list', 'menu 0x08A358FC', 's16', '%d owners, 0-terminated, data follows' % len(mv),
        'listed' if own in mv else 'absent', 'needs relocation (costumes 4+ in viewer)')
    k1 = mn.u('<I', 0x08B57FBC + 4 * (own - 1))[0]
    k2 = struct.unpack_from('<I', mn.d, 0xCF58 + 4 * (own - 1))[0]
    k3 = struct.unpack_from('<I', mn.d, 0xF100 + 4 * (own - 1))[0]
    row('menu name keys', 'menu 0x08B57FBC / file 0xCF58 / 0xF100 [owner-1]', 'u32 ptr', '1..33',
        '0x%X / 0x%X / 0x%X' % (k1, k2, k3), 'needs pointers + key string (slots are 0; check NULL-terminator use)')
    tc = mn.u('<I', 0x089DEC04)[0]
    row('title call', 'menu 0x089DEC04', 'code', 'index != owner', imm_text(tc), 'n/a (index 34 is Sora\'s title call)')

    # ---------------------------------------------------------------- battle overlay
    bk = bt.u('<I', 0x08AFBC68 + 4 * own)[0]
    row('battle name keys', 'battle 0x08AFBC68[owner]', 'u32 ptr', '0..33', '0x%X' % bk,
        '34 OK: NULL slot -> needs key string + pointer' if bk == 0 else 'check')
    bn = struct.unpack_from('<ii', bt.d, 0x11E284 + 8 * (own - 1))
    row('battle names', 'battle file 0x11E284[owner-1]', 'i32 x2', '1..32', bn,
        '34 OK: (-1,-1) slot -> name index' if bn == (-1, -1) else 'check')
    print()
    print('save stat blocks (notes/unlocks.md §4): "as" save+0x10D38 + owner*200 (0..35), "vs" save+0x12958 + owner*0x30 '
          '(0..34) -> owner %d %s' % (own, 'fits both' if own <= 34 else ('fits "as" only' if own == 35 else 'needs save work')))


if __name__ == '__main__':
    main()
