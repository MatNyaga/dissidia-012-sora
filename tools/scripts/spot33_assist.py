"""Sora (owner 33) as an ASSIST character -- notes/assist.md.

Owner 33 was Aerith's slot, and Aerith is an assist-only character in 012: picking owner 33 as an assist loaded HER
files (model, Cure/Holy moves, voice). This step gives owner 33 a real Sora assist, built the same way the game's own
assist files are built (Cloud's p_sev100_a.objx is a plain subset of p_sev100.objx):

  obj/p_sev120_a.objx          <- built from Sora's own obj/p_sev120.objx (current disc state):
                                  script blocks (byte copies of Sora's KH2 blocks; sound ids stay 219000xx/219100xx,
                                  the engine adds +50000 for assist rows), type-7 motion table renumbered, only the
                                  plya pieces / atkp hits the 4 assist actions use, comb = 4 actions, own snd_ bank
                                  (h14 219500, only the slots the blocks + kept effects play), hit shapes, brat,
                                  text (banners), wind; effe = Cloud's stock assist effe re-IDed to Aerith's free
                                  assist FEP id 0x51280000 (textures 0xa80128NN), FXSE rows taken from Sora's own
                                  rows (KH2 hit sound) for the hit-mark/trail leaves, other rows silent.
  obj/P_SEV120_{1,2,3}P_A.gmo  <- Sora's model (all 3 costumes are the same file) with only the 17 motions the blocks
                                  play (motion index = block number), idle thinned, EX-only / Cloud-leftover textures
                                  stubbed like Cloud's assist model does (texture block keeps only its name arg).
  voice/EN/battle/voice_P_SEV120_a_00.scd <- Sora's voice bank, h14 219600, only the slots the blocks + chrp use.
  main.bin objentry.bin        owner-33 kind-8 rows (P_SEV120_xP_A): bytes +2..+0x24 <- Cloud's kind-8 rows
                                  (type id 340 -> 6 = Cloud skeleton, like Sora's kind-0 rows).
  main.bin assist.bin          owner-33 row only: action list 933-936 -> 1020/321/326/328 (= what eqaa 396 already
                                  enables through ablt 0x2100-0x2103), records/flags = Cloud's melee records.

  EBOOT (3 words)              the game drops assist owner 33 (= Aerith) from a loadout unless "Aerith unlocked"
                                  (FUN_0885c304(DAT_089d4e14)) is true -- test301: Sora picked as assist, battle setup
                                  assist owner -1, no assist object, gauge frozen. The 0x21 compare immediates in
                                  FUN_088f9bb0 (battle setup), FUN_088f6a58 (other setup copy) and FUN_0892905c
                                  (friend-card owner check) -> 0x7f (no owner), so owner 33 is never dropped.

Assist moves (KH2 animations already in Sora's model):
  ground Bravery (1020): Slide Dash -> swing -> swing -> Upper Slash launcher   (pieces 0x5c1 0x5bf 0x7d8 0x5c2)
  air Bravery    (321) : KH2 air combo, 3 swings                                (0x5c5 0x5c6 0x5cc)
  ground HP      (326) : Explosion (Sora's "Explosion alone" block 10308)       (0x5c8)
  air HP         (328) : Aerial Finish, 5 sweeps                                (0x5ca)

  python3 -I spot33_assist.py ISO [--dry] [--out DIR]   (--out: also write the built files to DIR)
Re-runnable: every target must be Aerith's stock bytes (sha256) or a Sora assist built by this script; anything else
stops before writing. Never run on dumps/ULUS10566.iso.
"""
import hashlib
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

OWNER, CLOUD = 33, 13
SORA_OBJX, SORA_GMO = 'obj/p_sev120.objx', 'obj/P_SEV120_1P.gmo'
SORA_VOICE = 'voice/EN/battle/voice_P_SEV120_00.scd'
CLOUD_A = 'obj/p_sev100_a.objx'
A_OBJX, A_VOICE = 'obj/p_sev120_a.objx', 'voice/EN/battle/voice_P_SEV120_a_00.scd'
A_GMOS = ['obj/P_SEV120_1P_A.gmo', 'obj/P_SEV120_2P_A.gmo', 'obj/P_SEV120_3P_A.gmo']
STOCK = {   # clean disc (Aerith's assist files, Cloud's assist objx)
    A_OBJX: '65b602d7b0515e2895954faf319fce07e830fbc2adca928d3340a2d33320dfa0',
    A_VOICE: '023e0b0d26ca349f8ed50662d630adfbabbb984db7445adf9d61afa37e6703fa',
    A_GMOS[0]: '2ebb3963caf7405e6a864061d3d6397e89e1e7ed9925b3f8fb699e981ac5ef60',
    A_GMOS[1]: 'ff16e8e6ef9d4aa77872ef15f2076ec5c12f2817dbc053ef98f30f5ba53656d4',
    A_GMOS[2]: '436c9c5ba48945c677e02c82e5c86ffc98de51b2a481a696fed187efa29e424c',
    CLOUD_A: '11473cddab8cc83bae956fda07f86d3adefb6632559debbe98c0b4d729c4931d',
}
SND_MAIN, SND_A, VOICE_MAIN, VOICE_A = 219000, 219500, 219100, 219600
FEP_OLD, FEP_NEW = 0x511C0000, 0x51280000          # Cloud's assist FEP id -> Aerith's (owner 33) assist FEP id
CLOUD_A_SND = 22500

