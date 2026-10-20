"""Sora's one-line style blurb in the "Play as this character?" dialog (RR-17 cosmetic, 2026-10-19, static).

Mat/coordinator (test348/349, Labyrinth > Character Select): other fighters show "[Paradigm Commando] Uses one of
three roles ..." under the question, Sora shows an empty band.

Where the text comes from (menu overlay + texts, static):
  The character-select grid row table (menu 0x08A864D0, getter FUN_08a85ecc; owner_tables qb_grid_rows, "5 screens")
  has 12-B rows (u16 picture, u16 name picture, u16 logo, u16 CHARACTER NUMBER, i32 owner). The u16 at +6 is not the
  owner: it is the blurb text id - Kain 24, Tifa 25, Laguna 26, Yuna 27, Vaan 28, Lightning 29, Prishe 30,
  Gilgamesh 31, Feral Chaos 32 (owners 24/26/27/28/30/31/29/25/32), owners 1..23 = 1..23. Sora's row (row 31, set by
  roster_patch qb-row / spot33_qbpics) has 33. Each screen's text pack has a 33-entry blurb group (#0 = "You cannot
  select this character yet.", #1..#32 = blurbs), and the text lookup returns the empty string for id >= count
  (FUN_0887a800) -> Sora's id 33 = empty band.
  Blurb groups (same 33 entries in each): mess_pk_chara_select_0 group 2 (Quick Battle / Arcade / Labyrinth select),
  mess_pk_creation_room_0 group 5, mess_pk_party_setting_0 group 5, mess_pk_story_mode_0 group 1,
  mess_pk_update_list_0 group 7.
Fix: append text id 33 = Sora's blurb to all five groups (same layout as the natives: "[Title]\\n<U+3000>line\\n<U+3000>line",
lines no longer than the natives' 37-43 characters). No code change, no other entry touched (re-encode checked
byte-for-byte for ids 0..32 and every other group). Guards: each group decodes to exactly 33 entries with the
native first/29th/last entries (or 34 with ours as the last); refuses the clean dump and an ISO PPSSPP has open.
--dry writes nothing, --rollback removes entry 33 again. Re-runnable ("already").

  python3 -I spot33_selectblurb.py ISO [--dry] [--rollback]
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

GROUPS = {'text/EN/mess_pk_chara_select_0.bin': 2, 'text/EN/mess_pk_creation_room_0.bin': 5,
          'text/EN/mess_pk_party_setting_0.bin': 5, 'text/EN/mess_pk_story_mode_0.bin': 1,
          'text/EN/mess_pk_update_list_0.bin': 7}
SORA_ID = 33
BLURB = '[Keyblade Master]\n　Chains long combos, magic and Reflect\n　into a relentless offense.\0'
FIRST = 'You cannot select this character yet.\0'
LIGHTNING = '[Paradigm Commando]\n　Uses one of three roles to adapt to\n　the pace of battle.\0'
LAST_TAG = '[The Omega and the Alpha]'


def u(s):
    return s.encode('utf-16-le')


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


def rebuild(d, gi, raws):
    """mess pak with group gi re-encoded from raws; every other group byte-identical (spot33_ownername layout)"""
    ng, = struct.unpack_from('<H', d, 10)
    groups = [struct.unpack_from('<II', d, 0x10 + 8 * i) for i in range(ng)]
    bodies = [d[go:go + gs] for go, gs in groups]
    bodies[gi] = encode(raws)
    out = bytearray(d[:groups[0][0]])
    for i, b in enumerate(bodies):
        out += b'\0' * ((-len(out)) % 16)
        struct.pack_into('<II', out, 0x10 + 8 * i, len(out), len(b))
        out += b
    out += b'\0' * ((-len(out)) % 16)
    for i, (go, gs) in enumerate(groups):
        no, ns = struct.unpack_from('<II', out, 0x10 + 8 * i)
        if i == gi:
            assert decode(bytes(out[no:no + ns])) == raws
        else:
            assert out[no:no + ns] == d[go:go + gs]
    return bytes(out)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    assert len(args) == 1, __doc__
    iso = args[0]
    dry, rollback = '--dry' in sys.argv, '--rollback' in sys.argv
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the clean dump'
    if not dry:
        r = subprocess.run(['pgrep', '-a', '-x', 'PPSSPPSDL'], capture_output=True, text=True)
        assert os.path.abspath(iso) not in r.stdout and os.path.basename(iso) not in r.stdout, \
            'PPSSPP has this ISO open - stop'
    longest = max(len(x) for x in BLURB.rstrip('\0').split('\n'))
    assert longest <= 40, longest
    plan = []
    for path, gi in GROUPS.items():
        d = get(iso, path)
        assert d[:8] == b'mess pak', (path, d[:8])
        ng, = struct.unpack_from('<H', d, 10)
        go, gs = struct.unpack_from('<II', d, 0x10 + 8 * gi)
        body = d[go:go + gs]
        raws = decode(body)
        e = encode(raws)
        assert e == body[:len(e)] and not body[len(e):].strip(b'\0'), '%s group %d does not re-encode - stop' % (path, gi)
        assert raws[0] == u(FIRST) and raws[29] == u(LIGHTNING) and u(LAST_TAG) in raws[32], \
            '%s group %d is not the 33-entry blurb list - stop' % (path, gi)
        if len(raws) == SORA_ID + 1:
            assert raws[SORA_ID] == u(BLURB), '%s group %d entry 33 is not ours - stop' % (path, gi)
            state = 'ours'
        else:
            assert len(raws) == SORA_ID, '%s group %d has %d entries - stop' % (path, gi, len(raws))
            state = 'vanilla'
        want = 'vanilla' if rollback else 'ours'
        print('  %s group %d: %s -> %s%s' % (path, gi, state, want, ' already' if state == want else ''))
        if state != want:
            new = rebuild(d, gi, raws[:SORA_ID] if rollback else raws + [u(BLURB)])
            plan.append((path, new, len(d)))
    for path, new, old in plan:
        print('  %s: %d -> %d bytes%s' % (path, old, len(new), ' (dry)' if dry else ''))
        if not dry:
            put_file(iso, path, new)
    if not dry:
        for path, gi in GROUPS.items():
            d = get(iso, path)
            go, gs = struct.unpack_from('<II', d, 0x10 + 8 * gi)
            raws = decode(d[go:go + gs])
            assert len(raws) == (SORA_ID if rollback else SORA_ID + 1), (path, len(raws))
    print('dry run, nothing written' if dry else ('nothing to do' if not plan else 'done'))


if __name__ == '__main__':
    main()
