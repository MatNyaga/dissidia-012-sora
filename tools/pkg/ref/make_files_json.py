"""P1.0: write the reference file list of a built disc (R0) -> tools/pkg/ref/R0.files.json.

Every game-readable path (PACKAGE_INFO row) -> size, sha256, install tier flag, source:
  vanilla    = same hash and same bytes as the clean dump
  replaced   = hash exists on the clean dump, bytes differ (the mod changed that file)
  added      = hash not on the clean dump (a file the mod adds)
plus every loose ISO file (EBOOT, overlays, PRX, PACKAGE_INFO itself ...) -> size, sha256, same source rule.
Names are cosmetic (equiv.load_names); the key is the 8-hex path hash the game uses.
Read-only. Usage: python3 -I tools/pkg/ref/make_files_json.py BUILT.iso [CLEAN.iso] [OUT.json]
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'tools/pkg'))
import equiv  # noqa: E402

SECTOR = 0x800


def sha(b):
    return hashlib.sha256(b).hexdigest()


def rows(d):
    """hash -> (size, tier, sha256) for every PACKAGE_INFO row of disc d"""
    base = d.pkg[0]
    out = {}
    for h, (_, sec, size, tier) in d.prows.items():
        d.f.seek((base + sec) * SECTOR)
        out[h] = (size, tier, sha(d.f.read(size)))
    return out


def loose(d):
    out = {}
    for p, (sec, size) in d.files.items():
        d.f.seek(sec * SECTOR)
        out[p] = (size, sha(d.f.read(size)))
    return out


def source(key, val, clean):
    if key not in clean:
        return 'added'
    return 'vanilla' if clean[key][-1] == val[-1] else 'replaced'


def main():
    built = sys.argv[1]
    clean_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'dumps/ULUS10566.iso')
    out_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, 'R0.files.json')
    a, c = equiv.Disc(built), equiv.Disc(clean_path)
    names = equiv.load_names([a, c])
    ra, rc = rows(a), rows(c)
    la, lc = loose(a), loose(c)
    pkg = {}
    for h in sorted(ra):
        size, tier, digest = ra[h]
        e = dict(size=size, sha256=digest, tier=tier, source=source(h, ra[h], rc))
        if h in names:
            e['name'] = names[h]
        pkg['%08x' % h] = e
    iso = {p: dict(size=s, sha256=d, source=source(p, (s, d), lc)) for p, (s, d) in sorted(la.items())}
    gone = sorted('%08x' % h for h in rc if h not in ra)
    count = {}
    for e in list(pkg.values()) + list(iso.values()):
        count[e['source']] = count.get(e['source'], 0) + 1
    doc = dict(format='R0.files v1', disc=os.path.basename(built), disc_sha256=equiv.isolib.sha256_file(built),
               clean_sha256=equiv.isolib.sha256_file(clean_path), counts=count, package=pkg, iso_files=iso,
               removed_from_clean=gone)
    with open(out_path, 'w') as f:
        json.dump(doc, f, indent=1, sort_keys=False)
    print('%s: %d package rows, %d iso files, %s, removed %d' % (out_path, len(pkg), len(iso), count, len(gone)))


if __name__ == '__main__':
    main()
