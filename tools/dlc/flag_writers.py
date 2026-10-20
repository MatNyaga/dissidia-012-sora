"""P2.6 (Phase 2): every unlock-flag reader / writer we can find on the CLEAN game -> tools/dlc/flag_map.json.

Flags = bits of the save flag array at *(u32*)0x089D726C: flag F = word F>>5 (byte (F>>5)*4), bit F&31. The new-game
init FUN_088b0788 clears 0x80 words (flags 0..4095) and a second block of 0x20 words right after (4096..5119).

Sources (all read-only; nothing is ever written except the JSON / report):
  code   Ghidra decompiles of the clean binaries (dumps/decomp/all.c = EBOOT + OVL_BATTLE_APP, menu_all.c = EBOOT +
         OVL_MENU_APP): constant word/bit operations on the array (set / clear / test), flag-helper calls with a
         constant flag argument, constant local arrays, and every table-driven site (index taken from a table or a
         parameter) listed with its function so the table can be decoded or marked "unresolved".
         Coverage check from the clean bytes: every `lw rX,0x726c(rY)` after `lui rY,0x089d` (= load of the array
         pointer) in the plain EBOOT / clean overlays must sit in a function the decompile shows using the array.
  tables flag tables inside the code images: EBOOT unlock table 0x089D7BE0, comflag lists 0x089CDB18/0x089CDB28,
         menu level table 0x08A2E8AC, menu "all set?" list 0x08A455EC.
  data   update_list_param (PP Catalog), collection_param sections 0/6/8 (Museum, music, Jukebox characters),
         collection_voice_param (Jukebox rows), system.bin uicn / infp / tuto, bgm_entry, party_battle-pbtl.
Kinds: W = the game sets it, C = clears it, R = reads it, RW = both / role not certain.

  python3 -I tools/dlc/flag_writers.py [CLEAN.iso] [--json OUT] [--quiet]
Self-test (exits 1 if any fails): 1250-1252 W by FUN_08a2b07c, 1253-1262 W by level table 0x08A2E8AC, 1372 R by
FUN_08a41098, 925 in unlock row 22 (Chaos), 856-887 W by PP Catalog Encounter Voice items, 886 R by Jukebox rows.
"""
import hashlib
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools/scripts'))
sys.path.insert(0, os.path.join(ROOT, 'tools/pkg/engine'))
sys.dont_write_bytecode = True
import mpk  # noqa: E402
import isolib  # noqa: E402
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from spot33_save import arc_split  # noqa: E402

