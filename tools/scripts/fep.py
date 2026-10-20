"""Dissidia 012 effect package (.fep) parser + writer with relocatable offsets -- notes/kh2-effects.md "Stage B/C".

The FEP is a tree of structures linked by file-relative u32 offsets. The game turns them into pointers in place at
load (FUN_0894351c); that function is the complete list of offset fields, mirrored by walk() below:

  header +0x08 -> {u32 n, ptr}            (n x 8-B entries, no inner offsets)
         +0x44 -> {u32 n, ptr} names: n x {u32 key, u32 len, ptr str}
         +0x40 -> {u16 n, u16 ?, ptr} n x ptr -> {.., +8 ptr}       (only if 0 < off < 0x500000; 0 entries here)
         +0x30/34/38/3c (n at +0x20/22/24/26) -> n x ptr -> 20-B record {f32 1, key, 0, +0xc ptr data, handle}
                                                 TEX / MDL / ANM / (4th list, empty)
         +0x28 (n +0x1c) -> n x ptr leaf {key, u16 tree, u16 nvar, +8 ptr -> nvar x ptr variant (0xa0 B, +0xc ptr
                            if non-zero)}
         +0x2c (n +0x1e) -> n x ptr tree (52 B):
               +0x1c -> (u16 +0x10) x ptr -> {.., +4 ptr}            "roots"
               +0x20 -> (u16 +0x12) x ptr node (0 = none) (0x48 B), if node u8 +8 != 0:
                        +0x1c -> (u8 +8) x ptr -> {.., +8 ptr}       tracks
                        +0x20 -> {.., +8 ptr}  only if u8 +0x12 != 0 (else the game zeroes it)
                        +0x24 -> (u8 +0x13) x ptr -> {.., +8 ptr}
                        +0x28 .. +0x44: 8 plain ptrs (param blocks / data)
               +0x24 plain ptr
               +0x28 -> 12 x ptr -> {.., +4 ptr}
               +0x2c -> (u16 +0x18) x ptr -> {.., +4 ptr}
               +0x30 -> (u16 +0x1a) x plain ptr

Model used here: every offset target starts a *blob*; a blob runs to the next target (so it keeps its original
trailing padding). Offset fields are stored symbolically (blob, field position, target blob, delta). write() lays
the blobs out in order, aligns each to its alignment (data resources TEX/MDL/ANM: 16, else 4), and rewrites every
offset field + header size +0x14. With nothing changed the output is byte-identical. Edits: change blob.data
(e.g. grow a list), insert new blobs (insert_after), add pointer fields (add_ptr).

Library:
  f = Fep(bytes);  f.write() -> bytes;  f.resources('TEX') -> [(record blob, data blob)];  f.add_tex(data, key)
CLI (read-only):
  python3 -I fep.py FILE.fep|FILE.objx|ISO [obj/p_sev120.objx] [--map]
  ... --roundtrip [--grow [OUT.fep]]   byte round trip + 4-byte shift relocation test (+ add-one-TEX test)
"""
import bisect
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RES = (('TEX', 0x20, 0x30), ('MDL', 0x22, 0x34), ('ANM', 0x24, 0x38), ('RES4', 0x26, 0x3c))
DATA_ALIGN = 16


def u8(d, o):
    return d[o]


