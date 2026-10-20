"""Equivalence checker for two Dissidia 012 discs (P1.6). READ-ONLY: opens both ISOs 'rb', never writes anything.

  python3 -I tools/pkg/equiv.py A.iso B.iso [--mode content|layout] [--expect-engine] [--json OUT.json] [--max N]

Resolves every game file the way the game does and compares bytes:
  * PACKAGE paths: EXTRA.IDX first (only when DATA/EXTRA.IDX is valid AND DATA/MODULE/EXTRA.PRX exists, else the game
    never reads it), then PACKAGE_INFO.BIN; bytes come from PACKAGE.BIN at row sector (the 20-bit field) for row size.
    The universe = every hash in either disc's PACKAGE_INFO or EXTRA.IDX.
  * every ISO9660 file except the index/layout files (PACKAGE.BIN, PACKAGE_INFO.BIN, EXTRA.IDX) byte for byte;
    EBOOT.BIN / OVL_*_APP.ELF differences are listed as words with their VA (+ the owner_tables code site nearby).
For every difference it drills down: MPK members (main.bin, main_lang …), ARC chunks (system.bin, objx …), FEP inside
an objx 'effe' chunk (fep.py semantic compare + the three effect-file rules: init blocks 12 mod 16, dense serials,
blob offsets mod 16 vs the other side), mess/menu pak entries, VOLD rows; names a path's owner_tables ids.

--mode content (default): verdict IDENTICAL when every game-readable file has the same bytes (= PHASE1-PLAN
  "content-identical"); layout differences (sectors, tier flags, EXTRA.IDX vs PACKAGE_INFO source, index files,
  PVD/ISO size) are summarised, not counted.
--mode layout: same, plus every layout difference listed and counted in the verdict.
--expect-engine: B may carry the engine (P1.4): DATA/MODULE/EXTRA.PRX only in B and EBOOT words equal to
  tools/pkg/engine/patches/engine-loader.json count as EXPECTED, not as differences.
Exit: 0 = IDENTICAL (in the chosen mode), 1 = differences, 2 = cannot read a disc.
"""
import argparse
import hashlib
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in ('tools/pkg/engine', 'tools/scripts'):
    sys.path.insert(0, os.path.join(ROOT, p))
import isolib  # noqa: E402  (tools/pkg/engine, read helpers only)
import xidx  # noqa: E402    (tools/pkg/engine, EXTRA.IDX parse with the module's checks)
from pkghash import pkg_hash  # noqa: E402

SECTOR = 2048
DATA = 'PSP_GAME/USRDIR/DATA/'
LAYOUT_FILES = {DATA + 'PACKAGE.BIN', DATA + 'PACKAGE_INFO.BIN', DATA + 'EXTRA.IDX'}
PRX = DATA + 'MODULE/EXTRA.PRX'
IMAGES = {'PSP_GAME/SYSDIR/EBOOT.BIN': ('EBOOT', 0x08804040 - 0x1018),
          DATA + 'OVL_MENU_APP.ELF': ('OVL_MENU_APP', 0x089DD4C0 - 0x54),
          DATA + 'OVL_BATTLE_APP.ELF': ('OVL_BATTLE_APP', 0x089DD4C0 - 0x54)}
ENGINE_PATCH = os.path.join(ROOT, 'tools/pkg/engine/patches/engine-loader.json')
OWNER_TABLES = os.path.join(ROOT, 'tools/dlc/owner_tables.json')


