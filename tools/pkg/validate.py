"""Validate fighter packages (P1.1, docs/PACKAGE-FORMAT.md). READ-ONLY: never writes anything, never opens an ISO.

  python3 -I tools/pkg/validate.py PKG_DIR [PKG_DIR ...] [--owner-tables FILE] [--pkginfo PACKAGE_INFO.BIN] [--strict]

Per package:
  1 schema       manifest.json, rows/*.json, patches/*.json, order.json against tools/pkg/schema/*.schema.json
                 (built-in JSON-Schema subset; no third-party module needed)
  2 canonical    every JSON file = sorted keys, 2-space indent, UTF-8, LF, final newline (pkgformat.canon_bytes)
  3 hashes       inventory lists every file (except manifest.json) with the right sha256 + size; nothing extra or
                 missing; package_sha256 matches; files[] sha256/size agree with the inventory
  4 table ids    every rows/<id>.json, patches/<id>.json, files[].table, allocation table, features[].table and
                 transitional patch id is an id in tools/dlc/owner_tables.json (kind sanity = warning)
  5 contents     row keys sorted + unique, op fields, raw length = row_size; patch edits aligned, sorted, no overlap;
                 allocations: known space, ids sorted/non-overlapping, limits, owner >= 34 -> objentry ids < 1338;
                 package paths unique by lower case and by PACKAGE hash; order.json keys exist
Across packages (all given dirs): unique id / owner / key, global allocation overlaps, same file or same row touched
twice, overlapping code edits, PACKAGE-hash clashes, requires/conflicts.
Optional --pkginfo (a PACKAGE_INFO.BIN you extracted yourself; read-only): 'add' paths must be new, 'replace' must exist.
Exit 0 = valid (warnings allowed unless --strict), 1 = errors.
"""
import argparse
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pkgformat as P  # noqa: E402

SCHEMA_DIR = os.path.join(HERE, 'schema')
ROOT = os.path.dirname(os.path.dirname(HERE))
OWNER_TABLES = os.path.join(ROOT, 'tools', 'dlc', 'owner_tables.json')
ROW_KINDS = {'data', 'text', 'menu-pack', 'save'}


# ---------------------------------------------------------------- JSON-Schema subset
PYTYPES = {'string': str, 'object': dict, 'array': list, 'boolean': bool}


def _type_ok(v, t):
    if t == 'integer':
        return isinstance(v, int) and not isinstance(v, bool)
    if t == 'number':
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == 'null':
        return v is None
    return isinstance(v, PYTYPES[t])


