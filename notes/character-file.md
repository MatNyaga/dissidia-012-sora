# Character battle file — Cloud (owner 13, internal name `sev100`), 2026-10-12

Found by scanning for Cloud's action ids (`tools/scripts/find_action_table.py`).
Two files hold the same move list:
- `dumps/package/03394_4e88d7ff_t1.bin` (1.35 MB, ARC, 19 chunks) — full battle file (model, effects, sound).
- `dumps/package/05973_89b1e0c7_t1.bin` (68 KB, ARC, 12 chunks) — light copy (no model/effects). Assist or menu preview? Unknown.
Real file names: unknown yet (hash = CRC-32/BZIP2 of the lowercase path, see `tools/scripts/pkghash.py`).

ARC entries here: u32 type, char[4] short tag, u32 offset, u32 size.

| type | tag | size | what (guess) |
|------|-----|------|--------------|
| 7  | p_se | 968    | ? |
| 8  | p_se | 33844  | ? (motion list?) |
| 5  | p_se | 1904   | ? |
| 6  | p_se | 644    | ? |
| 9  | p_se | 9814   | "hibg"… |
| 4  | effe | 848640 | effects (MPK) |
| 14 | snd_ | 339376 | sound bank (SSCF) |
| 1  | **plya** | 3836 | attack pieces? first entry has piece id 0x5BE |
| 1  | **comb** | 468  | **action (move) table** — see below |
| 1  | **atkp** | 4292 | attack params (63 entries?) |
| 1  | magi | 5720   | projectiles / magic ("MAGI") |
| 1  | brat | 636    | ? ("atta…") |
| 1  | text | 1612   | text ("mlng") |
| 3  | wind | 3356   | GIM texture |
| 3/17/13 | spec | … | "mlng" text / misc |
| 18 | d_se | 120    | nested ARC |
| 2  | d_se | 23960  | GMO model ("OMG.00.1PSP") |

## comb = action table
```
u16 6 (version?)   u16 count (18 for Cloud)   u32 offset[count]  (from table start)
entry:
  u16 action id      (matches ablt +12; this is what equipping switches on)
  u16 n              number of steps
  i16 alt id         (+4, also matched by FUN_08ab7f40)
  i16 parent id      (+6, e.g. 315's parent is 314 → follow-up / variant)
  n × 8 bytes: u32 piece id (0x5BE…, 0x85B…, 0xB30…), u16 0xFFFF, u8 flag, u8 0
```
Cloud: ids 313–328 + 927, 928. Example: 314 = 3 pieces 0x5BE, 0x5BF, 0x5C0 (a 3-hit chain).
The last entry (928) runs into the `atkp` chunk, so its length is just "rest of the chunk".

## How a move is chosen (current understanding)
ability (ablt row) --+12--> action id --enables--> comb entry --> pieces (plya?) --> attack params (atkp?)
So a NEW move = new comb entry (+ pieces) + an ablt row (18 free slots) pointing at its id.

## Test 4 — `dumps/ULUS10566-test4-cloud-comb.iso` (2026-10-12) ✅
ablt back to original. Cloud comb (pkg 3394 + 5973): every step of ground Bravery actions 313, 314, 316, 318, 319, 320
→ piece 0x5C4 (the single piece of action 317).
Result: **only Cloud's ground Bravery attack changed**; HP, air, everything else normal, no crash.
→ **Editing `comb` piece ids changes what a move does.** Stage 1 step "change a move" = done.

## Test 5 — `dumps/ULUS10566-test5-new-move.iso` (2026-10-12): first brand-new move
- Cloud files (pkg 3394, 5973) restored to original, then `tools/scripts/comb_add.py` appended a NEW comb entry:
  **action 1020 = pieces 0x5BE, 0x5BF (first two hits of 314) + 0x5C4 (piece of 317)**.
  comb 18 → 19 entries, file +48 bytes (fits the 1400/1508 padding), later chunks shifted by 48 (16-alignment kept),
  all other chunks byte-identical, PACKAGE_INFO.BIN size updated inside the ISO (sector 26000).
- ablt row 209 (Cloud idx 0, his neutral ground Bravery) +12: 313 → 1020.
- Expected: Cloud's neutral ground Bravery does 2 hits of the 314 combo, then the 317 attack.
Result: ✅ **new action 1020 runs** (2 hits) — but the 3rd piece (0x5C4) does NOT play.

