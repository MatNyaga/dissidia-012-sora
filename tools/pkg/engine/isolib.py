"""Minimal ISO9660 helpers for the Phase-1 installers (from tools/dlc/p02_module_disc.py + p07_xidx_disc.py).

Only what the engine installer needs: find a directory, list its records, add / replace / remove ONE file record
in a directory whose size does not change, append file data at the ISO end, keep the PVD volume size in step,
walk the whole tree (extent list, for safe truncation on rollback). All reads take an open binary file object.
"""
import hashlib
import struct

SECTOR = 0x800
PVD_AT = 16 * SECTOR


def read_at(f, off, n):
    f.seek(off)
    return f.read(n)


def set_both32(buf, at, v):
    struct.pack_into('<I', buf, at, v)
    struct.pack_into('>I', buf, at + 4, v)


def rec_name(r):
    return bytes(r[33:33 + r[32]])


def rec_extent(r):
    return struct.unpack_from('<I', r, 2)[0], struct.unpack_from('<I', r, 10)[0]


def is_dir(r):
    return bool(r[25] & 2)


def read_dir(f, sector, size):
    raw = read_at(f, sector * SECTOR, size)
    recs = []
    for s in range(0, size, SECTOR):
        o = s
        while o < s + SECTOR and raw[o]:
            recs.append(bytes(raw[o:o + raw[o]]))
            o += raw[o]
        if any(raw[o:s + SECTOR]):
            raise ValueError('junk after the last record in directory sector %d' % (sector + s // SECTOR))
    return recs


def pack_dir(recs, size):
    out, cur = bytearray(), bytearray()
    for r in recs:
        if len(cur) + len(r) > SECTOR:
            out += cur + b'\0' * (SECTOR - len(cur))
            cur = bytearray()
        cur += r
    out += cur + b'\0' * (SECTOR - len(cur))
    return bytes(out) if len(out) <= size else None


def root_record(f):
    pvd = read_at(f, PVD_AT, SECTOR)
    if pvd[0] != 1 or pvd[1:6] != b'CD001':
        raise ValueError('no ISO9660 primary volume descriptor')
    return pvd[156:156 + 34]


def find_dir(f, path):
    rec = root_record(f)
    for part in path:
        sec, size = rec_extent(rec)
        rec = next((r for r in read_dir(f, sec, size) if rec_name(r) == part.encode() and is_dir(r)), None)
        if rec is None:
            raise ValueError('directory %s not found' % '/'.join(path))
    return rec_extent(rec)


def find_file(f, path, name):
    """(sector, size) of file NAME (bytes, e.g. b'EXTRA.PRX') in directory PATH, or None."""
    dsec, dsize = find_dir(f, path)
    r = next((r for r in read_dir(f, dsec, dsize) if rec_name(r) == name and not is_dir(r)), None)
    return rec_extent(r) if r else None


def walk_extents(f):
    """[(path, sector, size)] of every file and directory record in the tree."""
    out, seen = [], set()
    stack = [('', root_record(f))]
    while stack:
        path, rec = stack.pop()
        sec, size = rec_extent(rec)
        if sec in seen:
            continue
        seen.add(sec)
        out.append((path + '/', sec, size))
        for r in read_dir(f, sec, size)[2:]:
            p = path + '/' + rec_name(r).decode('latin-1')
            if is_dir(r):
                stack.append((p, r))
            else:
                out.append((p, *rec_extent(r)))
    return out


def iso_size(f):
    f.seek(0, 2)
    end = f.tell()
    vol, = struct.unpack_from('<I', read_at(f, PVD_AT + 80, 4))
    if vol * SECTOR != end:
        raise ValueError('PVD volume size %d sectors != ISO size %d bytes' % (vol, end))
    return end


def new_record(donor, name, sector, size):
    nl = len(name)
    head = 33 + nl + (33 + nl) % 2
    su = donor[33 + donor[32] + (33 + donor[32]) % 2:]
    r = bytearray(head + len(su))
    r[1:33] = donor[1:33]
    r[0], r[32] = len(r), nl
    set_both32(r, 2, sector)
    set_both32(r, 10, size)
    r[33:33 + nl] = name
    r[head:] = su
    return bytes(r)


def plan_put(f, path, name, data):
    """Plan add/replace of file NAME in directory PATH. Data goes in place when it fits the old sectors, else it is
    appended at the ISO end. Returns a dict for apply_put (action 'same' = nothing to do)."""
    dsec, dsize = find_dir(f, path)
    recs = read_dir(f, dsec, dsize)
    iso_end = iso_size(f)
    names = [rec_name(r) for r in recs]
    cur = next((r for r in recs if rec_name(r) == name), None)
    if cur is not None:
        if is_dir(cur):
            raise ValueError('%s is a directory' % name)
        s, z = rec_extent(cur)
        if z == len(data) and read_at(f, s * SECTOR, z) == data:
            return dict(action='same', name=name, pos=s * SECTOR)
        if -(-len(data) // SECTOR) <= -(-z // SECTOR):
            pos, end = s * SECTOR, iso_end
        else:
            pos = end = -(-iso_end // SECTOR) * SECTOR
        newrecs = [new_record(cur, name, pos // SECTOR, len(data)) if rec_name(r) == name else r for r in recs]
        action = 'replace'
    else:
        donor = next(r for r in recs[2:] if not is_dir(r))
        pos = end = -(-iso_end // SECTOR) * SECTOR
        r = new_record(donor, name, pos // SECTOR, len(data))
        i = next(i for i in range(2, len(recs) + 1) if i == len(recs) or names[i] > name)
        newrecs = recs[:i] + [r] + recs[i:]
        action = 'add'
    d = pack_dir(newrecs, dsize)
    if d is None:
        raise ValueError('directory %s full' % '/'.join(path))
    return dict(action=action, name=name, dsec=dsec, dir=d, pos=pos, iso_end=iso_end, end=end, data=data,
                new_end=max(iso_end, pos + -(-len(data) // SECTOR) * SECTOR))


def write_pvd_size(f, end):
    pv = bytearray(8)
    set_both32(pv, 0, end // SECTOR)
    f.seek(PVD_AT + 80)
    f.write(pv)


def apply_put(f, p):
    if p['action'] == 'same':
        return
    f.seek(p['iso_end'])
    f.write(b'\0' * (p['end'] - p['iso_end']))
    f.seek(p['pos'])
    f.write(p['data'] + b'\0' * ((-len(p['data'])) % SECTOR))
    f.seek(p['dsec'] * SECTOR)
    f.write(p['dir'])
    write_pvd_size(f, p['new_end'])


def plan_remove(f, path, name):
    """Plan removal of file record NAME from directory PATH (data sectors are left alone). None if absent."""
    dsec, dsize = find_dir(f, path)
    recs = read_dir(f, dsec, dsize)
    cur = next((r for r in recs if rec_name(r) == name and not is_dir(r)), None)
    if cur is None:
        return None
    d = pack_dir([r for r in recs if r is not cur], dsize)
    s, z = rec_extent(cur)
    return dict(name=name, dsec=dsec, dir=d, sector=s, size=z)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()
