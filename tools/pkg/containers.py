"""Container codecs + row apply for fighter packages (P1.2 extractor, P1.3/P1.5 installers). Pure functions on bytes;
never opens an ISO. docs/PACKAGE-FORMAT.md §7 + the codec registry below (spec §14 "row sizes / codecs per table").

A rows/<table>.json row edits one NODE of a PACKAGE (or ISO) file, named by its ns:
  pkg:<path>                       the file itself
  pkg:<path>!<member>              MPK member (by name) | ARC chunk (by tag; a repeated tag = tag.N, N-th occurrence)
                                   | collection_param section (sec0..sec8)
  pkg:<path>#<g>                   mess pak group g (text group)
Every row key is {"at": X}. What X means depends on the node's codec:
  container  mpk  : X = member name   (add / replace / delete a whole member)
             arc  : X = chunk key     (replace a whole chunk)
             pak  : X = entry id      (menu pak picture etc.; add / replace / delete a whole entry)
             sections: X = section key
  leaf       grid : X = row index ("hdr" / "tail" = the bytes before / after the rows).
                    replace / patch / delete use the CLEAN row index, add uses the FINAL row index (apply: patches and
                    replaces, then deletes, then adds in ascending final index). Row-count fields named in the registry
                    are derived (rewritten from the row count), so they never appear in a row.
             bytes: X = byte offset in the CLEAN node; replace = old_raw -> raw (lengths may differ), add = insert raw,
                    delete = remove old_raw. Edits never overlap; applied from the highest offset down.
  any container node: X = "layout" (op replace) = layout pin: the exact non-member bytes of the reference container
                    (index table, gaps, filler, tail). Used only where the canonical re-encoder of that container kind
                    does not reproduce today's bytes (history-dependent filler / in-place writes). Guard: old_raw = the
                    skeleton of the CANONICAL re-encode of the new member list (so it also proves the members are the
                    expected ones); raw replaces it. Makes the container single-package in layout A.
Canonical re-encoders (no pin): mpk = header + entry table + names, members 16-aligned, end padded to 16
(tools/scripts/mpk.py / spot33_museum.mpk_add); arc = per ARC_RULES (pack4 = spot33_save.arc_join, grow16 =
arcfile.py); pak = header + table, first entry 16-aligned, entries 16-aligned, zero filler, zero-size entries offset 0,
end padded to 16; sections = 20 x u16 header (2, 9, counts, sizes) + sections back to back.
"""
import re
import struct

# ---------------------------------------------------------------- registry
# leaf codecs by ns regex (lower case). grid = (header bytes, row size, count field (offset, struct fmt) or None)
LEAVES = [
    (r'main\.bin!objentry\.bin$', ('grid', 8, 68, (4, '<I'))),
    (r'main\.bin!bgm_entry\.bin$', ('grid', 16, 44, (8, '<I'))),
    (r'main\.bin!manual_param\.bin$', ('bytes',)),
    (r'main\.bin!assist\.bin$', ('bytes',)),
    (r'system\.bin!chrp$', ('grid', 8, 144, (4, '<I'))),
    (r'system\.bin!ablt$', ('grid', 16, 40, (8, '<I'))),
    (r'system\.bin!item$', ('grid', 16, 104, (8, '<I'))),
    (r'system\.bin!eqpm$', ('grid', 8, 126, (4, '<I'))),
    (r'system\.bin!jobp$', ('grid', 8, 112, (4, '<I'))),
    (r'system\.bin!uicn$', ('grid', 4, 8, (2, '<H'))),
    (r'system\.bin!grwp$', ('grid', 8, 28, (4, '<I'))),       # Max CP growth: u32 3, u32 count, 0x1C rows (RC3, spot33_grwp)
    (r'system\.bin!(chrl|amas|acab|eqaa)$', ('bytes',)),
    (r'^pkg:battle_non_residing\.bin!brai\.0$', ('bytes',)),
    (r'^pkg:voice/[a-z]+/voice_load_p_[a-z0-9]+\.bin$', ('grid', 16, 24, (8, '<I'))),
    (r'^pkg:voice/[a-z]+/voice_load_parameter\.mpk!voice_load_p_[a-z0-9]+\.bin$', ('grid', 16, 24, (8, '<I'))),  # Museum VOLD copies
    (r'^pkg:collection_param\.bin!sec[0-8]$', ('grid-sec',)),
    (r'^pkg:collection_param\.bin!tail$', ('bytes',)),
    (r'^pkg:(command_list_param|update_list_param)\.bin$', ('bytes',)),
    (r'main_lang\.bin!(bgm_name|ability|item|item_help)\.bin$', ('bytes',)),
    (r'field_lang\.bin!battle_voice_name\.bin$', ('bytes',)),
    (r'#[0-9]+$', ('bytes',)),                       # mess pak text group
]
# containers that are descended by structure (path regex -> kind); others by magic
CONTAINERS = [(r'^pkg:collection_param\.bin$', 'sections')]
# ARC re-encode rule per ns (default grow16 = arcfile.py: grown chunks padded so growth is a multiple of 16)
ARC_RULES = [(r'main\.bin!system\.bin$', 'pack4')]
# MPK members / pak entries that are opaque (never descended; replaced whole): anything without a leaf codec


