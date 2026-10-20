"""Install (or roll back) the engine on a plain-EBOOT Dissidia 012 disc: EBOOT loader patch + EXTRA.PRX + EXTRA.IDX.

  python3 -I tools/pkg/engine/install_engine.py ISO [--out OUT] [--rows ROWS.json | --idx FILE | --no-idx]
          [--clean CLEAN.iso] [--allow-unflagged] [--rollback] [--dry] [--no-sha]

  ISO           disc to change IN PLACE (or, with --out, the source that is copied to OUT first; ISO stays untouched)
  --out OUT     copy ISO -> OUT (only when OUT does not exist; an existing OUT must be a stock or engine disc and is
                changed in place)
  --rows FILE   build EXTRA.IDX from a rows file (format below) and put it on the disc
  --idx FILE    put this prebuilt EXTRA.IDX on the disc (checked like the module checks it)
  --no-idx      remove EXTRA.IDX (engine only; module state -1 = vanilla behaviour)
  (none)        keep whatever EXTRA.IDX the disc has (checked again)
  --clean ISO   clean dump used for the vanilla PACKAGE_INFO hash list (default dumps/ULUS10566.iso; read only)
  --allow-unflagged  accept unflagged rows that collide with a disc/vanilla hash (test discs only: EXTRA.PRX
                will DROP them at boot; rows files can do the same per row with "test_collision": true)
  --rollback    undo: EBOOT words back to stock, EXTRA.PRX + EXTRA.IDX records removed, their data cut off the ISO
                tail when nothing else uses it (a disc installed by this tool on top of ISO X rolls back to X
                byte-for-byte when no other tool appended data after it)
  --dry         print the plan, write nothing

Rows file (JSON): {"format": 1, "rows": [
    {"path": "<game path>", "from": "<other game path in the disc PACKAGE_INFO>", "override": true, "note": "..."},
    {"path": "<game path>", "sector": <PACKAGE.BIN-relative sector>, "size": <bytes>} ]}
  "override": true is REQUIRED when the path's hash is already in the disc's PACKAGE_INFO or in the vanilla one
  (otherwise the install is refused, because the module would drop the row anyway).

Accepted discs: EBOOT.BIN must be the plain ELF at sector 560 with the stock loader words (or this tool's patched
words). The clean dump (encrypted EBOOT) is refused, and so is any OUT path equal to it. Re-runnable: a second
identical run changes nothing ("same"). Patch words come from patches/engine-loader.json, the module from
extra/extra.prx whose sha256 must match engine.json (rebuild: tools/dlc/pspenv.sh make -C tools/pkg/engine/extra
&& python3 -I tools/pkg/engine/make_manifest.py). Write order: file data, directory records, PVD size, EBOOT last
(EBOOT patched + no module = still boots, P0.2 control).
"""
import hashlib
import json
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../../..'))
sys.path.insert(0, HERE)
import isolib as iso  # noqa: E402
import xidx  # noqa: E402

SECTOR = iso.SECTOR
EBOOT_SECTOR = 560
INFO_SECTOR = 26000
DATA_DIR = ['PSP_GAME', 'USRDIR', 'DATA']
MODULE_DIR = DATA_DIR + ['MODULE']
PRX_NAME, IDX_NAME = b'EXTRA.PRX', b'EXTRA.IDX'
CLEAN_DEFAULT = os.path.join(ROOT, 'dumps/ULUS10566.iso')


def die(msg):
    sys.exit('install_engine: ' + msg)


def load_engine():
    man = json.load(open(os.path.join(HERE, 'engine.json')))
    pat = json.load(open(os.path.join(HERE, man['loader_patch'])))
    prx_path = os.path.join(HERE, 'extra/extra.prx')
    if not os.path.exists(prx_path):
        die('%s missing: tools/dlc/pspenv.sh make -C tools/pkg/engine/extra' % prx_path)
    prx = open(prx_path, 'rb').read()
    if hashlib.sha256(prx).hexdigest() != man['sha256'] or len(prx) != man['size']:
        die('extra.prx does not match engine.json (rebuilt?): python3 -I tools/pkg/engine/make_manifest.py')
    if prx[:4] != b'\x7fELF' or struct.unpack_from('<H', prx, 16)[0] != 0xFFA0:
        die('extra.prx is not a plain PRX')
    words = [(int(w['va'], 16), int(w['old'], 16), int(w['new'], 16)) for w in pat['words']]
    ctx = [(int(c['va'], 16), int(c['value'], 16)) for c in pat['context']]
    return man, prx, words, ctx


def eboot_off(va):
    return EBOOT_SECTOR * SECTOR + 0x1018 + va - 0x08804040


