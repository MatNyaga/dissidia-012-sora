"""Magnet Burst (motion 10098, p_se block 68, piece 0xb32) = KH2 Magnet Burst / Magnet look -- notes/kh2-effects.md
"Magnet Burst". Replaces Codex's visibility stopgap (inbox/20261016-magnet-visible-dispatch: Explosion swirl FEPA 68
@18 + flash 57 @60 in block 68). Same method as spot33_barrier.py (KH2 mesh into a dead effect leaf, own FEPA rows,
op 0x19 one-shots), meshes from kh2_magnet_mesh.py.

What it looks like (static meshes, timing = animation; hits 20-24 / 42-46 / 60-66 unchanged):
  ORB   a purple-pink-white swirl sphere (KH2 Magnet swirl texture) around Sora's chest from 14 to 60, pulsing bigger
        on hits 1/2, a big flash at the burst (60).
  RINGS the KH2 Magnet Burst swirl disc + Magnega ring band: before each hit 4 rings shrink 3.2 m -> 1.3 m, turning
        and tilting = "rings pulling inward"; at 60-66 4 rings grow 1.2 m -> 5.4 m = the burst.
Resources (all asserted on every run, original values guarded):
  - TEX 19 (o13, Cloud's gradient) <- KH2 MAGNET_3 tex 0 (Magnet swirl, = P_EX100 DPD 3 tex 5), same 128x64 size, same
    key, NO new texture (TEX count stays 21: a 22nd froze test250-253). o13 is drawn only by ANM 16, ANM 16 only by
    leaves 29 (no FEPA row) and 38 (row 42: no script id, magi fx bit of unreached magi only).
  - leaves 20 HAKOU_APPEAR (orb) / 39 HAKOU_BG_HTM (rings) (Blade Beam, no FEPA row): their trees <- a copy of the ONE
    kind-0xc0 mesh-node tree of p_thr100 leaf 46 SWORD_WIND (another fighter's FEP on the clean ISO; same component
    list 01/04/07/11/0e/14 as the barrier's mesh node, one-shot, 50 frames, node life 36; component-version tables of
    both FEPs identical, asserted). Node init -> rotation 0, scale 100 %, RGB 128, offset 0. Their FXSE sound records
    (Cloud slots 36 / 25) muted.
  - MDL 26 (orb) / 28 (rings): Blade Beam meshes drawn only by leaf 21 HAKOU_SHOT (no FEPA row) -> one triangle strip
    each (334 / 206 vertices <= 384).
  - FEPA rows 11-13, 16-18, 24-27, 43, 53 = spot33_firefx's swirl/outer pool (ids 9101-9103, 9105-9113 -> leaf 16),
    unspawned since Codex Fire v1 (only 9100/9104 remain) -> ids 9130-9141, anchored to root like the barrier.
  - block 68: Codex's two stopgap one-shots removed, 21 op 0x19 one-shots added; main events/hits untouched.
  - plya 0xb32 +0x18 flags 0x10013 -> 0x10012 (Mat test275: "stuck in a falling pose until you dodge or move";
    notes/abilities-owner33.md "Magnet Burst stuck"); spot33_combos FLAGS now writes 0x10012 too.
  - node SERIALS (tree t2c lists) rewritten dense 0..N-1 over the whole FEP (test280 froze on a ground Bravery
    attack: the tree copies left N 454 / max 468 -> DRAW_SONIC row 77 on _600A out of bounds; notes/kh2-effects.md).
  - LAYOUT: every FEP blob keeps its input offset mod 16 (filler blobs; copied blobs keep the donor's). Node init
    data must stay at 12 mod 16 (lv.q): test280/284 froze on any attack because the copies shifted it.
effe stays 848,640 B, FEP 803,952 B. Re-runnable ("nothing to do"). Owner 33 (obj/p_sev120.objx) only.
Run after spot33_firefx / spot33_barrier / the Codex Fire chain (it takes rows they leave unspawned).

  python3 -I spot33_magnet.py ISO CLEAN_ISO [--dry] [--out NEW.objx]
  python3 -I spot33_magnet.py --preview OUT.png        offline timeline sheet (dumps/renders/kh2magnet/)
  env: MAGNET_SCALE (size x, default 1.0), MAGNET_OPACITY / MAGNET_TEX_GAIN (kh2_magnet_mesh), MAGNET_Y (orb height
       above root, m, default 0.35)
"""
import collections
import hashlib
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fep as F  # noqa: E402
import fep_edit as E  # noqa: E402
import fep_transplant as T  # noqa: E402
import kh2_magnet_mesh as K  # noqa: E402
import spot33_barrier as B  # noqa: E402

