# Thundaga redo (2026-10-16, Claude Thunder helper; Mat's direct request)

Mat: Codex Thunder v1/v2 went UP, did no damage, the air cast crashed. Canonical Thundaga ships now.
Wanted: KH2 Thundaga feel = bolts come DOWN from above onto the target, deal damage, safe on ground AND air casts.
"Even Garland has thunder" -> Garland is the donor/template for HOW the bolt is placed on the target.

## 1. Garland's thunder (owner 2, obj/p_one200.objx, clean ISO, read-only)
- Move: piece 0xb68 **BR_A_THUNDAGA1** = his AIR Bravery "Thundaga", motion 10030, block 55.
  Hit atkp 0xc00 R_A_THUNDAGA1_1 (kind 7 = Bravery ranged, flags 0x84).
- Block 55 one-shot spawns (op 0x04): f0 / f10 / f20 / f26 magi 0x804, f26 magi 0x803.
- Magi chain (K = parameter triple, see section 2):
  | magi | role | type (+0x1e) | kids | key params |
  |---|---|---|---|---|
  | 0x803 | marker | 11 = at the TARGET | 0x83c | count 1, life 1, clamp H 0..30 m, V -15..15 m |
  | 0x83c | "appear" flashes, fx 9 -> THUNDER_APP | 5 = at parent | - | count 3, every 2, ring r 0.5 turning 60 deg |
  | 0x804 | tracking marker (bullet class 0) | 11 = at the TARGET, dir 4 (aim) | 0x86f | life 56, clamp H 30 / V +-15 |
  | 0x86f | delay | 5 | 0x802 | life 2, r 1 / 5 |
  | 0x802 | the strike, fx 10 -> THUNDER_BODY1 + HIT, hit 0xc00 | 5 = stationary at parent | - | r 1 / 5, life 10 |
- So Garland's bolt is NOT a flying projectile: a marker is put on the target (type 11), and the strike is a
  stationary column (type 5) at the marker. The falling look is inside his effect tree.
