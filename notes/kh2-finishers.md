# KH2 Sora attack animations → which combo ability each one is (2026-10-14)

## CORRECTED (2026-10-14, checked against the KH2 gameplay video) — use this table
Video: a local copy of a KH2 "All Abilities" gameplay video (one chapter per ability). Frame sheets of the key
moments: `dumps/renders/kh2video/*.jpg` (file name = ability + video time). Every ability's own motion is in
P_EX100.mset; none had to come from another mset. The guesses further down are SUPERSEDED where they differ.

**Strongest evidence: the A-code order matches KH2's ability ID order.** KH2's ability IDs (from memory, not
checked against game data) are Slapshot 262, Dodge Slash 263, Slide Dash 264, Guard Break 265, Explosion 266,
Finishing Leap 267, Counterguard 268, Aerial Sweep 269, Aerial Spiral 270, Horizontal Slash 271, Aerial Finish 272,
Retaliating Slash 273. The Final Mix additions are Flash Step 559, Aerial Dive 560, Magnet Burst 561 and Vicinity
Break 562. The motion codes follow the same order:
A310 Slapshot, (A311 Upper Slash, an older ability), A312 Dodge Slash, A313 Slide Dash, A314 Guard Break, A315 Explosion,
A316 Finishing Leap, A317 Counterguard · A340 Aerial Sweep, A341 Aerial Spiral, A342 Horizontal Slash, A343 Aerial
Finish, A344 Retaliating Slash · Final Mix: A318 Flash Step, A345 Aerial Dive, A346 Magnet Burst, A319 Vicinity Break.
Every row that could be checked in the video agrees with this order.

| ability (video time) | idx (EX / A) | conf. | what the video shows | finisher / combo hit, hits, magic |
|---|---|---|---|---|
| Guard (0:42) | 164 / 168 (A320 / A321), not an attack | high | Block, then knock-back | not an attack. **692 (A322)** belongs to the guard group (it turns 180° to block or hit behind). It is not a combo ability. |
| Upper Slash (1:22) | **648** (EX011 A311) | high | One rising slash that launches the target into the air for an air combo | combo hit, 1 hit |
| Horizontal Slash (2:19) | **772** (EX042 A342) | high | In the air: fast slashes left, then right, then down, in place | air combo hit (can repeat), 3 hits |
| Finishing Leap (3:15) | **668** (EX016 A316) | high | After the last ground hit Sora crouches, then leaps about 2 m with a full flip. A white wing-shaped burst of light shoots up from the ground under him, then he lands | ground **finisher**, 1 hit (hitbox f17–19) + light burst |
| Retaliating Slash (4:29) | **688** (EX021 A344) | high | Knocked into the air, Sora recovers (white ring flash) and spins about one turn in the air with flat slashes, then lands | counter / recovery, 2–3 hits |
| Slapshot (5:13) | **644** (EX010 A310) | medium-high | Fast up-and-down slashes in place, about 0.35 s each, repeated many times on one target (vs Saïx) | combo hit (repeats), 1 per use |
| Dodge Slash (6:05) | **652** (EX012 A312) | medium-high (Mat agrees) | Spinning flurry among several nearby enemies | combo hit, 4–5 hits |
| Flash Step (6:59) | **676** (EX018 A318, Final Mix) | medium-high (not re-checked in video) | Very fast dash to a distant target, then slashes | combo opener, 3–4 hits |
| Slide Dash (8:36) | **656** (EX013 A313) | high (not re-checked in video) | Long low rush at a distant target | combo opener, 1–2 hits |
| Vicinity Break (9:26) | **680** (EX019 A319, Final Mix) | high | Spin in place; a white ring sweeps all around Sora | combo hit vs. surrounding enemies, 1–2 hits |
| Guard Break (10:35) | **660** (EX014 A314) | medium (video too dark to check) | not readable | ground **finisher** |
| Explosion (12:09) | **664** (EX015 A315) | **high** | The previous combo swing ends with the blade low. Sora lifts the Keyblade straight up overhead (white flash at the tip), slams it down and stays crouched. Light orbs with rings burst out and spiral outward around him (magic damage) | ground **finisher**, plant hit + magic burst |
| Aerial Sweep (13:10) | **764** (EX040 A340) | medium-high | Jumps up at a target directly above and spins flat (horizontal pink arcs) | air approach hit, 1 big hit |
| Aerial Dive (13:49) | **784** (EX045 A345, Final Mix) | medium-high | Leaps off the ground at a distant airborne target, doing **front flips** (wheel) with overhead strikes | air approach (loops), 3–5 hits |
| Aerial Spiral (14:25) | **768** (EX041 A341) | medium (by ID order; the video is unclear) | Closes in on an air target while flipping and turning | air approach (loops), 2 hits |
| Aerial Finish (15:26) | **776** (EX043 A343) | **high** | About 5 big full-circle crescent sweeps around Sora in about 1.3 s, ending with a sweep that knocks the target away | air **finisher**, 5 hits |
| Magnet Burst (16:07) | **788** (EX046 A346, Final Mix) | high | Spins more than 2 turns inside a gold magnet vortex that pulls enemies in, then a big sphere bursts | air **finisher**, multi-hit + magic burst |
| Counterguard (17:15) | **684** (EX020 A317) | high (pose evidence; not re-checked in video) | After a successful block, a hop forward with a flat slash | counter, 1 hit |