def u16(d, o):
    return struct.unpack_from('<H', d, o)[0]


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def walk(d):
    """-> list of (field offset, target offset, target kind) for every offset field the loader relocates"""
    out = []

    def p(field, kind):
        t = u32(d, field)
        out.append((field, t, kind))
        return t

    h8 = p(0x08, 'h8') if u32(d, 0x08) else None
    if h8 is not None:
        p(h8 + 4, 'h8_data')
    if u32(d, 0x44):
        nm = p(0x44, 'names')
        arr = p(nm + 4, 'names_arr')
        for i in range(u32(d, nm)):
            p(arr + 12 * i + 8, 'name_str')
    x40 = u32(d, 0x40)
    if x40 and x40 < 0x500000:
        p(0x40, 'x40')
        lst = p(x40 + 4, 'x40_list')
        for i in range(u16(d, x40)):
            it = p(lst + 4 * i, 'x40_item')
            p(it + 8, 'x40_data')
    for kind, cnt, tab in RES:
        if u32(d, tab):
            lst = p(tab, kind + '_list')
            for i in range(u16(d, cnt)):
                rec = p(lst + 4 * i, kind + '_rec')
                p(rec + 0xc, kind)
    lst = p(0x28, 'leaf_list')
    for i in range(u16(d, 0x1c)):
        lf = p(lst + 4 * i, 'leaf')
        vl = p(lf + 8, 'var_list')
        for k in range(u16(d, lf + 6)):
            v = p(vl + 4 * k, 'var')
            if u32(d, v + 0xc):
                p(v + 0xc, 'var_data')
    lst = p(0x2c, 'tree_list')
    for i in range(u16(d, 0x1e)):
        t = p(lst + 4 * i, 'tree')
        rl = p(t + 0x1c, 'root_list')
        for k in range(u16(d, t + 0x10)):
            r = p(rl + 4 * k, 'root')
            p(r + 4, 'root_data')
        nl = p(t + 0x20, 'node_list')
        for k in range(u16(d, t + 0x12)):
            if not u32(d, nl + 4 * k):
                continue
            n = p(nl + 4 * k, 'node')
            if not d[n + 8]:
                continue
            tl = p(n + 0x1c, 'track_list')
            for j in range(d[n + 8]):
                tr = p(tl + 4 * j, 'track')
                p(tr + 8, 'track_data')
            if d[n + 0x12]:
                y = p(n + 0x20, 'n20')
                p(y + 8, 'n20_data')
            l24 = p(n + 0x24, 'n24_list')
            for j in range(d[n + 0x13]):
                it = p(l24 + 4 * j, 'n24')
                p(it + 8, 'n24_data')
            for j in range(8):
                p(n + 0x28 + 4 * j, 'np%d' % j)
        p(t + 0x24, 't24')
        l28 = p(t + 0x28, 't28_list')
        for k in range(12):
            it = p(l28 + 4 * k, 't28')
            p(it + 4, 't28_data')
        l2c = p(t + 0x2c, 't2c_list')
        for k in range(u16(d, t + 0x18)):
            it = p(l2c + 4 * k, 't2c')
            p(it + 4, 't2c_data')
        l30 = p(t + 0x30, 't30_list')
        for k in range(u16(d, t + 0x1a)):
            p(l30 + 4 * k, 't30')
    return out


# Node components (tracks): node +0x1c -> u8 +8 x {u16 component id, u16 ?, u32 n, ptr}; node +0x20 -> {0, n, ptr
# init data}: init data starts with n x {u16 track index, u16 offset, u32 0}; the component's parameters sit at that
# offset. Resource references found by comparing all fighters' FEPs (index ranges vs list sizes, e.g. Emperor: ANM 36,
# TEX 25 -> comps 0x0a/0x15 reach 34/35):  0x0b / 0x14 = u16 MDL index, 0x0a / 0x15 = u16 ANM index,
# 0x6a (sword-trail ribbon) = u16 TEX index (unconfirmed). Every drawable node has exactly one of them.
COMP_RES = {0x0b: 'MDL', 0x14: 'MDL', 0x0a: 'ANM', 0x15: 'ANM', 0x6a: 'TEX'}


def node_components(d, nd):
    """-> [(component id, track u32 n, init-data offset or None)] of the node at file offset ND"""
    nt = d[nd + 8]
    if not nt:
        return []
    tl = u32(d, nd + 0x1c)
    offs = {}
    if d[nd + 0x12]:
        n20 = u32(d, nd + 0x20)
        p, cnt = u32(d, n20 + 8), u32(d, n20 + 4)
        offs = {u16(d, p + 8 * k): p + u16(d, p + 8 * k + 2) for k in range(cnt) if u16(d, p + 8 * k + 2)}
    out = []
    for j in range(nt):
        tr = u32(d, tl + 4 * j)
        out.append((u16(d, tr), u32(d, tr + 4), offs.get(j)))
    return out


def node_resources(d, nd):
    """-> [(kind 'MDL'/'ANM'/'TEX', index into that list)] referenced by the node at ND"""
    return [(COMP_RES[c], u16(d, o)) for c, _, o in node_components(d, nd) if c in COMP_RES and o is not None]


def resource_keys(d):
    """-> {'TEX': [keys], 'MDL': [keys], 'ANM': [keys], 'MDL_tex': [[tex/anm keys]], 'ANM_tex': [[tex keys]]}"""
    out = {}
    for kind, cnt, tab in RES[:3]:
        recs = [u32(d, u32(d, tab) + 4 * i) for i in range(u16(d, cnt))] if u32(d, tab) else []
        out[kind] = [u32(d, r + 4) for r in recs]
        datas = [u32(d, r + 0xc) for r in recs]
        if kind == 'MDL':
            out['MDL_tex'] = [[u32(d, x + u32(d, x + 0x10) + 0x18 * k) for k in range(u32(d, x + 0xc))]
                              if d[x:x + 4] == b'MDL\0' and u32(d, r + 8) else [] for x, r in zip(datas, recs)]
        if kind == 'ANM':
            out['ANM_tex'] = [[u32(d, x + u32(d, x + 0x30) + 8 * k) for k in range(u32(d, x + 0x20))]
                              if d[x:x + 4] == b'ANM\0' and u32(d, r + 8) else [] for x, r in zip(datas, recs)]
    return out


