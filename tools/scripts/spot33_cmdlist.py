"""Command chart (Customization → Abilities → □ "additional description") for #33 (Sora).

What □ shows (menu overlay FUN_08ad788c → FUN_08ad887c, 2026-10-17): the COMMAND CHART of the selected attack ability
(+ the chain abilities whose ablt +6 parent is that ability, overlaid on it). Data:
- command_list_param.bin (standalone PACKAGE file, loaded by FUN_08ad103c into an exact-size heap block):
  "ACMD" 12 10 08 20, 8×FF; +0x10 s16 n8 (1), +0x12 s16 n40 (581); n8 × 8 B (u16 group-1 id of the "line-drawing
  characters" text, entry 0); n40 × 40 B records, found by LINEAR search on +0 (FUN_08ad113c):
  +0 u16 ability id, +2 s16 header text id (the chart: inputs + ━ lines + "Wall Rush (→)"/"Chase"),
  +4 9 × (s16 input text id, s16 description text id), −1 = end. The screen holds at most 10 rows in total
  (base ability + chains), headers of chains are merged line by line (the LONGER line wins).
- texts = group 1 (OFF4) of text/EN/mess_pk_customize_ability_0.bin (u32 offsets in 4-byte units, entries u32
  length + UTF-16LE, byte j of entry L ^ KEY[(2L+20+j)%32]). Icons: "\\x15" + one char (vanilla statistics:
  ground ◯ presses ∘∙√∛∡∢ (1st..6th), single ∗; air ◯ ∤∥∦∧∨∩, single ∣; ground □ ∪, air □ ∳; description
  tails "/\\x15≘" on every HP hit, "≚" on strong hits, "≙" on area/pull moves). Owner 33 had NO records → empty page.

This step: appends one record per Sora attack ability (0x2100..0x2116, names checked in ability.bin) + their texts
(new group-1 entries after the vanilla 2604, deduplicated). Same file sizes on disc: group 0 gets back the bytes by
emptying unused "Name NN" filler entries (no ablt +4 points at them; the same method as spot33_desc.py, proven in
game), the pak is zero-padded to its old size; command_list_param.bin grows 40 B per record inside its old sectors.
Every vanilla record / text entry stays byte-identical (checked before writing). Re-runnable: our old records + texts
(ids ≥ the first id our records use, referenced by nobody else) are removed and rebuilt; identical → "no change".

  python3 -I spot33_cmdlist.py ISO [--dry]
"""
import os
import re
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ability_text  # noqa: E402
import mpk  # noqa: E402
from ablt_patch import ROW, locate_ablt, package_entry  # noqa: E402
from comb_patch import PACKAGE_ISO_SECTOR, SECTOR, pkg_offset, read_at, use_iso  # noqa: E402
from pkg_put import PACKAGE_INFO_ISO_SECTOR  # noqa: E402
from spot33_desc import FILLER, decode as g0_decode, encode as g0_encode  # noqa: E402
from voice_text import KEY  # noqa: E402

PAK = 'text/EN/mess_pk_customize_ability_0.bin'
CLP = 'command_list_param.bin'
OWNER = 33
VANILLA_TEXTS = 2604                    # group 1 entry count on the clean disc
VANILLA_RECORDS = 581

I = lambda c: '\x15' + c                # noqa: E731  icon
SP = '\x1e＂'                       # one blank cell (vanilla chain charts)
NOTE = lambda t: '\x10脁！' + t + '\x1b'   # noqa: E731  coloured note ("Move OK" style)
HP, K, AREA = I('≘'), I('≚'), I('≙')
GN = [I(c) for c in '∘∙√∛∡∢']           # ground ◯ presses 1..6
AN = [I(c) for c in '∤∥∦∧∨∩']           # air ◯ presses 1..6
GSQ, ASQ = I('∪'), I('∳')


def chart(icons, end):
    return '━'.join(icons) + '━━' + end


def branch(pos, line, sq, end):
    """chain header: '┳' under cell POS of the parent's chart, '┗' + □ on LINE (2 = first line below)"""
    pad = SP * pos
    return '\n'.join([pad + '┳'] + [pad + '┃'] * (line - 2) + [pad + '┗' + sq + '━━' + end])