# --- what the assist plays -------------------------------------------------------------------------------------
# assist block k = GMO motion k: (main GMO motion name, main block, [(motion id, variant), ...])
# generic part mirrors Cloud's assist table (ids + variants); attack part = Sora's own blocks
MOTIONS = [
    ('_000A', 0, [(0x1, 0), (0xa, 0)]),                      # idle
    ('_021A', 3, [(0x65, 0)]),                               # fall
    ('_022A', 4, [(0x66, 0)]),                               # land
    ('_043A', 7, [(0x385, 0), (0x38f, 0)]),
    ('_170A', 22, [(0x12c, 1)]),
    ('_210A', 25, [(0x1f4, 1), (0x1fe, 1), (0x226, 1), (0x230, 1)]),     # hurt
    ('_211A', 26, [(0x1f5, 1), (0x1ff, 1), (0x227, 1), (0x231, 1)]),
    ('_500A', 37, [(0xf0, 0)]),                              # dash in
    ('_610A', 47, [(0x271a, 0)]),                            # Slide Dash (KH2 656)
    ('_601A', 45, [(0x2711, 1)]),                            # ground swing
    ('_640A', 55, [(0x2742, 1)]),                            # ground swing (LAND_NEAR4)
    ('_611A', 48, [(0x271b, 0)]),                            # Upper Slash launcher (KH2 648)
    ('_620A', 50, [(0x2724, 0)]),                            # air combo 1 (KH2 724)
    ('_620B', 51, [(0x2725, 0)]),                            # air combo 2 (KH2 728)
    ('_621A', 52, [(0x2726, 0)]),                            # air combo 3 (KH2 732)
    ('_728A', 95, [(0x2841, 0)]),                            # Explosion alone (10308's block) under LF1's motion id
    ('_726A', 93, [(0x2842, 0)]),                            # Aerial Finish (KH2 776)
]
THIN = {'_000A': 2, '_043A': 2, '_170A': 2, '_210A': 2, '_211A': 2, '_500A': 2}   # rarely-seen generic motions: every 2nd key (size budget)
# one-shot op 0x19 = spawn FEPA id; Explosion's 57/68 (Cloud Omnislash bursts) are not in the assist effe -> dropped
DROP_ONESHOTS = {95: {(0x19, 57), (0x19, 68)}}
ACTIONS = [(1020, [0x5c1, 0x5bf, 0x7d8, 0x5c2]),           # ground Bravery
           (321, [0x5c5, 0x5c6, 0x5cc]),                    # air Bravery
           (326, [0x5c8]),                                  # ground HP
           (328, [0x5ca])]                                  # air HP
ABLT_IDS = {0x2100: 1020, 0x2101: 321, 0x2102: 326, 0x2103: 328}     # eqaa 396 equips these (read-only check)
EQAA_ID = 396
EXTRA_HITS = [0x38, 0x39, 0x3a, 0x16c, 0x1a3, 0x1a4, 0x2aa, 0x30a, 0x349, 0x354, 0x763]   # generic rows (cheap)
STUB_TEX = [0, 1, 2, 5, 9]          # file15 file17 file19 (Cloud leftovers), texture-1 + ultima_weapon (EX weapon)
VOICE_EXTRA = [1, 4, 41]         # engine voices (KO 4; Cloud's assist bank keeps 1 and 41); EX lines 30/42 left out (assists never enter EX Mode)
FXSE_KEEP = ('HTM', 'KYOU_HTM', 'FAST_LOCUS', 'FAST_GLOW', 'SWORD_LOCUS', 'SWORD_LIGHT')   # hit marks + trails


def sha(b):
    return hashlib.sha256(b).hexdigest()


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


# ------------------------------------------------------------------------------------------------ ARC helpers
def arc_entries(d):
    assert d[:4] == b'ARC\x01', 'not an ARC'
    return [list(struct.unpack_from('<I4sII', d, 16 + k * 16)) for k in range(u32(d, 4))]


def chunk(d, tag, typ=None):
    hits = [d[o:o + s] for t, g, o, s in arc_entries(d) if g == tag and (typ is None or t == typ)]
    assert len(hits) == 1, (tag, typ, len(hits))
    return hits[0]


def rebuild(template, new):
    """template ARC with chunk k's bytes replaced by new[k] (16-aligned chunks, like the game files)"""
    from spot33_combos import rebuild_arc
    return rebuild_arc(template, new)


# ------------------------------------------------------------------------------------------------ script blocks
def parse_blocks(t8):
    n = u32(t8, 4)
    out = []
    for b in range(n):
        o = u32(t8, 8 + 4 * b)
        idx, nm, no, e1, size = struct.unpack_from('<HBBHH', t8, o)
        assert idx == b, 'block %d header says %d' % (b, idx)
        k, mains = o + 8, []
        for _ in range(nm):
            c = t8[k + 5]
            mains.append(bytes(t8[k:k + 12 + 4 * c]))
            k += 12 + 4 * c
        assert k == o + e1, 'block %d: mains end %x, e1 %x' % (b, k - o, e1)
        ones = []
        for _ in range(no):
            c = t8[k + 3]
            ones.append(bytes(t8[k:k + 8 + 4 * c]))
            k += 8 + 4 * c
        assert k == o + size, 'block %d size' % b
        out.append((mains, ones))
    return out