def node_texture_keys(d, nd, rk=None):
    """-> set of texture keys (TEX keys, ANMs resolved to their TEX) the node draws with"""
    rk = rk or resource_keys(d)
    keys = set()
    for kind, i in node_resources(d, nd):
        if kind == 'TEX' and i < len(rk['TEX']):
            keys.add(rk['TEX'][i])
        elif kind == 'MDL' and i < len(rk['MDL']):
            for k in rk['MDL_tex'][i]:
                keys.add(k)
        elif kind == 'ANM' and i < len(rk['ANM']):
            keys.update(rk['ANM_tex'][i] or [rk['ANM'][i]])
    for k in list(keys):                                  # an MDL may point at an animated texture (ANM key)
        if k in rk['ANM'] and rk['ANM_tex'][rk['ANM'].index(k)]:
            keys.discard(k)
            keys.update(rk['ANM_tex'][rk['ANM'].index(k)])
    return keys


class Blob:
    __slots__ = ('off', 'data', 'kinds', 'align', 'new_off')

    def __init__(self, off, data, align=4):
        self.off, self.data, self.kinds, self.align, self.new_off = off, bytearray(data), set(), align, None

    def __repr__(self):
        return '<blob @%#x %d B %s>' % (self.off if self.off is not None else -1, len(self.data),
                                         ','.join(sorted(self.kinds)))