def leaf_codec(ns):
    low = ns.lower()
    for rx, spec in LEAVES:
        if re.search(rx, low):
            return spec
    return None


def kind_of(ns, data):
    low = ns.lower()
    for rx, k in CONTAINERS:
        if re.search(rx, low):
            return k
    if data[:4] == b'MPK ':
        return 'mpk'
    if data[:4] == b'ARC\x01':
        return 'arc'
    if data[:8] in (b'mess pak', b'menu pak'):
        return 'pak'
    spec = leaf_codec(ns)
    if spec:
        return spec[0]
    return None


def arc_rule(ns):
    for rx, r in ARC_RULES:
        if re.search(rx, ns.lower()):
            return r
    return 'grow16'


# ---------------------------------------------------------------- containers: split / join / skeleton
def _pad(n, a):
    return (-n) % a


def mpk_split(d):
    count, = struct.unpack_from('<I', d, 8)
    out = []
    for i in range(count):
        noff, doff, size, _ = struct.unpack_from('<IIII', d, 16 + 16 * i)
        name = d[noff:d.index(b'\0', noff)].decode('ascii')
        out.append((name, d[doff:doff + size]))
    return out


def mpk_index(d):
    count, = struct.unpack_from('<I', d, 8)
    return [struct.unpack_from('<II', d, 16 + 16 * i + 4) for i in range(count)], 16 + 16 * count


def mpk_join(clean, units):
    head = bytearray(clean[:16])
    struct.pack_into('<I', head, 8, len(units))
    table = bytearray(16 * len(units))
    names, noffs = bytearray(), []
    base = 16 + len(table)
    for n, _ in units:
        noffs.append(base + len(names))
        names += n.encode('ascii') + b'\0'
    out = head + table + names
    for i, (n, blob) in enumerate(units):
        out += b'\0' * _pad(len(out), 16)
        struct.pack_into('<IIII', out, 16 + 16 * i, noffs[i], len(out), len(blob), 0)
        out += blob
    out += b'\0' * _pad(len(out), 16)
    return bytes(out)


def arc_keys(d):
    count, = struct.unpack_from('<I', d, 4)
    tags = [struct.unpack_from('<4s', d, 16 + 16 * i + 4)[0].decode('latin-1') for i in range(count)]
    seen, keys = {}, []
    for t in tags:
        if tags.count(t) > 1:
            keys.append('%s.%d' % (t, seen.get(t, 0)))
            seen[t] = seen.get(t, 0) + 1
        else:
            keys.append(t)
    return keys


def arc_split(d):
    count, = struct.unpack_from('<I', d, 4)
    keys = arc_keys(d)
    out = []
    for i in range(count):
        _, _, o, z = struct.unpack_from('<I4sII', d, 16 + 16 * i)
        out.append((keys[i], d[o:o + z]))
    return out