FILE, DONOR_FILE, DONOR_LEAF, DONOR_MDL = 'obj/p_sev120.objx', 'obj/p_thr100.objx', 46, 79
EFFE_SIZE, FEP_SIZE, TEX_COUNT, MDL_COUNT = 848640, 803952, 21, 85
MOTION, BLOCK, PIECE = 10098, 68, 0xb32
HITS = [(20, 24, 0x372), (42, 46, 0x372), (60, 66, 0x1001)]
STOPGAP = [(18, 68), (60, 57)]                 # Codex magnet-visible-dispatch one-shots (op 0x19 [id, 0], cond 0)
FLAGS_OLD, FLAGS_NEW = 0x10013, 0x10012
TEX_I = 19                                     # o13
TEX_ORIG = '2065779e1dd5ed1621a480154d317f3b30e782cffba846c0f1cdf18a5341d102'   # sha256 of data[0x30:] (Cloud's o13)
TEX_ANM, TEX_ANM_LEAVES = 16, {29, 38}
LAYERS = {   # name: leaf, MDL, builder, original MDL sha256 (key field zeroed)
    'orb': dict(leaf=20, mdl=26, build=K.orb_mdl,
                orig='f26803b1c83b48eb734e453d24aab9344953483e04ad460eb42a72fe8c48fcd4'),
    'rings': dict(leaf=39, mdl=28, build=K.ring_mdl,
                  orig='9fe7cc9463632f93ad7143872b425eccc0275d0c8b11b325c0a20eee2170c7ae'),
}
MDL_ONLY_LEAF = 21                             # HAKOU_SHOT also draws MDL 26/28 (no FEPA row: never spawned)
NODE_INIT = {0x01: (0.0, 0.0, 0.0), 0x04: (100.0, 100.0, 100.0), 0x07: (128.0, 128.0, 128.0), 0x0e: (0.0, 0.0, 0.0)}
# comps 0x11 (48 B, ends with flags 0x0101 vs the donor's 0x0001: blend/depth?) and 0x14 (MDL draw: index + 2.0/6.0/
# 64/32 in the donor = maybe UV scroll) <- the barrier mesh node's vanilla values (KYOU_WORDS_3 node 0, seen in game)
NODE_RAW = {0x11: bytes.fromhex('0000000000000000000000000000000020c24341000000000000000000000000895f15bf01010000'
                                '0000cdcdcdcdcdcd'),
            0x14: bytes.fromhex('440000000000000000000000000000000000803f0000000000000000000000000000000000000000'
                                '0000000000000000')[2:]}     # 0x14: bytes 2.. (the u16 MDL index stays)
TREE_DUR, NODE_LIFE = 50, 36                   # donor values (asserted, kept)
# KEYFRAMES (test287, Mat: "I can't see the new effects"): a node's real values live in its KEY blocks (node +0x24 ->
# node[0x13] x {u16 start, u16 len, u32 n, ptr -> n x {u16 track, u16 offset, u16 start, u16 len} + params}); the init
# block (n20) is not what is drawn. The donor's key 0 had scale 10 %, rotation z 180, colour (128,160,192) and its own
# MDL index 79 in comp 0x14 -> the magnet meshes were drawn tiny / as another mesh. Every key block of our nodes gets:
# rotation 0 (native meshes are authored flat in x/z, y up: Firaga's ground ring MDL 22 draws with rotation 0),
# scale 100 %, RGB 128, offset 0, and the barrier node's (KYOU_WORDS_3, vanilla) comp 0x11 / 0x14 key blocks (alpha
# 0 -> 128 fade-in, flags 0x0101 / 01 03 00) with our MDL index.
KEY_VEC = {0x01: (0.0, 0.0, 0.0), 0x04: (100.0, 100.0, 100.0), 0x07: (128.0, 128.0, 128.0), 0x0e: (0.0, 0.0, 0.0)}
KEY_RAW = {   # (key index, comp) -> barrier bytes (Cloud leaf 51 node 0)
    (0, 0x11): bytes.fromhex('0000000000000000000000000000000020c24341000000000000000000000000895f15bf01010000'
                             '0000cdcdcdcdcdcd'),
    (0, 0x14): bytes.fromhex('440000000000000000000000000000000000803f0000000000000000000000000000000000000000'
                             '0000000000000000000000000000803f00000000010300cdcdcdcdcd'),
    (1, 0x11): bytes.fromhex('000000430000000000000000000000000000000000000000000000000000000000000000'),
    (2, 0x11): bytes.fromhex('0000004300000000000000000000000071a399c10000000000000000000000009e25b63f'),
}
SC = float(os.environ.get('MAGNET_SCALE', '1.0'))
Y = float(os.environ.get('MAGNET_Y', '0.35'))  # root space, y > 0 = up (spot33_barrier, Mat-verified)
# FEPA rows: index -> (layer, new id, scale, rotation deg (x, y, z), start offset (+0x30; visible = 36 - start))
POOL = (11, 12, 13, 16, 17, 18, 24, 25, 26, 27, 43, 53)
POOL_IDS = set(range(9101, 9114)) - {9104}
ROWS = {
    11: ('orb', 9130, 1.0, (0, 0, 0), 0),          # O1 36 frames
    12: ('orb', 9131, 1.0, (0, 0, 0), 14),         # O2 22 frames
    13: ('orb', 9132, 1.35, (0, 45, 0), 30),       # pulse 6 frames
    16: ('orb', 9133, 2.4, (0, 90, 0), 26),        # burst flash 10 frames
    17: ('rings', 9134, 3.2, (12, 0, 0), 31),      # pull-in 1..4, 5 frames each
    18: ('rings', 9135, 2.5, (0, 22.5, -12), 31),
    24: ('rings', 9136, 1.85, (-12, 45, 0), 31),
    25: ('rings', 9137, 1.3, (0, 67.5, 12), 31),
    26: ('rings', 9138, 1.2, (0, 0, 0), 30),       # burst 1..4, 6 frames each
    27: ('rings', 9139, 2.4, (0, 30, 0), 30),
    43: ('rings', 9140, 3.8, (0, 60, 0), 30),
    53: ('rings', 9141, 5.4, (0, 90, 0), 30),
}
assert sorted(ROWS) == sorted(POOL)


