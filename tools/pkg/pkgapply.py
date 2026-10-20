"""Apply a fighter package to the clean disc's files IN MEMORY (core of the P1.3/P1.5 installers) + verify against a
reference disc. READ-ONLY: opens discs 'rb', never writes a disc or the package.

  python3 -I tools/pkg/pkgapply.py verify CLEAN.iso REF.iso PKG_DIR [PKG_DIR ...]

contents(clean_disc, packages) -> {('package', lower-case path): bytes, ('iso', ISO path): bytes} for every file the
packages add or change, built exactly in the spec §12 order: produce transforms -> patches + img: rows on the code
images -> rows per container (tools/pkg/containers.apply_file) -> whole files. `verify` then checks:
  * every produced file equals the reference disc's file byte for byte (PACKAGE path via PACKAGE_INFO, ISO path);
  * completeness: every PACKAGE_INFO path and ISO file that differs between CLEAN and REF is produced by the packages
    (index/layout files PACKAGE.BIN / PACKAGE_INFO.BIN excluded; tier flags reported separately).
Exit 0 = the packages reproduce REF's content from CLEAN.
"""
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools/scripts'))
sys.dont_write_bytecode = True
import containers as K  # noqa: E402
import equiv  # noqa: E402
from pkghash import pkg_hash  # noqa: E402

DATA = 'PSP_GAME/USRDIR/DATA/'
EBOOT = 'PSP_GAME/SYSDIR/EBOOT.BIN'
IMAGES = {'EBOOT': (EBOOT, 0x08804040 - 0x1018),
          'OVL_MENU_APP': (DATA + 'OVL_MENU_APP.ELF', 0x089DD4C0 - 0x54),
          'OVL_BATTLE_APP': (DATA + 'OVL_BATTLE_APP.ELF', 0x089DD4C0 - 0x54)}
LAYOUT_FILES = {DATA + 'PACKAGE.BIN', DATA + 'PACKAGE_INFO.BIN', DATA + 'EXTRA.IDX'}


def load_package(d):
    with open(os.path.join(d, 'manifest.json'), encoding='utf-8') as f:
        man = json.load(f)
    rows, patches = [], {}
    for t in man['rows']:
        with open(os.path.join(d, 'rows', t + '.json'), encoding='utf-8') as f:
            doc = json.load(f)
        for r in doc['rows']:
            rows.append(dict(r, _table=t))
    for s in man['patches']:
        with open(os.path.join(d, 'patches', s + '.json'), encoding='utf-8') as f:
            patches[s] = json.load(f)
    return {'dir': d, 'man': man, 'rows': rows, 'patches': patches}


def produce(name, clean, path):
    if name == 'eboot_plain':
        import eboot_plain as E
        enc = clean.file_bytes(path)
        if enc[:4] == b'\x7fELF':
            raise ValueError('EBOOT already plain: not the clean dump')
        elf, _ = E.decrypt(enc)
        return elf
    raise ValueError('unknown produce transform %s' % name)


def apply_image(img, base, data, edits, rows):
    buf = bytearray(data)
    for e in sorted(edits, key=lambda e: int(e['va'], 16)):
        o = int(e['va'], 16) - base
        if 'old' in e:
            if struct.unpack_from('<I', buf, o)[0] != int(e['old'], 16):
                raise ValueError('%s %s: old word mismatch' % (img, e['va']))
            struct.pack_into('<I', buf, o, int(e['new'], 16))
        elif e.get('append'):
            if o != len(buf):
                raise ValueError('%s append at %s but the image ends at 0x%08x' % (img, e['va'], len(buf) + base))
            buf += bytes.fromhex(e['new_bytes'])
        else:
            old = bytes.fromhex(e['old_bytes'])
            if bytes(buf[o:o + len(old)]) != old:
                raise ValueError('%s %s: old bytes mismatch' % (img, e['va']))
            buf[o:o + len(old)] = bytes.fromhex(e['new_bytes'])
    for r in sorted(rows, key=lambda r: r['key']['at']):
        o = r['key']['at'] - base
        old = bytes.fromhex(r['old_raw'])
        if r['op'] != 'replace' or len(old) != len(bytes.fromhex(r['raw'])):
            raise ValueError('%s row %s: only same-length replace is defined for img: rows' % (img, r['key']['at']))
        if bytes(buf[o:o + len(old)]) != old:
            raise ValueError('%s 0x%08x: old_raw mismatch' % (img, r['key']['at']))
        buf[o:o + len(old)] = bytes.fromhex(r['raw'])
    return bytes(buf)


def root_of(ns):
    if ns.startswith('pkg:'):
        p = ns[4:]
        for c in '!#':
            p = p.split(c)[0]
        return ('package', p)
    if ns.startswith('img:'):
        return ('img', ns[4:])
    if ns.startswith('iso:'):
        return ('iso', ns[4:])
    return ('other', ns)


