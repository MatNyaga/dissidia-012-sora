"""Scan unpacked PACKAGE files (and MPK members) for a character action table:
u16 ?, u16 count, u32 offsets[count] (relative to table start); entry starts with u16 action id.
A table "matches" if most entry ids are in the given action-id set.
Usage: python3 -I find_action_table.py PACKAGE_DIR id1,id2,...
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mpk import entries as mpk_entries  # noqa: E402


def scan(data, ids, label):
    need = [struct.pack('<H', i) for i in list(ids)[:3]]
    if not all(n in data for n in need):
        return
    n = len(data)
    for p in range(0, n - 8, 4):
        count, = struct.unpack_from('<H', data, p + 2)
        if not 8 <= count <= 400 or p + 4 + count * 4 > n:
            continue
        offs = struct.unpack_from('<%dI' % count, data, p + 4)
        if offs[0] < 4 + count * 4 or any(b <= a for a, b in zip(offs, offs[1:])) or p + offs[-1] + 2 > n:
            continue
        got = [struct.unpack_from('<H', data, p + o)[0] for o in offs]
        hit = sum(1 for g in got if g in ids)
        if hit >= max(5, len(ids) // 2):
            print('%s @0x%x count=%d hits=%d first ids=%s' % (label, p, count, hit, got[:12]))


def main():
    folder, ids = sys.argv[1], {int(x) for x in sys.argv[2].split(',')}
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        data = open(path, 'rb').read()
        if data[:4] == b'MPK ':
            for member, doff, size in mpk_entries(data):
                scan(data[doff:doff + size], ids, '%s/%s' % (name, member))
        else:
            scan(data, ids, name)


if __name__ == '__main__':
    main()
