"""EX Mode Reflect BARRIER = KH2 Reflega's faceted shell -- notes/kh2-effects.md "Barrier resource audit",
notes/reflect.md section 14, Q-20261016-CODEX-001.

Mat (test247): "the reflect barrier effect is not visible"; then: "the reflect effect has to look as close to the KH2
one as possible". KH2 source = kh2_export/raw/kh2_fifth/original/magic/REFLECT_3.mag (kh2_reflect_mesh.py converts):
  ground guard (block of motion 470) -> KH2 ground dome = model 0, all 128 facets, KH2 fold diagonals 128/128
  air guard    (block of motion 471) -> KH2 faceted sphere model 6 minus pole cap + lowest ring = 160 of 224 facets
each ONE triangle strip <= 384 vertices (v2, test253: v1's 768 / 1,344-vertex lists froze test250-252; see VERTEX
BUDGET below), KH2 program scale (radius 1.98 / 2.07 m) x ROW_SCALE (env BARRIER_SCALE, default 2.5), KH2's cyan
panel texture TEX1 mapped once per hex facet (why not KH2's TEX0: see SHELL_TEX below).
Not reproducible natively (yet): KH2's refraction layers (VSF), the 8-frame destroy fade, the colour animation and
the ring / hull / glow / sparkle layers (decoded timing in notes/kh2-effects.md "Barrier resource audit").

Resources -- all proven unreachable on the current disc (asserted again on every run, see audit()):
  - leaves 51/52 KYOU_WORDS_3/4 (Cloud's Cross-slash marks): only FEPA rows 55/56 point at them, whose only spawners
    are magi 0x47D/0x47C (fx bits 12/13), spawned only by p_se block 58 = motion 10090 (Cloud's Cross-slash), which
    no plya piece (+0x1c/+0x10/+0x1e) and no script parameter reaches. FXSE records of both: none.
  - leaves 10/12/14/49/50 (KYOUGIRI_KENATSU, KYOU_APPEAR, KYOUGIRI, KYOU_WORDS_1/2 = Cross-slash too) have NO FEPA
    row: the only leaf-spawn path is FEPA row -> FUN_088aa4e0 -> FUN_088a68fc -> FUN_088a4d7c(res = row +0x28) ->
    FUN_08941914 (single callers in the decompile), so nothing can instantiate them.
  - MDL 63-70 are drawn only by leaves 49-52, MDL 9/10/12 only by leaves 10/12/14.
Binding (edit classes already proven in game: MDL rewrite = spot33_lightningfx MDL 30, degenerate MDL = its MDL 31,
empty tree = test201 bisect C, loop flag off = spot33_firefx LOOP_OFF, anchored FEPA row = spot33_fx/firefx):
  - layer leaf: node 0 (kind 0xc0 mesh) draws the layer MDL (own key kept, texture key -> NEW TEX 21); its constant
    init data: rotation (90,0,0) -> 0, scale 30 % -> 100 %, offset (0,0,-1.2) -> 0; node 1 hidden (its MDL -> one
    degenerate triangle); tree loop 2 -> 0 (one-shot), duration 76 -> TREE_DUR (nodes live 34 frames = guard 0-36).
  - NEW TEX 21 (key base|0x15) = KH2 TEX1, premultiplied (additive native materials). TEX 9 / TEX 20 and every other
    resource and every other leaf's tree are asserted unchanged.
  - bytes: trees of leaves 49/50 -> empty trees (Lightning's 0-node THUNDER_APPER tree = exactly test201 bisect C),
    MDL 9/10/12/63-67/69 -> one degenerate triangle (trees 10/12/14 stay); pad blob -> exact FEP size.
  - FEPA rows 56 / 55 (index) -> own ids 9120 (ground) / 9121 (air), row 22's fields (kind 0, like spot33_firefx
    TEMPLATE_ROW), magi bits 0, anchored to Sora's 'root' (y > 0 = up, Q005 Q3); ground offset keeps KH2's rim
    height above the floor at any ROW_SCALE (row_pos).
  - Scripts: each guard block (motions 470/471 = blocks 20/21, and spot33_exguard's EX copies 10318/10319 = blocks
    60/67 when present) gets a one-shot op 0x19 [id, 0] at frame 0 with the SAME condition bytes as its EX-only barrier
    sound one-shot (op 0x03 sound 81, cond [0,2,0,0]) -> EX Mode only. Type-7 rows / other blocks untouched.
Re-runnable ("nothing to do" on a second run). Run after spot33_reflect.py.

  python3 -I spot33_barrier.py ISO CLEAN_ISO [--dry]
"""
import collections
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
import kh2_reflect_mesh as M  # noqa: E402