class Fep:
    def __init__(self, d):
        assert d[:4] == b'FEP\xcd', 'not a FEP'
        assert u32(d, 0x0c) == 0, 'already relocated (runtime copy?)'
        d = bytes(d)
        fields = walk(d)
        starts = sorted({0} | {t for _, t, _ in fields})
        assert starts[-1] < len(d), 'offset past the end'
        self.blobs = []
        for i, s in enumerate(starts):
            e = starts[i + 1] if i + 1 < len(starts) else len(d)
            self.blobs.append(Blob(s, d[s:e]))
        by_off = {b.off: b for b in self.blobs}
        for _, t, kind in fields:
            b = by_off[t]
            b.kinds.add(kind)
            if kind in ('TEX', 'MDL', 'ANM', 'RES4'):
                b.align = DATA_ALIGN
        self.ptrs = []                   # [blob, pos in blob, target blob, delta]
        seen = set()
        for f, t, kind in fields:
            if f in seen:
                continue
            seen.add(f)
            i = bisect.bisect_right(starts, f) - 1
            self.ptrs.append([self.blobs[i], f - starts[i], by_off[t], 0])
        for b in self.blobs:              # alignment the original honours (keeps round trip exact)
            assert b.off % b.align == 0, b

    # ---- generic helpers
    def head(self):
        return self.blobs[0]

    def target(self, blob, pos):
        for p in self.ptrs:
            if p[0] is blob and p[1] == pos:
                return p[2]
        raise KeyError('no offset field at %r+%#x' % (blob, pos))

    def add_ptr(self, blob, pos, target, delta=0):
        self.ptrs.append([blob, pos, target, delta])

    def insert_after(self, anchor, new):
        self.blobs.insert(self.blobs.index(anchor) + 1, new)
        return new

    def resources(self, kind):
        """-> [(record blob, data blob)] for TEX / MDL / ANM"""
        _, cnt, tab = next(r for r in RES if r[0] == kind)
        h = self.head().data
        lst = self.target(self.head(), tab)
        out = []
        for i in range(u16(h, cnt)):
            rec = self.target(lst, 4 * i)
            out.append((rec, self.target(rec, 0xc)))
        return out

    # ---- edits
    def add_resource(self, kind, data, key):
        """append a new TEX/MDL/ANM: record (copy of the last one with KEY) + data blob; -> (record, data)"""
        _, cnt, tab = next(r for r in RES if r[0] == kind)
        h = self.head()
        lst = self.target(h, tab)
        items = self.resources(kind)
        n = len(items)
        assert len(lst.data) >= 4 * n
        lst.data[4 * n:4 * n] = b'\0\0\0\0'     # grow the pointer list (keeps the old trailing padding)
        last_rec, last_data = items[-1]
        rec = Blob(None, struct.pack('<fIIII', 1.0, key, len(data), 0, 0xFFFFFFFF))   # +8 = data size
        rec.kinds.add(kind + '_rec')
        self.insert_after(max((r for r, _ in items), key=self.blobs.index), rec)
        blob = Blob(None, bytes(data) + b'\0' * (-len(data) % DATA_ALIGN), DATA_ALIGN)
        blob.kinds.add(kind)
        self.insert_after(max((x for _, x in items), key=self.blobs.index), blob)
        self.add_ptr(lst, 4 * n, rec)
        self.add_ptr(rec, 0xc, blob)
        struct.pack_into('<H', h.data, cnt, n + 1)
        return rec, blob

    def add_tex(self, tex_bytes, key):
        t = bytearray(tex_bytes)
        assert t[:4] == b'TEX\0'
        struct.pack_into('<I', t, 4, key)
        return self.add_resource('TEX', t, key)

    # ---- resource keys
    def key_base(self):
        """own-resource key base derived from the FEP id (key = base | type << 8 | index; ANM = TEX space | 0x80):
        g = id >> 18 -> 0x80000000 | (g & 0x3f00) << 17 | (g & 0xff) << 10. Cloud 0x311C0000 -> 0x98011C00."""
        g = u32(self.head().data, 0x10) >> 18
        return 0x80000000 | (g & 0x3f00) << 17 | (g & 0xff) << 10

    def own_key_bases(self):
        return sorted({u32(r.data, 4) & 0xFFFFFC00 for k in ('TEX', 'MDL', 'ANM') for r, _ in self.resources(k)
                       if (u32(r.data, 4) >> 27 & 0xf) != 0xe})

    def rekey(self, new_base=None):
        """move every own TEX/MDL/ANM key (records +4, TEX +4, MDL +8 self + texture table (FUN_08971554), ANM +4
        self + texture table (FUN_089428f8)) from the copied FEP's base to NEW_BASE (default: the base of this FEP's
        id). -> number of u32 set"""
        new_base = self.key_base() if new_base is None else new_base
        olds = [b for b in self.own_key_bases() if b != new_base]
        assert len(olds) <= 1, 'several own key bases %s' % olds
        if not olds:
            return 0
        old, n = olds[0], 0

        def where(b, kind):
            if kind in ('TEX_rec', 'MDL_rec', 'ANM_rec', 'TEX'):
                return [4]
            if kind == 'MDL':       # self key +8; texture refs: u32 count +0xc, table +0x10, 0x18-B rows {key, handle}
                return [8] + [u32(b.data, 0x10) + 0x18 * k for k in range(u32(b.data, 0xc))]
            if kind == 'ANM':       # self key +4; texture refs: u32 count +0x20, table +0x30, 8-B rows {key, handle}
                return [4] + [u32(b.data, 0x30) + 8 * k for k in range(u32(b.data, 0x20))]
            return []
        for b in self.blobs:
            for kind in b.kinds:
                for pos in where(b, kind):
                    v = u32(b.data, pos)
                    if v & 0xFFFFFC00 == old:
                        struct.pack_into('<I', b.data, pos, new_base | (v & 0x3ff))
                        n += 1
        return n

    # ---- writer
    def write(self):
        out = bytearray()
        for b in self.blobs:
            out += b'\0' * (-len(out) % b.align)
            b.new_off = len(out)
            out += b.data
        for blob, pos, tgt, delta in self.ptrs:
            struct.pack_into('<I', out, blob.new_off + pos, tgt.new_off + delta)
        struct.pack_into('<I', out, 0x14, len(out))
        return bytes(out)


def load_fep(args):
    """FILE.fep | FILE.objx | ISO [package path] -> fep bytes (via fep_dump.load)"""
    from fep_dump import load
    return load(args)[0]


def semantic(d):
    """layout-independent view: for every offset field in walk order, (kind, bytes of the target blob with all
    offset fields zeroed and trailing zero padding stripped). Two FEPs with equal views are the same data."""
    fields = walk(d)
    starts = sorted({0} | {t for _, t, _ in fields})
    nxt = {s: (starts[i + 1] if i + 1 < len(starts) else len(d)) for i, s in enumerate(starts)}
    pf = {f for f, _, _ in fields}

    def body(t):
        b = bytearray(d[t:nxt[t]])
        for o in range(0, len(b) - 3, 4):
            if t + o in pf:
                b[o:o + 4] = b'\0\0\0\0'
        if t == 0:
            b[0x14:0x18] = b'\0\0\0\0'          # file size
        return bytes(b).rstrip(b'\0')
    return [('header', body(0))] + [(k, body(t)) for _, t, k in fields]


