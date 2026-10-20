"""Shared helpers for the fighter package format (P1.1, docs/PACKAGE-FORMAT.md).

Library (used by validate.py; meant for extract.py / install.py later):
  canon_bytes(obj)        canonical JSON bytes (sorted keys, 2-space indent, UTF-8, LF, final newline)
  pkg_hash(path)          PACKAGE_INFO name hash (CRC-32/BZIP2 of the lower-case path; = tools/scripts/pkghash.py)
  build_inventory(dir)    {relpath: {sha256, size}} for every package file except manifest.json
  package_sha256(man)     sha256 of the canonical manifest without its package_sha256 field
  norm_ids(items)         [int | [lo, hi]] -> sorted list of (lo, hi)

CLI (WRITES only inside the given package folder; never touches an ISO):
  python3 -I tools/pkg/pkgformat.py seal PKG_DIR [--dry]
      rewrites every *.json in PKG_DIR canonically, refreshes manifest 'inventory' + 'package_sha256'.
      Refuses paths under dumps/. --dry prints what would change.
"""
import hashlib
import json
import os
import sys

FORMAT = 'dissidia012-package'
FORMAT_MAJOR = 1
FORMAT_MINOR = 0
TOP_DIRS = ('files', 'rows', 'patches')


def canon_bytes(obj):
    return (json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()


def pkg_hash(name):
    crc = 0xFFFFFFFF
    for c in name.lower().encode():
        crc ^= c << 24
        for _ in range(8):
            crc = ((crc << 1) ^ 0x04C11DB7) if crc & 0x80000000 else (crc << 1)
            crc &= 0xFFFFFFFF
    return crc ^ 0xFFFFFFFF


def walk_files(root):
    """Sorted relative paths ('/'-separated) of every regular file under root."""
    out = []
    for d, dirs, files in os.walk(root):
        dirs.sort()
        for fn in files:
            p = os.path.join(d, fn)
            out.append(os.path.relpath(p, root).replace(os.sep, '/'))
    return sorted(out)


def build_inventory(pkg_dir):
    inv = {}
    for rel in walk_files(pkg_dir):
        if rel == 'manifest.json':
            continue
        p = os.path.join(pkg_dir, rel)
        inv[rel] = {'sha256': sha256_file(p), 'size': os.path.getsize(p)}
    return inv


def package_sha256(manifest):
    m = dict(manifest)
    m.pop('package_sha256', None)
    return hashlib.sha256(canon_bytes(m)).hexdigest()


def norm_ids(items):
    out = []
    for it in items:
        if isinstance(it, list):
            out.append((it[0], it[1]))
        else:
            out.append((it, it))
    return out


def key_tuple(key, fields):
    """Sort key for a row key: values in key_fields order; ints before strings."""
    t = []
    for f in fields:
        v = key.get(f)
        t.append((0, v, '') if isinstance(v, int) and not isinstance(v, bool) else (1, 0, str(v)))
    return tuple(t)


def seal(pkg_dir, dry=False):
    real = os.path.realpath(pkg_dir)
    if 'dumps' in real.split(os.sep):
        sys.exit('refusing to write under dumps/: %s' % real)
    changed = []
    for rel in walk_files(pkg_dir):
        if not rel.endswith('.json') or rel.startswith('files/'):
            continue   # files/ holds game files verbatim, never rewritten
        p = os.path.join(pkg_dir, rel)
        with open(p, 'rb') as f:
            old = f.read()
        new = canon_bytes(json.loads(old.decode('utf-8')))
        if rel != 'manifest.json' and new != old:
            changed.append(rel)
            if not dry:
                with open(p, 'wb') as f:
                    f.write(new)
    mp = os.path.join(pkg_dir, 'manifest.json')
    with open(mp, 'rb') as f:
        old = f.read()
    man = json.loads(old.decode('utf-8'))
    man['inventory'] = build_inventory(pkg_dir)
    man['package_sha256'] = package_sha256(man)
    new = canon_bytes(man)
    if new != old:
        changed.append('manifest.json')
        if not dry:
            with open(mp, 'wb') as f:
                f.write(new)
    print('%s %s: %s' % ('would rewrite' if dry else 'rewrote', pkg_dir, ', '.join(changed) or 'nothing (already sealed)'))
    print('package_sha256 %s' % man['package_sha256'])


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] != 'seal':
        sys.exit(__doc__)
    seal(a[1], dry='--dry' in a[2:])


if __name__ == '__main__':
    main()