### Answers to Mat's specific questions
- **664 = Explosion** (high). The "612-like swing" Mat saw is the combo hit just before it. Explosion itself is
  "Keyblade straight up, slam down, stay crouched while the light orbs burst out". For our port: hit 3 (a 612-type
  swing) followed by 664 plus a magic burst effect.
- **668 = Finishing Leap** (high). It is KH2's own motion (crouch, ~2 m leaping flip, light burst from the ground).
  If it reads like Onion Knight's finisher, that is a coincidence of shape, not a wrong index.
- **776 = Aerial Finish** (high). Measured on the Keyblade tip: about 2200° of total sweep (about 6 full circles) and
  5 speed peaks (f13, 17, 27, 37, 42). It is one of only two air ability finishers (t50 trigger); the other is 788,
  which the video confirms is Magnet Burst. It has 4 effect triggers. If it doesn't look like 5 sweeps in-game, the
  cause is the port's retiming or root pinning, not the index.
- **652 = Dodge Slash** (Mat was right). **Slapshot = 644**, not 652.
- Body rotation measured in the world frame (Z = travel direction, X = side axis, Y = up): 784 does about 3.3
  front flips. 768 does about 2.8 flips the other way plus a 1-turn yaw. 764 and 788 are flat spins (2.6 and 2 turns).
  776 is mixed: about 1 yaw turn, 0.7 flip and 0.3 roll.
- What this changes in `build_sora.sh` (labels only; the script itself was not edited): `_610A` = 652 is
  **Dodge Slash** (was called Slapshot). `_702A` = 644 is **Slapshot** (was called Retaliating Slash).
  `_621A` = 768 is **Aerial Spiral** (was called Aerial Dive; the real Aerial Dive is 784). `_650A` = 764
  (Aerial Sweep) and `_651A` = 772 (Horizontal Slash) were already right. The HP/Burst uses of 776, 788 and 664
  are correct: Aerial Finish, Magnet Burst and Explosion.
- Not in P_EX100.mset as their own motion: Guard (it uses the guard motions 164/168). The mset has no motion in
  slots 672 (EX017) or 780 (EX044); they are DUMM placeholders.

---
# SUPERSEDED: the first-pass guesses below (kept for the evidence; see the corrected table above)


Source: `kh2_export/raw/kh2_sixth/original/obj/P_EX100.mset`. Its 839 slots hold 89 real animations; the other
750 are `DUMM` placeholders. `dumps/kh2anim/list_named.txt` already lists all 89 (checked with `bake … list`),
so this file has no hidden attack animations. Drive Forms and other variants have their own msets
(`P_EX100_BTLF/MAGF/TRIF/ULTF/KH1F/LAST/HTLF…`), which this note does not cover.

## Pictures
- GIFs: `dumps/renders/poses/<IDX>_<EXnnn>.gif` (step 2, rendered again on 2026-10-14 with the current model).
- Contact sheets: `dumps/renders/kh2finishers/<IDX>_<EX>_<A>.png`. Each has 10–11 frames in two rows (top = 3/4
  view, bottom = side view; the camera follows the hips). The red box marks the frame of the fastest Keyblade tip.
  Each sheet also shows how far the hips moved (fwd/up, metres), the turn (yaw, degrees), a side-view hip path and
  a tip-speed bar chart. Index sheets: `dumps/renders/kh2finishers/index_1.png` and `index_2.png` (8 frames per motion).
- Single frames (q + side): `dumps/renders/kh2finishers/frames/<IDX>/`.

## How the evidence was collected
1. **Keyblade tip speed.** `kh2_attack.tip_track/impacts` on the solved Dissidia pose. These are the "hit f" values.
   They are animation frames at 30 fps; Dissidia script frames are double that.
2. **Hip travel and turning.** Hip position in the solved pose. The turn is measured from the left femur to the
   right femur. Hip travel is raw KH2; `kh2_attack` pins the root when it ports a motion.
3. **Start and end poses.** Each motion's first frame was compared with every frame of the non-attack motions,
   using bone positions with the facing direction removed.