def enc_block(idx, mains, ones):
    body = b''.join(mains)
    e1 = 8 + len(body)
    tail = b''.join(ones)
    size = e1 + len(tail)
    assert size % 4 == 0 and len(mains) < 256 and len(ones) < 256
    return struct.pack('<HBBHH', idx, len(mains), len(ones), e1, size) + body + tail


def enc_t8(blocks):
    head = struct.pack('<II', 3, len(blocks))
    offs, body, at = [], b'', 8 + 4 * len(blocks)
    for b in blocks:
        offs.append(at + len(body))
        body += b
    return head + struct.pack('<%dI' % len(blocks), *offs) + body


def events(mains, ones):
    """-> [(op, params)] of both lists"""
    out = []
    for m in mains:
        out.append(('M', m[4], struct.unpack_from('<%dI' % m[5], m, 12)))
    for e in ones:
        out.append(('1', e[2], struct.unpack_from('<%dI' % e[3], e, 8)))
    return out


# ------------------------------------------------------------------------------------------------ objx tables
def rows(b, start, size):
    return [bytes(b[start + i * size:start + (i + 1) * size]) for i in range(u32(b, 4))]


def comb_parse(cb):
    n = u16(cb, 2)
    out = []
    for o in struct.unpack_from('<%dI' % n, cb, 4):
        aid, m, alt, par = struct.unpack_from('<HHhh', cb, o)
        out.append((aid, [struct.unpack_from('<HHhBB', cb, o + 8 + 8 * k) for k in range(m)]))
    return out


def comb_build(actions):
    head = struct.pack('<HH', 6, len(actions))
    ents = []
    for aid, pieces in actions:
        ents.append(struct.pack('<HHhh', aid, len(pieces), -1, -1)
                    + b''.join(struct.pack('<HHhBB', p, 0, -1, 0, 0) for p in pieces))
    offs, at = [], 4 + 4 * len(actions)
    for e in ents:
        offs.append(at)
        at += len(e)
    return head + struct.pack('<%dI' % len(ents), *offs) + b''.join(ents)


# ------------------------------------------------------------------------------------------------ sound banks
EMPTY_ENTRY = bytes([0, 0, 0x20, 0] + [0] * 14 + [0xff, 0, 0xca, 0x5f] + [0] * 10)


def bank_base(h):
    h10, h12, h14 = struct.unpack_from('<HHI', h, 0x10)
    return h14 * 100 if (h12 == 0 and h14 > 599) else h10 * 10000 + h12 * 100 - 10000


def bank_subset(bank, keep, new_id):
    """same slot count/numbering; only KEEP slots carry data (shared data stays shared); header id -> new_id"""
    assert bank[:4] == b'SSCF'
    n = u32(bank, 12)
    out_e, data, placed = [], bytearray(), {}
    hdr_end = 0x20 + 32 * n
    for i in range(n):
        e = bytearray(bank[0x20 + 32 * i:0x40 + 32 * i])
        off, size = u32(e, 4), u32(e, 8)
        if i in keep and size:
            blob = bytes(bank[off:off + size])      # identical sample data is stored once (the game banks do this)
            if blob not in placed:
                placed[blob] = hdr_end + len(data)
                data += blob
                data += b'\0' * (-len(data) % 16)
            struct.pack_into('<I', e, 4, placed[blob])
            out_e.append(bytes(e))
        else:
            out_e.append(EMPTY_ENTRY)
    head = bytearray(bank[:0x20])
    struct.pack_into('<I', head, 8, hdr_end + len(data))
    struct.pack_into('<HHI', head, 0x10, 1, 0, new_id)
    out = bytes(head) + b''.join(out_e) + bytes(data)
    assert bank_base(out) == new_id * 100
    return out


def bank_slots_used(bank):
    n = u32(bank, 12)
    return [i for i in range(n) if u32(bank, 0x28 + 32 * i)]


