"""Sora's outfits (KH2 Drive Forms), data only. notes/outfits.md.

Outfit 2 = Limit Form, 3 = Master Form (Mat 2026-10-16: "Limit and master"), 4 = Valor, 5 = Wisdom, 6 = Final:
Codex's texture-only variants (codex/inbox/20261016-drive-outfits, apply_variant.py) applied to the CURRENT 1P model.
Only the two Sora textures (sora_tex0 body, sora_tex1 face/clothing) change; every other byte stays the 1P model's, so
motions/size stay identical. Re-runnable ("already"); --dry writes nothing.

How the game picks costumes (notes/outfits.md §1): costume k = objentry row (owner 33, +7 = k, kind 0) -> files
obj/<NAME>.gmo/.cosx/.exex + menu/JP/battle/chara_image/<NAME>.gim. Costumes 2/3 need the costume flags of the EBOOT
unlock table row; costumes 4..12 (the game's DLC slots) are offered whenever such an objentry row exists.

Parts (all guarded):
  textures   obj/P_SEV120_2P/3P.gmo <- 1P model + Limit / Master textures      (after spot33_2p.py + spot33_p2fix.py)
  extra      obj/P_SEV120_4P..6P.gmo <- 1P model + Valor / Wisdom / Final textures; .cosx/.exex + HUD face <- 1P's
             (new PACKAGE files); objentry rows P_SEV120_4P..6P (ids 1457..1459, +7 = 4..6, copies of the 2P row)
  unlock     EBOOT unlock row of owner 33 (0x089D7D98): costume-2/3 flags -1 (never) -> 1 (set by every new save,
             FUN_088b0788; the game's own "owned from start" flag) -> outfits 2/3 selectable
  events     obj/p_sev120.objx p_se: costume-only events (condition byte main +9 / one-shot +7 = costume+1) made
             identical for every outfit: Keyblade trails (op 0x2a) of costume 1 -> any costume, the costume 2/3/4
             duplicates (Cloud's per-costume sword-trail variants) and the costume-2-only sounds (one-shot op 3, Cloud
             2P) -> 0xFF (never). In place, same size. Must run AFTER every p_se writer (end of build_sora.sh).

  python3 -I spot33_outfits.py ISO [--dry] [--no-events | --events-only]
Note: the mirror-match CPU uses the 2P model. Outfits 4+ are not in the Museum viewer (its owner table has no Sora).
"""
import hashlib
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
PKG = os.path.join(ROOT, 'codex', 'inbox', '20261016-drive-outfits')
sys.path.insert(0, HERE)
sys.path.insert(0, PKG)
sys.dont_write_bytecode = True
import fep_edit as E  # noqa: E402
import mpk  # noqa: E402
from build_variants import patch, tex  # noqa: E402
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402

SLOTS = [('obj/P_SEV120_2P.gmo', 'Limit'), ('obj/P_SEV120_3P.gmo', 'Master')]
EXTRA = [(4, 'Valor', 1457), (5, 'Wisdom', 1458), (6, 'Final', 1459)]      # costume, form, objentry id
NAME = 'P_SEV120_%dP'
FILES = ['obj/%s.gmo', 'obj/%s.cosx', 'obj/%s.exex', 'menu/JP/battle/chara_image/%s.gim']
OBJENTRY_MAX = 0x13d30                   # FUN_08847158 buffer 0x09afee58; battle.bin spec buffer follows at 0x09b12b88
EBOOT_ISO = 560 * 0x800                  # plain ELF since test20
UNLOCK_ROW_VA = 0x089D7BE0 + 22 * 20     # row 22 (was Chaos) = owner 33 since test20
UNLOCK_OLD = (33, -1, -1, -1, 3623)
UNLOCK_NEW = (33, -1, 1, 1, 3623)
UNLOCK_CATALOG = (33, 925, 1, 1, 3623)    # spot33_catalog.py: Sora bought in the PP Catalog (flag 925); costumes kept
NEVER = 0xFF                             # condition byte 0xFF = costume 254 = never


def sha(d):
    return hashlib.sha256(d).hexdigest()


