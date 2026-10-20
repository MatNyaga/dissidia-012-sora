"""EXTRA.IDX v1 — build / parse / check (the same rules EXTRA.PRX applies at boot). Spec: docs/ENGINE.md.

    0x00 "XIDX"  0x04 u16 version = 1  0x06 u16 header size (>= 32, multiple of 4)
    0x08 u32 count N (0..16384)  0x0C u32 flags (bit 0 = override bitmap present; other bits must be 0)
    0x10 u32 PACKAGE.BIN ISO sector = 186624 (sanity)
    0x14 u32 sum = 32-bit sum of (hash ^ sector ^ size) over all rows + every u32 word of the override bitmap
    0x18 u32 override bitmap offset (flags bit 0; >= header + 12*N, 4-aligned; ceil(N/32) u32 words,
         bit i of word i>>5 = row i is an INTENDED override of a disc PACKAGE_INFO row; unused high bits 0)
    0x1C u32 names offset (tools only, 0 = none; the module never reads it): N NUL-terminated paths in row order
    header: rows[N] = u32 hash, u32 sector (PACKAGE.BIN-relative, < 2^20), u32 size (1..2^28-1, top 4 bits 0 =
         install flag 0 -> never served from a Data Install), strictly ascending by hash
"""
import struct

MAGIC = b'XIDX'
VERSION = 1
HDR = 32
PKG_ISO_SECTOR = 186624
MAX_ROWS = 16384
F_OVERRIDES = 1


def pkg_hash(name):
    """Game path hash (EBOOT FUN_08871288): CRC-32/BZIP2 of the lower-cased path (= tools/scripts/pkghash.py)."""
    crc = 0xFFFFFFFF
    for c in name.lower().encode():
        crc ^= c << 24
        for _ in range(8):
            crc = ((crc << 1) ^ 0x04C11DB7) if crc & 0x80000000 else (crc << 1)
            crc &= 0xFFFFFFFF
    return crc ^ 0xFFFFFFFF


def build(rows):
    """rows: iterable of dicts {hash, sector, size, override (bool), path (optional)}. Returns bytes."""
    rows = sorted(rows, key=lambda r: r['hash'])
    n = len(rows)
    if n > MAX_ROWS:
        raise ValueError('too many rows (%d > %d)' % (n, MAX_ROWS))
    for i, r in enumerate(rows):
        if i and r['hash'] == rows[i - 1]['hash']:
            raise ValueError('duplicate hash %08x (%s / %s)' % (r['hash'], rows[i - 1].get('path'), r.get('path')))
        if not 0 <= r['sector'] <= 0xFFFFF or not 0 < r['size'] < 1 << 28:
            raise ValueError('row %08x: sector/size out of range' % r['hash'])
    body = b''.join(struct.pack('<III', r['hash'], r['sector'], r['size']) for r in rows)
    s = sum(r['hash'] ^ r['sector'] ^ r['size'] for r in rows)
    flags, ovr_off, bm = 0, 0, b''
    if any(r.get('override') for r in rows):
        words = [0] * ((n + 31) // 32)
        for i, r in enumerate(rows):
            if r.get('override'):
                words[i >> 5] |= 1 << (i & 31)
        flags, ovr_off = F_OVERRIDES, HDR + len(body)
        bm = struct.pack('<%dI' % len(words), *words)
        s += sum(words)
    names = b''
    names_off = 0
    if rows and all(r.get('path') for r in rows):
        names_off = HDR + len(body) + len(bm)
        names = b''.join(r['path'].encode() + b'\0' for r in rows)
    head = MAGIC + struct.pack('<HHIIIIII', VERSION, HDR, n, flags, PKG_ISO_SECTOR, s & 0xFFFFFFFF, ovr_off, names_off)
    return head + body + bm + names


def parse(data):
    """Parse + check like the module. Returns dict(rows=[(hash, sector, size)], overrides=set(index),
    names=[str]|None). Raises ValueError(code, text) with the module's state code on failure."""
    def bad(code, text):
        raise ValueError(code, text)
    if len(data) < HDR:
        bad(-2, 'short header')
    magic = data[:4]
    ver, hdr, n, flags, pkg, s, ovr_off, names_off = struct.unpack_from('<HHIIIIII', data, 4)
    if magic != MAGIC or ver != VERSION or hdr < HDR or hdr & 3 or n > MAX_ROWS or pkg != PKG_ISO_SECTOR or \
            flags & ~F_OVERRIDES:
        bad(-2, 'bad header')
    words = []
    if flags & F_OVERRIDES:
        nw = (n + 31) // 32
        if not n or ovr_off & 3 or ovr_off < hdr + 12 * n:
            bad(-9, 'bad override bitmap offset')
        if len(data) < ovr_off + 4 * nw:
            bad(-4, 'short override bitmap')
        words = list(struct.unpack_from('<%dI' % nw, data, ovr_off))
        if n & 31 and words[-1] >> (n & 31):
            bad(-9, 'override bits set past the last row')
    if len(data) < hdr + 12 * n:
        bad(-4, 'short rows')
    rows = [struct.unpack_from('<III', data, hdr + 12 * i) for i in range(n)]
    total = sum(words)
    for i, (h, sec, size) in enumerate(rows):
        total += h ^ sec ^ size
        if (i and h <= rows[i - 1][0]) or sec > 0xFFFFF or size >> 28 or not size:
            bad(-5, 'row %d (%08x) not sorted / sector > 20 bits / flag != 0 / size 0' % (i, h))
    if total & 0xFFFFFFFF != s:
        bad(-6, 'checksum')
    ovr = {i for i in range(n) if words and words[i >> 5] >> (i & 31) & 1}
    names = None
    if names_off and names_off < len(data):
        parts = data[names_off:].split(b'\0')
        if len(parts) > n:
            names = [p.decode('latin-1') for p in parts[:n]]
    return dict(rows=rows, overrides=ovr, names=names, flags=flags)