# ------------------------------------------------------------------------------------------------ effe
def build_effe(cloud_effe, sora_effe):
    import fep as F
    import mpk
    mem = list(mpk.entries(cloud_effe))
    names = [m[0] for m in mem]
    assert names == ['p_sev100_a.fep', 'p_sev100_a.feb', 'p_sev100_a.fxseb'], names
    fep = bytearray(cloud_effe[mem[0][1]:mem[0][1] + mem[0][2]])
    assert u32(fep, 0x10) & 0xFFFC0000 == FEP_OLD, hex(u32(fep, 0x10))
    f0 = F.Fep(bytes(fep))
    data_start = min(b.off for k in ('TEX', 'MDL', 'ANM') for _, b in f0.resources(k))
    nref = 0
    for o in range(0, data_start - 3, 4):
        v = u32(fep, o)
        if v & 0xFFFC0000 == FEP_OLD and v & 0x3FF == 0:
            struct.pack_into('<I', fep, o, (v & 0x3FFFF) | FEP_NEW)
            nref += 1
    # own TEX/MDL/ANM keys 0xa8011cNN -> 0xa80128NN (base of the new id). fep.Fep.rekey() walks the global-resource
    # records too (their data pointers land on unrelated blobs -> garbage counts), so use the exact key prefix over
    # the whole file instead; texture pixel areas must hold none of them.
    old_base, new_base = 0xA8011C00, 0xA8012800
    pix = [(b.off + 0x30, b.off + len(b.data)) for r, b in f0.resources('TEX') if u32(r.data, 4) & 0xFFFFFC00 == old_base]
    nkey = 0
    for o in range(0, len(fep) - 3, 4):
        v = u32(fep, o)
        if v & 0xFFFFFC00 == old_base:
            assert not any(a <= o < b for a, b in pix), 'key pattern inside texture pixels at %#x' % o
            struct.pack_into('<I', fep, o, new_base | (v & 0x3FF))
            nkey += 1
    f = F.Fep(bytes(fep))
    assert F.u32(f.head().data, 0x10) & 0xFFFC0000 == FEP_NEW and f.key_base() == new_base
    assert sorted({u32(r.data, 4) & 0xFFFFFC00 for k in ('TEX', 'MDL', 'ANM') for r, _ in f.resources(k)
                   if u32(r.data, 4) >> 28 != 0xf}) == [new_base]
    new_fep = bytes(fep)
    assert f.write() == new_fep, 'FEP does not round-trip'
    feb = cloud_effe[mem[1][1]:mem[1][1] + mem[1][2]]
    assert struct.pack('<I', FEP_OLD) not in feb, 'FEPA table holds a FEP id'
    # FXSE: row i = leaf i. Rows of leaves we keep take Sora's own row (same leaf name in Sora's main FEP), the rest
    # are silenced (those leaves -- Cross-slash / Braver -- are never spawned by Sora's assist scripts).
    fx = bytearray(cloud_effe[mem[2][1]:mem[2][1] + mem[2][2]])
    smem = list(mpk.entries(sora_effe))
    sfep = sora_effe[smem[0][1]:smem[0][1] + smem[0][2]]
    sfx = sora_effe[smem[2][1]:smem[2][1] + smem[2][2]]
    a_names, s_names = leaf_names(bytes(new_fep)), leaf_names(sfep)
    nrow = u32(fx, 12)
    assert nrow == len(a_names) and u32(sfx, 12) == len(s_names)
    slots = set()
    for i, nm in enumerate(a_names):
        suffix = nm.split('P_SEV100_', 1)[1].rsplit('_LEAF', 1)[0]
        at = 16 + i * 0x140
        if suffix in FXSE_KEEP:
            j = next(k for k, s in enumerate(s_names) if s.split('P_SEV100_', 1)[-1].rsplit('_LEAF', 1)[0] == suffix)
            row = bytearray(sfx[16 + j * 0x140:16 + (j + 1) * 0x140])
            for o in range(0, 0x140 - 7, 4):
                base, slot = struct.unpack_from('<II', row, o)
                if base == SND_MAIN * 100 and slot < 200:
                    struct.pack_into('<I', row, o, SND_A * 100)
                    slots.add(slot)
            fx[at:at + 0x140] = row
        else:
            fx[at:at + 0x140] = bytes(0x140)
    for o in range(16, len(fx) - 7, 4):
        base, = struct.unpack_from('<I', fx, o)
        assert base != CLOUD_A_SND * 100, 'Cloud sound row left in FXSE'
    out = bytearray(cloud_effe)
    import mpk as M
    out = M.replace(bytes(out), names[0], new_fep)
    out = M.replace(out, names[2], bytes(fx))
    return out, slots, nref, nkey


def leaf_names(fep):
    """leaf index -> debug name (names list +0x44 -> {u32 n, ptr} -> n x {key, len, ptr}; matched by key bits 0x1fc00)"""
    import fep as F
    nn, np_ = F.u32(fep, F.u32(fep, 0x44)), F.u32(fep, F.u32(fep, 0x44) + 4)
    bykey = {}
    for k in range(nn):
        key, ln, sp = struct.unpack_from('<III', fep, np_ + 12 * k)
        bykey[key & 0x1fc00] = fep[sp:sp + ln].split(b'\0')[0].decode('latin1')
    lst = F.u32(fep, 0x28)
    return [bykey[F.u32(fep, F.u32(fep, lst + 4 * i)) & 0x1fc00] for i in range(F.u16(fep, 0x1c))]


