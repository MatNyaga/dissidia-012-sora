# Chapter 11 — Working with two AI helpers (Claude and Codex)

**The big idea:** Mat runs two AI helpers on this project. **Claude** builds the discs, tests in
PPSSPP and owns the build. **Codex** (OpenAI's coding agent, "ChatGPT" in some notes) makes
assets — animations, sounds, research — offline. They don't talk to each other directly. They
share **files**: a start page, one question list, one inbox. The key rule is that Codex delivers
a **recipe** (a script that makes the change on any disc), not a finished disc file.

---

## 11.1 Who owns what

| who | owns |
|---|---|
| **Mat** | priorities, taste (looks, sounds), and every approval to run, install or change settings |
| **Claude** | `tools/scripts/`, `build_sora.sh`, `docs/CURRENT-BUILD.md`, building and testing discs |
| **Codex** | scoped offline deliveries in `codex/inbox/`: animations, audio picks, research |

Claude also starts its own helpers (sub-agents, e.g. "the effects helper") for big jobs. They
work in parallel; when one needs the game, it gets PPSSPP to itself.

An answer from one helper is **evidence, not permission**. Only Mat approves runtime tests,
installs or setting changes.

---

## 11.2 The one rule: deliver a re-runnable step, not a finished file

Claude rebuilds the whole disc from the base many times a day (Chapter 10). A finished
`.objx` or `.gmo` built on one day's disc goes **stale within hours**.

**Story:** Codex's Keyblade-audio packages review-v4 … v7 were all built on test201/202a, while
the real disc had moved on to test204. They couldn't be dropped in.

So a good delivery is a folder `codex/inbox/YYYYMMDD-topic/` with:
1. `README.md` — at most 10 lines: what it does, what Mat approved, which slots / motions /
   blocks it touches, the exact command, how to check it in game.
2. the assets (formats below),
3. optionally a `spot33_<topic>.py` written like Claude's steps: edits *whatever ISO it's given*,
   re-runnable, one line printed per change, works with both sound-id bases.

Claude then dry-runs it on the current disc, runs it on a copy → `testNN`, smoke-tests, asks
Mat to look/listen, adds the build line, updates `CURRENT-BUILD.md` and moves the folder to
`codex/done/`.

### Asset formats

| kind | format |
|---|---|
| sound effect | WAV 16-bit mono, 16 or 22.05 kHz, trimmed, peak ≤ −3 dBFS |
| voice line | WAV 16-bit mono 16 kHz |
| animation | a pose script for `pose_author.py`, or a GMO motion + its slot name |
| picture | PNG, same size as the one it replaces |
| code | an `--apply-code` style script with original-byte checks |

---

## 11.3 Shared resources: ask before using

Some things are shared and limited. Claude keeps this table current in `codex/START-HERE.md` §5:

| resource | state |
|---|---|
| Sora `snd_` slots | 0–95 used, **96** next free |
| Sora `snd_` bank size | keep ≤ ~540 KB (the Break-sound lesson) |
| voice bank slots | 0–44 used |
| new motion ids | up to 10317 used |
| battle overlay code cave | Reflect only, through `spot33_reflect.py`'s writer |
| effects chunk | **exactly 848,640 bytes**; no foreign effect trees |

To claim something ("I'm taking sound slots 96–99"), write it in `codex/QUESTIONS.md` first.

---

## 11.4 One question list

`codex/QUESTIONS.md` is the only place for questions between the two. Format and rules are in
`codex/COLLABORATION.md`:

- Each question has a permanent ID like `Q-20261015-CODEX-001`.
- States: `OPEN → ANSWERED → VERIFIED → CLOSED` (plus `NEEDS_FOLLOWUP`, `STALE`, `CANCELLED`).
  "Answered" is not "verified": the asker checks the answer against the real files.
- Times in UTC. Append; never rewrite someone else's entry.
- **Nothing wakes a helper up automatically.** Saving a question means "queued", not "read".
  Mat has to open the right session and paste the instruction (there's a ready-made paragraph
  in `COLLABORATION.md`).

Example: Q-20261015-CODEX-001 asked which hit frames the EX Burst endings must hit. Claude
answered from a dump of the scripts (flurry 9 hits at 4, 24, 48 … 130; final blow 120–126;
grand finish 92 and 116) and recommended "put your strikes on these frames, then no gameplay
data changes". Codex did exactly that for the timed Trinity endings.

---

## 11.5 What Codex has delivered (2026-10-15)

| delivery | state |
|---|---|
| Keyblade swing / hit / finisher sounds (slots 83–95) | in the build (`spot33_sfx.py` + `spot33_weaponsfx.py`) |
| EX Burst sounds on the current hits | in the build |
| Intro "slow flourish" (`intro_codex.py VARIANT=spin`) | in the build (`tools/poses/intro_spin.py`) |
| EX Mode "LIGHT!" activation, burst opening, charge-strain loop, finisher | taken into the build (`gmo_motion.py take`) |
| timed solo **Trinity** EX endings `_812A/B/C` | in the build; plays through in test215 |
| blink / angry EX face (texture animation) | offline only; not in the game yet |
| overlay hook to silence Cloud's two Omnislash sounds for Sora | not yet |

### Lessons from integrating Codex's work

- **Take motion blocks, never whole files.** Codex's GMOs carry an *older* snapshot of Sora's
  model. `gmo_motion.py take` copies only the named motions into the current model.
- **Memory:** taking the Trinity motions grew the model to 2,523,344 bytes → **crash at battle
  start** (test215). Fixed by thinning the win-camera motion (`gmo_thin.py`). Every delivery
  costs model memory; check the size.
- **Asserts can clash:** Codex's builder asserted that bone 51 (`wep0`) never moves in the burst
  motions. But the keychain uses `wep0` as its pendulum, and the burst MATCH warp keys it.
  Claude ran a copy with that check off and asked Codex to relax it.
- **Mat picks.** Sometimes Claude's helper and Codex do the same job in parallel (Firaga and
  Thundaga looks, intro). Mat compares and chooses. Separate scripts make that easy.

---

## 11.6 Where to look

These files are in the private working project (not published here):

- `codex/START-HERE.md` — the contract (read it first).
- `codex/COLLABORATION.md` — question states, editing rules.
- `codex/QUESTIONS.md` — the queue.
- `codex/TASKS.md` — jobs for Codex.
- `codex/README.md`, `codex/CODEX-HANDOFF-20261015.md` — Codex's own index of candidates.
- `docs/CURRENT-BUILD.md` — the disc everybody works from.

Next: [Chapter 12 — Lessons learned](12-lessons-learned.md).
