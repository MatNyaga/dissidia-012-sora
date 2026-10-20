"""KH2-style long combos for #33 (Mat, 2026-10-13: "the amount of Bravery increases the more hits you do, all
culminating in a finisher that can be chained"). Rewrites actions in obj/p_sev120.objx `comb` and the power of the
hits (`atkp` +0x10), then puts the file back (pkg_put; moves to the ISO end if it grew).

How chaining works (notes/character-file.md): after piece A, piece B can follow if some ENABLED action (equipped
ability) has B right after A anywhere in its step list, B is a follow-up (plya role 1/4) and B's ground/air rule
fits. Bravery pieces follow on Circle (Bravery button), HP pieces (plya +0x0f = 2) on Square (HP button). So one action's step list can hold a
small graph: every neighbouring pair is a link.

  python3 -I spot33_combos.py ISO
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402

FILE = 'obj/p_sev120.objx'
N1, N2, N3, M2, NM3, N12, N4 = 0x5be, 0x5bf, 0x5c0, 0x5c2, 0xff0, 0x85b, 0x7d8
AN1, AN2, AN3, AM1, R1, R2 = 0x5c5, 0x5c6, 0x5cc, 0x5c7, 0xb30, 0xb31
LF3, AF3 = 0x5ce, 0x5cf                  # LAND_FINISH3 (= Upper Slash now, motion 10091 authored; was the 10-hit spin) / AIR_FINISH3 (air flurry), both HP role 1
FL = 0x5c3                               # LAND_MIDDLE3 (unused piece, air Bravery follow-up) → Finishing Leap
# piece → motion id: FL plays motion 10300 = NEW slot (block 86 = GMO motion 86 _720A, spot33_chain.py SLOTS; a copy
# of AIR_MIDDLE1's block), animation KH2 668 Finishing Leap (build_sora.sh). (10094/_704C was Braver's LANDING.)
# Air moveset (Mat 2026-10-14: "Sora has additional air combos e.g. horizontal slash"): Horizontal Slash / Aerial Sweep
# = own air HP finishers, Aerial Dive = air starter for a foe BELOW. Pieces = unused Cloud rows (LAND_LONG1/2,
# LAND_NEAR2_2) overwritten with a CLONE of a template row, then own motion (new slots 10301-10303), banner, ranges.
HS, SW, DV = 0x5c4, 0x5cd, 0x85c
LF1, AF1 = 0x5c8, 0x5ca                  # base HP pieces (were Cross-slash / Braver start)
# Dodge Slash (Mat: "two moves, dodge slash into explosion; only the explosion is the HP attack"): Bravery ground
# starter DS (unused LAND_LONG3 row ← clone of NEAR1) → long ground combo; chain piece EX2 (LAND_LONG4 ← clone of
# LF1, follow-up) = Explosion after Dodge Slash (same motion/block as the base ground □ Explosion)
DS, EX2 = 0x604, 0x605
CLONE = {HS: AF3, SW: AF3, DV: N4, DS: N1, EX2: LF1}   # piece: template piece (whole 116-byte row except id + name)
# 10304 Aerial Finish (Bravery air-chain finisher, KH2 776 5 sweeps), 10305 Dodge Slash → Explosion (ground □),
# 10306 Aerial Finish HP (air □) — all AUTHORED blocks in new slots (spot33_chain.py), natural KH2 speed
# 10305 = Dodge Slash wind-up + ONE Explosion strike (ground □, Mat), 10308 = Explosion alone (after Dodge Slash),
# 10309 = Retaliating Slash (KH2 688) replaces Cloud's Aerial Flurry on the AF3 piece (Mat: replace with a KH2 move)
MOTION = {FL: 10300, HS: 10301, SW: 10302, DV: 10303, AM1: 10304, LF1: 10305, AF1: 10306, DS: 10307, EX2: 10308,
          AF3: 10309}
LANDING = {HS: 0xFFFF, SW: 0xFFFF, AF3: 0xFFFF}       # plya +0x10 = landing motion (AIR_FINISH3 → 10097); none for these
# plya +0x1e u16 = motion after the move ends (1 idle, 0x65 fall). LF3 kept Cloud's 0x65 → after the ground Upper Slash
# Sora stood in the FALL motion forever (never 'lands': he is on the ground; test 150, Mat: "stuck in an animation")
AFTER = {LF3: 1}
# KH2 finishers on Square (equippable chain abilities): Guard Break (ground; was 'Explosion' — Mat: real KH2
# Explosion = 612 swing + magic AoE burst, later) = LAND_FINISH2 piece (Meteorain, unused),
# block 65 _705A; Magnet Burst (air) = HP_A_METEO1 piece, block 68 _707A. Blocks rewritten by spot33_chain.py COPY.
EXP, MB = 0x5c9, 0xb32
# own hit data (atkp rows appended; ids binary-searched → bigger than every old id): new id: (template hit, name)
NEW_HITS = {0x1006: ('BR_A_REN1_1', 'HS_SLASH'), 0x1005: ('LAND_FINISH1_3', 'EXPLOSION'), 0x1004: ('LAND_FINISH1_3', 'UPPER_SLASH'), 0x1000: ('LAND_FINISH1_3', 'GUARD_BREAK'), 0x1001: ('AIR_FINISH2_3', 'MAGNET_BURST'),
            0x1002: ('AIR_FINISH3_1', 'AERIAL_SWEEP_1'), 0x1003: ('AIR_FINISH2_3', 'AERIAL_SWEEP')}
# KH2 Combo-Plus chain (Mat: 6-7 ground hits, 10+ once launched). Neighbouring pairs = links; the tail adds the
# HP (Square) links: ground hits 2/4 → spin, air hits 9/11 → air flurry.
# Ground chain ends with its OWN finisher (Finishing Leap), the air chain with Aerial Finish (Mat 2026-10-14: "it has
# the same finisher, we need to mix it up")
# R1 = Horizontal Slash, ALL 6 slashes in one piece (2 × KH2 772; two 3-slash pieces lost the link, test 139)
GROUND = [N1, N2, N12, N3, N4, M2, NM3, AN2, AN3, R1, FL]   # N4 leaves Sora airborne → before the launcher
AIR = [AN1, AN2, AN3, R1, AM1]
# FOUR COMBOS (Mat 2026-10-15 3 AM: "I want 4 combos, right now all combos lead to one finisher in the air. I want
# different combo variations"). Before: Combo Plus / Slide Dash / Dodge Slash all ran GROUND (→ Finishing Leap) and all
# air starters ran AIR (→ Aerial Finish). Now every starter has its own route + finisher, no new animations:
# new pieces = clones of existing rows on motion VARIANTS (spot33_chain.py VARIANTS: one swing block, two hit sets):
G4, G5, GF, HSF, GSP, G6 = 0x1020, 0x1021, 0x1022, 0x1023, 0x1024, 0x1025
NEW_PIECES = {G4: (N1, 10003, 'LAND_NEAR1_C'),        # KH2 604 again (block 43 variant 2, same hit as N1)
              G5: (N2, 10004, 'LAND_NEAR2_C'),        # KH2 608 again (block 45 variant 2, own light hit 0x64e)
              GF: (N3, 10005, 'LAND_FINISH_C'),       # KH2 620 ground combo finisher, BLOW-AWAY (block 46 variant 2)
              HSF: (R1, 10316, 'BR_A_REN1_F'),        # Horizontal Slash x6, last slash blows away (block 56 variant 2)
              GSP: (N1, 10317, 'LAND_SPIN_C'),        # Dodge Slash spin (4 hits) as a combo link (block 94 variant 2)
              G6: (N12, 10008, 'LAND_NEAR1_3C')}      # KH2 612 again (block 44 variant 2)
# Mat: "all the combos should be 12 hits plus" (hits counted from the script blocks; multi-hit pieces count each hit)
# and "you can do additional horizontal slashes in the air" (R1 → HSF = two Horizontal Slash x6). No piece repeats inside
# a route (a repeat would make a link loop), every route ends in its own finisher.
COMBO_GROUND = [N1, N2, N12, G4, G5, GSP, G6, N3, GF]           # 1 "Ground Rave": 12 hits, stays on the ground
COMBO_DASH = [0x5c1, N2, N4, M2, NM3, AN2, AN3, R1, AM1]       # 2 dash-in → launch → air rave → Horizontal Slash → Aerial Finish (19)
COMBO_SPIN = [DS, N3, N12, G4, N4, M2, NM3, AN2, FL]           # 3 spin → heavy ground hits → launch → Finishing Leap slam (13)
ACTIONS = {
    1020: COMBO_GROUND,                  # base Combo Plus (Circle only); Square finishers are separate chain abilities
    321: AIR,                            # 4a Air Combo → Horizontal Slash → Aerial Finish (15)
    316: COMBO_DASH,                     # Slide Dash (links only come from the action that STARTED the chain)
    324: [0x88e, AN2, AN3, R1, HSF],     # 4b Aerial Spiral (foe above) → Horizontal Slash x6 twice, last slash blows away (16)
    327: COMBO_SPIN,                     # Dodge Slash (Bravery, ground)
    320: [DS, EX2],                      # chain "Dodge Slash > Explosion"
    328: [AF1],                          # air □ = Aerial Finish (HP) alone — no Braver slam (AF2) any more
    315: [N2, LF3, G5, LF3],             # chain "Combo Plus > Upper Slash" (after hit 2 or 5)
    # air chains, one branch point each: Magnet Burst after AN2, Retaliating Slash after AN3, Horizontal Slash after
    # R1, Aerial Sweep after AN1 (all can be equipped together)
    323: [AN3, AF3],                     # chain "Air Combo > Retaliating Slash"
    318: [R1, HS],                       # chain "Air Combo > Horizontal Slash"
    319: [AN1, SW],                      # chain "Air Combo > Aerial Sweep" (after air hit 1)
    325: [DV, AN2, AN3, R1, FL],         # 4c Aerial Dive (foe below) → Horizontal Slash x6 → Finishing Leap plunge (13)
    313: [0x5c1, LF3],                   # chain "Slide Dash > Upper Slash" (right after the dash)
    # Guard Break chains branch at OTHER hits than Upper Slash, so both can be equipped
    314: [N12, EXP, G4, EXP],            # chain "Combo Plus > Guard Break" (after hit 3 or 4)
    317: [N2, EXP],                      # chain "Slide Dash > Guard Break" (after the dash's hit 2)
    927: [AN2, MB],                      # chain "Air Combo > Magnet Burst"
}
ROLE1 = [N12, N4, R1, EXP, MB, HS, SW, EX2, G4, G5, GF, HSF, GSP, G6]
ROLE0 = [DV, DS]                             # follow-up turned into a starter                    # starters turned into follow-ups (plya +3 = 1)
# finishers after the 6 Horizontal Slash hits: the foe drifts out of 6 m (test 136: finisher never started)
REACH = {G4: 3.0, G5: 3.0, GF: 4.0, HSF: 6.0, GSP: 3.0, G6: 3.0, N3: 4.0, AN2: 6.0, AN3: 6.0, R1: 6.0, R2: 6.0, NM3: 6.0, FL: 10.0, AM1: 10.0, EXP: 6.0, MB: 7.0, HS: 7.0, SW: 7.0, DV: 6.0}
MINR = {EXP: 0.0, MB: 0.0, HS: 0.0, SW: 0.0, DV: 0.0}               # plya +0x24 min distance (Meteorain pieces had 7 m)
# plya +0x21 = in-battle banner text entry - 1 (spot33_battlenames.py NAMES); both Meteorain pieces had 4
BANNER = {MB: 10, HS: 11, SW: 12}
# plya +0x18 flags: 0x200000 = only with stick UP, 0x400000 = only DOWN (CHASE_ATTACK_UP/LO); AIR_NEAR2 had it →
# never came out when just mashing Circle (Mat: pause after hit 7). Use the normal flags.
FLAGS = {AN2: 0x10002, MB: 0x10012}     # MB: 0x10012 = vanilla HP_A_METEO1 / like AIR_FINISH1 (stays in the air).
# Was 0x10013 (like Braver/AIR_FINISH3): bit 0 = plunge piece that waits to LAND and plays its plya +0x10 landing
# motion (0x5cb -> 10094, 0x5cf -> 10097 have it). MB's block 68 is authored from 10092 (op 0x0a stay airborne to
# 65535, +0x10 = none) -> never lands -> Mat test275: 'stuck in a falling pose until you dodge or move'.
HEIGHT = {HSF: 6.0, AN2: 6.0, AN3: 6.0, R1: 6.0, R2: 6.0, NM3: 6.0, AM1: 10.0, FL: 10.0, EXP: 6.0, MB: 10.0, HS: 10.0, SW: 10.0}   # plya +0x2c/+0x30 = -h..+h (air hits after launch)                        # plya +0x28 max distance (NEAR3 was 2.0: missed after 3 pushes)
# hit power ramp (atkp +0x10) by hit name, and light reactions (copy +0x05, +0x14..+0x34 from a template hit)
POWER = {'LAND_NEAR1': 6, 'LAND_NEAR2': 7, 'LAND_NEAR1_2': 8, 'LAND_NEAR4': 9, 'LAND_NEAR3': 10, 'LAND_MIDDLE2': 12,
         'NEW_MIDDLE3': 13, 'AIR_NEAR1_3': 14, 'AIR_NEAR2': 15, 'BR_A_REN1_1': 25, 'BR_A_REN2_1': 17,
         'AIR_MIDDLE1_1': 2, 'AIR_MIDDLE1_2': 25, 'AIR_NEAR1_1': 5, 'AIR_NEAR1_2': 9, 'AIR_MIDDLE1_0': 8,
         'HS_SLASH': 10}
# (HP hits: +0x10 is not Bravery damage; EXPLOSION / MAGNET_BURST keep their templates' values)
LIGHT = {'LAND_MIDDLE1': 'LAND_NEAR1', 'LAND_MIDDLE1_2': 'LAND_NEAR1',   # Slide Dash: flinch, not knock back
         'LAND_NEAR2': 'LAND_NEAR1', 'LAND_NEAR1_2': 'LAND_NEAR1', 'LAND_NEAR4': 'LAND_NEAR1',
         'LAND_NEAR3': 'LAND_NEAR1', 'NEW_MIDDLE3': 'AIR_NEAR1_1', 'AIR_NEAR1_3': 'AIR_NEAR1_1',
         'AIR_NEAR2': 'AIR_NEAR1_1', 'BR_A_REN2_1': 'AIR_NEAR1_1', 'AIR_NEAR1_2': 'AIR_NEAR1_1',
         'AIR_MIDDLE1_0': 'AIR_NEAR1_1',
         'LAND_NEAR2_2': 'LAND_NEAR1',        # Ground Rave hit 5 (motion 10004): was Cloud's push-back → finisher whiffed
         # Horizontal Slash slashes keep the foe in place (Aerial Flurry's multi-hit reaction, push 0.3) — with normal
         # light hits the foe drifted out of reach after 1-2 slashes (test 137, Mat: "horizontal slash misses")
         'HS_SLASH': 'AIR_FINISH3_1',                              # Aerial Spiral starter: flinch, combo goes on
}
# own knockback: name: (reaction +5, bytes +0x14..+0x17, floats +0x18..+0x24). Reaction 0x0c = blow away, floats =
# (?, push forward, push UP, ?). Upper Slash (Mat: "in KH2 it sends the opponent into the air, Sora stays on the
# ground"): was a copy of AIR_FINISH1_4 (react 07 = crumple on the spot, test 150/151); (0, 2, 6, 30) = ~6 m up,
# tuned live 2026-10-14 (30 up = 18 m, 12 up = 12 m).
KNOCK = {'UPPER_SLASH': (0x0c, '00146464', (0.0, 2.0, 6.0, 30.0)),
         # Ground Rave finisher (motion 10005, spot33_chain VARIANTS): unused Bravery hit, blown far BACK, slightly up
         'BR_A_REN1_1': (0x0c, '00143232', (0.0, 30.0, 3.0, 20.0))}
# light AIR hits pushed the foe 4 m each (Cloud's AIR_NEAR1_1 values, copied by LIGHT) → after the 2-hit openers the 3rd hit
# whiffed (Mat, test191r). KH2 air combos keep the foe close: push 1.5.
for _n in ('AIR_NEAR1_1', 'AIR_NEAR1_2', 'AIR_NEAR1_3', 'AIR_NEAR2', 'AIR_MIDDLE1_0', 'NEW_MIDDLE3', 'BR_A_REN2_1'):
    KNOCK[_n] = (0x0d, '080a0f0f', (0.0, 1.5, 0.5, 18.0))


def rebuild_arc(d, new_chunks):
    n, = struct.unpack_from('<I', d, 4)
    ents = [list(struct.unpack_from('<I4sII', d, 16 + k * 16)) for k in range(n)]
    order = sorted(range(n), key=lambda k: ents[k][2])
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


def main():
    iso = sys.argv[1]
    use_iso(iso)
    st, sz = pkg_offset(FILE)
    with open(iso, 'rb') as f:
        d = read_at(f, st, sz)
    n, = struct.unpack_from('<I', d, 4)
    ents = [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]
    ci = next(k for k, e in enumerate(ents) if e[1] == b'comb')
    ai = next(k for k, e in enumerate(ents) if e[1] == b'atkp')
    comb = d[ents[ci][2]:ents[ci][2] + ents[ci][3]]
    ver, cnt = struct.unpack_from('<HH', comb, 0)
    offs = struct.unpack_from('<%dI' % cnt, comb, 4)
    acts = []
    for o in offs:
        aid, ns, alt, par = struct.unpack_from('<HHhh', comb, o)
        steps = [comb[o + 8 + k * 8:o + 16 + k * 8] for k in range(ns)]
        if aid in ACTIONS:
            tpl = steps[0]
            steps = [struct.pack('<I', p) + tpl[4:] for p in ACTIONS[aid]]
            print('action %d: %d steps' % (aid, len(steps)))
        acts.append(struct.pack('<HHhh', aid, len(steps), alt, par) + b''.join(steps))
    head = 4 + 4 * cnt
    new = bytearray(struct.pack('<HH', ver, cnt))
    pos = head
    for a in acts:
        new += struct.pack('<I', pos)
        pos += len(a)
    for a in acts:
        new += a
    atkp = bytearray(d[ents[ai][2]:ents[ai][2] + ents[ai][3]])
    na, = struct.unpack_from('<I', atkp, 4)
    have = {struct.unpack_from('<I', atkp, 8 + k * 68)[0] for k in range(na)}
    byname = {atkp[8 + k * 68 + 0x34:8 + k * 68 + 0x44].split(b'\0')[0].decode(): k for k in range(na)}
    for hid, (tpl, name) in sorted(NEW_HITS.items()):
        if hid in have:
            continue
        assert hid > max(have), 'new hit ids must be the biggest'
        row = bytearray(atkp[8 + byname[tpl] * 68:8 + byname[tpl] * 68 + 68])
        struct.pack_into('<I', row, 0, hid)
        row[0x34:0x44] = name.encode().ljust(16, b'\0')
        atkp[8 + na * 68:8 + na * 68] = row
        na += 1
        struct.pack_into('<I', atkp, 4, na)
        have.add(hid)
        print('hit %x %s <- copy of %s' % (hid, name, tpl))
    for k in range(na):
        at = 8 + k * 68
        name = atkp[at + 0x34:at + 0x44].split(b'\0')[0].decode()
        if name in POWER:
            old, = struct.unpack_from('<H', atkp, at + 0x10)
            struct.pack_into('<H', atkp, at + 0x10, POWER[name])
            print('hit %-12s power %3d -> %d' % (name, old, POWER[name]))
    rows = {atkp[8 + k * 68 + 0x34:8 + k * 68 + 0x44].split(b'\0')[0].decode(): 8 + k * 68 for k in range(na)}
    for dst, src in LIGHT.items():
        a, b2 = rows[dst], rows[src]
        atkp[a + 5] = atkp[b2 + 5]
        atkp[a + 0x14:a + 0x34] = atkp[b2 + 0x14:b2 + 0x34]
        print('hit %-12s reaction <- %s (light)' % (dst, src))
    for dst, (react, b14, fl) in KNOCK.items():
        a = rows[dst]
        atkp[a + 5] = react
        atkp[a + 0x14:a + 0x28] = bytes.fromhex(b14) + struct.pack('<4f', *fl)
        print('hit %-12s knockback -> %02x %s' % (dst, react, fl))
    pi = next(k for k, e in enumerate(ents) if e[1] == b'plya')
    plya = bytearray(d[ents[pi][2]:ents[pi][2] + ents[pi][3]])
    npl, = struct.unpack_from('<I', plya, 4)
    byid = {struct.unpack_from('<H', plya, 8 + k * 116)[0]: 8 + k * 116 for k in range(npl)}
    for pid, (tpl, motion, name) in NEW_PIECES.items():          # appended rows (plya is searched linearly)
        if pid in byid:
            continue
        r = bytearray(plya[byid[tpl]:byid[tpl] + 116])
        struct.pack_into('<H', r, 0, pid)
        struct.pack_into('<H', r, 0x1c, motion)
        r[0x64:0x74] = name.encode().ljust(16, b'\0')
        byid[pid] = len(plya)
        plya += r
        npl += 1
        struct.pack_into('<I', plya, 4, npl)
        print('piece %x %s <- copy of %x, motion %d' % (pid, name, tpl, motion))
    for pid, tpl in CLONE.items():
        a, t = byid[pid], byid[tpl]
        plya[a + 2:a + 0x64] = plya[t + 2:t + 0x64]                    # keep id (+0) and name (+0x64)
        print('piece %x <- clone of %x' % (pid, tpl))
    for k in range(npl):
        at = 8 + k * 116
        if struct.unpack_from('<H', plya, at)[0] in ROLE0:
            plya[at + 3] = 0
        if struct.unpack_from('<H', plya, at)[0] in LANDING:
            struct.pack_into('<H', plya, at + 0x10, LANDING[struct.unpack_from('<H', plya, at)[0]])
        if struct.unpack_from('<H', plya, at)[0] in ROLE1:
            plya[at + 3] = 1
            print('piece %x -> follow-up' % struct.unpack_from('<H', plya, at)[0])
        pid = struct.unpack_from('<H', plya, at)[0]
        if pid in AFTER:
            struct.pack_into('<H', plya, at + 0x1e, AFTER[pid])
            print('piece %x after-motion -> %d' % (pid, AFTER[pid]))
        if pid in REACH:
            struct.pack_into('<f', plya, at + 0x28, REACH[pid])
            print('piece %x reach -> %.1f' % (pid, REACH[pid]))
        if pid in FLAGS:
            struct.pack_into('<I', plya, at + 0x18, FLAGS[pid])
            print('piece %x flags -> %x' % (pid, FLAGS[pid]))
        if pid in BANNER:
            plya[at + 0x21] = BANNER[pid]
            print('piece %x banner -> text %d' % (pid, BANNER[pid] + 1))
        if pid in MINR:
            struct.pack_into('<f', plya, at + 0x24, MINR[pid])
            print('piece %x min distance -> %.1f' % (pid, MINR[pid]))
        if pid in MOTION:
            struct.pack_into('<H', plya, at + 0x1c, MOTION[pid])
            print('piece %x motion -> %d' % (pid, MOTION[pid]))
        if pid in HEIGHT:
            struct.pack_into('<ff', plya, at + 0x2c, -HEIGHT[pid], HEIGHT[pid])
            print('piece %x height -> +-%.1f' % (pid, HEIGHT[pid]))
    out = rebuild_arc(d, {ci: bytes(new), ai: bytes(atkp), pi: bytes(plya)})
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'f.objx')
        open(p, 'wb').write(out)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main()