# ---------------------------------------------------------------- disc model
class Disc:
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        self.notes = []
        self.files = {}
        for p, sec, size in isolib.walk_extents(self.f):
            if not p.endswith('/'):
                self.files[p.lstrip('/').split(';')[0]] = (sec, size)
        self.f.seek(0, 2)
        self.iso_size = self.f.tell()
        self.pvd_sectors, = struct.unpack('<I', isolib.read_at(self.f, isolib.PVD_AT + 80, 4))
        self.pkg = self.files[DATA + 'PACKAGE.BIN']
        s, z = self.files[DATA + 'PACKAGE_INFO.BIN']
        self.pinfo_bytes = isolib.read_at(self.f, s * SECTOR, z)
        n, = struct.unpack_from('<I', self.pinfo_bytes, 8)
        self.prows = {}
        for i in range(n):
            h, sec, size = struct.unpack_from('<III', self.pinfo_bytes, 16 + 12 * i)
            self.prows[h] = (i, sec & 0xFFFFF, size & 0x0FFFFFFF, size >> 28)
        self.xrows, self.xover, self.xnames, self.xactive = {}, set(), {}, False
        self.xidx_bytes = None
        if DATA + 'EXTRA.IDX' in self.files:
            s, z = self.files[DATA + 'EXTRA.IDX']
            self.xidx_bytes = isolib.read_at(self.f, s * SECTOR, z)
            try:
                x = xidx.parse(self.xidx_bytes)
            except ValueError as ex:
                self.notes.append('EXTRA.IDX invalid (%s): the module would refuse it, game uses PACKAGE_INFO only' % (ex,))
            else:
                for i, (h, sec, size) in enumerate(x['rows']):
                    self.xrows[h] = (i, sec, size, 0)
                    if x['names']:
                        self.xnames[h] = x['names'][i]
                self.xover = {x['rows'][i][0] for i in x['overrides']}
                self.xactive = PRX in self.files
                if not self.xactive:
                    self.notes.append('EXTRA.IDX present but DATA/MODULE/EXTRA.PRX missing: the game never reads it')
        self._sha = {}

    def resolve(self, h):
        if self.xactive and h in self.xrows:
            i, sec, size, fl = self.xrows[h]
            return ('xidx', i, sec, size, fl)
        if h in self.prows:
            i, sec, size, fl = self.prows[h]
            return ('pinfo', i, sec, size, fl)
        return None

    def hashes(self):
        return set(self.prows) | (set(self.xrows) if self.xactive else set())

    def pkg_ok(self, sec, size):
        return sec * SECTOR + size <= self.pkg[1]

    def pkg_read(self, sec, size):
        return isolib.read_at(self.f, (self.pkg[0] + sec) * SECTOR, size)

    def sha_extent(self, abs_sector, size):
        k = (abs_sector, size)
        if k not in self._sha:
            h = hashlib.sha256()
            self.f.seek(abs_sector * SECTOR)
            left = size
            while left:
                b = self.f.read(min(left, 1 << 22))
                if not b:
                    h.update(b'<short read>')
                    break
                h.update(b)
                left -= len(b)
            self._sha[k] = h.hexdigest()
        return self._sha[k]

    def pkg_sha(self, sec, size):
        return self.sha_extent(self.pkg[0] + sec, size)

    def file_bytes(self, path):
        s, z = self.files[path]
        return isolib.read_at(self.f, s * SECTOR, z)


# ---------------------------------------------------------------- names and owner_tables ids
NAME_RE = re.compile(r"[A-Za-z0-9_./%-]+\.(?:objx|gmo|cosx|exex|gim|scd|bin|pak|mpk|arc|txt|at3|pmf|png|edat)", re.I)
NAME_GLOBS = ('tools/scripts/*.py', 'tools/scripts/*.sh', 'tools/dlc/*.py', 'tools/voice/*', 'notes/*.md', 'docs/*.md',
              'docs/learn/*.md', 'codex/inbox/*/*.json', 'codex/inbox/*/*.md', 'codex/inbox/*/*.py', 'codex/inbox/*/*.txt')