SECTOR = 0x800
ELF = os.path.join(ROOT, 'dumps/extracted/EBOOT.elf')
ELF_SHA = '0bc8e779aad2814a3d1bd77346f69ca5e16665845ed053cd0ad44a9cbfaefe6d'
DECOMP = {'battle': os.path.join(ROOT, 'dumps/decomp/all.c'), 'menu': os.path.join(ROOT, 'dumps/decomp/menu_all.c')}
OVL = {'menu': 'PSP_GAME/USRDIR/DATA/OVL_MENU_APP.ELF', 'battle': 'PSP_GAME/USRDIR/DATA/OVL_BATTLE_APP.ELF'}
OVL_VA, OVL_OFF, EBOOT_DELTA = 0x089DD4C0, 0x54, 0x08803028        # EBOOT VA = ELF offset + 0x08803028
NFLAGS = 5120
# where the flag numbers of table-driven code sites come from ('?' = inferred from the globals the function reads,
# not traced end to end). Every function not listed here is reported as an UNRESOLVED source.
SOURCES = {
    'FUN_088cc2b0': 'data infp (DAT_089d7808: u16 2, u16 n, 8-B rows, set-flag +4)?',
    'FUN_088cc3b0': 'data infp?', 'FUN_088cc440': 'data infp?',
    'FUN_088d5ac8': 'table EBOOT unlock 0x089D7BE0', 'FUN_088d5ce8': 'table EBOOT unlock 0x089D7BE0',
    'FUN_088d5e0c': 'table EBOOT unlock 0x089D7BE0', 'FUN_088d60e4': 'table EBOOT unlock 0x089D7BE0',
    'FUN_088d617c': 'table EBOOT unlock 0x089D7BE0',
    'FUN_088c42a8': 'table EBOOT 0x089CBB9C', 'FUN_088c4998': 'table EBOOT 0x089CBBEC',
    'FUN_08901d48': 'table EBOOT comflag 0x089CDB18/0x089CDB28',
    'FUN_08927bd0': 'data bgm_entry (DAT_089d6c30)?', 'FUN_08928b90': 'data bgm_entry (DAT_089d6c30)?',
    'FUN_08a55d54': 'data bgm_entry (DAT_089d6c30)?',
    'FUN_08ade4e0': 'data bgm_entry (DAT_089d6c30)?', 'FUN_08adebb4': 'data bgm_entry (DAT_089d6c30)?',
    'FUN_08aded20': 'data bgm_entry (DAT_089d6c30)?', 'FUN_08adeeb4': 'data bgm_entry (DAT_089d6c30)?',
    'FUN_08adf04c': 'data bgm_entry (DAT_089d6c30)?', 'FUN_08adf22c': 'data bgm_entry (DAT_089d6c30)?',
    'FUN_08a36d1c': 'data collection_param section 6 (Jukebox music)',
    'FUN_08a36ee8': 'data collection_param section 8 (Jukebox characters)',
    'FUN_08a37024': 'data collection_voice_param (Jukebox rows)',
    'FUN_08a3c548': 'data collection_param (Museum completion)', 'FUN_08a3c5e8': 'data collection_param (Museum completion)',
    'FUN_08a3c720': 'data collection_param (Museum completion)', 'FUN_08a3c7c4': 'data collection_param (Museum completion)',
    'FUN_08a3c868': 'data collection_param (Museum completion)', 'FUN_08a3c90c': 'data collection_param (Museum completion)',
    'FUN_08a3c9c8': 'data collection_param + collection_voice_param (Museum completion)',
    'FUN_08a2ebc8': 'data collection_param (Museum lists)?', 'FUN_08a2ee38': 'data collection_param (Museum lists)?',
    'FUN_08a301b0': 'data collection_param (Museum lists)?', 'FUN_08a3248c': 'data collection_param (Museum lists)?',
    'FUN_08a327cc': 'data collection_param (Museum lists)?', 'FUN_08a3cf00': 'data collection_param (Museum)?',
    'FUN_08a2b07c': 'table menu level 0x08A2E8AC', 'FUN_08a410b4': 'table menu list 0x08A455EC',
    'FUN_08a2adcc': 'table menu 0x08A2E730', 'FUN_08ab1470': 'table menu 0x08AB2374',
    'FUN_08ab185c': 'table menu 0x08AB2374', 'FUN_08af71e8': 'table menu 0x08B01C98',
    'FUN_08b0cb80': 'table menu 0x08B1C692', 'FUN_08b0ce94': 'table menu 0x08B1C692?',
    'FUN_08b19c14': 'table menu 0x08B1C692?', 'FUN_08b19f90': 'table menu 0x08B1C692?',
    'FUN_08a8a108': 'table menu 0x08A8B67E/0x08A8B680', 'FUN_08a8ba30': 'table menu 0x08A93A2E',
    'FUN_088b0788': 'new-game init (constant bits; clears both blocks)',
    'FUN_088b0ad8': 'sets the array pointer (save buffer DAT_089d712c + 0x1DF88)',
    'FUN_088ad574': 'whole-array copy/compare (save)?',
}
ARR = 'DAT_089d726c'
NUM = r'(0x[0-9a-fA-F]+|\d+)'


def num(s):
    return int(s, 0)


