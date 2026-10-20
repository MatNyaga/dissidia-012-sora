"""Read a PSP GMO model ("OMG.00.1PSP") and print its structure: bones, parts/meshes, materials, textures.

Format (worked out from Cloud's P_SEV100_1P.gmo, 2026-10-12):
  16-byte file header, then chunks. Chunk = u16 type, u16 header size, u32 total size (incl. header).
  - Block chunks (type & 0x8000 == 0): header = 8 bytes + u32 + u32 + name (zero-padded); children follow the header.
      0x02 file, 0x03 model, 0x04 bone, 0x05 part, 0x06 mesh, 0x07 array (vertices), 0x08 material,
      0x09 layer, 0x0A texture, 0x0B motion, 0x0C fcurve ...
  - Argument chunks (type & 0x8000): 8-byte header + data. Seen on bones: 0x8041 parent ref, 0x8042 ?,
      0x8048 translate (3 floats), 0x804B rotate (quaternion, 4 floats).
  References are u32 (block type << 16) | 0x1000 | index.

Usage: python3 -I gmo.py FILE.gmo [--bones] [--tree]
"""
import struct
import sys

BLOCK = {0x02: 'file', 0x03: 'model', 0x04: 'bone', 0x05: 'part', 0x06: 'mesh', 0x07: 'array',
         0x08: 'material', 0x09: 'layer', 0x0A: 'texture', 0x0B: 'motion', 0x0C: 'fcurve', 0x0F: 'blind'}


def chunks(d, start, end):
    o = start
    while o + 8 <= end:
        t, hs, size = struct.unpack_from('<HHI', d, o)
        if size < 8 or o + size > end:
            return
        yield o, t, hs, size
        o += size


def name_of(d, o, hs):
    if hs <= 16:
        return ''
    return d[o + 16:o + hs].split(b'\0')[0].decode('latin1')


def walk(d, start, end, depth, out):
    for o, t, hs, size in chunks(d, start, end):
        if t & 0x8000:
            out.append((depth, o, t, hs, size, None))
        else:
            out.append((depth, o, t, hs, size, name_of(d, o, hs)))
            if t not in (0x07, 0x0A):            # arrays and textures hold raw data, not chunks
                walk(d, o + hs, o + size, depth + 1, out)


def main():
    path = sys.argv[1]
    d = open(path, 'rb').read()
    if d[:11] != b'OMG.00.1PSP':
        sys.exit('not a GMO')
    items = []
    walk(d, 16, len(d), 0, items)
    if '--tree' in sys.argv:
        for depth, o, t, hs, size, name in items:
            if name is None:
                print('  ' * depth + 'arg %04x (%d bytes) %s' % (t, size - 8, d[o + 8:o + min(size, 24)].hex(' ')))
            else:
                print('  ' * depth + '%s "%s" @0x%x (%d bytes)' % (BLOCK.get(t, hex(t)), name, o, size))
        return
    counts = {}
    for depth, o, t, hs, size, name in items:
        if name is not None:
            counts[BLOCK.get(t, hex(t))] = counts.get(BLOCK.get(t, hex(t)), 0) + 1
    print(path, len(d), 'bytes;', ', '.join('%s %d' % kv for kv in counts.items()))
    bones = [(o, t, hs, size, name) for depth, o, t, hs, size, name in items if t == 0x04 and name is not None]
    names = [b[4] for b in bones]
    if '--bones' in sys.argv:
        for i, (o, t, hs, size, name) in enumerate(bones):
            parent = '-'
            for ao, at, ahs, asz in chunks(d, o + hs, o + size):
                if at == 0x8041:
                    ref, = struct.unpack_from('<I', d, ao + 8)
                    parent = names[ref & 0xFFF] if (ref & 0xFFF) < len(names) else hex(ref)
            print('%3d %-24s parent %s' % (i, name, parent))
    tex = [name for depth, o, t, hs, size, name in items if t == 0x0A and name is not None]
    print('textures:', tex)
    print('materials:', len([1 for i in items if i[2] == 0x08 and i[5] is not None]),
          'parts:', [i[5] for i in items if i[2] == 0x05 and i[5] is not None][:20])



# ---- vertex arrays (PSP GE vertex format) ----
def ge_layout(vt):
    """Return (components, size): components = list of (name, offset, count, fmt)."""
    tc, col, nrm, pos = vt & 3, (vt >> 2) & 7, (vt >> 5) & 3, (vt >> 7) & 3
    wt, wcount = (vt >> 9) & 3, ((vt >> 14) & 7) + 1
    comps, off, align = [], 0, 1

    def add(name, n, size, fmt):
        nonlocal off, align
        off = (off + size - 1) // size * size
        comps.append((name, off, n, fmt))
        off += n * size
        align = max(align, size)
    if wt:
        add('weight', wcount, {1: 1, 2: 2, 3: 4}[wt], {1: 'B', 2: 'H', 3: 'f'}[wt])
    if tc:
        add('uv', 2, {1: 1, 2: 2, 3: 4}[tc], {1: 'B', 2: 'H', 3: 'f'}[tc])
    if col:
        add('color', 1, 4 if col == 7 else 2, 'I' if col == 7 else 'H')
    if nrm:
        add('normal', 3, {1: 1, 2: 2, 3: 4}[nrm], {1: 'b', 2: 'h', 3: 'f'}[nrm])
    if pos:
        add('pos', 3, {1: 1, 2: 2, 3: 4}[pos], {1: 'b', 2: 'h', 3: 'f'}[pos])
    size = (off + align - 1) // align * align
    return comps, size


def arrays(d, items):
    """Yield (name, vtype, vertices) for every array block; vertices = list of dicts."""
    for depth, o, t, hs, size, name in items:
        if t != 0x07 or name is None:
            continue
        vt, count, morphs, _ = struct.unpack_from('<IIII', d, o + hs)
        comps, vsize = ge_layout(vt)
        base, verts = o + hs + 16, []
        for k in range(count):
            v = {}
            for cname, off, n, fmt in comps:
                v[cname] = struct.unpack_from('<%d%s' % (n, fmt), d, base + k * vsize + off)
            verts.append(v)
        yield name, vt, verts


if __name__ == '__main__':
    main()
