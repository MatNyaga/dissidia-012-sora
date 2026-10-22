# Testing: how a change is checked

Every change goes through the same ladder: **static checks** (no emulator) → **host tests** (our code run on the PC)
→ **PPSSPP** (the emulator, in a throw-away profile, strict mode) → **PS Vita** (real hardware, PSP mode). A step
only counts when its check says PASS. Terms: [glossary](../learn/GLOSSARY.md#phase-2-engine-and-package-terms).
The full list of checks per package: [PACKAGE-ACCEPTANCE.md](../PACKAGE-ACCEPTANCE.md).

Keep these apart when you report results: source checks (syntax, unit tests), file hashes, structural checks of a
built disc, short in-game smoke tests, full in-game tests, hardware tests, and the project owner's own acceptance.
A newer build isn't automatically a tested build, and an old test result doesn't prove a newer build works.

Run every Python tool from the repository root with `python3 -I` (isolated mode: a stray file named like a standard
module in the current folder cannot break the import). All tools below open discs read-only unless they say
otherwise.

> **What you can run from this repository.** Section 0 needs no game files and runs from a fresh clone. Sections
> 2-7 describe the project's full check ladder. Several of its tools (the acceptance kit under `tools/qa/`, the
> engine v2 host tests and step builders, `rowgen.py`, `owner_scan.py`, the registry sources under
> `tools/dlc/registry/`) are in the private working project and **not published here yet**:
> [list](../REPRODUCIBILITY.md#phase-2-tools-not-in-this-snapshot). Published and usable with your own disc:
> `tools/pkg/equiv.py`, `install.py`, `extract.py`, `validate.py`, `pkgapply.py`, `make_release.py`,
> `tools/pkg/engine/install_engine.py`, `find_status.py`, `launch_isolated.sh` and `test/run_host_test.py`.

## 0. Checks that need no game files

From the repository root:

```sh
bash tools/repository/smoke.sh
```

This makes a temporary copy of the committed source (`git archive HEAD`), runs every check on it with Cargo
offline and synthetic test files, then deletes the copy. It needs Bash, Git, tar, Python 3, Cargo, xdelta3 and an
already filled Cargo cache. It does not test uncommitted edits. It checks Python and Bash syntax, JSON files, the
patch app's Rust unit tests and the synthetic patch-app cases.

You can also run the parts one by one:

```sh
python3 tools/repository/check_source.py
cargo test --locked --manifest-path tools/installer/Cargo.toml
bash tools/installer/tests/run_synthetic.sh "$(mktemp -d)"
python3 -I tools/pkg/engine/find_status.py --selftest
```

The synthetic suite makes its own tiny test files and checks VCDIFF round trips, that the input is never changed,
"(2)" naming instead of overwriting, wrong region or game, truncated, modified or already-patched files, archives and
compressed images, missing or empty inputs, read-only output folders, unsupported compression and corrupted patches.
Don't point its working folder at real game files.

Some tools are not asset-free: `tools/pkg/engine/test/run_host_test.py` reads a real local disc, and
`tools/scripts/test_combo.sh`, the debugger tools and GUI automation can change emulator state. Read them before you
run them.

---

## 1. The ground rules

- **Never write the clean dump** (`dumps/ULUS10566.iso`, SHA-256 `df94177d…d1ab6e`) or the **oracle**. Work on new
  files only. The installer and the build scripts refuse to overwrite.
- **The oracle** is the frozen reference disc: `dumps/ULUS10566-P2-oracle-R4.iso`, SHA-256
  `9d311d17a7739fee2c6768f0dce3e1703db587b7c0eefd5d5180e983eb92205f` (release 1.0 plus the 1.0.1 Opponent Info fix).
  Every Phase 2 disc is compared with it.
- **"Equivalent"** means: the game reads the same bytes from both discs, and the code differs only at the hook sites
  you declared.
- Inside the project, a build or patch first gets its base disc confirmed in the project's internal question queue
  ([CONTRIBUTING.md](CONTRIBUTING.md#how-questions-and-claims-are-tracked)).

## 2. Static: one command for a whole disc

The acceptance runner calls every static check on one disc and judges the result against a **profile** (a small
JSON file that says what this disc is supposed to be: owners, registry sources, allowed code differences and their
exact word count, the frozen module, the reference sha).

```
python3 -I tools/qa/acceptance/run_static.py --list-profiles
python3 -I tools/qa/acceptance/run_static.py --disc DISC.iso --profile p25-saves --fast      # about 2 minutes
python3 -I tools/qa/acceptance/run_static.py --disc DISC.iso --profile p25-saves             # about 10 minutes
python3 -I tools/qa/acceptance/run_static.py --disc DISC.iso --profile p25-saves --controls  # + proves each allowance is needed
```

- Profiles live in `tools/qa/acceptance/profiles/`: `oracle-r4`, `p23-flags`, `p24-items`, `p24-step1`,
  `p25-saves`, `p28-sorac`. A new kind of disc (for example Sora + a second fighter) gets a new profile file; the
  runner has no Sora default.
- Output: `report.md`, `report.json` and one log per tool (each log starts with the exact command), by default in
  `dumps/acceptance/<disc>-<sha8>-<profile>/`. Exit 0 = PASS, 1 = FAIL.
- `--with-verify` adds the slow package check (`pkgapply.py verify`, about 15 minutes). `--selftest` checks the
  runner itself, no disc needed.

What it runs (items A0-A16), and the tool behind each, if you want one alone:

| item | checks | tool |
|---|---|---|
| A0 | disc sha before and after (unchanged), = the profile | built in |
| A1 | every per-fighter table in `system.bin` has a row for each package owner (a missing row crashed the Vita once) | `python3 -I tools/qa/owner_rows.py DISC --owners 33,34` |
| A2 | packages are valid | `python3 -I tools/pkg/validate.py --strict PKG ...` |
| A3 | registry sources are valid against the disc | `python3 -I tools/dlc/registry.py validate tools/dlc/registry/sora.json --disc DISC` |
| A5 | equivalence with the oracle | `python3 -I tools/pkg/equiv.py ORACLE DISC --expect-engine --allow-site ID ... --expect-words N --json OUT.json` |
| A6 | no owner-33 constant left in the code (the owner-33 compares and other owner numbers in the code) | `python3 -I tools/pkg/owner_scan.py --disc DISC --budget 0,0` |
| A7 | every owner → name map has each package owner | `python3 -I tools/qa/owner_names.py DISC --owners 33,34` |
| A8 | model lookup for owner 34 (the Cosmos check) | `python3 -I tools/qa/objentry_resolve.py DISC --owner 34` |
| A9 | Sora's release checks | `python3 -I tools/qa/static_checks.py DISC` |
| A11 | the installer-written tables equal what the generator computes | `python3 -I tools/pkg/rowgen.py check --disc DISC --registry sora` |
| A12 | nothing still points into code ranges we freed | `tools/pkg/engine/p24_refscan.py` |
| A13 | **the 16-byte stack rule** (below) | `python3 -I tools/qa/acceptance/stack_rule.py DISC` |
| A14 | the engine install state: module, EXTRA.REG, stub table | `python3 -I tools/qa/acceptance/engine_disc.py DISC` |
| A15 | host tests and selftests (section 4) | — |
| A16 | with `--controls`: equiv again with one allowance left out must say DIFFERENT | — |

### equiv.py, the comparison tool
`tools/pkg/equiv.py A.iso B.iso` resolves every game file the way the game does (our `EXTRA.IDX` first, then the
game's own file list) and compares bytes, down into containers (MPK, ARC chunks, effect packages, text packs).
Code differences are listed as words with their address and the code-site id from `tools/pkg/code_sites.json`.
- `--expect-engine`: disc B may carry `EXTRA.PRX` / `EXTRA.REG`.
- `--allow-site ID`: only the listed sites may differ (an id from `code_sites.json`, or `IMAGE:0xLO-0xHI`).
- `--allow-shrink IMAGE:0xLO-0xHI`: a code image may get shorter there (declared, never silent).
- `--expect-words N`: FAIL unless exactly N allowed words differ. This keeps old discs tight when an id grows.
- Exit 0 = IDENTICAL. A full run takes about 7 minutes on a fast disk.

## 3. The 16-byte stack rule

Module code is C, compiled by psp-gcc, which keeps the stack pointer only 8-byte aligned. The game keeps vectors on
its stack and stores them with VFPU `sv.q`, which needs 16-byte alignment. On 2026-10-21 a module function that
called game code with a misaligned stack froze PPSSPP's JIT forever (the real hardware would raise an address
error). Rule: **every call from module C into game code goes through an aligning thunk** (`GFN` → `gt_<address>` in
`tools/pkg/engine/extra/beh.c`, the function listed in `GAME_FNS`); asm wrappers keep the stack a multiple of 16.

```
python3 -I tools/qa/acceptance/stack_rule.py DISC.iso        # or a .prx file
python3 -I tools/qa/acceptance/stack_rule.py --selftest
```

Story: [P2.4-tri.md](../../notes/phase2/P2.4-tri.md) §8, [notes/dlc.md](../../notes/dlc.md) §F 15.

## 4. Host tests (our code on the PC, no emulator)

The engine's C code is compiled for the PC and run against real disc data; the old hand-written MIPS it replaced is
run in a small MIPS emulator (`tools/pkg/engine/test/mips_emu.py`) on the same fake game memory, and the game calls
of both are compared.

```
python3 -I tools/pkg/engine/test/run_host_test.py       # module v1 boot logic (14 cases)
python3 -I tools/pkg/engine/test/run_host_test_v2.py    # engine v2: status cases + every C behaviour vs the old asm
python3 -I tools/pkg/engine/test/run_p23_test.py        # P2.3 lookup blocks, owner by owner
python3 -I tools/pkg/engine/test/run_p25_test.py        # P2.5 save records (25 friend cards, migration)
python3 -I tools/pkg/engine/test/run_p27_test.py        # P2.7 installer words + the grid cap
```

Each takes an optional reference ISO (read-only; the default is named in its header). Planted bugs inside the
tests prove the test can fail. Selftests without a disc:

```
python3 -I tools/dlc/registry.py selftest
python3 -I tools/pkg/rowgen.py selftest
python3 -I tools/pkg/engine/p24_stubs.py --selftest
python3 -I tools/pkg/engine/find_status.py --selftest
python3 -I tools/qa/acceptance/engine_disc.py --selftest
```

## 5. PPSSPP: a throw-away profile, strict mode

```
python3 -I tools/qa/acceptance/runtime_plan.py --disc DISC.iso --profile p25-saves --port 41337 --out PLAN.md
```

`runtime_plan.py` **runs nothing**. It prints the emulator checklist for one disc (items B and the strict smoke E):
the exact launch line, the tool for each item, what PASS looks like, and "n/a" for features the package does not
have. Then the person who owns the emulator runs the steps.

Launching a disc in a disposable profile (PPSSPP as a Flatpak; the script runs inside it):

```
flatpak run --env=STRICT=1 --env=PORT=41337 --command=sh org.ppsspp.PPSSPP "$PWD/tools/pkg/engine/launch_isolated.sh" DISC.iso
```

- The script copies the PPSSPP settings and saves into a temporary profile, so your own profile and saves are never
  written. It reads the settings from the Flatpak config path at the top of the script; adjust that line for your
  machine. `SAVES=folder` uses other saves, `SAVES=none` starts with no save (new-game tests).
- `STRICT=1`: a bad memory read stops the game instead of reading 0. PPSSPP normally hides such reads; a real PSP or
  Vita crashes on them. Use it for every smoke test.
- `PORT=n`: the debugger port of this instance (default 41336). Two people or helpers at once need two ports.
- `CPUCORE=2` runs the IR interpreter instead of the JIT (useful to tell a JIT problem from a real one).
- `python3 -I tools/pkg/engine/find_status.py PORT` reads the engine's status block from the running game: file
  index state, registry state, stub state, calls per stub.

What a full in-game pass covers: Sora as player and as CPU, a mirror match, all six outfits, normal and EX Mode,
Trinity Limit (full, incomplete and KO), ground and air magic, Reflect, assists, the menus (shop, customisation,
Museum, Jukebox, Records), saves and unlocks, music, and intros from both sides. Check other fighters too,
especially Cloud and Garland. Long battles and many rematches in a row matter, because shared sound-bank memory
problems show up late. Use **copies** of saves, never your own.

Habits that saved time:
- One emulator instance per person; kill only the process you started (by its PID).
- **Every test battle: set CPU strength Minimal and the stage Order's Sanctuary explicitly**, and check the setup
  screenshot before the battle. A restart resets them.
- Put a vanilla fighter on the same screen as a control for every menu check.
- Remove every breakpoint when done; a forgotten one looks like a frozen game.
- Compare the busy time per frame with the oracle for menus that build long lists (the Shop list calls one item hook
  about 29,600 times in one frame).

More detail: [learn/09-testing.md](../learn/09-testing.md) (the debugger tools) and
[PHASE2-START.md](../PHASE2-START.md) §11 (traps).

## 6. PS Vita (real hardware)

The Vita runs PSP games through Adrenaline (custom firmware), which uses Sony's own PSP firmware. It is much closer
to a real PSP than PPSSPP and is the project's hardware gate. Guide and the five-minute check for a new fighter
disc: [TEST-ON-VITA.md](../TEST-ON-VITA.md). Key points: game plugins off, CPU clock Default for menu-speed
comparisons, verify the disc's sha after a remount (a card once dropped a write silently), saves made by PPSSPP are
refused by the real firmware.

## 7. Building the disc you test

| disc | command |
|---|---|
| engine + Sora, layout C (from the clean dump) | `python3 -I tools/pkg/install.py dumps/ULUS10566.iso OUT.iso packages/engine packages/sora-C --layout C` |
| Phase 2 step discs (from a copy of the oracle) | `tools/pkg/engine/build_p27.sh [OUT.iso] [REGISTRY ...]`; also `build_p23.sh STEP [OUT]`, `build_p25.sh` (arguments in each script's header; each refuses to overwrite) |
| the release-style disc (layout B) | `python3 -I tools/pkg/install.py dumps/ULUS10566.iso OUT.iso packages/sora --layout B` |
| a player patch from a finished disc | `python3 -I tools/pkg/make_release.py dumps/ULUS10566.iso DISC.iso OUT_DIR --version X.Y` |

A package still reproduces its reference disc:
`python3 -I tools/pkg/pkgapply.py verify dumps/ULUS10566.iso dumps/ULUS10566-P2-oracle-R4.iso packages/sora-R4`.

Check package bounds, ids, event order, FEP alignment and serials, the sound budget, and that a patcher run twice
gives the same result, always on a throw-away copy. Note the input and output hashes, the commands and the tool
versions. Use `equiv.py` instead of requiring whole-ISO equality after a layout change.

## 8. Known limitations

- A fresh clone can't do a full build until the excluded inputs and missing helpers are restored locally
  ([REPRODUCIBILITY.md](../REPRODUCIBILITY.md)).
- There is no pinned dependency environment yet.
- A real PSP hasn't been tested.
- The Phase 2 engine is tested step by step against the oracle; Sora as package #1 on the engine (P2.8) is in
  progress, and no second fighter has been installed yet (P2.9).

Current release status and known issues: [ROADMAP.md](../ROADMAP.md).