FILE, LIGHT = 'obj/p_sev120.objx', 'obj/p_gst130.objx'
EFFE_SIZE, FEP_SIZE = 848640, 803952
# Texture/UV (fidelity choice, notes/kh2-effects.md "Barrier resource audit"): KH2 draws the shell with TEX0 (a narrow
# iridescent streak) whose UVs it SCROLLS (DrawMdlTs3), plus a screen REFRACTION layer (VSF); a static native mesh can
# do neither, and static KH2 UVs leave nearly every facet on the streak's transparent part (= invisible). So the shell
# uses KH2 TEX1 (the cyan-white panel gradient KH2 puts on its reflected-hit panel shells, models 12/16) mapped once
# per facet: every hex panel gets a bright cyan edge + KH2 cell pattern fading to clear. SHELL_TEX = 0 + uv 'source'
# reproduces KH2's own static mapping (A/B switch).
SHELL_TEX = 1
OPACITY = float(os.environ.get('BARRIER_OPACITY', '0.25'))   # Mat: test265 "more transparent" (0.7), test267 "~60%" (0.4), test268 "75%" (0.25) (additive
#                                                materials: dimmer vertex colour = more see-through; 1.0 = before)
TINT = tuple(c * OPACITY for c in (0.85, 1.0, 1.0))                        # slight cyan-white bias on TEX1 (KH2 layer colour 79,205,181 / 128 is
#                                                for TEX0's warm streak; on TEX1 it would oversaturate)
# VERTEX BUDGET (test250-252 froze with the 768 / 1,344-vertex triangle lists of v1; notes/kh2-effects.md "Vertex
# budget"): every layer is ONE triangle strip (prim 4, like Sora's own MDLs) over the KH2 quad bands, asserted
# <= kh2_reflect_mesh.MAX_VERTS = 384 (largest original triangle list), or per layer up to 454 (largest original
# strip, MDL 57). The test250-253 freezes turned out to be the 22nd texture (TEX 21), not vertex counts (test258).
# POLE CAPS (Mat test262b: "for the barrier there's a hole, can this be covered up?"): KH2's sphere model 6 is OPEN at
# both poles: 32-vertex loops shaped like 16-pointed stars (top: tips r 175 h 313 / notches r 144 h 333 KH2 units,
# ~7 m across at x4; KH2 hides them with other layers). Each loop in 'caps' gets a FAN around a new pole vertex on
# the sphere (shallow cone; a zigzag would fold over the star): 'full' = all 32 loop vertices (64 strip vertices),
# 'tips' = the 16 outer tips only (32; still covers the hole in projection, the notch facets sit just inside).
#   ground: top half of model 6 (4 rings, 128 facets) + full top fan  -> 369 vertices (<= 384), KH2 diagonals 128/128,
#           open only at the floor rim (half dome)
#   air:    model 6 rings -206..333 (5 rings, 160 facets) + full top fan + tips bottom fan (cone to the bottom pole)
#           -> 440 vertices (<= 454 = largest original strip, MDL 57), fully closed; diagonals 128/160
#           (6 rings + caps would be >= 474)
# layer name: KH2 model, program scale, leaf, node-0 MDL, node-1 MDL (hidden), FEPA row index (+ its old id), new
# id, guard motions; row offset = row_pos()
LAYERS = {
    # Mat test261: "the ground dome of reflect should be a half dome" -> the TOP HALF of KH2's full faceted sphere
    # (model 6, bands at/above its equator), equator on the floor (row_pos); + top pole fan (test264)
    'ground dome': dict(model=6, scale=0.56 * 1.08, tint=TINT, min_band_y=0, caps={'top': 'full'}, max_verts=384, leaf=52,
                        mdl=70, hide=69, row=56, old_id=56, id=9120, motions=(470, 10318), ground=True),
    'air sphere': dict(model=6, scale=0.56 * 1.08, tint=TINT, min_band_y=-200, caps={'top': 'full', 'bottom': 'tips'},
                       max_verts=454,
                       leaf=51, mdl=68, hide=67, row=55, old_id=55, id=9121, motions=(471, 10319), ground=False),
}
MAX_VERTS_ANY = 454                            # largest original strip (MDL 57): no layer may exceed it


def layer_mdl(spec, self_key=0, tex_key=0):
    assert spec['max_verts'] <= MAX_VERTS_ANY
    return M.build_strip_mdl(spec['model'], spec['scale'], spec['tint'], self_key, tex_key, spec['min_band_y'],
                             max_verts=spec['max_verts'], caps=spec['caps'])
