# Chapter 4 — Moves and combos

**The big idea:** a move is not one thing. It is a chain of small tables, like a recipe book
where each recipe points to other pages. Equipping an ability **switches on** a recipe. The
recipe lists **pieces** (one per swing). Each piece names an **animation**. The animation's
**script** says on which frames a **hitbox** is on, and which **hit** it deals. The hit says the
damage and how far the foe flies.

```
ablt row  (the ability you equip in Customization)
   │  +12 = action id  → "switch on action 1020"
   ▼
comb      (the action table: combo recipes)
   │  action 1020 = piece 0x5BE, then 0x5BF, then …
   ▼
plya      (attack pieces: one row per swing)
   │  piece +0x1c = motion id 10000
   ▼
p_se type 7  (motion id → script block + variant)
   ▼
p_se type 8  (the animation SCRIPT: timed events)
   │  op 0x00 "hitbox" frames 16–24, hit 0x35D, shape group 0x30
   ├──────────────► p_se type 5 (shape group 0x30 = spheres on r_wep)
   ▼
atkp      (the hit: power, reaction, knockback)
```

Everything here lives in the fighter's battle file `obj/p_sev120.objx` (Chapter 2), except
`ablt`, which is in `system.bin` (Chapter 8).

---

## 4.1 Words you need first

- **Bravery attack / HP attack:** Dissidia has two kinds. Bravery attacks (◯ Circle) steal the
  foe's Bravery points. HP attacks (□ Square) turn your Bravery into real damage.
- **Action:** one entry in the `comb` table = one move recipe (an action id like 1020).
- **Piece:** one swing (a `plya` row). Pieces have names like `LAND_NEAR1` (ground, close, 1st)
  or `AIR_FINISH3`.
- **Hit:** one `atkp` row = what happens when a hitbox touches the foe.
- **Hitbox:** an invisible ball that can hurt the foe while it is "on". **Hurtbox:** the
  balls on your own body that can *get* hurt.
- **p_se script / script block:** a list of timed events for one animation.
  Think of a musical score: "at beat 16, cymbal; from beat 16 to 24, drums".
- **Event / op:** one line of the script. "op" = operation code, a number saying what kind of
  event it is (`0x00` = hitbox, `0x03` = sound, `0x19` = effect, …).
- **Frame window:** the frames during which something is allowed (a hit, a follow-up press).

---

## 4.2 ablt → comb: equipping switches a recipe on

Story (tests 1–3, 2026-10-11/12):
- **Test 2:** pointed every Bravery ability at an HP action. Result: the **Bravery button did
  nothing at all**.
- **Test 3:** pointed every Bravery ability at one Bravery action. Result: **no change at all**.
- **Conclusion [PROVEN]:** `ablt +12` (the action id) is read and checked, but it does not
  *pick* the move. In the code (`FUN_08ab7f40`), for each equipped ability, the game walks the
  fighter's own action table and sets an **"enabled" bit** for every action whose id matches.
  The real move lives in the fighter's file.

The action table (`comb`) is a list of entries:

```
u16 action id      (what ablt switches on)
u16 n              number of steps
i16 alt id, i16 parent id
n × step:  u16 piece id, u16 min frame, i16 max frame, u8 flag, u8 0
```

Cloud has 18 actions (ids 313–328, 927, 928). Example: 314 = pieces 0x5BE, 0x5BF, 0x5C0
(a 3-hit chain).

**[PROVEN]** Test 4: changed the piece ids of Cloud's ground Bravery actions → only that
attack changed. Test 5: a **brand-new action 1020** (made with `comb_add.py`) ran in game.

---

## 4.3 plya pieces: the rules for each swing

A piece row is 116 bytes. Fields we know:

