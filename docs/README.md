# Docs index

Every document, grouped by who it is for. One line each: the question it answers.
Words you don't know are in the [glossary](learn/GLOSSARY.md). Status of every phase: **[ROADMAP.md](ROADMAP.md)**.

## Start here

| doc | answers |
|---|---|
| [../README.md](../README.md) | What is this project, what works today, where do I start? |
| [ROADMAP.md](ROADMAP.md) | Which phases exist, which are done, what comes next? |
| [modding/OVERVIEW.md](modding/OVERVIEW.md) | How do the disc, the engine module, the registry, packages and the installer fit together (one page)? |

## Players

| doc | answers |
|---|---|
| [RELEASE-POLICY.md](RELEASE-POLICY.md) | Which game copy works, where the new file goes, saves and friend cards, updates, uninstalling, platforms. |
| [TEST-ON-VITA.md](TEST-ON-VITA.md) | How do we test a disc on a PS Vita (PSP mode, Adrenaline), including the five-minute check? |

## Modders: learn how it works

| doc | answers |
|---|---|
| [GUIDE.md](GUIDE.md) | The short tour (written 2026-10-13/14): disc, fighter files, Sora's model, KH2 animations, voices, tests. |
| [learn/00-START-HERE.md](learn/00-START-HERE.md) | How to read the learning path; the whole project in one picture. |
| [learn/01-the-disc.md](learn/01-the-disc.md) | What is inside the ISO, PACKAGE.BIN, files found by hash, how to add a file. |
| [learn/02-a-fighter-and-slot-33.md](learn/02-a-fighter-and-slot-33.md) | What files make a fighter, what an owner number is, how slot #33 became Sora's. |
| [learn/03-model-skeleton-animation.md](learn/03-model-skeleton-animation.md) | How models, bones and motions work, and how KH2 animations were brought over. |
| [learn/04-moves-and-combos.md](learn/04-moves-and-combos.md) | How a move is built: actions, pieces, scripts, hitboxes, hits, magic, EX Burst. |
| [learn/05-sounds-and-voices.md](learn/05-sounds-and-voices.md) | Sound banks, sound ids, voice lines, subtitles. |
| [learn/06-visual-effects.md](learn/06-visual-effects.md) | Effect packages, effect rows, textures, and the rules that prevent freezes. |
| [learn/07-game-code.md](learn/07-game-code.md) | EBOOT, overlays, Ghidra, code caves, hooks, Reflect, and the Phase 2 engine code. |
| [learn/08-menus-and-abilities.md](learn/08-menus-and-abilities.md) | Customization, text tables, banners, grid pictures. |
| [learn/09-testing.md](learn/09-testing.md) | PPSSPP, the remote debugger, breakpoints, recordings (the early test method). |
| [learn/10-build-pipeline.md](learn/10-build-pipeline.md) | The Sora build script, then packages, the installer and the release. |
| [learn/11-working-with-codex.md](learn/11-working-with-codex.md) | How the two AI helpers share work. |
| [learn/12-lessons-learned.md](learn/12-lessons-learned.md) | Every big break up to 2026-10-16, why it happened, the rule now. |
| [learn/13-open-questions.md](learn/13-open-questions.md) | What was still unknown on 2026-10-16. |
| [learn/14-dlc-and-more-fighters.md](learn/14-dlc-and-more-fighters.md) | Why more fighters need an engine, and what Phases 0-2 built. |
| [learn/15-engine-and-registry.md](learn/15-engine-and-registry.md) | How the engine replaces "owner 33" checks, with a worked example (EX run speed). |
| [learn/GLOSSARY.md](learn/GLOSSARY.md) | Every term, A-Z, plus the Phase 2 engine and package terms. |

## Modders: make a fighter, test, contribute

| doc | answers |
|---|---|
| [modding/MAKE-A-FIGHTER.md](modding/MAKE-A-FIGHTER.md) | What does a fighter package need today, step by step, and what are the limits for fighter #2? |
| [modding/TESTING.md](modding/TESTING.md) | How is a change checked? From the checks that need no game files to the PS Vita. |
| [modding/CONTRIBUTING.md](modding/CONTRIBUTING.md) | Sharing rules, what never goes in a patch, naming, reporting a finding, credits. |

## Modders: reference

| doc | answers |
|---|---|
| [ENGINE.md](ENGINE.md) | The engine in detail: EXTRA.PRX, EXTRA.IDX, EXTRA.REG, the stub table, every as-built step. |
| [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) | The package folder: manifest, files, rows, patches, allocations; v1.1 identity keys. |
| [PACKAGE-ACCEPTANCE.md](PACKAGE-ACCEPTANCE.md) | The checklist every package and release candidate must pass (static, emulator, Vita, installer). |
| [INSTALLER-TECH.md](INSTALLER-TECH.md) | How the patch app works inside (Tauri, VCDIFF, EBOOT decrypt, CI). |
| [INSTALLER-UX.md](INSTALLER-UX.md) | The patch app's screens and texts. |
| [../notes/dlc.md](../notes/dlc.md) | The DLC research, the new-fighter table, and §F: lessons every new fighter must respect. |
| [../notes/phase2/](../notes/phase2/) | One note per Phase 2 step: what was built, the disc, the checks, the open questions. |
| [../notes/README.md](../notes/README.md) | Research notes by topic (models: `gmo-format.md`; battle file: `character-file.md`; sound: `voice-and-sound.md`; slot 33: `roster.md`; effects: `kh2-effects.md`; disc layout: `package-format.md`). |

## Building from source

| doc | answers |
|---|---|
| [SETUP.md](SETUP.md) | What do I need to rebuild the mod, and how does the full build run? |
| [ASSETS.md](ASSETS.md) | What never goes in Git, and how do I get my own local inputs? |
| [REPRODUCIBILITY.md](REPRODUCIBILITY.md) | Every outside input, what is still missing, and which Phase 2 tools are not published yet. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | The short technical tour and the folder map. |
| [AUDIO.md](AUDIO.md) | How the voice and sound inputs are prepared. |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common problems when playing or building. |

## Phase 2 working docs

| doc | answers |
|---|---|
| [PHASE2-START.md](PHASE2-START.md) | For helpers: the Phase 2 oracle, decisions, address map, tools, traps. |
| [PHASE2-PLAN.md](PHASE2-PLAN.md) | The Phase 2 task plan (P2.0-P2.13) and its status table. |

## History

| doc | answers |
|---|---|
| [history/ORIGINAL-PLAN.md](history/ORIGINAL-PLAN.md) | The first stage plan (2026-10-11): change a move → new move → new slot → Sora. |

The project's internal work log, the Phase 0/1 plans and the day-by-day summaries stay in the private working
project; their results are in the [roadmap](ROADMAP.md), [notes/dlc.md](../notes/dlc.md) and the learning path.