def contents(clean, pkgs):
    out, srcs = {}, {}
    images = {}
    # (2) produce transforms
    for p in pkgs:
        for f in p['man']['files']:
            if f.get('produce'):
                data = produce(f['produce'], clean, f['path'])
                if hashlib.sha256(data).hexdigest() != f['sha256'] or len(data) != f['size']:
                    raise ValueError('%s: produced %s has the wrong sha256' % (p['man']['id'], f['path']))
                images[f['path']] = data
    # (3) patches + img: rows
    for img, (path, base) in IMAGES.items():
        edits = [e for p in pkgs for doc in p['patches'].values() for e in doc['edits'] if e['image'] == img]
        irows = [r for p in pkgs for r in p['rows'] if r['ns'] == 'img:' + img]
        if not edits and not irows:
            continue
        data = images.get(path) or clean.file_bytes(path)
        out[('iso', path)] = apply_image(img, base, data, edits, irows)
    for path, data in images.items():
        out.setdefault(('iso', path), data)
    # (4) rows per container
    groups = {}
    for p in pkgs:
        for r in p['rows']:
            k = root_of(r['ns'])
            if k[0] == 'img':
                continue
            if k[0] != 'package':
                raise ValueError('rows ns %s not supported by this applier' % r['ns'])
            groups.setdefault(k[1].lower(), (k[1], []))[1].append(r)
    for low, (path, rws) in sorted(groups.items()):
        h = pkg_hash(path)
        if h not in clean.prows:
            raise ValueError('rows edit %s, which the clean disc does not have' % path)
        _, sec, size, _ = clean.prows[h]
        out[('package', low)] = K.apply_file('pkg:' + path, clean.pkg_read(sec, size), rws)
        srcs[('package', low)] = 'rows'
    # (5) whole files
    for p in pkgs:
        for f in p['man']['files']:
            if f.get('produce'):
                continue
            key = ('package', f['path'].lower()) if f['target'] == 'package' else ('iso', f['path'])
            if key in out:
                raise ValueError('%s: shipped whole AND produced by rows/patches' % f['path'])
            with open(os.path.join(p['dir'], 'files', f['target'], f['path']), 'rb') as fh:
                out[key] = fh.read()
            srcs[key] = 'file'
    return out, srcs


def verify(clean_path, ref_path, pkg_dirs):
    pkgs = [load_package(d) for d in pkg_dirs]
    C, R = equiv.Disc(clean_path), equiv.Disc(ref_path)
    out, srcs = contents(C, pkgs)
    bad, ok = [], 0
    for (target, path), data in sorted(out.items()):
        if target == 'package':
            h = pkg_hash(path)
            if h not in R.prows:
                bad.append('%s: not on the reference disc' % path)
                continue
            _, sec, size, _ = R.prows[h]
            ref = R.pkg_read(sec, size)
        else:
            if path not in R.files:
                bad.append('%s: not on the reference disc' % path)
                continue
            ref = R.file_bytes(path)
        if ref != data:
            bad.append('%s %s: %d B, reference %d B, bytes differ' % (target, path, len(data), len(ref)))
        else:
            ok += 1
    # completeness: every difference clean -> ref is produced
    missing, tiers = [], 0
    for h, (_, sec, size, tier) in R.prows.items():
        rc = C.prows.get(h)
        if rc is not None and rc[2] == size and C.pkg_sha(rc[1], rc[2]) == R.pkg_sha(sec, size):
            tiers += rc[3] != tier
            continue
        if not any(t == 'package' and pkg_hash(p) == h for t, p in out):
            missing.append('PACKAGE %08x (%d B) %s on the reference disc' % (h, size, 'changed' if rc else 'added'))
    for p, (s, z) in R.files.items():
        if p in LAYOUT_FILES:
            continue
        e = C.files.get(p)
        if e is not None and e[1] == z and C.sha_extent(*e) == R.sha_extent(s, z):
            continue
        if ('iso', p) not in out:
            missing.append('ISO %s %s on the reference disc' % (p, 'changed' if e else 'added'))
    gone = [h for h in C.prows if h not in R.prows] + [p for p in C.files if p not in R.files]
    print('packages: %s' % ', '.join('%s %s (%s)' % (p['man']['id'], p['man']['version'], p['man']['package_sha256'][:12]) for p in pkgs))
    print('produced files: %d (rows %d, whole files %d, code images %d); equal to the reference: %d'
          % (len(out), sum(1 for v in srcs.values() if v == 'rows'), sum(1 for v in srcs.values() if v == 'file'),
             sum(1 for k in out if k[0] == 'iso' and k[1] in (v[0] for v in IMAGES.values())), ok))
    print('unchanged files with a different tier flag (layout, not content): %d' % tiers)
    for x in bad:
        print('DIFF ' + x)
    for x in missing:
        print('MISSING ' + x)
    for x in gone:
        print('REMOVED on the reference disc: %s' % x)
    verdict = not bad and not missing and not gone
    print('VERDICT: %s' % ('REPRODUCES the reference content' if verdict else 'DIFFERENT (%d diff, %d missing, %d removed)'
                           % (len(bad), len(missing), len(gone))))
    return 0 if verdict else 1


def main():
    a = sys.argv[1:]
    if len(a) < 4 or a[0] != 'verify':
        sys.exit(__doc__)
    sys.exit(verify(a[1], a[2], a[3:]))


if __name__ == '__main__':
    main()