HS6 = 'Horizontal Slash: six rapid slashes'
AF5 = 'Aerial Finish: five sweeps, sending foe flying/' + K
FIRE = 'Unleash a burst of swirling flames around you/' + HP + AREA + K
THUNDER = "Sparks mark the foe's position, then three bolts\nof lightning strike that spot/" + HP + K
FLEAP = 'Finishing Leap: leap and strike twice, sending foe flying/' + K
UPPER = 'Slash upward, launching foe high into the air/'
GUARDB = 'Lunge with a spinning strike that sends foe flying/'

# ability id: (expected ability.bin name, header, [(input, description), ...])  ≤ 9 rows each; chains 1 row
CHARTS = {
    0x2100: ('Combo Plus', chart(GN, 'Wall Rush (→)'), [
        (GN[0], 'Slash three times in quick succession'),
        (GN[1], 'Follow up with two more swift slashes'),
        (GN[2], 'Spin in place, striking four times'),
        (GN[3], 'Slash in a wide arc'),
        (GN[4], 'Bring the Keyblade down with a heavy swing'),
        (GN[5], 'Swing with full force, sending foe flying/' + K)]),
    0x2101: ('Air Combo Plus', chart(AN[:5], 'Wall Rush (↑)'), [
        (AN[0], 'Slash in midair'),
        (AN[1], 'Slash again with a backhand swing'),
        (AN[2], 'Spin with a wide slash'),
        (AN[3], HS6),
        (AN[4], AF5)]),
    0x2102: ('Explosion', GSQ + '━━Wall Rush (→)', [
        (GSQ, 'Spin with four strikes; orbs of light hold foe in\nplace, then a magic blast hits all around/' + HP + AREA + K)]),
    0x2103: ('Aerial Finish', ASQ + '━━Wall Rush (↘)', [
        (ASQ, 'Sweep the Keyblade around five times in midair;\nthe last sweep sends foe flying/' + HP + K)]),
    0x2104: ('Slide Dash', chart(GN[:3] + AN[3:6], 'Wall Rush (↑)'), [
        (GN[0], 'Dash in from afar with a sliding strike'),
        (GN[1], 'Slash, then strike while rising'),
        (GN[2], 'Launch foe upward with a rising slash'),
        (AN[3], 'Chase foe in midair with three slashes'),
        (AN[4], HS6),
        (AN[5], AF5)]),
    0x2105: ('Combo Plus > Upper Slash', branch(3, 2, GSQ, 'Wall Rush (↑)'), [
        (GSQ, UPPER + NOTE('After swing 2 or 5') + '/' + HP + K)]),
    0x2106: ('Air Combo > Retaliating Slash', branch(5, 4, ASQ, 'Wall Rush (↘)'), [
        (ASQ, 'Whirl, striking three times; the last sends\nfoe flying/' + NOTE('After slash 3') + '/' + HP + K)]),
    0x2107: ('Slide Dash > Upper Slash', branch(1, 2, GSQ, 'Wall Rush (↑)'), [
        (GSQ, UPPER + NOTE('Right after the dash') + '/' + HP + K)]),
    0x2108: ('Aerial Spiral', chart(AN[:5], 'Wall Rush (↑)'), [
        (AN[0], 'Spiral up at a foe above, slashing'),
        (AN[1], 'Slash again with a backhand swing'),
        (AN[2], 'Spin with a wide slash'),
        (AN[3], HS6),
        (AN[4], 'Six more slashes; the last sends foe flying/' + K)]),
    0x2109: ('Combo Plus > Guard Break', branch(1, 3, GSQ, 'Wall Rush (→)'), [
        (GSQ, GUARDB + NOTE('After swing 3 or 4') + '/' + HP + K)]),
    0x210a: ('Slide Dash > Guard Break', branch(3, 3, GSQ, 'Wall Rush (→)'), [
        (GSQ, GUARDB + NOTE('After hit 2') + '/' + HP + K)]),
    0x210b: ('Air Combo > Magnet Burst', branch(3, 3, ASQ, 'Wall Rush (↓)'), [
        (ASQ, 'A magnetic sphere pulls foe in, then bursts/' + NOTE('After slash 2') + '/' + HP + AREA + K)]),
    0x210c: ('Aerial Dive', chart(AN[:5], 'Wall Rush (↑)'), [
        (AN[0], 'Dive at a foe below, slashing'),
        (AN[1], 'Slash again with a backhand swing'),
        (AN[2], 'Spin with a wide slash'),
        (AN[3], HS6),
        (AN[4], FLEAP)]),
    0x210d: ('Air Combo > Horizontal Slash', branch(7, 5, ASQ, 'Wall Rush (↘)'), [
        (ASQ, 'Three wide slashes: left, right, then down/' + NOTE('After the six slashes') + '/' + HP + K)]),
    0x210e: ('Air Combo > Aerial Sweep', branch(1, 2, ASQ, 'Wall Rush (↓)'), [
        (ASQ, 'A big midair sweep that sends foe flying/' + NOTE('After slash 1') + '/' + HP + K)]),
    0x210f: ('Dodge Slash', chart(GN[:3] + AN[3:5], 'Wall Rush (↑)'), [
        (GN[0], 'Spin toward foe, striking four times'),
        (GN[1], 'Three heavy slashes on the ground'),
        (GN[2], 'Slash, then launch foe with a rising strike'),
        (AN[3], 'Chase foe with two slashes in midair'),
        (AN[4], FLEAP)]),
    0x2110: ('Dodge Slash > Explosion', branch(1, 2, GSQ, 'Wall Rush (→)'), [
        (GSQ, 'Orbs of light hold foe in place, then a magic\nblast hits all around/' + NOTE('After the spin') + '/' + HP + AREA + K)]),
    0x2111: ('Firaga', GSQ, [(GSQ, FIRE)]),
    0x2112: ('Thundaga', GSQ, [(GSQ, THUNDER)]),
    0x2113: ('Blizzaga', GSQ, [(GSQ, 'Fire a spread of three ice shards straight ahead/' + HP + K)]),
    0x2114: ('Aerial Firaga', ASQ, [(ASQ, 'Unleash swirling flames around you in midair/' + HP + AREA + K)]),
    0x2115: ('Aerial Thundaga', ASQ, [(ASQ, THUNDER)]),
    0x2116: ('Aerial Blizzaga', ASQ, [(ASQ, 'Fire a spread of three ice shards from midair/' + HP + K)]),
}