# ------------------------------------------------------------------------------------------------ build objx
def build_objx(sora, cloud_a):
    t7 = chunk(sora, b'p_se', 7)
    mot = {}
    for k in range(u32(t7, 4)):
        mid, blk, var, _ = struct.unpack_from('<HHHH', t7, 8 + 8 * k)
        mot[mid] = (blk, var)
    blocks = parse_blocks(chunk(sora, b'p_se', 8))
    # attack rows must still point at the blocks we copy (guards Sora's main table against later renumbering)
    for name, mb, ids in MOTIONS[8:]:
        for mid, var in ids:
            if mid == 0x2841:
                assert mot[0x2844] == (mb, 0), 'Explosion-alone block moved: %s' % (mot[0x2844],)
                assert mot[0x2841][0] != mb
            else:
                assert mot[mid] == (mb, var), 'motion %#x -> %s, expected (%d, %d)' % (mid, mot[mid], mb, var)
    new_blocks, rows7 = [], []
    snd, voice, hits = set(), set(), set()
    for k, (name, mb, ids) in enumerate(MOTIONS):
        mains, ones = blocks[mb]
        drop = DROP_ONESHOTS.get(mb, set())
        kept = []
        for e in ones:
            op, n = e[2], e[3]
            p0 = struct.unpack_from('<I', e, 8)[0] if n else None
            if (op, p0) in drop:
                continue
            kept.append(e)
        assert len(ones) - len(kept) == len(drop), 'block %d: drop list does not match' % mb
        for kind, op, ps in events(mains, kept):
            if kind == '1':                         # one-shots: sounds / voices / spawns
                if op == 0x03:
                    snd.add(ps[0])
                elif op == 0x11:
                    snd.add(ps[1])
                elif op == 0x15:
                    voice.add(ps[0])
                assert op not in (0x04, 0x19, 0x66), 'block %d spawns magi/effect op %#x %s' % (mb, op, ps)
            elif op in (0x00, 0x20, 0x43) and ps:   # hitboxes
                hits.add(ps[0])
        new_blocks.append(enc_block(k, mains, kept))
        rows7 += [(mid, k, var) for mid, var in ids]
    rows7.sort()
    t7_new = struct.pack('<II', 2, len(rows7)) + b''.join(struct.pack('<HHHH', m, b, v, 0) for m, b, v in rows7)
    t8_new = enc_t8(new_blocks)
    # plya: the action pieces, Sora's rows unchanged, in Sora's file order
    pb = chunk(sora, b'plya')
    want = {p for _, ps in ACTIONS for p in ps}
    prow = [r for r in rows(pb, 8, 116) if u16(r, 0) in want]
    assert {u16(r, 0) for r in prow} == want, 'plya pieces missing'
    have7 = {m for m, _, _ in rows7}
    for r in prow:
        for off in (0x1c, 0x1e, 0x10):
            m = u16(r, off)
            assert m == 0xffff or m in have7, 'piece %#x +%#x motion %#x has no block' % (u16(r, 0), off, m)
    plya_new = struct.pack('<II', u32(pb, 0), len(prow)) + b''.join(prow)
    # atkp: hits the blocks use + generic rows, sorted by id (binary-searched)
    ab = chunk(sora, b'atkp')
    arow = {u32(r, 0): r for r in rows(ab, 8, 68)}
    need = (hits | set(EXTRA_HITS))
    missing = sorted(h for h in hits if h not in arow)
    assert not missing, 'hits not in Sora atkp: %s' % [hex(h) for h in missing]
    atkp_new = struct.pack('<II', u32(ab, 0), len([h for h in need if h in arow])) + \
        b''.join(arow[h] for h in sorted(need) if h in arow)
    comb_new = comb_build(ACTIONS)
    # sound banks
    lo, hi = SND_MAIN * 100, SND_MAIN * 100 + 1000
    snd_slots = {s - lo for s in snd if lo <= s < hi}
    voice_slots = {s - VOICE_MAIN * 100 for s in voice if VOICE_MAIN * 100 <= s < VOICE_MAIN * 100 + 1000}
    effe, fx_slots, nref, nkey = build_effe(chunk(cloud_a, b'effe'), chunk(sora, b'effe'))
    sbank = chunk(sora, b'snd_')
    assert bank_base(sbank) == SND_MAIN * 100, 'Sora snd_ bank is not 219000 (run spot33_soundids first)'
    keep = snd_slots | fx_slots
    have = set(bank_slots_used(sbank))
    assert keep <= have | {9}, 'sound slots without data: %s' % sorted(keep - have)
    snd_new = bank_subset(sbank, keep, SND_A)
    # assemble in Cloud's assist container (same chunk list/order/types)
    ents = arc_entries(cloud_a)
    tags = [(t, g) for t, g, _, _ in ents]
    assert tags == [(7, b'p_se'), (8, b'p_se'), (5, b'p_se'), (6, b'p_se'), (4, b'effe'), (14, b'snd_'), (1, b'plya'),
                    (1, b'comb'), (1, b'atkp'), (1, b'magi'), (1, b'brat'), (1, b'text'), (3, b'wind')], tags
    new = {0: t7_new, 1: t8_new, 2: chunk(sora, b'p_se', 5), 3: chunk(sora, b'p_se', 6), 4: effe, 5: snd_new,
           6: plya_new, 7: comb_new, 8: atkp_new, 9: chunk(cloud_a, b'magi'), 10: chunk(sora, b'brat'),
           11: chunk(sora, b'text'), 12: chunk(sora, b'wind')}
    out = rebuild(cloud_a, new)
    info = dict(blocks=len(new_blocks), t7=len(rows7), plya=len(prow), atkp=u32(atkp_new, 4), snd_slots=sorted(keep),
                voice_slots=sorted(voice_slots), fep_refs=nref, fep_keys=nkey, size=len(out), snd=len(snd_new),
                effe=len(effe))
    return out, voice_slots, info