## plya = attack pieces
Header: u32 0x16, u32 count (33 for Cloud). Entries 116 bytes:
  +0 u16 piece id, +2 u8 ?, +3 u8 **role: 0 starter, 1 follow-up, 2 chase**,
  +0x0e u8 kind (0 near, 1/2 long/dash, 3/4/5 HP finisher), +0x0f u8 (1 Bravery, 2 HP),
  +0x1c u16 0x27xx id (hit/atkp link?), floats…, +0x64 char[16] name (LAND_NEAR1, AIR_FINISH2, …).
More plya fields (from the game code, 2026-10-12):
  +5 u8 **where Cloud must be**: 0 either, 1 must be in the AIR, 2 must be on the GROUND (checked by FUN_08847f10)
  +6 u8 where the target must be (same values)
  +0x18 u32 flags: 0x2 = skip the distance check, 0x80 = air move, 0x10 = HP, 0x400/0x800 special
  +0x24/+0x28 f32 distance min/max, +0x2c/+0x30 height window (FUN_08847e08)

## How the next hit is picked (FUN_08849700 → FUN_08848984 / FUN_08848160)
1. If the current animation script added "allowed next pieces" (script opcode 'g' / 'y', list at char+0x1028,
   count char+0x1068), only those are tried. **Cloud's scripts have no 'g' events**, other fighters do.
2. Otherwise (Cloud): every plya piece with **role 1 or 4** is a candidate, if it passes FUN_08847f10
   (ground/air rule above), the distance check, and **FUN_08ab81e0**: some *enabled* comb action has
   step[k] = candidate and step[k-1] = current piece, inside the step's frame window.
comb step is really: u16 piece, u16 min frame, i16 max frame (-1 = none), u8 flag, u8 0.
Animation scripts: p_se type-8 chunk = u32 3, u32 count, u32 offsets[count]; each block:
  u8,u8, u8 event count, u8, u16 size1, u16 size; events at +8: u16 frame from, u16 frame to (0xFFFF open),
  u8 opcode, u8 n params, 6 bytes conditions, n × u32 params. Runner: FUN_08829930, scheduler FUN_08828eec.

Why test 5 stopped: 0x5C4 LAND_LONG1 is role 0 (a starter), never a follow-up candidate.
Why test 6 stopped: 0x5C3 LAND_MIDDLE3 has +5 = 1 (Cloud must be in the air). After NEAR2 he is on the ground.

## Test 6 — `dumps/ULUS10566-test6-mixed-combo.iso`
Same as test 5, but action 1020 = 0x5BE LAND_NEAR1, 0x5BF LAND_NEAR2, **0x5C3 LAND_MIDDLE3** (follow-up from another combo).
Result: ❌ still 2 hits (LAND_MIDDLE3 needs Cloud in the air, see above).

## Test 7 — `dumps/ULUS10566-test7-four-hit.iso`
Cloud files restored from the original ISO, then action 1020 = 0x5BE NEAR1, 0x5BF NEAR2, **0x5C2 LAND_MIDDLE2**
(role 1, +5 = 0 so ground is fine), 0x5C3 LAND_MIDDLE3 (air). ablt row 209 still → 1020. Only `comb` differs.
Expected: 4 hits, ending like his middle combo (MIDDLE2 should lift him so MIDDLE3 can play).
Result: ✅ **4 hits** (2026-10-12). Last two lift Cloud into the air, last hit knocks the opponent to the ground.
→ **Brand-new combos from existing pieces work.** Rule: each next piece must be a follow-up (role 1/4)
  and its +5 ground/air rule must match where Cloud is at that moment.

## atkp = hit table (one entry per hit; names match the plya pieces)
Header: u32 0xC, u32 count (63 for Cloud). Entries 68 bytes:
  +0x00 u32 hit id (LAND_NEAR1 = 0x35D …), +0x04 u8 kind (0 Bravery hit, 1–3 HP/finish, 4+ guard/dash/etc),
  +0x05 u8 reaction? (0x0C on launching hits), +0x10 u16 **power** ✅ (NEAR1 8, NEAR2 12, NEAR3 25, MIDDLE3 15;
  HP finishers 0), +0x12 u16 ?, +0x14 4 bytes (e.g. 0a 14 64 64 on HP hits), floats (knockback?), +0x34 char[16] name.