def arc_index(d):
    count, = struct.unpack_from('<I', d, 4)
    return [struct.unpack_from('<II', d, 16 + 16 * i + 8) for i in range(count)], 16 + 16 * count


def arc_join(clean, units, rule):
    count, = struct.unpack_from('<I', clean, 4)
    ents = [list(struct.unpack_from('<I4sII', clean, 16 + 16 * i)) for i in range(count)]
    keys = arc_keys(clean)
    if [k for k, _ in units] != keys:
        raise ValueError('ARC chunk list changed (add/remove of chunks is not supported)')
    body = {k: b for k, b in units}
    if rule == 'pack4':
        out = bytearray(clean[:16 + 16 * count])
        pos = 16 + 16 * count
        for i in range(count):
            blob = body[keys[i]]
            pad = _pad(len(blob), 4) if i < count - 1 else 0
            struct.pack_into('<I4sII', out, 16 + 16 * i, ents[i][0], ents[i][1], pos, len(blob))
            out += blob + b'\0' * pad
            pos += len(blob) + pad
        return bytes(out)
    # grow16 (arcfile.py ArcFile.save): chunks in offset order, original gaps kept, a grown chunk is followed by
    # (-growth) % 16 zero bytes so later chunks keep their alignment
    order = sorted(range(count), key=lambda i: ents[i][2])
    out, pos = bytearray(), 0
    new = [e[:] for e in ents]
    for i in order:
        _, _, off, size = ents[i]
        out += clean[pos:off]
        blob = body[keys[i]]
        grow = len(blob) - size
        if grow < 0:
            raise ValueError('ARC chunk %s shrinks (grow16 cannot encode)' % keys[i])
        new[i][2], new[i][3] = len(out), len(blob)
        out += blob + b'\0' * (_pad(grow, 16) if grow else 0)
        pos = off + size
    out += clean[pos:]
    for i, e in enumerate(new):
        struct.pack_into('<I4sII', out, 16 + 16 * i, *e)
    return bytes(out)


def pak_split(d):
    cnt, base = struct.unpack_from('<HI', d, 10)
    out = []
    for i in range(cnt):
        o, z = struct.unpack_from('<II', d, 16 + 8 * i)
        out.append((base + i, d[o:o + z]))
    return out


def pak_index(d):
    cnt, = struct.unpack_from('<H', d, 10)
    return [struct.unpack_from('<II', d, 16 + 8 * i) for i in range(cnt)], 16 + 8 * cnt


def pak_join(clean, units):
    base, = struct.unpack_from('<I', clean, 12)
    ids = [k for k, _ in units]
    if ids != list(range(base, base + len(units))):
        raise ValueError('pak entry ids not contiguous from the base id')
    head = bytearray(clean[:16])
    struct.pack_into('<H', head, 10, len(units))
    out = head + bytearray(8 * len(units))
    for i, (_, blob) in enumerate(units):
        if not blob:
            continue
        out += b'\0' * _pad(len(out), 16)
        struct.pack_into('<II', out, 16 + 8 * i, len(out), len(blob))
        out += blob
    out += b'\0' * _pad(len(out), 16)
    return bytes(out)


SEC_HDR = 40


def sec_split(d):
    h = struct.unpack_from('<20H', d, 0)
    if h[0] != 2 or h[1] != 9:
        raise ValueError('collection_param header %r' % (h[:2],))
    out, pos = [], SEC_HDR
    for i in range(9):
        out.append(('sec%d' % i, d[pos:pos + h[11 + i]]))
        pos += h[11 + i]
    if pos > len(d):
        raise ValueError('collection_param sections end at %d, file %d' % (pos, len(d)))
    out.append(('tail', d[pos:]))                    # bytes after section 8 (kept as they are)
    return out


def sec_rowsize(clean, key):
    h = struct.unpack_from('<20H', clean, 0)
    i = int(key[3:])
    return h[11 + i] // h[2 + i] if h[2 + i] else None