4. **KH2 motion triggers.** These are stored in each ANB (BAR sub-entry type 16). They were decoded with a small
   parser (layout below). Most useful:
   - range trigger **t10 [atkp, collision]** = a special hitbox, given in 60 Hz ticks (the same unit as Dissidia
     script frames). Normal swings have no t10, so their hits come from the game code.
   - **t11 [from-]** = combo can continue from here. It is missing on finishers.
   - **t50** appears only on finishers (616, 620, 660, 664, 732, 736, 776, 788).
   - **t3** = hovering in the air. **t1 frame trigger [n]** = effect number. 406/6 and 124/6 look like
     invulnerability or guard-type collisions; they show up during dashes, spins and guards.
   - The effect numbers come in groups per motion. Final Mix additions seem to be the high ones (49–56) and have
     high atkp IDs (1869, 1900–1903).

   Trigger layout: `u8 nRange, u8 nFrame, u16 frameOffset`. Range triggers start at +4 and are
   `s16 start, s16 end(-1 = to the end), u8 type, u8 nParam, s16 params[]`. Frame triggers start at frameOffset and
   are `s16 frame, u8 type, u8 nParam, s16 params[]`. Frames are in 60 Hz ticks.

## Ground (all end in the battle stance unless noted) (SUPERSEDED guesses)
| idx | EX | A | frames | what it looks like | best-guess KH2 ability (confidence) | hit frames (30 fps) |
|---|---|---|---|---|---|---|
| 604–620 | EX000–004 | A300–304 | 25/29/37/41/41 | Basic ground combo, for reference. 616 = 360° spin slash, 620 = 360° spin + hop and overhead slam. Both are finishers (t50). | Normal combo hits 1–3 and the two default finishers | 604 f9 · 608 f12 · 612 f8,f11,f22 · 616 f16 · 620 f16 |
| 644 | EX010 | A310 | 39 | Starts in a pushed-back stance (close to the guard recoil 168 f21). Winds the Keyblade up and back, then swings it two-handed diagonally down and low across the front while lunging 1.7 m; recovers with the blade upright. Combo can continue from f22. | **Retaliating Slash** (ground counter after being knocked back), low. Could also be Dodge Slash. | f11 |
| 648 | EX011 | A311 | 29 | One fast slash from low to above the head (tip moving straight up), small hop (+0.36 m), 0.5 m forward. Starts from the mid-combo pose (= end of 616). | **Upper Slash**, high | f5 |
| 652 | EX012 | A312 | 43 | Flurry while advancing 3 m. The body swings back and forth about one turn; 4–5 slashes. | **Slapshot** (rapid strikes), medium. Could also be Dodge Slash. | f8, f17, f27 (+f24, f30) |
| 656 | EX013 | A313 | 29 | Long low rush: 7 m in about 15 frames, body nearly horizontal, Keyblade forward. Ends with a 360° spin to brake and stand up. | **Slide Dash**, high | f5 (launch), f13 |
| 660 | EX014 | A314 | 39 | Hops back (−1 m, +0.7 m up) with overhead swings, then lunges 3.9 m forward spinning 360°. Effects 30–32 at f12–15. Finisher (no t11, has t50). | **Guard Break**, medium | f2, f10, f16 (+f25, f30, f33) |
| 664 | EX015 | A315 | 45 | Lifts the Keyblade overhead with both hands, drives it into the ground at f16 and stays crouched about 12 frames, then steps back 1 m. Area hitboxes atkp 911 (ticks 32–57 = f16–28) and 912 (f28–32), 5 effects. Finisher. | **Explosion**, high | f16 (plant), burst f28–32 |
| 668 | EX016 | A316 | 33 | Crouches, then jumps 1.8 m with a forward somersault, Keyblade trailing below. **Ends in the air** (t3 airborne from f1). Hitbox atkp 854 at f17–19. Finisher (no t11). | **Finishing Leap**, medium-high | f14, f22 (hitbox f17–19) |
| 676 | EX018 | A318 | 31 | Instant dash of 3.8 m in about 10 frames, crouched, with a 406/6 collision during f0–9. Then quick slashes on arrival. Effects 53–56 (Final Mix range). | **Flash Step**, medium-high | f12, f15, f23, f25 |
| 680 | EX019 | A319 | 37 | Stands, then spins 1.5 turns in place with the Keyblade held out flat. Area hitbox atkp 1869 at f10–15 (a high, Final Mix-style ID), effects 49–50. | **Vicinity Break**, medium-high | f12, f17 (main) |
| 684 | EX020 | A317 | 29 | Starts **exactly in the guard-recoil pose** (= 168 AUTOGUARD f19; 168 is the blocked-hit push-back). Hops 1.5 m forward (+0.8 m) with a flat slash. Hitbox atkp 1581 at f10–14, guard-type collision 124/6 at f0–10. | **Counterguard**, high | f9 (hitbox f10–14) |
| 688 | EX021 | A344 | 37 | Air motion despite the ground slot: its last frame matches 768/784 exactly, and it is flagged airborne (t3) at f10–18. Spins about 1.2 turns from an upright, recoil-like pose, with 3 slashes around. Effect 39. | **Retaliating Slash** (air recovery spin), low-medium | f4, f12, f20 |
| 692 | EX022 | A322 | 31 | Turns about 175° and swings behind, holds the Keyblade upright (guard-like), then turns back with a second swing. Both swings land behind or to the side. Its flags match the guard motions A320/A321 (no combo window, t2 return), and the code sits right after them. | Probably a **turn-around guard or back attack**, not a combo ability (possibly Dodge Slash), low | f5, f22 |

