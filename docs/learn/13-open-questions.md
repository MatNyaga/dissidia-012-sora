# Chapter 13 — Open questions and what's next

What we **don't** know yet, and what's still to build. Status as of 2026-10-16 evening
(from the project's work log, morning summary and Codex task list, which are private working files).
For the newest state see the roadmap below.

> Status of every phase and task today: [ROADMAP.md](../ROADMAP.md). Many items below were done later (for example
> "more fighters as packages" became Phases 0-2, Chapter 14).

---

## 13.1 Still to build (updated 2026-10-16 evening)

| item | state | what's needed |
|---|---|---|
| Reflect sends damage back | ✅ done (Bravery + HP attacks, test271) | — |
| Reflect look (KH2 Reflega barrier) | ✅ built; 🧪 upright dome over Sora (test292) | Mat to judge the upright version |
| Trinity Limit EX Burst | ✅ done (2 s solo wind-up, voice, louder finisher, "TRINITY LIMIT") | — |
| CPU AI for Sora | ✅ aggressive (v3, test294); Thunder spam fixed in Thundaga v2 | faster reactions / EX activation need code |
| Magnet Burst look | 🧪 visible (test290); rings overlap | Mat: "leave it for now" |
| Thundaga | 🧪 v2: warning, locked spot, 3 bolts, end lag (test296) | Mat to test damage + dodge |
| EX Mode Bravery damage | 🧪 ×1.5 extra (test295) | Mat to feel |
| Sora as assist | 🧪 built (test279); gauge does not fill | fix in progress (test303) |
| Menus / Museum / Icons / Records | ✅ menus + Museum; 🧪 portrait, icon 414, Records (test302) | Mat to check |
| voice lines from every fighter meeting Sora | tooling ready (`!LINE`) | Mat will send the lines |
| title voice in Sora's voice | not started (title call is chosen by the PSP date) | Mat to help generate |
| 2P/3P outfits | copies of 1P (EX banner/aura fixed) | own colour variants |
| real PSP hardware test | not done | custom firmware + the plain EBOOT |
| final release | full build verified (test288) | fresh full build → `make_release.sh` |

---

## 13.2 Questions waiting for Mat

1. Air finishers (Magnet Burst, Horizontal Slash, Aerial Sweep, Retaliating Slash) only work in
   **air-started** combos. Allow them in the air part of the ground combo too? (Needs more chain
   rows = more CP and menu rows.)
2. Block voice "Defense!" also plays when R is pressed a moment before △ (dash). Keep, or a
   short grunt?
3. Slide Dash "hard to land": vs Average CPU it hits 8/8 from 8 m but 2/3 from 4 m. Does it not
   *come out*, or does the foe dodge?
4. Win/loss cameras are still aimed at Cloud's height. Scale them like the intro camera?
5. Is the Explosion sound pick right (by ear `se999_038`, by the tool `se999_036`)?
6. Reflect strength: full, half, Bravery only? (Mat said full; revisit once damage return works.)
7. Codex Q-20261015-CODEX-002: the exact frame the burst exit (`_813A`) starts, for a seamless
   Trinity ending — needs a runtime trace when approved.

---

## 13.3 Things we don't understand yet

| unknown | why it matters | notes |
|---|---|---|
| exact model memory limit (somewhere 2,506,640–2,517,912 B) | every animation added costs memory | `notes/gmo-format.md` |
| exact effect memory budget | we only know "must not grow" | `notes/kh2-effects.md` |
| run speed / jump height | Sora's movement feel | not in chrp/chrl/animation speed; probably action-state code (`notes/adjustables.md`) |
| PACKAGE_INFO 4-bit flag | harmless so far | `notes/package-format.md` |
| many atkp fields (+0x14..+0x17, +0x16 "15/50/100") | finer hit feel | test: 30 made escapes worse |
| emitter fields (particle count, life, speed) | KH2 orb count (5–6) | values 5/6 seen, undecoded |
| keyframe tracks in effect nodes | retiming effects | not decoded |
| whether a deflected projectile can home on the caster | Reflect | needs a runtime test |
| a 10th hit in the burst flurry | Trinity has 10 cues, Cloud's flurry 9 hits | structurally possible, untested |
| which code picks a second skin in EX Mode | form change | Terra's `model-0-0000` lead |
| `p_se` type 9 "hibg", `brat` chunk | unknown | not needed so far |
| CPU-side setup-screen banner row for #33 | only when #33 is the CPU | `notes/qb-grid-pictures.md` |
| how hit-spark effects are chosen per hit | a "free" leaf could still be used | table not found on disc |

---

## 13.4 Bigger projects for later

- **More fighters as packages** (2026-10-18): research done (`notes/dlc.md`, Chapter 14); **Phase 0 probes started**
  (`docs/PHASE0-DLC-PLAN.md`: toolchain, own code module, free RAM, owner 34, grid, plain DLC, extra file index, registry).


- **PAX → FEP converter** (KH2 effects as real particle effects, not repaints): weeks of work;
  a hand-made Explosion with the FEP writer would be ~1–2 weeks.
- **Bone physics for the keychain**: hang it on engine-simulated bones like Cloud's coat tails
  (`p_se` type 6) for a real in-game swing.
- **More fighters**: owners 34 and maybe 23 are free. The recipe is this whole document — and
  the rule from Chapter 2: own effect id, own sound ids, own texture keys, own outfit files.

---

## 13.5 Where to look

- [ROADMAP.md](../ROADMAP.md) — the status of every phase and task today.
- In the private working project: `HANDOFF.md` §4 and the bottom (the live to-do list), `docs/MORNING-2026-10-15.md`
  (Mat's checklist), `codex/TASKS.md` and `codex/QUESTIONS.md` (Codex's jobs and open questions).

Back to [00 — Start here](00-START-HERE.md) · [Glossary](GLOSSARY.md)
