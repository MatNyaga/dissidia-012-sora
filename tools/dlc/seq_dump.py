"""Read-only dump of a menu SEQ layout (version 1), decoded from the game's own parser
(EBOOT FUN_088dc84c / FUN_088dc9dc sprites / FUN_088dcf18 groups / FUN_088dd21c anims / FUN_088dd608 keyframes).

  python3 -I seq_dump.py FILE.seq [ANIM]              a single SEQ blob
  python3 -I seq_dump.py PACK.bin --entry N [ANIM]    entry N of a "menu pak" seq pack (seq id = id_base + N)

Layout (all little endian):
  header 0x24: 'SEQ ', u32 version (1), u32 sprites, u32 groups, u32 ?, u32 anims, u32 ?, u32 ?, u32 ?
  sprites  : sprites x 0x20 (u16 u0,v0,u1,v1, f32 ?, f32 ?, 4 x RGBA vertex colour)
  groups   : groups x (u32 n, n x 12: s16 sprite, s16 ?, s16 x?, s16 ?, s16 y?, s16 flags)
  anims    : anims x (16-byte head: s16 tracks, s16 extra, s32, s16, s16, s32;
                      tracks x (s16 kind, s16 keys, keys x 100-byte keyframe);
                      extra x (u32 n, n x 8))
  keyframe : s16[0] start frame, s16[1..2] x,y at start, s16[0x14] end frame, s16[0x15..0x16] x,y at end,
             byte[16..19] RGBA start, byte[0x38..0x3b] RGBA end, f32 @0x18/0x1c scale start, f32 @0x40/0x44 end,
             s16[0x28] group/part index, s16[0x2e] flags.
A "locator" query FUN_088da0a8(sprite, p) reads track (tracks - p - 1) of the sprite's current anim.
Never writes anything.
"""
import struct
import sys


def parse(q):
    assert q[:4] == b'SEQ ', 'not a SEQ'
    ver, nspr, ngrp, h4, nanim, h6, h7, h8 = struct.unpack_from('<8I', q, 4)
    assert ver == 1, 'only version 1 decoded'
    o = 0x24
    sprites = [struct.unpack_from('<4H', q, o + 0x20 * i) for i in range(nspr)]
    o += 0x20 * nspr
    groups = []
    for _ in range(ngrp):
        n, = struct.unpack_from('<I', q, o); o += 4
        groups.append([struct.unpack_from('<6h', q, o + 12 * k) for k in range(n)])
        o += 12 * n
    anims = []
    for _ in range(nanim):
        ntr, nex, a4, a8, a10, a12 = struct.unpack_from('<hhihhi', q, o); o += 16
        tracks = []
        for _ in range(ntr):
            kind, nkey = struct.unpack_from('<hh', q, o); o += 4
            keys = []
            for _ in range(nkey):
                s = struct.unpack_from('<50h', q, o)
                keys.append({'start': s[0], 'xy': (s[1], s[2]), 'end': s[0x14], 'xy_end': (s[0x15], s[0x16]),
                             'part': s[0x28], 'flags': s[0x2e] & 0xffff,
                             'scale': struct.unpack_from('<2f', q, o + 0x18)})
                o += 100
            tracks.append((kind, keys))
        for _ in range(nex):
            n, = struct.unpack_from('<I', q, o); o += 4 + 8 * n
        anims.append({'head': (ntr, nex, a4, a8, a10, a12), 'tracks': tracks})
    return {'header': (ver, nspr, ngrp, h4, nanim, h6, h7, h8), 'sprites': sprites, 'groups': groups,
            'anims': anims, 'parsed_bytes': o, 'size': len(q)}


def pack_entry(data, n):
    assert data[:8] == b'menu pak'
    cnt, base = struct.unpack_from('<HH', data, 10)
    off, size = struct.unpack_from('<II', data, 16 + 8 * n)
    return data[off:off + size], base + n


def main():
    a = sys.argv[1:]
    data = open(a[0], 'rb').read()
    if '--entry' in a:
        i = a.index('--entry'); n = int(a[i + 1]); del a[i:i + 2]
        data, sid = pack_entry(data, n)
        print("seq id", sid)
    only = int(a[1]) if len(a) > 1 else None
    s = parse(data)
    print('header', s['header'], 'parsed %d of %d bytes' % (s['parsed_bytes'], s['size']))
    print('sprites (uv):', s['sprites'])
    for gi, g in enumerate(s['groups']):
        print('group', gi, g)
    for ai, an in enumerate(s['anims']):
        if only is not None and ai != only:
            continue
        print('anim', ai, 'head', an['head'])
        nt = len(an['tracks'])
        for ti, (kind, keys) in enumerate(an['tracks']):
            k0 = keys[0] if keys else {}
            print('  track %2d (locator p=%2d) kind %d keys %d first: frames %s-%s xy %s -> %s part %s flags %#x' % (
                ti, nt - ti - 1, kind, len(keys), k0.get('start'), k0.get('end'), k0.get('xy'), k0.get('xy_end'),
                k0.get('part'), k0.get('flags', 0)))


if __name__ == '__main__':
    main()
