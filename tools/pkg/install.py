"""P1.3 / P1.5 installer: clean ULUS10566 ISO + fighter packages -> a new playable ISO (layout A or B).

  python3 -I tools/pkg/install.py CLEAN.iso OUT.iso PACKAGE [PACKAGE ...] [--layout A] [--dry]

Guards: CLEAN must be the known clean dump (sha256 below; it is only read); OUT must not exist (any existing file =
refuse) and must not be CLEAN. The output is
written to OUT + '.part' in the same folder and renamed only after the self-check passed; on any error the
.part file is removed. --dry computes everything (bytes + placement) and writes nothing.

Order (docs/PACKAGE-FORMAT.md §12): packages in dependency order (requires / install_after, ties by id); file bytes
from tools/pkg/pkgapply.contents() = produce (eboot_plain) -> patches + img: rows -> container rows -> whole files.
Placement, layout A (deterministic, no timestamps):
  * code images: EBOOT.BIN / OVL_*_APP.ELF written over their old extent when they fit its sectors (else appended);
    directory record size = new size (old bytes after a shorter file stay, like eboot_plain.py);
  * PACKAGE files (added or changed): appended once each at the ISO end, 2048-aligned, in lower-case path order;
    PACKAGE_INFO row repointed (changed; tier kept unless the package names one) or inserted sorted by hash
    (added; tier from files[].tier, default 0 = spot33_installfix); PACKAGE_INFO.BIN rewritten in place (room
    check: 80 sectors on disc, 0x20F8C B game buffer); PACKAGE.BIN record stretched to the end of the last append;
  * loose ISO files (target iso, e.g. DATA/BGM/*.AT3): appended after the PACKAGE data in path order, record
    added to its directory (sorted, directory size unchanged) or replaced;
  * PVD volume size = new ISO size.
Layout B (P1.5): PACKAGE_INFO.BIN stays the clean bytes; the same appended PACKAGE files are listed in
DATA/EXTRA.IDX instead (tools/pkg/engine/xidx.py; override bit = the hash is in the disc PACKAGE_INFO, tier forced
0); the engine (tools/pkg/engine: EXTRA.PRX sha-checked against engine.json, loader edits patches/extra_prx.json)
is installed: DATA/MODULE/EXTRA.PRX appended, loader words applied to the EBOOT after the packages' patches.
EBOOT / overlays / BGM stay direct ISO writes (the game reads them from disc0, not through PACKAGE).
Self-check before the rename: every produced file is read back from the new ISO (through PACKAGE_INFO /
ISO9660) and compared with the bytes it should have.
"""
import argparse
import hashlib
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'engine'))
sys.path.insert(0, os.path.join(ROOT, 'tools/scripts'))
sys.dont_write_bytecode = True
import equiv  # noqa: E402
import isolib  # noqa: E402
import pkgapply  # noqa: E402
import xidx  # noqa: E402
from pkghash import pkg_hash  # noqa: E402

SECTOR = 0x800
CLEAN_SHA256 = 'df94177d3e194e82800a574b50b61ee3c7be6caa877c8e82242a41af75d1ab6e'
CLEAN_SIZE = 1754529792
DATA = ['PSP_GAME', 'USRDIR', 'DATA']
INFO_SECTOR, INFO_ROOM, INFO_MAX = 26000, 80 * SECTOR, 0x20F8C
ENGINE_DIR = os.path.join(HERE, 'engine')
EBOOT = 'PSP_GAME/SYSDIR/EBOOT.BIN'
IDX_PATH = 'PSP_GAME/USRDIR/DATA/EXTRA.IDX'
ROW_RAM_BUDGET = 240 * 1024                      # docs/ENGINE.md: ~240 KB free after the game's heaps


def load_engine():
    """P1.4 engine (not yet a package folder): EXTRA.PRX bytes (sha-checked) + its EBOOT loader edits"""
    with open(os.path.join(ENGINE_DIR, 'engine.json'), encoding='utf-8') as f:
        eng = json.load(f)
    with open(os.path.join(ENGINE_DIR, 'extra', 'extra.prx'), 'rb') as f:
        prx = f.read()
    if hashlib.sha256(prx).hexdigest() != eng['sha256'] or len(prx) != eng['size']:
        raise ValueError('engine EXTRA.PRX does not match engine.json')
    with open(os.path.join(ENGINE_DIR, 'patches', 'extra_prx.json'), encoding='utf-8') as f:
        pat = json.load(f)
    if pat.get('set') != 'engine' or any(e['image'] != 'EBOOT' for e in pat['edits']):
        raise ValueError('unexpected engine patch set')
    return {'prx': prx, 'path': eng['disc_path'], 'edits': pat['edits'], 'version': eng['version'], 'sha256': eng['sha256']}