Same table in pkg 3394 and 5973. Tool: `tools/scripts/atkp_patch.py` (list / set-power).

## Test 8 — `dumps/ULUS10566-test8-big-damage.iso` (copy of test 7)
LAND_MIDDLE3 (last hit of action 1020) power 15 → 150 in both files. Test 7 ISO kept as the "working combo" copy.
Expected: last hit of Cloud's neutral ground Bravery does ~10× Bravery damage.
Result: ✅ last hit did **129** Bravery damage, far above the other hits (2026-10-12; may be capped by the
enemy's Bravery). → **atkp +0x10 u16 = hit power, confirmed.**
Reaction byte guesses (atkp +0x05): 0x07 slam down (LAND_MIDDLE3, matches test 7), 0x0C blow away (NEAR3, finishers),
0x01 small flinch, 0x0D/0x0B launch?, 0x04 push back?. Floats at +0x18..+0x2b look like knockback speed/height/distance.

## Test 9 — `dumps/ULUS10566-test9-knockback.iso` (copy of test 8)
LAND_MIDDLE3: reaction + bytes +0x14..+0x34 copied from LAND_NEAR3 (`atkp_patch.py copy-knockback`), power stays 150.
Expected: last hit blows the enemy far away (like NEAR3's finisher) instead of slamming them down.
Result: ✅ enemy flew far away into the wall (2026-10-12). → knockback lives in atkp +0x05 and +0x14..+0x34.
Not yet split field by field (which float = speed / height / distance).
Also seen in test 9: forward + Circle (action 316, ends with LAND_MIDDLE3) ALSO blew the enemy into the wall
→ proves hits are shared between moves.

## The full chain (2026-10-12)
comb step → **plya piece** → piece +0x1c **motion id** (0x27xx) → **p_se type 7** table
(u32 2, u32 count, sorted 8-byte rows: u16 motion id, u16 script block, u16 variant, u16 0; binary-searched)
→ **p_se type 8 script block** → event **op 0x00 = hitbox**, frames from–to, param0 = **atkp hit id**, param1 0x30
→ **atkp** entry (binary-searched by id, so ids must stay sorted).
Event +6 = **variant condition** (0 any). Example: block 45 (NEAR2 animation) hits 0x35E in variant 1 (motion 0x2711)
and 0x64E in variant 2 (motion 0x2714, LAND_NEAR2_2). Same animation, different hit.
Other ops seen: 0x12 param 0x15/0x3A (chase?), 0x20 (follow-up window?), 0x43 (multi-hit hitbox), 0x2A (effects by mode).
pkg 5973 has no attack scripts (type 7 only has 13 motions) → probably a lite/assist copy; 3394 is the real one.
Tools: `tools/scripts/arcfile.py` (rebuild an ARC in the ISO, grow chunks, keep 16-alignment, fix PACKAGE_INFO),
`tools/scripts/own_hit.py` (give a comb step its own piece + hit, sharing the animation).

## Test 10 — `dumps/ULUS10566-test10-own-hit.iso` (copy of test 7, original hit values)
`own_hit.py … 0x5c3 0xff0 0x27f0 0xff0 NEW_MIDDLE3 1020 3394 5973`, then NEW_MIDDLE3 power 150 + knockback from LAND_NEAR3.
- new atkp hit 0xFF0 NEW_MIDDLE3, new plya piece 0xFF0 (motion 0x27F0), type 7: 0x271C → (49, variant 1), 0x27F0 → (49, variant 2)
- block 49: old hitbox (0x362) variant 1 only, new hitbox (0xFF0) variant 2 only
- action 1020 last step → piece 0xFF0. LAND_MIDDLE3 itself back to original (power 15, slam down).
Expected: neutral Circle → last hit huge + blow away; forward Circle → normal slam down, normal damage.
If the variant guess is wrong: the last hit of BOTH moves does no damage.
Result: ✅ (2026-10-12) forward Circle back to normal; neutral Circle = 4 hits, last one blows the enemy into the wall.
→ **A move can now have its own hits.** Variant byte (+6) confirmed. New ids 0xFF0 (piece, hit) and motion 0x27F0 work.

## Knockback floats (atkp +0x18 f0, +0x1c f1, +0x20 f2, +0x24 f3, +0x28 f4) — guesses for reaction 0x0C (blow away)
NEAR3 0/30/8/25, AIR_FINISH2_3 0/20/-30/30 (slams down), AIR_FINISH3_4 0/-15/-35/30.
Guess: f1 = sideways push (negative = toward attacker), f2 = up push (negative = down), f3 = flight time/distance.
Reaction 0x07 (slam): f0 = 20/30 (down speed?), f2 = 1.5. Reaction 0x04 (push): f1 = 4–6, f2 = 0.4–0.5.

## Test 11 — `dumps/ULUS10566-test11-launch-up.iso` (copy of test 10)
NEW_MIDDLE3: +0x1c 30 → 0, +0x20 8 → 40 (`atkp_patch.py set-float`). Expected: enemy flies straight up.
Result: ✅ straight up, high (2026-10-12). → **+0x1c = sideways push, +0x20 = up push** (for reaction 0x0C).

## Test 12 — `dumps/ULUS10566-test12-flight-time.iso` (copy of test 11)
NEW_MIDDLE3: +0x24 25 → 5 (still sideways 0, up 40). Guess: +0x24 = flight time/distance → enemy pops up only a little.
Result: ❓ can't tell — up 40 throws the enemy off screen. File renamed/reused as test 13a.

## Test 13a/13b — `dumps/ULUS10566-test13a-time25.iso`, `dumps/ULUS10566-test13b-time100.iso`
NEW_MIDDLE3: sideways 0, up 15 (stays on screen). 13a: +0x24 = 25, 13b: +0x24 = 100. Only difference is +0x24.
Result: ✅ 13b enemy stayed in the air much, much longer (2026-10-12). → **+0x24 = flight time** (blow-away hits).

### Knockback summary for reaction 0x0C (blow away), confirmed in game
| offset | meaning | NEAR3 value |
|---|---|---|
| +0x05 | reaction type (0x0C blow away, 0x07 slam down) | 0x0C |
| +0x10 | power (u16) | 25 |
| +0x1c | sideways push (− = toward attacker) | 30 |
| +0x20 | up push (− = down) | 8 |
| +0x24 | flight time | 25 |
Still unknown: +0x18, +0x28, +0x14..+0x17 bytes (0a 14 64 64 on finishers — hitstop?), other reaction types.

## Parry idea (2026-10-13, unfinished)
- Sora's block (motion 470/471, script blocks 20/21) has op00 frames 0-36 with hit 0x30A GUARD (kind 4) = the guard
  area. atkp 0x349 GUARD_REF (kind 7, power 5) is not referenced by any script/plya → applied by code when a block
  repels a hit (attacker recoil = motion 911 seen right after S470).
- Test 77: GUARD_REF power 40 + LAND_NEAR3 knockback (atkp_patch.py) → inconclusive (Lightning rarely attacked into
  the block in `tools/scripts/ppparry.py` runs: 10 blocks, 0 reactions; normal disc 3 blocks, 0). Needs a test where
  the opponent attacks on cue (e.g. force the opponent's attack motion) and a Bravery read-out.
- Other route: add an op00 Bravery hitbox to block 20 (Reflect burst) — needs event insertion in a script block.

## KH2-style long combos (test 95/97, 2026-10-13) — tools/scripts/spot33_combos.py
Mat: Bravery gained grows with each hit; the chain ends in a finisher that can be chained (KH2 video "KH2 combat is
superior."). Link rule: after piece A, B can follow if an ENABLED action has (A, B) as NEIGHBOURS anywhere in its
step list (+ B role 1/4, ground/air rule) — so one action list can hold a small graph. Circle = Bravery pieces,
Square = HP pieces (plya +0x0f). Cloud's own action 315 = NEAR1 > NEAR2 > LAND_FINISH3 (Bravery→HP chain).
- #33 action 1020 (ground Circle): NEAR1 > NEAR2 > MIDDLE2 (lift) > NEW_MIDDLE3 (air) > AIR_NEAR2 > AIR_NEAR3,
  Square after AIR_NEAR3 → AIR_FINISH3 (air flurry HP), Square after NEAR2 → LAND_FINISH3 (= _703A, now Explosion).
- action 321 (air Circle): AIR_NEAR1 > AIR_NEAR2 > AIR_NEAR3 > Square AIR_FINISH3.
- Power ramp (atkp +0x10): NEAR1 6, NEAR2 8, MIDDLE2 11, NEW_MIDDLE3 14 (was 150 since test 8/10!), AIR_NEAR2 18,
  AIR_NEAR1_1/2/3 5/9/22. NEW_MIDDLE3 knockback ← LAND_NEAR2 (stagger instead of NEAR3's blow-away).
- Test 95 (high CPU load from other programs): the chain stopped after NEAR2 — not confirmed yet whether timing
  (load) or a rule; to retest with ppcombo.py (now stops pressing when the battle is over).
- Test 101 (`dumps/ULUS10566-test101-kh2combo.iso`): KH2 Combo-Plus chain (Mat: 6-7 ground, 10+ air). Ground Circle:
  NEAR1 > NEAR2 > NEAR1_2 > NEAR4 > NEAR3 > MIDDLE2 (launch) > NEW_MIDDLE3 > AIR_NEAR2 > AIR_NEAR3 > BR_A_REN1 >
  BR_A_REN2 > AIR_MIDDLE1 (finisher, blow away) = 12 hits; anims KH2 604,608,612,616,620,648 / 732,728,768,764,772,776.
  Square links: NEAR2/NEAR4 → LAND_FINISH3 spin, AIR_NEAR3/REN2 → AIR_FINISH3. Combo hits get light reactions
  (copied from LAND_NEAR1 / AIR_NEAR1_1), power ramp 6..17. op01 continue windows added to NEAR4, NEAR3, REN2
  (spot33_chain.py). plya role → 1 for NEAR1_2, NEAR4, BR_A_REN1. Not tested yet.
- Test 102: hits 5-6 sped up (LAND_NEAR3 block shifted 20 → hit 14-22, window 22-52; launcher MIDDLE2 window 32→18; _602A anim hit 18). Mat: hits 5+ were WAY too slow in 101.
- Test 104: chain order N1 N2 N1_2 N3 N4 M2 … (LAND_NEAR4 ends airborne, so ground-only NEAR3 could not follow it; Mat: 4 perfect hits, then the chain broke into a new air combo).
- Test 105: hit 4 (NEAR3) later (hit 14-22, window 22-52), _602A :match=38 (Keyblade on Cloud's hitbox path), reach 2.0→4.0. Mat (on 104): landed it once, window tight.
- Test 106: hits 8/9 (AIR_NEAR2/3) later (hits 14-24 / 14-22, windows 24 / 22), reach 6, height ±6 for air chain pieces (+ finisher ±10). Mat (105): 7 hits smooth, 8th missed.
- Test 107: plya +0x18 flag 0x200000 = needs stick UP (0x400000 DOWN; Cloud's AIR_NEAR2 = up-air). Mat's log: chain stopped after NEW_MIDDLE3, then a fresh AIR_NEAR1. AIR_NEAR2 flags → 0x10002.
- ✅ Test 107: Mat — the full long combo works, perfect. Recipe: comb chain + op01 windows + light reactions + hits at ~frame 10-14 + Keyblade :match at the hit + reach/height + no direction flags.

## plya / atkp fields learned 2026-10-14 night (test 150-153)
- plya (116-B pieces): +3 role (0 starter, 1 follow-up, 2 chase), +5 ground/air (2 ground, 1 air, 0 both),
  +0x0f button (1 Circle, 2 Square), +0x10 landing motion, +0x1c u16 motion id, **+0x1e u16 motion after the move
  ends** (1 idle for ground moves, 0x65 = 101 fall for air moves). A ground move with 101 there leaves the fighter in
  the fall motion forever on the ground (landing needs fighter +0x384 & 0x200 clear, which is the "on ground" bit).
  Seen with Upper Slash on Cloud's LAND_FINISH3 piece (spot33_combos.py AFTER).
- atkp reaction +5: 0x07 = crumple on the spot (Braver shockwave AIR_FINISH1_4), 0x0c = blow away along
  floats +0x1c (forward push) / +0x20 (UP push, negative = slam down), 0x01 flinch, 0x0d air flinch, 0x04 push back.
  Upper Slash (0x0c, +0x14 `00 14 64 64`, floats 0/2/6/30) ≈ 6-9 m straight up; 30 up ≈ 18 m.
- Live tuning: the fighter file's atkp rows sit in RAM (one copy per fighter using the file); find them by name in a
  ppsnap dump (name at entry +0x34) and write memory.write — takes effect on the next hit, no rebuild.
