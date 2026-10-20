"""Move descriptions for #33 (Sora) in Customization → Abilities (the info panel showed "WOL 15", "Ultimecia 59"…).
The panel text is NOT ability.bin: ablt +4 indexes group 0 of text/EN/mess_pk_customize_ability_0.bin.
File = "mess pak", u16 1, u16 group count (2), u32 0, then (u32 offset, u32 size) per group, groups 16-aligned.
Group 0 has the ability.bin layout (u16 offset table ×2 bytes, entry L = u16 byte length + UTF-16LE XOR
KEY[(2L+18+j)%32]); description id d = entry d + 1. Offsets are u16 → group 0 must stay < 131,070 bytes.
Sora's rows (spot33_moves.py / spot33_movenames.py) point at unused placeholders 395–398 and 1042/1044/1046/1048.
Cloud's style: "[Range] what it does.\\n…" and an optional coloured last line "\\x10Łａ…\\x1b".
Same-size rule: a GROWN text table garbled in RAM before (ability.bin, notes/roster.md), so group 0 is re-encoded
at its old size: unused filler entries ("Chaos 70", no ablt row points at them) become empty to make room.

  python3 -I spot33_desc.py ISO
"""
import os
import re
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, mpk_member, package_entry  # noqa: E402
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from pkg_put import PACKAGE_INFO_ISO_SECTOR  # noqa: E402
from spot33_save import arc_split  # noqa: E402
from voice_text import KEY  # noqa: E402

FILE = 'text/EN/mess_pk_customize_ability_0.bin'
DESC = {                               # ablt +4 description id → text
    395: '[Combo] Twelve ground strikes, then\na blow that sends foes flying.',
    396: '[Combo] Air strikes, Horizontal\nSlash, then Aerial Finish.',
    397: '[Close] Plant the Keyblade: a\nmagic blast hits all around.',
    398: '[Close] Five full Keyblade\nsweeps in midair.',
    1042: '[Mid] Dash in, launch the foe\nand rave it in midair.',
    1044: '[Combo] End a ground combo with\na slash that launches foes.',
    1046: '[Combo] A spinning counter of\nKeyblade strikes in midair.',
    1048: '[Combo] Follow Slide Dash with\na slash that launches foes.',
    1050: '[Close] Spiral up at a foe above;\nends in Horizontal Slash.',
    1052: '[Combo] A spinning lunge that\nsends foes flying.',
    1054: '[Combo] A spinning lunge that\nsends foes flying.',
    1056: '[Combo] Whirl, then raise your\nKeyblade in a burst of power.',
    1058: '[Close] Dive at a foe below;\nends in a Finishing Leap.',
    1060: '[Combo] A flurry of horizontal\nslashes in midair.',
    1062: '[Combo] A whirling midair spin\nthat sends foes flying.',
    1064: '[Close] Spin, heavy strikes, then\nlaunch into a Finishing Leap.',
    1066: '[Combo] Plant the Keyblade: a\nmagic blast hits all around.',
    1068: '[Close] Unleash a burst of\nswirling flames around you.',
    1070: '[Long] Call down strikes of\nthunder on your foe.',
    1072: '[Long] Fire a spread of\nice shards.',
    1074: '[Close] Unleash swirling\nflames around you in midair.',
    1076: '[Long] Call down thunder\nfrom midair.',
    1078: '[Long] Fire ice shards\nfrom midair.',
}
FILLER = re.compile(r'^[A-Za-z]+ ?\d+\0$')     # "WOL 15", "Kefka57", "Chaos 70"


def used_ids(iso):
    """every ablt +4 (description id) in system.bin"""
    with open(iso, 'rb') as f:
        info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
        pkg = PACKAGE_ISO_SECTOR * SECTOR
        off, size = package_entry(info, 'general_archive/main/main.bin')
        main_bin = read_at(f, pkg + off, size)
        so, ss = mpk_member(f, pkg + off, 'system.bin')
    so -= pkg + off
    ablt = next(c[2] for c in arc_split(main_bin[so:so + ss])[1] if c[1] == b'ablt')
    n, = struct.unpack_from('<I', ablt, 8)
    return {struct.unpack_from('<H', ablt, 16 + i * 40 + 4)[0] for i in range(n)}


def decode(g):
    n, = struct.unpack_from('<H', g, 0)
    offs = struct.unpack_from('<%dH' % (n + 1), g, 0)
    out = []
    for lid in range(1, n + 1):
        p = offs[lid] * 2
        ln, = struct.unpack_from('<H', g, p)
        out.append(bytes(c ^ KEY[(2 * lid + 18 + j) % 32] for j, c in enumerate(g[p + 2:p + 2 + ln])))
    return out


def encode(raws):
    n = len(raws)
    out = bytearray(2 * (n + 1))
    struct.pack_into('<H', out, 0, n)
    for lid, raw in enumerate(raws, 1):
        out += b'\0' * (len(out) % 2)
        struct.pack_into('<H', out, 2 * lid, len(out) // 2)
        out += struct.pack('<H', len(raw)) + bytes(c ^ KEY[(2 * lid + 18 + j) % 32] for j, c in enumerate(raw))
    out += b'\0' * (len(out) % 2)
    return bytes(out)


def main():
    iso = sys.argv[1]
    use_iso(iso)
    st, sz = pkg_offset(FILE)
    with open(iso, 'rb') as f:
        d = read_at(f, st, sz)
    assert d[:8] == b'mess pak', d[:8]
    ng, = struct.unpack_from('<H', d, 10)
    groups = [struct.unpack_from('<II', d, 0x10 + 8 * i) for i in range(ng)]
    g0 = d[groups[0][0]:groups[0][0] + groups[0][1]]
    raws = decode(g0)
    e = encode(raws)
    assert e == g0[:len(e)] and not g0[len(e):].strip(b'\0'), 'group 0 does not re-encode exactly'   # (+ our padding)
    for k, t in DESC.items():
        raws[k] = (t + '\0').encode('utf-16-le')              # entry k + 1 = list index k
    used = used_ids(iso)
    blanked = 0
    for k in range(len(raws) - 1, -1, -1):                  # empty unused fillers from the end until it fits
        if len(encode(raws)) <= len(g0):
            break
        if k not in used and k not in DESC and FILLER.match(raws[k].decode('utf-16-le', 'replace')):
            raws[k] = b'\0\0'
            blanked += 1
    g = encode(raws)
    assert len(g) <= len(g0), 'not enough filler entries to stay the same size'
    print('%d unused filler entries emptied' % blanked)
    g0 = g + b'\0' * (len(g0) - len(g))
    out = bytearray(d[:groups[0][0]])
    bodies = [g0] + [d[o:o + s] for o, s in groups[1:]]
    for i, b in enumerate(bodies):
        out += b'\0' * ((-len(out)) % 16)
        struct.pack_into('<II', out, 0x10 + 8 * i, len(out), len(b))
        out += b
    out += b'\0' * ((-len(out)) % 16)
    for k, t in DESC.items():
        print('description %d: %s' % (k, t.replace('\n', ' / ')))
    print('group 0: %d -> %d bytes, file %d -> %d' % (groups[0][1], len(g0), len(d), len(out)))
    if bytes(out) == d:
        print('no change')
        return
    if '--dry' in sys.argv:          # (added 2026-10-17: a --dry run used to write the ISO)
        print('--dry: nothing written')
        return
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, os.path.basename(FILE))
        open(p, 'wb').write(out)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main()
