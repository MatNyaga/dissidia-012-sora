# EX Burst → KH2 Limit look (2026-10-14 night, research only, nothing built into an ISO)

Mat: "I want to use KH2's limit when Sora is alone where he hits the opponent and then you press triangle for break.
We can still use cloud's sequence for mashing circle but I need the look to be Kingdom Hearts and not FF7."

## Which KH2 limit
Sora's solo limits in KH2 Final Mix = the **Limit Form** moves. They live in their own animation set
`kh2_export/raw/kh2_sixth/original/obj/P_EX100_KH1F.mset` (+ effects `P_EX100_KH1F.a.us`). Each is a multi-hit run
that you keep going with △, and it ends in a finisher:
| KH2 limit | animations (mset index, frames @30 fps) | what it looks like |
|---|---|---|
| **Sonic Rave** | 844 K400 (14, start: Keyblade raised high, then crouch), 848 K401 (27, dash lunge strike), 852 K402 (41, long dash + strike) | dashes straight through the foe again and again |
| **Ars Arcanum** | 884 K410 (85, long opening flurry of big swings), 888-904 K411-K415 (30/30/30/30/30/46, one swing each, back to stance), 908 K416 (40, finisher: jump-up slash, then slam into a low stance) | a fast multi-hit sword flurry with a jumping finisher |
| **Strike Raid** | 924 K420 (15, wind-up), 928 K421 / 932 K422 (41/58, throw the Keyblade + catch), 936 K423 (72, arm out, waiting for the Keyblade) | Keyblade thrown again and again |
| **Ragnarok** | 964-980 K430-K434 (9/7/8/6/8, quick hits), 984 K435 (93, hang in the air pointing the Keyblade: beam volley), 988 K436 / 992 K437 (33, air raise/flip + point = final beam) | air combo, then light beams shot from the Keyblade tip |
(Also in this set: Limit Form copies of combo swings 616 K303, 620 K304, 692 K322, 732 K332, and 215 A121.)
Contact sheets (12 frames each, Sora's own model): `dumps/renders/kh2limit/<IDX>_<NAME>.png` (+ `.gif`).
Mat's ability video has no limit chapters, so the names above come from the animations + KH2 knowledge. ❓ Mat to confirm.

**Recommendation: Ars Arcanum.** It is all close-range Keyblade hits, so it fits Omnislash's "hit, hit, hit" shots best.
Its single-swing clips K411-K415 map 1:1 onto Cloud's single-slash shots, K410 is a ready-made multi-hit flurry, and
K416 is a clear finisher. The in-battle burst name is already "Ars Arcanum" (spot33_battlenames.py). Sonic Rave's
dash (K401) replaces Cloud's dash shots.

## Cloud's Omnislash shots → proposed KH2 clips
Motion ids / phases from notes/gmo-format.md "EX Burst". Hits = Cloud's script frames (60 Hz), as in today's BURST.
| slot | phase (Cloud) | today (P_EX100) | proposed (Limit Form) |
|---|---|---|---|
| _801A | opening, 2 hits (14, 55) | 644+664 | **k884/0-45** Ars Arcanum opening swings |
| _801B | "Rapidly tap ◯" power-up, no hit | 210 Drive Form pose | **k844** Limit ready: Keyblade raised high |
| _802A / _803A | dashes, no hit | 814 / 822 glide poses | **k848** Sonic Rave dash lunge (both) |
| _803B-_807A | single slashes (hit 23) | 724/728/732/736/768 | **k888, k892, k896, k900, k904** (one Ars Arcanum swing each) |
| _812B | 9-hit flurry (path 1 end) | ground combo ×2 | **k884** whole Ars Arcanum flurry, 9 hits |
| _812A | final blow (path 2 end, hit 123) | 776 | **k908** Ars Arcanum finisher (the "△ break" look) |
| _812C | other finish (hits 104, 119) | 788 | **k908** |
| _813A | end | 22 | keep 22 (landing) |

Proposed line for build_sora.sh (replaces BURST=; nothing else needed, see "Tooling"):
```
BURST="_801A=burst:k884/0-45:14,55 _801B=burst:k844:- _802A=burst:k848:- _803A=burst:k848:- _803B=burst:k888:23 _804A=burst:k892:23 _805A=burst:k896:23 _806A=burst:k900:23 _807A=burst:k904:23 _812A=burst:k908:123 _812B=burst:k884:7,27,50,67,81,95,109,121,133 _812C=burst:k908:104,119 _813A=burst:22:-"
```
Dry run on a scratch copy of `dumps/models/sora_natural.gmo` (Cloud's shots still in the slots, like in a real build),
FOLLOW=1 MATCH=1 exactly like the build: every slot converted (e.g. `_803B <- combo: 21 frames`, `_812A … 91 frames`).
Preview of all shots: **`dumps/renders/kh2limit/burst_proposal.png`** (8 frames per slot; frames in
`dumps/renders/kh2limit/burst_frames/`). Not checked in game yet.
Watch out: the slash shots are 21 frames (0.7 s), so the 30-frame KH2 swings play ~1.4× faster — fine for a burst,
but say so if it looks rushed (then trim with `k888/0-24`).

## The △ "break"
Cloud's burst code only reads ◯ mashing; the shots that follow are picked by the game. Real △ input = new game code
(later, like the parry). For now the "break" is the LOOK: the burst ends in Ars Arcanum's finisher (K416) and the game
already shows the "LIMIT BREAK" banner. Optional later: change the "Rapidly tap ◯!" text.

## Tooling
- `tools/scripts/kh2_combo.py` now takes `kNNN` clips = Limit Form (bakes into `dumps/kh2anim_kh1f/` from
  P_EX100_KH1F.mset with P_EX100.mdlx — both skeletons have 228 bones; separate folder because the indexes clash
  with P_EX100, e.g. 616 = A303 there, K303 here). Normal numbers work as before.
- `tools/scripts/kh2limit_sheets.sh IDX…` = contact sheets of Limit Form animations into dumps/renders/kh2limit/.
- Triggers: `MSET=$PWD/kh2_export/raw/kh2_sixth/original/obj/P_EX100_KH1F.mset python3 -I tools/scripts/kh2_triggers.py OUT.json 884 …`

## KH2 effects + sounds of these moves (for later, PAX `P_EX100_KH1F.a.us`, `kh2_pax_dump.py`)
Motion triggers (F type 1 = effect element id, type 2 = sound slot of the motion, R type 20/26 = attack id):
- Sonic Rave: K400 effect 40 (se 999054 → se999 subsong 51), K401 effects 26/27/28 (27: se 999005 → subsong 5),
  attack 698; K402 effects 29/30/31 (30: 999005).
- Ars Arcanum: K410 effect 41 (999054 → subsong 51), attack 701 throughout + 702 on the last hit; K411-K414 attack 702,
  K415 attack 703; K416 no attack id (finisher move, t28 = movement).
- Strike Raid: K420 effect 42 (999054); K421/K422 throw spawn (t9); K423 effect 33 (999051 → subsong 48), attack 704.
- Ragnarok: K430 effect 43 (999054); K435 attacks 684/685/686 (beam volley 42-100); K436 effect 21 (999046 → subsong
  43), K437 effect 22 (999047 → subsong 44) = final beam.
- SE id → file: `tools/scripts/kh2_se.py id 999054` (subsong = audio index + 1; WAVs in dumps/renders/kh2sounds/).
  Note: by this tool, Explosion's 999038 = se999_036 and 999042 = se999_040 (not _038/_042 as guessed in
  HANDOFF); Mat liked _038/_042 by ear, so keep them unless they want the "real" ones.

## Open questions for Mat
1. Which limit: Ars Arcanum (recommended), Sonic Rave, Strike Raid or Ragnarok? (Can mix: e.g. Sonic Rave dashes + Ars
   Arcanum swings, as proposed.)
2. OK that the △ "break" is only the look for now (real △ input = game code, later)?
3. Effects/sounds: port the KH2 Limit effects (light trails, flashes) with the effects helper's FEP tools next?