| offset | meaning | proven? |
|---|---|---|
| +0 | piece id | yes |
| +3 | **role**: 0 starter, 1 follow-up, 2 chase (4 also follows) | yes (tests 5–7) |
| +5 | where the attacker must be: 0 either, 1 **air**, 2 **ground** | yes (test 6) |
| +6 | where the target must be (same values) | from code |
| +0x0e | kind (0 near, 1/2 long/dash, 3/4/5 HP finisher) | guess |
| +0x0f | button: 1 Circle (Bravery), 2 Square (HP) | yes |
| +0x10 | landing motion (for air moves) | yes |
| +0x18 | flags: 0x2 skip distance check, 0x80 air, 0x10 HP, **0x200000 needs stick UP, 0x400000 DOWN** | yes for stick (test 107) |
| +0x1c | **motion id** (which animation/script) | yes |
| +0x1e | **motion after the move ends** (1 idle, 0x65 = fall) | yes (Upper Slash bug) |
| +0x21 | which in-battle **name banner** to show (−1 = none) | yes |
| +0x24 / +0x28 | distance window min / max (metres) | yes |
| +0x2c / +0x30 | height window | yes |
| +0x64 | name (`LAND_NEAR1` …) | yes |

### Building the first new combo (tests 5–7)

- **Test 5:** new action 1020 = NEAR1, NEAR2, LONG1. Only **2 hits** played. Why: LONG1 has
  role 0 (a starter). A starter never comes as a follow-up.
- **Test 6:** NEAR1, NEAR2, MIDDLE3. Still 2 hits. Why: MIDDLE3 has +5 = 1 (must be in the
  air). After NEAR2, Cloud is on the ground.
- **Test 7:** NEAR1, NEAR2, MIDDLE2, MIDDLE3. **4 hits** — MIDDLE2 lifts Cloud into the air,
  so MIDDLE3 can play. **[PROVEN]**

**Rule:** each next piece must be a follow-up (role 1/4), and its ground/air rule must match
where the fighter *is* at that moment.

### How the next hit is chosen (from the code, `FUN_08849700`)

1. Some fighters' scripts list "allowed next pieces" (ops `g`/`y`). Cloud's don't.
2. Otherwise: every follow-up piece is a candidate if it passes the ground/air rule, the
   distance and height window, and **some enabled action has the current piece and this piece
   as neighbours** inside the step's frame window.

So one action's step list can hold a small **graph**: "after A comes B; after B comes C or D".

**Lesson (test 117/118):** follow-ups are looked up in the action that **started** the chain
(plus chain abilities whose parent is that ability), not in every equipped action.
Slide Dash → NEAR2 worked, then stopped, even though action 1020 had NEAR2 → next.
**Every new starter move needs its own full follow-up list.**

---

## 4.4 The animation script (p_se type 8)

Each animation has a **script block**:

```
header: u8 id, u8 0, u8 main event count, u8 one-shot count, u16 one-shot list offset, u16 size
main events:  u16 from, u16 to (0xFFFF = open), u8 op, u8 n params, 6 bytes conditions, n × u32
one-shots:    u16 frame, u8 op, u8 n params, 4 bytes conditions, n × u32
```

- **Main events** are "on from frame A to frame B" (hitbox on, combo window open, stay in the air).
- **One-shots** fire once at a frame (play a sound, spawn an effect, shake the screen).
- **Frames are script frames: 60 per second** (the animation runs at 30, see Chapter 3).
- **Condition bytes:** byte 0 = **variant** (0 = always), byte 1 = **mode** (0 any,
  1 normal, **2 = only in EX Mode**).

### The ops we know