# ------------------------------------------------------------------ binaries
class Images:
    def __init__(self, iso):
        self.iso = iso
        eb = open(ELF, 'rb').read()
        assert hashlib.sha256(eb).hexdigest() == ELF_SHA, 'dumps/extracted/EBOOT.elf is not the clean plain EBOOT'
        self.eboot = eb
        self.ovl = {}
        with open(iso, 'rb') as f:
            files = {p.lstrip('/').split(';')[0]: (s, z) for p, s, z in isolib.walk_extents(f) if not p.endswith('/')}
            for k, p in OVL.items():
                s, z = files[p]
                self.ovl[k] = read_at(f, s * SECTOR, z)

    def read(self, va, n, where='eboot'):
        if va < OVL_VA:
            o = va - EBOOT_DELTA
            return self.eboot[o:o + n]
        o = va - OVL_VA + OVL_OFF
        return self.ovl[where][o:o + n]

    def code(self):
        """(name, bytes, va of byte 0) for the byte scan"""
        yield 'eboot', self.eboot, EBOOT_DELTA
        for k, b in self.ovl.items():
            yield k, b, OVL_VA - OVL_OFF


# ------------------------------------------------------------------ decompile
def functions(path):
    src = open(path).read()
    parts = re.split(r'(?m)^// ===== (FUN_[0-9a-f]+) @ ([0-9a-f]+)\n', src)
    return {parts[i]: (int(parts[i + 1], 16), parts[i + 2]) for i in range(1, len(parts), 3)}


def load_decomp():
    """name -> (va, body, image); EBOOT functions once (from all.c)"""
    out = {}
    for img, path in DECOMP.items():
        for n, (va, body) in functions(path).items():
            im = 'eboot' if va < OVL_VA else img
            if im == 'eboot' and n in out:
                continue
            out[n if im != 'menu' or n not in out else n + '@menu'] = (va, body, im)
    return out


def bits(mask):
    return [b for b in range(32) if mask >> b & 1]


def statements(body):
    return [s.strip() for s in re.split(r';\s*\n', body)]


WORD_PATS = [
    (re.compile(r'\*\(uint \*\)\(' + ARR + r' \+ ' + NUM + r'\)'), 'byte'),
    (re.compile(ARR + r'\[' + NUM + r'\]'), 'word'),
    (re.compile(r'\*' + ARR + r'(?![\w\[])'), 'zero'),
]


def const_sites(name, body, image, rec):
    """constant word + mask operations"""
    for st in statements(body):
        if ARR not in st:
            continue
        for pat, how in WORD_PATS:
            for m in pat.finditer(st):
                if how == 'byte':
                    off = num(m.group(1))
                    if off % 4:
                        continue
                    w = off // 4
                elif how == 'word':
                    w = num(m.group(1))
                else:
                    w = 0
                write = re.search(re.escape(m.group(0)) + r'\s*=(?!=)', st) is not None
                after = re.match(r'\s*([|&])\s*(~?)\s*\(?' + NUM, st[m.end():])
                if not after:
                    continue
                op, neg, mv = after.groups()
                mask = num(mv) & 0xFFFFFFFF
                if neg:
                    mask = ~mask & 0xFFFFFFFF
                if op == '|':
                    kind, bl = ('W' if write else 'R'), bits(mask)
                elif bin(mask).count('1') > 16:
                    kind, bl = ('C' if write else 'R'), bits(~mask & 0xFFFFFFFF)
                else:
                    kind, bl = 'R', bits(mask)
                for b in bl:
                    rec(32 * w + b, kind, 'code %s %s' % (image, name), 'constant word %d mask 0x%X' % (w, mask))


GEN = re.compile(r'\(' + ARR + r' \+ \((?:\(uint\))?\(?([^;]*?)\)?\s*>> 5\)\s*\*\s*4\)')


def generic_sites(name, body):
    """index expressions of `(ARR + (X >> 5) * 4)` sites"""
    return [m.group(1).strip() for m in GEN.finditer(body)]


def helper_params(body):
    """param numbers used directly as a flag index"""
    out = set()
    for e in generic_sites(None, body):
        m = re.fullmatch(r'\(?(?:uint\))?\(?param_(\d)(?: & 0xffff)?\)?', e.replace('(uint)', ''))
        if m:
            out.add(int(m.group(1)))
    return out