# ---------- OFF4 (group 1): raw entries kept byte-exact ----------
def off4_split(g):
    assert g[:4] == b'OFF4', g[:4]
    n, = struct.unpack_from('<I', g, 4)
    offs = struct.unpack_from('<%dI' % n, g, 8)
    raws = []
    for lid, o in enumerate(offs):
        assert o, 'empty OFF4 slot %d (not expected in this file)' % lid
        ln, = struct.unpack_from('<I', g, o * 4)
        raws.append(g[o * 4:o * 4 + 4 + ln])
    return raws


def off4_text(raw, lid):
    return bytes(c ^ KEY[(2 * lid + 20 + j) % 32] for j, c in enumerate(raw[4:])).decode('utf-16-le').split('\0')[0]


def off4_entry(text, lid):
    b = text.encode('utf-16-le') + b'\0\0'
    b += b'\0' * ((-len(b)) % 4)
    return struct.pack('<I', len(b)) + bytes(c ^ KEY[(2 * lid + 20 + j) % 32] for j, c in enumerate(b))


def off4_join(raws):
    n = len(raws)
    pos = 8 + 4 * n
    offs, body = [], bytearray()
    for r in raws:
        assert (pos + len(body)) % 4 == 0
        offs.append((pos + len(body)) // 4)
        body += r
    return b'OFF4' + struct.pack('<I', n) + struct.pack('<%dI' % n, *offs) + bytes(body)


# ---------- disc reads ----------
def ablt_info(iso):
    """{ability id: (name, desc id)} for every ablt row + set of all +4 ids"""
    with open(iso, 'rb') as f:
        info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
        off, size = package_entry(info, 'general_archive/main/EN/main_lang.bin')
        lang = read_at(f, PACKAGE_ISO_SECTOR * SECTOR + off, size)
        m = [e for e in mpk.entries(lang) if e[0] == 'ability.bin'][0]
        names = ability_text.decode(lang[m[1]:m[1] + m[2]])
        ablt, count = locate_ablt(f, info)
        f.seek(ablt)
        tab = f.read(16 + count * ROW)
    n, = struct.unpack_from('<I', tab, 8)
    rows, used = {}, set()
    for i in range(n):
        aid, nm, ds = struct.unpack_from('<HHH', tab, 16 + i * ROW)
        rows[aid] = names[nm + 1].rstrip('\0') if nm + 1 < len(names) else None
        used.add(ds)
    return rows, used


def clp_split(d):
    assert d[:4] == b'ACMD', d[:4]
    n8, n40 = struct.unpack_from('<hh', d, 0x10)
    base = 0x14 + n8 * 8
    assert len(d) == base + n40 * 40, 'command_list_param.bin size %d != header %d' % (len(d), base + n40 * 40)
    return d[:base], [d[base + i * 40:base + i * 40 + 40] for i in range(n40)]


def main():
    iso = sys.argv[1]
    dry = '--dry' in sys.argv
    use_iso(iso)
    with open(iso, 'rb') as f:
        pst, psz = pkg_offset(PAK)
        pak = read_at(f, pst, psz)
        cst, csz = pkg_offset(CLP)
        clp = read_at(f, cst, csz)

    # --- guards: names of Sora's rows ---
    rows, used = ablt_info(iso)
    for aid, (name, _, _) in CHARTS.items():
        assert rows.get(aid) == name, 'ablt %#x is %r, expected %r' % (aid, rows.get(aid), name)

    # --- command_list_param.bin ---
    head, recs = clp_split(clp)
    ours = [r for r in recs if r[1] == OWNER]
    other = [r for r in recs if r[1] != OWNER]
    assert len(other) == VANILLA_RECORDS, 'expected %d non-Sora records, found %d' % (VANILLA_RECORDS, len(other))
    assert recs[:len(other)] == other, 'Sora records are not at the end of command_list_param.bin'

    # --- mess pak ---
    assert pak[:8] == b'mess pak', pak[:8]
    ng, = struct.unpack_from('<H', pak, 10)
    assert ng == 2, ng
    groups = [struct.unpack_from('<II', pak, 0x10 + 8 * i) for i in range(ng)]
    g0 = pak[groups[0][0]:groups[0][0] + groups[0][1]]
    g1 = pak[groups[1][0]:groups[1][0] + groups[1][1]]
    raws = off4_split(g1)
    assert off4_join(raws) == g1, 'group 1 does not re-encode exactly'
    assert len(raws) >= VANILLA_TEXTS
    # texts owned by our old records: every id >= VANILLA_TEXTS must be referenced by our records only
    refs_other = {v for r in other for v in struct.unpack_from('<19h', r, 2) if v >= 0}
    assert max(refs_other) < VANILLA_TEXTS, 'a non-Sora record points past the vanilla texts'
    refs_ours = {v for r in ours for v in struct.unpack_from('<19h', r, 2) if v >= 0}
    assert all(v >= VANILLA_TEXTS for v in refs_ours), 'old Sora records point at vanilla texts'
    assert len(raws) == VANILLA_TEXTS or refs_ours == set(range(VANILLA_TEXTS, len(raws))), \
        'group 1 has extra entries not owned by Sora records'
    base_raws = raws[:VANILLA_TEXTS]
    assert off4_text(base_raws[1833], 1833) == I('∘') and off4_text(base_raws[0], 0) == '━┃┳┣┗┻╋', 'vanilla texts moved'

    # --- build texts + records ---
    new_texts, index = [], {}

    def tid(t):
        if t not in index:
            index[t] = VANILLA_TEXTS + len(new_texts)
            new_texts.append(t)
        return index[t]

    new_recs = []
    for aid, (name, hdr, pairs) in CHARTS.items():
        assert 1 <= len(pairs) <= 9
        vals = [tid(hdr)]
        for a, b in pairs:
            vals += [tid(a), tid(b)]
        vals += [-1] * (19 - len(vals))
        new_recs.append(struct.pack('<H19h', aid, *vals))
    out_raws = base_raws + [off4_entry(t, VANILLA_TEXTS + k) for k, t in enumerate(new_texts)]
    for k, t in enumerate(new_texts):
        assert off4_text(out_raws[VANILLA_TEXTS + k], VANILLA_TEXTS + k) == t
    new_g1 = off4_join(out_raws)
    new_head = bytearray(head)
    struct.pack_into('<h', new_head, 0x12, len(other) + len(new_recs))
    new_clp = bytes(new_head) + b''.join(other) + b''.join(new_recs)
    clp_room = -(-csz // SECTOR) * SECTOR

    # --- group 0: empty unused fillers until the pak keeps its old size ---
    t0 = g0_decode(g0)
    e0 = g0_encode(t0)
    assert e0 == g0[:len(e0)] and not g0[len(e0):].strip(b'\0'), 'group 0 does not re-encode exactly'

    def pak_size(g0len):
        p = 0x10 + 8 * ng
        p += (-p) % 16
        p += g0len
        p += (-p) % 16
        return p + len(new_g1)

    blanked = 0
    for k in range(len(t0) - 1, -1, -1):
        if pak_size(len(g0_encode(t0))) <= psz:
            break
        if k not in used and FILLER.match(t0[k].decode('utf-16-le', 'replace')):
            t0[k] = b'\0\0'
            blanked += 1
    new_g0 = g0_encode(t0)
    assert pak_size(len(new_g0)) <= psz, 'not enough unused filler entries to keep the pak size'
    out = bytearray(pak[:0x10 + 8 * ng])
    for i, b in enumerate([new_g0, new_g1]):
        out += b'\0' * ((-len(out)) % 16)
        struct.pack_into('<II', out, 0x10 + 8 * i, len(out), len(b))
        out += b
    out += b'\0' * (psz - len(out))
    out = bytes(out)

    # --- checks: everything vanilla unchanged ---
    t0n = g0_decode(new_g0)
    old0 = g0_decode(g0)
    changed0 = [k for k in range(len(old0)) if old0[k] != t0n[k]]
    assert all(k not in used and t0n[k] == b'\0\0' for k in changed0), 'a used group-0 entry changed'
    assert off4_split(out[struct.unpack_from('<I', out, 0x18)[0]:][:len(new_g1)])[:VANILLA_TEXTS] == base_raws
    assert new_clp[0x14 + 8:0x14 + 8 + 40 * len(other)] == clp[0x14 + 8:0x14 + 8 + 40 * len(other)]

    print('Sora command charts: %d records, %d new texts (group 1 ids %d..%d)'
          % (len(new_recs), len(new_texts), VANILLA_TEXTS, VANILLA_TEXTS + len(new_texts) - 1))
    print('%s: %d -> %d bytes (sectors hold %d); %s: %d -> %d bytes, group 0 %d -> %d (%d fillers emptied now, '
          '%d differ from this disc)' % (CLP, csz, len(new_clp), clp_room, PAK, psz, len(out), len(g0), len(new_g0),
                                         blanked, len(changed0)))
    if '-v' in sys.argv:
        for aid, (name, hdr, pairs) in CHARTS.items():
            print('%#x %s\n   %s' % (aid, name, hdr.replace('\n', '\n   ')))
            for a, b in pairs:
                print('      %s | %s' % (a, b.replace('\n', ' / ')))
    if new_clp == clp and out == pak:
        print('no change')
        return
    if dry:
        print('--dry: nothing written')
        return
    assert len(new_clp) <= clp_room and len(out) <= -(-psz // SECTOR) * SECTOR
    with tempfile.TemporaryDirectory() as t:
        for path, data, old in ((CLP, new_clp, clp), (PAK, out, pak)):
            if data == old:
                continue
            p = os.path.join(t, os.path.basename(path))
            open(p, 'wb').write(data)
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                               check=True, capture_output=True, text=True)
            print(r.stdout.strip())


if __name__ == '__main__':
    main()