def schedule():
    """-> [(frame, FEPA id)] one-shots for block 68 (60 ticks/s; hits 20-24, 42-46, 60-66, animation 0-90)"""
    pull = [9134, 9135, 9136, 9137]
    out = [(t0 + 3 * k, i) for t0 in (8, 30, 48) for k, i in enumerate(pull)]      # rings shrink into each hit
    out += [(14, 9130), (38, 9131), (20, 9132), (42, 9132), (60, 9133)]            # orb, pulses, burst flash
    out += [(60 + 2 * k, i) for k, i in enumerate([9138, 9139, 9140, 9141])]       # burst rings grow
    return sorted(out)


NEW_IDS = {r[1] for r in ROWS.values()}
ATTACH_MODEL, ATTACH_NODE, ATTACH_FLAGS, ATTACH_SLOT = 'p_sev100_1p', 'root', 0x80, '_000A'
TEMPLATE_ROW = 22


def sha(b):
    return hashlib.sha256(b).hexdigest()


def mdl_bytes(f, i):
    rec, blob = f.resources('MDL')[i]
    return bytes(blob.data[:F.u32(rec.data, 8)])


def key0(mdl):
    x = bytearray(mdl)
    struct.pack_into('<I', x, 8, 0)
    struct.pack_into('<I', x, 0x1c, 0)
    return bytes(x)


def fepa_rows(feb):
    n, = struct.unpack_from('<I', feb, 12)
    return [struct.unpack_from('<II', feb, 16 + 0x104 * i + 0x24) for i in range(n)]


# ---------------------------------------------------------------- audit (resources dead in THIS objx)
def audit(objx, mine_ok=True):
    u = E.script_usage(objx)
    feb = E.mpk_member(objx, 1)
    rows = fepa_rows(feb)
    live_bits = {b for b, ms in u['fx_bits'].items() if ms & u['magi_reach']}
    d = E.split(objx)[3]
    L, users = B.leaf_users(d)
    lay_leaves = {s['leaf'] for s in LAYERS.values()}
    for i, (rid, res) in enumerate(rows):
        mb, = struct.unpack_from('<I', feb, 16 + 0x104 * i + 0x3c)
        if i in ROWS:
            assert rid in POOL_IDS | ({ROWS[i][1]} if mine_ok else set()), 'FEPA row %d id %d not ours/pool' % (i, rid)
            if rid in POOL_IDS:
                assert res == 16 and rid not in u['ids'], 'pool row %d (id %d) -> leaf %d / spawned %s' % (
                    i, rid, res, u['ids'].get(rid))
            else:
                want = LAYERS[ROWS[i][0]]['leaf']
                assert res == want, 'row %d -> leaf %d' % (i, res)
            assert not {b for b in range(32) if mb >> b & 1} & live_bits, 'row %d has live magi bits' % i
            continue
        assert rid not in NEW_IDS, 'FEPA row %d already uses id %d' % (i, rid)
        assert res not in lay_leaves | {MDL_ONLY_LEAF, 29}, 'FEPA row %d (id %d) -> leaf %d' % (i, rid, res)
        if res == 38:
            assert rid not in u['ids'] and not {b for b in range(32) if mb >> b & 1} & live_bits, \
                'leaf 38 (draws o13) is live via row %d' % i
    for rid in NEW_IDS:
        for where in u['ids'].get(rid, ()):
            assert where.startswith('blk%d ' % BLOCK) and 'os19' in where, 'id %d spawned by %s' % (rid, where)
    # o13 users
    for lf in L:
        for n in lf['nodes']:
            for k, x in F.node_resources(d, n['at']):
                if k == 'TEX':
                    assert x != TEX_I, 'leaf %d draws TEX %d directly' % (lf['i'], TEX_I)
                if k == 'ANM' and x == TEX_ANM:
                    assert lf['i'] in TEX_ANM_LEAVES, 'leaf %d draws ANM %d (o13)' % (lf['i'], TEX_ANM)
    rk = F.resource_keys(d)
    tkey = rk['TEX'][TEX_I]
    for i, ks in enumerate(rk['ANM_tex']):
        assert tkey not in ks or i == TEX_ANM, 'ANM %d uses o13' % i
    for i, ks in enumerate(rk['MDL_tex']):
        assert tkey not in ks or i in {s['mdl'] for s in LAYERS.values()}, 'MDL %d uses o13' % i
    for s in LAYERS.values():
        assert users[('MDL', s['mdl'])] <= {s['leaf'], MDL_ONLY_LEAF}, 'MDL %d drawn by %s' % (
            s['mdl'], users[('MDL', s['mdl'])])
    return u