def get(iso, path):
    """file bytes, or None if PATH is not in the ISO's PACKAGE_INFO"""
    use_iso(iso)
    try:
        st, sz = pkg_offset(path)
    except SystemExit:
        return None
    with open(iso, 'rb') as f:
        return read_at(f, st, sz)


def put(iso, path, data):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, os.path.basename(path))
        open(p, 'wb').write(data)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p], check=True,
                           capture_output=True, text=True)
        print('    ' + r.stdout.strip())


def variant_of(src, form):
    """1P model bytes -> that model with the form's two textures (guards like apply_variant.apply)"""
    v = Path(PKG) / 'output' / form
    for name, f, t in (('sora_tex0', 'restore-body.gim', 'body.gim'), ('sora_tex1', 'restore-face.gim', 'face-clothing.gim')):
        old = tex(src, name)[1]
        if old != (Path(PKG) / 'output' / f).read_bytes():
            sys.exit('1P %s is not the textures the variants were made from: regenerate the variants' % name)
    out = patch(src, (v / 'body.gim').read_bytes(), (v / 'face-clothing.gim').read_bytes())
    assert len(out) == len(src)
    return out


def is_sora_variant(cur, one):
    """an older build of an outfit model: same size, only the two texture payloads differ from the 1P model"""
    if cur is None or len(cur) != len(one):
        return False
    out = bytearray(cur)
    for name in ('sora_tex0', 'sora_tex1'):
        at, old = tex(one, name)
        out[at:at + len(old)] = old
    return bytes(out) == one


# ---------------------------------------------------------------------------------------------------- textures
def textures(iso, dry, one):
    for path, form in SLOTS:
        want = variant_of(one, form)
        cur = get(iso, path)
        if cur == want:
            print('%s: already %s Form' % (path, form))
            continue
        assert cur == one or is_sora_variant(cur, one), '%s is neither the 1P model nor an outfit build - stop' % path
        print('%s <- 1P model + %s Form textures%s' % (path, form, ' (dry)' if dry else ''))
        if not dry:
            put(iso, path, want)


# ---------------------------------------------------------------------------------------------------- extra outfits
def extra_files(iso, dry, one):
    src = {ext: get(iso, pat % (NAME % 1)) for ext, pat in zip(('gmo', 'cosx', 'exex', 'gim'), FILES)}
    assert all(src.values()), 'P_SEV120_1P files missing'
    for k, form, _ in EXTRA:
        for ext, pat in zip(('gmo', 'cosx', 'exex', 'gim'), FILES):
            path = pat % (NAME % k)
            want = variant_of(one, form) if ext == 'gmo' else src[ext]
            cur = get(iso, path)
            if cur == want:
                print('%s: already (%s)' % (path, form if ext == 'gmo' else 'copy of 1P'))
                continue
            if cur is not None:      # only overwrite our own older build
                ok = is_sora_variant(cur, one) if ext == 'gmo' else len(cur) == len(want)
                assert ok, '%s exists and is not an outfit build - stop' % path
            print('%s <- %s%s' % (path, '1P model + %s Form textures' % form if ext == 'gmo' else '1P copy',
                                  ' (new file)' if cur is None else '') + (' (dry)' if dry else ''))
            if not dry:
                put(iso, path, want)


