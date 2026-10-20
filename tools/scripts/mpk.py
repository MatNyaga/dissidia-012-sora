"""List or extract Dissidia 012 MPK archives.

MPK layout (worked out 2026-10-11):
  0x00 char "MPK "   0x04 u32 0x20070606   0x08 u32 count   0x0C u32 0
  0x10 entries, 16 bytes: u32 name_offset, u32 data_offset, u32 size, u32 0
  names are NUL-terminated strings.

Usage: python3 -I mpk.py FILE [OUT_DIR]
"""
import os
import struct
import sys


def entries(data):
    if data[:4] != b'MPK ':
        raise ValueError('not an MPK')
    count, = struct.unpack_from('<I', data, 8)
    for i in range(count):
        noff, doff, size, _ = struct.unpack_from('<IIII', data, 16 + i * 16)
        name = data[noff:data.index(b'\0', noff)].decode('ascii', 'replace')
        yield name, doff, size


def replace(data, member, new):
    """rebuild the MPK with MEMBER's bytes replaced (same names and order, members 16-aligned)"""
    ents = list(entries(data))
    first = min(o for _, o, _ in ents)
    out = bytearray(data[:first])
    for i, (name, o, s) in enumerate(ents):
        blob = new if name == member else data[o:o + s]
        out += b'\0' * ((-len(out)) % 16)
        struct.pack_into('<II', out, 16 + i * 16 + 4, len(out), len(blob))
        out += blob
    out += b'\0' * ((-len(out)) % 16)
    return bytes(out)


if __name__ == '__main__':
    data = open(sys.argv[1], 'rb').read()
    out = sys.argv[2] if len(sys.argv) > 2 else None
    for name, doff, size in entries(data):
        print('%08x %8d %s' % (doff, size, name))
        if out:
            path = os.path.join(out, name)
            os.makedirs(os.path.dirname(path) or out, exist_ok=True)
            open(path, 'wb').write(data[doff:doff + size])