GUT = (49, 50)                                 # empty trees: exactly the set test201 (bisect C) ran with
SHRINK = (9, 10, 12, 63, 64, 65, 66, 67, 69)   # degenerate MDLs (spot33_lightningfx MDL 31 class); MDL 9/10/12 belong
#                                                to the unspawnable (no FEPA row) leaves 10/12/14, whose trees stay
EXCLUSIVE = {9: {10}, 10: {12}, 12: {14}, 63: {49}, 64: {49}, 65: {50}, 66: {50}, 67: {51}, 68: {51}, 69: {52},
             70: {52}}                         # MDL -> the only leaf drawing it (asserted)
DEAD_MAGI = (0x47C, 0x47D, 0x47E, 0x47F)
DEAD_MOTIONS = {10090}                         # Cloud's Cross-slash (block 58)
EMPTY_SRC = 46                                 # Lightning THUNDER_APPER: 0 nodes
NEW_TEX, KEEP_TEX = 21, (9, 20)
NEW_TEX_ON = os.environ.get('BARRIER_NEW_TEX') == '1'   # default OFF (test253 freeze)
TREE_DUR, NODE_LIFE = 40, 34                   # frames (guard hitbox 0-36, op 0x22 at 38)
NODE_INIT = {0x01: (0.0, 0.0, 0.0),            # rotation deg (was 90,0,0: flat slash mark stood up)
             0x04: (100.0, 100.0, 100.0),      # scale % (was 30)
             0x0e: (0.0, 0.0, 0.0),            # offset (was 0,0,-1.2)
             0x07: (128.0, 128.0, 128.0)}      # RGB, 128 = 1.0 (colour is in the vertex colours)
# KEYFRAMES (test292, notes/kh2-effects.md "Invisible Magnet"): a node draws from its KEY blocks (node +0x24), not from
# the init block NODE_INIT edits (those are no-ops). Vanilla KYOU_WORDS key 0 = rotation (90,0,0) (stands Cloud's
# flat slash mark up), scale 30 %, offset (0,0,-1.2) -> the y-up KH2 dome was drawn lying on its side, off-centre.
# Mat (2026-10-16, "yes"): upright and centred, same size -> key 0 rotation 0, offset 0, scale kept at 30 %
# (visible size = 30 % x ROW_SCALE, what Mat approved), alpha keys / timing untouched.
KEY_ROT_OLD, KEY_OFS_OLD, KEY_SCALE = (90.0, 0.0, 0.0), (0.0, 0.0, -1.2), (30.0, 30.0, 30.0)
KEY_SET = {0x01: (0.0, 0.0, 0.0), 0x0e: (0.0, 0.0, 0.0)}
TEMPLATE_ROW = 22
ROW_SCALE = float(os.environ.get("BARRIER_SCALE", "4.0"))   # Mat: 1.0 too small -> 2.5 -> x2 = 5.0 -> test262 "about 80% of its current size" = 4.0 (1.0 = KH2 size)
ROOT_H, KH2_RIM = 0.85, 0.283                  # root ~0.85 m above the feet (Q005 Q3: 0.63-1.06); KH2 dome rim 0.28 m
#                                                above the floor (element 0 offset 85 cm + model 0 y range)


def row_pos(spec, info):
    """FEPA offset (root space, y > 0 = up, not scaled by the row scale): ground = keep KH2's rim height above the
    floor at any ROW_SCALE; air = centred on root"""
    if not spec['ground']:
        return (0.0, float(os.environ.get('BARRIER_AIR_Y', '0.35')), 0.0)   # chest (root ~ hips); test292
    # Mat test258: at x2.5 the computed 2.55 m put the dome "above me when I'm on the ground" (the engine evidently
    # also scales/centres differently than assumed); test250/251 used the KH2 element offset 0.68 m and sat right.
    # half dome (sphere centre = mesh origin): put the centre at the feet = root height below root (not scaled by the
    # row scale: test258's 2.55 m sat wholly above Sora, test251's 0.68 m around his chest)
    return (0.0, float(os.environ.get('BARRIER_GROUND_Y', str(-ROOT_H))), 0.0)
ATTACH_MODEL, ATTACH_NODE, ATTACH_FLAGS, ATTACH_SLOT = 'p_sev100_1p', 'root', 0x80, '_000A'
EX_SOUND = 81
DEAD_LEAVES = tuple(sorted(set(GUT) | {s['leaf'] for s in LAYERS.values()}))
NEW_IDS = {s['id'] for s in LAYERS.values()}


# ---------------------------------------------------------------- scripts / objx helpers
def chunks(objx):
    return {(e[0], e[1]): objx[e[2]:e[2] + e[3]] for e in E.arc_entries(objx)}


