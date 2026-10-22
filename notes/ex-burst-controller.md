# EX Burst controller (Cloud's "tap ◯" burst, which owner 33 runs) — static code study

Started 2026-10-16T00:17Z by the EX Burst controller helper (Claude), for Codex question Q-20261015-CODEX-004
(codex/QUESTIONS.md). Goal (Mat): Sora's EX Burst = the real KH2 solo Limit **Trinity (A870)**, not Omnislash replayed
with Sora's animations. Phase 1 = static only (a local Ghidra decompile, overlay bytes in dumps/extracted/OVL_BATTLE_APP.ELF,
scratch disassembler). Everything marked **[static]** still needs a runtime trace.

## 1. Object layout (battle overlay)

- **Burst manager** = `DAT_08a405e0` → `&DAT_09aef060` (built once by `FUN_08878c28`). Holds 20 controller objects of
  0x18 bytes (`FUN_08a3d720(mgr, i)` returns `mgr + i*0x18`, i = 0..19), then manager fields:
  `+0x214` current controller, `+0x21c` float, `+0x220` burst UI layout resource, `+0x228..` UI element handles,
  `+0x26c` **attacker** fighter, `+0x270` **victim** fighter, `+0x278` manager phase (0 = no burst), `+0x288` sub
  object, `+0x298` float (angle offset factor), `+0x2a0` passed to the controller start. [static]
- **Controller object** (0x18 B): `[0]` fighter (attacker), `[1]` arg, `[2]` **variant**, `[3]` UI resource
  (`*(fighter+0x390)+0xd0`), `[4]` vtable (+0x10), `[5]` state struct pointer. Start = `FUN_08a40684(ctrl, mgr+0x2a0,
  attacker, arg, variant)` (called from manager code) → vt slot 1 (init).