def schema_check(v, s, root, path='$'):
    """Return a list of error strings. Supports the keywords listed in manifest.schema.json 'description'."""
    errs = []
    if '$ref' in s:
        ref = s['$ref']
        if not ref.startswith('#/$defs/'):
            return ['%s: unsupported $ref %s' % (path, ref)]
        return schema_check(v, root['$defs'][ref[8:]], root, path)
    if 'type' in s:
        ts = s['type'] if isinstance(s['type'], list) else [s['type']]
        if not any(_type_ok(v, t) for t in ts):
            return ['%s: expected %s, got %s' % (path, '|'.join(ts), type(v).__name__)]
    if 'const' in s and v != s['const']:
        errs.append('%s: must be %r' % (path, s['const']))
    if 'enum' in s and v not in s['enum']:
        errs.append('%s: %r not in %s' % (path, v, s['enum']))
    if isinstance(v, str):
        if 'pattern' in s and not re.search(s['pattern'], v):
            errs.append('%s: %r does not match %s' % (path, v, s['pattern']))
        if len(v) < s.get('minLength', 0):
            errs.append('%s: shorter than %d' % (path, s['minLength']))
        if 'maxLength' in s and len(v) > s['maxLength']:
            errs.append('%s: longer than %d' % (path, s['maxLength']))
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if 'minimum' in s and v < s['minimum']:
            errs.append('%s: %r < %r' % (path, v, s['minimum']))
        if 'maximum' in s and v > s['maximum']:
            errs.append('%s: %r > %r' % (path, v, s['maximum']))
    if isinstance(v, list):
        if len(v) < s.get('minItems', 0):
            errs.append('%s: fewer than %d items' % (path, s['minItems']))
        if 'maxItems' in s and len(v) > s['maxItems']:
            errs.append('%s: more than %d items' % (path, s['maxItems']))
        if s.get('uniqueItems'):
            seen = [json.dumps(x, sort_keys=True) for x in v]
            if len(seen) != len(set(seen)):
                errs.append('%s: items not unique' % path)
        if 'items' in s:
            for i, x in enumerate(v):
                errs += schema_check(x, s['items'], root, '%s[%d]' % (path, i))
    if isinstance(v, dict):
        if len(v) < s.get('minProperties', 0):
            errs.append('%s: fewer than %d properties' % (path, s['minProperties']))
        for k in s.get('required', []):
            if k not in v:
                errs.append('%s: missing %r' % (path, k))
        props = s.get('properties', {})
        pprops = s.get('patternProperties', {})
        for k, x in v.items():
            sub = '%s.%s' % (path, k)
            if 'propertyNames' in s:
                errs += schema_check(k, s['propertyNames'], root, sub + '(name)')
            if k in props:
                errs += schema_check(x, props[k], root, sub)
                continue
            hit = False
            for pat, ps in pprops.items():
                if re.search(pat, k):
                    hit = True
                    errs += schema_check(x, ps, root, sub)
            if hit:
                continue
            ap = s.get('additionalProperties', True)
            if ap is False:
                errs.append('%s: unknown property' % sub)
            elif isinstance(ap, dict):
                errs += schema_check(x, ap, root, sub)
    for sub in s.get('allOf', []):
        errs += schema_check(v, sub, root, path)
    if 'anyOf' in s and not any(not schema_check(v, sub, root, path) for sub in s['anyOf']):
        errs.append('%s: matches none of anyOf' % path)
    if 'oneOf' in s:
        n = sum(1 for sub in s['oneOf'] if not schema_check(v, sub, root, path))
        if n != 1:
            errs.append('%s: matches %d of oneOf (need exactly 1)' % (path, n))
    return errs


def ns_file(ns):
    """Row namespace -> (target, file path) of the container it edits, or None (img:/save:)."""
    if ns.startswith('pkg:'):
        return ('package', ns[4:].split('!')[0].split('#')[0].lower())
    if ns.startswith('iso:'):
        return ('iso', ns[4:])
    return None


# ---------------------------------------------------------------- per package
class Pkg:
    def __init__(self, d):
        self.dir = d
        self.errs = []
        self.warns = []
        self.man = None
        self.rows = {}      # table id -> parsed rows file
        self.patches = {}   # site id -> parsed patches file
        self.order = None

    def e(self, msg):
        self.errs.append(msg)

    def w(self, msg):
        self.warns.append(msg)

    @property
    def name(self):
        return (self.man or {}).get('id') or self.dir


def load_json(pkg, rel, schema=None, schema_name=''):
    p = os.path.join(pkg.dir, rel)
    try:
        with open(p, 'rb') as f:
            raw = f.read()
        obj = json.loads(raw.decode('utf-8'))
    except (OSError, ValueError) as ex:
        pkg.e('%s: cannot read JSON (%s)' % (rel, ex))
        return None
    if raw != P.canon_bytes(obj):
        pkg.e('%s: not canonical JSON (sorted keys, indent 2, LF, final newline; run pkgformat.py seal)' % rel)
    if schema is not None:
        for m in schema_check(obj, schema, schema)[:40]:
            pkg.e('%s [%s]: %s' % (rel, schema_name, m))
    return obj


def version_ok(pkg, rel, fv):
    try:
        major, minor = (int(x) for x in fv.split('.'))
    except (ValueError, AttributeError):
        return
    if major != P.FORMAT_MAJOR:
        pkg.e('%s: format major %d unsupported (validator %d.%d)' % (rel, major, P.FORMAT_MAJOR, P.FORMAT_MINOR))
    elif minor > P.FORMAT_MINOR:
        pkg.e('%s: format %s newer than validator %d.%d - update tools/pkg' % (rel, fv, P.FORMAT_MAJOR, P.FORMAT_MINOR))