def sec_join(clean, units):
    h = list(struct.unpack_from('<20H', clean, 0))
    for i, (k, blob) in enumerate(units):
        if k == 'tail':
            continue
        rs = sec_rowsize(clean, k)
        if rs is None or len(blob) % rs:
            raise ValueError('section %s: %d B is not a whole number of %s-B rows' % (k, len(blob), rs))
        h[2 + i], h[11 + i] = len(blob) // rs, len(blob)
    return struct.pack('<20H', *h) + b''.join(b for _, b in units)


SPLIT = {'mpk': mpk_split, 'arc': arc_split, 'pak': pak_split, 'sections': sec_split}
INDEX = {'mpk': mpk_index, 'arc': arc_index, 'pak': pak_index}


def join(kind, ns, clean, units):
    """canonical re-encode of a container from its (new) member list"""
    if kind == 'mpk':
        return mpk_join(clean, units)
    if kind == 'arc':
        return arc_join(clean, units, arc_rule(ns))
    if kind == 'pak':
        return pak_join(clean, units)
    if kind == 'sections':
        return sec_join(clean, units)
    raise ValueError(kind)


def skeleton(kind, data):
    """non-member bytes of a container in file order (index table, gaps, filler, tail)"""
    idx, hlen = INDEX[kind](data)
    cover = bytearray(len(data))
    cover[:hlen] = b'\0' * hlen
    for o, z in idx:
        if z:
            cover[o:o + z] = b'\1' * z
    return bytes(b for b, c in zip(data, cover) if not c)


def join_pinned(kind, skel, units):
    """container = skeleton (its index table names every member's offset/size) + member bytes at those offsets"""
    blobs = [b for _, b in units]
    if kind == 'mpk':
        n = len(blobs)
        hlen = 16 + 16 * n
        idx = [struct.unpack_from('<II', skel, 16 + 16 * i + 4) for i in range(n)]
    elif kind == 'arc':
        n = len(blobs)
        hlen = 16 + 16 * n
        idx = [struct.unpack_from('<II', skel, 16 + 16 * i + 8) for i in range(n)]
    elif kind == 'pak':
        n = len(blobs)
        hlen = 16 + 8 * n
        idx = [struct.unpack_from('<II', skel, 16 + 8 * i) for i in range(n)]
    else:
        raise ValueError('no layout pin for %s' % kind)
    cover = {}
    for (o, z), b in zip(idx, blobs):
        if z != len(b):
            raise ValueError('layout pin: member size %d != %d' % (len(b), z))
        for j in range(z):
            if cover.get(o + j, b[j]) != b[j]:
                raise ValueError('layout pin: overlapping members disagree')
        if z:
            cover.update(zip(range(o, o + z), b))
    total = len(skel) + len(cover)
    out = bytearray(total)
    s = 0
    for p in range(total):
        if p in cover:
            out[p] = cover[p]
        else:
            out[p] = skel[s]
            s += 1
    if s != len(skel) or bytes(out[:hlen]) != skel[:hlen]:
        raise ValueError('layout pin does not fit the members')
    return bytes(out)


# ---------------------------------------------------------------- leaves
def grid_parts(spec, data, rs=None):
    if spec[0] == 'grid-sec':
        hdr, row, cnt = 0, rs, None
    else:
        _, hdr, row, cnt = spec
    n = (len(data) - hdr) // row if cnt is None else struct.unpack_from(cnt[1], data, cnt[0])[0]
    rows = [data[hdr + i * row:hdr + (i + 1) * row] for i in range(n)]
    head = bytearray(data[:hdr])
    if cnt is not None:
        struct.pack_into(cnt[1], head, cnt[0], 0)          # derived field: never part of a header edit
    return bytes(head), rows, data[hdr + n * row:], row, cnt


def grid_join(spec, head, rows, tail, rs=None):
    h = bytearray(head)
    if spec[0] != 'grid-sec' and spec[3] is not None:
        struct.pack_into(spec[3][1], h, spec[3][0], len(rows))
    return bytes(h) + b''.join(rows) + tail


