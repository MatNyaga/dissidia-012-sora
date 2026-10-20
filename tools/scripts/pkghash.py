"""Dissidia 012 PACKAGE name hash (EBOOT FUN_08871288): CRC-32/BZIP2 of the lowercased path."""
import struct
import sys


def pkg_hash(name):
    crc = 0xFFFFFFFF
    for c in name.lower().encode():
        crc ^= c << 24
        for _ in range(8):
            crc = ((crc << 1) ^ 0x04C11DB7) if crc & 0x80000000 else (crc << 1)
            crc &= 0xFFFFFFFF
    return crc ^ 0xFFFFFFFF


def load_hashes(info_path):
    info = open(info_path, 'rb').read()
    n, = struct.unpack_from('<I', info, 8)
    return {struct.unpack_from('<I', info, 16 + i * 12)[0]: i for i in range(n)}


if __name__ == '__main__':
    hashes = load_hashes(sys.argv[1])
    for name in sys.argv[2:]:
        h = pkg_hash(name)
        print('%08x %-6s %s' % (h, hashes.get(h, '-'), name))