# ---------------------------------------------------------------- FEP
def edit_fep(sd, donor_d):
    assert len(sd) == FEP_SIZE, 'FEP %d B' % len(sd)
    S = F.Fep(sd)
    assert S.own_key_bases() == [S.key_base()], 'run spot33_fx (rekey) first'
    assert len(S.resources('TEX')) == TEX_COUNT and len(S.resources('MDL')) == MDL_COUNT
    vt = lambda d: d[F.u32(d, F.u32(d, 8) + 4):F.u32(d, F.u32(d, 8) + 4) + 4 * F.u32(d, F.u32(d, 8))]
    assert vt(sd) == vt(donor_d), 'component-version tables differ (donor FEP)'
    changes = []
    trees_before, res_before = B.tree_views(F.Fep(zero_serials(sd))), B.res_views(S)
    lay_trees = {T.leaf_tree_index(sd, s['leaf']) for s in LAYERS.values()}
    # 1. TEX 19 = KH2 Magnet swirl
    rec, blob = S.resources('TEX')[TEX_I]
    tkey = F.u32(rec.data, 4)
    assert tkey == S.key_base() | 0x13, 'TEX %d key %08x' % (TEX_I, tkey)
    w, h, idx, pal = K.texture()
    t = E.make_tex(tkey, w, h, idx, pal)
    cur = bytes(blob.data[:F.u32(rec.data, 8)])
    if cur != t:
        assert sha(cur[0x30:]) == TEX_ORIG, 'TEX %d is neither Cloud\'s o13 nor ours' % TEX_I
        assert len(cur) == len(t)
        T.put_resource(S, 'TEX', TEX_I, t)
        changes.append('TEX %d %08x <- KH2 MAGNET_3 tex 0 (Magnet swirl) 128x64, same size' % (TEX_I, tkey))
    # 2. meshes
    for name, s in LAYERS.items():
        rec, blob = S.resources('MDL')[s['mdl']]
        m, info = s['build'](F.u32(rec.data, 4), tkey)
        cur = bytes(blob.data[:F.u32(rec.data, 8)])
        if cur != m:
            assert sha(key0(cur)) == s['orig'], 'MDL %d is neither the original nor ours (%s)' % (s['mdl'], sha(key0(cur)))
            T.put_resource(S, 'MDL', s['mdl'], m)
            changes.append('MDL %d <- %s: %s, one strip %d vertices (%d B)' % (s['mdl'], name, info['kh2'],
                                                                                info['vertices'], len(m)))
    # 3. trees: copy of the donor's single mesh-node tree. tgt = the offset mod 16 every blob must keep: the input's
    # own for its blobs, the donor's for copied ones (test284/280 froze: the copy shifted every later blob by a
    # non-multiple of 16 -> node init data (vanilla always offset = 12 mod 16, read with lv.q at +4) misaligned ->
    # address error in the trail draw FUN_08964eac).
    from fep_dump import leaves, resources
    tgt = {id(bl): bl.off % 16 for bl in S.blobs if bl.off is not None}
    D = F.Fep(donor_d)
    dl = leaves(donor_d, resources(donor_d))[DONOR_LEAF]
    assert dl['name'] == 'P0031_P_THR100_SWORD_WIND_LEAF_0' and len(dl['nodes']) == 1
    assert dl['nodes'][0]['kind'] == 0xc0 and dl['nodes'][0]['res'] == [('MDL', DONOR_MDL)]
    dsub = T.subgraph(D, T.tree_slot(D, T.leaf_tree_index(donor_d, DONOR_LEAF))[2])
    for name, s in LAYERS.items():
        cur = S.write()
        nodes = leaves(cur, resources(cur))[s['leaf']]['nodes']
        if not (len(nodes) == 1 and nodes[0]['kind'] == 0xc0 and nodes[0]['res'] == [('MDL', s['mdl'])]):
            rm, add = T.copy_tree(S, D, donor_d, DONOR_LEAF, s['leaf'], cur, {'MDL': {DONOR_MDL: s['mdl']},
                                                                               'ANM': {}, 'TEX': {}})
            nsub = T.subgraph(S, T.tree_slot(S, T.leaf_tree_index(cur, s['leaf']))[2])
            assert len(nsub) == len(dsub) and all(len(x.data) == len(y.data) for x, y in zip(nsub, dsub))
            for x, y in zip(nsub, dsub):
                tgt[id(x)] = y.off % 16
            changes.append('leaf %d tree (%s) <- copy of p_thr100 leaf %d (one kind-0xc0 mesh node -> MDL %d): '
                           '-%d +%d B' % (s['leaf'], name, DONOR_LEAF, s['mdl'], rm, add))
    # 4. layout: trim the absorbed pad, keep every blob's offset mod 16 (filler blobs), pad to the exact size
    last = S.blobs[-1]
    keep = len(bytes(last.data).rstrip(b'\0'))
    keep += -keep % F.DATA_ALIGN
    if keep < len(last.data):
        del last.data[keep:]
    fill = align_layout(S, tgt)
    T.pad_to(S, FEP_SIZE)
    # 5. node init (in place, layout unchanged)
    new = bytearray(S.write())
    L = leaves(bytes(new), resources(bytes(new)))
    for name, s in LAYERS.items():
        tr = B.tree_of(new, s['leaf'])
        assert struct.unpack_from('<II', new, tr) == (0, TREE_DUR), 'leaf %d tree header' % s['leaf']
        (n,) = L[s['leaf']]['nodes']
        assert n['life'] == NODE_LIFE
        comps = {c: o for c, _, o in F.node_components(bytes(new), n['at']) if o is not None}
        for c, v in NODE_INIT.items():
            o = comps[c] + 4
            if struct.unpack_from('<3f', new, o) != v:
                changes.append('leaf %d node comp %#x %s -> %s' % (
                    s['leaf'], c, tuple(round(x, 2) for x in struct.unpack_from('<3f', new, o)), v))
                struct.pack_into('<3f', new, o, *v)
        for c, raw in NODE_RAW.items():
            o = comps[c] + (2 if c == 0x14 else 0)
            if bytes(new[o:o + len(raw)]) != raw:
                changes.append('leaf %d node comp %#x params -> barrier node values' % (s['leaf'], c))
                new[o:o + len(raw)] = raw
        assert F.u16(new, comps[0x14]) == s['mdl']
        assert all(o % 16 == 12 for o in comps.values()), 'leaf %d init data misaligned' % s['leaf']
        nd = n['at']
        tl = F.u32(new, nd + 0x1c)
        tcomp = [F.u16(new, F.u32(new, tl + 4 * j)) for j in range(new[nd + 8])]
        l24 = F.u32(new, nd + 0x24)
        assert new[nd + 0x13] == 3, 'leaf %d: %d key blocks' % (s['leaf'], new[nd + 0x13])
        for kj in range(new[nd + 0x13]):
            it = F.u32(new, l24 + 4 * kj)
            dat = F.u32(new, it + 8)
            assert dat % 16 == 12, 'leaf %d key %d misaligned' % (s['leaf'], kj)
            for e in range(F.u32(new, it + 4)):
                tr, off = struct.unpack_from('<HH', new, dat + 8 * e)
                c = tcomp[tr]
                o = dat + off
                if c in KEY_VEC:
                    if struct.unpack_from('<3f', new, o + 4) != KEY_VEC[c]:
                        changes.append('leaf %d key %d comp %#x %s -> %s' % (
                            s['leaf'], kj, c, tuple(round(x, 2) for x in struct.unpack_from('<3f', new, o + 4)),
                            KEY_VEC[c]))
                        struct.pack_into('<3f', new, o + 4, *KEY_VEC[c])
                elif (kj, c) in KEY_RAW:
                    raw = bytearray(KEY_RAW[(kj, c)])
                    if c == 0x14:
                        struct.pack_into('<H', raw, 0, s['mdl'])
                    if bytes(new[o:o + len(raw)]) != bytes(raw):
                        changes.append('leaf %d key %d comp %#x params -> barrier key (MDL %d)' % (
                            s['leaf'], kj, c, s['mdl']))
                        new[o:o + len(raw)] = raw
                else:
                    raise AssertionError('leaf %d key %d: unexpected comp %#x' % (s['leaf'], kj, c))
    if fill and bytes(new) != sd:
        changes.append('layout: %d B filler so every blob keeps its offset mod 16' % fill)
    out = bytes(new)
    out, nser, total = renumber_serials(out)
    if nser:
        changes.append('t2c node serials renumbered dense 0..%d in tree order (%d entries changed)' % (total - 1, nser))
    G = F.Fep(out)
    assert G.write() == out and renumber_serials(out)[1] == 0
    assert init_alignment(out) == init_alignment(sd) or init_alignment(out)[0] < init_alignment(sd)[0], \
        'node init data alignment got worse: %s -> %s' % (init_alignment(sd), init_alignment(out))
    assert len(out) == FEP_SIZE
    assert len(G.resources('TEX')) == TEX_COUNT and len(G.resources('MDL')) == MDL_COUNT
    trees_after, res_after = B.tree_views(F.Fep(zero_serials(out))), B.res_views(G)
    for ti, v in trees_before.items():
        if ti not in lay_trees:
            assert trees_after[ti] == v, 'tree %d changed' % ti
    mine = {('TEX', TEX_I)} | {('MDL', s['mdl']) for s in LAYERS.values()}
    for k in ('TEX', 'MDL', 'ANM'):
        for i, v in enumerate(res_before[k]):
            if (k, i) not in mine:
                assert res_after[k][i] == v, '%s %d changed' % (k, i)
    _, users = B.leaf_users(out)
    for s in LAYERS.values():
        assert users[('MDL', s['mdl'])] == {s['leaf'], MDL_ONLY_LEAF}
    return (None if out == sd else out), changes


