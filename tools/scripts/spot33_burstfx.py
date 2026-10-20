"""KH2 look for #33's (Sora's) EX Burst effects -- notes/kh2-effects.md "EX Burst background" (2026-10-14 night).

Sora runs Cloud's Omnislash code. Its burst effects are Sora's own FEP leaves (copied from Cloud):
  CHOU_FIRE  (leaf 46, FEPA 50, slot _801B)  aura around him in the "tap ◯" phase: MDL 60 = orange flame texture o09
  CHOU_SMOKE (leaf 47, FEPA 51; also spawned per ◯ tap by the burst code FUN_08a3a638) = the swirling cloud dome
             behind the fight: MDL 61 (o14 clouds) + MDL 62 (G6 wisps)
  CHOU_LIGHT (leaf 48, FEPA 52; spawned when the tap target is reached) light column, violet/lavender
  CHOU_FINISH_APPEAR / CHOU_HIT_FINISH / CHOU_KOUKA_PERFECT (leaves 54/55/58) finish flashes, orange/peach/pink
Theme "KH2 night sky + white-gold light" (Dive to the Heart / Kingdom Hearts moon), size-neutral, Sora's files only:
  1. rekey (same as spot33_fx.py; no-op if already done) so Cloud vs Sora never share an edited MDL
  2. MDL 60 (only CHOU_FIRE) texture o09 flames -> global G6 soft wisps, vertex colours x white-gold => light aura
     MDL 61 (only CHOU_SMOKE) texture -> global G6, vertex colours x deep navy => dark blue swirling sky
     MDL 62 (only CHOU_SMOKE, G6) vertex colours x KH blue
     (global textures are only referenced by key, never edited)
  3. colour values (RGBA floats, 128 = 1.0) inside those leaves: FF7 warm/pink/violet -> KH2 blues and golds
     (COLOURS below; exact matches of the original values, so re-runs change nothing)
Run AFTER spot33_effects.py (Sora's FEP id 0x31280000); order vs spot33_fx.py doesn't matter.

  python3 -I spot33_burstfx.py ISO [--dry]
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fep as F  # noqa: E402
import fep_edit as E  # noqa: E402
from fep_dump import leaves, resources  # noqa: E402

FILE = 'obj/p_sev120.objx'
G6 = 0xF0000006                                    # global soft wisp texture (system resident.frr)
# MDL index: (new texture key or None, vertex tint RGB (128 = 1.0), leaf names that must be its only users)
MDLS = {60: (G6, (224, 200, 136), {'CHOU_FIRE'}),
        61: (G6, (40, 60, 132), {'CHOU_SMOKE'}),
        62: (None, (80, 112, 184), {'CHOU_SMOKE'})}
LEAVES = ('CHOU_FIRE', 'CHOU_SMOKE', 'CHOU_LIGHT', 'CHOU_FINISH_APPEAR', 'CHOU_HIT_FINISH', 'CHOU_KOUKA_PERFECT')
COLOURS = {  # FF7 (Cloud) RGB -> KH2 RGB
    (200, 128, 112): (210, 190, 120),   # CHOU_FIRE emitters: peach-pink -> white-gold
    (96, 112, 128): (56, 80, 140),      # CHOU_SMOKE: grey-blue -> night blue
    (72, 48, 128): (40, 64, 140),       # CHOU_LIGHT: violet -> royal blue
    (98, 98, 128): (90, 120, 180),      # CHOU_LIGHT: lavender -> KH blue
    (140, 160, 170): (200, 210, 230),   # CHOU_LIGHT: grey-cyan -> moonlight white
    (200, 64, 12): (230, 180, 60),      # CHOU_FINISH_APPEAR: orange-red -> gold
    (200, 200, 240): (200, 220, 255),   # CHOU_HIT_FINISH: lavender-white -> cool white
    (48, 24, 12): (12, 24, 56),         # CHOU_KOUKA_PERFECT: dim brown -> dim navy
    (200, 128, 98): (220, 200, 140),    # peach -> white-gold
    (200, 128, 64): (230, 190, 90),     # orange -> gold
    (240, 128, 64): (240, 210, 110),    # bright orange -> bright gold
    (200, 150, 128): (190, 200, 230),   # pink-beige -> pale blue-white
    (200, 112, 98): (120, 150, 220),    # salmon-pink -> blue
}
assert not set(COLOURS) & set(COLOURS.values()), 'a new colour equals an old one: re-runs would change it again'


def tint_grey(blob, rgb):
    """tint the GREY RGBA4444 vertices (R == G == B, these MDLs only have grey ones) by RGB (128 = 1.0), alpha kept.
    Already tinted vertices are no longer grey -> re-runs leave them alone (black stays black). -> count changed"""
    d = blob.data
    n = 0
    for k in range(F.u32(d, 0x34)):
        prim, vtype, stride, _, cnt, off = struct.unpack_from('<6I', d, F.u32(d, 0x38) + 0x18 * k)
        assert (vtype >> 2) & 7 == 6 and stride == 8 and vtype & 3 == 1, 'unexpected vertex type %x' % vtype
        for v in range(cnt):
            o = off + v * stride + 2                      # u8 u, u8 v, u16 colour, s8 x y z, pad
            c, = struct.unpack_from('<H', d, o)
            r, g, b = c & 15, c >> 4 & 15, c >> 8 & 15
            if not (r == g == b) or r == 0:
                continue
            nr, ng, nb = (min(15, round(r * x / 128)) for x in rgb)
            nc = nr | ng << 4 | nb << 8 | (c & 0xF000)
            if nc != c:
                struct.pack_into('<H', d, o, nc)
                n += 1
    return n


def leaf_ranges(d):
    """-> (leaves, {leaf index: [(start, end), ...]}) = the blobs of each leaf's own tree data (tree + nodes + tracks +
    params: everything reachable from its tree), one range per blob. Was "first node .. next leaf's first node", which
    breaks once a tree is transplanted elsewhere (spot33_lightningfx.py); a single min..max span is wrong too (tree
    headers and nodes live in different areas -> it overlaps other leaves)."""
    import fep_transplant as T
    L = leaves(d, resources(d))
    f = F.Fep(d)
    rng = {}
    for lf in L:
        if not lf['nodes']:
            continue
        blobs = T.subgraph(f, T.tree_slot(f, T.leaf_tree_index(d, lf['i']))[2])
        rng[lf['i']] = sorted((b.off, b.off + len(b.data)) for b in blobs)
    return L, rng


def scan(rng_list):
    """aligned offsets to test for a colour quad: every 4-byte position in each blob of the leaf's tree data"""
    for a, b in rng_list:
        yield from range(a, b - 16, 4)