def blocks(t8):
    """-> {block: (offset, mains [(f0, f1, op, var, cond, params)], ones [(frame, op, cond, params)])}"""
    m, = struct.unpack_from('<I', t8, 4)
    out = {}
    for b in range(m):
        o, = struct.unpack_from('<I', t8, 8 + 4 * b)
        e1, = struct.unpack_from('<H', t8, o + 4)
        k, mains, ones = o + 8, [], []
        for _ in range(t8[o + 2]):
            c = t8[k + 5]
            mains.append(struct.unpack_from('<HH', t8, k) + (t8[k + 4], t8[k + 6], bytes(t8[k + 7:k + 12]),
                                                             struct.unpack_from('<%dI' % c, t8, k + 12)))
            k += 12 + 4 * c
        k = o + e1
        for _ in range(t8[o + 3]):
            c = t8[k + 3]
            ones.append((struct.unpack_from('<H', t8, k)[0], t8[k + 2], bytes(t8[k + 4:k + 8]),
                         struct.unpack_from('<%dI' % c, t8, k + 8)))
            k += 8 + 4 * c
        out[b] = (o, mains, ones)
    return out


def motion_rows(t7):
    m7, = struct.unpack_from('<I', t7, 4)
    return [struct.unpack_from('<HHH', t7, 8 + 8 * k) for k in range(m7)]


def guard_blocks(t7, motions):
    """blocks of the guard motion (must exist, one block) + of its EX override motion if spot33_exguard already added
    it (jobp stance 470/471 -> 10318/10319 -> blocks 60/67 = copies of 20/21; exguard re-copies on every run, so this
    step may run before or after it)"""
    out = []
    for k, motion in enumerate(motions):
        bs = {blk for mid, blk, _ in motion_rows(t7) if mid == motion}
        assert len(bs) <= 1 and (bs or k), 'motion %d -> blocks %s' % (motion, bs)
        out += sorted(bs - set(out))
    return out


def audit(objx):
    """the Cross-slash resources must still be dead in THIS objx (notes/kh2-effects.md "Barrier resource audit")"""
    ch = chunks(objx)
    t7, t8, plya, mg = ch[(7, b'p_se')], ch[(8, b'p_se')], ch[(1, b'plya')], ch[(1, b'magi')]
    mot = collections.defaultdict(set)
    for mid, blk, _ in motion_rows(t7):
        mot[blk].add(mid)
    ours = {b: s['id'] for s in LAYERS.values() for b in guard_blocks(t7, s['motions'])}
    spawners = set()
    for b, (_, mains, ones) in blocks(t8).items():
        for f0, f1, op, var, cond, p in mains:
            if op == 0x43 and len(p) > 2 and (p[2] & 0xFFFF) in DEAD_MAGI:
                spawners.add(b)
            assert not (op == 0x66 and p and p[0] in NEW_IDS), 'block %d main op 0x66 uses %d' % (b, p[0])
            assert not set(p) & DEAD_MOTIONS, 'block %d names motion 10090' % b
        for fr, op, cond, p in ones:
            if op == 4 and p and (p[0] & 0xFFFF) in DEAD_MAGI:
                spawners.add(b)
            if op in (0x19, 0x30) and p and p[0] in NEW_IDS:
                assert ours.get(b) == p[0], 'block %d one-shot op %#x uses %d' % (b, op, p[0])
            assert not (op == 0x2f and len(p) > 2 and NEW_IDS & {p[0], p[2]}), 'block %d op 0x2f' % b
            assert not set(p) & DEAD_MOTIONS, 'block %d names motion 10090' % b
    live = [b for b in spawners if mot[b] - DEAD_MOTIONS]
    assert not live, 'Cross-slash magi spawned by blocks %s of live motions %s' % (live, [mot[b] for b in live])
    npl, = struct.unpack_from('<I', plya, 4)
    for k in range(npl):
        r = plya[8 + 116 * k:8 + 116 * (k + 1)]
        ms = {struct.unpack_from('<H', r, a)[0] for a in (0x1c, 0x10, 0x1e)}
        assert not ms & DEAD_MOTIONS, 'plya piece %#x reaches motion 10090' % struct.unpack_from('<H', r)[0]
    cnt, = struct.unpack_from('<I', mg, 8)
    rows = [mg[16 + 204 * i:16 + 204 * (i + 1)] for i in range(cnt)]
    dead_bits = {struct.unpack_from('<H', r, 4)[0] for r in rows if struct.unpack_from('<H', r, 0)[0] in DEAD_MAGI}
    for r in rows:
        mid, bit = struct.unpack_from('<H', r, 0)[0], struct.unpack_from('<H', r, 4)[0]
        assert mid in DEAD_MAGI or bit not in dead_bits, 'magi %#x shares a Cross-slash fx bit %d' % (mid, bit)
    feb = E.mpk_member(objx, 1)
    n, = struct.unpack_from('<I', feb, 12)
    want = {s['row']: s for s in LAYERS.values()}
    for i in range(n):
        rid, res = struct.unpack_from('<II', feb, 16 + 0x104 * i + 0x24)
        if res in DEAD_LEAVES:
            assert i in want and res == want[i]['leaf'] and rid in (want[i]['old_id'], want[i]['id']), \
                'FEPA row %d (id %d) -> leaf %d' % (i, rid, res)
        if rid in NEW_IDS:
            assert i in want and rid == want[i]['id'], 'FEPA row %d already uses id %d' % (i, rid)
    fx = E.mpk_member(objx, 2)
    for s in LAYERS.values():
        recs = [struct.unpack_from('<5I', fx, 16 + s['leaf'] * 0x140 + k * 0x14) for k in range(16)]
        assert not [r for r in recs if r[0]], 'FXSE leaf %d has sound records' % s['leaf']
    return sorted(spawners)


