"""EX-only Reflect cast animation (Mat, test247: "all the block animations have shifted to the reflect one"): the NORMAL
guard keeps the old guard poses (_160A/_161A), only the EX Mode guard plays Codex's KH2 Reflect cast. Data only, no code.

How (notes/reflect.md §14): the game's own STANCE system (system.bin `jobp`, picked by chrp row +8; Gabranth / Feral
Chaos use it for their EX motions). Each stance has 4 motion-override pairs (from id -> to id) that the animation
controller applies before the type-7 lookup (FUN_0882fe28 in FUN_0882f0d4; fighter+0x290 = controller+0x160). EX Mode
start (FUN_08acafac) switches to the next stance when chrp +0x0C has bit 0x2, EX Mode end (FUN_08aca77c) back to 0.
  - jobp row key 10 (new, appended; the static buffer 0x09b692b0 holds 13 rows, 10 used): stance 0 = no overrides,
    stance 1 = 470 -> 10318, 471 -> 10319. Both entries = WoL's neutral entry (no mesh/weapon/effect/ability-set change).
  - chrp row of owner 33: +8 = 10, +0x0C |= 2.
  - p_se type-7 rows 10318 -> block 60, 10319 -> block 67; blocks 60/67 := copies of guard blocks 20/21 (all events,
    incl. the Reflect data part + EX voice; motion id stays 470/471 at fighter+0x180, so the guard checks still hold).
  - GMO slots 60 _702A / 67 _706B (DEAD: only motion ids 10040 / 10097 lead there, no #33 plya piece, comb step or
    engine constant) get the Reflect cast; four more dead stubs (_700A _701A _704A _706A, 10,148 B copies of _401A)
    become copies of the smallest valid motion _070A (7,968 B) to pay for it.

  python3 -I spot33_exguard.py --gmo MODEL.gmo OUT.gmo CANDIDATE.gmo   (model part; build_sora.sh, before pkg_put 1P)
  python3 -I spot33_exguard.py ISO [--dry]                              (objx + system.bin; run LAST, after reflectvoice)
Both parts check the layout first and are idempotent.
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

OWNER = 33
GMO_MAX = 2506640                      # model memory: 2,506,640 B ran (test214), 2,523,344 crashed (test215)
# guard motion: (EX motion id, guard block, reused dead block = GMO motion index, its slot name, the one old motion id)
EX = {470: (10318, 20, 60, '_702A', 10040),
      471: (10319, 21, 67, '_706B', 10097)}
ROOM = ('_700A', '_701A', '_704A', '_706A')   # dead stubs -> copy of _070A (-2,180 B each)
SMALL, STUB_SRC = '_070A', '_401A'
JOBP_KEY, JOBP_MAX = 10, 13
# entry = u8 mesh (ff none), u8 needs EX, i16 +0x39c table (-1 keep), i16 +4/+6 (0), i16 +8/+0xA/+0xE switch effects
# (-1 none), u8 +0xC = 1 (FUN_08acf234 -> ability set 0), then 4 x (from, to) motion pairs. Values = WoL's entry 0.
ENTRY = bytes.fromhex('ff00ffff00000000ffffffff0100ffff')
FILLER = bytes.fromhex('ff00ffffffffffffffffffff0000ffff') + b'\xff' * 16


def jobp_row():
    pairs = [470, 10318, 471, 10319, -1, -1, -1, -1]
    head = struct.pack('<HBB12x', JOBP_KEY, 2, 0)                  # key, 2 stances, start in 0; +4/+5/+6 = 0
    return head + ENTRY + struct.pack('<8h', *[-1] * 8) + ENTRY + struct.pack('<8h', *pairs) + FILLER


# ---------------------------------------------------------------------------------------------------- model part
def gmo_part(src, dst, cand):
    from gmo_motion import motions, replace
    d, c = open(src, 'rb').read(), open(cand, 'rb').read()
    body = lambda b, n: next(b[o + struct.unpack_from('<H', b, o + 2)[0]:o + s] for nm, o, s in motions(b)[0] if nm == n)
    names = [n for n, _, _ in motions(d)[0]]
    for i, n in ((20, '_160A'), (21, '_161A'), (12, SMALL)) + tuple((v[2], v[3]) for v in EX.values()):
        assert names[i] == n, 'GMO motion %d is %s, expected %s' % (i, names[i], n)
    for g in ('_160A', '_161A'):
        assert body(d, g) != body(c, g), '%s already holds the Reflect cast: give this step the old-guard model' % g
    for n in ROOM:
        assert body(d, n) in (body(d, STUB_SRC), body(d, SMALL)), '%s is not a dead stub any more' % n
    for v in EX.values():
        assert body(d, v[3]) in (body(d, STUB_SRC), body(c, '_160A'), body(c, '_161A')), '%s is not a dead stub' % v[3]
    d = replace(d, [(EX[470][3], '_160A'), (EX[471][3], '_161A')], c)
    d = replace(d, [(n, SMALL) for n in ROOM])
    assert len(d) <= GMO_MAX, 'model %d B > %d B (model memory)' % (len(d), GMO_MAX)
    open(dst, 'wb').write(d)
    print('model %d B (limit %d, room %d)' % (len(d), GMO_MAX, GMO_MAX - len(d)))


# ----------------------------------------------------------------------------------------------------- objx part
def chunks(d):
    n, = struct.unpack_from('<I', d, 4)
    return [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]


def objx_part(d):
    from spot33_combos import rebuild_arc
    ch = chunks(d)
    i7 = next(k for k, c in enumerate(ch) if c[0] == 7 and c[1] == b'p_se')
    i8 = next(k for k, c in enumerate(ch) if c[0] == 8 and c[1] == b'p_se')
    get = lambda tag: next(d[c[2]:c[2] + c[3]] for c in ch if c[1] == tag)
    t7, t8, pl, cb = d[ch[i7][2]:][:ch[i7][3]], bytearray(d[ch[i8][2]:][:ch[i8][3]]), get(b'plya'), get(b'comb')
    m7, = struct.unpack_from('<I', t7, 4)
    rows = [struct.unpack_from('<HHHH', t7, 8 + k * 8) for k in range(m7)]
    # dead-slot proof, rechecked on every run: the reused blocks are reached only by their one old id (+ ours), and
    # no plya piece plays (+0x1c) or lands in (+0x10) that id
    np_, = struct.unpack_from('<I', pl, 4)
    piece_ids = set()
    for i in range(np_):
        piece_ids |= set(struct.unpack_from('<H', pl, 8 + i * 116 + 0x1c)) | set(struct.unpack_from('<H', pl, 8 + i * 116 + 0x10))
    for g, (ex, gb, db, _, old) in EX.items():
        assert (g, gb, 0, 0) in rows, 'motion %d does not map to guard block %d' % (g, gb)
        into = {r[0] for r in rows if r[1] == db}
        assert into <= {old, ex}, 'block %d is reached by %s' % (db, sorted(into))
        assert old not in piece_ids, 'motion %d is played by a plya piece: block %d is not dead' % (old, db)
        assert all(r[0] != ex or r[1:] == (db, 0, 0) for r in rows), 'motion %d already maps elsewhere' % ex
    # type-8: dead block := copy of the guard block (byte 0 = its own number)
    m, = struct.unpack_from('<I', t8, 4)
    for g, (ex, gb, db, _, _) in EX.items():
        offs = list(struct.unpack_from('<%dI' % m, t8, 8))
        so, do = offs[gb], offs[db]
        new = bytearray(t8[so:so + struct.unpack_from('<H', t8, so + 6)[0]])
        new[0] = db
        old_size = struct.unpack_from('<H', t8, do + 6)[0]
        if t8[do:do + old_size] == new:
            continue
        assert t8[do] == db and db + 1 < m and offs[db + 1] == do + old_size, 'type-8 layout changed near block %d' % db
        t8[do:do + old_size] = new
        offs = [o + len(new) - old_size if o > do else o for o in offs]
        struct.pack_into('<%dI' % m, t8, 8, *offs)
        print('block %d := copy of guard block %d (%d -> %d B)' % (db, gb, old_size, len(new)))
    # type-7: EX motion ids (variant 0), rows kept sorted
    want = [r for r in rows if r[0] not in [v[0] for v in EX.values()]] + [(v[0], v[2], 0, 0) for v in EX.values()]
    want.sort()
    t7n = t7[:4] + struct.pack('<I', len(want)) + b''.join(struct.pack('<HHHH', *r) for r in want) + t7[8 + m7 * 8:]
    if t7n != t7:
        print('type-7: + rows %s' % ['%d -> block %d' % (v[0], v[2]) for v in EX.values()])
    if t7n == t7 and bytes(t8) == d[ch[i8][2]:][:ch[i8][3]]:
        return d
    return rebuild_arc(d, {i7: t7n, i8: bytes(t8)})


# ----------------------------------------------------------------------------------------------- system.bin part
def system_part(sysbin):
    from spot33_save import arc_join, arc_split
    head, chs = arc_split(sysbin)
    chrp = next(c for c in chs if c[1] == b'chrp')
    jobp = next(c for c in chs if c[1] == b'jobp')
    c = bytearray(chrp[2])
    _, nrows = struct.unpack_from('<II', c, 0)
    at = next(8 + r * 144 for r in range(nrows) if c[8 + r * 144] == OWNER)
    assert c[at + 8] in (0xFF, JOBP_KEY), 'chrp %d +8 = %d (another stance table)' % (OWNER, c[at + 8])
    bits, = struct.unpack_from('<I', c, at + 0xC)
    assert not bits & 0x8, 'chrp +0x0C bit 8 changes the EX stance count path (FUN_08ab3610)'
    c[at + 8] = JOBP_KEY
    struct.pack_into('<I', c, at + 0xC, bits | 2)
    j = bytearray(jobp[2])
    ver, cnt = struct.unpack_from('<II', j, 0)
    assert len(j) == 8 + cnt * 0x70, 'jobp layout'
    keys = [struct.unpack_from('<H', j, 8 + r * 0x70)[0] for r in range(cnt)]
    row = jobp_row()
    if JOBP_KEY in keys:
        k = keys.index(JOBP_KEY)
        j[8 + k * 0x70:8 + (k + 1) * 0x70] = row
    else:
        assert max(keys) < JOBP_KEY, 'jobp keys must stay sorted'
        j += row
        cnt += 1
        struct.pack_into('<I', j, 4, cnt)
    assert cnt <= JOBP_MAX, 'jobp %d rows > static buffer (%d rows at 0x09b692b0)' % (cnt, JOBP_MAX)
    if bytes(c) == chrp[2] and bytes(j) == jobp[2]:
        return sysbin
    print('chrp %d: +8 0x%02x -> %d, +0x0C 0x%x -> 0x%x; jobp %d rows' % (OWNER, chrp[2][at + 8], JOBP_KEY, bits,
                                                                        bits | 2, cnt))
    chrp[2], jobp[2] = bytes(c), bytes(j)
    return arc_join(head, chs)


def put(iso, path, data):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, os.path.basename(path))
        open(p, 'wb').write(data)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p], check=True,
                           capture_output=True, text=True)
        print(r.stdout.strip())


def iso_part(iso, dry):
    import fep_edit as E
    import mpk
    from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, mpk_member, package_entry, read_at
    from pkg_put import PACKAGE_INFO_ISO_SECTOR
    d = E.load_objx(iso, 'obj/p_sev120.objx')
    out = objx_part(d)
    print('objx: %s' % ('no change' if out == d else '%+d B' % (len(out) - len(d))))
    with open(iso, 'rb') as f:
        info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
        pkg = PACKAGE_ISO_SECTOR * SECTOR
        off, size = package_entry(info, 'general_archive/main/main.bin')
        main_bin = read_at(f, pkg + off, size)
        so, ss = mpk_member(f, pkg + off, 'system.bin')
    sysbin = main_bin[so - pkg - off:so - pkg - off + ss]
    new_sys = system_part(sysbin)
    print('system.bin: %s' % ('no change' if new_sys == sysbin else '%+d B' % (len(new_sys) - len(sysbin))))
    if dry:
        return
    if out != d:
        put(iso, 'obj/p_sev120.objx', out)
    if new_sys != sysbin:
        put(iso, 'general_archive/main/main.bin', mpk.replace(main_bin, 'system.bin', new_sys))


def main():
    if sys.argv[1] == '--gmo':
        gmo_part(*sys.argv[2:5])
    else:
        iso_part(sys.argv[1], '--dry' in sys.argv)


if __name__ == '__main__':
    main()
