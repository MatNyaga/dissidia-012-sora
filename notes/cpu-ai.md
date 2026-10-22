# CPU AI (enemy Sora) — how the game's AI works, why CPU Sora was passive, the fix

Started 2026-10-16 by Claude (CPU AI helper). Static research only (decomp `dumps/decomp/all.c`, data from
`dumps/ULUS10566-test275-solo2s.iso` and the clean dump). Nothing here run in game yet.

## 1. Where the AI data lives
| data | where | per who |
|---|---|---|
| **brai "seco"** (52,944 B, v4.36) | `battle_non_residing.bin` (pkg 9651) ARC chunk `brai` type 1 | GLOBAL (all fighters) |
| brai "atta" (32 small attack tables) | same file, `brai` type 3 | global, other use (loaded by FUN_0885af78) |
| **brat "atta"** = the fighter's AI attack table | fighter objx chunk `brat` (Cloud 636 B) | per fighter |
| objentry +2 (u16) = id of the brat table to use | main.bin objentry.bin | per model row |

Loader: FUN_0881391c reads tag `brai` (type 1) → FUN_08a801b4 → FUN_08aabd38 → parser FUN_08aad8f8.
The seco file = "seco", f32 4.36, then 58 tables, each `u32 count + count × fixed-size rows` (order and row sizes:
`FIELDS` in the helper; table data is used IN PLACE, so every table must stay 4-byte aligned).

## 2. How the AI picks an attack (FUN_08a7c1dc)
- Walks every **comb** entry of the fighter. A comb entry is a candidate only if:
  equipped (comb bit set from the loadout), its first piece passes ground/air + Bravery/HP + kind filters,
  the action sits in one of the 12 equip slots (FUN_08a652f4), the foe is in its distance/height window
  (plya +0x24/+0x28 distance, +0x2c/+0x30 height of the first real piece), and **its action id is in the brat table**.
- Weight = brat weight byte for (action, situation, level) → mapped through seco table 0x15c:
  `0→0.2, 1→0.4, 2→0.7, 3→0.0 (never), 4→0.01, 8→0.04, 9→0.44, 10→1.04, 11→1.0, 12→2.0, 13→3.5, 14→1.0,
  15→2.0, 16→3.5`. Plus a range bonus (in range: +0.4, +0.2 more if height + air/ground also fit). Roulette pick.
- **brat format**: "atta", f32 1.02, u32 1, u32 id (= objentry +2; Cloud/Sora 6), u32 N, N × 28 B
  (u32 action id, 6 × (u16 offset, u16 count) = one weight list per situation), u32 M, M weight bytes.
  Weight used = list[min(level, count-1)]; Cloud has count 1 everywhere (same weights at every strength).
- **Situation** 0..5 (FUN_08a7b5e0): from Bravery/HP comparisons of both fighters through the brain set's
  profile grids (seco tables 0x30/0x3c/0x48/0x54/0x90/0x9c/0xa0): 0/1/2 = HP-state rows, 3/4 = Bravery-state rows,
  5 = set by special callers (chases etc.). Cloud's tables favour HP attacks in 2 and 4.
- **Level** 0..3 = personality +0x130 (seco table 0x150, 16 personalities): ids 8-11 → 0 (strongest), 6-7 → 1,
  4-5 → 2, others → 3. Personality chain (+4 = next weaker) is walked down "steps" times when the CPU is doing
  well (brain set rows in seco 0x24, byte +5) = built-in rubber band.
- Executor: FUN_08a66d7c → FUN_08a66f8c: in range → FUN_08a672f4 attack, else approach/back off. Commands go
  into a queue (FUN_08a65b50, 43 command ids at 0x08a7ac4c).

## 3. Why CPU Sora was passive (2 reasons)
1. **Owner 33 has no row in the seco owner table** (0x1a8 = 32 owners 1..32; 0x1c0 = 32 × 40 matrix that maps
   the battle-setup "brain x" (side struct +0xf36) to a brain set id). FUN_08aacc28 returns x UNCHANGED for an
   unknown owner → Sora gets brain set 0..28, but brain sets only exist from 29 up (seco 0x18). → FUN_08aad3f0
   fails → situation = −2 → FUN_08a7c1dc rejects the query (situation must be 0..5) → **the main attack picker
   never picks anything for owner 33**. Only side paths (fixed-situation callers, reactions) still fire. Every
   other owner 1..32 (Cloud too) has the same standard row (x 0..7 → brain sets 29..36).