def check_package(pkg, S, tables, spaces):
    man = load_json(pkg, 'manifest.json', S['manifest'], 'manifest')
    if not isinstance(man, dict):
        return
    pkg.man = man
    version_ok(pkg, 'manifest.json', man.get('format_version'))
    tid = lambda t, where: t in tables or pkg.e('%s: %r is not an owner_tables.json id' % (where, t))  # noqa: E731

    # kind / owner / key consistency
    if man.get('kind') == 'fighter':
        if not isinstance(man.get('owner'), int) or not man.get('key'):
            pkg.e('manifest: a fighter package needs owner and key')
    elif man.get('owner') is not None:
        pkg.w('manifest: owner set on a non-fighter package')
    owner = man.get('owner') if isinstance(man.get('owner'), int) else None

    # ---- inventory / hashes
    inv = man.get('inventory') or {}
    disk = [r for r in P.walk_files(pkg.dir) if r != 'manifest.json']
    for r in disk:
        top = r.split('/')[0]
        if top not in P.TOP_DIRS and r != 'order.json':
            pkg.e('%s: file outside files/ rows/ patches/ (not allowed)' % r)
        if r not in inv:
            pkg.e('%s: on disk but not in manifest inventory' % r)
    for r in sorted(inv):
        p = os.path.join(pkg.dir, r)
        if not os.path.isfile(p):
            pkg.e('%s: in inventory but missing on disk' % r)
            continue
        size = os.path.getsize(p)
        if size != inv[r].get('size'):
            pkg.e('%s: size %d != inventory %s' % (r, size, inv[r].get('size')))
        if P.sha256_file(p) != inv[r].get('sha256'):
            pkg.e('%s: sha256 mismatch with inventory' % r)
    if man.get('package_sha256') and man['package_sha256'] != P.package_sha256(man):
        pkg.e('manifest: package_sha256 mismatch (manifest edited after sealing?)')

    # ---- files
    seen_lc, seen_hash = {}, {}
    for i, f in enumerate(man.get('files', [])):
        where = 'files[%d] %s' % (i, f.get('path'))
        tid(f.get('table'), where)
        rel = 'files/%s/%s' % (f.get('target'), f.get('path'))
        if f.get('produce'):
            if rel in inv:
                pkg.e('%s: produce=%s but bytes are shipped in %s' % (where, f['produce'], rel))
        elif rel not in inv:
            pkg.e('%s: %s missing from inventory' % (where, rel))
        else:
            if inv[rel].get('sha256') != f.get('sha256') or inv[rel].get('size') != f.get('size'):
                pkg.e('%s: sha256/size differ from inventory' % where)
        if f.get('target') == 'iso':
            if not str(f.get('path', '')).startswith('PSP_GAME/'):
                pkg.e('%s: iso path must start with PSP_GAME/' % where)
            if 'tier' in f:
                pkg.e('%s: tier only applies to target package' % where)
        else:
            if f.get('path', '').startswith('PSP_GAME/'):
                pkg.e('%s: package path looks like an ISO path' % where)
            lc = f.get('path', '').lower()
            if lc in seen_lc:
                pkg.e('%s: same package path (case-insensitive) as %s' % (where, seen_lc[lc]))
            seen_lc[lc] = f.get('path')
            h = P.pkg_hash(lc)
            if h in seen_hash and seen_hash[h] != lc:
                pkg.e('%s: PACKAGE hash %08x clashes with %s' % (where, h, seen_hash[h]))
            seen_hash[h] = lc
        if f.get('origin') == 'own' and f.get('action') == 'replace':
            pkg.w('%s: origin own but replaces a game file (check origin)' % where)
        if f.get('layouts') and not set(f['layouts']) <= set(man.get('layouts', [])):
            pkg.e('%s: layouts not a subset of manifest layouts' % where)
    paths = [(f.get('target'), f.get('path')) for f in man.get('files', [])]
    if paths != sorted(paths):
        pkg.e('manifest.files: not sorted by (target, path)')
    if len(set(paths)) != len(paths):
        pkg.e('manifest.files: duplicate entries')
    shipped = {'files/%s/%s' % tp for tp in paths}
    for r in inv:
        if r.startswith('files/') and r not in shipped:
            pkg.e('%s: file in files/ not described in manifest.files' % r)

    # ---- rows
    want_rows = set(man.get('rows', []))
    have_rows = {r[5:-5] for r in inv if r.startswith('rows/') and r.endswith('.json') and r.count('/') == 1}
    for r in inv:
        if r.startswith('rows/') and (r.count('/') != 1 or not r.endswith('.json')):
            pkg.e('%s: rows/ holds only <table id>.json files' % r)
    if man.get('rows', []) != sorted(man.get('rows', [])):
        pkg.e('manifest.rows: not sorted')
    for t in sorted(want_rows ^ have_rows):
        pkg.e('rows/%s.json: manifest.rows and rows/ disagree' % t)
    for t in sorted(have_rows):
        rel = 'rows/%s.json' % t
        tid(t, rel)
        if t in tables and tables[t]['kind'] not in ROW_KINDS:
            pkg.w('%s: owner_tables kind is %s (rows expected on data/text/menu-pack/save)' % (rel, tables[t]['kind']))
        doc = load_json(pkg, rel, S['rows'], 'rows')
        if not isinstance(doc, dict):
            continue
        version_ok(pkg, rel, doc.get('format_version'))
        pkg.rows[t] = doc
        if doc.get('table') != t:
            pkg.e('%s: table %r != file name' % (rel, doc.get('table')))
        kf = doc.get('key_fields') or []
        rs = doc.get('row_size')
        prev, keys = None, set()
        for i, row in enumerate(doc.get('rows', [])):
            w = '%s rows[%d]' % (rel, i)
            k = row.get('key') or {}
            if sorted(k) != sorted(kf):
                pkg.e('%s: key fields %s != key_fields %s' % (w, sorted(k), sorted(kf)))
                continue
            sk = (row.get('ns', ''), P.key_tuple(k, kf))
            if prev is not None and sk <= prev:
                pkg.e('%s: rows not sorted by (ns, key) or duplicate key' % w)
            prev = sk
            keys.add((row.get('ns'), json.dumps(k, sort_keys=True)))
            for fld in ('raw', 'old_raw'):
                if fld in row and isinstance(rs, int) and len(row[fld]) != 2 * rs:
                    pkg.e('%s: %s is %d bytes, row_size %d' % (w, fld, len(row[fld]) // 2, rs))
            if row.get('op') == 'patch':
                if len(row.get('old', '')) != len(row.get('new', '')) or not row.get('new'):
                    pkg.e('%s: patch old/new must be non-empty and equal length' % w)
                if isinstance(rs, int) and row.get('offset', 0) + len(row.get('new', '')) // 2 > rs:
                    pkg.e('%s: patch runs past row_size' % w)
            if row.get('op') == 'replace' and row.get('raw') == row.get('old_raw'):
                pkg.w('%s: replace with identical bytes' % w)
        doc['_keys'] = keys
        own = {(f.get('target'), f.get('path', '').lower() if f.get('target') == 'package' else f.get('path'))
               for f in man.get('files', [])}
        for ns in sorted({k[0] for k in keys}):
            if ns_file(ns) in own:
                pkg.e('%s: ns %s edits a file this package also ships whole (pick one)' % (rel, ns))

    # ---- patches
    want_p = set(man.get('patches', []))
    have_p = {r[8:-5] for r in inv if r.startswith('patches/') and r.endswith('.json') and r.count('/') == 1}
    if man.get('patches', []) != sorted(man.get('patches', [])):
        pkg.e('manifest.patches: not sorted')
    for t in sorted(want_p ^ have_p):
        pkg.e('patches/%s.json: manifest.patches and patches/ disagree' % t)
    spans = []
    for t in sorted(have_p):
        rel = 'patches/%s.json' % t
        tid(t, rel)
        if t in tables and tables[t]['kind'] not in ('code-site', 'iso-file'):
            pkg.w('%s: owner_tables kind is %s (patches expected on code-site/iso-file ids)' % (rel, tables[t]['kind']))
        doc = load_json(pkg, rel, S['patches'], 'patches')
        if not isinstance(doc, dict):
            continue
        version_ok(pkg, rel, doc.get('format_version'))
        pkg.patches[t] = doc
        if doc.get('site') != t:
            pkg.e('%s: site %r != file name' % (rel, doc.get('site')))
        if doc.get('layouts') and not set(doc['layouts']) <= set(man.get('layouts', [])):
            pkg.e('%s: layouts not a subset of manifest layouts' % rel)
        prev = None
        for i, ed in enumerate(doc.get('edits', [])):
            w = '%s edits[%d]' % (rel, i)
            try:
                va = int(ed.get('va', '0x0'), 16)
            except ValueError:
                continue
            if 'old' in ed:
                n = 4
                if va & 3:
                    pkg.e('%s: word edit at unaligned va' % w)
                if ed.get('old') == ed.get('new'):
                    pkg.w('%s: old == new' % w)
            else:
                n = len(ed.get('new_bytes') or '') // 2
                ob = ed.get('old_bytes')
                if ob is None and not ed.get('append'):
                    pkg.e('%s: old_bytes null needs append=true' % w)
                if ob is not None and len(ob) != len(ed.get('new_bytes') or ''):
                    pkg.e('%s: old_bytes/new_bytes length differ' % w)
            if 'append' in ed and 'old' in ed:
                pkg.e('%s: append only for byte edits' % w)
            key = (ed.get('image'), va)
            if prev is not None and key <= prev:
                pkg.e('%s: edits not sorted by (image, va)' % w)
            prev = key
            spans.append((ed.get('image'), va, va + n, t))
    spans.sort()
    for a, b in zip(spans, spans[1:]):
        if a[0] == b[0] and b[1] < a[2]:
            pkg.e('patches: %s %s 0x%08x overlaps %s 0x%08x' % (a[0], a[3], a[1], b[3], b[1]))
    pkg.spans = spans

    # ---- allocations
    pkg.alloc = []   # (space, ns, lo, hi | value, role)
    for space in sorted(man.get('allocations', {})):
        sp = spaces.get(space)
        if sp is None:
            pkg.e('allocations.%s: unknown space (tools/pkg/schema/spaces.json)' % space)
            continue
        ranges_by_ns = {}
        for j, a in enumerate(man['allocations'][space]):
            w = 'allocations.%s[%d]' % (space, j)
            tid(a.get('table', sp['table']), w)
            if sp.get('ns_required') and 'ns' not in a:
                pkg.e('%s: ns required for this space' % w)
            lim = sp.get('limits', {})
            bad = pkg.e if lim.get('level') == 'error' else pkg.w
            ns = a.get('ns', '')
            if sp['kind'] == 'int':
                if 'ids' not in a:
                    pkg.e('%s: int space needs ids' % w)
                    continue
                rs = P.norm_ids(a['ids'])
                for lo, hi in rs:
                    if lo > hi:
                        pkg.e('%s: range [%d, %d] reversed' % (w, lo, hi))
                    if lo < lim.get('min', 0) or ('max' in lim and hi > lim['max']):
                        bad('%s: %d..%d outside %s..%s' % (w, lo, hi, lim.get('min', 0), lim.get('max')))
                    cap = sp.get('owner_min_34_max')
                    if cap is not None and owner is not None and owner >= 34 and hi > cap:
                        pkg.e('%s: owner %d needs ids <= %d (P0.4 Cosmos rule), got %d' % (w, owner, cap, hi))
                if rs != sorted(rs):
                    pkg.e('%s: ids not sorted' % w)
                ranges_by_ns.setdefault(ns, []).extend((lo, hi, w) for lo, hi in rs)
                for lo, hi in rs:
                    pkg.alloc.append((space, ns, lo, hi, a.get('role', '')))
            else:
                if 'values' not in a:
                    pkg.e('%s: string space needs values' % w)
                    continue
                for v in a['values']:
                    if len(v) < lim.get('min_length', 0) or len(v) > lim.get('max_length', 1 << 30):
                        bad('%s: %r length outside limits' % (w, v))
                    pkg.alloc.append((space, ns, v, v, a.get('role', '')))
        for ns, rs in ranges_by_ns.items():
            rs.sort()
            for x, y in zip(rs, rs[1:]):
                if y[0] <= x[1]:
                    pkg.e('allocations.%s: %d..%d (%s) overlaps %d..%d (%s) inside this package'
                          % (space, x[0], x[1], x[2], y[0], y[1], y[2]))

    # ---- features
    for name, ft in sorted(man.get('features', {}).items()):
        tid(ft.get('table'), 'features.%s' % name)
        for s in ft.get('transitional_patches', []):
            if s not in have_p:
                pkg.e('features.%s: transitional patch %s has no patches/%s.json' % (name, s, s))

    # ---- order.json
    if 'order.json' in inv:
        doc = load_json(pkg, 'order.json', S['order'], 'order')
        if isinstance(doc, dict):
            version_ok(pkg, 'order.json', doc.get('format_version'))
            pkg.order = doc
            for i, sq in enumerate(doc.get('sequences', [])):
                w = 'order.json sequences[%d]' % i
                rd = pkg.rows.get(sq.get('table'))
                if rd is None:
                    pkg.e('%s: no rows/%s.json' % (w, sq.get('table')))
                    continue
                listed = [(sq.get('ns'), json.dumps(k, sort_keys=True)) for k in sq.get('keys', [])]
                if len(set(listed)) != len(listed):
                    pkg.e('%s: duplicate keys' % w)
                for k in listed:
                    if k not in rd['_keys']:
                        pkg.e('%s: key %s not in rows/%s.json ns %s' % (w, k[1], sq.get('table'), sq.get('ns')))
                inns = {k for k in rd['_keys'] if k[0] == sq.get('ns')}
                if inns - set(listed):
                    pkg.e('%s: sequence must list every row of ns %s (%d missing)' % (w, sq.get('ns'), len(inns - set(listed))))


# ---------------------------------------------------------------- across packages
def cross_check(pkgs, spaces, errs, warns):
    def uniq(field):
        seen = {}
        for p in pkgs:
            v = (p.man or {}).get(field)
            if v is None:
                continue
            if v in seen:
                errs.append('%s %r used by both %s and %s' % (field, v, seen[v], p.name))
            seen[v] = p.name
    for f in ('id', 'owner', 'key'):
        uniq(f)
    ids = {p.name: p for p in pkgs}
    for p in pkgs:
        for r in p.man.get('requires', []):
            if r['id'] not in ids:
                warns.append('%s requires %s %s (not among the checked packages)' % (p.name, r['id'], r['version']))
            else:
                try:
                    have = tuple(int(x) for x in ids[r['id']].man['version'].split('.'))
                    need = tuple(int(x) for x in r['version'][2:].split('.'))
                except (KeyError, ValueError, AttributeError):
                    continue   # malformed version: already a schema error
                ok = have >= need if r['version'].startswith('>=') else have == need
                if not ok:
                    errs.append('%s requires %s %s, found %s' % (p.name, r['id'], r['version'], ids[r['id']].man['version']))
        for c in p.man.get('conflicts', []):
            if c in ids:
                errs.append('%s conflicts with %s' % (p.name, c))
    # allocations
    pool = {}
    for p in pkgs:
        for space, ns, lo, hi, role in p.alloc:
            sp = spaces.get(space, {})
            if sp.get('scope') != 'global':
                continue
            pool.setdefault((space, ns), []).append((lo, hi, p.name, role))
    for (space, ns), items in sorted(pool.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if spaces[space]['kind'] == 'string':
            for i, a in enumerate(items):
                for b in items[i + 1:]:
                    if a[2] != b[2] and (a[0].startswith(b[0]) or b[0].startswith(a[0])):
                        errs.append('allocation %s: %r (%s) clashes with %r (%s)' % (space, a[0], a[2], b[0], b[2]))
            continue
        items.sort()
        for i, a in enumerate(items):
            for b in items[i + 1:]:
                if b[0] > a[1]:
                    break
                if a[2] != b[2]:
                    fmt = '0x%08x' if space == 'code_cave' else '%d'
                    errs.append(('allocation %s%s: ' + fmt + '..' + fmt + ' (%s) overlaps ' + fmt + '..' + fmt + ' (%s)')
                                % (space, ' ns=' + ns if ns else '', a[0], a[1], a[2], b[0], b[1], b[2]))
    # files, rows, code
    fseen, hseen, rseen = {}, {}, {}
    for p in pkgs:
        for f in p.man.get('files', []):
            k = (f['target'], f['path'].lower() if f['target'] == 'package' else f['path'])
            if k in fseen:
                errs.append('file %s:%s touched by both %s and %s' % (k[0], f['path'], fseen[k], p.name))
            fseen[k] = p.name
            if f['target'] == 'package':
                h = P.pkg_hash(f['path'])
                if h in hseen and hseen[h][0] != f['path'].lower():
                    errs.append('PACKAGE hash %08x: %s (%s) vs %s (%s)' % (h, f['path'], p.name, hseen[h][0], hseen[h][1]))
                hseen[h] = (f['path'].lower(), p.name)
        for t, doc in p.rows.items():
            for k in doc.get('_keys', ()):
                kk = (t,) + k
                if kk in rseen:
                    errs.append('row %s %s %s touched by both %s and %s' % (t, k[0], k[1], rseen[kk], p.name))
                rseen[kk] = p.name
    for p in pkgs:
        for t, doc in p.rows.items():
            for ns in sorted({k[0] for k in doc.get('_keys', ())}):
                tgt = ns_file(ns)
                if tgt in fseen and fseen[tgt] != p.name:
                    errs.append('%s rows/%s.json edits %s, which %s replaces whole' % (p.name, t, ns, fseen[tgt]))
    spans = sorted(s + (p.name,) for p in pkgs for s in getattr(p, 'spans', []))
    for a, b in zip(spans, spans[1:]):
        if a[0] == b[0] and b[1] < a[2] and a[4] != b[4]:
            errs.append('code %s 0x%08x (%s/%s) overlaps 0x%08x (%s/%s)' % (a[0], a[1], a[4], a[3], b[1], b[4], b[3]))


def pkginfo_check(pkgs, path, errs):
    with open(path, 'rb') as f:
        info = f.read()
    n, = struct.unpack_from('<I', info, 8)
    hashes = {struct.unpack_from('<I', info, 16 + i * 12)[0] for i in range(n)}
    for p in pkgs:
        for f in p.man.get('files', []):
            if f['target'] != 'package':
                continue
            present = P.pkg_hash(f['path']) in hashes
            if f['action'] == 'add' and present:
                errs.append('%s: add %s but its hash is already in %s' % (p.name, f['path'], path))
            if f['action'] == 'replace' and not present:
                errs.append('%s: replace %s but it is not in %s' % (p.name, f['path'], path))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('packages', nargs='+')
    ap.add_argument('--owner-tables', default=OWNER_TABLES)
    ap.add_argument('--pkginfo')
    ap.add_argument('--strict', action='store_true', help='warnings count as errors')
    a = ap.parse_args()
    with open(a.owner_tables, encoding='utf-8') as f:
        tables = {t['id']: t for t in json.load(f)['tables']}
    S = {}
    for n in ('manifest', 'rows', 'patches', 'order'):
        with open(os.path.join(SCHEMA_DIR, n + '.schema.json'), encoding='utf-8') as f:
            S[n] = json.load(f)
    with open(os.path.join(SCHEMA_DIR, 'spaces.json'), encoding='utf-8') as f:
        spaces = json.load(f)['spaces']
    for sp in spaces.values():
        if sp['table'] not in tables:
            sys.exit('spaces.json names unknown owner_tables id %s' % sp['table'])

    pkgs, bad = [], 0
    for d in a.packages:
        p = Pkg(d)
        if not os.path.isfile(os.path.join(d, 'manifest.json')):
            p.e('no manifest.json')
        else:
            check_package(p, S, tables, spaces)
        pkgs.append(p)
    gerr, gwarn = [], []
    good = [p for p in pkgs if p.man is not None]
    cross_check(good, spaces, gerr, gwarn)
    if a.pkginfo:
        pkginfo_check(good, a.pkginfo, gerr)
    for p in pkgs:
        ne = len(p.errs) + (len(p.warns) if a.strict else 0)
        bad += ne
        m = p.man or {}
        print('%s %s  (%s %s, owner %s, key %s, %d files, %d row tables, %d patch sites)'
              % ('FAIL' if ne else 'OK  ', p.dir, m.get('id'), m.get('version'), m.get('owner'), m.get('key'),
                 len(m.get('files', [])), len(p.rows), len(p.patches)))
        for x in p.errs:
            print('  ERROR %s' % x)
        for x in p.warns:
            print('  warn  %s' % x)
    if len(pkgs) > 1 or gerr or gwarn:
        for x in gerr:
            print('ERROR (across packages) %s' % x)
        for x in gwarn:
            print('warn  (across packages) %s' % x)
        bad += len(gerr) + (len(gwarn) if a.strict else 0)
    print('VALID' if not bad else 'INVALID (%d problem%s)' % (bad, '' if bad == 1 else 's'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
