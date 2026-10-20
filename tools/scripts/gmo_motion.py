"""List / swap animations (GMO "motion" blocks) in a Dissidia 012 fighter model.

Motion block (type 0x0B, header 0x18 + name): args 0x80B1 frame range (2 floats), 0x80B2 fps (float),
0x80B4 ?, 0x80B3 animate entries (u32 bone ref 0x1004xxxx, u32 channel 0x48 translate / 0x4B rotate /
0x4D scale, 4 bytes 0, u16 fcurve index (local to the motion), u16 0x0C), then fcurve blocks (type 0x0C):
header 0x1C incl. name, u32 format (0x80 = half floats; low bits interpolation: 0 constant, 4 = per-frame
quaternions), u32 dims, u32 key count, u32 0, then keys = (half frame, dims × half).
Battle entry of Cloud = motion ids 1100 → "_900A", 1110 → "_902A" (logged 2026-10-12); _910A/_911A = win poses?

Usage:
  python3 -I gmo_motion.py list FILE.gmo
  python3 -I gmo_motion.py copy IN.gmo OUT.gmo DST=SRC [DST=SRC ...]      (DST's data becomes SRC's; name kept)
  python3 -I gmo_motion.py take IN.gmo OUT.gmo OTHER.gmo DST=SRC [...]     (SRC from another GMO)
  python3 -I gmo_motion.py append IN.gmo OUT.gmo NEW=SRC [...]   (NEW slots after the last motion, copies of SRC;
        motion index = position → a new p_se type-8 block with that number is needed, spot33_chain.py SLOTS)
"""
import struct
import sys


def blocks(d, start, end):
    o = start
    while o < end:
        t, hs, size = struct.unpack_from('<HHI', d, o)
        yield o, t, hs, size
        o += size


def name(d, o, hs):
    return d[o + 16:o + hs].split(b'\0')[0].decode('latin1')


def motions(d):
    """-> list of (name, offset, size) and the offsets of the file + animation model blocks."""
    fo = 0x10
    _, fhs, fsize = struct.unpack_from('<HHI', d, fo)
    for mo, t, hs, size in blocks(d, fo + fhs, fo + fsize):
        if t == 3:
            out = [(name(d, o, h), o, s) for o, tt, h, s in blocks(d, mo + hs, mo + size) if tt == 0x0B]
            if out:
                return out, fo, mo
    raise ValueError('no motions found')


def replace(d, pairs, src_d=None):
    src_d = src_d or d
    src = {n: (o, s) for n, o, s in motions(src_d)[0]}
    for dst_name, src_name in pairs:
        mots, fo, mo = motions(d)
        dst = {n: (o, s) for n, o, s in mots}
        o, s = dst[dst_name]
        so, ss = src[src_name]
        _, hs, _ = struct.unpack_from('<HHI', d, o)
        _, shs, _ = struct.unpack_from('<HHI', src_d, so)
        new = bytearray(d[o:o + hs]) + src_d[so + shs:so + ss]      # keep DST's header (name), take SRC's body
        struct.pack_into('<I', new, 4, len(new))
        delta = len(new) - s
        d = d[:o] + bytes(new) + d[o + s:]
        for b in (fo, mo):                                          # parents grow / shrink
            struct.pack_into('<I', d := bytearray(d), b + 4, struct.unpack_from('<I', d, b + 4)[0] + delta)
        d = bytes(d)
        print('%s <- %s (%+d bytes)' % (dst_name, src_name, delta))
    return d


def append(d, pairs):
    """add motion blocks NEW (copy of SRC with NEW's name) right after the last motion; skip names that exist"""
    for new_name, src_name in pairs:
        mots, fo, mo = motions(d)
        have = {n: (o, s) for n, o, s in mots}
        if new_name in have:
            print('%s already there' % new_name)
            continue
        so, ss = have[src_name]
        _, shs, _ = struct.unpack_from('<HHI', d, so)
        head = bytearray(d[so:so + shs])
        nm = new_name.encode('latin1')
        assert len(nm) < shs - 16, 'name too long'
        head[16:shs] = nm.ljust(shs - 16, b'\0')
        blk = bytes(head) + d[so + shs:so + ss]
        lo, ls = mots[-1][1], mots[-1][2]
        at = lo + ls
        d = bytearray(d[:at] + blk + d[at:])
        for b in (fo, mo):
            struct.pack_into('<I', d, b + 4, struct.unpack_from('<I', d, b + 4)[0] + len(blk))
        d = bytes(d)
        print('%s = new motion %d (copy of %s, %d bytes)' % (new_name, len(mots), src_name, len(blk)))
    return d


def main():
    cmd = sys.argv[1]
    d = open(sys.argv[2], 'rb').read()
    if cmd == 'list':
        for i, (n, o, s) in enumerate(motions(d)[0]):
            r = d.find(struct.pack('<HHI', 0x80B1, 0, 16), o, o + 64)
            f0, f1 = struct.unpack_from('<ff', d, r + 8) if r > 0 else (0, 0)
            print('%2d %s  frames %g-%g  %d bytes' % (i, n, f0, f1, s))
    elif cmd == 'append':
        open(sys.argv[3], 'wb').write(append(d, [p.split('=') for p in sys.argv[4:]]))
    elif cmd in ('copy', 'take'):
        out = sys.argv[3]
        other = open(sys.argv[4], 'rb').read() if cmd == 'take' else None
        pairs = [p.split('=') for p in sys.argv[5 if cmd == 'take' else 4:]]
        open(out, 'wb').write(replace(d, pairs, other))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