| op | kind | meaning | proven? |
|---|---|---|---|
| 0x00 | main | **hitbox**: param 0 = atkp hit id, param 1 = shape group | yes |
| 0x43 | main | hitbox + extras: spawn a projectile (magi) **when it hits** | yes |
| 0x01 | main | **combo can continue** window | yes (test 98) |
| 0x02 | main | a movement mode (mode 4 = dash) | yes |
| 0x02 | one-shot | **end the motion now** | yes |
| 0x0a | main | stay airborne (don't switch to falling) | yes |
| 0x22 | main | cancel window | from code |
| 0x28 | main | "free to act" (any action may cancel) | yes |
| 0x2d | main | landing window | from code |
| 0x39 | main | **lunge** toward the foe (params 0.2, 8.0, 0.5, 0, 0) | yes |
| 0x2a | main | weapon trail (ids 8888 / 9999) | yes |
| 0x26 | main | slow-motion factor (0.2) in the burst | guess |
| 0x14 | main | expression/phase (?) | unknown |
| 0x45 / 0x46 | main | guard flags (just-guard / reflect bit) | from code |
| 0x03 / 0x11 | one-shot | **sound** (absolute id) | yes |
| 0x15 | one-shot | **voice** | yes |
| 0x04 | one-shot | **spawn a projectile** (magi id) | yes |
| 0x19 | one-shot | **spawn an effect** by FEPA id | yes |
| 0x06 | one-shot | screen shake | yes |
| 0x1b | one-shot | screen flash (white / black / red) | from data |
| 0x1d | one-shot | name banner | from code |
| 0x10 / 0x25 | one-shot | camera | guess |

### Rule: a script must end before its animation does ("stuck after the move")

A motion is "finished" when its frame passes **2 × the animation's last frame** (script frames)
or when one-shot op 0x02 fires. One-shots placed after that **never fire**.

- **Magnet Burst bug:** copied Braver's script (end marker at 102, "stay airborne" until 104)
  onto a KH2 animation of only 47 frames (= 94 script frames). The motion ran out while
  "stay airborne" was still on and the end marker was never reached → **Sora hung in the air**
  (Mat: "stuck after"). Fix: make the animation as long as the script, or move the markers.
- **Rule:** after copying or scaling a block, the last op 0x02 / op 0x28 / op 0x0a end must be
  ≤ 2 × the GMO end frame.

Another "stuck" bug: **Upper Slash** (test 150). Mat: "after he does Upper Slash he's stuck in
an animation" (arm up, like falling). The piece came from Cloud's air move, whose
**+0x1e "motion after"** was 0x65 = fall. On the ground, Sora stayed in the fall motion forever
(landing needs an "in the air" bit that never comes). Fix: +0x1e → 1 (idle). **[PROVEN]**

### Variants: one script, several moves

The type-7 table row says "motion id → block **+ variant**". Events whose condition byte 0 is
`v` only run in variant `v`. So **one animation and one script can serve several moves with
different hits**. Cloud's block 45 deals hit 0x35E in variant 1 and hit 0x64E in variant 2.
We use this a lot for the four combos (4.9): no new animations needed.

Trap: Cloud's Fire spell script spawns its fireballs only in variants 1–3. A copy with
variant 0 spawned **nothing**.

---

## 4.5 Hitboxes: spheres on bones (p_se type 5)

The script's op 0x00 says "shape group 0x30". The **hit-shape table** (`p_se` type 5) says what
that group is: one or more **spheres**, each sitting on a **bone** or on the character's
**root** (`0x4000` = position on the floor + facing).

```
record (32 bytes): group id, kind (4 = hit sphere, 6 = clash sphere),
                   bone (50 = r_wep, 0x4000 = root), offset x/y/z, radius
```

Sora's groups (copied from Cloud):

| group | spheres | used by |
|---|---|---|
| 0x00 | body hurt spheres | always on |
| **0x06** | root, 1.0 m up, **radius 2.5** | area hits (Explosion, Firaga flurry) |
| 0x13 | root, 2 m in front, r 2 | chase hits |
| 0x21 | root, **radius 7** | EX Burst hits |
| **0x30** | on `r_wep` (Keyblade), r 0.8 | most combo hits |
| 0x31 | chest + `r_wep` | heavier hits |
| **0x32** | ~1.3 m sphere 1.8 m in front | KH2 moves at natural speed ("FRONT") |

- Every frame, each sphere's centre is worked out from its bone and **swept** from last
  frame's position, so a fast swing has no gaps.
- 1 unit ≈ 1 metre. Group ids must be under 64.
- **Area attacks are just big spheres on the root.** Exdeath's Almagest is radius 5;
  Limit hits are 7–24. So Sora's Explosion uses group 0x06.

**Lesson (tests 136–138):** KH2 swings at natural speed with Keyblade spheres (0x30)
**whiffed** (the foe escaped). The 2 m sphere (0x13) landed but hit beyond the blade (Mat
noticed). The 1.8 m "FRONT" group 0x32 + a lunge first was right.

---

## 4.6 atkp: what a hit does

68-byte rows, **sorted by id** (the game binary-searches them, so new ids must be the biggest).

| offset | meaning | proven? |
|---|---|---|
| +0x00 | hit id | yes |
| +0x04 | **kind**: 0/1 Bravery melee, 2 HP melee, 3 HP ranged, 4 guard, 7 Bravery ranged, 8 Bravery magic | from code + data |
| +0x05 | **reaction**: 0x01 flinch, 0x04 push back, 0x07 crumple/slam, 0x0c **blow away**, 0x0d air flinch | yes |
| +0x08 | flags: 0x10 = HP damage, 0x80 = projectile | from data |
| +0x10 | **power** (u16) | yes (test 8: 15 → 150 gave 129 damage) |
| +0x1c | sideways / forward push (for blow away) | yes (test 11) |
| +0x20 | **up push** (negative = slam down) | yes (test 11) |
| +0x24 | **flight time** | yes (test 13b) |
| +0x34 | name | yes |

Tests 8–13 (2026-10-12) each changed one number and Mat watched:
- 8: power ×10 → huge damage. 9: copied a finisher's knockback → foe flew into the wall.
- 10: `own_hit.py` gave one step **its own** piece + hit (sharing the animation) → only that
  move changed. 11: sideways 0, up 40 → straight up, very high. 13a/13b: flight time 25 vs
  100 → the foe stayed up much longer.
- Upper Slash today: reaction 0x0c, up push 6, flight time 30 → foe goes ~6–9 m up.

**Live tuning:** the hit rows sit in memory while you play. Find them by name in a RAM dump
(`ppsnap.py`) and write a new value with the debugger. It takes effect on the next hit, no
rebuild. Great for finding good numbers fast.

---

## 4.7 magi: projectiles and bursts

The `magi` chunk holds projectiles: fireballs, meteors, shockwaves, Blade Beam.
- Rows are 204 bytes, **sorted by id** (new ids must be > 0x7C0).
- **+0x0A = the hit id** in the *caster's* atkp. Point a projectile at an HP hit = HP projectile.
- +0x04 = a visual effect bit, +0x0e… = child projectiles (spawned on hit/end),
  +0x1e = **spawn mode**, +0x22 = direction mode, +0x2c = collision radius.
- Most numbers (speed, life, scale, angles) are **byte indexes into a shared list of floats**
  at the end of the chunk. To change a speed you point at another float in the list.
- Spawned by one-shot op 0x04, or on hit by op 0x43. All projectiles share **one pool of 32**
  in the whole battle.

**Story — Firaga shot nothing (test 149):** the spawn breakpoint said the fireball *was*
created, but it vanished at once. Cause: Fire balls use **spawn mode 6 = "start at a live effect
of the caster"** (effect 19, the Fire charge glow). That effect was only auto-spawned by Cloud's
Fire animation slot. Sora's spell used a new slot → no glow → the ball found no anchor → freed.
Fix: spawn effect 19 two frames before the release (op 0x19). **[PROVEN]** test 150: the
fireball flies and hits.

Spawn modes we know: 0 at the caster, 1/2 at a bone, 3/4/8/9/11/12 at the **target**, 5 at a
parent projectile, 6 at a live effect, 13 at the lock-on partner.

---

## 4.8 How Sora's moves were built (the timeline)

| test | what | result |
|---|---|---|
| 51 | KH2 ground/air swings timed onto Cloud's hit windows (`kh2_attack.py`) | swings play and connect (late — two clocks lesson) |
| 52 | HP attacks from KH2 clips (`kh2_combo.py`) | play |
| 59 | finishers land after loop-flag fix + `:match` | ground 4th + air 3rd land |
| 95–107 | **long KH2 combo**, 12 hits, ground → air | Mat (test 107): "Wonderful!! It was perfect!!!" |
| 119 | own ground finisher (Finishing Leap) in a free slot | lands |
| 120 | Explosion + Magnet Burst as □ finishers, new hits 0x1000/0x1001 | land |
| 126 | new animation slots (`_720A`…) work | yes |
| 135 | **every KH2 move at natural speed with own script blocks** (AUTHOR) | lands vs Average CPU |
| 150 | Upper Slash launch (replaces Spin Finish), Firaga fireball | yes |
| 191 | **four combos**, all 12+ hits | ground ones confirmed by Mat |

### The recipe for the long combo (test 107)

comb chain + **op 0x01 continue windows** added to Cloud's enders + **light reactions** on
combo hits (so the foe stays close) + hits around script frame 10–14 + `:match` on the
Keyblade at the hit + bigger reach/height windows + **no stick-direction flags** on air pieces.
Plus later: **lunges** (op 0x39) on every link so distance stays 1.5–2 m (it grew to 3–4 m
by hit 5 before), and **hurt clips as long as Cloud's** (Chapter 3).

Bravery ramps up: power 6 → 8 → 11 → 14 → 18 → 22 (Mat: "Bravery gained grows with each hit").

### COPY vs AUTHOR (spot33_chain.py)

- **COPY** = take a Cloud script block as is. Fast, but keeps Cloud's hit *pattern*.
  Finishing Leap was a copy of Cloud's AIR_MIDDLE1: a 20–60 multi-hit window with blue sparks.
  Mat: "looks like Onion Knight's finisher". Not KH2.
- **AUTHOR** = keep the template's "plumbing" (trails, sounds, stay-airborne, end markers…)
  stretched to the new length, **drop its hits**, add **our own** hits at KH2's real hit moments
  (`kh2_hits.py` finds the fastest Keyblade-tip frames; `kh2_triggers.py` reads KH2's own hit
  windows from its motion data).
- Order inside `spot33_chain.py`: SLOTS → COPY → ADVANCE (lunges) → AUTHOR → WINDOWS → VARIANTS.

Lesson: authored combo pieces need "free to act" (op 0x28) **late**. With it early, presses
started a **new** combo instead of the finisher.

### Which KH2 animation is which ability

We guessed at first, and some guesses were **wrong** (Explosion, Aerial Finish, Dodge Slash
vs Slapshot, Aerial Dive vs Spiral). The fix was checking against Mat's KH2 "All Abilities"
video and KH2's ability ID order. Corrected list (`notes/kh2-finishers.md`):

| KH2 | ability | | KH2 | ability |
|---|---|---|---|---|
| 604–620 | normal ground combo | | 724–736 | normal air combo |
| 644 | Slapshot | | 764 | Aerial Sweep |
| 648 | Upper Slash | | 768 | Aerial Spiral |
| 652 | Dodge Slash | | 772 | Horizontal Slash |
| 656 | Slide Dash | | 776 | Aerial Finish (5 sweeps) |
| 660 | Guard Break | | 784 | Aerial Dive |
| 664 | Explosion | | 788 | Magnet Burst |
| 668 | Finishing Leap | | 164 / 172 | Reflect (guard) |
| 676 / 680 / 684 / 688 | Flash Step / Vicinity Break / Counterguard / Retaliating Slash | | 838 | dodge roll |

**Lesson:** when unsure what a KH2 animation is, ask Mat or check the video. Mat knows KH2.

---

## 4.9 Sora's combos today (2026-10-15)

Mat: "I want 4 combos, right now all combos lead to one finisher in the air." And: "all the
combos should be 12 hits plus." Built with **variants** (4.4), so no new animations:

| # | starter (input) | route (KH2 clips) | finisher | hits |
|---|---|---|---|---|
| 1 Ground Rave | Combo Plus (◯ close, ground) | 604 → 608 → 612 → 604 → 608 → Dodge Slash spin → 612 → 620 | 620 swing, blow away; Sora stays on the ground | 12 |
| 2 Sky Rave | Slide Dash (◯ from range) | dash 656 → 608 → 616 → 648 launch → air swings → Horizontal Slash ×6 | Aerial Finish (776, 5 sweeps) | 19 |
| 3 Spin Leap | Dodge Slash (◯ + stick away) | 652 spin (4 hits) → 620 → 612 → 616 → 648 launch → 732 | Finishing Leap (668) | 13 |
| 4 Air | Air Combo / Aerial Spiral / Aerial Dive | three air routes | three different air endings | 13–16 |

Square (□) finishers branch off at fixed hits: Upper Slash, Guard Break, Explosion,
Magnet Burst, Horizontal Slash, Aerial Sweep, Retaliating Slash.

Dodges: stick away = backward hop (start of KH2 Guard Break), stick toward = KH2 forward roll.
Mat: "it works".

**[BUILT, partly seen]** The ground combos are confirmed by Mat. The air-combo fix
(test191s, Aerial Dive no longer overshoots) still needs a look.

---

## 4.10 HP magic: Firaga, Thundaga, Blizzaga

`spot33_magic.py` adds 3 new HP hits, 15 projectile rows, 6 pieces, 6 script blocks and 6
actions, copied from Cloud's spells in the **clean** disc (test discs carry old edits of
Cloud's file).

- **Firaga:** first a fireball (fixed in test 150). Then Mat: "a flurry of flames around you
  like KH2", so now **no projectile**: body-sphere hits around Sora (group 0x06, r 2.5) + a ring
  of KH2 fire effects (Chapter 6).
- **Thundaga:** first it was Cloud's Meteorain (slanted meteors). `spot33_thunder.py` makes the
  strikes spawn above the foe and fall **straight down**. **[PROVEN]** test211: a vertical bolt.
- **Blizzaga:** one fast ice shard. Mat: "perfect".

Limits: the ability table needed 809 rows → raised from 808 to 832 (`spot33_ablt_cap.py`,
Chapter 7/8).

---

## 4.11 EX Mode and EX Burst

- **EX gauge:** a float at `*(fighter+0x52C)+0x18`, 0 to 10,000. Full → R+□ = EX Mode.
- **EX Mode weapon:** `wep1` = Ultima Weapon (Chapter 3). Voice "LIGHT!".
- **EX Mode start** (motion 5000) shared Cloud's slot with the homing dash. `spot33_exmode.py`
  gave it its own slot `_736A` and script; the animation is Codex's "LIGHT!" activation.
- **EX Burst:** Sora runs **Cloud's Omnislash code**. The burst is a set of shots, motions
  8000–8600 (opening, "rapidly tap ◯", dashes, slashes, final blow). Cloud's shots place him
  around the foe with the root bone, so Sora's shots use `burst:` entries that copy that
  placement (FOLLOW) and match the weapon at each hit (MATCH). The shots play KH2 **Limit Form
  Ars Arcanum** clips (`notes/kh2-limit.md`), and Codex's animations replace the opening,
  the "tap ◯" charge, and the three endings `_812A/_812B/_812C` (Codex's timed **Trinity**
  limit, with every strike placed on the existing hit frames).
  **[PROVEN]** test 60: the whole burst plays with Sora's moves, hits land. Test215: Codex's
  Trinity burst plays through vs CPU Lightning (flurry, grand finish, final blow, win).
- The burst's hit frames are fixed by Cloud's scripts: the flurry `_812B` has 9 hits at
  4, 24, 48, 64, 78, 92, 106, 118, 130; the final blow `_812A` at 120–126; the grand finish
  `_812C` at 92 and 116. Animations are made to fit these, so no gameplay data changes.
- **The △ "break"** Mat wants (KH2's Limit: hit, then △) needs new game code. **[NOT DONE]**
  Today the "break" is only the look.
- **Reflect** (EX Mode guard) is game code → [Chapter 7](07-game-code.md).

---

## 4.12 Where to look

- `notes/character-file.md` — comb / plya / atkp / scripts, tests 4–13 and the long combo.
- `notes/hitbox-shapes.md` — shapes, magi, script layout, end rule, banners.
- `notes/abilities-owner33.md` — new moves, chains, four combos (bottom = newest).
- `notes/kh2-finishers.md`, `notes/hp-magic.md`, `notes/kh2-limit.md`.
- `tools/scripts/comb_patch.py`, `comb_add.py`, `atkp_patch.py`, `own_hit.py`,
  `spot33_combos.py`, `spot33_chain.py`, `spot33_speed.py`, `spot33_magic.py`, `spot33_thunder.py`,
  `kh2_hits.py`, `kh2_triggers.py`.

Next: [Chapter 5 — Sounds and voices](05-sounds-and-voices.md).
