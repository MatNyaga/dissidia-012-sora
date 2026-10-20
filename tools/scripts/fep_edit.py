"""Edit #33's effect package (FEP inside obj/p_sev120.objx chunk `effe`) -- notes/kh2-effects.md "Stage B/C".

Copy-on-write like spot33_effects.py: reads the ISO (or an .objx), never writes an ISO. Without --out it is a dry run.

  python3 -I fep_edit.py ISO|FILE.objx [--file obj/p_sev120.objx] [ops...] [--out NEW.objx] [--png-dir DIR]

ops (applied in this order):
  --rekey                   own TEX/MDL/ANM keys -> the base of this FEP's id (Sora 0x98011cNN -> 0x980128NN).
                            NEEDED before any TEX/MDL/ANM edit: the texture/model managers reuse an already
                            registered key and ignore the new data (FUN_08941d40), and Sora's FEP is a copy of
                            Cloud's with Cloud's keys -> in Cloud vs Sora one fighter's textures show on both.
  --tex KEY --png FILE      replace own texture KEY (index or full key, e.g. 13 or 0x980128 13) with a PNG
  --tex KEY --kh2 PAX:D:T   ... with KH2 texture T of DPD D from a PAX BAR file (e.g. P_EX100.a.us:3:7):
                            PSMT8 CSM1 palette order -> linear, alpha x2 (0x80 = opaque) clamped to 255.
      --premultiply         RGB *= alpha, alpha = 255 (for additive materials that ignore alpha; most own textures
                            are opaque-alpha on black)
  --mdl-tex MDL=TEX         point model MDL (index) at texture TEX (index; +0x1c of the MDL data)

Texture size may change (e.g. 128x64 into a 128x128 slot): the FEP is rewritten with fep.py (relocatable), the MPK
and the objx are rebuilt around it. Same size -> only the texture bytes change.
After --out: pkg_put.py ISO obj/p_sev120.objx NEW.objx (a build step, not done here).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fep as F  # noqa: E402
import mpk  # noqa: E402

KH2_DEFAULT = 'kh2_export/raw/kh2_sixth/original/obj/P_EX100.a.us'


# ---------- texture conversion
def swizzle8(lin, w, h):
    """linear 8-bit indices -> PSP swizzled (16-byte x 8-row blocks, row-major over blocks); inverse of
    fep_dump.unswizzle"""
    out = bytearray()
    for by in range(h // 8):
        for bx in range(w // 16):
            for r in range(8):
                o = (by * 8 + r) * w + bx * 16
                out += lin[o:o + 16]
    return bytes(out)


def make_tex(key, w, h, idx, pal):
    """Dissidia TEX: 0x30 header | swizzled CLUT8 pixels | 16-B clut header | 256 x RGBA8888"""
    assert w % 16 == 0 and h % 8 == 0 and len(idx) == w * h and len(pal) == 1024
    hdr = struct.pack('<4s9I', b'TEX\0', key, 1, 0, 4, 1, 0x30 + w * h, w, h, 0x30) + b'\xcd' * 8
    clut = struct.pack('<HHI', 256, 0, 0) + b'\xcd' * 8
    return hdr + swizzle8(bytes(idx), w, h) + clut + bytes(pal)


def from_kh2(spec):
    """'FILE:DPD:TEX' -> (w, h, linear idx, RGBA palette) with linear palette order and alpha x2"""
    import kh2_pax_dump as K
    path, dpd, tex = spec.rsplit(':', 2)
    d = open(path, 'rb').read()
    pax = next(d[o:o + s] for t, _, _, o, s in K.bar(d) if t == 18)
    _, _, dpxoff = K.pax_elements(pax)
    _, dpds = K.dpx_parse(pax[dpxoff:])
    D = dpds[int(dpd)]
    info, pix, pal = K.texture(D, K.dpd_lists(D)[1][int(tex)])
    assert info['fmt'] == 0x13, 'only PSMT8 here (PSMT4 -> expand to 16 colours first)'
    # K.texture already maps each pixel through the CSM1 swap (bits 3 <-> 4), so `pix` indexes `pal` linearly
    p = bytearray(pal)
    for i in range(256):
        p[4 * i + 3] = min(255, p[4 * i + 3] * 2)
    return info['w'], info['h'], bytes(pix), bytes(p)


def from_png(path):
    from PIL import Image
    im = Image.open(path)
    if im.mode != 'P':
        rgba = im.convert('RGBA')
        px = list(rgba.getdata())
        cols = sorted(set(px))
        if len(cols) <= 256:                                  # exact: build the palette directly
            pos = {c: i for i, c in enumerate(cols)}
            pal = b''.join(bytes(c) for c in cols)
            return im.size[0], im.size[1], bytes(pos[c] for c in px), pal + b'\0' * (1024 - len(pal))
        im = rgba.quantize(256, method=2)                     # 2 = FASTOCTREE (keeps alpha)
    w, h = im.size
    pal = im.getpalette('RGBA') if 'A' in (im.palette.mode or '') else None
    if pal is None:
        rgb = im.getpalette() or []
        trn = im.info.get('transparency')
        pal = []
        for i in range(len(rgb) // 3):
            a = 255 if trn is None else (trn[i] if isinstance(trn, (bytes, bytearray)) and i < len(trn)
                                          else (0 if trn == i else 255))
            pal += rgb[3 * i:3 * i + 3] + [a]
    pal = bytes(pal[:1024]) + b'\0' * (1024 - min(1024, len(pal)))
    return w, h, im.tobytes(), pal


def premultiply(pal):
    p = bytearray(pal)
    for i in range(256):
        a = p[4 * i + 3]
        for c in range(3):
            p[4 * i + c] = p[4 * i + c] * a // 255
        p[4 * i + 3] = 255
    return bytes(p)


# ---------- objx plumbing
def load_objx(path, rel):
    if path.lower().endswith('.iso'):
        from comb_patch import pkg_offset, read_at, use_iso
        use_iso(path)
        st, sz = pkg_offset(rel)
        with open(path, 'rb') as f:
            return read_at(f, st, sz)
    return open(path, 'rb').read()


def arc_entries(d):
    n, = struct.unpack_from('<I', d, 4)
    return [list(struct.unpack_from('<I4sII', d, 16 + k * 16)) for k in range(n)]


def rebuild_arc(d, new_chunks):
    """same as spot33_combos.rebuild_arc: chunks re-laid in offset order, 16-aligned"""
    ents = arc_entries(d)
    order = sorted(range(len(ents)), key=lambda k: ents[k][2])
    out = bytearray(d[:ents[order[0]][2]])
    for k in order:
        body = new_chunks.get(k, d[ents[k][2]:ents[k][2] + ents[k][3]])
        out += b'\0' * ((-len(out)) % 16)
        ents[k][2], ents[k][3] = len(out), len(body)
        out += body
    out += b'\0' * ((-len(out)) % 16)
    for k, e in enumerate(ents):
        struct.pack_into('<I4sII', out, 16 + k * 16, *e)
    return bytes(out)


def split(objx):
    """-> (effe chunk index, effe bytes, fep member name, fep bytes)"""
    ents = arc_entries(objx)
    ei = next(k for k, e in enumerate(ents) if e[1] == b'effe')
    effe = objx[ents[ei][2]:ents[ei][2] + ents[ei][3]]
    name, o, s = next(iter(mpk.entries(effe)))            # member 0 = .fep (members are used by index)
    return ei, effe, name, effe[o:o + s]


def join(objx, ei, effe, name, fep_bytes):
    old = split(objx)[3]
    if len(fep_bytes) == len(old):                          # same size: patch in place, nothing moves
        out = bytearray(objx)
        o = arc_entries(objx)[ei][2] + next(iter(mpk.entries(effe)))[1]
        out[o:o + len(fep_bytes)] = fep_bytes
        return bytes(out)
    return rebuild_arc(objx, {ei: mpk.replace(effe, name, fep_bytes)})


# ---------- edits
def res_index(f, kind, spec):
    """index or key -> index in the TEX/MDL list"""
    v = int(spec, 0)
    items = f.resources(kind)
    if v < len(items):
        return v
    keys = [F.u32(r.data, 4) for r, _ in items]
    if v in keys:
        return keys.index(v)
    low = [k & 0x3ff for k in keys]
    return low.index(v & 0x3ff)


def replace_tex(f, spec, w, h, idx, pal):
    i = res_index(f, 'TEX', spec)
    rec, blob = f.resources('TEX')[i]
    key = F.u32(rec.data, 4)
    assert (key >> 27 & 0xf) != 0xe, 'global texture %08x: shared by every fighter, never edit' % key
    old = F.u32(rec.data, 8)
    shared = [F.u32(r.data, 4) for r, b in f.resources('TEX') if b is blob and r is not rec and F.u32(r.data, 8)]
    assert not shared, 'data shared with own keys %s' % shared
    t = make_tex(key, w, h, idx, pal)
    blob.data[:] = t + b'\0' * (-len(t) % F.DATA_ALIGN) if len(t) != old else t + blob.data[old:]
    struct.pack_into('<I', rec.data, 8, len(t))
    print('  TEX %d %08x: %d B -> %d B (%dx%d)' % (i, key, old, len(t), w, h))
    return key


GENERIC_IDS = {0, 1, 2, 3, 4, 5}     # DOGE_* rows: every fighter's FEPA starts with them; the engine spawns ids 0/1/
#                                     param by constant (FUN_08b4677c id 0, FUN_08ab7044 id 1, FUN_08ab6f98 param)
# constant ids < 79 found in character-specific EBOOT code (FUN_08a2d41c .. FUN_08a4f454, names don't fit Cloud):
MAYBE_HARDCODED = {0x29, 0x2d, 0x2e, 0x2f, 0x30, 0x33, 0x34, 0x37, 0x3c, 0x3d, 0x4e}


def script_usage(objx):
    """-> dict of effect references in the objx scripts (p_se type 8) and magi rows"""
    ents = arc_entries(objx)
    t8 = next(objx[e[2]:e[2] + e[3]] for e in ents if e[0] == 8 and e[1] == b'p_se')
    mg = next(objx[e[2]:e[2] + e[3]] for e in ents if e[1] == b'magi')
    use = dict(ids={}, trails={}, magi_script=set())
    m, = struct.unpack_from('<I', t8, 4)
    for b in range(m):
        o, = struct.unpack_from('<I', t8, 8 + 4 * b)
        blk, nmain, nones = t8[o], t8[o + 2], t8[o + 3]
        e1, = struct.unpack_from('<H', t8, o + 4)
        k = o + 8
        for _ in range(nmain):
            op, n = t8[k + 4], t8[k + 5]
            p = struct.unpack_from('<%dI' % n, t8, k + 12)
            if op == 0x66 and n:
                use['ids'].setdefault(p[0], set()).add('blk%d main66' % blk)
            if op == 0x2a and n > 1:
                use['trails'].setdefault(p[1], set()).add((blk, t8[k + 6], t8[k + 7], t8[k + 8]))
            if op == 0x43 and n > 2 and p[2] not in (0xFFFFFFFF,):
                use['magi_script'].add(p[2] & 0xFFFF)
            k += 12 + 4 * n
        k = o + e1
        for _ in range(nones):
            op, n = t8[k + 2], t8[k + 3]
            p = struct.unpack_from('<%dI' % n, t8, k + 8)
            fr, = struct.unpack_from('<H', t8, k)
            if op in (0x19, 0x30) and n:
                use['ids'].setdefault(p[0], set()).add('blk%d f%d os%x' % (blk, fr, op))
            if op == 0x2f and n > 2:
                for x in (p[0], p[2]):
                    use['ids'].setdefault(x, set()).add('blk%d f%d os2f' % (blk, fr))
            if op == 4 and n:
                use['magi_script'].add(p[0] & 0xFFFF)
            k += 8 + 4 * n
    cnt, = struct.unpack_from('<I', mg, 8)
    rows = {struct.unpack_from('<h', mg, 16 + 204 * i)[0] & 0xFFFF: mg[16 + 204 * i:16 + 204 * (i + 1)]
            for i in range(cnt)}
    reach, todo = set(), [x for x in use['magi_script'] if x in rows]
    while todo:                                           # children at +0x0E..+0x1C
        x = todo.pop()
        if x in reach:
            continue
        reach.add(x)
        for off in range(0x0E, 0x1E, 2):
            c, = struct.unpack_from('<H', rows[x], off)
            if c != 0xFFFF and c in rows:
                todo.append(c)
    use['magi_rows'], use['magi_reach'] = rows, reach
    use['fx_bits'] = {}
    for x in rows:
        r = rows[x]
        bit, = struct.unpack_from('<H', r, 4)
        if bit < 32:
            use['fx_bits'].setdefault(bit, set()).add(x)
        if r[0x1e] == 6:                                   # Fire-type ball starts at a live effect of id +0x20
            fid, = struct.unpack_from('<H', r, 0x20)
            use['ids'].setdefault(fid, set()).add('magi %x +0x20' % x)
    return use


def usage_report(objx, fep_bytes):
    """which FEPA rows / leaves / MDL / TEX / ANM the fighter can still reach -> printed report + free sets"""
    from fep_dump import fepa, leaves, resources
    feb = mpk_member(objx, 1)
    rows = fepa(feb)
    res = resources(fep_bytes)
    L = leaves(fep_bytes, res)
    u = script_usage(objx)
    used, why = set(), {}

    def mark(r, reason):
        used.add(r['i'])
        why.setdefault(r['i'], []).append(reason)
    trail_ids = set(u['trails'])
    for r in rows:
        if r['id'] in u['ids']:
            mark(r, 'id %d: %s' % (r['id'], ', '.join(sorted(u['ids'][r['id']]))[:60]))
        if r['id'] in GENERIC_IDS:
            mark(r, 'engine generic id')
        if r['id'] in trail_ids:
            mark(r, 'trail op 0x2a')
        bits = [b for b in range(32) if r['mbits'] >> b & 1]
        hit = [b for b in bits if b in u['fx_bits'] and (u['fx_bits'][b] & u['magi_reach'])]
        if hit:
            mark(r, 'magi fx bit %s (script-reachable magi %s)' % (hit, ','.join(
                '%x' % x for b in hit for x in sorted(u['fx_bits'][b] & u['magi_reach']))))
        elif [b for b in bits if b in u['fx_bits']]:
            why.setdefault(r['i'], []).append('magi fx bit of unreached magi rows only')
        if r['model'] and r['slot'] and not (r['flags'] & 0x80):
            why.setdefault(r['i'], []).append('slot-bound %s f%d (only if FUN_088aa844 name check matches)' % (
                r['slot'], r['frame']))
        if r['id'] in MAYBE_HARDCODED:
            why.setdefault(r['i'], []).append('id in char-specific EBOOT code (probably not Cloud)')
    print('\nscript effect ids: %s' % ' '.join(str(x) for x in sorted(u['ids'])))
    print('trail ids (op 0x2a): %s' % ' '.join(str(x) for x in sorted(u['trails'])))
    print('magi spawned by scripts: %s; reachable with children: %s' % (
        ' '.join('%x' % x for x in sorted(u['magi_script'])), ' '.join('%x' % x for x in sorted(u['magi_reach']))))
    print('\nFEPA row -> leaf, use')
    for r in rows:
        print(' %2d id %4d -> %2d %-32s %s %s' % (r['i'], r['id'], r['res'],
                                                 L[r['res']]['name'].replace('P0071_', '').replace('P_SEV100_', '')[:-7],
                                                 'USED' if r['i'] in used else '    ', '; '.join(why.get(r['i'], []))))
    used_leaf = {rows[i]['res'] for i in used}
    cond_leaf = {r['res'] for r in rows if r['i'] not in used and r['i'] in why}
    free_leaf = [lf['i'] for lf in L if lf['i'] not in used_leaf and lf['i'] not in cond_leaf]
    rk = F.resource_keys(fep_bytes)

    def deps(leaf_ids):
        """-> (MDL indexes, ANM indexes, TEX indexes (trails), own texture/ANM keys) drawn by these leaves"""
        got = {'MDL': set(), 'ANM': set(), 'TEX': set()}
        keys = set()
        for i in leaf_ids:
            for n in L[i]['nodes']:
                for k, x in F.node_resources(fep_bytes, n['at']):
                    got[k].add(x)
                keys |= F.node_texture_keys(fep_bytes, n['at'], rk)
                keys |= {rk['ANM'][x] for k, x in F.node_resources(fep_bytes, n['at']) if k == 'ANM'}
                keys |= {kk for k, x in F.node_resources(fep_bytes, n['at']) if k == 'MDL' for kk in rk['MDL_tex'][x]}
        return got, keys
    own = lambda k: k and (k >> 27 & 0xf) != 0xe
    (ug, uk), (fg, fk) = deps(used_leaf | cond_leaf), deps(free_leaf)
    nm = lambda i: L[i]['name'].replace('P0071_', '').replace('P_SEV100_', '')[:-7]
    print('\nleaves used: %s' % ' '.join('%d %s' % (i, nm(i)) for i in sorted(used_leaf)))
    print('leaves conditional (slot-bound / unreached magi / maybe hard-coded): %s' % ' '.join(
        '%d %s' % (i, nm(i)) for i in sorted(cond_leaf)))
    print('leaves FREE (no reference found): %s' % ' '.join('%d %s' % (i, nm(i)) for i in free_leaf))
    for k in ('MDL', 'ANM', 'TEX'):
        n = len(rk[k])
        print('%s (%d): only free leaves %s | used by nobody %s' % (
            k, n, sorted(fg[k] - ug[k]), sorted(set(range(n)) - ug[k] - fg[k])))
    allk = set(x for x in rk['TEX'] + rk['ANM'] if own(x))
    print('own TEX/ANM keys drawn by used/conditional leaves: %s' % ' '.join('%08x' % k for k in sorted(uk) if own(k)))
    print('own TEX/ANM keys drawn only by free leaves: %s' % ' '.join('%08x' % k for k in sorted(fk - uk) if own(k)))
    print('own TEX/ANM keys drawn by no leaf: %s' % ' '.join('%08x' % k for k in sorted(allk - uk - fk)))
    return used_leaf, cond_leaf, free_leaf


def mpk_member(objx, i):
    ei, effe, _, _ = split(objx)
    name, o, s = list(mpk.entries(effe))[i]
    return effe[o:o + s]


def main(a):
    rel = a[a.index('--file') + 1] if '--file' in a else 'obj/p_sev120.objx'
    out = a[a.index('--out') + 1] if '--out' in a else None
    objx = load_objx(a[0], rel)
    ei, effe, name, fep_bytes = split(objx)
    f = F.Fep(fep_bytes)
    print('%s %s: effe member %s, FEP %d B, id %08x, own key base(s) %s (id base %08x)' % (
        a[0], rel, name, len(fep_bytes), F.u32(fep_bytes, 0x10), ['%08x' % b for b in f.own_key_bases()],
        f.key_base()))
    if '--usage' in a:
        usage_report(objx, fep_bytes)
        return
    changed = []
    if '--rekey' in a:
        n = f.rekey()
        print('  rekey: %d key fields -> base %08x' % (n, f.key_base()))
        changed.append('rekey')
    if '--tex' in a:
        spec = a[a.index('--tex') + 1]
        if '--kh2' in a:
            src = a[a.index('--kh2') + 1]
            if src.count(':') == 1:
                src = KH2_DEFAULT + ':' + src
            w, h, idx, pal = from_kh2(src)
        else:
            w, h, idx, pal = from_png(a[a.index('--png') + 1])
        if '--premultiply' in a:
            pal = premultiply(pal)
        if f.own_key_bases() != [f.key_base()]:
            print('  WARNING: own keys still %s (not this FEP id\'s base): add --rekey or Cloud vs Sora shares the'
                  ' texture' % ['%08x' % b for b in f.own_key_bases()])
        replace_tex(f, spec, w, h, idx, pal)
        changed.append('tex')
    if '--mdl-tex' in a:
        m, t = a[a.index('--mdl-tex') + 1].split('=')
        mi, ti = res_index(f, 'MDL', m), res_index(f, 'TEX', t)
        rec, blob = f.resources('MDL')[mi]
        tkey = F.u32(f.resources('TEX')[ti][0].data, 4)
        print('  MDL %d %08x: texture %08x -> %08x' % (mi, F.u32(rec.data, 4), F.u32(blob.data, 0x1c), tkey))
        struct.pack_into('<I', blob.data, 0x1c, tkey)
        changed.append('mdl-tex')
    new = f.write()
    F.Fep(new)                                                # re-parse check
    nobjx = join(objx, ei, effe, name, new)
    print('FEP %d -> %d B, objx %d -> %d B, changes: %s' % (len(fep_bytes), len(new), len(objx), len(nobjx),
                                                          ', '.join(changed) or 'none'))
    if out:
        open(out, 'wb').write(nobjx)
        print('patched copy written to', out, '(put it in with: pkg_put.py ISO %s %s)' % (rel, out))
        if '--png-dir' in a:
            from fep_dump import main as dump_main
            dump_main([out, '--png', a[a.index('--png-dir') + 1]])


if __name__ == '__main__':
    main(sys.argv[1:])