def same_semantics(a, b, extra=(), drop_kind_tail=None):
    """compare semantic(a) and semantic(b); EXTRA = kinds allowed to differ (the edit); DROP_KIND_TAIL = (kind, n):
    drop b's last field of KIND and the n-1 fields before it (= fields an add_* created). -> list of differences"""
    va, vb = semantic(a), semantic(b)
    if drop_kind_tail:
        kind, n = drop_kind_tail
        i = max(k for k, x in enumerate(vb) if x[0] == kind)
        del vb[i - n + 1:i + 1]
    diffs = []
    if len(va) != len(vb):
        diffs.append('field count %d vs %d' % (len(va), len(vb)))
    for i, (x, y) in enumerate(zip(va, vb)):
        if x != y and x[0] not in extra:
            diffs.append('field %d %s/%s differs' % (i, x[0], y[0]))
    return diffs


def check(d, label=''):
    """parse, write, compare bytes; then a relocation test: shift everything after the header table by 4 bytes,
    write, re-parse and compare semantically (proves every offset field is known and rewritten)"""
    f = Fep(d)
    w = f.write()
    same = w == bytes(d)
    print('%s: %d blobs, %d offset fields, %d B -> %d B, byte-identical: %s' % (
        label, len(f.blobs), len(f.ptrs), len(d), len(w), same))
    if not same:
        diff = [i for i in range(min(len(w), len(d))) if w[i] != d[i]]
        print('  first differences at', [hex(x) for x in diff[:10]])
    g = Fep(d)
    g.blobs[1].data += b'\0\0\0\0'               # h8 {n, ptr} + 4 spare bytes: every later offset moves
    s = g.write()
    moved = sum(1 for b in g.blobs if b.new_off != b.off)
    diffs = same_semantics(d, s)
    print('  shift test: %d of %d blobs moved, re-parse %s, semantic differences: %s' % (
        moved, len(g.blobs), 'ok' if Fep(s) else '?', diffs[:5] or 'none'))
    return same and not diffs


def grow_test(d, out=None):
    """add a copy of the first own TEX with the next free key, write, re-parse; -> new bytes"""
    f = Fep(d)
    tex = f.resources('TEX')
    own = [(r, b) for r, b in tex if u32(r.data, 4) >> 28 != 0xF]
    src = own[0][1]
    key = (u32(own[-1][0].data, 4) & ~0xff) | len(tex)
    size = u32(own[0][0].data, 8)
    f.add_tex(bytes(src.data[:size]), key)
    w = f.write()
    g = Fep(w)
    tex2 = g.resources('TEX')
    r, b = tex2[-1]
    ok = (len(tex2) == len(tex) + 1 and u32(r.data, 4) == key and u32(b.data, 4) == key
          and b.data[8:size] == src.data[8:size] and u32(w, 0x14) == len(w) and g.write() == w)
    diffs = same_semantics(d, w, extra={'TEX_list', 'header'}, drop_kind_tail=('TEX', 2))
    extra = len(semantic(w)) - len(semantic(d))
    print('grow test: +TEX %08x (copy of %08x, %d B): %d -> %d B, TEX %d -> %d, new data at %#x, re-parse ok: %s,'
          ' new fields %d, other differences: %s' % (key, u32(src.data, 4), size, len(d), len(w), len(tex),
                                                     len(tex2), b.new_off, ok, extra, diffs[:5] or 'none'))
    if out:
        open(out, 'wb').write(w)
    return w


def main(a):
    d = load_fep(a)
    if '--roundtrip' in a:
        ok = check(d, a[0])
        if '--grow' in a:
            grow_test(d, a[a.index('--grow') + 1] if len(a) > a.index('--grow') + 1 else None)
        sys.exit(0 if ok else 1)
    f = Fep(d)
    print('FEP %d B: %d blobs, %d offset fields' % (len(d), len(f.blobs), len(f.ptrs)))
    for k in ('TEX', 'MDL', 'ANM'):
        print('  %s %d' % (k, len(f.resources(k))))
    if '--map' in a:                     # runs of blob kinds in file order
        run, start = None, 0
        for b in f.blobs + [None]:
            k = ','.join(sorted(b.kinds)) if b else None
            if k != run:
                if run is not None:
                    print('  %#08x..%#08x  %s' % (start, b.off if b else len(d), run))
                run, start = k, b.off if b else 0


if __name__ == '__main__':
    main(sys.argv[1:])
