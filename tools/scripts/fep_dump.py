"""Read-only dump of a fighter's effect package (objx chunk `effe` = MPK: .fep, .feb FEPA table, .fxseb) -- notes/kh2-effects.md.

  python3 -I fep_dump.py ISO [obj/p_sev120.objx]       summary: resources, every leaf effect, FEPA table
  python3 -I fep_dump.py FILE.objx|FILE.fep [FILE.feb]  same from a file (objx: effe chunk is found; package MPKs too)
  extra:  --leaf N [N...]   node detail of leaf effect(s) N (param-block colour/scale where the layout is known)
          --png OUTDIR      own textures (TEX) as PNG

FEP layout (version 1/3, "FEP\\xCD"; all offsets relative to the FEP; the game relocates them in place, flags +0x0c):
  +0x10 u32 id (top 14 bits global; must be unique per loaded FEP -- notes/effects-clash.md)
  +0x14 size   +0x18 u16 memory pool   +0x1c u16 nLeaf (+0x1e copy)
  +0x20 u16 nTEX  +0x22 u16 nMDL  +0x24 u16 nANM  +0x26 u16 n4
  +0x28 -> nLeaf x ptr: leaf index {u32 key = id|res<<10, u16 tree index, u16 nVariant, ptr variant bodies (0xa0 B)}
  +0x2c -> nLeaf x ptr: node tree {.., +4 duration, +0x10 nNodes<<16|nRoots, .., +0x1c ptr roots, +0x20 ptr nodes[] ..}
  +0x30/+0x34/+0x38/+0x3c -> ptr lists of 20-B resource records {f32 1, u32 key, 0, ptr data, handle -1}
        TEX / MDL / ANM / (unused).  key 0x98011cNN = own texture, 0x98011dNN own model, 0xF00000NN = GLOBAL
        texture from system resident.frr (shared by every fighter: never recolour those).
  +0x44 -> {n, ptr} name table n x {key, len, ptr "P0071_..._LEAF_0"}; FEPA +0x28 res = index here.
  TEX  "TEX\\0", key, 1, 0, fmt 4, 1, size, w, h, 0x30 | w*h 8-bit indices, PSP-swizzled (16 B x 8 rows) |
       16-B clut header (u16 256) | 256 x RGBA8888 palette.
  MDL  "MDL\\0", 1, 8, key, .., +0x1c texture key, .. PSP GE vertex stream (u8 uv, 4444 colour, s8 xyz + scale).
  node 0x48 B: u16 ?, u16 kind/flags, u16 MDL index, u16 node index, 20 B, 11 ptrs (tracks, param block, ...).
       kind 0x8e = 424-B param block: +0x40 pos, +0x50 rot(deg), +0x60 scale %, +0x70 RGBA (128 = 1.0).
FEPA (.feb): "FEPA", 0x20100205, size, count; 0x104-B rows (notes/hitbox-shapes.md section 5) +0x24 id (op 0x19 /
  0x66 use this), +0x28 res (leaf), +0x38 magi kind mask, +0x3c magi fx bit mask (magi row +0x04 = bit number),
  +0x44 trail variant mask, +0x70 attach, +0x74 start frame, +0x88 model, +0xa8 node, +0xc8 motion slot.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def floats(d, o, n):
    return struct.unpack_from('<%df' % n, d, o)


def mpk_members(data):
    from mpk import entries
    return {name: data[o:o + s] for name, o, s in entries(data)}


def load(args):
    """-> (fep bytes, feb bytes or None)"""
    path = args[0]
    if path.lower().endswith('.iso'):
        from comb_patch import pkg_offset, read_at, use_iso
        use_iso(path)
        rel = args[1] if len(args) > 1 and not args[1].startswith('--') else 'obj/p_sev120.objx'
        st, sz = pkg_offset(rel)
        with open(path, 'rb') as f:
            data = read_at(f, st, sz)
    else:
        data = open(path, 'rb').read()
    if data[:4] == b'FEP\xcd':
        feb = open(args[1], 'rb').read() if len(args) > 1 and not args[1].startswith('--') else None
        return data, feb
    if data[:4] != b'MPK ':                       # objx: find the effe chunk
        n = u32(data, 4)
        ch = [struct.unpack_from('<I4sII', data, 16 + k * 16) for k in range(n)]
        _, _, o, s = next(c for c in ch if c[1] == b'effe')
        data = data[o:o + s]
    mem = mpk_members(data)
    fep = next(v for k, v in mem.items() if k.endswith('.fep'))
    feb = next((v for k, v in mem.items() if k.endswith('.feb')), None)
    return fep, feb


def resources(d):
    out = {}
    for kind, cnt_at, tab_at in (('TEX', 0x20, 0x30), ('MDL', 0x22, 0x34), ('ANM', 0x24, 0x38), ('RES4', 0x26, 0x3c)):
        n = struct.unpack_from('<H', d, cnt_at)[0]
        lst = []
        for i in range(n):
            e = u32(d, u32(d, tab_at) + 4 * i)
            lst.append(dict(key=u32(d, e + 4), data=u32(d, e + 0xc)))
        out[kind] = lst
    return out


def tex_info(d, o):
    key, _, _, fmt, _, size, w, h, hdr = struct.unpack_from('<9I', d, o + 4)
    return dict(key=key, fmt=fmt, w=w, h=h, size=size)


def unswizzle(b, w, h):
    rb, out, i = w, bytearray(w * h), 0
    for by in range(h // 8):
        for bx in range(rb // 16):
            for r in range(8):
                o = (by * 8 + r) * rb + bx * 16
                out[o:o + 16] = b[i:i + 16]
                i += 16
    return bytes(out)


def tex_png(d, o, path):
    from PIL import Image
    t = tex_info(d, o)
    w, h = t['w'], t['h']
    px = unswizzle(d[o + 0x30:o + 0x30 + w * h], w, h)
    pal = d[o + 0x30 + w * h + 0x10:o + 0x30 + w * h + 0x410]
    im = Image.new('RGBA', (w, h))
    im.putdata([tuple(pal[4 * i:4 * i + 4]) for i in px])
    im.save(path)


def leaves(d, res):
    n = struct.unpack_from('<H', d, 0x1c)[0]
    cnt, p = struct.unpack_from('<II', d, u32(d, 0x44))
    names = []
    for i in range(cnt):
        k, ln, s = struct.unpack_from('<3I', d, p + 12 * i)
        names.append(d[s:s + ln].decode('latin1'))
    from fep import node_resources, node_texture_keys, resource_keys
    rk = resource_keys(d)
    out = []
    for i in range(n):
        key, tree, nvar, body = struct.unpack_from('<IHHI', d, u32(d, u32(d, 0x28) + 4 * i))
        t2 = struct.unpack_from('<13I', d, u32(d, u32(d, 0x2c) + 4 * tree))
        nodes = []
        for k in range(t2[4] >> 16):
            nd = u32(d, t2[8] + 4 * k)
            if not nd:
                continue
            a, kind, life, idx = struct.unpack_from('<4H', d, nd)     # +4 = life (frames), NOT an MDL index
            ptrs = struct.unpack_from('<11I', d, nd + 0x1c)
            # resources come from the node's components (fep.node_resources, 2026-10-14; before that this tool
            # wrongly read node +4 as an MDL index, so older leaf/texture lists in the notes were wrong)
            rr = node_resources(d, nd)
            mdl = next((i for k, i in rr if k == 'MDL'), -1)
            nodes.append(dict(at=nd, kind=kind, life=life, mdl=mdl, res=rr,
                              tex=sorted(node_texture_keys(d, nd, rk)) or None,
                              param=ptrs[1], param_size=ptrs[2] - ptrs[1]))
        out.append(dict(i=i, key=key, name=names[i] if i < len(names) else '?', dur=t2[1], nodes=nodes))
    return out


def texname(t):
    if t is None:
        return '-'
    if isinstance(t, (list, tuple, set)):
        return '+'.join(texname(x) for x in t) or '-'
    return ('G%x' % (t & 0xff)) if t >> 28 == 0xF else ('o%x' % (t & 0xff))


def fepa(feb):
    assert feb[:4] == b'FEPA'
    n = u32(feb, 12)
    rows = []
    for i in range(n):
        o = 16 + 0x104 * i
        s = lambda a: feb[o + a:o + a + 32].split(b'\0')[0].decode('latin1')
        rows.append(dict(i=i, id=u32(feb, o + 0x24), res=u32(feb, o + 0x28), mkind=u32(feb, o + 0x38),
                         mbits=u32(feb, o + 0x3c), var=u32(feb, o + 0x44), attach=u32(feb, o + 0x70),
                         frame=u32(feb, o + 0x74), flags=u32(feb, o + 0x7c), scale=floats(feb, o + 0x18, 1)[0],
                         model=s(0x88), node=s(0xa8), slot=s(0xc8)))
    return rows


def main(a):
    d, feb = load(a)
    assert d[:4] == b'FEP\xcd', 'not a FEP'
    res = resources(d)
    print('FEP id %#010x size %#x  TEX %d  MDL %d  ANM %d  leaves %d' % (
        u32(d, 0x10), u32(d, 0x14), len(res['TEX']), len(res['MDL']), len(res['ANM']), struct.unpack_from('<H', d, 0x1c)[0]))
    own = [t for t in res['TEX'] if t['key'] >> 28 != 0xF and d[t['data']:t['data'] + 4] == b'TEX\0']
    seen = set()
    for t in own:
        if t['key'] in seen:
            continue
        seen.add(t['key'])
        ti = tex_info(d, t['data'])
        print('  own TEX %08x %dx%d @%#x' % (t['key'], ti['w'], ti['h'], t['data']))
    print('  global TEX used: %s' % ' '.join(sorted({'%08x' % t['key'] for t in res['TEX'] if t['key'] >> 28 == 0xF})))
    L = leaves(d, res)
    print('\nleaf  res-key    dur  name / nodes (kind:texture, G = global system texture, o = own)')
    for lf in L:
        print(' %2d  %08x %4d  %s\n         %s' % (lf['i'], lf['key'], lf['dur'], lf['name'],
              ' '.join('%x:%s' % (n['kind'], texname(n['tex'])) for n in lf['nodes'])))
    if feb:
        print('\nFEPA id -> leaf (op 0x19 / 0x66 spawn by id; magi row +0x04 = bit number in mbits)')
        for r in fepa(feb):
            bits = [b for b in range(32) if r['mbits'] >> b & 1]
            print(' %2d id %4d -> %2d %-40s magi fx %-6s kind %-4x node %-15s slot %-6s fr %3d scale %.2f' % (
                r['i'], r['id'], r['res'], L[r['res']]['name'][6:-7] if r['res'] < len(L) else '?',
                ','.join(map(str, bits)) or '-', r['mkind'], r['node'], r['slot'], r['frame'], r['scale']))
    if '--leaf' in a:
        for x in a[a.index('--leaf') + 1:]:
            if not x.isdigit():
                break
            lf = L[int(x)]
            print('\n=== leaf %s %s (%d frames)' % (x, lf['name'], lf['dur']))
            for k, n in enumerate(lf['nodes']):
                line = '  node %2d @%#x kind %#x mdl %d tex %s param %d B' % (k, n['at'], n['kind'], n['mdl'],
                                                                             texname(n['tex']), n['param_size'])
                if n['param_size'] == 424:
                    p = n['param']
                    line += ' pos %s rot %s scale %s rgba %s (@%#x)' % (
                        floats(d, p + 0x40, 3), floats(d, p + 0x50, 3), floats(d, p + 0x60, 3),
                        floats(d, p + 0x70, 4), p + 0x70)
                print(line)
    if '--png' in a:
        out = a[a.index('--png') + 1]
        os.makedirs(out, exist_ok=True)
        for t in own:
            tex_png(d, t['data'], os.path.join(out, 'fep_%08x.png' % t['key']))
        print('PNGs ->', out)


if __name__ == '__main__':
    main(sys.argv[1:])
