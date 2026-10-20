"""Let #33's long combo continue past hit 4: add the "combo can continue" window (script event op 0x01, 1 param) to
moves that were combo ENDERS in Cloud's set. Without it the next piece never starts (test 98 log: NEAR1, NEAR2,
MIDDLE2, NEW_MIDDLE3, then fall). Event = u16 from, u16 to, u8 op 1, u8 npar 1, 6 bytes condition (byte 0 =
variant, 0 any), u32 0. Block header: u8 id, u8 0, u8 event count, u8 ?, u16 events end, u16 block size.
Run AFTER spot33_speed.py (windows below are for the sped-up hit frames).

  python3 -I spot33_chain.py ISO
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from spot33_combos import rebuild_arc  # noqa: E402

FILE = 'obj/p_sev120.objx'
# motion id: (from, to) script frames of the continue window (just after the hit, like NEAR2's 24-54 after 16-22)
# whole script block copies (target motion: source motion): an unused block gets another move's events (hitboxes,
# windows, effects) so a piece pointed at it (spot33_combos.py MOTION) plays like the source with its own animation.
# Block = u8 block number, u8 0, u8 event count, u8 ?, u16 events end, u16 block size, events, extra records.
# NEW animation slots (2026-10-14): motion id: (block = GMO motion index, template motion). Appends a p_se type-8
# block (copy of the template's block, byte 0 = its number) and a type-7 row motion id → block (variant 0). The GMO
# gets the matching motion via build_sora.sh SLOTS (gmo_motion.py append), same order. Ids from 10300 up.
SLOTS = {10299: (86, 1200),             # GMO motion 86 = the WIN CAMERA hook (test 148: with any other motion there the
         #   results camera cut away ~4.5 s into the win pose and panned off Sora; Cloud has no motion 86). Copy of _910A.
         10300: (87, 10030),             # _720A Finishing Leap (was block 64 = Braver's landing, Aerial Finish HP!)
         10301: (88, 10096),             # _721A Horizontal Slash (Square finisher)
         10302: (89, 10030),             # _722A Aerial Sweep
         10303: (90, 10050),             # _723A Aerial Dive
         10304: (91, 10030),             # _724A Aerial Finish (Bravery air-chain finisher)
         10305: (92, 10090),             # _725A Dodge Slash → Explosion (ground HP)
         10306: (93, 10092),             # _726A Aerial Finish HP (air HP)
         10307: (94, 10000),             # _727A Dodge Slash (Bravery ground starter)
         10308: (95, 10090),             # _728A Explosion alone (chain after Dodge Slash)
         10309: (96, 10096)}             # _729A Retaliating Slash (air Square finisher, replaces Aerial Flurry)
# value = (source motion, {old hit id: new hit id}) — hitbox events (op 0x00/0x43) of the copy use the new hits.
# (2026-10-14: every KH2 move is AUTHORED now; COPY kept for later use)
COPY = {}
# AUTHORED blocks (2026-10-14, Mat: copies of Cloud's blocks keep Cloud's hit patterns, e.g. AIR_MIDDLE1's 20-60
# multi-hit = "blue series of attacks"): motion: dict(tpl=template motion, hits=[(from, to, atkp hit id, shape)],
# end=last frame[, ones=[(frame, op, [params])], free=frame (op 0x28 'free to act' start), cancel=frame (op 0x22 start), lunge=[(from, to)] (op 0x39)]). The template only gives the plumbing (trails, sounds, cancel/end/
# airborne ops); its hit events are DROPPED and every other frame is stretched piecewise-linearly: template first-hit
# start → hits[0] start, last-hit end → hits[-1] end, template end (last op 0x02 / op 0x28 start) → end.
# Hit moments = KH2's own (tools/scripts/kh2_hits.py; animations played at natural speed, build_sora.sh `nat:`).
# Shapes (p_se type 5, notes/hitbox-shapes.md): 0x30/0x31 Keyblade spheres, 0x06 body-centred r 2.5 (area).
L_AIR, L_GND, L_HPA, L_HPG = 0x359, 0x35d, 0x372, 0x365
# FRONT = shape group 0x32: sphere r ~1.3 centred 1.8 m in front of Sora's root (≈ Keyblade-tip distance). KH2 swings
# at natural speed (no MATCH) put the Keyblade where KH2 has it, often short of the foe (test 135: Horizontal Slash
# whiffed, CPU escaped); 0x13 (r 2 at 2 m) landed but hit beyond the blade (Mat: "the opponent is further away").
FRONT = 0x32  # light Bravery air / ground, light HP air / ground hits
# own KH2 sounds appended to #33's snd_ bank by spot33_sfx.py (70 Explosion start = KH2 se 999038, 71 orb hit,
# 72 blast = 999042 head/full). Orb sounds 3 frames AFTER each hold hit: the hit's own spark sound (slots 25/27/3)
# starts ~2 frames after the hit and cut the orb sound off (Mat, test 154: "the 5 orbs hitting is not there"). Played with one-shot op 0x03; ids are Cloud's base 2200000 + slot until
# spot33_soundids.py (last build step) moves them. SFX_BASE=21900000 when patching an already-moved test ISO.
SFX = lambda slot: int(os.environ.get('SFX_BASE', 2200000)) + slot  # noqa: E731
AUTHOR = {
    # air combo: Horizontal Slash = 6 slashes in ONE piece (KH2 772 frames 0-22 + 772 whole: 16/26/38 + 60/70/82),
    # Mat: "up to 6". (With the full first clip slash 4 came 0.6 s after slash 3 → the CPU air-dodged out, test 140)
    10060: dict(tpl=10022, hits=[(14, 18, 0x1006, FRONT), (24, 28, 0x1006, FRONT), (36, 40, 0x1006, FRONT),
                                 (58, 62, 0x1006, FRONT), (68, 72, 0x1006, FRONT), (80, 84, 0x1006, FRONT)],
                end=104, free=104, cancel=80, nolunge=True,   # own lunges below (template 10022 now has one too)
                lunge=[(0, 14), (18, 24), (28, 36), (42, 58), (62, 68), (72, 80)]),
    # Aerial Finish (776, 5 full sweeps at 26/34/54/74/84), last one blows away
    10304: dict(tpl=10030, hits=[(24, 28, 0x1006, FRONT), (32, 36, 0x1006, FRONT), (52, 56, 0x1006, FRONT),
                                 (72, 76, 0x1006, FRONT), (82, 88, 0x36e, FRONT)], end=116,
                lunge=[(0, 24), (40, 52), (60, 72)]),      # sweeps keep the foe in place (test 141: escaped)
    # Finishing Leap (668: hits 28 / 44)
    10300: dict(tpl=10030, hits=[(26, 30, L_AIR, FRONT), (42, 46, 0x36e, FRONT)], end=64),
    # Aerial Spiral (768: 16 / 30) and Aerial Dive (784: 12 / 26 / 34 / 40) — air starters, windows below
    10031: dict(tpl=10022, hits=[(14, 18, 0x6c2, FRONT), (28, 32, 0x6c2, FRONT)], end=72, free=62, nolunge=True),
    # Aerial Dive: no dash (Mat, test191r: "the 4th hit of back+O … Sora goes too close": the template's op 0x02 mode-4
    # dash at 0-10 carried Sora into the foe, so the next swing (AN2) missed). No lunge either: FRONT hits sit 1.8 m ahead
    # and the NEAR1 lunge closes to ~0.5 m.
    10303: dict(tpl=10050, hits=[(10, 14, 0x517, FRONT), (24, 28, 0x517, FRONT), (38, 42, 0x517, FRONT)], end=70, free=70,
                nodash=True),
    # Square finishers: Guard Break (660: lunge hit 32), Magnet Burst (788: 22 / 44 / 62), Aerial Sweep (764: 34),
    # Horizontal Slash (772: 16 / 26 / 38)
    10095: dict(tpl=10090, hits=[(30, 36, 0x1000, FRONT)], end=76),
    10098: dict(tpl=10092, hits=[(20, 24, L_HPA, FRONT), (42, 46, L_HPA, FRONT), (60, 66, 0x1001, FRONT)], end=90),
    10302: dict(tpl=10092, hits=[(30, 38, 0x1003, FRONT)], end=60),
    10301: dict(tpl=10092, hits=[(14, 18, L_HPA, FRONT), (24, 28, L_HPA, FRONT), (36, 40, 0x37d, FRONT)], end=60),
    # ground □ = Explosion (664: plant 32, burst 68 = AREA hit on the body sphere 0x06 + Cloud's Firaga burst effect 5
    # as a stand-in for KH2's light orbs; Mat: KH2 look long term). Dodge Slash is a separate Circle move (Mat).
    # Mat: "explosion … doesn't have its dodge slash wind up and it's a single strike with orbs surrounding him":
    # 652 wind-up (no hits) + 664 from tick 84, ONE area strike at its burst (84 + 68) + burst effect
    # Mat: "dodge slash does brv but not hp and then explosion does the damage" → the 4 spin hits are Bravery hits
    # (also keep the foe locked through the wind-up), then the ONE area HP strike
    10305: dict(tpl=10090, hits=[(14, 18, L_GND, FRONT), (32, 36, L_GND, FRONT), (46, 50, L_GND, FRONT),
                                 (58, 62, L_GND, FRONT),
                                 # hold hits while the Keyblade goes up (spin end 62 → orbs 116: 0.9 s gap, the CPU
                                 # jumped / air-dodged out, test 145)
                                 (72, 75, 0x1006, FRONT), (84, 87, 0x1006, FRONT), (96, 99, 0x1006, FRONT),
                                 (108, 111, 0x1006, FRONT),
                                 # Mat: "in KH2 the explosion holds you in place … no dodging once the orbs hit you":
                                 # 664's orbs (KH2 triggers 32-57) = area HOLD hits (no push) every 6 frames, then
                                 # the HP blast at 57-64
                                 (116, 119, 0x1006, 0x06), (122, 125, 0x1006, 0x06), (128, 131, 0x1006, 0x06), (134, 137, 0x1006, 0x06), (140, 143, 0x1006, 0x06),
                                 (146, 156, 0x1005, 0x06)], end=172,
                ones=[(116, 0x19, [22, 0]), (146, 0x19, [22, 0]), (84, 0x03, [SFX(70), 0, 0])] +
                     [(f + 3, 0x03, [SFX(71), 0, 0]) for f in (116, 122, 128, 134, 140)] + [(146, 0x03, [SFX(72), 0, 0])],
                lunge=[(0, 14), (20, 32), (36, 46)]),
    10308: dict(tpl=10090, hits=[(32, 35, 0x1006, 0x06), (38, 41, 0x1006, 0x06), (44, 47, 0x1006, 0x06), (50, 53, 0x1006, 0x06), (56, 59, 0x1006, 0x06), (62, 72, 0x1005, 0x06)], end=88,
                ones=[(32, 0x19, [22, 0]), (62, 0x19, [22, 0]), (0, 0x03, [SFX(70), 0, 0])] +
                     [(f + 3, 0x03, [SFX(71), 0, 0]) for f in (32, 38, 44, 50, 56)] + [(62, 0x03, [SFX(72), 0, 0])]),
    # Retaliating Slash (688: spinning hits 8 / 24 / 40), air HP, last blows away
    10309: dict(tpl=10092, hits=[(6, 10, L_HPA, FRONT), (22, 26, L_HPA, FRONT), (38, 44, 0x37d, FRONT)], end=72,
                lunge=[(0, 6), (12, 22)]),
    # Upper Slash (KH2 648, uppercut at 10) replaces Spin Finish on LF3 (Mat 2026-10-14: "let's replace it"):
    # ONE HP hit that launches the foe up (0x1004 UPPER_SLASH, reaction of Braver's launch)
    10091: dict(tpl=10090, hits=[(8, 14, 0x1004, FRONT)], end=56, lunge=[(0, 8)]),
    # Dodge Slash (652: spinning flurry 16/34/48/60), Bravery starter → long ground combo
    10307: dict(tpl=10000, hits=[(14, 18, L_GND, FRONT), (32, 36, L_GND, FRONT), (46, 50, L_GND, FRONT),
                                 (58, 62, L_GND, FRONT)], end=84, free=84, lunge=[(0, 14), (20, 32), (36, 46)]),
    # Aerial Finish HP (776 sweeps), no Braver slam
    10306: dict(tpl=10092, hits=[(24, 28, L_HPA, FRONT), (32, 36, L_HPA, FRONT), (52, 56, L_HPA, FRONT),
                                 (72, 76, L_HPA, FRONT), (82, 88, 0x37d, FRONT)], end=116),
}
SCALE = {}
DROP_MAGI = {}
# lunge toward the foe (op 0x39, params copied from NEAR1's: 0.2, 8.0, 0.5, 0, 0) on later combo hits: only NEAR1 had
# it, so every hit's push-back added distance (test 128 log: 1.1 m → 2.5 → 3-4 m at hit 5, then the CPU dodged out).
# motion: (from, to) script frames (up to the hit)
ADVANCE = {10001: (0, 10), 10007: (0, 10), 10002: (0, 14), 10050: (0, 10),
           # air combo pieces had NO lunge while every light air hit pushed the foe 4 m → the 3rd hit whiffed
           # (Mat 2026-10-15, test191r: "the third hit that launches you further away doesn't hit")
           10020: (0, 24), 10021: (0, 14), 10022: (0, 14), 10224: (0, 10)}
WINDOWS = {10004: (18, 48), 10307: (62, 84), 10303: (42, 72), 10031: (32, 62), 10060: (80, 110), 10224: (16, 46), 10021: (24, 54), 10022: (22, 52),
           10050: (20, 50), 10002: (22, 52), 10061: (36, 70)}

# FOUR COMBOS (Mat 2026-10-15: "I want 4 combos, right now all combos lead to one finisher in the air"): one KH2 swing
# block can serve as a combo LINK in one route and as a blow-away FINISHER in another through type-7 VARIANTS (rows =
# motion id -> block + variant; events with condition byte 0 = variant run in that variant only, 0 = always).
# spec: base motion (its row variant, made non-zero if 0), new motion id + variant, hits: 'copy' = the base's hit
# events re-emitted for the new variant with ids replaced (REPLACE {old: new} or 'last' = only the last hit),
# lunge: copy the base variant's op 0x39 lunges, free: op 0x28 start for the new variant. Runs after WINDOWS.
VARIANTS = [
    # Combo Plus ground finisher = KH2 620 swing (block 46) as motion 10005 (variant 2): hit 0xb85 BR_A_REN1_1 (unused by
    # any script) made a HORIZONTAL Bravery blow-away in spot33_combos KNOCK (0x36e launched the foe ~22 m up, test 191q)
    dict(base=10002, new=10005, var=2, hits='copy', replace={0x35f: 0xb85}, lunge=True),
    # Combo Plus 5th hit = KH2 608 again (block 45, Cloud's variant 2 = motion 10004): own lunge, later free
    dict(base=10001, new=10004, var=2, hits=None, lunge=True, free=50),
    # Aerial Spiral finisher = Horizontal Slash x6 (block 56) as new motion 10316, LAST slash blows away (0x36e)
    dict(base=10060, new=10316, var=2, hits='copy', last=0x36e, lunge=True),
    # Mat: "all the combos should be 12 hits plus" → Ground Rave gets the Dodge Slash spin (block 94, 4 hits) mid-combo
    # as motion 10317 and the 612 swing again (block 44) as motion 10008; both keep their continue windows
    dict(base=10307, new=10317, var=2, hits='copy', lunge=True, window=(62, 84)),
    dict(base=10007, new=10008, var=2, hits='copy', lunge=True, window=(16, 46)),
]


def _events(c, o):
    """-> (header bytes, [event bytearrays], one-shot bytes) of the block at offset o"""
    size = struct.unpack_from('<H', c, o + 6)[0]
    e1 = struct.unpack_from('<H', c, o + 4)[0]
    evs, k = [], o + 8
    for _ in range(c[o + 2]):
        n4 = 12 + 4 * c[k + 5]
        evs.append(bytearray(c[k:k + n4]))
        k += n4
    return bytearray(c[o:o + 8]), evs, bytes(c[o + e1:o + size])


def variant(t7, c, rows, spec):
    """split one block between two type-7 variants (VARIANTS); re-runnable"""
    t7 = bytearray(t7)
    m7, = struct.unpack_from('<I', t7, 4)
    base, new, nv = spec['base'], spec['new'], spec['var']
    blk, bv = rows[base]
    if bv == 0:                                          # base must own a variant so its events can be exclusive
        for k in range(m7):
            if struct.unpack_from('<H', t7, 8 + k * 8)[0] == base:
                struct.pack_into('<H', t7, 12 + k * 8, 1)
        bv = 1
        rows[base] = (blk, bv)
        print('motion %d (block %d): row variant 0 -> 1' % (base, blk))
    if new not in rows:
        rr = [bytes(t7[8 + k * 8:16 + k * 8]) for k in range(m7)] + [struct.pack('<HHHH', new, blk, nv, 0)]
        rr.sort(key=lambda r: struct.unpack_from('<H', r)[0])
        t7 = bytearray(t7[:4]) + struct.pack('<I', m7 + 1) + b''.join(rr) + t7[8 + m7 * 8:]
        rows[new] = (blk, nv)
        print('motion %d -> block %d variant %d (new row)' % (new, blk, nv))
    m, = struct.unpack_from('<I', c, 4)
    offs = list(struct.unpack_from('<%dI' % m, c, 8))
    o = offs[blk]
    head, evs, ones = _events(c, o)
    old_size = struct.unpack_from('<H', c, o + 6)[0]
    hit = lambda e: e[4] in (0x00, 0x43)
    for e in evs:                                        # base-only: its hits and continue windows
        if e[6] == 0 and (hit(e) or e[4] == 0x01):
            e[6] = bv
    add = []
    if spec.get('hits') == 'copy':
        evs = [e for e in evs if not (hit(e) and e[6] == nv)]       # rebuilt every run (hit ids may change)
        base_hits = [e for e in evs if hit(e) and e[6] == bv]
        last = max(range(len(base_hits)), key=lambda i: struct.unpack_from('<H', base_hits[i], 0)[0]) if base_hits else -1
        for i, e in enumerate(base_hits):
            ne = bytearray(e)
            ne[6] = nv
            hid = struct.unpack_from('<I', ne, 12)[0]
            if hid in spec.get('replace', {}):
                struct.pack_into('<I', ne, 12, spec['replace'][hid])
            if 'last' in spec and i == last:
                struct.pack_into('<I', ne, 12, spec['last'])
            add.append(ne)
    if spec.get('lunge') and not any(e[4] == 0x39 and e[6] == nv for e in evs):
        add += [bytearray(e[:6]) + bytes([nv]) + e[7:] for e in evs if e[4] == 0x39 and e[6] == bv]
    if 'window' in spec and not any(e[4] == 0x01 and e[6] == nv for e in evs):   # combo can continue (link pieces)
        add.append(bytearray(struct.pack('<HHBB6sI', spec['window'][0], spec['window'][1], 1, 1,
                                         bytes([nv, 0, 0, 0, 0, 0]), 0)))
    if 'free' in spec:
        for e in evs:
            if e[4] == 0x28 and e[6] == nv:
                struct.pack_into('<H', e, 0, spec['free'])
    evs += add
    body = b''.join(evs)
    head[2] = len(evs)
    struct.pack_into('<HH', head, 4, 8 + len(body), 8 + len(body) + len(ones))
    blkb = bytes(head) + body + ones
    c[o:o + old_size] = blkb
    offs = [x + len(blkb) - old_size if x > o else x for x in offs]
    struct.pack_into('<%dI' % m, c, 8, *offs)
    print('motion %d / %d (block %d): variants %d / %d, +%d events' % (base, new, blk, bv, nv, len(add)))
    return t7, c


def main():
    iso = sys.argv[1]
    use_iso(iso)
    st, sz = pkg_offset(FILE)
    with open(iso, 'rb') as f:
        d = read_at(f, st, sz)
    n, = struct.unpack_from('<I', d, 4)
    ch = [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]
    i7 = next(k for k, c in enumerate(ch) if c[0] == 7)
    i8 = next(k for k, c in enumerate(ch) if c[0] == 8)
    t7 = d[ch[i7][2]:ch[i7][2] + ch[i7][3]]
    m7, = struct.unpack_from('<I', t7, 4)
    rows = {struct.unpack_from('<H', t7, 8 + k * 8)[0]: struct.unpack_from('<HH', t7, 10 + k * 8) for k in range(m7)}
    c = bytearray(d[ch[i8][2]:ch[i8][2] + ch[i8][3]])
    t7 = bytearray(t7)
    for mid, (blk, tpl) in SLOTS.items():
        m, = struct.unpack_from('<I', c, 4)
        if blk >= m:
            assert blk == m, 'new slots must be added in order (next block %d)' % m
            offs = list(struct.unpack_from('<%dI' % m, c, 8))
            so = offs[rows[tpl][0]]
            new = bytearray(c[so:so + struct.unpack_from('<H', c, so + 6)[0]])
            new[0] = blk
            body = c[8 + 4 * m:]
            body += b'\0' * ((-len(body)) % 4)
            offs = [o + 4 for o in offs] + [8 + 4 * (m + 1) + len(body)]
            c = bytearray(struct.pack('<II', struct.unpack_from('<I', c, 0)[0], m + 1)) + \
                struct.pack('<%dI' % (m + 1), *offs) + body + new
            print('block %d added (copy of motion %d\'s block %d)' % (blk, tpl, rows[tpl][0]))
        if mid not in rows:
            m7, = struct.unpack_from('<I', t7, 4)
            rr = [bytes(t7[8 + k * 8:16 + k * 8]) for k in range(m7)] + [struct.pack('<HHHH', mid, blk, 0, 0)]
            rr.sort(key=lambda r: struct.unpack_from('<H', r)[0])
            t7 = bytearray(t7[:4]) + struct.pack('<I', m7 + 1) + b''.join(rr) + t7[8 + m7 * 8:]
            rows[mid] = (blk, 0)
            print('motion %d -> block %d' % (mid, blk))
    for dst, (src, remap) in COPY.items():
        m, = struct.unpack_from('<I', c, 4)
        offs = list(struct.unpack_from('<%dI' % m, c, 8))
        bd, bs = rows[dst][0], rows[src][0]
        new = bytearray(c[offs[bs]:offs[bs] + struct.unpack_from('<H', c, offs[bs] + 6)[0]])
        new[0] = c[offs[bd]]
        k = 8
        for _ in range(new[2]):
            fr, to = struct.unpack_from('<HH', new, k)
            if new[k + 4] in (0, 0x43) and new[k + 5]:
                h, = struct.unpack_from('<I', new, k + 12)
                if h in remap:
                    struct.pack_into('<I', new, k + 12, remap[h])
            if dst in SCALE:
                f = SCALE[dst]
                struct.pack_into('<HH', new, k, int(fr * f), to if to == 0xFFFF else max(int(fr * f), int(to * f)))
            k += 12 + 4 * new[k + 5]
        # one-shot list (sounds, shakes, camera, magi; notes/hitbox-shapes.md §10): u16 frame, u8 op, u8 n, 4 cond, params
        e1, = struct.unpack_from('<H', new, 4)
        recs, k = [], e1
        for _ in range(new[3]):
            rec = bytearray(new[k:k + 8 + 4 * new[k + 3]])
            k += len(rec)
            if rec[2] == 4 and struct.unpack_from('<I', rec, 8)[0] in DROP_MAGI.get(dst, ()):
                continue
            if dst in SCALE:
                struct.pack_into('<H', rec, 0, int(struct.unpack_from('<H', rec, 0)[0] * SCALE[dst]))
            recs.append(rec)
        new = new[:e1] + b''.join(recs)
        new[3] = len(recs)
        struct.pack_into('<H', new, 6, len(new))
        old = struct.unpack_from('<H', c, offs[bd] + 6)[0]
        if c[offs[bd]:offs[bd] + old] == new:
            print('motion %d (block %d): already a copy of motion %d' % (dst, bd, src))
            continue
        o = offs[bd]
        c[o:o + old] = new
        offs = [x + len(new) - old if x > o else x for x in offs]
        struct.pack_into('<%dI' % m, c, 8, *offs)
        print('motion %d (block %d) <- copy of motion %d (block %d), %d -> %d bytes' % (dst, bd, src, bs, old, len(new)))
    lunge = None
    m, = struct.unpack_from('<I', c, 4)
    offs = list(struct.unpack_from('<%dI' % m, c, 8))
    o = offs[rows[10000][0]]
    k = o + 8
    for _ in range(c[o + 2]):
        if c[k + 4] == 0x39:
            lunge = bytes(c[k + 12:k + 12 + 4 * c[k + 5]])
        k += 12 + 4 * c[k + 5]
    for mid, (fr, to) in ADVANCE.items():
        blk, var = rows[mid]
        m, = struct.unpack_from('<I', c, 4)
        offs = list(struct.unpack_from('<%dI' % m, c, 8))
        o = offs[blk]
        k = o + 8
        has = False
        for _ in range(c[o + 2]):
            has |= c[k + 4] == 0x39
            k += 12 + 4 * c[k + 5]
        if has:
            print('motion %d (block %d): already lunges' % (mid, blk))
            continue
        ev = struct.pack('<HHBB6s', fr, to, 0x39, len(lunge) // 4, bytes([var, 0, 0, 0, 0, 0])) + lunge
        c[k:k] = ev
        c[o + 2] += 1
        s1, s2 = struct.unpack_from('<HH', c, o + 4)
        struct.pack_into('<HH', c, o + 4, s1 + len(ev), s2 + len(ev))
        offs = [x + len(ev) if x > o else x for x in offs]
        struct.pack_into('<%dI' % m, c, 8, *offs)
        print('motion %d (block %d): lunge toward the foe %d-%d' % (mid, blk, fr, to))
    for dst, spec in AUTHOR.items():
        m, = struct.unpack_from('<I', c, 4)
        offs = list(struct.unpack_from('<%dI' % m, c, 8))
        bd, bs = rows[dst][0], rows[spec['tpl']][0]
        src = bytes(c[offs[bs]:offs[bs] + struct.unpack_from('<H', c, offs[bs] + 6)[0]])
        mains, k = [], 8
        for _ in range(src[2]):
            n4 = 12 + 4 * src[k + 5]
            mains.append(bytearray(src[k:k + n4]))
            k += n4
        e1, = struct.unpack_from('<H', src, 4)
        ones, k = [], e1
        for _ in range(src[3]):
            n4 = 8 + 4 * src[k + 3]
            ones.append(bytearray(src[k:k + n4]))
            k += n4
        hitev = [e for e in mains if e[4] in (0, 0x43)]
        h0 = min(struct.unpack_from('<H', e, 0)[0] for e in hitev)
        h1 = max(struct.unpack_from('<H', e, 2)[0] for e in hitev)
        ends = [struct.unpack_from('<H', e, 0)[0] for e in mains if e[4] == 0x28] + \
               [struct.unpack_from('<H', e, 0)[0] for e in ones if e[2] == 0x02]
        E = max(ends + [h1 + 1])
        n0, n1, nE = spec['hits'][0][0], max(h[1] for h in spec['hits']), spec['end']
        kx, ky = [0, h0, h1, E], [0, n0, n1, nE]

        def remap(f):
            if f == 0xFFFF:
                return f
            if f >= E:
                return max(0, f - E + nE)
            for i in range(3):
                if kx[i] <= f <= kx[i + 1]:
                    t = (f - kx[i]) / max(1, kx[i + 1] - kx[i])
                    return int(round(ky[i] + t * (ky[i + 1] - ky[i])))
            return f
        out = []
        for e in mains:
            # template hits, its continue window (WINDOWS adds our own) and op 0x59 = "chain ends here" (Cloud's enders
            # had it: authored Horizontal Slash pieces could only continue for ~9 frames, test 139)
            if e[4] in (0, 0x43, 0x01, 0x59):
                continue
            if spec.get('nolunge') and e[4] == 0x39:        # FRONT hits sit 1.8 m ahead: no template lunge (closes to ~0.5 m)
                continue
            if spec.get('nodash') and e[4] == 0x02 and struct.unpack_from('<I', e, 12)[0] == 4:   # op 0x02 mode 4 = dash
                continue
            fr, to = struct.unpack_from('<HH', e, 0)
            struct.pack_into('<HH', e, 0, remap(fr), max(remap(fr), remap(to)) if to != 0xFFFF else to)
            out.append(e)
        for fr, to in spec.get('lunge', []):                # lunge toward the foe (NEAR1's op 0x39) before slashes
            out.append(bytearray(struct.pack('<HHBB6s', fr, to, 0x39, len(lunge) // 4, bytes(6)) + lunge))
        for fr, to, hid, shape in spec['hits']:
            out.append(bytearray(struct.pack('<HHBB6sII', fr, to, 0, 2, bytes(6), hid, shape)))
        if 'cancel' in spec:                                # op 0x22 (other actions may cut in) from this frame
            for e in out:
                if e[4] == 0x22:
                    struct.pack_into('<H', e, 0, spec['cancel'])
        if 'free' in spec:                                  # combo pieces: stay in the move until the window is used
            for e in out:                                   # (test 135: free at 45 vs window 40 → presses started a
                if e[4] == 0x28:                            # NEW combo instead of the finisher)
                    struct.pack_into('<H', e, 0, spec['free'])
        for e in ones:
            struct.pack_into('<H', e, 0, remap(struct.unpack_from('<H', e, 0)[0]))
        for fr, op, pars in spec.get('ones', []):            # extra one-shots, e.g. op 0x19 = effect by id
            ones.append(bytearray(struct.pack('<HBB4s%dI' % len(pars), fr, op, len(pars), bytes(4), *pars)))
        new = bytearray(src[:8])
        new[0] = c[offs[bd]]
        new[2], new[3] = len(out), len(ones)
        body = b''.join(out)
        struct.pack_into('<HH', new, 4, 8 + len(body), 8 + len(body) + sum(map(len, ones)))
        new += body + b''.join(ones)
        o = offs[bd]
        old = struct.unpack_from('<H', c, o + 6)[0]
        if c[o:o + old] == new:
            print('motion %d (block %d): already authored' % (dst, bd))
            continue
        c[o:o + old] = new
        offs = [x + len(new) - old if x > o else x for x in offs]
        struct.pack_into('<%dI' % m, c, 8, *offs)
        print('motion %d (block %d) authored from motion %d: hits %s, end %d' %
              (dst, bd, spec['tpl'], [(h[0], h[1], hex(h[2])) for h in spec['hits']], nE))
    for mid, (fr, to) in WINDOWS.items():
        blk, var = rows[mid]
        m, = struct.unpack_from('<I', c, 4)
        offs = list(struct.unpack_from('<%dI' % m, c, 8))
        o = offs[blk]
        cnt = c[o + 2]
        k = o + 8
        has = False
        for _ in range(cnt):
            if c[k + 4] == 1 and c[k + 6] in (0, var):
                has = True
            k += 12 + 4 * c[k + 5]
        if has:
            print('motion %d (block %d): already has a continue window' % (mid, blk))
            continue
        ev = struct.pack('<HHBB6sI', fr, to, 1, 1, bytes([var, 0, 0, 0, 0, 0]), 0)
        c[k:k] = ev                                       # after the last event
        c[o + 2] = cnt + 1
        s1, s2 = struct.unpack_from('<HH', c, o + 4)
        struct.pack_into('<HH', c, o + 4, s1 + len(ev), s2 + len(ev))
        offs = [x + len(ev) if x > o else x for x in offs]
        struct.pack_into('<%dI' % m, c, 8, *offs)
        print('motion %d (block %d, variant %d): continue window %d-%d added' % (mid, blk, var, fr, to))
    for spec in VARIANTS:
        t7, c = variant(t7, c, rows, spec)
    out = rebuild_arc(d, {i7: bytes(t7), i8: bytes(c)})
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'f.objx')
        open(p, 'wb').write(out)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main()
