"""Cloud back to vanilla (release QA D-313-01). Removes the test-4..10 move experiment that every build inherited from
the old base disc dumps/ULUS10566-test28-lines.iso:
  obj/p_sev100.objx    Cloud's battle file: comb action 1020 (4-hit combo), plya piece 0xFF0, atkp hit 0xFF0
                       NEW_MIDDLE3 (power 150, NEAR3 knockback), p_se motion 0x27F0 + variant-2 hitbox  (+304 B)
  obj/p_sev100_w.objx  Cloud's lite copy: same comb/plya/atkp additions                                (+256 B)
  system.bin ablt      row id 0x0d00 (owner 13 idx 0 = Cloud's neutral ground Bravery): action 1020 -> 313
Both files are copied from the CLEAN dump (opened read-only); the ablt row is reset to the clean row.
Nothing Sora needs is touched: Sora's own copy of the experiment lives in obj/p_sev120.objx (action 1020 is his
Combo Plus) and his ablt rows are owner 33. No intentional Sora-side edit lives in Cloud's files (checked against
test314: Cloud's cosx/exex/GMOs/voice/_a.objx/chrp/objentry rows are already vanilla; notes/release-qa-triage.md).

Guards (stops, writes nothing): a Cloud file that is neither clean nor "clean + only the experiment chunks"
(p_se, plya, comb, atkp, with comb holding action 1020); an ablt 0x0d00 row that differs from clean anywhere but the
action field, or whose action is not 313/1020; any other owner-13 ablt row differing from clean (reported).

  python3 -I spot33_cloudvanilla.py ISO [CLEAN_ISO] [--dry]      CLEAN_ISO default dumps/ULUS10566.iso
Re-runnable: prints "no change" when Cloud is already vanilla. Run it right after the base copy (build_sora.sh).
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import arc  # noqa: E402
import mpk  # noqa: E402
from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, package_entry  # noqa: E402
from pkg_put import PACKAGE_INFO_ISO_SECTOR  # noqa: E402

CLEAN_DEFAULT = os.path.join(HERE, '../../dumps/ULUS10566.iso')
FILES = ['obj/p_sev100.objx', 'obj/p_sev100_w.objx']
EXPERIMENT_CHUNKS = {'p_se', 'plya', 'comb', 'atkp'}
CLOUD, ROW_ID, VANILLA_ACTION, EXPERIMENT_ACTION = 13, 0x0d00, 313, 1020
ABLT_ROW, ABLT_HEAD = 40, 16


def pkg_file(f, info, path):
    off, size = package_entry(info, path)
    f.seek(PACKAGE_ISO_SECTOR * SECTOR + off)
    return f.read(size)


def read_iso(iso, paths):
    with open(iso, 'rb') as f:
        f.seek(PACKAGE_INFO_ISO_SECTOR * SECTOR)
        info = f.read(0x21000)
        return {p: pkg_file(f, info, p) for p in paths}


def comb_actions(chunk):
    _, n = struct.unpack_from('<HH', chunk, 0)
    return [struct.unpack_from('<H', chunk, o)[0] for o in struct.unpack_from('<%dI' % n, chunk, 4)]


def check_file(path, cur, clean):
    """True = needs restoring; exits on an unknown edit."""
    if cur == clean:
        print('%s: already vanilla (%d B)' % (path, len(cur)))
        return False
    ca, cc = list(arc.chunks(cur)), list(arc.chunks(clean))
    if [t for t, _, _ in ca] != [t for t, _, _ in cc]:
        sys.exit('%s: chunk list differs from clean - unknown edit, stop' % path)
    changed = []
    for (t, o, s), (_, o2, s2) in zip(ca, cc):
        if cur[o:o + s] != clean[o2:o2 + s2]:
            changed.append(t)
            if t not in EXPERIMENT_CHUNKS:
                sys.exit('%s: chunk %s differs from clean - not the test-24 experiment, stop' % (path, t))
            if t == 'comb' and EXPERIMENT_ACTION not in comb_actions(cur[o:o + s]):
                sys.exit('%s: comb differs from clean but has no action %d - unknown edit, stop' % (path, EXPERIMENT_ACTION))
    print('%s: %d -> %d B (test-24 experiment in %s) -> clean copy' % (path, len(cur), len(clean), ', '.join(changed)))
    return True


def ablt_fix(sysbin, clean_sysbin):
    """Returns the new system.bin (or the same object if nothing to do)."""
    def ablt(s):
        t, o, n = next(c for c in arc.chunks(s) if c[0] == 'ablt')
        return o, s[o:o + n]
    o, cur = ablt(sysbin)
    _, cl = ablt(clean_sysbin)
    rows = lambda c: [c[ABLT_HEAD + i * ABLT_ROW:ABLT_HEAD + (i + 1) * ABLT_ROW]  # noqa: E731
                      for i in range(struct.unpack_from('<I', c, 8)[0])]
    cur_rows, cl_rows = rows(cur), rows(cl)
    cl_cloud = {(r[1] << 8) | r[0]: r for r in cl_rows if r[1] == CLOUD}
    at, fix = None, None
    for i, r in enumerate(cur_rows):
        if r[1] != CLOUD:
            continue
        rid = (r[1] << 8) | r[0]
        want = cl_cloud.get(rid)
        if want is None:
            sys.exit('ablt row %d id 0x%04x: owner-13 row not in the clean table - stop' % (i, rid))
        if r == want:
            continue
        if rid != ROW_ID:
            sys.exit('ablt row %d id 0x%04x differs from clean (not the known 0x0d00 leftover) - stop' % (i, rid))
        act, = struct.unpack_from('<H', r, 12)
        if r[:12] + r[14:] != want[:12] + want[14:] or act != EXPERIMENT_ACTION:
            sys.exit('ablt row %d id 0x0d00: unexpected content (action %d) - stop' % (i, act))
        at, fix = i, want
    if len(cl_cloud) != sum(1 for r in cur_rows if r[1] == CLOUD):
        sys.exit('owner-13 ablt row count differs from clean - stop')
    if at is None:
        print('ablt id 0x0d00 (Cloud neutral ground Bravery): already action %d; all %d Cloud rows = clean' % (
            VANILLA_ACTION, len(cl_cloud)))
        return sysbin
    print('ablt row %d id 0x0d00 (Cloud neutral ground Bravery): action %d -> %d (= clean row)' % (
        at, EXPERIMENT_ACTION, VANILLA_ACTION))
    p = o + ABLT_HEAD + at * ABLT_ROW
    return sysbin[:p] + fix + sysbin[p + ABLT_ROW:]


def put(iso, path, data):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, os.path.basename(path))
        open(p, 'wb').write(data)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                           check=True, capture_output=True, text=True)
        print('  ' + r.stdout.strip())


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)
    iso = args[0]
    clean = args[1] if len(args) > 1 else CLEAN_DEFAULT
    dry = '--dry' in sys.argv[1:]
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the clean dump'
    assert os.path.exists(clean), 'clean dump not found: %s' % clean
    assert not os.path.samefile(iso, clean), 'ISO is the clean dump - stop'
    MB = 'general_archive/main/main.bin'
    cur = read_iso(iso, FILES + [MB])
    ref = read_iso(clean, FILES + [MB])
    todo = [p for p in FILES if check_file(p, cur[p], ref[p])]
    member = lambda d, n: next(d[o:o + s] for m, o, s in mpk.entries(d) if m == n)  # noqa: E731
    sb = member(cur[MB], 'system.bin')
    new_sb = ablt_fix(sb, member(ref[MB], 'system.bin'))
    if not todo and new_sb is sb:
        print('Cloud: no change (vanilla)')
        return
    if dry:
        print('--dry: nothing written')
        return
    for p in todo:
        put(iso, p, ref[p])
    if new_sb is not sb:
        put(iso, MB, mpk.replace(cur[MB], 'system.bin', new_sb))
    after = read_iso(iso, FILES)
    assert all(after[p] == ref[p] for p in FILES), 'Cloud files not byte-identical to clean after the write'
    print('Cloud: restored to vanilla (objx + _w byte-identical to clean, ablt 0x0d00 = action %d)' % VANILLA_ACTION)


if __name__ == '__main__':
    main()