# ---------------------------------------------------------------- FEP
def leaf_users(d):
    from fep_dump import leaves, resources
    L = leaves(d, resources(d))
    users = collections.defaultdict(set)
    for lf in L:
        for n in lf['nodes']:
            for k, i in F.node_resources(d, n['at']):
                users[(k, i)].add(lf['i'])
    return L, users


def tree_views(f):
    """-> {tree index: [blob bytes with offset fields zeroed]} (layout-independent)"""
    zero = collections.defaultdict(set)
    for blob, pos, _, _ in f.ptrs:
        zero[id(blob)].add(pos)
    lst = f.target(f.head(), 0x2c)
    out = {}
    for ti in range(F.u16(f.head().data, 0x1e)):
        parts = []
        for b in T.subgraph(f, f.target(lst, 4 * ti)):
            x = bytearray(b.data)
            for pos in zero[id(b)]:
                x[pos:pos + 4] = bytes(4)
            parts.append(bytes(x).rstrip(b'\0'))          # trailing pad joins the file's last blob
        out[ti] = parts
    return out


def res_views(f):
    return {k: [bytes(b.data[:F.u32(r.data, 8)]) + bytes(r.data[4:12]) for r, b in f.resources(k)]
            for k in ('TEX', 'MDL', 'ANM')}


def degenerate(data):
    """header + draw table of an MDL, one strip of 3 identical vertices (zero area = invisible; lightningfx MDL 31)"""
    rows = [struct.unpack_from('<6I', data, F.u32(data, 0x38) + 0x18 * k) for k in range(F.u32(data, 0x34))]
    first = min(r[5] for r in rows)
    sb = bytearray(data[:first])
    struct.pack_into('<I', sb, 0x34, 1)
    struct.pack_into('<6I', sb, F.u32(sb, 0x38), 4, 0x99, 8, 0, 3, first)
    return bytes(sb + bytes(24))


def is_degenerate(data):
    r = struct.unpack_from('<6I', data, F.u32(data, 0x38))
    return F.u32(data, 0x34) == 1 and r[:5] == (4, 0x99, 8, 0, 3) and len(data) == r[5] + 24


def tree_of(d, leaf):
    lf = F.u32(d, F.u32(d, 0x28) + 4 * leaf)
    return F.u32(d, F.u32(d, 0x2c) + 4 * F.u16(d, lf + 4))


def misaligned_init(d):
    """node init / key blocks (n20_data, n24_data) not at offset 12 mod 16 (vanilla: none; lv.q in the trail draw
    freezes on them, notes/kh2-effects.md test280)"""
    return sum(1 for b in F.Fep(d).blobs if b.kinds & {'n20_data', 'n24_data'} and b.off % 16 != 12)