def apply_grid(spec, data, rows, rs=None):
    head, rws, tail, row, cnt = grid_parts(spec, data, rs)
    head = bytearray(head)
    keep = list(rws)
    dels, adds = set(), []
    for r in rows:
        at, op = r['key']['at'], r['op']
        if at == 'hdr' or at == 'tail':
            buf = head if at == 'hdr' else bytearray(tail)
            if op == 'patch':
                o, old, new = r['offset'], bytes.fromhex(r['old']), bytes.fromhex(r['new'])
                if bytes(buf[o:o + len(old)]) != old:
                    raise ValueError('%s %s: old bytes do not match' % (r['ns'], at))
                buf[o:o + len(old)] = new
            elif op == 'replace':
                if bytes(buf) != bytes.fromhex(r['old_raw']):
                    raise ValueError('%s %s: old_raw does not match' % (r['ns'], at))
                buf = bytearray(bytes.fromhex(r['raw']))
            else:
                raise ValueError('%s %s: op %s' % (r['ns'], at, op))
            if at == 'hdr':
                head = buf
            else:
                tail = bytes(buf)
            continue
        if op == 'add':
            adds.append((at, bytes.fromhex(r['raw'])))
            continue
        if not 0 <= at < len(keep):
            raise ValueError('%s row %s: no such clean row' % (r['ns'], at))
        cur = rws[at]
        if op == 'replace':
            if cur != bytes.fromhex(r['old_raw']):
                raise ValueError('%s row %d: old_raw does not match' % (r['ns'], at))
            keep[at] = bytes.fromhex(r['raw'])
        elif op == 'patch':
            o, old, new = r['offset'], bytes.fromhex(r['old']), bytes.fromhex(r['new'])
            if cur[o:o + len(old)] != old:
                raise ValueError('%s row %d: old bytes do not match' % (r['ns'], at))
            keep[at] = cur[:o] + new + cur[o + len(new):]
        elif op == 'delete':
            if cur != bytes.fromhex(r['old_raw']):
                raise ValueError('%s row %d: old_raw does not match' % (r['ns'], at))
            dels.add(at)
    out = [b for i, b in enumerate(keep) if i not in dels]
    for at, raw in sorted(adds, key=lambda x: x[0]):
        if at > len(out):
            raise ValueError('add at %d past the end (%d rows)' % (at, len(out)))
        out.insert(at, raw)
    for b in out:
        if len(b) != row:
            raise ValueError('row of %d B in a %d-B table' % (len(b), row))
    return grid_join(spec, bytes(head), out, tail, rs)


def apply_bytes(data, rows):
    eds = sorted(rows, key=lambda r: r['key']['at'], reverse=True)
    buf = bytearray(data)
    prev = None
    for r in eds:
        at, op = r['key']['at'], r['op']
        old = bytes.fromhex(r.get('old_raw', ''))
        if prev is not None and at + len(old) > prev:
            raise ValueError('%s: byte edits overlap at %d' % (r['ns'], at))
        if bytes(buf[at:at + len(old)]) != old:
            raise ValueError('%s @%d: old bytes do not match' % (r['ns'], at))
        new = bytes.fromhex(r['raw']) if op in ('add', 'replace') else b''
        if op not in ('add', 'replace', 'delete'):
            raise ValueError('%s: op %s in a bytes node' % (r['ns'], op))
        buf[at:at + len(old)] = new
        prev = at
    return bytes(buf)


# ---------------------------------------------------------------- apply a whole file
def node_children(kind, ns, data):
    """-> (units, {child ns: unit key}) for a container node"""
    units = SPLIT[kind](data)
    if kind == 'pak' and data[:8] == b'mess pak':
        return units, {'%s#%d' % (ns, k): k for k, _ in units}
    if kind == 'pak':
        return units, {}                              # menu pak entries are opaque pictures
    return units, {'%s!%s' % (ns, k): k for k, _ in units}