2. **Sora's brat is Cloud's** (identical bytes): actions 313-328 + 927/928 only, with Cloud's weights. Sora's main
   ground combo **1020** (Combo Plus, ablt 0x2100) and all HP magic **1021-1026** are not in it → never chosen
   even after fix 1. Several ids now mean different moves (327 = Dodge Slash, Bravery; Cloud's 327 was an HP move).

3. (found later) **owner 33 has no `acab` row** (system.bin). acab = per-owner list for the CPU auto-equip:
   ids with flag 0x10000000 are ALWAYS equipped (Ground/Midair Evasion, Ground/Midair Block, Aerial Recovery,
   Multi Air Slide, EX Core / Assist Lock On, Evasion Boosts, Air Dash, Free Air Dash), ids without the flag are
   never equipped by the CPU (Auto Chase, Auto EX Burst …, gear abilities). No row → CPU Sora's general abilities
   were a random pick inside his CP budget (he could miss Block / Evasion / Air Dash).

## 4. How a Quick Battle CPU is set up (static, EBOOT)
- FUN_088fa2ac → FUN_088b3b98(record, owner, level, strength row …): builds an AUTO record, not your save.
  - `acco` (system.bin, 53 rows × 20 B): CPU strength row → personality = random in [+0, +4]. Row 0 = 10 (strongest),
    row 8 = 0. Personality → brat level (+0x130) and many skill floats (392-byte record, global).
  - **AI style** 0..7 = random unless set (= battle "brain x", side struct +0xf36) → brain sets 29..36 for normal
    owners (profiles 5,4,4,4,4,5,7,6). Styles also switch mid-battle (seco 0x2a4 group [29..36], FUN_08aabe2c).
  - Learned list = default eqpm preset + every chrl level up to the CPU level (so a high-level CPU Sora knows all
    his moves). Equip = FUN_088b5254 / FUN_088b5670: acab "always" list first, then by **ablt +32..39 priority**
    (byte = row +0x20 + style), highest first, random among equal, inside the CP budget.
- acit (items) uses an owner bit mask `1 << (owner & 31)` → owner 33 shares owner 1's (WoL) gear presets. Left as is.
- Slots: 0-2 ground Bravery (neutral/toward/away), 3-5 air Bravery, 6-8 ground HP, 9-11 air HP. The AI "uses" an
  action by pressing its slot (FUN_08a6b65c: Circle for 0-5, Square for 6-11). A chain (Brv→HP link) resolves to its
  parent's Circle slot; the HP finisher fires when the in-combo command (FUN_08a75d38) picks an HP action in range
  and presses Square at a branch. So wide-range HP moves (magic 0-25 m) also make Square presses mid-combo likely.

## 5. What spot33_ai.py writes (test276-ai)
- `obj/p_sev120.objx` brat: Sora's own table, 23 actions (1020, 316, 327, 321, 324, 325, chains 314 315 317 313
  320 927 318 319 323, HP 326 1021-1023 328 1024-1026), 4 strength levels per situation. Max/Strong: Combo Plus,
  Air Combo, Combo Plus > Guard Break = 3.5; the rest 2.0 (1.0 for Blizzaga / weaker chains); HP-favoured
  situations 2 and 4 raise Explosion / Aerial Finish / Guard Break / Magnet Burst chains to 3.5. Minimal: flat.
  322 (Cloud air leftover) and 928 (no Sora ablt row) left out. 1,220 B (Cloud's was 636 B).
- `battle_non_residing.bin` brai seco: owners += [33, −1 pad]; matrix += 2 copies of owner 13's row. +164 B in the
  chunk, +176 B file (later chunks keep their 16-byte phase). Other chunks byte-identical.
- system.bin: acab + (33 → owner 13's list, shared data, +8 B); ablt owner-33 rows +32..39 = priority 3 (core
  moves, Explosion, Firaga, Thundaga, Aerial Finish, A. Thundaga, Guard Break chains, Magnet Burst, DS > Explosion),
  2 (Aerial Spiral/Dive, Upper Slash chains, Horizontal Slash, A. Firaga), 1 (Blizzagas, Aerial Sweep, Retaliating).
- Not changed (on purpose): personalities, styles, rubber band (brain set 0x24 rows, key 4 → 1 step weaker),
  any code. Next option if Sora still feels soft at Max: own brain sets for owner 33 (copies of 29..36 with the
  key-4 step removed; needs rows in seco 0x18 / 0x24 / 0xf0 / 0xfc and a 0x2a4 group).

## 6. Runtime checklist (test276-ai; not run yet — the main session owns the emulator)
Quick Battle, Order's Sanctuary, Mat = any fighter (Cloud or Lightning), opponent = CPU Sora. Run CPU strength
**max** first, then **Minimal** for comparison (restarts reset the settings: set both explicitly).
1. Battle starts, no freeze; CPU Sora walks/dashes TO you within a few seconds (before: mostly stood/blocked).
2. He starts combos on his own: Combo Plus (◯ close), Slide Dash from mid range (5-11 m), Dodge Slash, Air Combo,
   Aerial Spiral (you above him) / Aerial Dive (you below). Do the long chains continue past 3-4 hits?
3. HP moves: Explosion, Firaga / Thundaga / Blizzaga (also from far away), Aerial Finish; Guard Break /
   Upper Slash / Magnet Burst at the end of combos (Square branch).
4. Defence: he blocks (in EX Mode = Reflect barrier) and dodges; air dashes after you; recovers in the air.
5. EX Mode when his gauge fills; Trinity Limit EX Burst plays through, no hang; KO + rematch OK.
6. Minimal: clearly weaker but still uses his moves (not frozen).
7. Optional debug check (only if 1-2 fail): fighter AI controller +0x20 (chosen action id) should change to Sora
   ids (1020, 316, 321 …); brain set = 29..36 (FUN_08aae300 return).
If CPU AI breaks for EVERY fighter (not only Sora): suspect the battle_non_residing.bin growth (+176 B) → rebuild
test276 without part B and report.
- **Mat on test276 (2026-10-16T14:18:28Z): "the cpu ai is good", no freeze. Issue: CPU casts Fire (close-range spell) from far away often (exploitable).**

## 7. v2 (test282-ai2, 2026-10-16) — Mat on test276: "the cpu ai is good", no freeze; but CPU Fire from far away
Cause: the AI only casts when the foe is inside the move's plya window (+0x24 min, +0x28 max, +0x2c/+0x30 height),
else it walks in / backs off first; the HP starters still had Cloud's windows (spells = Meteorain rows 0-25 m,
Explosion 4-7 m, Aerial Finish 5-8 m). Fire is a flame flurry around Sora (body sphere r 2.5), so 0-25 = free punish.
The player never uses these windows (flag 0x2 = skip distance check) → CPU-only change.
New windows (spot33_ai.py part D, `REACH`): Firaga / Aerial Firaga 0-2.5 m, Explosion 0-3 m, Aerial Finish 0-6 m,
Blizzaga 0-12 m, Thundaga 0-20 m (bolts at the foe). Magnet / Guard Break / Upper Slash chains use their first combo
piece (0-6 / 0-4.5 m) and only fire mid-combo, so they already fit. brat: Firaga weights 2.0 → 1.0 (close only).
Far away the CPU now rolls moves that reach (Slide Dash 5-11 m, Thundaga) or walks in for the rest.
Runtime check: Fire only point blank; Explosion / Aerial Finish land instead of whiffing at 4-8 m; Thundaga at range.
- Mat (2026-10-16T17:02:37Z): "cpu ai is hard, can we make him even harder though?"