def disc_state(f, words, ctx):
    """'stock' | 'installed' | 'encrypted' | 'unknown'."""
    e = iso.find_file(f, ['PSP_GAME', 'SYSDIR'], b'EBOOT.BIN')
    if not e or e[0] != EBOOT_SECTOR:
        return 'unknown'
    if iso.read_at(f, EBOOT_SECTOR * SECTOR, 4) != b'\x7fELF':
        return 'encrypted'
    def w(va):
        return struct.unpack('<I', iso.read_at(f, eboot_off(va), 4))[0]
    if any(w(va) != v for va, v in ctx):
        return 'unknown'
    cur = [w(va) for va, _, _ in words]
    if cur == [o for _, o, _ in words]:
        return 'stock'
    if cur == [n for _, _, n in words]:
        return 'installed'
    return 'unknown'


def info_rows(f):
    head = iso.read_at(f, INFO_SECTOR * SECTOR, 16)
    if head[4:8] != b'pack':
        raise ValueError('PACKAGE_INFO.BIN header not found at sector %d' % INFO_SECTOR)
    n, = struct.unpack_from('<I', head, 8)
    body = iso.read_at(f, INFO_SECTOR * SECTOR + 16, 12 * n)
    return {struct.unpack_from('<I', body, 12 * i)[0]: struct.unpack_from('<III', body, 12 * i) for i in range(n)}


def vanilla_hashes(clean_path):
    if not clean_path or not os.path.exists(clean_path):
        return None
    with open(clean_path, 'rb') as f:
        return set(info_rows(f))


def rows_from_file(path, disc_info):
    spec = json.load(open(path))
    if spec.get('format') != 1:
        die('%s: format must be 1' % path)
    out = []
    for r in spec['rows']:
        p = r['path']
        if 'from' in r:
            src = disc_info.get(xidx.pkg_hash(r['from']))
            if not src:
                die('row %s: "from" path %s is not in the disc PACKAGE_INFO' % (p, r['from']))
            sec, size = src[1] & 0xFFFFF, src[2] & 0x0FFFFFFF
        else:
            sec, size = int(r['sector']), int(r['size'])
        out.append(dict(path=p, hash=xidx.pkg_hash(p), sector=sec, size=size, override=bool(r.get('override')),
                        test_collision=bool(r.get('test_collision')), src=r.get('from')))
    return out


def check_rows(rows, disc_info, vanilla, pkg_size, allow_unflagged):
    """Collision + bounds checks. rows: dicts with hash/sector/size/override(/path/test_collision)."""
    errors, notes = [], []
    for r in rows:
        name = r.get('path') or '%08x' % r['hash']
        in_disc, in_van = r['hash'] in disc_info, vanilla is not None and r['hash'] in vanilla
        if (in_disc or in_van) and not r['override']:
            what = 'disc+vanilla' if in_disc and in_van else ('disc' if in_disc else 'vanilla')
            if r.get('test_collision') or allow_unflagged:
                notes.append('WARNING test row %s collides with a %s PACKAGE_INFO hash and is NOT flagged: '
                             'EXTRA.PRX will drop it at boot (counts in rejected)' % (name, what))
            else:
                errors.append('row %s collides with a %s PACKAGE_INFO hash; set "override": true if intended'
                              % (name, what))
        elif r['override'] and not in_disc:
            notes.append('note: row %s is flagged override but not in this disc\'s PACKAGE_INFO%s' % (
                name, ' (it is vanilla: fine for a clean-layout disc)' if in_van else ' (flag unused)'))
        if r['sector'] * SECTOR + r['size'] > pkg_size:
            errors.append('row %s points past the end of PACKAGE.BIN' % name)
    return errors, notes