def renumber_serials(d):
    """tree +0x2c t2c lists: {u16 n, ptr -> n x (u16 frame?, u16 SERIAL)}. Vanilla (Cloud, p_thr100): serials are one
    FEP-wide sequence 0..N-1 in tree order, N = number of entries. Copying a foreign tree brings the donor's serial
    (test277: 307 twice) and dropping nodes leaves holes / max >= N (test275 already: 463 entries, max 468).
    test280 froze on a plain ground Bravery attack (PC 0x08964eac, like Lightning's tree transplant test200 'froze on
    the first Bravery swing') -> rewrite them dense again. -> (new bytes, number of changed entries)"""
    out = bytearray(d)
    k = changed = 0
    for field, target, kind in F.walk(d):
        if kind != 't2c_data':
            continue
        n = F.u16(d, field - 4)
        for j in range(n):
            if F.u16(out, target + 4 * j + 2) != k:
                struct.pack_into('<H', out, target + 4 * j + 2, k)
                changed += 1
            k += 1
    return bytes(out), changed, k


def align_layout(S, tgt):
    """insert unreferenced zero filler blobs so every blob in tgt starts at its wanted offset mod 16 -> bytes added"""
    pos, out, added = 0, [], 0
    for bl in S.blobs:
        pos += -pos % bl.align
        want = tgt.get(id(bl))
        if want is not None and pos % 16 != want:
            gap = (want - pos) % 16
            assert gap % 4 == 0 and want % bl.align == 0, (bl, want)
            out.append(F.Blob(None, bytes(gap), 4))
            pos += gap
            added += gap
        out.append(bl)
        pos += len(bl.data)
    S.blobs = out
    return added