def local_arrays(body):
    arr = {}
    for v, i, c in re.findall(r'(local_\w+)\[(\d+)\] = ' + NUM + ';', body):
        arr.setdefault(v, {})[int(i)] = num(c)
    for v, c in re.findall(r'(local_\w+) = ' + NUM + ';', body):
        arr.setdefault(v.split('[')[0], {})[0] = num(c)
    return arr


def call_args(body, fname):
    for m in re.finditer(fname + r'\(', body):
        i, depth, cur, args = m.end(), 1, '', []
        while i < len(body) and depth:
            ch = body[i]
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if not depth:
                    break
            if ch == ',' and depth == 1:
                args.append(cur.strip())
                cur = ''
            else:
                cur += ch
            i += 1
        args.append(cur.strip())
        yield args


def scan_code(dec, rec, report):
    users = {n for n, (_, b, _) in dec.items() if ARR in b}
    helpers = {}
    for n in users:
        ps = helper_params(dec[n][1])
        if ps:
            helpers[n.split('@')[0]] = ps
    report['helpers'] = {h: sorted(p) for h, p in sorted(helpers.items())}
    table_driven = []
    for n in sorted(users):
        va, body, im = dec[n]
        const_sites(n, body, im, rec)
        la = local_arrays(body)
        for e in generic_sites(n, body):
            m = re.fullmatch(r'(local_\w+)\[.*\]', e)
            if m and m.group(1) in la:
                for v in la[m.group(1)].values():
                    rec(v, 'R' if '|' not in body.split(e)[1][:80] else 'RW', 'code %s %s' % (im, n),
                        'constant local array %s' % m.group(1))
                continue
            if re.fullmatch(r'\(?(?:uint\))?\(?param_\d(?: & 0xffff)?\)?', e.replace('(uint)', '')):
                continue                                    # a helper: its callers are scanned below
            table_driven.append({'function': n, 'image': im, 'va': '0x%08X' % va, 'index': e})
    for n, (va, body, im) in dec.items():
        for h, ps in helpers.items():
            if h == n.split('@')[0] or h + '(' not in body:
                continue
            for args in call_args(body, h):
                for p in ps:
                    if p - 1 < len(args) and re.fullmatch(NUM, args[p - 1]):
                        v = num(args[p - 1])
                        if v not in (0xFFFF, 0xFFFFFFFF) and v < NFLAGS:
                            rec(v, 'RW', 'code %s %s' % (im, n), 'constant argument to helper %s' % h)
    for n in sorted(users):                                 # anything else (precomputed word index, aliases)
        va, body, im = dec[n]
        rest = GEN.sub('', body)
        for pat, _ in WORD_PATS:
            rest = pat.sub('', rest)
        for m in re.finditer(ARR + r'[^;]{0,50}', rest):
            table_driven.append({'function': n, 'image': im, 'va': '0x%08X' % va, 'index': 'other: ' + m.group(0)})
    for t in table_driven:
        t['source'] = SOURCES.get(t['function'].split('@')[0], 'UNRESOLVED')
    report['table_driven_sites'] = table_driven
    report['unresolved_functions'] = sorted({t['function'] for t in table_driven if t['source'] == 'UNRESOLVED'})
    return users


