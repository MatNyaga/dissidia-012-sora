"""Read or patch a character's `atkp` (attack/hit) table directly inside a Dissidia 012 ISO.

atkp: u32 0xC, u32 count, then count x 68-byte entries:
  +0x00 u32 hit id (0x35D ...)   +0x04 u8 kind (0 Bravery hit, 1-3 HP/finish, 4+ other)
  +0x05 u8 reaction?             +0x10 u16 power (confirmed in game, test 8)
  +0x34 char[16] name (LAND_NEAR1, LAND_MIDDLE3, ...)
See notes/character-file.md. Sizes never change, so patches are written in place.

Usage:
  python3 -I atkp_patch.py ISO list PKG_INDEX      (PKG_INDEX may also be a path, e.g. obj/p_sev120.objx)
  python3 -I atkp_patch.py ISO set-power PKG_INDEX NAME VALUE      (writes!)
  python3 -I atkp_patch.py ISO copy-knockback PKG_INDEX FROM TO     (writes! copies +0x05 and +0x14..+0x34)
  python3 -I atkp_patch.py ISO set-float PKG_INDEX NAME OFFSET VALUE (writes! e.g. OFFSET 0x1c)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402

ENTRY = 68


def atkp_base(f, index):
    base, _ = pkg_offset(index)
    head = read_at(f, base, 16)
    if head[:4] != b'ARC\x01':
        sys.exit('package entry %d is not an ARC' % index)
    count, = struct.unpack_from('<I', head, 4)
    for i in range(count):
        _, tag, off, size = struct.unpack_from('<I4sII', read_at(f, base + 16 + i * 16, 16))
        if tag == b'atkp':
            return base + off
    sys.exit('no atkp chunk in entry %d' % index)


def entries(f, atkp):
    _, count = struct.unpack('<II', read_at(f, atkp, 8))
    for i in range(count):
        at = atkp + 8 + i * ENTRY
        e = read_at(f, at, ENTRY)
        yield at, struct.unpack_from('<I', e, 0)[0], e[0x34:0x44].split(b'\0')[0].decode('latin1'), e


def main():
    iso, cmd, index = sys.argv[1], sys.argv[2], sys.argv[3]       # index: number or path (obj/p_x.objx)
    use_iso(iso)
    with open(iso, 'rb' if cmd == 'list' else 'r+b') as f:
        atkp = atkp_base(f, index)
        if cmd == 'list':
            for at, hid, name, e in entries(f, atkp):
                power, = struct.unpack_from('<H', e, 0x10)
                print('id 0x%03x  %-18s kind %d  power %3d' % (hid, name, e[4], power))
        elif cmd == 'set-power':
            want, value = sys.argv[4], int(sys.argv[5], 0)
            for at, hid, name, e in entries(f, atkp):
                if name == want:
                    old, = struct.unpack_from('<H', e, 0x10)
                    f.seek(at + 0x10)
                    f.write(struct.pack('<H', value))
                    print('pkg %s %s power %d -> %d' % (index, name, old, value))
                    return
            sys.exit('no hit named %s' % want)
        elif cmd == 'set-float':
            want, off, value = sys.argv[4], int(sys.argv[5], 0), float(sys.argv[6])
            for at, hid, name, e in entries(f, atkp):
                if name == want:
                    old, = struct.unpack_from('<f', e, off)
                    f.seek(at + off)
                    f.write(struct.pack('<f', value))
                    print('pkg %s %s +0x%x %g -> %g' % (index, name, off, old, value))
                    return
            sys.exit('no hit named %s' % want)
        elif cmd == 'copy-knockback':
            hits = {name: (at, e) for at, _, name, e in entries(f, atkp)}
            (_, src), (dst_at, dst) = hits[sys.argv[4]], hits[sys.argv[5]]
            f.seek(dst_at + 0x05)
            f.write(src[0x05:0x06])
            f.seek(dst_at + 0x14)
            f.write(src[0x14:0x34])
            print('pkg %s %s knockback <- %s (reaction 0x%02x -> 0x%02x)' % (
                index, sys.argv[5], sys.argv[4], dst[5], src[5]))


if __name__ == '__main__':
    main()
