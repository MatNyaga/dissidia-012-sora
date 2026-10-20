"""List or split Dissidia 012 "ARC\\x01" table containers (battle.bin, system.bin, ...).

Layout (worked out 2026-10-11):
  0x00 char "ARC\\x01"   0x04 u32 count   0x08 u32 0   0x0C u32 0
  0x10 entries, 16 bytes: u32 1, char tag[4], u32 offset, u32 size

Usage: python3 -I arc.py FILE [OUT_DIR]
"""
import os
import struct
import sys


def chunks(data):
    if data[:4] != b'ARC\x01':
        raise ValueError('not an ARC')
    count, = struct.unpack_from('<I', data, 4)
    for i in range(count):
        one, tag, off, size = struct.unpack_from('<I4sII', data, 16 + i * 16)
        yield tag.decode('ascii', 'replace'), off, size


if __name__ == '__main__':
    data = open(sys.argv[1], 'rb').read()
    out = sys.argv[2] if len(sys.argv) > 2 else None
    for tag, off, size in chunks(data):
        print('%s %08x %7d  %s' % (tag, off, size, data[off:off + 16].hex(' ')))
        if out:
            os.makedirs(out, exist_ok=True)
            open(os.path.join(out, tag + '.bin'), 'wb').write(data[off:off + size])