def byte_sites(ws, k):
    """small forward data-flow from the array-pointer load at word K: constant word + mask operations
    -> [(word, mask, kind)]; kind R / W / C. Masks built at run time (sllv) are left to the decompile scan."""
    const, arr, val, out = {0: 0}, {}, {}, []
    for j in range(max(0, k - 16), min(len(ws), k + 16)):
        w = ws[j]
        op, rs, rt, rd, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31, w & 0xFFFF
        fn = w & 63
        simm = imm - 0x10000 if imm & 0x8000 else imm
        dest = None
        new = {}
        if op == 0x0F:
            dest, new = rt, {'const': imm << 16}
        elif op == 0x0D:
            dest = rt
            if rs in const:
                new = {'const': const[rs] | imm}
        elif op == 0x09:
            dest = rt
            if rs == 0:
                new = {'const': simm & 0xFFFFFFFF}
            elif rs in arr:
                new = {'arr': arr[rs] + simm}
        elif op in (0x20, 0x21, 0x23, 0x24, 0x25):                       # loads
            dest = rt
            if op == 0x23 and j == k:
                new = {'arr': 0}
            elif op == 0x23 and rs in arr and (arr[rs] + simm) % 4 == 0:
                new = {'val': ((arr[rs] + simm) // 4, None, None)}
        elif op == 0x0C:                                                 # andi = test
            dest = rt
            if rs in val and val[rs][1] is None:
                out.append((val[rs][0], imm, 'R'))
        elif op in (0x0A, 0x0B, 0x0E):
            dest = rt
        elif op == 0 and fn in (0x24, 0x25, 0x27, 0x21, 0x23, 0x2A, 0x2B, 0x00, 0x02, 0x03, 0x04, 0x06, 0x07, 0x0A, 0x0B):
            dest = rd
            if fn in (0x24, 0x25):
                x, y = (rs, rt) if rs in val else (rt, rs)
                if x in val and val[x][1] is None and y in const:
                    m = const[y]
                    if fn == 0x24:
                        out.append((val[x][0], m, 'R?'))                 # test, or a clear if stored below
                        new = {'val': (val[x][0], 'and', m)}
                    else:
                        new = {'val': (val[x][0], 'or', m)}
            elif fn == 0x27 and rs in const and rt in const:
                new = {'const': ~(const[rs] | const[rt]) & 0xFFFFFFFF}
            elif fn == 0x21 and rs in arr and rt == 0:
                new = {'arr': arr[rs]}
        elif op == 0x2B and rs in arr and rt in val and val[rt][1] in ('or', 'and'):
            wd, how, m = val[rt]
            if how == 'or':
                out.append((wd, m, 'W'))
            else:
                out = [o for o in out if not (o[0] == wd and o[1] == m and o[2] == 'R?')]
                out.append((wd, ~m & 0xFFFFFFFF, 'C'))
        if dest is not None and dest != 0:
            for d in (const, arr, val):
                d.pop(dest, None)
            for kk, v in new.items():
                {'const': const, 'arr': arr, 'val': val}[kk][dest] = v
        if op in (0x02, 0x03) or (op == 0 and fn in (0x08, 0x09)):
            if j > k + 1:
                break
    res = []
    for wd, m, kind in out:
        if kind == 'R?':
            kind = 'R'
            if bin(m).count('1') > 16:                                   # "x & ~bits" tested: report the bits
                m = ~m & 0xFFFFFFFF
        res.append((wd, m, kind))
    return res


def coverage(imgs, dec, users, rec=None, byte_only=None):
    """array-pointer loads in the clean bytes vs functions the decompile shows using the array"""
    starts = {}
    for n, (va, _, im) in dec.items():
        starts.setdefault(im if im != 'eboot' else 'eboot', []).append((va, n))
    for k in starts:
        starts[k].sort()
    missing, total = [], 0
    for im, code, base in imgs.code():
        ws = struct.unpack('<%dI' % (len(code) // 4), code[:len(code) // 4 * 4])
        for k, w in enumerate(ws):
            if w >> 26 == 0x23 and (w & 0xFFFF) == 0x726C:
                rs = (w >> 21) & 31
                if not any(ws[j] >> 16 == (0x3C00 | rs) and (ws[j] & 0xFFFF) == 0x089D for j in range(max(0, k - 24), k)):
                    continue
                total += 1
                va = base + 4 * k
                if rec is not None:
                    for wd, mask, kind in byte_sites(ws, k):
                        for b in bits(mask):
                            rec(32 * wd + b, kind, 'code-bytes %s 0x%08X' % (im, va), 'word %d mask 0x%X' % (wd, mask))
                            byte_only.add((32 * wd + b, kind, im, va))
                lst = starts.get(im, [])
                fn = None
                for s, n in lst:
                    if s <= va:
                        fn = n
                    else:
                        break
                if fn is None or fn not in users:
                    missing.append('%s 0x%08X (in %s)' % (im, va, fn))
    return total, missing


# ------------------------------------------------------------------ tables in the code images
def scan_tables(imgs, rec):
    for i in range(64):                                             # EBOOT unlock table
        r = struct.unpack('<5i', imgs.read(0x089D7BE0 + 20 * i, 20))
        if r[0] == -1:
            break
        for col, what in ((1, 'unlock'), (2, 'costume 2'), (3, 'costume 3')):
            if 0 <= r[col] < NFLAGS:
                rec(r[col], 'R', 'table EBOOT unlock 0x089D7BE0', 'row %d owner %d %s' % (i, r[0], what))
    for t in (0x089CDB18, 0x089CDB28):                               # comflag lists (FUN_08901d48)
        for k in range(32):
            c, p = struct.unpack('<iI', imgs.read(t + 8 * k, 8))
            if c <= 0:
                break
            for v in struct.unpack('<8h', imgs.read(p, 16)):
                if 0 <= v < NFLAGS:
                    rec(v, 'RW', 'table EBOOT comflag 0x%08X' % t, 'key %d' % c)
    va = 0x08A2E8AC                                                  # menu level milestones (owner, level, flag)
    while True:
        o, lv, fl = struct.unpack('<3i', imgs.read(va, 12, 'menu'))
        if o <= 0:
            break
        rec(fl, 'W', 'table menu level 0x08A2E8AC (FUN_08a2b07c)', 'owner %d at level %d' % (o, lv))
        va += 12
    # small constant tables found behind table-driven sites (decoded by hand from the clean images)
    for va, n, fmt, where, site, kind in (
            (0x089CBB9C, 20, 'I', 'eboot', 'table EBOOT 0x089CBB9C (FUN_088c42a8)', 'R'),
            (0x089CBBEC, 30, 'H', 'eboot', 'table EBOOT 0x089CBBEC u16 pairs (FUN_088c4998)', 'R'),
            (0x08A2E730, 15, 'i', 'menu', 'table menu 0x08A2E730 (FUN_08a2adcc)', 'RW'),
            (0x08AB2374, 10, 'i', 'menu', 'table menu 0x08AB2374 (FUN_08ab1470/FUN_08ab185c)', 'R'),
            (0x08B01CB0, 3, 'i', 'menu', 'table menu 0x08B01C98 (FUN_08af71e8)', 'R'),
            (0x08B1C692, 18, 'H', 'menu', 'table menu 0x08B1C692 (FUN_08b0cb80/FUN_08b19c14)', 'RW'),
            (0x08A8B67E, 1, 'H', 'menu', 'table menu 0x08A8B67E base (+index, FUN_08a8a108)', 'R'),
            (0x08A8B680, 1, 'H', 'menu', 'table menu 0x08A8B680 (FUN_08a8a108)', 'W'),
            (0x08A93A2E, 1, 'H', 'menu', 'table menu 0x08A93A2E (FUN_08a8ba30)', 'R')):
        sz = struct.calcsize(fmt)
        for v in struct.unpack('<%d%s' % (n, fmt), imgs.read(va, n * sz, where)):
            if 0 <= v < NFLAGS:
                rec(v, kind, site, '')
    va = 0x08A455EC                                                  # menu "all set?" list (FUN_08a410b4)
    while True:
        v, = struct.unpack('<I', imgs.read(va, 4, 'menu'))
        if v == 0xFFFFFFFF or v >= NFLAGS:
            break
        rec(v, 'R', 'table menu list 0x08A455EC (FUN_08a410b4)', '')
        va += 4


# ------------------------------------------------------------------ data files
def scan_data(iso, rec):
    use_iso(iso)

    def get(path):
        st, sz = pkg_offset(path)
        with open(iso, 'rb') as f:
            return read_at(f, st, sz)

    d = get('update_list_param.bin')                                 # PP Catalog
    cnt = struct.unpack_from('<5h', d, 2)
    k = 0
    for tab, n in enumerate(cnt):
        for j in range(n):
            it = struct.unpack_from('<I12h', d, 16 + 28 * k)
            src = 'data PP Catalog tab %d item %d' % (tab, j)
            for col, kind, what in ((4, 'R', 'visible-after'), (5, 'R', 'visible-after 2'), (6, 'W', 'set when bought'),
                                    (7, 'RW', 'NEW tag')):
                if 0 <= it[col] < NFLAGS:
                    rec(it[col], kind, src, '%s (%d PP)' % (what, it[0]))
            k += 1
    cp = get('collection_param.bin')                                 # Museum
    h = struct.unpack_from('<20H', cp, 0)
    offs = [40]
    for sz in h[11:20]:
        offs.append(offs[-1] + sz)
    for i in range(h[2]):
        a, b = struct.unpack_from('<2H', cp, offs[0] + 48 * i + 8)
        rec(a, 'R', 'data Museum record %d' % i, 'unlock')
        rec(b, 'RW', 'data Museum record %d' % i, 'viewed')
    for i in range(h[8]):
        rec(struct.unpack_from('<H', cp, offs[6] + 8 * i + 2)[0], 'R', 'data Museum music %d' % i, 'unlock')
    for i in range(h[10]):
        e = cp[offs[8] + 4 * i:offs[8] + 4 * i + 4]
        rec(struct.unpack('<H', e[:2])[0], 'R', 'data Jukebox character %d (owner %d)' % (i, e[2]), 'listed')
    v = get('collection_voice_param.bin')                            # Jukebox rows
    one, ng = struct.unpack_from('<HH', v, 0)
    o = 4 + 8 * ng
    for g in range(ng):
        owner, rows, nbytes, _m = struct.unpack_from('<HHHh', v, 4 + 8 * g)
        for r in range(rows):
            cat, fl = struct.unpack_from('<hh', v, o + 44 * r)
            rec(fl, 'R', 'data Jukebox voice group %d row %d' % (owner, r), 'category %d' % cat)
        o += nbytes
    m = get('general_archive/main/main.bin')
    ents = {n_: (o_, s_) for n_, o_, s_ in mpk.entries(m)}
    so, ss = ents['system.bin']
    _, chunks = arc_split(m[so:so + ss])
    ch = {c[1]: c[2] for c in chunks}
    u = ch[b'uicn']
    for i in range(struct.unpack_from('<H', u, 2)[0]):
        a, b = struct.unpack_from('<2H', u, 4 + 8 * i + 4)
        rec(a, 'R', 'data uicn icon %d' % i, 'unlock')
        rec(b, 'RW', 'data uicn icon %d' % i, 'viewed')
    ip = ch[b'infp']
    for i in range(struct.unpack_from('<H', ip, 2)[0]):
        kind_, a, b = struct.unpack_from('<3h', ip, 4 + 8 * i)
        rec(a, 'R', 'data infp row %d' % i, 'if-flag (kind %d)' % kind_)
        rec(b, 'W', 'data infp row %d' % i, 'set-flag (kind %d)' % kind_)
    tu = ch[b'tuto']
    for i in range(struct.unpack_from('<I', tu, 8)[0]):
        rec(struct.unpack_from('<h', tu, 16 + 16 * i + 6)[0], 'RW', 'data tuto row %d' % i, 'tutorial')
    bo, bs = ents['bgm_entry.bin']
    for i in range(struct.unpack_from('<I', m, bo + 8)[0]):
        for j, fl in enumerate(struct.unpack_from('<4h', m, bo + 16 + 44 * i + 4)):
            rec(fl, 'R', 'data bgm_entry row %d' % i, 'unlock slot %d' % j)
    d = get('party_battle-pbtl.bin')
    for i in range(struct.unpack_from('<h', d, 8)[0]):
        for j, fl in enumerate(struct.unpack_from('<4h', d, 0x14 + 200 * i + 2)):
            rec(fl, 'R' if j == 0 else 'RW', 'data pbtl row %d' % i, 'field %d' % j)


# ------------------------------------------------------------------ main
def ranges(nums):
    out, s = [], None
    for f in range(NFLAGS + 1):
        if f < NFLAGS and f in nums:
            if s is None:
                s = f
        elif s is not None:
            out.append([s, f - 1])
            s = None
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    iso = args[0] if args else os.path.join(ROOT, 'dumps/ULUS10566.iso')
    out = os.path.join(HERE, 'flag_map.json')
    if '--json' in sys.argv:
        out = sys.argv[sys.argv.index('--json') + 1]
    flags, report = {}, {}

    def rec(f, kind, site, what):
        if 0 <= f < NFLAGS:
            flags.setdefault(f, []).append({'kind': kind, 'site': site, 'what': what})

    imgs = Images(iso)
    dec = load_decomp()
    users = scan_code(dec, rec, report)
    byte_only = set()
    total, missing = coverage(imgs, dec, users, rec, byte_only)
    report['coverage'] = {'array_pointer_loads': total, 'outside_decompiled_users': missing}
    # byte findings the decompile scan did not also report
    report['bytes_only'] = sorted('%d %s %s 0x%08X' % (f, k, im, va) for f, k, im, va in byte_only
                                  if not any(e['site'].startswith('code ') and e['kind'] == k for e in flags.get(f, [])))
    scan_tables(imgs, rec)
    scan_data(iso, rec)

    # dedupe
    for f in flags:
        seen, uniq = set(), []
        for e in flags[f]:
            key = (e['kind'], e['site'], e['what'])
            if key not in seen:
                seen.add(key)
                uniq.append(e)
        flags[f] = uniq
    used = set(flags)
    free = [r for r in ranges(set(range(NFLAGS)) - used)]
    writers = sorted(f for f, es in flags.items() if any(e['kind'] in ('W', 'C', 'RW') and e['site'].startswith(('code', 'table')) for e in es))
    tests = [
        ('1250-1252 W by FUN_08a2b07c', all(any(e['kind'] == 'W' and 'FUN_08a2b07c' in e['site'] for e in flags.get(f, []))
                                           for f in (1250, 1251, 1252))),
        ('1253-1262 W by level table', all(any('0x08A2E8AC' in e['site'] for e in flags.get(f, [])) for f in range(1253, 1263))),
        ('1372 R by FUN_08a41098', any('FUN_08a41098' in e['site'] for e in flags.get(1372, []))),
        ('925 unlock row 22 (Chaos)', any('row 22 owner 23 unlock' == e['what'] for e in flags.get(925, []))),
        ('856-887 W by Catalog EV items', all(any(e['kind'] == 'W' and 'PP Catalog' in e['site'] for e in flags.get(f, []))
                                             for f in range(856, 888))),
        ('886 R by Jukebox rows', any('Jukebox voice' in e['site'] for e in flags.get(886, []))),
        ('1263-1270 unreferenced on clean', not (used & set(range(1263, 1271)))),
    ]
    doc = {'format': 'flag_map v1 (P2.6)', 'iso': os.path.basename(iso), 'flag_space': [0, NFLAGS - 1],
           'note': 'flags 0..4095 = block 1 (0x80 words), 4096..5119 = block 2 (0x20 words), both cleared by FUN_088b0788',
           'self_test': {t: ok for t, ok in tests}, 'coverage': report['coverage'], 'bytes_only': report['bytes_only'], 'helpers': report['helpers'],
           'table_driven_sites': report['table_driven_sites'],
           'unresolved_functions': report['unresolved_functions'],
           'used_count': len(used), 'code_writers': ranges(set(writers)),
           'free_ranges': free,
           'flags': {str(f): flags[f] for f in sorted(flags)}}
    with open(out, 'w') as fo:
        json.dump(doc, fo, indent=1)
    if '--quiet' not in sys.argv:
        print('%s: %d flags referenced, %d free ranges, %d array-pointer loads (%d outside decompiled users), '
              '%d table-driven code sites, %d helpers' % (out, len(used), len(free), total, len(missing),
                                                         len(report['table_driven_sites']), len(report['helpers'])))
        for t, ok in tests:
            print('  self-test %-34s %s' % (t, 'PASS' if ok else 'FAIL'))
    sys.exit(0 if all(ok for _, ok in tests) else 1)


if __name__ == '__main__':
    main()