- **Controller 0 = the "rapidly tap ◯" family**, vtable `0x08a3b168` (8-byte entries {offset, fn}):
  init `FUN_08a39bd8`, cleanup `FUN_08a39cf8`, `FUN_08a39fa8`, **update `FUN_08a39db4`**, more at 0x08a3b194…
  `FUN_08a39db4` dispatches on `[2]` variant: **0 → `FUN_08a3a0b8` (Cloud's Omnislash — the one owner 33 runs:
  EX_SND hooks at 0x08a3a15c/0x08a3a374 are inside it and were hit in test219)**, 1 → `FUN_08a3a638`, 2 → `FUN_08a3abc4`.
  ⚠ Correction to notes/kh2-effects.md: `FUN_08a3a638` is variant **1** (another fighter's tap burst), NOT Cloud's.
  Cloud's variant 0 spawns NO effect per tap (per tap it only flashes one of the five ◯ UI icons, `FUN_088d9f5c(icon,3,1)`).

## 2. State struct (`ctrl[5]`, 0x60 bytes, zeroed by init `FUN_08a39bd8`)

| off | meaning (variant 0) |
|---|---|
| +0x00 | state: 0 enter, 1 charge (tap ◯), 2 full-bar dash wait, 3 shot chain, 4/5 done (5 = final queued) |
| +0x04 | ◯ taps counted (max 19 = 0x13) |
| +0x08 | number of extra shots chosen at the end of the charge |
| +0x0c | shot index in state 3 |
| +0x10 | **grade** (0..4): +1 each time taps reach the next threshold |
| +0x14 | LIMIT bar fill (float 0..100), eased toward taps/19*100 by `FUN_08a39db4` (step max((target-cur)/5, 1)) |
| +0x18 | timer (float, +`DAT_089d5eac` per frame while the state is unchanged; reset to 0 on a state change) |
| +0x1c | float 240/random(…) (set by `FUN_08a399d0`, CPU tap rate — `FUN_08a39b48` taps for a CPU via `FUN_08a6427c`) |
| +0x20 | CPU taps done |
| +0x24 | effect handle (grade effect) |
| +0x44..+0x54 | 5 ◯ icon UI handles; +0x58 UI; **+0x5c LIMIT bar UI** (`FUN_088d9aec(fill, bar)`) |

Grade table (copied from `0x08a3b268`, 4 × {tap threshold, shots, effect id}):
`{5,1,0x32} {10,2,0x33} {15,3,0x34} {19,5,-1}` — effect ids 0x32/0x33/0x34 = Cloud-bank FEPA 50 CHOU_FIRE / 51
CHOU_SMOKE / 52 CHOU_LIGHT, spawned ONCE when the grade is reached (`FUN_088a9de8(*(f+0x390)+0x5c, id, f+0x4c8, 0, 0)`).

## 3. Variant 0 state machine (`FUN_08a3a0b8`, s0 = controller, fighter = *(s0)) [static]

- state 0: sound 2200053 (`0x08a3a15c`, skipped for owner 33 by EX_SND) → state 1.
- state 1 (charge, motion 8101 `_801B` set by init): while taps < 19 and `FUN_08b326c4(fighter)` (◯ pressed this
  frame): taps++, icon flash; if taps == threshold[grade] → spawn effect[grade] (if != -1), grade++.
- **End of charge**: timer +0x18 ≥ **180.0** (`DAT_08a3b1d0`) **or** bar +0x14 ≥ 100.0. shots = (grade == 0) ? 0 :
  table[grade-1].shots → grade 1:1, 2:2, 3:3, 4:5. Then:
  - grade < 4, shots == 0 → motion **8501** (`_812A` incomplete finish), state 5.
  - grade < 4, shots > 0 → motion **8109** (`_803A`), state 3.
  - **grade == 4 (19 taps)** → `FUN_08856d48(DAT_089d4dc8+0x69c0, fighter, 1, 1)`, sound 2200054 (`0x08a3a374`,
    skipped for 33), bar UI anim, motion **8102** (`_802A`), state 2.
- state 2: when timer ≥ **50.0** → `FUN_08856a58(DAT_089d4dc8+0x69c0)`, `FUN_08856d48(…, fighter, 0, 1)`, bar UI
  destroyed, state 3 (motion 8102 keeps playing).
- state 3: each frame where **fighter+0x188 bit 0** (current motion finished) is set:
  index < shots → next motion = (grade < 4 ? **8110 + index** : **8103 + index**), index++;
  index == shots → grade < 4 ? motion **8501** : motion **8108** + queued **8500** (`FUN_0882fb90`), state 5.
- So: incomplete = 8109 → 8110..(8109+shots) → 8501; full = 8102 → 8103..8107 → 8108 → 8500. 8600 (`_813A`) is not
  set here (the manager / the 8500/8501 script end must lead to it — open).
- **Shots advance on the motion-end flag**, i.e. every shot's length = its own script/motion end. No per-shot timeout in
  this function; the only timers are the 180-unit charge and the 50-unit full-bar dash wait.
- Motion calls: `FUN_0882fa10(0, 0, fighter+0x130, motion, 0)` = play now; `FUN_0882fb90(0, 0, fighter+0x130, motion)`
  = queue after the current one.

## 4. Which controller a fighter gets = DATA (system.bin chrp row) [static, 2026-10-16T00:23Z]

`FUN_08a3eb70(mgr, attacker)` (burst start): victim = attacker vt+0x134 (his target); controller =
`FUN_08a3d720(mgr, chrp[+6])`, variant = `chrp[+7]` (chrp row = `*(fighter+0x5a4)`, system.bin, 144 B/row).
Rows read from test220 (`scratchpad/exb/chrp.py`): Cloud (13) **+6 = 0, +7 = 0**; owner 33 (P_SEV120) = **0, 0** (copy
of Cloud); Sephiroth (14) = 0, 2; P_ORG200 (23) and P_ORG800 (34) = 0, 0; every other fighter uses another controller
(+6 = 1..0x13). No row picks controller 0 variant 1 (`FUN_08a3a638`). → A different burst mini-game for #33 is a
1–2 byte chrp change (but every controller expects ITS owner's motion ids/blocks; not checked).

## 5. Manager per-frame update `FUN_08a3fe10` (phase = mgr+0x278, timer mgr+0x27c) [static]

- every frame (phase ≠ 0): victim struggle UI/gauge (`FUN_08a3e688` CPU, `FUN_08a3e14c`, `FUN_08a3dcd4`);
  **victim time-scale** `FUN_08b34cb0(scale, victim, slot 1)` = 1.0, or `attacker+0x1b8` while attacker+0x193 bit 0x40;
  attacker+0x193 bit 0x80 → `FUN_08a62020(attacker+0x1b8 * 2, DAT_08a62280, 0)` (global, unidentified) else reset.
- phase 1 (set by start): collision/state clears, attacker motion = `vt+0x4c()` = **8000** (stored mgr+0x274, played
  with `FUN_0882fa10(…, 8000, 1)`), screen fade (`FUN_08873b64`) → phase 2.
- phase 2: `FUN_08a3ee44` = move both fighters into the burst "arena" (`DAT_09b491b0` ← `DAT_09af84c0`,
  attacker+0x188 |= 2, stage systems paused) → phase 3.
- phase 3 (opening 8000): at timer ≥ 12 once: banner `vt+0x5c()` (Cloud: −1 = none); "Rapidly tap ◯" prompt
  (`FUN_08a39fa8` → `FUN_08a3dbd0(mgr, text 2)`) when < 60 frames of 8000 remain and the attacker is human. When 8000
  ends (motion-end flag) → victim struggle UI (`FUN_08a3e418`), **controller init `vt+0x14` = `FUN_08a39bd8`**
  (state zeroed, **motion 8101**), lock `FUN_08a3d904` if `vt+0x6c()` (Cloud: 1) → phase 4.
- phase 4/5: victim struggle `FUN_08a3e4a8`; **controller update `vt+0x2c` = `FUN_08a39db4` → `FUN_08a3a0b8`**; lock
  `FUN_08a3d904` every frame; when attacker+0x188 bit 0: `FUN_0880cd90(attacker+0x398)`.
  - **Finisher latch**: first frame the attacker's motion is in 8500..8700 → mgr+0x1e4 = motion, **mgr+0x1e2 = 1**.
  - **END** when the attacker's motion is < 8000 or > 8700, **or** (mgr+0x1e2 && attacker+0x188 bit 0 = the 8500/8501
    motion finished) → fade, **`FUN_08a3f448` (burst end: both fighters back to the stage at mgr+0x1f0 / +0x200,
    facing each other, flags restored)**, phase 0. ⇒ The burst lasts until the FIRST 85xx motion ends; 8600 `_813A`
    plays afterwards on the stage (it is not the controller's). → the clean exit is "reach an 85xx motion and let it end".
- No global burst timeout found: the burst ends only through the motion rules above (the 180-unit charge timer is the
  controller's). A shot motion that never ends (no end marker, looping) would hang the burst.

## 6. Victim lock `FUN_08a3d904` (every frame in phase 3→4/5 while `vt+0x6c` = 1) [static]

attacker = mgr+0x26c, victim = mgr+0x270. Script flag byte **attacker+0x194** (script state +0x64) decides:
- bit 2 (main **op 0x3e** window): victim+0x384 &= ~0x1000 (not held), nothing placed (attacker free).
- bit 1 (main **op 0x31** window): victim not held; victim position = its position with **z + 0.9** (per frame), set
  with `FUN_088359a8(victim, pos, 1)` + victim vt+0xe8. (= pushed along world Z; meaning unverified.)
- neither: victim+0x384 |= **0x1000 (held)**; if the victim is not at (0,0,0) it is put at `DAT_09af84c0` (arena
  origin, value not read yet); then the **attacker's base position = the victim's reference point**
  (`FUN_08835134(victim,1,0)` +8/+0xc/+0x10, y × victim+0x2c8 + mgr+0x298 × victim+0x2cc), `FUN_088359a8(attacker, p, 0)`.
  ⇒ every burst shot's travel is the ROOT-bone translation of the motion, relative to the victim. This is why Cloud's
  shots put the root metres away from (0,0,0); a Trinity motion can carry its own source travel the same way
  (opponent-relative by construction) — no root warp code needed, as long as op 0x3e/0x31 are not active.

## 7. Burst scripts (owner 33, test220 `obj/p_sev120.objx`, `scratchpad/exb/bdump.py`) [static]

Common main events: op 0x0c [5,0,0], 0x13, 0x0a (stay airborne), 0x06 (busy), 0x16 [0,180] + [1,180], 0x14 face.
- **Slow motion is script data**: main **op 0x26 [f]** → attacker+0x1b8 = f, +0x193 bit 0x40 → manager sets the
  VICTIM's time-scale to f (8000 54-80 0.2; 8103 0-24 0.2; 8104/8110 0-24 0.1; 8500 0-126 + 170- 0.2; 8501 170- 0.2;
  8101/8102/8109 = 0 → victim frozen while charging). Main op 0x34 [f] = same value + bit 0x80 → global `FUN_08a62020`.
- **Victim visibility**: one-shot **op 0x21 [p]** → victim +0x3b0/+0x370 = p/100 (8101 f0 = 0 → hidden during the
  charge; 8102 f90 / 8109 f0 / 8501 f0 = 100 → shown). op 0x1f [p] (8600 f0) = victim fade rate. (Alpha reading is
  a guess from FUN_08834df4/08834d60/08834d30.)
- one-shot op 0x02 "end motion now" ends 8104-8106/8110-8112 at 26-34 and 8107 at 24 → that is what advances state 3.
- **Hits are ordinary hitbox events** (main op 0x00 [atkp id, group 33] or op 0x43 [id, 33, magi 1197, …]), group 33 =
  the root r 7 "Limit" sphere: 8000 0x3ad 12-16, 0x3ae 52-58; 8103-8107 0x3af 20-26 (8104-8106 variant 1) / 0x77f
  20-26 (variant 2 = 8110-8112); 8108 0x3cf ×9 (4…136); 8500 0x708 92-116 + 0x709 116-122; 8501 0x709 120-126.
- atkp (kind 2 for all): 0x3ad/0x3ae power 14, 0x3af 2, 0x3cf 2, 0x708 2, 0x77f 8 (Bravery); **0x709 LIMIT_ATK06
  power 0, +8 = 0x02 = HP flag** = the final HP hit (Bravery → HP) in both finishes; 0x735 LIMIT_ATK07 (HP) and 0x68f
  LIMIT_ATK_EXIT are not in any burst block (code-used?).
- Banners: one-shot op 0x1d / code `FUN_08856d48(DAT_089d4dc8+0x69c0, fighter, text index, flag)` = fighter `text`
  chunk (0 burst name, 1 LIMIT BREAK, 2 Rapidly tap ◯!) — NOT the camera. Full bar: index 1, then index 0 after 50.

## 8. Arena entry / capture / release (decompile re-run with FUN_089a3868's "noreturn" flag cleared) [static]

- `FUN_08a3ee44` (phase 2): saves stage positions (mgr+0x1f0 attacker, +0x200 victim); attacker → `DAT_09af84c0`
  (zero vector: the same address is used as the black/zero colour of screen fades in one-shot op 0x1b); victim →
  (0, `vt+0x54()` = 0.0 for controller 0, chrp[+0x8c] (0.5 for Cloud/33) + radius(victim) + radius(attacker), 1);
  attacker faces +Z, victim −Z; **victim action `FUN_08834c10(victim, 0x12, 0)`**, attacker action 0; both
  +0x384 |= 0x1000; burst background `FUN_08acda90(DAT_08acee24, *(attacker+0x390)+0x30, vt+0x44())`.
- During shots: lock §6 (victim held at the arena origin, attacker anchored at the victim's reference point).
- `FUN_08a3f448` (end): restores flags/time-scale 1.0/colours, puts both back at the saved stage positions facing each
  other; victim gets `FUN_08a56f98(victim, {0, 15.0, 1.0, 0.5}, 1, 0)` (post-burst launch; unverified meaning) and a
  direction (`FUN_08835c24`). **If the finisher latch mgr+0x1e2 is set: attacker action 0x12, motion 0x2198 = 8600
  (`_813A`), queued motion 0x65 = 101**, effects 9000/9001 and 2 × (9002/9003 if the latched finisher was 8500 or 8700,
  else 9004/9005) from the attacker's FEP bank — owner 33's bank (Cloud copy) has no ids ≥ 9000 → no-ops.
  ⇒ 8600 is played by the END code, after the burst, on the stage.
- FINAL BLOW: no "final blow" code in the burst manager; the burst only ends by `FUN_08a3f448`. The victim's KO scene
  must come from the KO/HP system after the 0x709 HP hit (main session's investigation). The burst code never sets a
  victim MOTION itself (only action 0x12 at entry, hit reactions from atkp rows, the end launch).

## 9. Camera, effects, UI: data vs code [static]

| thing | where | data or code |
|---|---|---|
| burst camera | main **op 0x0c [5,0,0]** in every burst block → `FUN_08b3e840/864(*(f+0x5ac)+0x168, 5, 0)` = camera-manager bone mode with battle.bin camr entry 5 + bone camera_include of the CURRENT motion | DATA (motion camera curves + script) |
| slow motion | op 0x26 / 0x34 windows (§7) | DATA |
| victim visibility | one-shot op 0x21 / 0x1f | DATA |
| trails / flashes | op 0x2a (8888/9999), one-shot 0x1b (8102 f0 white 30, 8500 f124) | DATA |
| slot-bound effects (FEPA "slot") | _801A 47 f12 / 48 f54; _801B 50/51/52 f0; _802A 62 f14; _812A 49 f124, 64 f180; _812C 58 f20, 59 f96, 63 f200 (fep_dump test220) | DATA (Sora's .feb) |
| grade effects 50 CHOU_FIRE / 51 CHOU_SMOKE / 52 CHOU_LIGHT | `FUN_08a3a0b8` at taps 5/10/15, ids from overlay table 0x08a3b268 | CODE (ids resolve in Sora's FEP → repointing FEPA ids 50-52 is the data way to change them) |
| ◯ icons, LIMIT bar, prompt | burst UI layout (`FUN_088daa40/68`), per-tap icon flash | CODE + system UI |
| banners | `FUN_08856d48(…, text index)` from code (full bar: 1 then 0) / one-shot op 0x1d | text = DATA (fighter `text` chunk) |
| burst-end effects 9000-9005 | `FUN_08a3f448` | CODE (no-op for 33) |
| Cloud sounds 2200053/54 | `FUN_08a3a0b8` | CODE (EX_SND skips them for 33) |
⚠ notes/kh2-effects.md "FUN_08a3a638 spawns CHOU_SMOKE on every tap" is variant 1 (unused); Cloud's/Sora's variant 0
spawns 50/51/52 once each at the grade thresholds, nothing per tap.

## 10. Input checks available (overlay, PSP button bits in the low mask word) [static]

`FUN_08b326c4` ◯ (0x2000, CPU press id 1) — used by the burst; `FUN_08b3261c` **△ (0x1000, CPU id 2)**;
`FUN_08b32824` ✕ (0x4000, id 0); `FUN_08b328cc` □ (0x8000, id 3); d-pad up/right/down/left `FUN_08b3237c/424/4cc/574`
(0x10/0x20/0x40/0x80, ids 7/4/5/6). CPU presses come from `FUN_08a6427c(*(f+0x5c4), id)` (the burst's CPU tapper
`FUN_08a39b48` uses id 1). ⇒ A real △ step needs only a controller that calls `FUN_08b3261c` (+ CPU `FUN_08a6427c(…,2)`).

## 11. Code space for a Trinity controller [static, verified by byte scan]

- The battle-overlay cave 0x08B62F70..0x08B63170 is FULL (Reflect v2 + EX_SND = 496 B).
- **Dead function inside the overlay: `FUN_08a3a638` = controller-0 variant 1, 0x08a3a638..0x08a3abc4 = 1420 B
  (355 words), + its table `DAT_08a3b298` (160 B).** No chrp row has (+6, +7) = (0, 1). Byte scan of the whole overlay and
  EBOOT (jal/j/branch targets, raw pointers, lui+addiu/ori pairs): the ONLY references are the call at 0x08a39e04
  (in `FUN_08a39db4`, taken when ctrl[2] == 1) and the function's own table load at 0x08a3a644. `ctrl[2]` is written only by
  `FUN_08a40684` (from chrp[+7]) and reset to −1 by `FUN_08a40670`.
  ⇒ Setting **owner 33's chrp[+7] = 1** routes Sora's burst update into this slot with NO new hook site; Cloud (0,0)
  and Sephiroth (0,2) are untouched. Side effects of variant 1 (static): vt+0x24 shows prompt **text 1** instead of 2
  during the opening; vt+0x5c returns 0 → banner **text 0** (burst name) at 12 units into 8000. Both are Sora's own
  text chunk (spot33_battlenames: swap/rename entries).
- Other small room: EBOOT gap 0x089DD3C0.. = 172 B safe (docs/learn 7.6).
- Not usable without more proof: anything past 0x08B63170 (EBOOT 2nd LOAD segment).

## 12. Proposal: owner-33 Trinity route (for Q-20261015-CODEX-004) [design, nothing built]

### Milestone A (recommended) — own controller in the dead variant-1 slot, no new hook site
1. Data: system.bin chrp row 33 **+7: 0 → 1** (guarded: expect 0 or 1). Sora's burst update then runs 0x08a3a638.
2. Code (≤ 355 words at 0x08a3a638, table in 0x08a3b298; written by **spot33_reflect.py** as a new switch
   `TRINITY_CTL`, original 1420 + 160 B checked by hash before writing, switch off = originals + chrp 0 restored):
   - guard: owner byte ≠ 33 → jump to 0x08a3a0b8 (anyone else with variant 1 gets Cloud's logic).
   - states 0/1 = variant 0's charge unchanged (taps < 19, ◯ = `FUN_08b326c4`, thresholds 5/10/15/19, grade++,
     grade effect from OUR table → −1 = none, or KH2 FEPA ids Codex supplies; bar easing/CPU taps stay in the shared
     `FUN_08a39db4`). No Cloud sound calls (EX_SND then only protects Cloud's own path).
   - end of charge (timer ≥ 180 or bar ≥ 100): free grade effect/UI as variant 0 does, then
     - grade 4: banner (text index chosen by us), motion **8500 = one continuous A870 incl. the original final attack**,
       state 5 (optionally state 2 → banner swap after 50 units).
     - grade g < 4: motion **8109 + g** (incomplete Trinity prefixes of increasing length: g = 0 shortest), queued
       **8501** (common recovery + the HP strike, no grand attack), state 5. (If the model budget is tight: every grade
       → 8501 alone, as Cloud's grade 0.)
   - Exit is the manager's: latch at the first 85xx motion, burst ends when it finishes, 8600 `_813A` plays on the
     stage. No state-3 shot chain, so 8102-8108 never play for #33 (their GMO motions can be thinned to 1 key → frees
     model budget for the long A870 clip).
3. Scripts (type 8, Sora only): 8500 block 80 = source contact windows as op 0x00 hitboxes on group 33 (r 7 root
   sphere): pre-final contacts → 0x3cf (Bravery, power 2) or a new Bravery row, final attack → 0x708 then **0x709 (HP
   flag)** last; 8501 block 78 keeps its single 0x709; 8109/8110-8112 blocks: their prefixes' contacts as 0x77f/0x3cf
   (strip the cond-1 Cloud events of blocks 74-76; 8104-8106 never play). Keep op 0x0c [5,0,0] (bone camera),
   0x06/0x0a/0x13, face op 0x14; slow-motion op 0x26 windows where wanted; one-shot op 0x21 [100] at frame 0 of every
   post-charge motion (victim visible again after the charge hid it).
4. Motion data (Codex): A870 root travel stays in the root bone (attacker is re-anchored on the victim every frame —
   §6), with a constant offset so the root never sits inside the victim (Cloud's shots keep ≥ ~1-5 m); camera framing =
   camera_include/camera2_include curves in the same motion. Do NOT use op 0x3e/0x31 windows unless a release is wanted.
5. Text (spot33_battlenames): variant 1 shows prompt text 1 during the opening and banner text 0 at 12 units →
   text 0 = "Trinity", text 1 = the ◯ prompt, our controller's full-bar banner = the "LIMIT BREAK" entry.
Risks: (a) new code in a live overlay function's body — any missed caller would run Sora's code (guarded by the
owner check; byte scan found none); (b) variant-1 vtable side effects (prompt/banner, see §11) — banner 0 appears during
the opening (patchable later: at 0x08a3a0ac the return value 0 → −1 only affects variants ≠ 0/2);
(c) one long 85xx motion: hits/HP conversion rely on the normal hitbox pipeline (Cloud's 9 repeated 0x3cf windows
all land in test215, min. window gap unknown); (d) GMO budget (~10 KB left) — needs the 8102-8108 thinning first;
(e) all of it is static reading until traced.

### Milestone B — real △ "Break"
Same slot: after the charge, a BREAK state plays Trinity in segments; each segment's tail opens a window where
`FUN_08b3261c` (△) continues (CPU: `FUN_08a6427c(cpu, 2)` with a random delay like `FUN_08a39b48`), a miss → 8501.
Needs new type-7 motion ids or reuse 8102-8108 as segment carriers (they are free once Milestone A is in) and a UI
prompt (reuse the ◯ icon layout with another sprite, or banner text). Size not measured yet; A's charge + branch
logic is far smaller than variant 0's 352 words, so A + B should fit the 355-word slot (to be checked by --code-plan).

### Fallback 0 — data only, keep Cloud's controller
Full: 8102 (Trinity part 1, must last > 50 units so state 2 → 3 happens before it ends) → 8103-8107 pass-through
(one-shot op 0x02 at frame 0; 8104-8106 with cond byte 1 = variant 1 only, since blocks 74-76 are shared with
8110-8112) → 8108 (part 2 or pass-through) → 8500 (final attack). Incomplete: (grade 0) 8501, or 8109 → 8110[..8112]
→ 8501. Costs ≥ 1 frame hold per pass-through (6 on the full route) and every boundary pose must match (shared
GMO slots _804A-_806A serve both routes). No code, but the cuts are still Omnislash-shaped.

## 13. Runtime trace plan (needs the emulator; owner Claude) — completes Q-002 / Q-004 item 2
Log breakpoints (no pause): `FUN_0882fa10` (a3 = motion when a2 = attacker+0x130) and `FUN_0882fb90`; 0x08a3a16c
(state 0 → 1), 0x08a3a374 region (full branch), FUN_08a3f448 entry (burst end), FUN_08a3d904 entry (lock), FUN_08a3ee44.
Each hit: mgr = 0x09aef060: +0x278 phase, +0x27c timer, +0x1e2/+0x1e4 latch; state struct mgr+0x2a0: +0 state, +4 taps,
+8 shots, +0xc index, +0x10 grade, +0x14 bar, +0x18 timer; attacker/victim (+0x26c/+0x270): +0x180 motion,
+0x130+0x78 motion time, +0x130+0x70 end time, +0x80 position, +0x90 facing, +0x384 bit 0x1000, +0x194/+0x193 script
flags, +0x1b8 slow factor; camera eye 0x08baead0 / *(0x089d5ec0)+0x720; read DAT_09af84c0 and DAT_089d5eac
(frame step → seconds of the 180/50 timers). Cases: full (19 taps), each incomplete grade 0/1/2/3 (0, 5, 10, 15 taps),
KO and non-KO, Sora vs CPU Sora and vs Cloud (variant 0 untouched).

## 14. Milestone A built (static only, NOT run in game) — 2026-10-16T00:47:14Z

- **Writer:** tools/scripts/spot33_reflect.py (the one overlay/EBOOT writer), new switch **TRINITY_CTL, default OFF**;
  on with env `TRINITY_CTL=1` or `--trinity` (only for test discs). Code: block "TRINITY_CTL" (TRI asm, TRI_TABLE
  constants, `trinity_plan`, `trinity_regions`, `trinity_chrp`), called from `--apply-code`.
  tools/scripts/mips_asm.py gained lwc1/swc1/mtc1/add.s/div/mfhi (encodings checked against FUN_08a3a0b8's own words).
- **What it writes (on):**
  - overlay 0x08a3a638: TRI = 245 words (room 355), the rest of the dead variant-1 body keeps its original bytes;
    0x08a3b298: 64-B table {thresholds 5/10/15/19 + grade effects 0x32/0x33/0x34/−1 (= Cloud's), incomplete motions
    [8501, 8110, 8111, 8112], full 8500, follow 8501, banners 1 (LIMIT BREAK) / 0 (burst name)}. Both regions are
    sha256-checked against the clean overlay (dumps/extracted) before writing; anything else stops the run.
  - site 0x08a3a048: prompt text index 1 → 2 (variant-1-only prompt → "Rapidly tap ◯!" like Cloud).
  - site 0x08a3a094: the branch target 0x08a3a0ac → TRI_B5C (0x08a3a9c4): reached only for variants ≠ 0/2;
    TRI_B5C returns −1 (no early burst-name banner in the opening) when the manager's attacker is owner 33, else 0
    (= original). Owner-scoped.
  - system.bin chrp row 33 **+7: 0 → 1** (in place, same method as spot33_soundids.py's chrp row-33 edits; asserts +6 == 0
    and +7 ∈ {0,1}). Lives in --apply-code (not the objx data part) so one switch drives code + data together.
- **TRI behaviour:** owner ≠ 33 → jump to 0x08a3a0b8 (Cloud's logic). States 0/1 = Cloud's charge (no Cloud sound).
  End of charge (timer ≥ 180.0 / bar ≥ 100.0; float bits compared as ints, both ≥ 0): grade effect + 0x58 UI freed,
  **victim shown again** (`FUN_08834df4(1.0, victim = ctrl[1])` = what one-shot op 0x21 [100] does in 8102/8109/8501 —
  needed because 8500 and 8110-8112 have no op 0x21 and 8101 hid the victim), then
  grade 4 → banner 1 + bar flash, **motion 8500**, state 2 → after 50.0: banners cleared, banner 0, bar freed, state 5;
  grade 0 → **8501**; grade 1/2/3 → **8110/8111/8112** with **8501 queued**; state 5. Timer epilogue = Cloud's. Exit =
  the manager's 85xx latch (8600 on the stage).
- **Disc:** `dumps/ULUS10566-test240-trinityctl.iso` = copy of test241-refsnd + `TRINITY_CTL=1 spot33_reflect.py
  --apply-code` (sha256 prefix 6d9e8ba8fa292c8d). Differs from test230 in sectors 186009-186011 (overlay) and 862388
  (system.bin chrp) only. Re-run = no change; the same script with the switch OFF on a copy of test231 gives a file
  **byte-identical to test230** (round trip checked). Note: the number 231 is also used by the Fire/Thunder helper's
  test231-t7p59 (different file).
- **Static checks done:** TRI disassembled back and reviewed (delay slots, a0 = state pointer at every use, stack 0x20,
  f12/f13 = 0.0 for FUN_0882fa10/fb90 like Cloud); only reader of chrp +7 in the battle decompile is the burst start.
- **Runtime test (Milestone A, with the §13 trace):** vs CPU Sora + vs CPU Cloud (Cloud must still run 8102-8108);
  full bar (19 taps) → 8101 → 8500 → burst end → 8600; grades 0/1/2/3 (0/5/10/15 taps) → 8501 / 8110→8501 / 8111→8501 /
  8112→8501; check the victim is visible after the charge, LIMIT BREAK + name banners, no early banner in 8000, prompt
  text, HP damage from 0x709, clean exit/rematch, CPU Sora's own burst (CPU tapper). Known stand-in limits: 8500 is
  Codex's _812C (built to follow 8108), 8110-8112 are Cloud-route slashes (_804A-_806A) → positions/looks will jump.

## 15. Milestone A runtime, partial (test246-trinityctl vs CPU Sora) — paused at 2026-10-16T04:18:21Z for Mat's play-test

Disc dumps/ULUS10566-test246-trinityctl.iso (= test245-tumble + TRINITY_CTL=1). Driver: scratchpad ppexb_tri.py
(copy of ppexburst_mirror.py + TRI=1 state log of manager 0x09aef060 / state struct +0x2a0 every 0.1 s, TAPS=n = tap until
the controller has counted n, HEAL=1 = foe damage reset). No breakpoints used. Logs/videos: scratchpad tri/.
- **Runtime constants:** DAT_089d5eac (frame step) = **2.0** per frame → charge 180 units = 90 frames = 3 s at 30 fps; full
  bar wait 50 units = 25 frames. DAT_09af84c0 = (0,0,0,0) (arena origin confirmed).
- **Manager phases seen** exactly as §5: ph 1 → 2 (both moved: S (0,0,0), O (0,0,1.7) = 0.5 + radii) → 3 (8000, victim
  held 0x1000) → 4 at 8101 (victim alpha +0x3b0 = 0.00 = hidden; S at (0,0.9,0) = anchored on the victim point).
- ✅ **Full bar (19 taps):** grade 1/2/3/4 at taps 5/10/15/19; st 1 → 2 at charge end, **8500 directly**, victim alpha
  → **1.00**, latch 1/8500, st 5 after 50 units; banners **LIMIT BREAK → "Ars Arcanum"** (name), Critical hits, burst end →
  "HIT!" scene → back to battle (both idle, phase 0); victim damage +617 (HP hit landed). Video tri/full1.mp4, sheet
  tri/full1_sheet.png.
- ✅ **Grade 0 (2 taps counted):** **8501 directly**, victim visible, latch 8501 → burst end → **8600 → 101 → idle**.
- ✅ **Grade 1 (5 taps):** **8110 → 8501 → 8600 → 101 → idle**, victim visible, held bit cleared by 8110's op 0x3e window.
- Not yet done: grade 2 (10) and grade 3 (15) (two attempts: the HP attack missed / KO'd before the burst), the CPU-Cloud
  control (Cloud must still run 8102-8108), KO → rematch, video review of the grade-0/1 clips (tri/h5.mp4, g5.mp4).
- Driver note: the emulator runs far below real time while the driver polls (90 frames ≈ 20 s wall); count taps from
  the controller (+0x2a4), not from presses sent. After the last run PPSSPP's debugger socket stopped answering
  (cpu.status timed out) while the GAME keeps running normally (screenshots change; battle on screen) → PPSSPP left
  RUNNING for Mat. No breakpoints were set, ppsspp.ini not touched, no recorder/driver left running.
- No crash/freeze of the game in 4 bursts. TRINITY_CTL stays DEFAULT OFF in spot33_reflect.py until the remaining cases pass.

## 16. Codex v5 Trinity integrated: test257-trinity (static; NOT run in game) — 2026-10-16T07:05:16Z

Base **dumps/ULUS10566-test248-exguard.iso** (sha256 2964d2acc9950bf26b597c416a00e68ec1b04ce9e84304a46bd67d728a7a56ef,
re-hashed). Disc **dumps/ULUS10566-test257-trinity.iso** (sha256 432e2bb570a2e39ab7bbc938f268368fdc624b1b6632b53cb00abca488291306).
Differs from test248 only in: PACKAGE_INFO sizes (26052-26054, 26064), overlay (186009-186011, 186021), system.bin chrp
(862388), objx + 1P/2P/3P GMO (872058-876522). effe unchanged (848,640 B, 2972c168…).
- **Model:** test248's 1P GMO (787a1981…, 2,497,336 B, = 2P = 3P) + `gmo_motion take` v5 `_812A` (= _812A.motion
  eeb414cb… byte-exact) + continuous `_812C` (= _812C.motion e76dbcb4… byte-exact; the installed _812C was NOT it:
  body db8568e8 vs d05c3d12). Same 54-bone skeleton/bone names, bone refs 0..0x35 in both clips; every other byte
  identical (checked with both parent sizes masked). Result **2,478,576 B** (sha256 8683ff3c45c53cd52adb3e3ca56552bdef7292d4a8673709994cebce722c801a),
  18,760 B smaller than test248 → no thinning. On 1P/2P/3P (spot33_2p), all three read back identical.
- **Events:** NEW tools/scripts/spot33_trinity.py (re-runnable, asserts rows 8500→80 / 8501→78 unshared, sound base from
  the bank): 8501 = 3 × op 0x00 [0x3CF, 33] at 16-31/35-39/51-58, no HP; 8500 = 9 × 0x3CF + 0x709 at 213-223 (event-contract
  windows). Kept camera 0x0C [5,0,0], 0x06/0x0A/0x13/0x16, face 0x14, voices; one-shot 0x21 [100] at 0; trails 0x2A over the
  swings; KH2 sounds 90@1 + 83/84/87 two ticks before each window, heavy 88/89 on the final HP. Removed: Cloud-timed
  116-126 HP, 0x708, op 0x26 slow windows (8501's 0-126 victim freeze), flash moved 124 → 213. End = GMO length (168/274).
  objx 1,534,800 B (sha256 4efed5ac3704f0e7d9b566422dc885033d4c9a4a475fad7129ab4e848990c0e8).
- **Controller (spot33_reflect TRINITY_CTL, on for this disc, default OFF):** TRI_INC = 8501 for grades 0-3, TRI_FOLLOW
  = 0 (code now queues only if the table value is nonzero) → 8501 once; grade 4 → 8500. TRI 290 words of 355.
- **Grounded exit (incomplete only):** new site 0x08a3fca4 (FUN_08a3f448's call to FUN_08834c10 with action 0x12) → TRI_EXIT
  (0x08a3aa04): owner 33 AND latched finisher mgr+0x1e4 == 8501 → action state 0, position = restored stage position
  with **y − 1.0** (undoes FUN_08a3ee44's lift "saved y += 1 − height_above_ground (fighter+0x3c0) when < 1"; ground ≤
  saved y − 1 always, so never below ground), **motion 1 (_000A battle stance)**, and it returns past the original 8600 +
  queue-101 calls (to 0x08a3fce0). Everyone else / the full route → the original call (8600/_813A unchanged).
  The 60-frame end fade + teleport to the stage separate the arena from the stage, so the v5 model-space root delta
  (−1.014, −0.902, −1.739) is consumed inside the arena (anchor y 0.9 measured in §15 + root −0.902 ≈ floor) and is NOT
  re-applied after the teleport (idle _000A has its own root).
- Off round trip: TRINITY off on a copy of test257 restores overlay + EBOOT + chrp sectors byte-identical to test248.
- Not done (outside this job's scope): FEPA slot-bound Cloud effects still bound to _812A (49 f124, 64 f180) and _812C
  (58 f20, 59 f96, 63 f200) — check in game, Codex/effects owner; burst-name banner still "Ars Arcanum" (text chunk);
  owner-33 yellow "Break" gauge = pending (not built).

## 17. Runtime checklist for test257-trinity (emulator owner schedules it)
Driver: scratchpad ppexb_tri.py (TRI=1 state log, TAPS=n counted by the controller at mgr+0x2a4, HEAL=1), go_battle
OPP=sora (Minimal + Order's Sanctuary verified). No breakpoints needed; poll the TRI line + motions.
1. Thresholds: TAPS 0, 4, 5, 9, 10, 14, 15, 18, 19 → grade 0,0,1,1,2,2,3,3,4 (check state +0x10). Grades 0-3: S8101 → **8501
   once** (no 8110-8112, no second 8501), latch 1/8501; grade 4: 8101 → 8500, latch 8500, banner LIMIT BREAK → name.
2. Hits: 8501 = exactly 3 Bravery contacts (damage numbers / foe Bravery drops 3×), no HP damage (status +8 unchanged);
   8500 = 10 contacts, HP damage at the last (213-223), status +8 rises once.
3. Incomplete exit: after 8501, NO 8600: S motion goes straight to **1** (battle stance) on the ground (S y == ground y,
   e.g. 0.00 on Order's Sanctuary; +0x3c0 == 0), no float/fall/snap/slide after the fade; full route still 8600 → 101 → land.
   Also an AIR-started burst (HP attack high up): expect a short fall from (saved y − 1) — note it.
4. Victim: visible after the charge (alpha +0x3b0 = 1.0), held bit 0x1000 cleared after the burst, victim tumbles /
   recovers, no stuck phase (mgr+0x278 back to 0), face restored (op 0x14 [0,2] at the end), camera follows (camera_include).
5. Cloud's own EX: Sora vs CPU Cloud AND a Cloud burst (Cloud must run 8101 → 8102-8108 → 8500 with his UI/sounds).
6. CPU Sora's own burst (mirror; CPU tapper) uses the same route; 2P model shows the new clips.
7. KO: full burst KO (LOWHP) → FINAL BLOW → results (no input on results) → rematch → incomplete and full again.

## 18. Trinity camera: the real test262 bug + test263 (static, 2026-10-16T07:48:58Z)

- **Root cause of test262's screen-filling skin = the body, not the camera.** GMO motions SHARE fcurves between
  entries; Codex's _812A/_812C use ONE constant (1,1,1) scale fcurve for all 54 bones. gmo_camfov.py (first version)
  set z = 45 in that shared fcurve → every bone scaled 45× along local Z (checked in test262's 1P GMO: 54/54 scale
  channels z = 45; test262 GMO == test257 GMO + old camfov byte-for-byte). test259's brown screen = FOV 1°.
- **gmo_camfov.py fixed**: a camera scale entry whose fcurve is shared gets its own appended copy (entry repointed,
  motion/parents grow); camera-only fcurves edited in place; re-run = no change. Only bones 0/1 scale change (verified).
- **Burst camera semantics (decompile, FUN_0886b6bc / FUN_08836a30 / FUN_08b3e6d0, noreturn fixed):** op 0x0C [5,0,0]
  → camera bone = model+0xe8 = bone 1 camera_include; eye = fighter matrix × bone translation; look = fighter matrix ×
  bone rotation × (0,0,−1); up = rotation × (0,1,0) (camr entry 5 flags 0x18: bit 8 keeps the bone's up); FOV = the
  bone's scale z. camera2_include (bone 0) is not used by op 0x0C [5,0,0]. Checked offline on Cloud's own _812A/_812C
  (proven in game): they frame Cloud / both fighters with this convention.
- **Previews** (NEW tools/scripts/gmo_camview.py: stick figures from bone 1's point of view, victim idle at
  (0,−0.9,0), floor grid): dumps/renders/trinitycam/
  - cloud_812A/812C.png (reference, framed), donor248_812A/812C.png (test248's timed Trinity: Cloud's camera on a body
    near the origin — _812A frames empty space until ~f60),
  - **test263_codexcam_812A/812C.png: Codex's own camera + FOV 45 frames BOTH fighters in every sampled frame**
    (high over-shoulder overview, ~6.5 m),
  - test263b_camdonor_812A/812C.png: the requested Cloud-camera transplant (retimed) frames empty space for most of
    _812A and the middle of _812C (it follows Cloud's root path z −6…−13, Codex's root stays within ±3 m).
- **Tools:** NEW tools/scripts/gmo_camcopy.py DONOR IN OUT _812A _812C (bones 0/1 T/R/S from the donor, retimed donor
  camera span → target span, never edits shared fcurves, re-runnable); donor motions saved:
  dumps/models/camdonor/_812A.motion (dd08d73d…, 40,484 B) and _812C.motion (83ae2ada…, 42,232 B) from test248's 1P GMO.
- **Discs** (copies of test262-halfdome; model on 1P/2P/3P; spot33_barrier re-run → BARRIER_SCALE 4.0; Trinity
  scripts/controller already in test262):
  - **dumps/ULUS10566-test263-trinitycam.iso** (recommended) = Codex camera + fixed FOV 45: GMO 2,478,784 B, sha256
    41ea78a592387068b870fac3ae0531a1ce201c38ec7f932297d89644b655f218; ISO c590cdabe43ade27c3360bc664c499a6db87e5045a3eb31bb761d205ce78b656.
  - **dumps/ULUS10566-test263b-camdonor.iso** = the requested transplant (on top of the fixed FOV): GMO 2,479,728 B,
    sha256 3c2b7741a6ede84c0734ca3d3b9374a5d4f75044e16ab3398c30210f760cb303; ISO 2188b72327f5ae5130362f6e93760e4f2de6a889592661dc13e06c10684f9cad.
  - objx identical on both (e861def7…; spot33_barrier.py changed on disk at 10:36 local during my checks — re-run gives
    "nothing to do" now).
- build_sora.sh: gmo_camfov (fixed) stays after the two takes; gmo_camcopy only with CAMDONOR=1. Budget fine (≤ 2,479,728).
- Runtime (pending, Mat playing): test263 first — check camera frames both fighters, normal body proportions, both routes.

## 19. Trinity ready package: bar-fill voice + yellow BREAK gauge → test270 (static, 2026-10-16T08:42:16Z)

- **Base** dumps/ULUS10566-test269-combined.iso (ready motions _812A f1269014… / _812C e1c79f95…, model de6668c0…
  2,487,252 B on 1P/2P/3P; events = patch_events output: final HP 237-247, one 21900091 @237, voice 21910032 @235,
  no launch speech — all re-verified). **Disc dumps/ULUS10566-test270-trinityvoice.iso**, sha256
  eb5905b2b327969482573619f7e2315c6812777bba9130a7f32097214b86a6ce; differs from test269 only in overlay sectors
  186009-186010 and Sora's objx spec chunks (objx sha256 3ad8eac0b670a9e50c7c7cd90cf8e0cb901ae9f77abf797097451aa878daa8ba).
- **Bar-fill voice (spot33_reflect TRINITY_CTL):** Codex's 35-word callback appended to TRI as TRI_BAR_VOICE at
  **0x08a3aac0** (= TRI_BASE + 290 words: my layout matched Codex's assumption; the grounded exit TRI_EXIT is at
  0x08a3aa04, before it). TRI = 325 of 355 words. New site **0x08a39ecc**: the call to FUN_088d9aec becomes
  a call to 0x08a3aac0 (delay slot kept); original-word guard + KNOWN_PATCHED + rollback. The
  assembled words are identical to Codex's controller-candidate/bar-fill-voice.bin (independent assembler). FUN_088d9aec
  = a single float store (the store the callback repeats for every fighter); FUN_0884ea08(fighter+0xcf0, id, 1) = the game's
  own voice call (FUN_08b33f8c). Fires once: next frame the controller ends the charge (state 2), the setter is no longer
  called. Not covered: a charge ending on the 180-unit timer while the displayed bar is still < 100 (no voice then).
- **Yellow "BREAK" gauge (NEW tools/scripts/spot33_breakgauge.py, data only, owner 33 only):** the burst UI is drawn from
  the attacker's own fighter file: spec type 3 = 64x128 INDEX8 atlas (◯ icons, frame, fill, label "LIMIT" at
  (29,118)-(63,127)), spec type 17 = SEQ layout, sprite records 9-15 = the fill sprite (3,116)-(4,123) in 7 vertex
  colours (pink→orange→yellow→green→blue→blue→violet as it fills). Label redrawn as "BREAK" with the same palette
  shading (core 130, outline 8, shadow 12, drop 3); all 7 fill colours → (255,220,40). All 6 language blocks (identical).
  Preview of the atlas label: scratch t270/break_crop.png. Cloud's file untouched.
- **spot33_trinity.py** now leaves blocks alone when they already carry Codex's +24 ready timing (a re-run can't undo
  patch_events.py). NEW tools/scripts/pkg_get.py (read one package file out of an ISO).
- **build_sora.sh:** take _812A/_812C from trinity-ready.gmo (replaces v5/continuous) → gmo_camfov (no-op: FOV already
  set); spot33_breakgauge after spot33_battlenames; at the very end (after spot33_exguard, same order as discs
  262-269): patch_events.py (objx→objx) then Codex Fire v1 --kind fire → visibility-v2 revise --kind fire → appearance
  v3. These Codex steps are NOT idempotent on their own output (re-running Fire v1 over v2/v3 changed 212 effe bytes in a
  test) → run once per fresh build. TRINITY_CTL is still default OFF in the script (build needs TRINITY_CTL=1).
- Off round trip: TRINITY off on a copy of test270 restores overlay + EBOOT + chrp sectors byte-identical to test248.

## 20. test271: bar-full voice fixed + HP-attack Reflect (runtime-traced, 2026-10-16T10:26:16Z)

**Bar-full voice (Mat test270: never heard).** Runtime (test270 vs CPU Sora, separate breakpoint client
scratchpad t271/bptrace.py — log breakpoints inside the driver stalled PPSSPP's debugger socket): the callback ran every
frame with state 1 / grade 4 (0x08a3ab14 hit), but at the 100 % frame the old displayed value t2 was ALREADY 100.0
(t2 == f12 every frame after the easing slowed to +1/frame) → the "previous display < 100" test never passed, the voice
call (0x08a3ab30) was never reached. Fix: latch at state +0x60 (manager zeroes mgr+0x2a0..+0x5e0 per burst; TRI and the
shared cleanup never touch it): first state-1 / grade-4 / fill-100.0 frame → voice, latch 1; TRI's grade-4 branch calls
the same TBV_VOICE (covers a charge ending on the 180-unit timer). **Verified on test271:** 0x08a3ab38 (latch set) hit
once at fill 100.0, FUN_0884ea08(fighter+0xcf0, 0x014e521a = 21910042, 1) called once, the voice manager's current id
(fighter+0xcf8) = 21910042 right after, then 8500. Played once per charge.

**Reflect vs Cloud's HP attacks (Mat test270: "only blocked").** Runtime (test271 vs CPU Cloud, t271/c2trace.py
logging C2 entry fields): the stance-swapped EX guard (blocks 60/67 = byte-identical event copies of 20/21: GUARD hit
778 = 0x30a kind 4, op 0x46, barrier op 0x19) passes every C2 condition: outcome 3, incoming class 1 (melee hitbox),
touched kind 4, owner == source, +0x542 0 → C2slow → C4 reflects (Cloud recoils 901/911; Bravery moves, e.g. Sora
500→578 / Cloud 1084→1006 on a guarded Cross-Slash). So reflect worked — but the guarded hit of an HP attack is its
first, **Bravery** part (atkp kind 2, e.g. Cross-Slash 0x365 LAND_FINISH1_1; Braver-type 10092 = 0x369 AIR_FINISH1_1
+ a magi HP 0x64c), Cloud is interrupted and his HP hit (0x367 / 0x37d / magi) never happens → no HP damage back.
**Fix (TRINITY_CTL, C2):** before queuing, C2 calls TRI_HPROW (last 27 words of the variant-1 slot, TRI now 355/355):
incoming row (fp+0x34) kind 2 and not HP → walk forward in the attacker's sorted atkp table (≤ 24 rows, stop when ids
stop ascending) to the next kind-2 row with the HP flag and reflect that id: the attacker is "hit by his own HP attack"
= HP damage = his own Bravery, his Bravery resets (FUN_088131bc / FUN_08ae5bc8). Offline walk on the real tables: Cloud
0x365/0x366 → 0x367, 0x369…0x378 → 0x37d; Sora/others terminate cleanly (stop / 24-row limit). Normal Bravery attacks
(kind 0) unchanged. Cave 496 → 500 B (+1 jal; 512 B allocation).
- **Verified in game on test271 (vs CPU Cloud, Minimal, Order's Sanctuary):** Cloud's 10092 (Braver-type, Bravery hit
  0x369 + magi HP) guarded twice → C2 → TRI_HPROW found 0x37d → C4 queued 0x437d → Cloud HP 3125 → 2740 and 2740 →
  2585 (= his Bravery), his Bravery → 0, blown away (702). Ordinary Bravery reflects (0x35d, 0x517, 0xb85…) unchanged.
  Cross-Slash (10090) was guarded and reflected at its first hit in the earlier run (0x365, Bravery, before this fix);
  with the fix that hit maps to 0x367 (offline walk) — not re-observed (the CPU used it twice, my scripted guard missed).
  Voice re-checked on the final build: full bar → FUN_0884ea08(…, 21910042, 1) once; incomplete grade 1 → no call.
- **Disc dumps/ULUS10566-test271-trinityfix.iso** sha256 3d3b85cf4d548722ffb585cc4eea42e689cd29465b0f051140f96768682d8db0
  (= test270 + spot33_reflect.py: TRI 355/355 words, cave 500 B; changed sectors 27, 571, 185824, 186009-186010, 186021,
  186329, 186331, 186603). Re-run = no change; TRINITY_CTL=0 on a copy → overlay/EBOOT/chrp = test248 again.
  Tools: scratchpad t271/bptrace.py (separate breakpoint client), t271/c2trace.py (C2 field logger).
  Note: TRI slot is now FULL (355/355); further controller code needs new room. (2026-10-16T11:21:55Z)
- **Mat on test271 (2026-10-16T11:51:20Z): "the voice works now, reflect took cloud's hp" = both fixes USER-VERIFIED.**

## 21. New code room for the controller — static study (2026-10-16T11:32:50Z)

### ❗ First: the variant-1 slot is NOT dead — it is Garland's
Re-reading every chrp row's (+6, +7) pair properly (test248 system.bin): (0,0) Cloud 13, P_ORG200 23, Sora 33 (orig),
P_ORG800 34; **(0,1) = owner 2 P_ONE200 (Garland)**; (0,2) Sephiroth 14; other controllers 1-19 as listed below. My
§11 claim "no chrp row picks (0,1)" was a misread (I took the wrong bytes). Consequence for every TRINITY_CTL build
(test257 … test271, and the canonical build now that the default is ON): **Garland's EX Burst controller FUN_08a3a638
and its table 0x08a3b298 are overwritten by TRI**; for owner ≠ 33 TRI jumps to Cloud's variant 0 (FUN_08a3a0b8), so
Garland's burst runs Omnislash logic with his own motions, and his opening prompt shows text 2 instead of 1 (site
0x08a3a048 is not owner-scoped). Untested — could look wrong or hang. Until TRI is moved: test Garland or turn
TRINITY_CTL off for builds Mat plays with Garland.
All pairs: (1,0) 17 (1,1) 18 | (2,0) 11 | (3,0) 3 (3,2) 9 (3,3) 1 (3,4) 31 | (4,0) 7 (4,1) 8 | (5,0) 12 | (6,0) 4 |
(7,0) 6 (7,1) 10 | (8,0) 5 | (9,0) 15 (9,1) 16 | (10,0) 19 (10,1) 20 | (11,0) 21 | (12,0) 22 (12,1) 30 | (13,0) 27 |
(14,0) 25 | (15,0) 26 | (16,0) 28 | (17,0) 29 | (18,0) 24 | (19,0) 32. Controllers only contain handlers for variants
that exist (e.g. controller 3 dispatches 0/2/3/4, no variant-1 code) → no dead variant code anywhere.

### Candidates (scratchpad t272/deadscan.py + rangeref.py: every function start / every address in a range checked
against jal/j targets, branches, raw data words, lui+addiu/ori/load/store pairs in EBOOT + battle + menu + extra overlay)
| # | range | size | proof | risk |
|---|---|---|---|---|
| 1 | shrink TRI | ~25-30 words | shared owner-check helper (4 copies), table base kept in s2 instead of 6 lui/addiu pairs | none (our own code) |
| 1b | EX_SND in the cave | 14 words (+2 sites back to original) | Sora no longer runs variant 0 (TRI), so the skip never triggers | none |
| 2 | **EBOOT 0x089c1c8c-0x089c2508** | **2172 B = 543 words** | no reference into the range from EBOOT, battle, menu or extra overlay (only 5 "branches" that are rodata words at 0x089d1d54-0x089d5db0); a self-contained loop (exit flag DAT_09af7208) = unused thread/library body | low-medium: static proof only |
| 2b | EBOOT 0x089a8b14-0x089a8f0c | 1016 B = 254 words | same scan; only refs are its own switch table at 0x089d1fb4 (dead with it); format-driven unpacker with callbacks = unused library code | low-medium |
| 3 | battle overlay dead functions | 0 | the scan found none (all 'unreferenced' EBOOT-only hits are used by the menu overlay) | — |
| 4 | EBOOT gap 0x089DD3C0-0x089DD46C | 172 B = 43 words | the overlay loader writes the ELF header to 0x089DD46C+ only (§7.6) | low |
| 5 | past 0x08B63170 | 0 | EBOOT segment 1 (bss, 16 MB) starts there | not usable |
Dead rodata: nothing found that is referenced only by dead code except 2b's jump table (~0x60 B). The PSP has no NX
bit, but rodata room is tiny here; not worth it. EBOOT text is loaded once at boot (no i-cache issue for disc patches).

### Recommended plan (also fixes Garland)
1. Move TRI (code + table + TRI_HPROW + TRI_BAR_VOICE + TRI_EXIT + TRI_B5C) to EBOOT 0x089c1c8c (543 words; TRI now
   ~371 words incl. table → ~170 words left; 2b gives 254 more, item 1/1b ~40 more).
2. Restore FUN_08a3a638 (1420 B) and DAT_08a3b298 (160 B) to the original bytes (Garland).
3. New site 0x08a39e04 (the call to 0x08a3a638 in FUN_08a39db4) → a call to TRI_DISPATCH: owner 33 → TRI, else
   0x08a3a638 (Garland's own code). TRI's own guard then jumps to 0x08a3a638 too.
4. Site 0x08a3a048 (prompt text): a call to a TRI_PROMPT stub: owner 33 → text 2, else keep 1, then on to 0x08a3dbd0.
   0x08a3a094 (TRI_B5C) is already owner-scoped.
5. spot33_reflect.py: add the EBOOT region as a guarded write (sha256 of the original 2172 B; accepts original or
   ours), sites with original words + KNOWN_PATCHED, everything under TRINITY_CTL; TRINITY_CTL=0 restores the EBOOT
   range, FUN_08a3a638/table, all sites and chrp +7 = 0 (same round-trip test as before).
6. Before shipping: a probe disc whose two dead functions start with a marker store + return (or a log breakpoint
   session) played through menus, Story/Quick Battle, replays and Extras — a hit means "not dead". Then Garland's EX
   Burst + Sora's full/incomplete + Cloud's EX in game.

### 21.1 Implemented — test272 (STATIC, not run in game) — 2026-10-16T11:41:02Z
- spot33_reflect.py (TRINITY_CTL): TRI moved to the dead EBOOT function: code 0x089c1c9c (368 words; room 523 → 155
  words free, + dead 0x089a8b14 254 words + EBOOT gap 43 words still unused), table 0x089c24c8 (64 B); the first 4
  words of the dead function stay original (probe hook). EBOOT range sha256 c14866cb… (clean) checked before any write;
  accepts original / ours / probe; TRINITY_CTL=0 restores it.
- Shrink: TRI's own owner guard replaced by the dispatcher, table base loaded once into s3 (6 lui/addiu pairs → 1 move),
  EX_SND dropped from the cave when TRINITY_CTL is on (cave 500 → 444 B; sites 0x08a3a15c/0x08a3a374 back to
  original, so Cloud's own burst sounds are exactly vanilla). With TRINITY_CTL=0 the cave is the old 496-B one incl.
  EX_SND.
- **Garland restored:** 0x08a3a638-0x08a3abc4 and 0x08a3b298-0x08a3b338 = the clean bytes (verified byte-for-byte vs
  dumps/extracted/OVL_BATTLE_APP.ELF). New sites (all TRINITY_CTL, guarded, rollback):
  0x08a39e04: the call to 0x08a3a638 → a call to TRI_DISPATCH (0x089c1c9c: owner 33 → TRI, else 0x08a3a638 = Garland);
  0x08a3a048 prompt → a call to TRI_PROMPT (owner 33 → text 2, else the original text 1);
  vtable word 0x08a3b1bc (controller-0 vt+0x5c, was 0x08a3a084) → TRI_VT5C (variant 0/2 → −1, variant 1: owner 33 →
  −1 else 0 = original semantics); 0x08a3a094 (old TRI_B5C branch) back to original; 0x08a3fca4 / 0x08a39ecc / C2 now
  jump into the EBOOT range. chrp row 33 +7 = 1 kept.
- Static checks: battle overlay differs from the clean file ONLY at the 8 site words (0x08a39e04, 0x08a39ecc,
  0x08a3a048, 0x08a3b1bc, 0x08a3fca4, 0x08ada22c, 0x08adaaac, 0x08adb32c) + the cave → Cloud's variant 0 and Sephiroth's
  variant 2 code are vanilla; re-run = no change; TRINITY_CTL=0 on a copy → overlay, EBOOT and chrp sectors identical
  to test248. Disassembly of TRI_DISPATCH / TRI_VT5C / TRI_PROMPT / table loads reviewed (scratch t272/tri_dis.txt).
- **dumps/ULUS10566-test272-trimove.iso** sha256 c3e08325771f956ed0172bf4a04eb192f7f41025662eafeabfdbac9946bc64e5
  (copy of test271 + spot33_reflect.py --apply-code).
- **dumps/ULUS10566-test272p-deadprobe.iso** sha256 a575dcaa422c6ed5ffbc6b0c2d468d7e215dafb712f73cb3a67fc35fdd4fa734
  = test272 + marker stubs (scratch t272/deadprobe.py): 0x089c1c8c → a stub that stores its return address at
  0x089a8c00 and returns 0; 0x089a8b14 → the same with 0x089a8c04. **Marker words: 0x089a8c00 and 0x089a8c04 (initially
  the original words there).** Any other value = that dead function was called; the value is the caller's return address.
- **Mat on test273 (2026-10-16T13:10:49Z): Garland's EX Burst fixed and fine = TRI move USER-VERIFIED.**
- **Probe result (2026-10-16T13:52:42Z): PASS.** Mat played test272p (menus, Quick Battle, replay, Extras/Museum, Story battle). Debugger read: 0x089a8c00 = 0x8fb10004, 0x089a8c04 = 0x8fb00000 (both unchanged) and both marker stubs present in RAM → neither dead EBOOT function (0x089c1c8c, 0x089a8b14) was ever called. TRI's EBOOT home is safe.

### 20.1 TRI_HPROW bounded (release QA D-313-06) — static, 2026-10-16T21:40:38Z
- The HP-row walk now stays inside the ATTACKER's own atkp table: table = *(attacker+0x49c) (attacker = hit +0x18;
  header +4 = count, rows from +8 — the same table FUN_08837f14 binary-searches). Incoming row outside it (global
  fallback table) → no change; the walk stops at rows + count×0x44 and still after 24 rows (as before); the loop's bound
  check has a nop delay slot, so nothing past the end is read. 33 words (was 27); TRI range 519/523 words.
- Offline simulation of the shipped algorithm on all 136 atkp tables of the disc (1164 walks): old walk read past the
  table end 160 times, new 0; found HP ids identical in every case.
- dumps/ULUS10566-test317-hprowbound.iso = cp --reflink of test314 (pre-desc copy) + spot33_reflect.py --apply-code:
  sha256 215378adf765eafefb158bfd9e06f7a92485b0b64adc90665a94d185089eb5ce. Changed: TRI EBOOT range (helper +6 words,
  EE_HIT/EE_GUARD behind it move with their sites 0x08ae6ed4 / C2), cave. Re-run = no change. Not run in game.