# ------------------------------------------------------------------------------------------------ build GMO
def gmo_blocks(d, start, end):
    o = start
    while o < end:
        t, hs, size = struct.unpack_from('<HHI', d, o)
        assert size >= 8 and o + size <= end, 'bad GMO block at %#x' % o
        yield o, t, hs, size
        o += size


def gmo_name(d, o, hs):
    return d[o + 16:o + hs].split(b'\0')[0].decode('latin1')


def build_gmo(g):
    from gmo_thin import thin_motion
    assert g[:12] == b'OMG.00.1PSP\0'
    fo = 0x10
    t, fhs, fsize = struct.unpack_from('<HHI', g, fo)
    assert t == 2 and fo + fsize == len(g)
    models = list(gmo_blocks(g, fo + fhs, fo + fsize))
    assert [gmo_name(g, o, hs) for o, t, hs, s in models] == ['_000A', 'model-0'], 'unexpected GMO layout'
    # animation model: args + bones, then the chosen motions in assist order
    mo, _, mhs, ms = models[0]
    kids = list(gmo_blocks(g, mo + mhs, mo + ms))
    mot = {gmo_name(g, o, hs): (o, s) for o, t, hs, s in kids if t == 0x0B}
    first = next(i for i, k in enumerate(kids) if k[1] == 0x0B)
    assert all(k[1] == 0x0B for k in kids[first:]), 'motions are not the last children'
    body = b''.join(g[o:o + s] for o, t, hs, s in kids[:first])
    main_order = [gmo_name(g, o, hs) for o, t, hs, s in kids[first:]]
    for name, mb, _ in MOTIONS:
        assert main_order[mb] == name, 'main GMO motion %d is %s, expected %s' % (mb, main_order[mb], name)
        o, s = mot[name]
        if name in THIN:
            blk, _, _ = thin_motion(g, o, s, THIN[name])
        else:
            blk = g[o:o + s]
        body += blk
    m0 = bytearray(g[mo:mo + mhs]) + body
    struct.pack_into('<I', m0, 4, len(m0))
    # geometry model: stub EX-only / leftover textures (keep header + 0x8012 file-name arg, like Cloud's assist)
    go, _, ghs, gs = models[1]
    gkids = list(gmo_blocks(g, go + ghs, go + gs))
    texs = [k for k in gkids if k[1] == 0x0A]
    assert len(texs) == 10, len(texs)
    m1 = bytearray(g[go:go + ghs])
    ti = 0
    for o, t, hs, s in gkids:
        blk = g[o:o + s]
        if t == 0x0A:
            if ti in STUB_TEX:
                at, arg_t, arg_s = o + hs, *struct.unpack_from('<HHI', g, o + hs)[::2]
                assert arg_t == 0x8012, 'texture %d: first arg %#x' % (ti, arg_t)
                blk = bytearray(g[o:o + hs] + g[at:at + arg_s])
                struct.pack_into('<I', blk, 4, len(blk))
                blk = bytes(blk)
            ti += 1
        m1 += blk
    struct.pack_into('<I', m1, 4, len(m1))
    fb = bytearray(g[fo:fo + fhs]) + m0 + m1
    struct.pack_into('<I', fb, 4, len(fb))
    out = bytes(g[:fo]) + bytes(fb)
    return out


# ------------------------------------------------------------------------------------------------ main.bin tables
def objentry_patch(ob):
    ob = bytearray(ob)
    n = u32(ob, 4)
    rowsx = [(8 + 68 * i, ob[8 + 68 * i:8 + 68 * (i + 1)]) for i in range(n)]
    cloud = {r[7]: bytes(r) for at, r in rowsx if r[6] == CLOUD and r[8] == 8 and r[0x24:0x34].startswith(b'P_SEV100_')
             and r[0x24:0x34].split(b'\0')[0].endswith(b'P_A')}
    done, already = [], []
    for at, r in rowsx:
        if r[6] != OWNER or r[8] != 8:
            continue
        nm = r[0x24:0x34].split(b'\0')[0]
        assert nm in (b'P_SEV120_1P_A', b'P_SEV120_2P_A', b'P_SEV120_3P_A'), nm
        assert r[0x34:0x44].split(b'\0')[0] == b'p_sev120_a'
        want = cloud[r[7]][2:0x24]
        want = want[:4] + bytes([OWNER, r[7]]) + want[6:]
        aerith = struct.pack('<HH', 0x154, 0xffff) + bytes([OWNER, r[7], 8, 0]) + b'\xff' * 26
        cur = bytes(r[2:0x24])
        if cur == want:
            already.append(nm.decode())
            continue
        assert cur == aerith, '%s row is neither Aerith\'s nor ours: %s' % (nm, cur.hex())
        ob[at + 2:at + 0x24] = want
        done.append(nm.decode())
    print('objentry kind-8 rows: changed %s, already %s' % (done, already))
    return bytes(ob)