def init_alignment(d):
    """-> (number of node init blocks (n20_data / n24_data) at offset != 12 mod 16, their leaves)"""
    f = F.Fep(d)
    owner = {}
    for ti in range(F.u16(d, 0x1e)):
        for bl in T.subgraph(f, T.tree_slot(f, ti)[2]):
            owner[id(bl)] = ti
    t2l = {F.u16(d, F.u32(d, F.u32(d, 0x28) + 4 * i) + 4): i for i in range(F.u16(d, 0x1c))}
    bad = collections.Counter(t2l.get(owner.get(id(bl))) for bl in f.blobs
                              if bl.kinds & {'n20_data', 'n24_data'} and bl.off % 16 != 12)
    return sum(bad.values()), dict(bad)


def zero_serials(d):
    out = bytearray(d)
    for field, target, kind in F.walk(d):
        if kind == 't2c_data':
            for j in range(F.u16(d, field - 4)):
                struct.pack_into('<H', out, target + 4 * j + 2, 0)
    return bytes(out)


# ---------------------------------------------------------------- FEPA / FXSE
def edit_fepa(feb):
    feb = bytearray(feb)
    rows = fepa_rows(feb)
    t = next(i for i, (rid, _) in enumerate(rows) if rid == TEMPLATE_ROW)
    tpl = bytes(feb[16 + 0x104 * t:16 + 0x104 * (t + 1)])
    msgs = []
    for i, (layer, rid, scale, rot, start) in sorted(ROWS.items()):
        a = 16 + 0x104 * i
        row = bytearray(tpl)
        struct.pack_into('<II', row, 0x24, rid, LAYERS[layer]['leaf'])
        struct.pack_into('<I', row, 0x30, start)
        struct.pack_into('<I', row, 0x3c, 0)
        struct.pack_into('<3f', row, 0x00, 0.0, Y, 0.0)
        struct.pack_into('<3f', row, 0x0c, *map(float, rot))
        struct.pack_into('<3f', row, 0x18, *([scale * SC] * 3))
        struct.pack_into('<I', row, 0x7c, ATTACH_FLAGS)
        row[0x88:0xa8] = ATTACH_MODEL.encode().ljust(32, b'\0')
        row[0xa8:0xc8] = ATTACH_NODE.encode().ljust(32, b'\0')
        row[0xc8:0xe8] = ATTACH_SLOT.encode().ljust(32, b'\0')
        if row != feb[a:a + 0x104]:
            feb[a:a + 0x104] = row
            msgs.append('FEPA row %d -> id %d, leaf %d (%s) x%.2f rot %s start %d (%d frames) at root +%.2f m' % (
                i, rid, LAYERS[layer]['leaf'], layer, scale * SC, rot, start, NODE_LIFE - start, Y))
    return (bytes(feb) if msgs else None), msgs


def edit_fxse(fx):
    fx = bytearray(fx)
    msgs = []
    for name, s in LAYERS.items():
        for k in range(16):
            o = 16 + s['leaf'] * 0x140 + k * 0x14
            r = struct.unpack_from('<5I', fx, o)
            if r[0]:
                assert r[0] % 100000 == 0 and r[2] == 0, 'leaf %d FXSE record %s' % (s['leaf'], r)
                fx[o:o + 0x14] = bytes(0x14)
                msgs.append('FXSE leaf %d (%s) record %d (Cloud slot %d) muted' % (s['leaf'], name, k, r[1]))
    return (bytes(fx) if msgs else None), msgs