## Air (they hover; hips do not travel; the game moves the fighter) (SUPERSEDED guesses)
| idx | EX | A | frames | what it looks like | best-guess KH2 ability (confidence) | hit frames (30 fps) |
|---|---|---|---|---|---|---|
| 724–736 | EX030–033 | A330–333 | 31/31/34/35 | Basic air combo, for reference. 728 = upward slash. 732 = downward chop and 736 = 384° spin; both are finishers (t50). | Normal air combo and default air finishers | 724 f8 · 728 f8 · 732 f9 · 736 f8 |
| 764 | EX040 | A340 | 31 | Spins flat in the air 2.7 turns with the blade out; one big hit, then a trailing sweep. | **Aerial Sweep**, medium | f5 (+f17) |
| 768 | EX041 | A341 | 37 | Forward somersault plus one turn; the Keyblade strikes **below** (tip 1.6 m under the hips). Ends in its start pose (loops). | **Aerial Dive**, low. Could also be Aerial Spiral. | f8, f15 |
| 772 | EX042 | A342 | 31 | Three quick slashes in place (left, right, down), hovering (t3) f8–22. Combo continues (t11). | **Horizontal Slash**, medium | f8, f13, f19 |
| 776 | EX043 | A343 | 59 | Longest air move: several slashes, a full 360° spin, 5+ hits, 4 effects (f9/16/24/40). Hovers f8–50. Finisher (t50). | **Aerial Finish**, medium-high | f13, f17, f27, f37, f42 |
| 784 | EX045 | A345 | 36 | Keeps somersaulting forward like a wheel, slashing 5 times. The start pose equals the end pose, so it loops. | **Aerial Spiral**, medium | f6, f13, f17, f20, f26 |
| 788 | EX046 | A346 | 46 | Spins more than 2 turns hitting all around (hitboxes atkp 1900/1901 at f8–28), then raises the Keyblade overhead for a final burst (atkp 1903 at f32–35). Effects 51–52. Finisher. | **Magnet Burst**, medium-high | spin f8–22, burst f31 |

## The rest (EX050–058): movement abilities, not attacks
| idx | EX | A | frames | what it looks like | guess |
|---|---|---|---|---|---|
| 806 | EX050 | B003 | 37 | Crouch, then a big jump (jump trigger at tick 4, +0.8 m); held in an airborne crouch. | **High Jump**, medium |
| 810 | EX051 | A160 | 7 | Very short 470° spin; 406/6 collision the whole time. | **Quick Run** burst or another dodge, low |
| 814 / 818 | EX052 / 053 | A150 / A151 | 31 / 19 | 814 = a still airborne crouch. 818 = a spinning hop up (+0.6 m, one turn) out of that crouch. | **Aerial Dodge** (hold + spin jump), low-medium |
| 822–834 | EX054–057 | A170–173 | 31/31/31/51 | Lying flat, "superman" pose, almost no motion. | **Glide** (straight, turns, start/stop), high |
| 838 | EX058 | A180 | 27 | Low roll 4.4 m forward, then stands up. | **Dodge Roll**, medium-high |

## Notes for porting (first pass; the ability labels here are SUPERSEDED)
- Good matches: Upper Slash 648, Slide Dash 656, Explosion 664, Counterguard 684 (the pose proves it starts from
  a block). Likely: Finishing Leap 668, Flash Step 676, Vicinity Break 680, Aerial Finish 776, Magnet Burst 788.
  Weakest: 644 / 652 / 692 (Retaliating Slash, Slapshot, Dodge Slash in some order) and 768 / 784 / 764 (Aerial
  Dive, Aerial Spiral, Aerial Sweep). Checking a KH2 gameplay video for these would settle them.
- `build_sora.sh` already uses some of these. `_610A` = 652, `_611A` = 648, `_702A` = 644, `_621A` = 768,
  `_650A` = 764, `_651A` = 772; HP/Burst use 776, 788, 652, 664.
- Hitbox ticks from t10 are already 60 Hz, so they can go straight into Dissidia script frames.
- Trigger decoder: `python3 -I tools/scripts/kh2_triggers.py OUT.json IDX…`. It writes every motion's triggers to
  OUT.json and prints the listed ones. The tip/hip metrics and start-pose matching were scratch scripts.