def objentry_rows(ob):
    """-> new objentry.bin bytes (or the same) with rows P_SEV120_4P.. appended (sorted by id, ids above all)"""
    head, n = struct.unpack_from('<II', ob, 0)
    assert head == 12 and len(ob) == 8 + n * 68, 'objentry layout'
    rows = [bytearray(ob[8 + i * 68:8 + (i + 1) * 68]) for i in range(n)]
    nm = lambda r: r[0x24:0x34].split(b'\0')[0].decode('latin1')  # noqa: E731
    tpl = [r for r in rows if r[6] == 33 and nm(r) == NAME % 2]
    assert len(tpl) == 1 and tpl[0][7] == 2 and tpl[0][8] == 0 and tpl[0][9] == 0, 'P_SEV120_2P row'
    ids = [struct.unpack_from('<H', r, 0)[0] for r in rows]
    assert ids == sorted(ids), 'objentry not sorted by id'
    add = []
    for k, _, oid in EXTRA:
        want = bytearray(tpl[0])
        struct.pack_into('<H', want, 0, oid)
        want[7] = k
        want[0x24:0x34] = (NAME % k).encode().ljust(16, b'\0')
        have = [r for r in rows if r[6] == 33 and r[7] == k and r[8] == 0]
        if have:
            assert len(have) == 1 and have[0] == want, 'owner-33 costume-%d row exists but differs - stop' % k
            print('objentry: already row %s (id %d, costume %d)' % (NAME % k, oid, k))
            continue
        assert oid not in ids and oid > max(ids), 'objentry id %d taken / not above the others' % oid
        add.append(bytes(want))
        ids.append(oid)
        print('objentry: + row %s (id %d, owner 33, costume %d, model p_sev120)' % (NAME % k, oid, k))
    if not add:
        return ob
    out = struct.pack('<II', 12, n + len(add)) + ob[8:] + b''.join(add)
    assert len(out) <= OBJENTRY_MAX, 'objentry.bin %d B > its 0x13d30 buffer' % len(out)
    return out


def extra_objentry(iso, dry):
    main = get(iso, 'general_archive/main/main.bin')
    mem = {n: main[o:o + s] for n, o, s in mpk.entries(main)}
    new_ob = objentry_rows(mem['objentry.bin'])
    if new_ob == mem['objentry.bin']:
        return
    new_main = mpk.replace(main, 'objentry.bin', new_ob)
    for n, o, s in mpk.entries(new_main):          # nothing else in main.bin changed
        assert n == 'objentry.bin' or new_main[o:o + s] == mem[n], n
    assert len(new_main) < 0x180000, 'main.bin load buffer'
    print('general_archive/main/main.bin: objentry %d -> %d B, main.bin %d -> %d B%s'
          % (len(mem['objentry.bin']), len(new_ob), len(main), len(new_main), ' (dry)' if dry else ''))
    if not dry:
        put(iso, 'general_archive/main/main.bin', new_main)


# ---------------------------------------------------------------------------------------------------- unlock
def unlock(iso, dry):
    with open(iso, 'rb') as f:
        f.seek(EBOOT_ISO)
        assert f.read(4) == b'\x7fELF', 'EBOOT is not the plain ELF'
        f.seek(EBOOT_ISO + 0x1018 + UNLOCK_ROW_VA - 0x8804040)
        cur = struct.unpack('<5i', f.read(20))
    seen = cur[4]                            # SEEN/"NEW" flag: 3623, or 3633 after spot33_newtag (kept as is)
    if seen == 3633:
        cur = cur[:4] + (3623,)
    if cur == UNLOCK_NEW or cur == UNLOCK_CATALOG:
        print('EBOOT unlock row owner 33: already costume flags 1/1 (outfits 2/3 selectable)%s' % (
            '; unlock flag 925 = PP Catalog purchase (spot33_catalog)' if cur == UNLOCK_CATALOG else ''))
        return
    assert cur == UNLOCK_OLD, 'EBOOT unlock row 22 = %s, expected %s - stop' % (cur, UNLOCK_OLD)
    print('EBOOT unlock row owner 33 (0x%08X): costume-2/3 flags -1/-1 -> 1/1%s' % (UNLOCK_ROW_VA, ' (dry)' if dry else ''))
    if not dry:
        with open(iso, 'r+b') as f:
            f.seek(EBOOT_ISO + 0x1018 + UNLOCK_ROW_VA - 0x8804040)
            f.write(struct.pack('<5i', *UNLOCK_NEW[:4], seen))