# ---------------------------------------------------------------- scripts / plya
def edit_scripts(objx):
    ents = E.arc_entries(objx)
    i8 = next(i for i, e in enumerate(ents) if e[0] == 8 and e[1] == b'p_se')
    ch = B.chunks(objx)
    t7, c = ch[(7, b'p_se')], ch[(8, b'p_se')]
    assert [blk for mid, blk, _ in B.motion_rows(t7) if mid == MOTION] == [BLOCK], 'motion %d block' % MOTION
    bl = B.blocks(c)
    o, mains, ones = bl[BLOCK]
    hits = [(f0, f1, p[0]) for f0, f1, op, var, cond, p in mains if op == 0]
    assert hits == HITS, 'Magnet hit windows changed %s' % hits
    assert not [x for x in ones if x[1] == 4], 'block %d spawns a magi (extra damage?)' % BLOCK
    vis = [x for x in ones if x[1] == 0x19]
    gap = [(x[0], x[3][0]) for x in vis if x[3] and x[3][0] in (68, 57)]
    assert all(x[2] == bytes(4) and len(x[3]) == 2 and x[3][1] == 0 for x in vis), 'unexpected op 0x19 form'
    assert set(gap) <= set(STOPGAP) and len(gap) == len(set(gap)), 'block %d op 0x19 %s' % (BLOCK, gap)
    other = [(x[0], x[3][0]) for x in vis if x[3][0] not in (68, 57)]
    assert set(other) <= set(schedule()), 'other effect one-shots in block %d: %s' % (BLOCK, other)
    want = schedule()
    keep = [x for x in ones if not (x[1] == 0x19 and x[3][0] in {68, 57} | NEW_IDS)]
    if not gap and sorted(other) == want and len(other) == len(want):
        return None, []
    recs = [(x[0], x[1], x[2], x[3]) for x in keep] + [(fr, 0x19, bytes(4), (rid, 0)) for fr, rid in want]
    size, e1 = struct.unpack_from('<H', c, o + 6)[0], struct.unpack_from('<H', c, o + 4)[0]
    head = bytearray(c[o:o + e1])
    head[3] = len(recs)
    assert len(recs) < 255
    body = b''.join(struct.pack('<HBB4s', fr, op, len(p), cond) + struct.pack('<%dI' % len(p), *p)
                    for fr, op, cond, p in recs)
    blob = bytearray(bytes(head) + body)
    struct.pack_into('<H', blob, 6, len(blob))
    n, = struct.unpack_from('<I', c, 4)
    offs = list(struct.unpack_from('<%dI' % n, c, 8))
    nc = bytearray(c)
    nc[o:o + size] = blob
    grow = len(blob) - size
    struct.pack_into('<%dI' % n, nc, 8, *[x + grow if x > o else x for x in offs])
    nb = B.blocks(bytes(nc))
    for b in range(n):
        if b != BLOCK:
            assert nb[b][1:] == bl[b][1:], 'block %d changed' % b
    assert nb[BLOCK][1] == mains, 'block %d main events changed' % BLOCK
    got = sorted((x[0], x[3][0]) for x in nb[BLOCK][2] if x[1] == 0x19)
    assert got == want and [x for x in nb[BLOCK][2] if x[1] != 0x19] == [x for x in ones if x[1] != 0x19]
    from spot33_combos import rebuild_arc
    msgs = ['p_se block %d (motion %d): removed stopgap one-shots %s; + %d op 0x19 one-shots %s' % (
        BLOCK, MOTION, sorted(gap), len(want), want)]
    return rebuild_arc(objx, {i8: bytes(nc)}), msgs


def edit_plya(objx):
    ents = E.arc_entries(objx)
    ip = next(i for i, e in enumerate(ents) if e[0] == 1 and e[1] == b'plya')
    pl = bytearray(objx[ents[ip][2]:ents[ip][2] + ents[ip][3]])
    n, = struct.unpack_from('<I', pl, 4)
    at = [8 + 116 * k for k in range(n) if struct.unpack_from('<H', pl, 8 + 116 * k)[0] == PIECE]
    assert len(at) == 1, 'piece %#x rows %s' % (PIECE, at)
    a = at[0]
    assert struct.unpack_from('<H', pl, a + 0x1c)[0] == MOTION and struct.unpack_from('<H', pl, a + 0x10)[0] == 0xFFFF
    fl, = struct.unpack_from('<I', pl, a + 0x18)
    if fl == FLAGS_NEW:
        return None, []
    assert fl == FLAGS_OLD, 'piece %#x flags %#x' % (PIECE, fl)
    struct.pack_into('<I', pl, a + 0x18, FLAGS_NEW)
    from spot33_combos import rebuild_arc
    return rebuild_arc(objx, {ip: bytes(pl)}), ['plya %#x (Magnet Burst) flags %#x -> %#x (no plunge/landing wait: '
                                                 'block 68 stays airborne, no landing motion)' % (PIECE, fl, FLAGS_NEW)]