def edit_fep(sd, ld):
    S = F.Fep(sd)
    assert len(sd) == FEP_SIZE, 'FEP %d B (expected %d)' % (len(sd), FEP_SIZE)
    assert S.own_key_bases() == [S.key_base()], 'run spot33_fx (rekey) first'
    base = S.key_base()
    # Mat test253: froze on Thundaga with the NEW TEX 21 (22nd texture); test258 drawing with the existing TEX 9 key
    # = no freeze at all. So by default the shells use TEX 9 (shared, untouched) and NO texture is added;
    # BARRIER_NEW_TEX=1 restores the TEX 21 path (freezes in game - keep for experiments only).
    tex_key = base | NEW_TEX if NEW_TEX_ON else F.u32(S.resources('TEX')[9][0].data, 4)
    _, users = leaf_users(sd)
    for i, ls in EXCLUSIVE.items():
        assert users[('MDL', i)] <= ls, 'MDL %d is drawn by %s' % (i, users[('MDL', i)])
    for (k, i), us in users.items():
        if us & {s['leaf'] for s in LAYERS.values()}:
            assert k == 'MDL' and i in EXCLUSIVE, 'layer leaves also draw shared %s %d' % (k, i)
    before_trees, before_res = tree_views(S), res_views(S)
    dead_trees = {T.leaf_tree_index(sd, li) for li in DEAD_LEAVES}
    changes = []
    # 1. TEX 21 = KH2 TEX<SHELL_TEX> (premultiplied)
    w, h, idx, pal = M.texture(SHELL_TEX, premultiply=True)
    t = E.make_tex(tex_key, w, h, idx, pal)
    texs = S.resources('TEX')
    if not NEW_TEX_ON:
        assert len(texs) == NEW_TEX, 'TEX count %d: a 22nd texture froze the game (test253)' % len(texs)
    elif len(texs) == NEW_TEX:
        allkeys = {F.u32(r.data, 4) for k in ('TEX', 'MDL', 'ANM') for r, _ in S.resources(k)}
        assert tex_key not in allkeys, 'key %08x already used' % tex_key
        S.add_tex(t, tex_key)
        changes.append('TEX %d %08x added = KH2 Reflega TEX%d %dx%d premultiplied (%d B)' % (NEW_TEX, tex_key, SHELL_TEX, w, h, len(t)))
    else:
        assert len(texs) == NEW_TEX + 1, 'TEX count %d' % len(texs)
        rec, blob = texs[NEW_TEX]
        if F.u32(rec.data, 4) != tex_key or bytes(blob.data[:F.u32(rec.data, 8)]) != t:
            assert F.u32(rec.data, 4) == tex_key and F.u32(rec.data, 8) == len(t), 'TEX 21 is not ours'
            T.put_resource(S, 'TEX', NEW_TEX, t)
            changes.append('TEX %d updated' % NEW_TEX)
    # 2. layer meshes
    for name, s in LAYERS.items():
        rec, blob = S.resources('MDL')[s['mdl']]
        m, info = layer_mdl(s, F.u32(rec.data, 4), tex_key)
        assert info['vertices'] <= s['max_verts'] <= MAX_VERTS_ANY
        if bytes(blob.data[:F.u32(rec.data, 8)]) != m:
            T.put_resource(S, 'MDL', s['mdl'], m)
            changes.append('MDL %d <- %s: KH2 model %d x%.3f, %d/%d facets + caps %s (open loops %d), ONE strip of '
                           '%d vertices (budget %d), diagonals %s, extents %s m (%d B)' % (
                               s['mdl'], name, s['model'], s['scale'], info['quads'],
                               info['quads'] + info['quads_dropped'], info['caps'], info['open_loops'],
                               info['vertices'], s['max_verts'], info['kh2_diagonals'],
                               tuple(round(x, 2) for x in info['extents_m']), len(m)))
    # 3. degenerate MDLs
    for i in SHRINK:
        rec, blob = S.resources('MDL')[i]
        x = bytes(blob.data[:F.u32(rec.data, 8)])
        if not is_degenerate(x):
            T.put_resource(S, 'MDL', i, degenerate(x))
            changes.append('MDL %d shrunk %d -> %d B (degenerate, hidden)' % (i, len(x), len(degenerate(x))))
    # 4. empty trees
    from fep_dump import leaves, resources
    for g in GUT:
        cur = S.write()
        if leaves(cur, resources(cur))[g]['nodes']:
            saved = T.gut(S, cur, g, F.Fep(ld), ld, EMPTY_SRC)
            changes.append('leaf %d tree emptied (-%d B)' % (g, saved))
    # 5. layer trees: one-shot, duration, node life, node-0 init data
    new = bytearray(S.write())
    L, _ = leaf_users(bytes(new))
    for name, s in LAYERS.items():
        tr = tree_of(new, s['leaf'])
        if F.u32(new, tr) != 0 or F.u32(new, tr + 4) != TREE_DUR:
            changes.append('leaf %d tree loop %d -> 0, duration %d -> %d' % (s['leaf'], F.u32(new, tr),
                                                                              F.u32(new, tr + 4), TREE_DUR))
            struct.pack_into('<II', new, tr, 0, TREE_DUR)
        nodes = L[s['leaf']]['nodes']
        mesh = [n for n in nodes if ('MDL', s['mdl']) in F.node_resources(bytes(new), n['at'])]
        assert len(mesh) == 1 and mesh[0]['kind'] == 0xc0, 'leaf %d mesh node' % s['leaf']
        assert all(n['life'] == NODE_LIFE for n in nodes), 'leaf %d node lives %s' % (s['leaf'], [n['life'] for n in nodes])
        comps = {c: o for c, _, o in F.node_components(bytes(new), mesh[0]['at']) if o is not None}
        for c, v in NODE_INIT.items():
            o = comps[c] + 4
            if struct.unpack_from('<3f', new, o) != v:
                changes.append('leaf %d mesh node comp %#x %s -> %s' % (
                    s['leaf'], c, tuple(round(x, 3) for x in struct.unpack_from('<3f', new, o)), v))
                struct.pack_into('<3f', new, o, *v)
        nd = mesh[0]['at']
        tl = F.u32(new, nd + 0x1c)
        tcomp = [F.u16(new, F.u32(new, tl + 4 * j)) for j in range(new[nd + 8])]
        l24 = F.u32(new, nd + 0x24)
        assert new[nd + 0x13] == 3, 'leaf %d: %d key blocks' % (s['leaf'], new[nd + 0x13])
        seen = set()
        for kj in range(new[nd + 0x13]):
            it = F.u32(new, l24 + 4 * kj)
            dat = F.u32(new, it + 8)
            for e in range(F.u32(new, it + 4)):
                tr, off = struct.unpack_from('<HH', new, dat + 8 * e)
                c, o = tcomp[tr], dat + off + 4
                if c == 0x04:
                    assert struct.unpack_from('<3f', new, o) == KEY_SCALE, 'leaf %d key scale' % s['leaf']
                if c in KEY_SET:
                    seen.add(c)
                    cur = struct.unpack_from('<3f', new, o)
                    if cur != KEY_SET[c]:
                        old = KEY_ROT_OLD if c == 0x01 else KEY_OFS_OLD
                        assert all(abs(a - b) < 1e-4 for a, b in zip(cur, old)), 'leaf %d key %d comp %#x %s' % (
                            s['leaf'], kj, c, cur)
                        struct.pack_into('<3f', new, o, *KEY_SET[c])
                        changes.append('leaf %d key %d comp %#x %s -> %s (upright, centred)' % (
                            s['leaf'], kj, c, tuple(round(x, 2) for x in cur), KEY_SET[c]))
        assert seen == set(KEY_SET), 'leaf %d keys lack %s' % (s['leaf'], set(KEY_SET) - seen)
    S = F.Fep(bytes(new))
    if len(S.write()) != FEP_SIZE:
        # earlier pad blobs (lightningfx, previous runs) are absorbed into the file's LAST blob on re-parse; trim its
        # trailing zeros so they can be reused -- the new pad re-creates them, nothing after it is referenced
        last = S.blobs[-1]
        keep = len(bytes(last.data).rstrip(b'\0'))
        keep += -keep % F.DATA_ALIGN
        if keep < len(last.data):
            del last.data[keep:]
        T.pad_to(S, FEP_SIZE)
    out = S.write()
    G = F.Fep(out)
    assert len(out) == FEP_SIZE, 'FEP size %d != %d' % (len(out), FEP_SIZE)
    assert misaligned_init(out) <= misaligned_init(sd), 'node init data alignment got worse (lv.q freeze, test280)'
    after_trees, after_res = tree_views(G), res_views(G)
    for ti, v in before_trees.items():
        if ti not in dead_trees:
            assert after_trees[ti] == v, 'tree %d changed' % ti
    for k in ('TEX', 'MDL', 'ANM'):
        for i, v in enumerate(before_res[k]):
            if not (k == 'MDL' and i in EXCLUSIVE) and not (k == 'TEX' and i == NEW_TEX):
                assert after_res[k][i] == v, '%s %d changed' % (k, i)
    for i in KEEP_TEX:
        assert after_res['TEX'][i] == before_res['TEX'][i], 'TEX %d changed' % i
    _, u2 = leaf_users(out)
    for s in LAYERS.values():
        assert u2[('MDL', s['mdl'])] == {s['leaf']}
    return (None if out == sd else out), changes