def assist_patch(ab):
    ab = bytearray(ab)
    assert u32(ab, 0) == 0x15
    n = u32(ab, 4)
    at = {u32(ab, 8 + 104 * i): 8 + 104 * i for i in range(n)}
    lo = 8 + 104 * n
    lst = lo + 4
    r33, r13 = at[OWNER], at[CLOUD]
    idx = [u16(ab, r33 + 8 + 24 * k) for k in range(4)]
    assert idx == [122, 123, 124, 125], idx
    assert [u16(ab, lst + 2 * i) for i in idx] in ([933, 934, 935, 936], [a for a, _ in ACTIONS]), 'action list'
    # header: u32 owner, u16 eqaa id, u8 flags (bit0 Brv / bit1 HP: choose record by target state), u8 0xff
    assert u16(ab, r33 + 4) == EQAA_ID
    new_head = struct.pack('<IHBB', OWNER, EQAA_ID, ab[r13 + 6], 0xff)
    recs = b''
    for k in range(4):
        c = bytearray(ab[r13 + 8 + 24 * k:r13 + 32 + 24 * k])
        struct.pack_into('<H', c, 0, idx[k])        # keep owner 33's global record index
        struct.pack_into('<H', c, 6, 0xffff)        # no extra id (Aerith had none either)
        recs += bytes(c)
    old = bytes(ab[r33:r33 + 104])
    stock_ok = old[:8] == struct.pack('<IHBB', OWNER, EQAA_ID, 0, 0xff)
    new_row = new_head + recs
    if old == new_row and [u16(ab, lst + 2 * i) for i in idx] == [a for a, _ in ACTIONS]:
        print('assist.bin owner 33: already Sora\'s')
        return bytes(ab)
    assert stock_ok or old == new_row, 'assist.bin owner-33 row is neither stock nor ours'
    ab[r33:r33 + 104] = new_row
    for i, (aid, _) in zip(idx, ACTIONS):
        struct.pack_into('<H', ab, lst + 2 * i, aid)
    print('assist.bin owner 33: flags %d, records = Cloud\'s melee records (flags %s), actions 933-936 -> %s'
          % (ab[r13 + 6], [ab[r13 + 12 + 24 * k] for k in range(4)], [a for a, _ in ACTIONS]))
    return bytes(ab)


def check_system(sysbin):
    """read-only: eqaa 396 = owner 33 idx 0..3 in the 4 assist categories; ablt 0x2100-0x2103 = our actions"""
    from spot33_save import arc_split
    _, chs = arc_split(sysbin)
    c = {ch[1]: ch[2] for ch in chs}
    e = c[b'eqaa']
    row = next(e[8 + 94 * i:8 + 94 * (i + 1)] for i in range(u32(e, 4)) if struct.unpack_from('<h', e, 8 + 94 * i)[0]
               == EQAA_ID)
    assert struct.unpack_from('<h', row, 2)[0] == OWNER and (row[4], row[16], row[28], row[31]) == (0, 1, 2, 3), \
        'eqaa %d changed: %s' % (EQAA_ID, row[:36].hex())
    a = c[b'ablt']
    acts = {}
    for i in range(u32(a, 8)):
        r = a[16 + 40 * i:56 + 40 * i]
        acts[r[1] << 8 | r[0]] = u16(r, 12)
    for aid, act in ABLT_IDS.items():
        assert acts.get(aid) == act, 'ablt %#x = %s, expected %d' % (aid, acts.get(aid), act)
    print('system.bin (read only): eqaa %d -> ablt 0x2100-0x2103 = %s OK' % (EQAA_ID, list(ABLT_IDS.values())))


# ------------------------------------------------------------------------------------------------ EBOOT
EBOOT_ISO = 560 * 0x800                 # PSP_GAME/SYSDIR/EBOOT.BIN, plain ELF since test20 (spot33_save.py)
# (va, original word, new word): "ori aX,zero,0x21" (owner 33) -> "ori aX,zero,0x7f" (no owner has that number)
EBOOT_WORDS = [(0x088F9CA4, 0x34070021, 0x3407007F),    # FUN_088f9bb0: loadout+0xb8 == 33 && !aerith -> 0xff
               (0x088F6C04, 0x34060021, 0x3406007F),    # FUN_088f6a58: same check, other setup path
               (0x08929060, 0x34050021, 0x3405007F)]    # FUN_0892905c: owner 33 -> "locked" (2) unless aerith


def eboot_part(iso, dry):
    todo = []
    with open(iso, 'rb') as f:
        assert f.seek(EBOOT_ISO) is not None and f.read(4) == b'\x7fELF', 'EBOOT is not the plain ELF'
        for va, old, new in EBOOT_WORDS:
            f.seek(EBOOT_ISO + 0x1018 + va - 0x8804040)
            cur = u32(f.read(4), 0)
            assert cur in (old, new), 'EBOOT %08x = %08x, expected %08x or %08x - stop' % (va, cur, old, new)
            if cur == old:
                todo.append((va, new))
    print('EBOOT owner-33 assist drop checks: %s' % ('%d word(s) to patch' % len(todo) if todo else 'already patched'))
    if dry or not todo:
        return todo
    with open(iso, 'r+b') as f:
        for va, new in todo:
            f.seek(EBOOT_ISO + 0x1018 + va - 0x8804040)
            f.write(struct.pack('<I', new))
            print('  EBOOT %08x <- %08x' % (va, new))
    return todo