- His effect trees: leaves 59 THUNDER_EISYO (cast), 60 EISYO_WEP, 61 THUNDER_APP, 62 THUNDER_BODY1, 63 THUNDER_HIT,
  70 THUNDER_KATA (FEPA rows 75-79, 87-88). They use only GLOBAL textures (G5/G7/G81/G83/G86/G89/G8a/Gb) and node
  kinds 0x150/0x130/0x66/0x91/0x44/0x6e/0xe7 (several not in Sora's FEP). Not transplanted (see section 4).

## 2. magi parameter triples — corrected decode (dumps/decomp + Ghidra re-decompile of FUN_08ad5d70)
Row bytes +0x40.. = 46 triples (min, max, delta) of float-table indexes. Triple K is stored at magi object +0x44+4K
(FUN_08ad0694: value = random(min..max) at spawn; on each later emission value += delta, or re-rolled if delta = 0).
The old "p0-8 = spawn offset x/y/z" guess (spot33_thunder 2026-10-15) was WRONG:
| K (bytes) | meaning | source |
|---|---|---|
| K0 (p0-2) | bullet COUNT per magi object (int) | FUN_08ad032c: obj+0x2c = K0 as an integer |
| K1 (p3-5) | delay before the first bullet | obj+0x34 = K1 |
| K2 (p6-8) | interval between bullets | FUN_08ad1588: timer = K2 after each emission |
| K3 / K4 (p9-14) | ring offset: radius K3, turned K4 degrees around the up axis (rotY) | FUN_08ad5d70 tail |
| K5 / K6 / K7 (p15-23) | offset right / UP / forward in the spawn basis | FUN_08ad5d70 tail |
| K8 / K9 (p24-29) | pitch (rotX; + = DOWN, - = up) / yaw of the travel direction | FUN_08ad5d70 tail |
| K19 (p57-59) | speed | (canonical evidence) |
| K30 / K31 / K32 (p90-98) | +0x0e child magi: how many / first delay / interval (FUN_08ad384c reads K32 bytes +0xa0..a2) | Q005 trace: one 0x7C5 at c+6 with K30 1, K31 3 |
| K33-K36 (p99-110) | target clamp: horizontal min/max, vertical min/max (types 3/4/8/9/11/12) | FUN_08ad3a2c |
| K43 (p129-131) | life | |
- Spawn basis (FUN_08ad5d70): position from type (+0x1e: 0 caster feet, 5 parent, 11 target feet clamped ...),
  direction from +0x22 (1 = caster facing, 3 = parent, 4 = aim at the target, 0 = keep the type's: caster facing for
  type 0, TARGET's facing for type 11). up = world up; right = up x dir; pos += K5*right + K6*up + K7*dir + ring.
  Travel dir = basis * rotX(K8) * (0,0,1), then yaw K9.
- This explains every Thunder result so far:
  - canonical 0x7C4: type 0, dir 1, K6 = 7, K8 = +60 -> starts 7 m above SORA, flies down-forward (Q005 trace) and hits.
  - Codex v1 0x7C4: type 11, dir 0, K6 = 3, K8 = **-89.9 = straight UP** -> starts 3 m above the foe, flies up, no hit.
  - old spot33_thunder 0x7C5 / 0x7CA: K0 = random(-0.5..0.5) -> **count 0** -> they never emit (Q005: "spawned and
    freed in the same frame"). They are harmless no-ops.
- Codex v2's air crash = its malformed leaf-23 node (state size 224 instead of 256; Codex FINDINGS), not magi.

## 3. What was built: tools/scripts/spot33_thundaga.py -> test287 (2026-10-16T15:40Z, static, NOT played)
Name: `spot33_thunder.py` already exists (2026-10-15, in build_sora.sh: 0x7C5/0x7CA no-op rows, Blizzaga single ball,
Thundaga min distance) -> the new step is `spot33_thundaga.py`. They touch different fields; both say "already set"
on each other's output.
- Only magi rows 0x7C4 (ground strike, block 98 f34) and 0x7C9 (air strike, after launcher 0x7C8, block 101 f30).
  Same hit 0x1008 (HP), same fx bit 4 (Lightning bolt leaf 22 + flashes leaf 23), same speed / life / impact children
  0x7C6 / 0x7C7 (r 2 m, HP hit at the landing point). Changed fields (guarded: canonical or new value only):
  | field | canonical 0x7C4 / 0x7C9 | new (both) |
  |---|---|---|
  | +0x1e type | 0 (Sora's feet) / 5 (the rising launcher) | **11 = the target's feet** (Garland's placement) |
  | K6 up offset | 7 / 0 | **9 m** above the target |
  | K7 forward | 0.5 / 0 | 0 |
  | K8 pitch | +60 (down-forward) | **+89.9 = straight down** (float appended; table 49 -> 50) |
  | K0 / K2 count / interval | 1 / - | **3 bolts, 6 apart** |
  | K3 / K4 ring | - | radius 0, +0.85, +1.7 m at 0 / 150 / 300 deg (bolt 1 exactly on the target) |
  | K34 / K35 / K36 clamp | 9999 / 0 / 9999 | horizontal max 30 m, vertical -15..15 m (Garland's) |
- Each bolt reads the target position when it is emitted -> later bolts follow a moving foe. Flag 0x40000 (kept)
  stops the remaining bolts if Sora is hit.
- No effe / FEP / texture / sound / script-block change -> no alignment/serial risk; TEX count 21, effe 848,640 B.
  objx chunk check vs test286: only the magi chunk differs (8780 -> 8784 B, same chunk offsets, objx size same).
- Env knobs for bisects: THUNDER_BOLTS, THUNDER_HEIGHT, THUNDER_GAP, THUNDER_SPREAD, THUNDER_RANGE.
- Disc: `dumps/ULUS10566-test287-thunder.iso` = test286 + spot33_thundaga only
  (sha256 a31b165358c18d591a8303e1c50f7f3967d131eb45bfdf81e04c367abc35e2da, 42 bytes differ from test286).
- Previews (offline, `tools/scripts/preview_thundaga.py ISO OUTDIR`): dumps/renders/thunder/thundaga_paths.png
  (old / Codex v1 / new paths, ground + air, top view with hit radii), thundaga_fall.png (the disc's bolt mesh +
  texture falling onto a 1.7 m foe). Speeds there are estimates from the Q005 trace.

## 4. Why not Garland's effect trees (yet)
- His look = leaves 61/62/63 (global textures only) but node kinds 0x150/0x130/0x66 that Sora's FEP lacks. The
  old Lightning tree freeze (test200) was most likely the 16-byte alignment bug (same symptom: freeze on the first
  Bravery swing), so a transplant is now possible with spot33_magnet.align_layout()/renumber_serials() — but it is a
  separate risk. test287 keeps the look the same so Mat tests ONLY the new path/damage first.
- If Mat wants Garland's look after that: copy leaves 62 (body) / 63 (hit) into dead Sora leaves (not 16/20/39/51/52
  and not FEPA 10/14/55/56/9120-9141), point FEPA rows 31/32 at them, keep effe 848,640 B, align + renumber.

## 5. Runtime checklist (test287; nobody has run it)
Vs CPU Sora (CPU Minimal, Order's Sanctuary set explicitly):
1. Ground Thundaga at ~3 m, ~8 m, ~15 m: bolts fall from above STRAIGHT DOWN onto the foe (not from above Sora,
   not upward); 3 bolts, first one on the foe; HP damage lands (foe HP drops by Sora's Bravery).
2. AIR Thundaga (jump, cast) at the same ranges: same; no freeze/crash; Sora lands normally.
3. Foe in the air (jumping) while casting: bolt still drops on/through the foe.
4. Get hit during the cast: remaining bolts stop, no stuck state.
5. 10+ casts in a row, then normal combos: no freeze (watch PC 0x08964eac), effects clear.
6. Unchanged: Fire (Codex v3), Magnet Burst look + landing, EX barrier (Reflect), Trinity Limit, Blizzaga.
If the bolts go UP: K8 sign is wrong -> THUNDER pitch must be -89.9 (one value). If they spawn at Sora: type 11
fell back (no lock target). If no damage but the bolt shows: try THUNDER_BOLTS=1 / check the impact children.
- Runtime 2026-10-16T16:10:16Z (Claude, test-only 287t): air bolts fall at the target, no freeze; damage/ground cast still for Mat.
- Mat (2026-10-16T17:17:59Z): beat CPU Sora by spamming Thundaga → balance + CPU anti-magic (test296).

## 6. v2 = beatable Thundaga (test296, 2026-10-16T17:34Z, static, NOT played)
Mat (test294): "I beat the CPU by spamming thunder with Sora". Why v1 was a sure hit: each bolt was PLACED 9 m above
the foe when it was emitted and fell at 1 m/frame -> ~9 frames from the cast frame to the hit; nobody reacts that fast.
More decode (Ghidra re-decompile of FUN_08ad46f0 / FUN_08ad48e8 / FUN_08ad30cc / FUN_08ad3234 / FUN_08ad96f0):
| field | meaning |
|---|---|
| K14 / K15 / K16 / K17 | bullet SPEED (m per 60/s frame) / min / max / accel (0x7C4: 1.0 -> the measured 1.06 m/frame) |
| K19 / K20 / K21 / K22 | HOMING turn rate deg/frame / start / duration / stop distance (only if +0x28 = 1) |
| K25-K29 | bullet scale (effect + collision size) / min / max / growth / growth start |
| K30 / K31 / K32 | kid-0 (+0x0e) count / first delay / interval (kid 0 at spawn if K30 = 0 and no flag 0x20) |
| K43 / K44 | life (frames) / ? (Garland markers 9999) |
| +0x28 | 1 = homing, 2 = stationary (Garland's markers/flashes), 0 = straight |
| +0x12 / +0x14 | kids spawned on hit / on ground (impacts) |
| +0x3c 4 bytes | AI TAGS: the CPU's incoming-projectile check reads them (section 7) |
| flag 0x20 | spawn kid 0 when the bullet dies (else at spawn) |
| flag 0x200 | NO effect spawns (FUN_08ad32a8/08ad3350 skipped) — only on fx-less rows |
| flag 0x2 | no ground raycast; 0x8 = dies on ground (impacts); 0x40000 = stop + delete bullets if the caster is hurt (state 500-798) |
Time unit = 60/s frames (bullet age += 2 per 30 Hz update).
What v2 does (spot33_thundaga.py rewritten; accepts canonical / v1 / v2 input):
- MARKER 0x7C4 (ground, block 98 f34) / 0x7C9 (air, block 101 f30 now spawns it directly; launcher 0x7C8 unused):
  type 11 = put on the foe's feet ONCE, speed 0, life 26 frames, no hit, fx 4 at half size pointing down = a small
  crackling bolt column on the spot (= the WARNING; silent: leaf 22 has no FXSE), AI tag 0x14, flag 0x20 -> at its
  death it spawns the STRIKE.
- STRIKE 0x7C5 / 0x7CA (were count-0 no-ops): type 5 = the marker's spot (LOCKED, not the foe's new spot), 9 m up,
  pitch +89.9, 1 m/frame, NO homing (+0x28 0), 3 bolts 6 frames apart in a 0 / 0.85 / 1.7 m ring, HP hit 0x1008,
  Lightning bolt look, impacts on landing.
- Impacts 0x7C6 / 0x7C7 radius 2.0 -> 1.3 m (2.5 -> 1.6).
- End lag (op 0x28 "can act again"): ground 88 -> 96, air 59 -> 72 (air was only 29 frames after the cast).
- Getting hit cancels it: flag 0x40000 on marker and strike (FUN_08ad1588: caster state 500-798 -> bullets deleted,
  the marker's death spawn does not run).
Timeline (ground): input f0 -> marker f34 (warning) -> strike f60 -> bolt 1 lands ~f69, bolts 2/3 ~f75/f81; Sora
can act again at f96. A dodge/dash of >= ~2 m during the 26-frame warning (+ 9 frames fall) escapes all bolts.
Disc: `dumps/ULUS10566-test296-thunderbal.iso` = test294 (a01eeaf4…) + spot33_thundaga v2 only,
sha256 5ecb57f3d193491ede748ccbfbcd444b4edc71da3e54f947a001c52bae9cd17e (157 bytes differ; objx chunks magi + p_se
type 8 only; spot33_ai --dry = no change). Previews dumps/renders/thunder/v2/.
build_sora.sh: spot33_thundaga must stay AFTER spot33_thunder.py (that old step rewrites 0x7C5/0x7CA).
Knobs: THUNDER_DELAY / WARN_SCALE / BOLTS / HEIGHT / GAP / SPREAD / RANGE / IMPACT_R / END_GROUND / END_AIR.

## 7. How the CPU reacts to projectiles (static; for the AI helper, notes/cpu-ai.md)
- The AI scans the opponent's live magi bullets: FUN_08a827ac -> FUN_08adb4f0 -> FUN_08adb3f0(filter FUN_08adb8b0).
  Callers = AI behaviours FUN_08a6656c / 08a6bc4c / 08a70ea4 / 08a83590 / 08a9bae0 / 08a9d824 / 08a9f2a8 / 08aa141c.
- A bullet counts only if its magi row +0x3c AI TAGS hit FUN_08a82b8c's list (0-7, 9, 0xa, 0x10, 0x11, 0x14-0x21,
  0x23, 0x24, 0x26-0x29, 0x2b-0x2d; 0x12/0x22/0x25 in one mode). Threat distance (FUN_08adb5d8) = distance to the CPU
  - 3 (or to the bullet's hit shape) - CPU radius - 4 x bullet speed (x20 more for some tags) - CPU motion; threat if
  <= 3.0 (DAT_08a83a48), or 8.0 for tags 4/5/7/0x10/0x16/0x26. Gate: the caster must be farther away than a
  per-fighter value (FUN_0884e47c) and the CPU in a state that allows it (FUN_08a8707c / 08a8535c / 08a8519c).
- Garland's Thundaga "appear" flash 0x83c (no hit) carries tag 0x14 = vanilla's way to make the CPU dodge a placed
  spell before it strikes. v2's marker copies that (tag 0x14, right at the CPU's feet = threat from the first frame).
- Sora's rows already had tag 0x14 (0x7C4/0x7C5) / 0x02 (0x7C9); v1 just came too late (9 frames).
- Also used: plya piece +0x60 4 bytes = AI tags of the attacker's current move (Thundaga pieces 0x1011/0x1014 =
  0x0d = Cloud's Meteorain value; FUN_08a828fc lists 0xc-0xf, 0x13); seco table 0x190 = 6 global magi ids with a
  distance (6d, ce, 154, 17c, 1d5, 618) for a charge-attack reaction (FUN_08a76a88) — not needed here.
- Not changed: brain / brat / seco (spot33_ai guards untouched). Optional for the AI helper if CPU Sora still eats
  it: raise owner 33's reaction gate rows (seco 0xcc) / evasion weights; personality is global (code needed above Max).