# ---------------------------------------------------------------- FEPA / scripts
def edit_fepa(feb):
    feb = bytearray(feb)
    b = 16 + 0x104 * next(i for i in range(struct.unpack_from('<I', feb, 12)[0])
                          if struct.unpack_from('<I', feb, 16 + 0x104 * i + 0x24)[0] == TEMPLATE_ROW)
    msgs = []
    for name, s in LAYERS.items():
        a = 16 + 0x104 * s['row']
        pos = row_pos(s, layer_mdl(s)[1])
        row = bytearray(feb[b:b + 0x104])
        struct.pack_into('<II', row, 0x24, s['id'], s['leaf'])
        struct.pack_into('<I', row, 0x30, 0)
        struct.pack_into('<I', row, 0x3c, 0)
        struct.pack_into('<3f', row, 0x00, *pos)
        struct.pack_into('<3f', row, 0x0c, 0.0, 0.0, 0.0)
        struct.pack_into('<3f', row, 0x18, ROW_SCALE, ROW_SCALE, ROW_SCALE)
        struct.pack_into('<I', row, 0x7c, ATTACH_FLAGS)
        row[0x88:0xa8] = ATTACH_MODEL.encode().ljust(32, b'\0')
        row[0xa8:0xc8] = ATTACH_NODE.encode().ljust(32, b'\0')
        row[0xc8:0xe8] = ATTACH_SLOT.encode().ljust(32, b'\0')
        if row != feb[a:a + 0x104]:
            feb[a:a + 0x104] = row
            msgs.append('FEPA row %d -> id %d, leaf %d (%s) x%.1f at %s %s, magi bits 0 (row %d fields)' % (
                s['row'], s['id'], s['leaf'], name, ROW_SCALE, ATTACH_NODE, pos, TEMPLATE_ROW))
    return (bytes(feb) if msgs else None), msgs


