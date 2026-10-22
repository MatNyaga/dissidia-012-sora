# Learning docs — start here

These pages explain **everything we've learned so far** about Dissidia 012 duodecim
(PSP, US disc `ULUS10566`), how the game works inside, and how the Sora mod is built. They were
written first for Mat (the project's owner) and are now also meant for other modders.

They are the long, teaching version. `docs/GUIDE.md` is the short tour; these docs build on it
and go deeper. The exact byte layouts and every test log stay in `notes/`. The current state is
on the [README](../../README.md) and the [roadmap](../ROADMAP.md). For the Phase 2 engine and making a fighter,
there is a short modding layer: [modding/OVERVIEW.md](../modding/OVERVIEW.md).

> **Files named but not published.** The chapters mention some of the project's own working files: the running work
> log `HANDOFF.md`, the `codex/` folder (how the two AI helpers share work), `docs/CURRENT-BUILD.md`, the morning
> summaries, the Phase 0/1 plans and their notes (`notes/dlc-phase0.md`, `notes/dlc-phase1.md`), the decompiled
> listings and test discs under `dumps/`. Those are private working files, not in this repository; their findings
> are in these chapters, the [roadmap](../ROADMAP.md) and [notes/](../../notes/README.md). Tools that are not
> published yet: [list](../REPRODUCIBILITY.md#phase-2-tools-not-in-this-snapshot).

---

## How to read these

- Read the chapters **in order** the first time. Each one uses words from the ones before.
- Every chapter starts with **"The big idea"** in a few lines. If that's all you need, stop there.
- New words are explained the first time they appear. All of them are also in the
  **[Glossary](GLOSSARY.md)**.
- File paths and commands are exact. You can copy them.
- Each chapter ends with **"Where to look"**: the notes and tools behind it.

### How sure are we? (the tags)

| tag | means |
|---|---|
| **[PROVEN]** | seen working in the game (logged by a tool, on screen, or Mat said so) |
| **[BUILT]** / **[BUILT, not seen]** | made and checked in the files, not yet seen in the game |
| **[GUESS]** | an educated guess from the code or data; may be wrong |
| **[UNKNOWN]** / **[OPEN]** | we don't know yet / still to do |

### How numbers are written

Numbers starting with `0x` are **hex** (base 16): `0x10` = 16, `0x800` = 2048. `+0x10` means
"16 bytes from the start". Chapter 1 explains this gently.

---

## The whole project in one picture

How Sora was first built (chapters 1-13), and how a fighter is installed now (chapters 10 and 14):

```
 Mat's KH2 (PC)                     Mat's Dissidia 012 disc
 kh2_export/                        dumps/ULUS10566.iso  (never written)
   Sora model, Keyblades,                  │
   animations, effects,                    │  tools/scripts/bootstrap_base.sh  (slot #33 setup)
   voices, sounds                          ▼
        │                           base disc
        └──────────► tools/scripts/build_sora.sh  (≈ 45 steps, ≈ 19 min)
                                           │
                                           ▼
                            reference disc (layout R)
                                           │  tools/pkg/extract.py: reference − clean disc
                                           ▼
                            packages/sora  (a fighter package)
                                           │  tools/pkg/install.py: clean disc + packages
                                           ▼
                            installed disc (release 1.0 = layout B)
                                           │  tools/pkg/make_release.py
                                           ▼
                   patch.vcdiff + release.json → the patch app players use
                   (only our changes; never game files)
```

Phase 2 replaces Sora's owner-33 code with a generic engine, so the same installer can add more
fighters as packages (layout C). Picture: [modding/OVERVIEW.md](../modding/OVERVIEW.md).

---

## The chapters

| # | chapter | what you'll learn |
|---|---|---|
| 01 | [The disc and its files](01-the-disc.md) | ISO, PACKAGE.BIN, files found by hash, boxes inside boxes, adding files |
| 02 | [A fighter's files and slot #33](02-a-fighter-and-slot-33.md) | owners and code names, the battle file's chunks, how #33 became Sora's own slot |
| 03 | [Model, skeleton, animations](03-model-skeleton-animation.md) | GMO, bones, motions, keyframes, KH2 animations, the keychain, the memory budget |
| 04 | [Moves and combos](04-moves-and-combos.md) | actions, pieces, scripts, hitboxes, hits, knockback, variants, magic, EX Burst |
| 05 | [Sounds and voices](05-sounds-and-voices.md) | sound banks, slots, ids and bases, effect sounds, voice lines, subtitles, memory |
| 06 | [Visual effects](06-visual-effects.md) | FEP leaves, FEPA rows, textures, anchors, the size rule, the freezes |
| 07 | [Game code](07-game-code.md) | EBOOT, overlays, Ghidra, code caves, hooks, Reflect |
| 08 | [Menus, names, pictures, abilities](08-menus-and-abilities.md) | Customization, text tables, banners, grid pictures |
| 09 | [How we test](09-testing.md) | PPSSPP, the remote debugger, breakpoints, reading memory, recording |
| 10 | [The build and the release](10-build-pipeline.md) | `build_sora.sh` step by step, then packages, the installer and the release patch |
| 11 | [Working with Codex](11-working-with-codex.md) | how the two AI helpers share work |
| 12 | [Lessons learned](12-lessons-learned.md) | every big break, why it happened, the rule now |
| 13 | [Open questions and next steps](13-open-questions.md) | what we didn't know on 2026-10-16 (status now: [ROADMAP](../ROADMAP.md)) |
| 14 | [DLC and adding more fighters](14-dlc-and-more-fighters.md) | why more fighters need an engine; what Phases 0-2 built |
| 15 | [The engine and the registry](15-engine-and-registry.md) | how the engine replaces "owner 33" checks: per-owner tables, REG_ROW, stubs, saves, packages |
| — | [Glossary](GLOSSARY.md) | every term in one or two sentences, plus the Phase 2 terms |

After chapters 14 and 15, the **modding layer** is short and practical:
[OVERVIEW](../modding/OVERVIEW.md) (the architecture on one page),
[MAKE-A-FIGHTER](../modding/MAKE-A-FIGHTER.md), [TESTING](../modding/TESTING.md),
[CONTRIBUTING](../modding/CONTRIBUTING.md).

**Short on time?** Read 00, then [12 — Lessons learned](12-lessons-learned.md). It's the most
valuable part.

---

## The project's rules (from the project's work log)

1. **Goal:** Sora as a full fighter: own model, moves, voice, sounds, EX Mode,
   EX Burst, a parry/Reflect — built from KH2, with Cloud's pieces only as templates.
   Then: an engine so more fighters can be added as packages.
2. **Release = a patch only** (a VCDIFF delta since release 1.0; xdelta in the early tests).
   Never share discs or game files.
3. **Every change is a real disc change** (no cheat codes).
4. **The clean dump `dumps/ULUS10566.iso` is never written.** Every test is a copy.
5. Write findings into `notes/` and the work log right away.

---

## Where things are right now (2026-10-22)

- **Release 1.0 is out** (2026-10-20). Phase 2, the fighter engine, is under way:
  [README](../../README.md) (status) and [ROADMAP](../ROADMAP.md) (every phase).
- These chapters were written from the notes as they were on 2026-10-15. Chapters 07, 10 and 14
  were brought up to date on 2026-10-22 (Phase 1 and 2). If a note and these docs disagree,
  **the note wins**: it is updated more often.
- Newest discs and results: the phase notes in [notes/phase2/](../../notes/phase2/).
  (The private work log and `docs/CURRENT-BUILD.md` list every disc; they are not published.)

Start with [Chapter 1 — The disc and its files](01-the-disc.md).