def apply_node(ns, data, by_ns, used):
    """apply every row whose ns is ns or below it; returns the new bytes. `used` collects the ns that were applied."""
    kind = kind_of(ns, data)
    own = by_ns.get(ns, [])
    below = [n for n in by_ns if n != ns and (n.startswith(ns + '!') or n.startswith(ns + '#'))]
    if kind in SPLIT:
        units, kids = node_children(kind, ns, data)
        units = [list(u) for u in units]
        pos = {k: i for i, (k, _) in enumerate(units)}
        inside = lambda n, c: n == c or n.startswith(c + '!') or n.startswith(c + '#')  # noqa: E731
        for n in below:
            if not any(inside(n, c) for c in kids):
                raise ValueError('rows for %s: no such member under %s' % (n, ns))
        for cns, k in kids.items():
            if any(inside(n, cns) for n in below):
                units[pos[k]][1] = apply_node(cns, units[pos[k]][1], by_ns, used)
        pin = None
        dels = set()
        adds = []
        for r in own:
            at, op = r['key']['at'], r['op']
            if at == 'layout':
                pin = (bytes.fromhex(r['old_raw']), bytes.fromhex(r['raw']))
                continue
            if op == 'add':
                if at in pos:
                    raise ValueError('%s: add %r but it exists' % (ns, at))
                adds.append((at, bytes.fromhex(r['raw'])))
                continue
            if at not in pos:
                raise ValueError('%s: no member %r' % (ns, at))
            cur = units[pos[at]][1]
            if op == 'replace':
                if cur != bytes.fromhex(r['old_raw']):
                    raise ValueError('%s %r: old_raw does not match' % (ns, at))
                units[pos[at]][1] = bytes.fromhex(r['raw'])
            elif op == 'delete':
                if cur != bytes.fromhex(r['old_raw']):
                    raise ValueError('%s %r: old_raw does not match' % (ns, at))
                dels.add(at)
            else:
                raise ValueError('%s: op %s on a container member' % (ns, op))
        units = [u for u in units if u[0] not in dels]
        if kind == 'pak':
            units += sorted(adds, key=lambda x: x[0])
            units.sort(key=lambda u: u[0])
        else:
            units += sorted(adds, key=lambda x: str(x[0]))   # appended in key order
        units = [tuple(u) for u in units]
        used.add(ns)
        canon = join(kind, ns, data, units)
        if pin is not None:
            if skeleton(kind, canon) != pin[0]:
                raise ValueError('%s: layout pin guard (canonical skeleton) does not match' % ns)
            return join_pinned(kind, pin[1], units)
        return canon
    if below:
        raise ValueError('%s is a leaf but rows name nodes below it' % ns)
    used.add(ns)
    if kind in ('grid', 'grid-sec'):
        spec = leaf_codec(ns)
        rs = None
        if spec[0] == 'grid-sec':
            raise ValueError('grid-sec needs its parent (use apply_section)')
        return apply_grid(spec, data, own)
    if kind == 'bytes':
        return apply_bytes(data, own)
    raise ValueError('%s: no codec for this node (kind %s)' % (ns, kind))


def apply_file(root_ns, data, rows):
    """rows: every row (dicts as in rows/*.json, any table) whose ns starts with root_ns. -> new file bytes"""
    by_ns = {}
    for r in rows:
        by_ns.setdefault(r['ns'], []).append(r)
    used = set()
    out = _apply(root_ns, data, by_ns, used)
    missing = set(by_ns) - used
    if missing:
        raise ValueError('rows never applied: %s' % sorted(missing))
    return out


def _apply(ns, data, by_ns, used):
    # collection_param sections need the parent's row sizes: handle the sections container here
    if kind_of(ns, data) == 'sections':
        units = [list(u) for u in sec_split(data)]
        for u in units:
            cns = '%s!%s' % (ns, u[0])
            if cns in by_ns:
                spec = leaf_codec(cns)
                u[1] = apply_grid(spec, u[1], by_ns[cns], rs=sec_rowsize(data, u[0]))
                used.add(cns)
        if ns in by_ns:
            raise ValueError('%s: rows on the sections container itself are not supported' % ns)
        used.add(ns)
        return sec_join(data, [tuple(u) for u in units])
    return apply_node(ns, data, by_ns, used)