# ---------------------------------------------------------------------------------------------------- events
def events_patch(objx):
    """-> (new objx, counts). Trail op 0x2a: costume byte 2 (costume 1) -> 0 (any), 3/4/5 -> NEVER; one-shot op 3
    costume byte 3 (costume 2 only) -> NEVER. Guard: each costume-k trail has a costume-1 twin (only the variant
    param differs), so no outfit loses a trail."""
    ents = E.arc_entries(objx)
    k8 = next(k for k, e in enumerate(ents) if e[0] == 8 and e[1] == b'p_se')
    base, size = ents[k8][2], ents[k8][3]
    t8 = bytearray(objx[base:base + size])
    m, = struct.unpack_from('<I', t8, 4)
    cnt = {'trail any': 0, 'trail never': 0, 'sound never': 0}
    for b in range(m):
        o, = struct.unpack_from('<I', t8, 8 + 4 * b)
        nmain, nones = t8[o + 2], t8[o + 3]
        e1, = struct.unpack_from('<H', t8, o + 4)
        k, twins = o + 8, {}
        for _ in range(nmain):
            op, n = t8[k + 4], t8[k + 5]
            if op == 0x2a and t8[k + 9] in (2, 3, 4, 5):
                p = struct.unpack_from('<%dI' % n, t8, k + 12)
                key = (bytes(t8[k:k + 4]), bytes(t8[k + 6:k + 9]), bytes(t8[k + 10:k + 12]), p[:2], p[3:], n)
                twins.setdefault(t8[k + 9], set()).add(key)
            k += 12 + 4 * n
        for c in (3, 4, 5):
            assert twins.get(c, set()) <= twins.get(2, set()), 'block %d: costume-%d trail without a costume-1 twin' % (b, c - 1)
        k = o + 8
        for _ in range(nmain):
            op, n = t8[k + 4], t8[k + 5]
            if op == 0x2a and t8[k + 9] == 2:
                t8[k + 9] = 0
                cnt['trail any'] += 1
            elif op == 0x2a and t8[k + 9] in (3, 4, 5):
                t8[k + 9] = NEVER
                cnt['trail never'] += 1
            k += 12 + 4 * n
        k = o + e1
        for _ in range(nones):
            op, n = t8[k + 2], t8[k + 3]
            if op == 3 and t8[k + 7] == 3:
                t8[k + 7] = NEVER
                cnt['sound never'] += 1
            k += 8 + 4 * n
    # nothing costume-specific may remain (other ops / other values would need a look)
    for b in range(m):
        o, = struct.unpack_from('<I', t8, 8 + 4 * b)
        nmain, nones = t8[o + 2], t8[o + 3]
        e1, = struct.unpack_from('<H', t8, o + 4)
        k = o + 8
        for _ in range(nmain):
            assert t8[k + 9] in (0, NEVER), 'block %d: main op 0x%x still costume-only (%d)' % (b, t8[k + 4], t8[k + 9])
            k += 12 + 4 * t8[k + 5]
        k = o + e1
        for _ in range(nones):
            assert t8[k + 7] in (0, NEVER), 'block %d: one-shot op 0x%x still costume-only (%d)' % (b, t8[k + 2], t8[k + 7])
            k += 8 + 4 * t8[k + 3]
    out = bytearray(objx)
    out[base:base + size] = t8
    return bytes(out), cnt


def events(iso, dry):
    path = 'obj/p_sev120.objx'
    objx = get(iso, path)
    new, cnt = events_patch(objx)
    if new == objx:
        print('%s p_se: already costume-neutral (every outfit = outfit 1 trails/sounds)' % path)
        return
    assert len(new) == len(objx)
    diff = sum(a != b for a, b in zip(new, objx))
    print('%s p_se: trails costume 1 -> any %d, costume 2-4 duplicates -> never %d, costume-2 sounds -> never %d '
          '(%d bytes, same size)%s' % (path, cnt['trail any'], cnt['trail never'], cnt['sound never'], diff,
                                       ' (dry)' if dry else ''))
    if not dry:
        put(iso, path, new)


def main():
    iso, dry = sys.argv[1], '--dry' in sys.argv
    only_ev, no_ev = '--events-only' in sys.argv, '--no-events' in sys.argv
    if not only_ev:
        one = get(iso, 'obj/P_SEV120_1P.gmo')
        textures(iso, dry, one)
        extra_files(iso, dry, one)
        extra_objentry(iso, dry)
        unlock(iso, dry)
    if not no_ev:
        events(iso, dry)
    if dry:
        print('--dry: nothing written')


if __name__ == '__main__':
    main()