def load_names(discs):
    """hash -> path. Cosmetic only (never decides a verdict): path strings in our scripts/notes/inbox, clip tokens of
    tools/voice maps, every clip named in every VOLD voice list on both discs, EXTRA.IDX name tables."""
    import glob
    cand = set()
    for g in NAME_GLOBS:
        for p in glob.glob(os.path.join(ROOT, g)):
            if not os.path.isfile(p) or os.path.getsize(p) > 4 << 20:
                continue
            with open(p, errors='replace') as f:
                txt = f.read()
            cand.update(NAME_RE.findall(txt))
            if '/tools/voice/' in p:
                cand.update('voice/EN/battle/%s.at3' % t for t in re.findall(r'[A-Za-z0-9_]{4,40}', txt))
    for base in list(cand):
        for k in range(1, 13):
            cand.add(base.replace('1P', '%dP' % k).replace('1p', '%dp' % k))
    for d in discs:
        for h in d.hashes():
            r = d.resolve(h)
            if r[3] < 16 or not d.pkg_ok(r[2], r[3]) or d.pkg_read(r[2], 4) != b'VOLD':
                continue
            v = d.pkg_read(r[2], r[3])
            for i in range((len(v) - 16) // 24):
                clip = v[16 + 24 * i:40 + 24 * i].split(b'\0')[0].decode('latin-1')
                if clip:
                    cand.update('voice/EN/%s/%s.at3' % (sub, clip) for sub in ('battle', 'event'))
    nm = {pkg_hash(c): c for c in cand}
    for d in discs:
        nm.update(d.xnames)
    return nm


class Tables:
    def __init__(self, path):
        with open(path, encoding='utf-8') as f:
            self.t = json.load(f)['tables']
        self.ranges = []                     # (image, lo, hi, id)
        for t in self.t:
            w = t['where']
            img = 'OVL_BATTLE_APP' if 'battle' in w.lower() else 'OVL_MENU_APP' if 'menu' in w.lower() else 'EBOOT'
            for m in re.finditer(r'0x(08[0-9a-fA-F]{6})(?:\s*(?:\.\.|-)\s*0x(0?8?[0-9a-fA-F]{6,8}))?', w):
                lo = int(m.group(1), 16)
                hi = int(m.group(2), 16) if m.group(2) else lo + 4
                if hi < lo:
                    hi = lo + 4
                self.ranges.append((img, lo, hi, t['id']))

    def for_path(self, name):
        if not name:
            return []
        low = name.lower()
        base = low.rsplit('/', 1)[-1]
        stem = base.split('.')[0]
        ids = []
        if low.startswith('obj/p_') and low.endswith('.objx'):
            return ['own_battle_file']
        if low.startswith('obj/') and re.search(r'\.(gmo|cosx|exex)$', low):
            ids.append('fighter_files')
        stem_re = re.sub(r'p_[a-z]{3}[0-9]{3}', 'p_<key>', stem)
        for t in self.t:
            w = t['where'].lower()
            if (len(stem) > 4 and stem in w) or base in w or ('<key>' in w and stem_re.replace('p_<key>', '<key>') in w):
                ids.append(t['id'])
        return sorted(set(ids))[:6]

    def for_va(self, img, va):
        hit = [i for (im, lo, hi, i) in self.ranges if im == img and lo <= va < hi]
        if hit:
            return sorted(set(hit))
        near = [(abs(va - lo), i) for (im, lo, hi, i) in self.ranges if im == img and abs(va - lo) <= 0x100]
        return ['near ' + min(near)[1]] if near else []


# ---------------------------------------------------------------- drill-down
def first_diff(a, b):
    n = min(len(a), len(b))
    for i in range(0, n, 4096):
        if a[i:i + 4096] != b[i:i + 4096]:
            for j in range(i, min(i + 4096, n)):
                if a[j] != b[j]:
                    return j
    return n if len(a) != len(b) else -1


def mpk_members(d):
    from mpk import entries
    return [(nm, d[o:o + z]) for nm, o, z in entries(d)]


def arc_chunks(d):
    n, = struct.unpack_from('<I', d, 4)
    out = []
    for k in range(n):
        typ, tag, o, z = struct.unpack_from('<I4sII', d, 16 + 16 * k)
        out.append(('%d:%s' % (k, tag.decode('latin-1')), d[o:o + z]))
    return out


def pak_entries(d):
    cnt, base = struct.unpack_from('<HI', d, 10)
    out = []
    for i in range(cnt):
        o, z = struct.unpack_from('<II', d, 16 + 8 * i)
        out.append(('id %d' % (base + i), d[o:o + z]))
    return out


def fep_health(d):
    import fep as F
    fields = F.walk(d)
    mis = sum(1 for _, t, k in fields if k in ('n20_data', 'n24_data') and t % 16 != 12)
    serials, seen_t = [], set()
    for f, t, k in fields:
        if k != 't2c_data' or t in seen_t:
            continue
        seen_t.add(t)
        n = F.u16(d, f - 4)
        serials += [F.u16(d, t + 4 * j + 2) for j in range(n)]
    dense = sorted(serials) == list(range(len(serials)))
    return 'init blocks off 12 mod 16: %d, serials %d %s' % (mis, len(serials), 'dense' if dense else 'NOT dense (gaps/repeats)')


def explain_fep(a, b):
    try:
        import fep as F
        diffs = F.same_semantics(a, b)
        out = []
        if not diffs:
            fa, fb = F.Fep(a), F.Fep(b)
            mod = sum(1 for x, y in zip(fa.blobs, fb.blobs) if x.off % 16 != y.off % 16)
            out.append('FEP same data, different layout; %d blob(s) changed offset mod 16 (alignment rule)' % mod)
        else:
            out.append('FEP data differs: %s%s' % ('; '.join(diffs[:4]), ' …' if len(diffs) > 4 else ''))
        out.append('FEP A: %s; size %d' % (fep_health(a), len(a)))
        out.append('FEP B: %s; size %d' % (fep_health(b), len(b)))
        return out
    except Exception as ex:
        return ['FEP compare failed (%s)' % ex]


def explain(a, b, depth=0, limit=12):
    """-> list of reason lines (indented by depth)."""
    pad = '  ' * depth
    out = []
    if len(a) != len(b):
        out.append('%ssize %d -> %d' % (pad, len(a), len(b)))
    kind, ga, gb = None, None, None
    try:
        if a[:4] == b[:4] == b'MPK ':
            kind, ga, gb = 'MPK member', mpk_members(a), mpk_members(b)
        elif a[:4] == b[:4] == b'ARC\x01':
            kind, ga, gb = 'ARC chunk', arc_chunks(a), arc_chunks(b)
        elif a[:4] == b[:4] == b'FEP\xcd':
            return out + [pad + x for x in explain_fep(a, b)]
        elif a[:8] == b[:8] and a[:8] in (b'mess pak', b'menu pak'):
            kind, ga, gb = a[:8].decode() + ' entry', pak_entries(a), pak_entries(b)
        elif a[:4] == b[:4] == b'VOLD':
            ra = [a[16 + 24 * i:40 + 24 * i] for i in range((len(a) - 16) // 24)]
            rb = [b[16 + 24 * i:40 + 24 * i] for i in range((len(b) - 16) // 24)]
            kind, ga, gb = 'VOLD row', [(str(i), r) for i, r in enumerate(ra)], [(str(i), r) for i, r in enumerate(rb)]
    except Exception as ex:
        out.append('%s(container parse failed: %s)' % (pad, ex))
        kind = None
    if kind is None:
        i = first_diff(a, b)
        nd = sum(1 for x, y in zip(a, b) if x != y) if len(a) == len(b) and len(a) <= 1 << 24 else None
        out.append('%sbytes differ from offset 0x%x%s' % (pad, i, ', %d byte(s) differ' % nd if nd is not None else ''))
        return out
    da, db = dict(ga), dict(gb)
    if [k for k, _ in ga] != [k for k, _ in gb]:
        only_a = [k for k in da if k not in db]
        only_b = [k for k in db if k not in da]
        if only_a or only_b:
            out.append('%s%s count %d -> %d; only A: %s; only B: %s' % (
                pad, kind, len(ga), len(gb), ', '.join(only_a[:6]) or '-', ', '.join(only_b[:6]) or '-'))
        else:
            out.append('%s%s order differs' % (pad, kind))
    changed = [k for k, _ in ga if k in db and da[k] != db[k]]
    for k in changed[:limit]:
        out.append('%s%s %s differs (%d -> %d B)' % (pad, kind, k, len(da[k]), len(db[k])))
        if depth < 3:
            if kind == 'ARC chunk' and k.endswith(':effe'):
                try:
                    fa, fb = mpk_members(da[k])[0][1], mpk_members(db[k])[0][1]
                    out += ['%s  %s' % (pad, x) for x in explain_fep(fa, fb)]
                    continue
                except Exception as ex:
                    out.append('%s  effe parse failed (%s)' % (pad, ex))
            out += explain(da[k], db[k], depth + 1, limit=6)
    if len(changed) > limit:
        out.append('%s… %d more %ss differ' % (pad, len(changed) - limit, kind))
    return out


def word_diff(name, a, b, tables, expected_words):
    img, base = IMAGES[name]
    if a[:4] != b[:4]:
        return ['header %r -> %r (encrypted vs plain EBOOT? = eboot_plain)' % (a[:4], b[:4])], 0, 0
    lines, n, exp = [], 0, 0
    for o in range(0, min(len(a), len(b)) - 3, 4):
        if a[o:o + 4] != b[o:o + 4]:
            wa, = struct.unpack_from('<I', a, o)
            wb, = struct.unpack_from('<I', b, o)
            va = o + base
            if (img, va, wa, wb) in expected_words or (img, va, wb, wa) in expected_words:
                exp += 1
                continue
            n += 1
            if len(lines) < 40:
                site = tables.for_va(img, va)
                lines.append('%s 0x%08x: 0x%08x -> 0x%08x%s' % (img, va, wa, wb, '  [%s]' % ', '.join(site) if site else ''))
    if len(a) != len(b):
        n += 1
        lines.append('%s size %d -> %d (bytes past 0x%08x %s)' % (img, len(a), len(b), min(len(a), len(b)) + base,
                                                                    'added' if len(b) > len(a) else 'removed'))
    if n > len(lines):
        lines.append('… %d differing words in total' % n)
    return lines, n, exp


def load_engine_words(path):
    out = set()
    if not os.path.isfile(path):
        return out
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    for w in d.get('words', []):
        out.add(('EBOOT', int(w['va'], 16), int(w['old'], 16), int(w['new'], 16)))
    for e in d.get('edits', []):          # PACKAGE-FORMAT patches shape
        if 'old' in e:
            out.add((e['image'], int(e['va'], 16), int(e['old'], 16), int(e['new'], 16)))
    return out


# ---------------------------------------------------------------- main compare
def compare(A, B, mode, expect_engine, maxn, out_json):
    tables = Tables(OWNER_TABLES)
    names = load_names([A, B])
    ewords = load_engine_words(ENGINE_PATCH) if expect_engine else set()
    diffs, expected, layout = [], [], []

    def nm(h):
        return names.get(h, '?%08x' % h)

    # PACKAGE paths
    uni = A.hashes() | B.hashes()
    src_count = {}
    for h in sorted(uni):
        ra, rb = A.resolve(h), B.resolve(h)
        if ra is None or rb is None:
            r = ra or rb
            diffs.append(dict(kind='package', path=nm(h), hash='%08x' % h, what='only in %s (%s row, %d B)' % (
                'A' if ra else 'B', r[0], r[3]), tables=tables.for_path(names.get(h))))
            continue
        bad = [s for s, d, r in (('A', A, ra), ('B', B, rb)) if not d.pkg_ok(r[2], r[3])]
        if bad:
            diffs.append(dict(kind='package', path=nm(h), hash='%08x' % h,
                              what='row points past the end of PACKAGE.BIN on %s (unreadable)' % '/'.join(bad)))
            continue
        k = (ra[0], rb[0])
        src_count[k] = src_count.get(k, 0) + 1
        lay = []
        if ra[0] != rb[0]:
            lay.append('source %s -> %s' % (ra[0], rb[0]))
        if ra[2] != rb[2]:
            lay.append('sector')
        if ra[4] != rb[4]:
            lay.append('tier %d -> %d' % (ra[4], rb[4]))
        if ra[3] != rb[3] or A.pkg_sha(ra[2], ra[3]) != B.pkg_sha(rb[2], rb[3]):
            why = explain(A.pkg_read(ra[2], ra[3]), B.pkg_read(rb[2], rb[3]))
            diffs.append(dict(kind='package', path=nm(h), hash='%08x' % h, what='content differs',
                              why=why, tables=tables.for_path(names.get(h))))
        if lay:
            layout.append(dict(kind='package', path=nm(h), hash='%08x' % h, what=', '.join(lay)))

    # ISO files
    for p in sorted(set(A.files) | set(B.files)):
        ea, eb = A.files.get(p), B.files.get(p)
        if p in LAYOUT_FILES:
            # PACKAGE.BIN: only its extent matters (the rows were compared above; bytes outside rows are dead)
            if ea != eb or (ea and not p.endswith('PACKAGE.BIN') and A.sha_extent(*ea) != B.sha_extent(*eb)):
                if p.endswith('PACKAGE.BIN'):
                    w = 'PACKAGE.BIN extent %s -> %s (bytes outside rows are not game data)' % (ea, eb)
                elif ea is None or eb is None:
                    w = 'only in %s' % ('A' if ea else 'B')
                else:
                    w = 'index bytes differ'
                layout.append(dict(kind='index', path=p, what=w))
            continue
        if ea is None or eb is None:
            item = dict(kind='iso', path=p, what='only in %s (%d B)' % ('A' if ea else 'B', (ea or eb)[1]))
            (expected if expect_engine and p == PRX and eb else diffs).append(item)
            continue
        if ea[0] != eb[0]:
            layout.append(dict(kind='iso', path=p, what='sector %d -> %d' % (ea[0], eb[0])))
        if ea[1] == eb[1] and A.sha_extent(*ea) == B.sha_extent(*eb):
            continue
        a, b = A.file_bytes(p), B.file_bytes(p)
        if p in IMAGES:
            lines, n, exp = word_diff(p, a, b, tables, ewords)
            if exp:
                expected.append(dict(kind='code', path=p, what='%d engine-loader word(s) as expected' % exp))
            if n:
                diffs.append(dict(kind='code', path=p, what='%d word(s)/size differ' % n, why=lines))
        else:
            diffs.append(dict(kind='iso', path=p, what='content differs', why=explain(a, b)))

    # disc-level layout facts
    for label, x, y in (('ISO size', A.iso_size, B.iso_size), ('PVD volume sectors', A.pvd_sectors, B.pvd_sectors),
                        ('PACKAGE_INFO rows', len(A.prows), len(B.prows)), ('EXTRA.IDX rows', len(A.xrows), len(B.xrows)),
                        ('EXTRA.IDX active', A.xactive, B.xactive)):
        if x != y:
            layout.append(dict(kind='disc', path=label, what='%s -> %s' % (x, y)))
    tier = sum(1 for l in layout if 'tier' in l['what'])

    # report
    print('A %s\nB %s\nmode %s%s' % (A.path, B.path, mode, ', expect engine in B' if expect_engine else ''))
    for d, lab in ((A, 'A'), (B, 'B')):
        print('%s: %d PACKAGE_INFO rows, EXTRA.IDX %s, %d ISO files' % (
            lab, len(d.prows), ('%d rows (%d overrides)%s' % (len(d.xrows), len(d.xover), '' if d.xactive else ', inactive'))
            if d.xidx_bytes is not None else 'none', len(d.files)))
        for n_ in d.notes:
            print('  note %s: %s' % (lab, n_))
    print('resolved paths: %d; sources (A,B): %s' % (len(uni), ', '.join('%s/%s %d' % (k[0], k[1], v) for k, v in sorted(src_count.items()))))
    for x in diffs[:maxn]:
        print('DIFF %-7s %s: %s%s' % (x['kind'], x['path'], x['what'], ('  [%s]' % ', '.join(x['tables'])) if x.get('tables') else ''))
        for line in x.get('why', [])[:30]:
            print('       ' + line)
    if len(diffs) > maxn:
        print('… %d more differences (use --max or --json)' % (len(diffs) - maxn))
    for x in expected:
        print('EXPECTED %s %s: %s' % (x['kind'], x['path'], x['what']))
    if mode == 'layout':
        for x in layout[:maxn]:
            print('LAYOUT %-7s %s: %s' % (x['kind'], x['path'], x['what']))
        if len(layout) > maxn:
            print('… %d more layout differences' % (len(layout) - maxn))
    else:
        kinds = {}
        for x in layout:
            kinds[x['kind']] = kinds.get(x['kind'], 0) + 1
        print('layout differences (not content): %d%s%s' % (
            len(layout), ' (%s)' % ', '.join('%s %d' % kv for kv in sorted(kinds.items())) if kinds else '',
            '; PACKAGE_INFO tier flags changed on %d rows' % tier if tier else ''))
        for x in layout:
            if x['kind'] in ('index', 'disc'):
                print('  layout %s: %s' % (x['path'], x['what']))
    content_ok = not diffs
    if mode == 'layout':
        ok = content_ok and not layout
        verdict = 'IDENTICAL (content and layout)' if ok else \
            'CONTENT IDENTICAL, LAYOUT DIFFERS (%d)' % len(layout) if content_ok else 'DIFFERENT (%d content, %d layout)' % (len(diffs), len(layout))
    else:
        ok = content_ok
        verdict = ('IDENTICAL (content%s)' % (', %d expected engine item(s)' % len(expected) if expected else '')) if ok \
            else 'DIFFERENT (%d content difference%s)' % (len(diffs), '' if len(diffs) == 1 else 's')
    print('VERDICT: ' + verdict)
    if out_json:
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(dict(a=A.path, b=B.path, mode=mode, verdict=verdict, diffs=diffs, expected=expected, layout=layout),
                      f, indent=1, sort_keys=True)
            f.write('\n')
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--mode', choices=('content', 'layout'), default='content')
    ap.add_argument('--expect-engine', action='store_true')
    ap.add_argument('--json')
    ap.add_argument('--max', type=int, default=60)
    a = ap.parse_args()
    if a.json and os.path.splitext(a.json)[1].lower() == '.iso':
        sys.exit('refusing to write a .iso')
    try:
        A, B = Disc(a.a), Disc(a.b)
    except (OSError, ValueError, KeyError) as ex:
        print('cannot read disc: %s' % ex)
        sys.exit(2)
    sys.exit(compare(A, B, a.mode, a.expect_engine, a.max, a.json))


if __name__ == '__main__':
    main()
