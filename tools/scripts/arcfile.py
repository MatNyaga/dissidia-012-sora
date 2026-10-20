"""Load a character ARC file (a PACKAGE.BIN entry) from a Dissidia 012 ISO, change chunks, write it back.

Chunks may only grow. Each grown chunk is padded so the growth is a multiple of 16, which keeps every
later chunk on its old alignment (textures/models need 16). The file is written in place, so it must
fit in the free bytes before the next file. PACKAGE_INFO.BIN inside the ISO gets the new size.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comb_add import free_room, iso_size_field  # noqa: E402
from comb_patch import SECTOR, pkg_offset, read_at  # noqa: E402


class ArcFile:
    def __init__(self, f, index):
        self.f, self.index = f, index
        self.base, orig_size = pkg_offset(index)
        self.span = orig_size + free_room(index)       # bytes up to the next file
        self.info_at = iso_size_field(f, index)
        self.size = struct.unpack('<I', read_at(f, self.info_at, 4))[0] & 0x0FFFFFFF   # current size in this ISO
        self.data = read_at(f, self.base, self.size)
        if self.data[:4] != b'ARC\x01':
            sys.exit('package entry %d is not an ARC' % index)
        count, = struct.unpack_from('<I', self.data, 4)
        self.chunks = [list(struct.unpack_from('<I4sII', self.data, 16 + i * 16)) for i in range(count)]
        self.new = {}

    def find(self, tag, ctype=None):
        for i, (t, g, _, _) in enumerate(self.chunks):
            if g == tag.encode() and (ctype is None or t == ctype):
                return i
        raise KeyError(tag)

    def get(self, i):
        if i in self.new:
            return bytearray(self.new[i])
        _, _, off, size = self.chunks[i]
        return bytearray(self.data[off:off + size])

    def put(self, i, chunk):
        if len(chunk) < self.chunks[i][3]:
            sys.exit('chunk %d would shrink, not supported' % i)
        self.new[i] = bytes(chunk)

    def save(self):
        order = sorted(range(len(self.chunks)), key=lambda i: self.chunks[i][2])
        out = bytearray()
        pos = 0
        new_chunks = [c[:] for c in self.chunks]
        for i in order:
            _, _, off, size = self.chunks[i]
            out += self.data[pos:off]                 # header or original gap, unchanged
            body = self.new.get(i, self.data[off:off + size])
            grow = len(body) - size
            new_chunks[i][2], new_chunks[i][3] = len(out), len(body)
            out += body + b'\0' * ((-grow) % 16 if grow else 0)
            pos = off + size
        out += self.data[pos:]
        for i, c in enumerate(new_chunks):
            struct.pack_into('<I4sII', out, 16 + i * 16, *c)
        if len(out) > self.span:
            sys.exit('pkg %d: file would be %d bytes, only %d fit' % (self.index, len(out), self.span))
        self.f.seek(self.base)
        self.f.write(out)
        sf, = struct.unpack('<I', read_at(self.f, self.info_at, 4))
        self.f.seek(self.info_at)
        self.f.write(struct.pack('<I', (sf & 0xF0000000) | len(out)))
        print('pkg %d: %d -> %d bytes (%d fit)' % (self.index, self.size, len(out), self.span))