## 8. v3 (test291-aihard = test289 + spot33_ai.py v3) — Mat on v2: "cpu ai is hard, can we make him even harder"
What the brain-set bytes mean (decoded now): seco 0x24 row (one per fight state 0..6) = key, **+1 HP-decision row**
(seco 0xb4: go for HP once Bravery ≥ lerp(lo, hi) × base Bravery; row 0 = 0×, 1 = 0.4-0.7×, 2 = 1.0-1.3×, 3 = 1.95-2.25×,
4 = 2.75-3.05×, 5 = 3.5-3.8×, 6 = never; FUN_08aaf138 → FUN_08aaef94), +2 spacing/EX row (0xc0; +0x14 = in EX Mode
go HP once the EX gauge ≤ x), +3 reaction-gate row (0xcc), +4 style pair (0xd8), **+5 "ease off" steps** (personality
walks that many links down its chain, e.g. Max 10 → 9, which has misses/slower reactions again).
- Personality 10 (Max) is already the top: every miss / delay rate 0 there. Raising guard/dodge/punish rates above
  Max for owner 33 only would need code (personality is picked from the battle setup, not per owner) → not done.
- v3 = Sora's OWN brain sets 200..207 (copies of 29..36): +5 = 0 everywhere (never eases off), +1 capped at row 3
  (styles that hoarded Bravery to 3.5× or never went HP now cash in at ~2× base Bravery = a Bravery lead). Owner 33's
  matrix row maps x 0..7 → 200..207; style switching mid-fight stays inside his own group (seco 0x2a4/0x2b0). New
  0xf0 keys share the stock 0xfc rows. All appended at table ends; other owners byte-identical (guard: strip ours →
  sha256 == stock). brai +840 B (+848 file); battle_non_residing.bin moved to the ISO end by pkg_put.