def plan_truncate(f, removed, iso_end):
    """New ISO end after removing our records: cut our own extents off the tail, never below anything else."""
    others = [(s, z) for p, s, z in iso.walk_extents(f)]
    floor = max(s * SECTOR + -(-z // SECTOR) * SECTOR for s, z in others)
    end = iso_end
    changed = True
    while changed:
        changed = False
        for s, z in removed:
            if s * SECTOR + max(1, -(-z // SECTOR)) * SECTOR == end:
                end, changed = s * SECTOR, True
    return max(end, floor)


def rollback(target, words, ctx, dry):
    with open(target, 'rb') as f:
        st = disc_state(f, words, ctx)
        if st not in ('stock', 'installed'):
            die('%s: disc state %s; rollback only works on a stock or engine disc' % (target, st))
        rems = [x for x in (iso.plan_remove(f, MODULE_DIR, PRX_NAME), iso.plan_remove(f, DATA_DIR, IDX_NAME)) if x]
        iso_end = iso.iso_size(f)
    print('state %s; records to remove: %s' % (st, ', '.join(r['name'].decode() for r in rems) or 'none'))
    if st == 'stock' and not rems:
        print('nothing to roll back')
        return False
    if dry:
        print('[dry] would restore %d EBOOT words, remove the records and cut our tail data' % len(words))
        return False
    with open(target, 'r+b') as f:
        if st == 'installed':
            for va, old, _ in words:
                f.seek(eboot_off(va))
                f.write(struct.pack('<I', old))
        for r in rems:
            f.seek(r['dsec'] * SECTOR)
            f.write(r['dir'])
        f.flush()
        end = plan_truncate(f, [(r['sector'], r['size']) for r in rems], iso_end)
        if end < iso_end:
            f.truncate(end)
            iso.write_pvd_size(f, end)
        else:
            for r in rems:              # data stays (something else lives after it): zero our sectors
                f.seek(r['sector'] * SECTOR)
                f.write(b'\0' * (-(-r['size'] // SECTOR) * SECTOR))
    with open(target, 'rb') as f:
        assert disc_state(f, words, ctx) == 'stock'
        assert not iso.find_file(f, MODULE_DIR, PRX_NAME) and not iso.find_file(f, DATA_DIR, IDX_NAME)
        print('rolled back: EBOOT stock, records removed, ISO %d -> %d bytes' % (iso_end, iso.iso_size(f)))
    return True


def main():
    argv = sys.argv[1:]
    flags = {a for a in argv if a.startswith('--')}
    opts, pos, i = {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a in ('--out', '--rows', '--idx', '--clean'):
            if i + 1 >= len(argv):
                die('%s needs a value' % a)
            opts[a] = argv[i + 1]
            i += 2
            continue
        if a.startswith('--') and a not in ('--no-idx', '--rollback', '--dry', '--no-sha', '--allow-unflagged'):
            die('unknown option %s' % a)
        if not a.startswith('--'):
            pos.append(a)
        i += 1
    if len(pos) != 1:
        die('usage: install_engine.py ISO [--out OUT] [--rows F | --idx F | --no-idx] [--rollback] [--dry]')
    if sum(k in opts for k in ('--rows', '--idx')) + ('--no-idx' in flags) > 1:
        die('use only one of --rows / --idx / --no-idx')
    dry = '--dry' in flags
    src = os.path.abspath(pos[0])
    target = os.path.abspath(opts.get('--out', src))
    clean = os.path.realpath(CLEAN_DEFAULT)
    if os.path.realpath(target) == clean or (os.path.exists(target) and os.path.exists(clean) and
                                             os.path.samefile(target, clean)):
        die('refusing to write the clean dump %s' % target)
    if '--out' in opts and os.path.realpath(target) == os.path.realpath(src):
        die('--out equals ISO')
    if not os.path.exists(src):
        die('%s not found' % src)
    man, prx, words, ctx = load_engine()

    with open(src, 'rb') as f:
        st_src = disc_state(f, words, ctx)
    if st_src == 'encrypted':
        die('%s has the encrypted (retail) EBOOT; the engine needs a plain-EBOOT disc (Sora build / installer '
            'output). The clean dump is decrypted by the package installer (P1.3), not here.' % src)
    if st_src not in ('stock', 'installed'):
        die('%s: loader/site words are neither stock nor this engine\'s (state %s); not touching it' % (src, st_src))

    if '--out' in opts:
        if os.path.exists(target):
            with open(target, 'rb') as f:
                st_t = disc_state(f, words, ctx)
            if st_t not in ('stock', 'installed'):
                die('%s exists and is not a stock/engine disc (state %s); not touching it' % (target, st_t))
            print('%s exists (%s): changing it in place' % (target, st_t))
        elif dry:
            print('[dry] would copy %s -> %s' % (src, target))
        else:
            subprocess.run(['cp', '--reflink=auto', src, target], check=True)
            print('copied %s -> %s' % (src, target))
    work = target if os.path.exists(target) else src        # dry run without OUT: plan against ISO

    if '--rollback' in flags:
        rollback(work, words, ctx, dry)
        if not dry and '--no-sha' not in flags:
            print('sha256 %s' % iso.sha256_file(target))
        return

    print('EXTRA.PRX %s %d B sha256 %s' % (man['version'], len(prx), man['sha256']))
    with open(work, 'rb') as f:
        st = disc_state(f, words, ctx)
        disc_info = info_rows(f)
        pkg = iso.find_file(f, DATA_DIR, b'PACKAGE.BIN')
        if not pkg:
            die('no DATA/PACKAGE.BIN')
        pkg_size = pkg[1]
        cur_idx = iso.find_file(f, DATA_DIR, IDX_NAME)
        cur_idx_data = iso.read_at(f, cur_idx[0] * SECTOR, cur_idx[1]) if cur_idx else None
    vanilla = vanilla_hashes(opts.get('--clean', CLEAN_DEFAULT))
    print('disc: %s; PACKAGE_INFO %d rows; PACKAGE.BIN %d B; vanilla hash list: %s' % (
        st, len(disc_info), pkg_size, '%d rows' % len(vanilla) if vanilla is not None else
        'NOT available (only the disc index is checked)'))

    idx_action, idx_data, rows = None, None, None
    if '--rows' in opts:
        rows = rows_from_file(opts['--rows'], disc_info)
        idx_data = xidx.build([dict(hash=r['hash'], sector=r['sector'], size=r['size'], override=r['override'],
                                    path=r['path']) for r in rows])
        idx_action = 'put'
    elif '--idx' in opts:
        idx_data = open(opts['--idx'], 'rb').read()
        idx_action = 'put'
    elif '--no-idx' in flags:
        idx_action = 'remove'
    elif cur_idx_data is not None:
        idx_data, idx_action = cur_idx_data, 'keep'
    if idx_data is not None:
        try:
            parsed = xidx.parse(idx_data)
        except ValueError as e:
            die('EXTRA.IDX invalid (module state %s): %s' % e.args if len(e.args) == 2 else str(e))
        names = parsed['names'] or [None] * len(parsed['rows'])
        if rows is None:
            rows = [dict(hash=h, sector=s, size=z, override=i in parsed['overrides'], path=names[i])
                    for i, (h, s, z) in enumerate(parsed['rows'])]
        errors, notes = check_rows(rows, disc_info, vanilla, pkg_size, '--allow-unflagged' in flags)
        for r in sorted(rows, key=lambda r: r['hash']):
            print('  row %08x sector %7d size %8d %s %s%s' % (
                r['hash'], r['sector'], r['size'], 'OVERRIDE' if r['override'] else 'new     ', r.get('path') or '',
                ' <- %s' % r['src'] if r.get('src') else ''))
        for n in notes:
            print('  ' + n)
        if errors:
            die('EXTRA.IDX refused:\n  ' + '\n  '.join(errors))
        print('EXTRA.IDX %s: %d rows (%d override), %d B sha256 %s' % (
            idx_action, len(parsed['rows']), len(parsed['overrides']), len(idx_data),
            hashlib.sha256(idx_data).hexdigest()))
    else:
        print('EXTRA.IDX: %s' % ('remove (engine only)' if idx_action == 'remove' and cur_idx else 'none (engine only)'))

    with open(work, 'rb') as f:
        pp = iso.plan_put(f, MODULE_DIR, PRX_NAME, prx)
    print('EBOOT loader patch: %s (%d words)' % ('already installed' if st == 'installed' else 'stock -> install',
                                                 len(words)))
    print('MODULE/EXTRA.PRX: %s%s' % (pp['action'], '' if pp['action'] == 'same' else
                                      ' at sector %d' % (pp['pos'] // SECTOR)))
    if dry:
        print('[dry] nothing written')
        return

    with open(target, 'r+b') as f:
        assert disc_state(f, words, ctx) in ('stock', 'installed')
        iso.apply_put(f, pp)
        if idx_action in ('put', 'keep'):
            pi = iso.plan_put(f, DATA_DIR, IDX_NAME, idx_data)
            iso.apply_put(f, pi)
            print('DATA/EXTRA.IDX: %s%s' % (pi['action'], '' if pi['action'] == 'same' else
                                            ' at sector %d' % (pi['pos'] // SECTOR)))
        elif idx_action == 'remove':
            r = iso.plan_remove(f, DATA_DIR, IDX_NAME)
            if r:
                f.seek(r['dsec'] * SECTOR)
                f.write(r['dir'])
                print('DATA/EXTRA.IDX: record removed (data sectors left as dead space)')
        if st != 'installed':
            for va, _, new in words:
                f.seek(eboot_off(va))
                f.write(struct.pack('<I', new))
    with open(target, 'rb') as f:
        assert disc_state(f, words, ctx) == 'installed'
        assert iso.plan_put(f, MODULE_DIR, PRX_NAME, prx)['action'] == 'same'
        if idx_data is not None:
            assert iso.plan_put(f, DATA_DIR, IDX_NAME, idx_data)['action'] == 'same'
        elif idx_action == 'remove':
            assert not iso.find_file(f, DATA_DIR, IDX_NAME)
        size = iso.iso_size(f)
        assert info_rows(f) == disc_info
    print('%s: done (%d bytes)' % (target, size))
    if '--no-sha' not in flags:
        print('sha256 %s' % iso.sha256_file(target))


if __name__ == '__main__':
    main()