# ------------------------------------------------------------------------------------------------ ISO
def put(iso, path, data):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, os.path.basename(path))
        open(p, 'wb').write(data)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p], check=True,
                           capture_output=True, text=True)
        print('  ' + r.stdout.strip())


def is_ours_objx(d):
    try:
        cb = chunk(d, b'comb')
        e = chunk(d, b'effe')
        import mpk
        m = list(mpk.entries(e))
        fep_id = u32(e, m[0][1] + 0x10)
        return [a for a, _ in comb_parse(cb)] == [a for a, _ in ACTIONS] and fep_id & 0xFFFC0000 == FEP_NEW
    except Exception:
        return False


def main(argv):
    if not argv or argv[0].startswith('-'):
        sys.exit(__doc__)
    iso, dry = argv[0], '--dry' in argv
    outdir = argv[argv.index('--out') + 1] if '--out' in argv else None
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the clean dump'
    import mpk
    from comb_patch import pkg_offset, read_at, use_iso
    use_iso(iso)
    with open(iso, 'rb') as f:
        def get(p):
            st, sz = pkg_offset(p)
            return read_at(f, st, sz)
        sora, sgmo, svoice, cloud_a = get(SORA_OBJX), get(SORA_GMO), get(SORA_VOICE), get(CLOUD_A)
        cur = {p: get(p) for p in [A_OBJX, A_VOICE] + A_GMOS}
        main_bin = get('general_archive/main/main.bin')
    assert sha(cloud_a) == STOCK[CLOUD_A], 'Cloud\'s assist objx is not stock - stop'
    mem = {n: main_bin[o:o + s] for n, o, s in mpk.entries(main_bin)}
    check_system(mem['system.bin'])
    # build
    objx, voice_slots, info = build_objx(sora, cloud_a)
    gmo = build_gmo(sgmo)
    vbank = svoice
    assert bank_base(vbank) == VOICE_MAIN * 100, 'Sora voice bank is not 219100'
    vkeep = set(voice_slots) | set(VOICE_EXTRA)
    vkeep &= set(bank_slots_used(vbank))
    voice = bank_subset(vbank, vkeep, VOICE_A)
    print('assist objx: %d B (Cloud\'s assist 309,532; vanilla max 391,296): %d blocks, %d motion rows, %d pieces, '
          '%d hits; snd_ %d B slots %s; effe %d B (FEP id refs %d, keys %d)'
          % (info['size'], info['blocks'], info['t7'], info['plya'], info['atkp'], info['snd'], info['snd_slots'],
             info['effe'], info['fep_refs'], info['fep_keys']))
    print('assist GMO: %d B (Cloud\'s 580,748; vanilla max 775,856), %d motions' % (len(gmo), len(MOTIONS)))
    print('assist voice: %d B (Cloud\'s 58,864), slots %s' % (len(voice), sorted(vkeep)))
    # targets: stock or ours
    plan = []
    targets = [(A_OBJX, objx, is_ours_objx), (A_VOICE, voice, lambda d: bank_base(d) == VOICE_A * 100)] + \
              [(p, gmo, lambda d: d[:12] == b'OMG.00.1PSP\0' and len(d) == len(gmo)) for p in A_GMOS]
    for path, new, ours in targets:
        c = cur[path]
        if c == new:
            print('%s: already built (no change)' % path)
            continue
        assert sha(c) == STOCK[path] or ours(c), '%s is neither Aerith\'s stock file nor a Sora assist - stop' % path
        plan.append((path, new, 'stock' if sha(c) == STOCK[path] else 'older Sora build'))
    new_ob = objentry_patch(mem['objentry.bin'])
    new_ab = assist_patch(mem['assist.bin'])
    new_main = main_bin
    if new_ob != mem['objentry.bin']:
        new_main = mpk.replace(new_main, 'objentry.bin', new_ob)
    if new_ab != mem['assist.bin']:
        new_main = mpk.replace(new_main, 'assist.bin', new_ab)
    for n, o, s in mpk.entries(new_main):          # nothing else in main.bin moved or changed
        if n not in ('objentry.bin', 'assist.bin'):
            assert new_main[o:o + s] == mem[n], n
    if new_main != main_bin:
        assert len(new_main) == len(main_bin)
        plan.append(('general_archive/main/main.bin', new_main, 'objentry + assist.bin'))
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        for name, data in (('p_sev120_a.objx', objx), ('P_SEV120_1P_A.gmo', gmo), ('voice_P_SEV120_a_00.scd', voice),
                           ('objentry.bin', new_ob), ('assist.bin', new_ab)):
            open(os.path.join(outdir, name), 'wb').write(data)
        print('built files written to', outdir)
    for path, new, why in plan:
        print('%s: %s -> %d B (%s)' % (path, 'would write' if dry else 'write', len(new), why))
    ework = eboot_part(iso, True)
    if not plan and not ework:
        print('nothing to do')
    if dry:
        print('--dry: nothing written')
        return
    for path, new, _ in plan:
        put(iso, path, new)
    eboot_part(iso, False)


if __name__ == '__main__':
    main(sys.argv[1:])