def order_packages(pkgs):
    by = {p['man']['id']: p for p in pkgs}
    done, out = set(), []

    def visit(p, stack=()):
        i = p['man']['id']
        if i in done:
            return
        if i in stack:
            sys.exit('package dependency cycle: %s' % ' -> '.join(stack + (i,)))
        deps = [r['id'] for r in p['man'].get('requires', [])] + list(p['man'].get('install_after', []))
        for d in sorted(deps):
            if d in by:
                visit(by[d], stack + (i,))
            elif d in [r['id'] for r in p['man'].get('requires', [])]:
                sys.exit('%s requires package %s (not given)' % (i, d))
        done.add(i)
        out.append(p)
    for i in sorted(by):
        visit(by[i])
    return out


def split_path(p):
    parts = p.split('/')
    return parts[:-1], parts[-1].encode('latin-1')


def dir_records(f, path):
    dsec, dsize = isolib.find_dir(f, path)
    return dsec, dsize, isolib.read_dir(f, dsec, dsize)


def plan(clean_path, pkgs, layout='A', engine=None):
    """-> (contents, writes, summary). writes = list of (offset, bytes); everything deterministic.
    layout B: PACKAGE_INFO.BIN untouched, PACKAGE files listed in EXTRA.IDX (override bit on rows that shadow a disc
    row), engine EXTRA.PRX added and its loader words applied to the EBOOT after the packages' patches."""
    C = equiv.Disc(clean_path)
    contents, srcs = pkgapply.contents(C, pkgs)
    if layout == 'B':
        base = pkgapply.IMAGES['EBOOT'][1]
        eb = contents.get(('iso', EBOOT))
        if eb is None or eb[:4] != b'\x7fELF':
            raise ValueError('layout B needs a plain EBOOT (a package with produce eboot_plain)')
        contents[('iso', EBOOT)] = pkgapply.apply_image('EBOOT', base, eb, engine['edits'], [])
        if ('iso', engine['path']) in contents:
            raise ValueError('a package ships %s itself' % engine['path'])
        contents[('iso', engine['path'])] = engine['prx']
    f = C.f
    writes = []
    end = isolib.iso_size(f)                         # current ISO end (bytes, sector aligned)
    if end % SECTOR:
        raise ValueError('ISO size not sector aligned')
    pkg_sec, pkg_size = C.files['PSP_GAME/USRDIR/DATA/PACKAGE.BIN']
    info_sec, info_size = C.files['PSP_GAME/USRDIR/DATA/PACKAGE_INFO.BIN']
    if info_sec != INFO_SECTOR:
        raise ValueError('PACKAGE_INFO.BIN not at sector %d' % INFO_SECTOR)
    tiers = {}
    for p in pkgs:
        for fe in p['man']['files']:
            if fe['target'] == 'package' and 'tier' in fe:
                tiers[fe['path'].lower()] = fe['tier']
    dir_cache = {}                                    # dir path tuple -> (dsec, dsize, records)

    def get_dir(path):
        k = tuple(path)
        if k not in dir_cache:
            dir_cache[k] = list(dir_records(f, path))
        return dir_cache[k]

    def set_record(path, name, sector, size, add=False):
        d = get_dir(path)
        recs = d[2]
        names = [isolib.rec_name(r) for r in recs]
        if name in names:
            if add:
                raise ValueError('%s/%s already exists' % ('/'.join(path), name))
            i = names.index(name)
            recs[i] = isolib.new_record(recs[i], name, sector, size)
        else:
            if not add:
                raise ValueError('%s/%s not found' % ('/'.join(path), name))
            donor = next(r for r in recs[2:] if not isolib.is_dir(r))
            i = next(i for i in range(2, len(recs) + 1) if i == len(recs) or names[i] > name)
            recs.insert(i, isolib.new_record(donor, name, sector, size))
        if isolib.pack_dir(recs, d[1]) is None:
            raise ValueError('directory %s full' % '/'.join(path))

    def append(data):
        nonlocal end
        pos = end
        writes.append((pos, data + b'\0' * ((-len(data)) % SECTOR)))
        end = pos + len(data) + (-len(data)) % SECTOR
        return pos // SECTOR

    summary = {'images': [], 'package_append': 0, 'package_bytes': 0, 'iso_append': [], 'rows_added': 0,
               'rows_repointed': 0}
    # ---- code images / other changed loose files that exist on the clean disc: in place when they fit
    iso_items = sorted((p, d) for (t, p), d in contents.items() if t == 'iso')
    late = []
    for path, data in iso_items:
        if path in C.files:
            sec, size = C.files[path]
            if -(-len(data) // SECTOR) <= -(-size // SECTOR):
                writes.append((sec * SECTOR, data))
                d, n = split_path(path)
                set_record(d, n, sec, len(data))
                summary['images'].append('%s in place at sector %d (%d -> %d B)' % (path, sec, size, len(data)))
                continue
        late.append((path, data))
    # ---- PACKAGE files: append in lower-case path order
    info = C.pinfo_bytes
    n, = struct.unpack_from('<I', info, 8)
    if len(info) != 16 + 12 * n:
        raise ValueError('PACKAGE_INFO.BIN has trailing bytes')
    rows = {}
    for i in range(n):
        h, sec, sf = struct.unpack_from('<III', info, 16 + 12 * i)
        rows[h] = [sec, sf]
    xrows = []
    for low, data in sorted((p, d) for (t, p), d in contents.items() if t == 'package'):
        h = pkg_hash(low)
        rel = append(data) - pkg_sec
        if layout == 'B':
            if rel >> 20 or not 0 < len(data) < 1 << 28:
                raise ValueError('%s: sector/size outside EXTRA.IDX limits' % low)
            xrows.append({'hash': h, 'sector': rel, 'size': len(data), 'override': h in rows, 'path': low})
            summary['package_append'] += 1
            summary['package_bytes'] += len(data)
            continue
        if rel >> 20:
            raise ValueError('package sector %d does not fit the 20-bit field' % rel)
        if len(data) >> 28:
            raise ValueError('%s too big for PACKAGE_INFO' % low)
        if h in rows:
            sec, sf = rows[h]
            tier = tiers.get(low, sf >> 28)
            rows[h] = [(sec & ~0xFFFFF) | rel, (tier << 28) | len(data)]
            summary['rows_repointed'] += 1
        else:
            rows[h] = [rel, (tiers.get(low, 0) << 28) | len(data)]
            summary['rows_added'] += 1
        summary['package_append'] += 1
        summary['package_bytes'] += len(data)
    if layout == 'A':
        new_info = bytearray(info[:16])
        struct.pack_into('<I', new_info, 8, len(rows))
        for h in sorted(rows):
            new_info += struct.pack('<III', h, *rows[h])
        if len(new_info) > min(INFO_ROOM, INFO_MAX):
            raise ValueError('PACKAGE_INFO.BIN %d B > room %d B' % (len(new_info), min(INFO_ROOM, INFO_MAX)))
        writes.append((INFO_SECTOR * SECTOR, bytes(new_info) + b'\0' * max(0, info_size - len(new_info))))
        set_record(DATA, b'PACKAGE_INFO.BIN', INFO_SECTOR, len(new_info))
        summary['package_info_rows'] = len(rows)
    else:
        idx = xidx.build(xrows)
        x = xidx.parse(idx)                           # the module's own checks
        flagged = {x['rows'][i][0] for i in x['overrides']}
        shadow = {r[0] for r in x['rows'] if r[0] in rows}
        if shadow != flagged:
            raise ValueError('override bits do not match the disc PACKAGE_INFO collisions')
        if late and any(p == IDX_PATH for p, _ in late):
            raise ValueError('a package ships EXTRA.IDX itself')
        late.append((IDX_PATH, idx))
        late.sort()
        summary['package_info_rows'] = '%d (vanilla, untouched)' % n
        summary['extra_idx'] = {'rows': len(x['rows']), 'overrides': len(flagged), 'bytes': len(idx),
                                'row_ram': 12 * len(x['rows']), 'sha256': hashlib.sha256(idx).hexdigest()}
        if 12 * len(x['rows']) + 3680 > ROW_RAM_BUDGET:
            raise ValueError('EXTRA.IDX rows need more RAM than the engine budget')
    pkg_end = end
    set_record(DATA, b'PACKAGE.BIN', pkg_sec, max(pkg_size, pkg_end - pkg_sec * SECTOR))
    # ---- loose ISO files that are new or did not fit: appended after the PACKAGE data, path order
    for path, data in late:
        sec = append(data)
        d, nm = split_path(path)
        set_record(d, nm, sec, len(data), add=path not in C.files)
        summary['iso_append'].append('%s at sector %d (%d B)' % (path, sec, len(data)))
    # ---- directories + PVD
    for k, (dsec, dsize, recs) in sorted(dir_cache.items()):
        writes.append((dsec * SECTOR, isolib.pack_dir(recs, dsize)))
    pv = bytearray(8)
    isolib.set_both32(pv, 0, end // SECTOR)
    writes.append((isolib.PVD_AT + 80, bytes(pv)))
    summary['iso_size'] = end
    summary['package_bin_size'] = max(pkg_size, pkg_end - pkg_sec * SECTOR)
    C.f.close()
    return contents, writes, summary


def self_check(out_path, contents, layout='A', clean_path=None):
    D = equiv.Disc(out_path)
    bad = []
    if layout == 'B':
        if not D.xactive:
            bad.append('EXTRA.IDX not active (%s)' % '; '.join(D.notes))
        with open(clean_path, 'rb') as f:
            f.seek(INFO_SECTOR * SECTOR)
            if f.read(len(D.pinfo_bytes)) != D.pinfo_bytes or len(D.pinfo_bytes) != equiv.Disc(clean_path).files[
                    'PSP_GAME/USRDIR/DATA/PACKAGE_INFO.BIN'][1]:
                bad.append('PACKAGE_INFO.BIN is not the clean bytes')
    for (t, p), data in sorted(contents.items()):
        if t == 'package':
            r = D.resolve(pkg_hash(p))
            got = D.pkg_read(r[2], r[3]) if r and D.pkg_ok(r[2], r[3]) else None
        else:
            got = D.file_bytes(p) if p in D.files else None
        if got != data:
            bad.append('%s %s' % (t, p))
    isolib.iso_size(D.f)                               # PVD == file size
    D.f.close()
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('clean')
    ap.add_argument('out')
    ap.add_argument('packages', nargs='+')
    ap.add_argument('--layout', default='A', choices=('A', 'B'))
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    clean, out = os.path.realpath(a.clean), os.path.realpath(a.out)
    part = out + '.part'
    if out == clean or os.path.basename(out) == 'ULUS10566.iso':
        sys.exit('refusing: OUT is the clean dump')
    if os.path.lexists(out) or os.path.lexists(part):
        sys.exit('refusing: %s (or its .part) already exists' % a.out)
    if os.path.getsize(clean) != CLEAN_SIZE:
        sys.exit('CLEAN is not the known clean ULUS10566 dump (size)')
    print('checking CLEAN sha256 ...', flush=True)
    if isolib.sha256_file(clean) != CLEAN_SHA256:
        sys.exit('CLEAN is not the known clean ULUS10566 dump (sha256)')
    pkgs = order_packages([pkgapply.load_package(d) for d in a.packages])
    for p in pkgs:
        if a.layout not in p['man']['layouts']:
            sys.exit('package %s does not support layout %s' % (p['man']['id'], a.layout))
        if p['man']['base'].get('clean_iso_sha256', CLEAN_SHA256) != CLEAN_SHA256:
            sys.exit('package %s was made for another base disc' % p['man']['id'])
    print('packages (apply order): %s' % ', '.join('%s %s %s' % (p['man']['id'], p['man']['version'],
                                                                 p['man']['package_sha256'][:12]) for p in pkgs))
    engine = load_engine() if a.layout == 'B' else None
    if engine:
        print('engine: EXTRA.PRX %s (%s), %d loader edits' % (engine['version'], engine['sha256'][:12], len(engine['edits'])))
    contents, writes, summary = plan(clean, pkgs, a.layout, engine)
    print(json.dumps(summary, indent=1))
    if a.dry:
        print('--dry: nothing written (%d writes planned, output would be %d B)' % (len(writes), summary['iso_size']))
        return 0
    try:
        print('copying CLEAN -> %s (the clean dump is only read) ...' % part, flush=True)
        shutil.copyfile(clean, part)
        with open(part, 'r+b') as f:
            for off, data in sorted(writes, key=lambda w: w[0]):
                f.seek(off)
                f.write(data)
            f.truncate(summary['iso_size'])
        bad = self_check(part, contents, a.layout, clean)
        if bad:
            raise RuntimeError('self-check failed for %d file(s): %s' % (len(bad), ', '.join(bad[:5])))
        os.rename(part, out)
    except BaseException:
        if os.path.exists(part):
            os.remove(part)
        raise
    print('wrote %s (%d B), sha256 %s' % (a.out, summary['iso_size'], isolib.sha256_file(out)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