def edit_scripts(objx):
    ents = E.arc_entries(objx)
    i8 = next(i for i, e in enumerate(ents) if e[0] == 8 and e[1] == b'p_se')
    ch = chunks(objx)
    t7, c = ch[(7, b'p_se')], ch[(8, b'p_se')]
    bl = blocks(c)
    n, = struct.unpack_from('<I', c, 4)
    offs = list(struct.unpack_from('<%dI' % n, c, 8))
    changes, msgs = {}, []
    for name, s, b in [(nm, sp, b) for nm, sp in LAYERS.items() for b in guard_blocks(t7, sp['motions'])]:
        o, mains, ones = bl[b]
        size, e1 = struct.unpack_from('<H', c, o + 6)[0], struct.unpack_from('<H', c, o + 4)[0]
        snd = [x for x in ones if x[1] == 0x03 and x[3] and x[3][0] % 100000 == EX_SOUND and x[3][0] // 100000 in (22, 219)]
        assert len(snd) == 1 and snd[0][0] == 0 and snd[0][2][1] == 2, 'block %d: EX sound %d one-shot %s' % (b, EX_SOUND, snd)
        have = [x for x in ones if x[1] == 0x19 and x[3] and x[3][0] in NEW_IDS]
        if have:
            assert have == [(0, 0x19, snd[0][2], (s['id'], 0))], 'block %d: barrier one-shot %s' % (b, have)
            continue
        assert b not in changes and len(ones) < 255
        rec = struct.pack('<HBB4sII', 0, 0x19, 2, snd[0][2], s['id'], 0)
        blob = bytearray(c[o:o + size])
        blob[3] += 1
        struct.pack_into('<HH', blob, 4, e1, size + len(rec))
        changes[b] = bytes(blob) + rec
        msgs.append('p_se block %d (motions %s, %s): + one-shot f0 op 0x19 [%d, 0] cond %s (EX only, = sound 81)' % (
            b, [m for m, bb, _ in motion_rows(t7) if bb == b], name, s['id'], snd[0][2].hex()))
    if not changes:
        return None, []
    nc = bytearray(c)
    for b in sorted(changes, key=lambda b: offs[b], reverse=True):
        z, = struct.unpack_from('<H', c, offs[b] + 6)
        nc[offs[b]:offs[b] + z] = changes[b]
    grow = {b: len(changes[b]) - struct.unpack_from('<H', c, offs[b] + 6)[0] for b in changes}
    struct.pack_into('<%dI' % n, nc, 8, *[x + sum(g for b, g in grow.items() if offs[b] < x) for x in offs])
    nb = blocks(bytes(nc))
    for b in range(n):
        if b not in changes:
            assert nb[b][1:] == bl[b][1:], 'block %d changed' % b
        else:
            assert nb[b][1] == bl[b][1] and nb[b][2][:-1] == bl[b][2], 'block %d: more than one record changed' % b
    from spot33_combos import rebuild_arc
    return rebuild_arc(objx, {i8: bytes(nc)}), msgs


def main(a):
    iso, clean = a[0], a[1]
    objx = E.load_objx(iso, FILE)
    ld = E.split(E.load_objx(clean, LIGHT))[3]
    sp = audit(objx)
    print('audit OK: Cross-slash magi 0x47C-0x47F only in block(s) %s (motion 10090, no piece reaches it); leaves %s '
          'and MDL %s free' % (sp, list(DEAD_LEAVES), sorted(EXCLUSIVE)))
    ei, effe, name, sd = E.split(objx)
    assert len(effe) == EFFE_SIZE, 'effe %d B' % len(effe)
    changes = []
    new, ch = edit_fep(sd, ld)
    changes += ch
    if new is not None:
        objx = E.join(objx, ei, effe, name, new)
    from spot33_fx import patch_member
    feb, ch = edit_fepa(E.mpk_member(objx, 1))
    changes += ch
    if feb is not None:
        objx = patch_member(objx, 1, feb)
    scr, ch = edit_scripts(objx)
    changes += ch
    if scr is not None:
        objx = scr
    eff = next(e for e in E.arc_entries(objx) if e[1] == b'effe')
    assert eff[3] == EFFE_SIZE, 'effe %d B != %d' % (eff[3], EFFE_SIZE)
    audit(objx)
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