def short(name):
    return name.replace('P0071_', '').replace('P_SEV100_', '').replace('_LEAF_0', '')


def edit_fep(fep_bytes):
    f = F.Fep(fep_bytes)
    nk = f.rekey()
    if nk:
        print('FEP: rekey %d fields -> base %08x' % (nk, f.key_base()))
    d0 = f.write()
    L, _ = leaf_ranges(d0)
    users = {}
    for lf in L:
        for n in lf['nodes']:
            for k, i in F.node_resources(d0, n['at']):
                if k == 'MDL':
                    users.setdefault(i, set()).add(short(lf['name']))
    for i, (tex, rgb, only) in sorted(MDLS.items()):
        assert users.get(i) == only, 'MDL %d is drawn by %s, expected only %s' % (i, users.get(i), only)
        rec, blob = f.resources('MDL')[i]
        if tex is not None and F.u32(blob.data, 0x1c) != tex:
            print('  MDL %d (%s) texture %08x -> %08x' % (i, ','.join(only), F.u32(blob.data, 0x1c), tex))
            struct.pack_into('<I', blob.data, 0x1c, tex)
        n = tint_grey(blob, rgb)
        print('  MDL %d grey vertex colours x %s: %d' % (i, rgb, n) if n else '  MDL %d: already tinted' % i)
    new = bytearray(f.write())
    assert len(new) == len(fep_bytes), 'size changed'
    L, rng = leaf_ranges(bytes(new))
    for lf in L:
        nm = short(lf['name'])
        if nm not in LEAVES:
            continue
        for o in scan(rng[lf['i']]):
            rgb = struct.unpack_from('<3f', new, o)
            if not all(0 <= x <= 255 and x == int(x) for x in rgb):    # also drops NaN / inf
                continue
            key = tuple(int(x) for x in rgb)
            if key not in COLOURS:
                continue
            prev = new[o - 4:o]
            p3 = struct.unpack_from('<3f', new, o - 12)
            alpha, = struct.unpack_from('<f', new, o + 12)
            if not (prev == b'\xcd' * 4 or p3[0] == p3[1] == p3[2]) or not 0 <= alpha <= 255:
                continue
            struct.pack_into('<3f', new, o, *COLOURS[key])
            print('  leaf %d %s @%#x colour %s -> %s' % (lf['i'], nm, o, key, COLOURS[key]))
    F.Fep(bytes(new))                              # re-parse check
    return None if bytes(new) == bytes(fep_bytes) else bytes(new)


def main(a):
    iso = a[0]
    objx = E.load_objx(iso, FILE)
    ei, effe, name, fep_bytes = E.split(objx)
    new = edit_fep(fep_bytes)
    if new is None:
        print('nothing to do')
        return
    objx = E.join(objx, ei, effe, name, new)
    if '--dry' in a:
        print('dry run: nothing written')
        return
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'f.objx')
        open(p, 'wb').write(objx)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main(sys.argv[1:])
