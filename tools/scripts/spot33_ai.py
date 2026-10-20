"""CPU Sora = a real AI opponent (Mat: "a power house ... take advantage of all his tools"). Data only, no code.
Research: notes/cpu-ai.md.

Why CPU Sora was passive:
  1. owner 33 has no row in the GLOBAL AI owner table (battle_non_residing.bin, ARC chunk `brai` type 1 = "seco",
     tables 0x1a8 owners / 0x1c0 owner x brain-x matrix). FUN_08aacc28 returns brain-x unchanged for an unknown
     owner, brain sets 0..28 do not exist (seco 0x18 starts at 29) -> situation = -2 -> the main attack picker
     FUN_08a7c1dc rejects every query, and most tactic lookups (guard/dodge/approach tables) fail too.
  2. his `brat` (AI attack table, objx) is Cloud's: no 1020 (Combo Plus), no HP magic 1021-1026, Cloud's weights.
  3. owner 33 has no `acab` row (system.bin): the CPU auto-equip gets no "always equip" list (Ground/Midair
     Evasion + Block, Aerial Recovery, Air Dash, Free Air Dash, Multi Air Slide, lock-ons ...), so CPU Sora may lack them.

What this writes (owner 33 only; every other owner's rows stay byte-identical):
  A. obj/p_sev120.objx `brat`: Sora's own table, every KH2 starter / chain / spell, 4 strength levels
     (level = personality +0x130: Max/Strong 0 ... Minimal 3), strong weights on the long combos + Guard Break.
  B. battle_non_residing.bin brai seco: owner 33 appended to 0x1a8 (+ a never-matching pad -1, keeps 4-byte
     alignment) and two matrix rows = copies of Cloud's (owner 13) row -> same brain sets as every normal fighter.
  D. objx plya: real AI reach windows of the HP starters (Fire 0-2.5 m, Explosion 0-3, Aerial Finish 0-6,
     Blizzaga 0-12, Thundaga 0-20; was Cloud's 0-25 / 4-7 / 5-8) -> no more Fire from across the stage.
  E. (v3) seco: Sora's own brain sets 200..207 (copies of styles 29..36, no 'ease off when ahead' step, earlier
     HP decision once he leads in Bravery); owner 33's row maps to them. Other owners' rows byte-identical.
  F. (v4) seco: Sora's brain sets use own EX rows (EX Mode the moment the gauge is full) and own reaction-gate rows
     (the two personality 'slip-up' behaviours off). Appended rows, other owners byte-identical.
  C. system.bin acab: entry (33 -> Cloud's list, shared data, +8 B); ablt rows of owner 33: +32..39 CPU
     auto-equip priority (8 AI styles) so the CPU equips his best moves first.

  python3 -I spot33_ai.py ISO [--dry]
Re-runnable: each part checks the stock form (sha256) or its own finished form, else stops without writing.
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

OWNER, TEMPLATE_OWNER = 33, 13
OBJX, BNR = 'obj/p_sev120.objx', 'battle_non_residing.bin'
BRAT_ID = 6                      # = objentry +2 of P_SEV120_* rows (FUN_08810678 matches it)
STOCK_BRAT = '48126120c4fa8497718bb69a35fa1bfd7b6478be6d7d2f426c644076ff4c7a56'   # Cloud's 636 B brat
STOCK_SECO = '5066eb141b2b3736554fe3d9e5348cfd7c498ee1c80f0b0ea5fb3d0a9dc75bcb'   # clean brai #1 (52,944 B)
OLD_OWN_BRAT = {'1161723e92029e897d0ba5924ab5b6528a8cb8364a613b6e5882b8fd88239c4a',   # v1 = test276-ai
                '0d71a76b7c961fc847c1d3cb9490940926b5311004a51373d13bd94da3693c56',   # v2 = test282-ai2
                '8a74e52be430e1fbc9862e9b53844f7e52f2f1bf7ac91274ac0493e33548fea1'}   # v3 = test291-aihard
# v3 (Mat: "even harder"): Sora's OWN brain sets = copies of the standard styles 29..36 as ids 200..207 with
#  - no 'ease off' step (brain-set row byte +5: personality walks this many steps down its chain, e.g. Max 10 -> 9,
#    in one fight state) -> he keeps the chosen CPU strength all fight;
#  - HP-decision threshold (byte +1 -> seco 0xb4: go for HP once Bravery >= lerp(lo, hi) x base Bravery,
#    FUN_08aaf138 / FUN_08aaef94) capped at row 3 (1.95-2.25 x base): styles that hoarded Bravery up to 3.5x or
#    never went HP (row 6 = 100x) now cash in once he has a Bravery lead. Rows 0-2 (lower) are kept.
OWN_SET0, STD_SETS, HP_CAP = 200, list(range(29, 37)), 3
# v4 (Mat: "harder still"): Sora's brain sets also point at OWN copies (id + 100) of
#  - the spacing/EX rows (seco 0xc0, row byte +2): +0x10 mask = when to press EX Mode (command 0x12) once the gauge
#    is full (FUN_08a9b0ac -> FUN_08aaf6a0: 1 attacking, 2 FUN_08a83f80, 4 far, 8 near, 0x10 ALWAYS). Own rows add
#    0x10 -> EX Mode the moment the gauge is full;
#  - the reaction-gate rows (seco 0xcc, row byte +3): +4 / +0x10 switch on two 'slip-up' behaviours whose chance is
#    personality +0x24 / +0x164 (1.0 / 0.8 at the weakest, 0 / 0.1 at Max; FUN_08a9ceb8 = drop the combo midway,
#    FUN_08a9d25c). Own rows = 0 -> no slip-ups at any strength.
OWN_ROW, EX_ALWAYS = 100, 0x10
# D. AI reach window of the HP starters (plya +0x24 min dist, +0x28 max dist, +0x2c/+0x30 height). Only the CPU uses
# it: these pieces are starters with flag 0x2 (player skips the distance check). The picker rolls a move first, then
# walks in / backs off until the foe is inside this window (FUN_08a66f8c), and the in-combo Square press only takes
# moves whose window holds the foe (range mode 1). test276 (Mat): Fire (KH2 flame flurry, body sphere r 2.5) was
# cast from far away because Cloud's Meteorain rows say 0-25 m. piece: (name, stock window, Sora's real reach)
REACH = {0x1010: ('HP_FIRAGA',     (0.0, 25.0, -10.0, 5.0), (0.0, 2.5, -2.0, 2.5)),   # flames around Sora
         0x1013: ('HP_A_FIRAGA',   (0.0, 25.0, -10.0, 5.0), (0.0, 2.5, -2.5, 2.5)),
         0x1011: ('HP_THUNDAGA',   (0.0, 25.0, -10.0, 5.0), (0.0, 20.0, -10.0, 5.0)), # bolts at the foe's feet
         0x1014: ('HP_A_THUNDAGA', (0.0, 25.0, -10.0, 5.0), (0.0, 20.0, -10.0, 5.0)),
         0x1012: ('HP_BLIZZAGA',   (0.0, 25.0, -10.0, 5.0), (0.0, 12.0, -4.0, 4.0)),  # shards from Sora, mid range
         0x1015: ('HP_A_BLIZZAGA', (0.0, 25.0, -10.0, 5.0), (0.0, 12.0, -5.0, 5.0)),
         0x5c8:  ('LAND_FINISH1',  (4.0, 7.0, -1.0, 1.0),   (0.0, 3.0, -1.5, 1.5)),   # Explosion: spin r1.3@1.8 m + orbs r 2.5
         0x5ca:  ('AIR_FINISH1',   (5.0, 8.0, -8.0, 8.0),   (0.0, 6.0, -4.0, 4.0))}   # Aerial Finish: 5 front sweeps
PAD_OWNER = -1                   # never equals an owner byte

# weight byte -> value (seco table 0x15c): 0 .2, 1 .4, 2 .7, 3 NEVER, 4 .01, 8 .04, 9 .44, 10 1.04, 11 1.0,
# 12 2.0, 13 3.5, 14 1.0, 15 2.0, 16 3.5. Situations 0-2 come from the HP grid, 3-4 from the Bravery grid, 5 =
# special callers (chases). The CPU first decides Bravery vs HP (FUN_08aaef94), then rolls among that class.
VALID = {0, 1, 2, 3, 4, 8, 9, 10, 11, 12, 13, 14, 15, 16}
# action: (name, level-0 key per situation 0..5). Chains (combo > HP finisher) count as HP actions for the CPU.
BRAT = [
    (1020, 'Combo Plus (Ground Rave)',  [13, 13, 13, 13, 13, 13]),
    (316,  'Slide Dash (Sky Rave)',     [13, 13, 13, 13, 13, 13]),     # 19-hit Sky Rave
    (327,  'Dodge Slash (Spin Leap)',   [12, 12, 12, 12, 12, 12]),
    (321,  'Air Combo',                 [13, 13, 13, 13, 13, 13]),
    (324,  'Aerial Spiral',             [12, 12, 12, 12, 12, 12]),
    (325,  'Aerial Dive',               [12, 12, 12, 12, 12, 12]),
    (314,  'Combo Plus > Guard Break',  [13, 13, 13, 13, 13, 13]),
    (317,  'Slide Dash > Guard Break',  [13, 13, 13, 13, 13, 13]),
    (315,  'Combo Plus > Upper Slash',  [13, 13, 13, 13, 13, 13]),
    (313,  'Slide Dash > Upper Slash',  [12, 12, 13, 12, 13, 12]),
    (320,  'Dodge Slash > Explosion',   [13, 13, 13, 13, 13, 13]),
    (326,  'Explosion',                 [12, 12, 13, 12, 13, 12]),
    (1021, 'Firaga',                    [11, 11, 11, 11, 11, 11]),     # close only (REACH), walks in first
    (1022, 'Thundaga',                  [12, 12, 12, 12, 12, 12]),
    (1023, 'Blizzaga',                  [11, 11, 11, 11, 11, 11]),
    (927,  'Air Combo > Magnet Burst',  [13, 13, 13, 13, 13, 13]),
    (318,  'Air Combo > Horizontal Slash', [13, 13, 13, 13, 13, 13]),
    (319,  'Air Combo > Aerial Sweep',  [12, 12, 13, 12, 13, 12]),
    (323,  'Air Combo > Retaliating Slash', [12, 12, 12, 12, 12, 12]),
    (328,  'Aerial Finish',             [12, 12, 13, 12, 13, 12]),
    (1024, 'Aerial Firaga',             [11, 11, 11, 11, 11, 11]),
    (1025, 'Aerial Thundaga',           [12, 12, 12, 12, 12, 12]),
    (1026, 'Aerial Blizzaga',           [11, 11, 11, 11, 11, 11]),
]


def levels(k):
    """level 0 (Max/Strong) .. 3 (Minimal): weaker CPUs roll more evenly, but still use every move"""
    return [k, k, 12 if k == 13 else 11, 11 if k == 13 else 2]      # v3: Strong = Max weights


# ablt +32..39 = CPU auto-equip priority per AI style 0..7 (FUN_088b5254 reads row +0x20 + style); same for all styles
PREF = {0x00: 3, 0x01: 3, 0x04: 3, 0x0f: 3, 0x08: 2, 0x0c: 2,          # starters
        0x02: 3, 0x11: 3, 0x12: 3, 0x13: 1,                            # ground HP: Explosion Firaga Thundaga Blizzaga
        0x03: 3, 0x14: 2, 0x15: 3, 0x16: 1,                            # air HP: Aerial Finish / spells
        0x09: 3, 0x0a: 3, 0x10: 3, 0x0b: 3, 0x05: 2, 0x07: 2, 0x0d: 2, 0x0e: 1, 0x06: 1}   # chains
OUR_PREF_VALUES = set(PREF.values())

# seco layout (FUN_08aad8f8): ("seco", f32 4.36) then tables (manager offset, row size); 'raw' = 0x74 bytes, no count
FIELDS = [(0x18, 0x10), (0x24, 8), (0x30, 0x28), (0x3c, 4), (0x48, 4), (0x54, 4), (0x60, 4), (0x6c, 4), (0x78, 4),
          (0x84, 4), (0x90, 4), (0x9c, 4), (0xa8, 4), (0xb4, 0x14), (0xc0, 0x18), (0xcc, 0x14), (0xd8, 0xc),
          (0xe4, 0x24), (0xf0, 8), (0xfc, 4), (0x108, 8), (0x114, 4), (0x120, 8), (0x12c, 8), (0x138, 4),
          (0x144, 8), (0x150, 0x188), (0x15c, 8), (0x168, 0xc), (0x174, 4), (0x180, 4), ('raw', 0x74), (0x190, 8),
          (0x19c, 0x10), (0x1a8, 2), (0x1b4, 2), (0x1c0, 2), (0x1cc, 0x1c), (0x1d8, 0x10), (0x1e4, 8),
          (0x1f0, 0x28), (0x1fc, 8), (0x208, 0xc), (0x214, 8), (0x220, 8), (0x22c, 0xc), (0x238, 8), (0x244, 8),
          (0x250, 0xc), (0x25c, 8), (0x268, 0x10), (0x274, 4), (0x280, 4), (0x28c, 4), (0x298, 0xc), (0x2a4, 4),
          (0x2b0, 4), (0x2bc, 4)]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def arc_entries(d):
    assert d[:4] == b'ARC\x01', 'not an ARC'
    n, = struct.unpack_from('<I', d, 4)
    return [list(struct.unpack_from('<I4sII', d, 16 + k * 16)) for k in range(n)]


# ------------------------------------------------------------------------------------------------- A. brat (objx)
def brat_build():
    out, weights = [], bytearray()
    for aid, name, keys in BRAT:
        assert len(keys) == 6 and all(k in VALID for k in keys), name
        pairs = []
        for k in keys:
            pairs.append((len(weights), 4))
            weights += bytes(levels(k))
        out.append(struct.pack('<I', aid) + b''.join(struct.pack('<HH', *p) for p in pairs))
    head = b'atta' + struct.pack('<fIII', 1.02, 1, BRAT_ID, len(out))
    return head + b''.join(out) + struct.pack('<I', len(weights)) + bytes(weights)


def comb_ids(cb):
    _, n = struct.unpack_from('<HH', cb, 0)
    return [struct.unpack_from('<H', cb, o)[0] for o in struct.unpack_from('<%dI' % n, cb, 4)]


def objx_part(d):
    from spot33_combos import rebuild_arc
    ch = arc_entries(d)
    ib = next(k for k, c in enumerate(ch) if c[1] == b'brat')
    cb = next(d[c[2]:c[2] + c[3]] for c in ch if c[1] == b'comb')
    cur = d[ch[ib][2]:ch[ib][2] + ch[ib][3]]
    new = brat_build()
    ids = set(comb_ids(cb))
    missing = [a for a, _, _ in BRAT if a not in ids]
    assert not missing, 'brat actions not in Sora comb: %s' % missing
    uncovered = sorted(ids - {a for a, _, _ in BRAT})
    print('brat: %d actions, %d B; comb actions left out (no ablt row / Cloud leftovers): %s'
          % (len(BRAT), len(new), uncovered))
    repl = {}
    if cur == new:
        print('brat: already Sora\'s table')
    else:
        assert sha(cur) == STOCK_BRAT or sha(cur) in OLD_OWN_BRAT, \
            'brat is neither Cloud\'s stock table nor ours (sha %s) - stop' % sha(cur)
        print('brat: %s -> Sora v3' % ('Cloud stock' if sha(cur) == STOCK_BRAT else 'an older Sora table'))
        for aid, name, keys in BRAT:
            print('  %4d %-30s L0 %s' % (aid, name, keys))
        repl[ib] = new
    ip = next(k for k, c in enumerate(ch) if c[1] == b'plya')
    pl = reach_patch(d[ch[ip][2]:ch[ip][2] + ch[ip][3]], cb)
    if pl != d[ch[ip][2]:ch[ip][2] + ch[ip][3]]:
        repl[ip] = pl
    return rebuild_arc(d, repl) if repl else d


def reach_patch(pl, cb):
    pl = bytearray(pl)
    _, n = struct.unpack_from('<II', pl, 0)
    at = {struct.unpack_from('<H', pl, 8 + i * 116)[0]: 8 + i * 116 for i in range(n)}
    # every edited piece must be a starter used only as step 0 (so no follow-up distance check sees it)
    _, nc = struct.unpack_from('<HH', cb, 0)
    for o in struct.unpack_from('<%dI' % nc, cb, 4):
        k, = struct.unpack_from('<H', cb, o + 2)
        for j in range(1, k):
            assert struct.unpack_from('<H', cb, o + 8 + j * 8)[0] not in REACH, 'REACH piece used as a follow-up'
    done = []
    for pid, (name, stock, want) in REACH.items():
        o = at[pid]
        nm = pl[o + 0x64:o + 0x74].split(b'\0')[0].decode()
        fl, = struct.unpack_from('<I', pl, o + 0x18)
        assert nm == name and pl[o + 3] == 0 and fl & 2, 'plya %x is %s role %d flags %x' % (pid, nm, pl[o + 3], fl)
        cur = tuple(round(x, 4) for x in struct.unpack_from('<4f', pl, o + 0x24))
        if cur == want:
            continue
        assert cur == stock, 'plya %x reach %s is neither stock %s nor ours' % (pid, cur, stock)
        struct.pack_into('<4f', pl, o + 0x24, *want)
        done.append('%s %g-%g m' % (name, want[0], want[1]))
    print('plya CPU reach: %s' % (', '.join(done) if done else 'already set'))
    return bytes(pl)


# ------------------------------------------------------------------------------------------ B. seco (battle file)
def seco_parse(b):
    assert b[:4] == b'seco', 'not seco'
    o, tabs = 8, []
    for f, sz in FIELDS:
        if f == 'raw':
            tabs.append([f, sz, None, b[o:o + sz]])
            o += sz
            continue
        n, = struct.unpack_from('<I', b, o)
        tabs.append([f, sz, n, b[o + 4:o + 4 + n * sz]])
        o += 4 + n * sz
    return b[:8], tabs, o


def seco_join(head, tabs):
    out = bytearray(head)
    for f, sz, n, data in tabs:
        assert len(out) % 4 == 0, 'table 0x%x would be misaligned' % f
        if f == 'raw':
            out += data
        else:
            assert len(data) == n * sz
            out += struct.pack('<I', n) + data
    return bytes(out)


def rows(t):
    return [t[3][i * t[1]:(i + 1) * t[1]] for i in range(t[2])]


def set_rows(t, rs):
    t[2], t[3] = len(rs), b''.join(rs)


def seco_strip(head, tabs):
    """remove our additions (v1/v2: owner 33 + pad; v3: + own brain sets) to compare with stock"""
    T = {t[0]: t for t in tabs}
    own = list(struct.unpack('<%dh' % T[0x1a8][2], T[0x1a8][3]))
    ncol = T[0x1b4][2]
    if OWNER not in own:
        return False
    k = own.index(OWNER)
    assert k == len(own) - 2 and own[-1] == PAD_OWNER, 'owner 33 row is not where this script puts it'
    T[0x1a8][2] -= 2
    T[0x1a8][3] = T[0x1a8][3][:-4]
    T[0x1c0][2] -= 2 * ncol
    T[0x1c0][3] = T[0x1c0][3][:-4 * ncol]
    own_ids = set(range(OWN_SET0, OWN_SET0 + len(STD_SETS)))
    bs = rows(T[0x18])
    mine = [r for r in bs if struct.unpack_from('<h', r)[0] in own_ids]
    if mine:
        assert bs[-len(mine):] == mine, 'own brain sets not at the end of 0x18'
        set_rows(T[0x18], bs[:-len(mine)])
        n24 = sum(struct.unpack_from('<h', r, 0xe)[0] for r in mine)
        first = min(struct.unpack_from('<h', r, 0xc)[0] for r in mine)
        assert first == T[0x24][2] - n24, 'own 0x24 rows not at the end'
        set_rows(T[0x24], rows(T[0x24])[:-n24])
        f0 = rows(T[0xf0])
        assert all(struct.unpack_from('<i', r)[0] in own_ids for r in f0[-len(mine):]), '0xf0 tail'
        set_rows(T[0xf0], f0[:-len(mine)])
        grp = rows(T[0x2a4])
        st, cn = struct.unpack('<hh', grp[-1])
        ids = [struct.unpack('<i', r)[0] for r in rows(T[0x2b0])]
        assert set(ids[st:st + cn]) == own_ids and st + cn == len(ids), 'own style group not at the end'
        set_rows(T[0x2a4], grp[:-1])
        set_rows(T[0x2b0], rows(T[0x2b0])[:st])
    for tb in (0xc0, 0xcc):                        # v4 own rows (ids >= OWN_ROW) at the table end
        rs = rows(T[tb])
        k = len(rs)
        while k and struct.unpack_from('<i', rs[k - 1])[0] >= OWN_ROW:
            k -= 1
        assert all(struct.unpack_from('<i', r)[0] < OWN_ROW for r in rs[:k]), 'own row not at the end of 0x%x' % tb
        set_rows(T[tb], rs[:k])
    return True


def own_brain_sets(T):
    """append ids 200..207 = copies of 29..36 (0x18 row, 0x24 rows: no step down, HP threshold capped; 0xf0 key
    sharing the stock 0xfc rows; a style-switch group). Returns {stock id: own id}."""
    bs = {struct.unpack_from('<h', r)[0]: r for r in rows(T[0x18])}
    t24 = rows(T[0x24])
    f0 = {struct.unpack_from('<i', r)[0]: r for r in rows(T[0xf0])}
    ids_b4 = {struct.unpack_from('<i', r)[0] for r in rows(T[0xb4])}
    new18, new24, newf0, remap = [], [], [], {}
    for k, sid in enumerate(STD_SETS):
        nid = OWN_SET0 + k
        assert nid not in bs and nid not in f0, 'brain set id %d taken' % nid
        r = bytearray(bs[sid])
        st, cn = struct.unpack_from('<hh', r, 0xc)
        struct.pack_into('<hh', r, 0, nid, struct.unpack_from('<h', r, 2)[0])
        struct.pack_into('<h', r, 0xc, len(t24) + len(new24))
        new18.append(bytes(r))
        for row in t24[st:st + cn]:
            row = bytearray(row)
            if row[1] > HP_CAP and row[1] <= 6:
                row[1] = HP_CAP
            assert row[1] in ids_b4
            row[5] = 0
            row[2] += OWN_ROW                      # own spacing/EX row
            row[3] += OWN_ROW                      # own reaction-gate row
            new24.append(bytes(row))
        fr = bytearray(f0[sid])
        struct.pack_into('<i', fr, 0, nid)
        newf0.append(bytes(fr))
        remap[sid] = nid
    newc0, newcc = [], []
    used_b = sorted({r[2] - OWN_ROW for r in new24})
    used_c = sorted({r[3] - OWN_ROW for r in new24})
    c0 = {struct.unpack_from('<i', r)[0]: r for r in rows(T[0xc0])}
    cc = {struct.unpack_from('<i', r)[0]: r for r in rows(T[0xcc])}
    for i in used_b:
        r = bytearray(c0[i])
        assert i + OWN_ROW not in c0 and i + OWN_ROW < 128
        struct.pack_into('<i', r, 0, i + OWN_ROW)
        struct.pack_into('<I', r, 0x10, struct.unpack_from('<I', r, 0x10)[0] | EX_ALWAYS)
        newc0.append(bytes(r))
    for i in used_c:
        r = bytearray(cc[i])
        assert i + OWN_ROW not in cc and i + OWN_ROW < 128
        struct.pack_into('<i', r, 0, i + OWN_ROW)
        struct.pack_into('<i', r, 4, 0)
        struct.pack_into('<i', r, 0x10, 0)
        newcc.append(bytes(r))
    set_rows(T[0xc0], rows(T[0xc0]) + newc0)
    set_rows(T[0xcc], rows(T[0xcc]) + newcc)
    print('seco: own EX rows %s (EX Mode as soon as the gauge is full), own reaction rows %s (no slip-ups)'
          % ([i + OWN_ROW for i in used_b], [i + OWN_ROW for i in used_c]))
    gstart = T[0x2b0][2]
    set_rows(T[0x18], rows(T[0x18]) + new18)
    set_rows(T[0x24], t24 + new24)
    set_rows(T[0xf0], rows(T[0xf0]) + newf0)
    set_rows(T[0x2a4], rows(T[0x2a4]) + [struct.pack('<hh', gstart, len(STD_SETS))])
    set_rows(T[0x2b0], rows(T[0x2b0]) + [struct.pack('<i', OWN_SET0 + k) for k in range(len(STD_SETS))])
    return remap


def seco_patch(b):
    head, tabs, end = seco_parse(b)
    assert end <= len(b)
    had = seco_strip(head, tabs)
    stock = seco_join(head, tabs)
    assert sha(stock) == STOCK_SECO, 'seco differs from the stock table (sha %s) - stop' % sha(stock)
    T = {t[0]: t for t in tabs}
    own = list(struct.unpack('<%dh' % T[0x1a8][2], T[0x1a8][3]))
    ncol = T[0x1b4][2]
    assert T[0x1c0][2] == len(own) * ncol, 'matrix size'
    k = own.index(TEMPLATE_OWNER)
    row = T[0x1c0][3][k * ncol * 2:(k + 1) * ncol * 2]
    remap = own_brain_sets(T)
    row33 = struct.pack('<%dh' % ncol, *[remap.get(v, v) for v in struct.unpack('<%dh' % ncol, row)])
    T[0x1a8][2] += 2
    T[0x1a8][3] += struct.pack('<hh', OWNER, PAD_OWNER)
    T[0x1c0][2] += 2 * ncol
    T[0x1c0][3] += row33 + row
    row = row33
    new = seco_join(head, tabs)
    xs = struct.unpack('<%dh' % ncol, T[0x1b4][3])
    print('seco: owner %d -> copy of owner %d row (x %s -> brain sets %s ...), %+d B%s'
          % (OWNER, TEMPLATE_OWNER, list(xs[:8]), list(struct.unpack('<8h', row[:16])), len(new) - len(stock),
             ' (already there)' if had else ''))
    return new


def bnr_part(d):
    ch = arc_entries(d)
    ib = next(k for k, c in enumerate(ch) if c[1] == b'brai' and d[c[2]:c[2] + 4] == b'seco')
    _, _, off, size = ch[ib]
    new_chunk = seco_patch(d[off:off + size])
    if new_chunk == d[off:off + size]:
        return d
    later = [c[2] for c in ch if c[2] > off]
    nxt = min(later) if later else len(d)
    assert off % 16 == 0 and nxt % 16 == 0, 'brai / next chunk not 16-aligned'
    body = new_chunk + b'\0' * ((-len(new_chunk)) % 16)            # later chunks stay 16-aligned
    delta = len(body) - (nxt - off)
    out = bytearray(d[:off]) + body + d[nxt:]
    for k, c in enumerate(ch):
        if k == ib:
            c[3] = len(new_chunk)
        elif c[2] > off:
            c[2] += delta
        struct.pack_into('<I4sII', out, 16 + k * 16, *c)
    for k, c in enumerate(ch):                                   # every other chunk byte-identical
        if k != ib:
            o0 = arc_entries(d)[k][2]
            assert out[c[2]:c[2] + c[3]] == d[o0:o0 + c[3]], 'chunk %d moved wrong' % k
    print('%s: %d -> %d B (later chunks +%d)' % (BNR, len(d), len(out), delta))
    return bytes(out)


# ------------------------------------------------------------------------------------------------ C. system.bin
def acab_patch(b):
    b = bytearray(b)
    n, = struct.unpack_from('<I', b, 8)
    ents = [list(struct.unpack_from('<hhI', b, 16 + i * 8)) for i in range(n)]
    keys = [e[0] for e in ents]
    assert keys == sorted(keys), 'acab keys not sorted'
    tpl = next(e for e in ents if e[0] == TEMPLATE_OWNER)
    if OWNER in keys:
        e = ents[keys.index(OWNER)]
        assert e[1:] == tpl[1:], 'acab %d row is not the shared copy of %d' % (OWNER, TEMPLATE_OWNER)
        print('acab: owner %d already shares owner %d\'s list' % (OWNER, TEMPLATE_OWNER))
        return bytes(b)
    assert max(keys) < OWNER, 'acab key order'
    first = min(e[2] for e in ents)
    assert first == 16 + n * 8, 'acab lists do not start right after the entry table'
    for e in ents:
        e[2] += 8
    ents.append([OWNER, tpl[1], tpl[2]])
    out = bytearray(b[:16]) + b''.join(struct.pack('<hhI', *e) for e in ents) + b[first:]
    struct.pack_into('<I', out, 8, n + 1)
    print('acab: + owner %d -> owner %d\'s %d always-equip general abilities (shared list), +8 B'
          % (OWNER, TEMPLATE_OWNER, tpl[1]))
    return bytes(out)


def ablt_patch(b):
    b = bytearray(b)
    n, = struct.unpack_from('<I', b, 8)
    done = []
    for i in range(n):
        at = 16 + i * 40
        idx, own = b[at], b[at + 1]
        if own != OWNER or b[at + 27] != OWNER:
            continue
        want = bytes([PREF.get(idx, 0)] * 8)
        cur = bytes(b[at + 32:at + 40])
        assert all(x in OUR_PREF_VALUES | {0} for x in cur), 'ablt %02x%02x +32 holds foreign values %s' % (
            own, idx, cur.hex())
        if cur != want:
            b[at + 32:at + 40] = want
            done.append('%02x%02x=%d' % (own, idx, want[0]))
    print('ablt CPU auto-equip priority: %s' % (' '.join(done) if done else 'already set'))
    return bytes(b)


def system_part(sysbin):
    from spot33_save import arc_join, arc_split
    head, chs = arc_split(sysbin)
    for c in chs:
        if c[1] == b'acab':
            c[2] = acab_patch(c[2])
        elif c[1] == b'ablt':
            c[2] = ablt_patch(c[2])
    out = arc_join(head, chs)
    return sysbin if out == sysbin else out


# ------------------------------------------------------------------------------------------------------- ISO
def put(iso, path, data):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, os.path.basename(path))
        open(p, 'wb').write(data)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p], check=True,
                           capture_output=True, text=True)
        print(r.stdout.strip())


def iso_part(iso, dry):
    import mpk
    from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, mpk_member, package_entry, read_at
    from comb_patch import pkg_offset, use_iso
    from pkg_put import PACKAGE_INFO_ISO_SECTOR
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the clean dump'
    use_iso(iso)
    with open(iso, 'rb') as f:
        st, sz = pkg_offset(OBJX)
        objx = read_at(f, st, sz)
        st, sz = pkg_offset(BNR)
        bnr = read_at(f, st, sz)
        info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
        pkg = PACKAGE_ISO_SECTOR * SECTOR
        off, size = package_entry(info, 'general_archive/main/main.bin')
        main_bin = read_at(f, pkg + off, size)
        so, ss = mpk_member(f, pkg + off, 'system.bin')
    sysbin = main_bin[so - pkg - off:so - pkg - off + ss]
    new_objx, new_bnr, new_sys = objx_part(objx), bnr_part(bnr), system_part(sysbin)
    for name, a, b in ((OBJX, objx, new_objx), (BNR, bnr, new_bnr), ('system.bin', sysbin, new_sys)):
        print('%s: %s' % (name, 'no change' if a == b else '%+d B' % (len(b) - len(a))))
    if dry:
        print('--dry: nothing written')
        return
    if new_objx != objx:
        put(iso, OBJX, new_objx)
    if new_bnr != bnr:
        put(iso, BNR, new_bnr)
    if new_sys != sysbin:
        put(iso, 'general_archive/main/main.bin', mpk.replace(main_bin, 'system.bin', new_sys))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    iso_part(sys.argv[1], '--dry' in sys.argv[2:])


if __name__ == '__main__':
    main()