- brat v3: long chains first: Slide Dash (19-hit Sky Rave) 3.5; every combo > HP finisher chain 3.5 (Retaliating 2.0);
  Strong uses the Max weights. Reach windows from v2 kept.
- Not changed: B (spacing / EX) and C rows, EX Mode activation (not decoded), personalities.
Feel for: no "calm phase" when he is ahead; HP finishers (Guard Break, Upper Slash, Magnet Burst, Explosion) at the
end of combos once he leads in Bravery; same reach rules (Fire only point blank).

## 9. v4 (test331-aihard2 = test330 + spot33_ai.py v4, 2026-10-17) — Mat: "make Sora harder" (static, not played)
**EX Mode decision (decoded):** the fighter enters EX Mode (FUN_08b3526c → FUN_08acafac) when FUN_08b337a0 says the
gauge is full (+0x52c +0x18 ≥ 10000, not in EX, objentry +8 bit 2 clear) and the controller holds command bit
**0x12** (FUN_08b31f54). The AI sets 0x12 in FUN_08a9b0ac only if FUN_08aaf6a0 is true = the brain set's spacing/EX
row (seco 0xc0, 0x24 byte +2) mask +0x10: 1 = while attacking, 2 = FUN_08a83f80, 4 = foe farther than spec value,
8 = foe nearer than spec value, **0x10 = always**. Stock rows 4/16 have mask 4 (only when far), 13/14 mask 12.
→ So CPUs often sat on a full gauge until the distance was right.
**EX Burst:** = an HP attack landing during EX Mode. The HP decision in EX (FUN_08aaef94) = normal Bravery threshold
(v3 cap) OR EX gauge ≤ row +0x14 × 100 % (0.2-0.8 in the used rows). Row +0x14 is also read by FUN_08a9ebbc
(command 0x13/0x14, EX-flag 0x5b2&8 path; not decoded) → left unchanged on purpose.
**Reaction rows (seco 0xcc, 0x24 byte +3):** +4 / +0x10 = switches for two "slip-up" behaviours rolled with
personality +0x24 / +0x164 (weakest 1.0 / 0.8, Max 0 / 0.1): FUN_08a9ceb8 = drop the current combo before its last
piece, FUN_08a9d25c (vtable, unnamed). +8 / +0xc = choice chances in FUN_08a9a79c / 08a9a968 (not decoded, kept).
**v4 writes (owner 33 only, appended, other owners byte-identical, guard = strip ours → stock sha):**
- own spacing/EX rows 104 113 114 116 = copies of 4 13 14 16 with mask |= 0x10 → EX Mode the moment the gauge is full.
- own reaction rows 100-104 = copies of 0-4 with +4 = +0x10 = 0 → no combo drops / slip-ups at any strength
  (also makes Minimal Sora finish his combos).
- Sora's brain sets 200-207 point at them (byte +2 / +3 += 100). brai +196 B vs v3.
**Not done (and why):** magi AI threat tags + plya +0x60 tags decide how the CPU reads the OPPONENT's attacks →
they belong to the other fighters (owner-33-only rule). Faster guard/dodge/punish/decision timing above Max = code
(personality is per battle, not per owner); Max already has every miss/delay rate 0 except +0x164 (now gated off),
battle code room is exhausted → skipped.
**Runtime checks vs CPU Sora (Max, Order's Sanctuary):** (1) he enters EX Mode right when his gauge fills, at any
distance (before: often waited); (2) in EX he keeps attacking and goes for Trinity Limit (HP hit) as before, no hang;
(3) his long combos run to the finisher instead of stopping halfway (also on Minimal); (4) Fire only point blank,
Thunder at range, no freeze, other CPUs unchanged.