def preview(out, frames=(8, 12, 17, 20, 30, 38, 42, 50, 57, 60, 63, 66)):
    """offline timeline: every live instance per script frame (additive, KH2 texture), 3/4 view at game scale with
    the floor and a 1.5 m bar for Sora (root 0.85 m above the feet)"""
    import math
    from PIL import Image, ImageDraw
    import kh2_reflect_mesh as M
    tex = K.texture()
    mesh = {n: M.decode_mdl(s['build']()[0]) for n, s in LAYERS.items()}
    byid = {r[1]: r for r in ROWS.values()}

    def rot(p, r):
        x, y, z = p
        for ax, deg in zip('xyz', r):
            c, s_ = math.cos(math.radians(deg)), math.sin(math.radians(deg))
            if ax == 'x':
                y, z = y * c - z * s_, y * s_ + z * c
            elif ax == 'y':
                x, z = x * c + z * s_, -x * s_ + z * c
            else:
                x, y = x * c - y * s_, x * s_ + y * c
        return x, y, z
    cell = 300
    sheet = Image.new('RGB', (cell * 4, cell * ((len(frames) + 3) // 4) + 26), (8, 10, 14))
    dr = ImageDraw.Draw(sheet)
    for k, fr in enumerate(frames):
        tris = []
        live = [(t, byid[i]) for t, i in schedule() if t <= fr < t + NODE_LIFE - byid[i][4]]
        for t, (layer, rid, sc, r, st) in live:
            for tri in mesh[layer]:
                tris.append([(tuple(v + o for v, o in zip(rot(tuple(c * sc * SC for c in p), r), (0, B.ROOT_H + Y, 0))),
                              uv, col) for p, uv, col in tri])
        im = (M.render(tris, tex, cell, yaw=30, pitch=12, scale=4.2, centre=(0.0, 1.2), marker=(1.5, 0.0)) if tris
              else Image.new('RGB', (cell, cell), (12, 16, 24)))
        ImageDraw.Draw(im).text((4, 4), 'f%d  %s' % (fr, ' '.join(sorted(l for _, (l, *_x) in live)) or '-'),
                                fill='white')
        sheet.paste(im, ((k % 4) * cell, 26 + (k // 4) * cell))
    dr.text((4, 6), 'Magnet Burst block 68 (hits 20-24 / 42-46 / 60-66), offline, additive, KH2 Magnet texture. '
            'White bar = Sora 1.5 m. No game shader.', fill='white')
    sheet.save(out)
    return out


def main(a):
    if a and a[0] == '--preview':
        print(preview(a[1]))
        return
    iso, clean = a[0], a[1]
    objx = E.load_objx(iso, FILE)
    before = objx
    donor_d = E.split(E.load_objx(clean, DONOR_FILE))[3]
    audit(objx)
    print('audit OK: o13 only via ANM %d (leaves %s, unspawned); leaves %s + MDL %s free; pool rows %s unspawned' % (
        TEX_ANM, sorted(TEX_ANM_LEAVES), [s['leaf'] for s in LAYERS.values()], [s['mdl'] for s in LAYERS.values()],
        list(POOL)))
    ei, effe, name, sd = E.split(objx)
    assert len(effe) == EFFE_SIZE, 'effe %d B' % len(effe)
    changes = []
    new, ch = edit_fep(sd, donor_d)
    changes += ch
    if new is not None:
        objx = E.join(objx, ei, effe, name, new)
    from spot33_fx import patch_member
    feb, ch = edit_fepa(E.mpk_member(objx, 1))
    changes += ch
    if feb is not None:
        objx = patch_member(objx, 1, feb)
    fx, ch = edit_fxse(E.mpk_member(objx, 2))
    changes += ch
    if fx is not None:
        objx = patch_member(objx, 2, fx)
    for step in (edit_scripts, edit_plya):
        x, ch = step(objx)
        changes += ch
        if x is not None:
            objx = x
    eff = next(e for e in E.arc_entries(objx) if e[1] == b'effe')
    assert eff[3] == EFFE_SIZE, 'effe %d B != %d' % (eff[3], EFFE_SIZE)
    audit(objx)
    keep = {(8, b'p_se'), (1, b'plya'), (eff[0], b'effe')}
    old_ch, new_ch = B.chunks(before), B.chunks(objx)
    assert set(old_ch) == set(new_ch)
    for k in old_ch:
        if k not in keep:
            assert old_ch[k] == new_ch[k], 'chunk %s changed' % (k,)
    for x in changes:
        print(x)
    print('effe chunk %d B, FEP %d B, objx %d B' % (eff[3], len(E.split(objx)[3]), len(objx)))
    if not changes:
        print('nothing to do')
        return
    if '--dry' in a:
        print('dry run: nothing written')
        return
    if '--out' in a:
        open(a[a.index('--out') + 1], 'wb').write(objx)
        print('objx written to', a[a.index('--out') + 1])
        return
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'f.objx')
        open(p, 'wb').write(objx)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main(sys.argv[1:])
