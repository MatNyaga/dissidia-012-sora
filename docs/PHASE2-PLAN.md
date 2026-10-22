# Phase 2 — the generic character engine (plan for Claude and Codex)

Written 2026-10-19 by Claude (phase2 research helper), updated by each step's helper. **Status: in progress
(P2.0-P2.7 done, P2.8 building; P2.9 next).** Phase 2 discs are test discs; release 1.0 is unchanged. **Start here: [docs/PHASE2-START.md](PHASE2-START.md)**
(2026-10-20: status, oracle, decisions, first three work items, space map, tools, traps, glossary). Background: `notes/dlc.md` (§2 new-fighter table incl.
rows 29-32, §3 design, §F lessons from the release tests), `notes/dlc-phase0.md` (P0.2-P0.8), `docs/ENGINE.md`
(EXTRA.PRX v1, status block, API skeleton), `docs/PACKAGE-FORMAT.md` (§11 `features` = the registry block),
registry spec `tools/dlc/owner_tables.json`, owner-33 inventory `notes/dlc-phase2.md`.

Some tools named here are in the private working project and not published yet: [list](REPRODUCIBILITY.md#phase-2-tools-not-in-this-snapshot).
Disc names (`dumps/…`) and package folders (`packages/…`) are local files and are never published.

## In plain words (for Mat)
- Today Sora works because **86 places in the game's code and tables say "owner 33 = Sora"** (counted in
  `notes/dlc-phase2.md`, inventory v2 2026-10-20). A second new fighter would need all 86 again, and some of them have no room left.
- Phase 2 replaces those 86 places with **one lookup table** (the "registry": one row per extra fighter) and moves
  Sora's special code (EX run speed, Reflect guard, Trinity Limit, his items) into **our own C module** (`EXTRA.PRX`,
  already on the release disc). After that, a new fighter is **a package + one registry row**, no new game code.
- **Proof that it works:** (1) Sora rebuilt on the engine behaves exactly like the released Sora; (2) a throw-away
  **test fighter at owner 34** (a Cloud copy with another name) is selectable, fights, saves and shows up in every
  menu, without one line of owner-34 code.
- **What stays out:** more than one extra cell on the select screen (needs an L/R page = Phase 3) and drop-in
  Memory Stick DLC (Phase 4). With today's grid the engine allows **two** extra fighters (33 and 34).
- **What you would test:** the real-PSP checks (our module and its file list on CFW), and later the test fighter.

## How to work on this (both agents) — same protocol as Phase 0/1
- **Claim before starting**: append to `codex/QUESTIONS.md` `### P2.N claimed — <Claude|Codex> — <UTC>` (append-only,
  UTC). One owner per task. Stopping → `P2.N released` + where you got to. Status lives in §5 (owner updates).
- **Base image rule (Mat)**: before EVERY build or patch application, get Claude's explicit confirmation of the base
  image (exact ISO path + sha256) through `codex/QUESTIONS.md`.
- **Never write** `dumps/ULUS10566.iso` or a disc someone else uses; copies only:
  `cp --reflink=auto <base> dumps/ULUS10566-p2N-<name>.iso`. Phase-2 discs are **test discs**; the shipped release
  stays the Phase-1 one until Mat approves an engine release.
- **Ownership**: canonical `tools/scripts/*`, `build_sora.sh`, `bootstrap_base.sh` = Claude only. Engine C code in
  `tools/pkg/engine/` (either agent), registry/allocator tools in `tools/pkg/` (Python `-I`, re-runnable, `--dry`
  never writes, refuses the clean dump as output). `tools/dlc/owner_tables.json` edits: one writer at a time (claim it).
- **Emulator**: one owner at a time, disposable profile (`tools/pkg/engine/launch_isolated.sh`), never `pkill -f`,
  game-window captures only; test battles CPU Minimal + Order's Sanctuary set explicitly. Real PSP = Mat (H).
- **Deliverables**: section appended to `notes/dlc-phase2.md` (question → method → evidence → answer → what it
  means); every lesson a future fighter would also hit also goes into `notes/dlc.md` §F and the registry spec.
- **Status words**: TODO → CLAIMED → DONE (static) → DONE (runtime) → BLOCKED (say on what).
- **Who**: S = static, R = emulator, H = Mat's real hardware (PS Vita, PSP mode), M = Mat decides.

## Definitions
- **Engine disc**: clean ISO + engine patch (EXTRA.PRX v2 + stub table + generic hooks) + zero or more packages.
- **Registry**: per-owner rows (owners 33..34 today, format allows up to 63) built by the installer from each package's
  `manifest.json` `features` + allocations; read by the module and by the generic hooks.
- **Oracle** (P2.0, frozen 2026-10-20): **R4** = release 1.0 (R3) + spot33_oppinfo, read-only copy
  `dumps/ULUS10566-P2-oracle-R4.iso` sha256 `9d311d17…205f`, package `packages/sora-R4` (6cec661e…749b). Was: p17, or RC3
  if the OQ fix shipped first (it did; R4 = RC3 + the one fix build_sora.sh added since). Why: notes/dlc-phase2.md §P2.0.
- **Behaviour-equivalent**: every game-readable data file identical to the oracle; code images differ only at the
  hook sites listed in `notes/dlc-phase2.md`; the per-package acceptance list (P2.10) passes on both discs.
- **Transitional patch**: a `packages/sora/patches/*.json` file (owner-33 code). Phase 2 retires them one by one.

## Tasks

### P2.0 — Freeze the oracle and the inventory (S, Claude)
- **Q:** what exactly must the engine reproduce, and is the owner-33 list complete?
- **Inputs:** p17 (or RC3), `packages/sora`, `tools/pkg/code_sites.json` (94 ranges), `notes/dlc-phase2.md` inventory.
- **Method:** pick the oracle; re-extract `packages/sora` from it if RC3 (brings `oq_slot_*` into patches/); re-run the
  inventory scan; add any site missing from code_sites.json; resolve the 3 "unconfirmed (indirect)" items by reading
  `spot33_reflect.py` (EX_SND, EE_B) — record the exact owner test or "keyed by item id".
- **Done when:** oracle path + sha256 recorded; inventory = all sites confirmed by bytes; count recorded.

### P2.1 — Engine ABI: registry layout, stub table, feature ids (S, either; design review by the other agent)
- **Q:** how do EBOOT and overlay code reach per-owner data and module code, given the module is relocatable and the
  overlays are re-read from disc on every scene change?
- **Why:** an overlay word cannot hold a module address. Everything else depends on this decision.
- **Method:** specify (a) a **fixed stub table** in EBOOT space freed by P2.4 (EXRUN/EXITEMS/EE_B ≈ 1 KB at
  0x089a8b14, TRI 2.1 KB at 0x089c1c8c, SCALE at 0x089d1fb4): N entries `j <module fn>` + one `REG` pointer word,
  written by `module_start`, **vanilla-safe when the module is missing** (each stub defaults to "return vanilla
  value"/`jr ra` so a disc without EXTRA.PRX still boots); (b) the registry row (fixed size, little-endian, versioned):
  owner, key (`sev120`), name_index, record_slot, start_preset, scenario names, pictures[scene] (QB, untold tale,
  party, arrange, OQ, Level Adjust, setup, Labyrinth face, Records icon, panel sprite + textures), setup_frame,
  party_frame, network name, OQ face/banner/name, title-call (voice, days), feature bits (reflect_guard,
  ex_run_speed, ex_burst_sound_skip, burst_controller id, item_effects), params (multiplier, voice slots, item ids);
  (c) feature ids for `extra_feature(id)` (already exported, returns 0 in v1); (d) where the registry bytes live:
  **a data file `EXTRA.REG` served through EXTRA.IDX** (installer writes it; module loads it at boot) — keeps the PRX
  identical for every roster. Bump status layout to v2 (append-only, as ENGINE.md requires).
- **Done when:** `docs/ENGINE.md` §"Registry + stubs v2" written, every inventory site mapped to a stub or a registry
  field, cost estimate (words per hook, bytes per row), reviewed by the other agent.
- **DECIDED 2026-10-20 (Claude, on Mat's go-ahead; Codex review still welcome):** v2 design changes in ENGINE.md:
  header-indirect XSTB stub table (6-word header at 0x089A8B24), installer-written per-owner tables for table lookups,
  stub list without S23 EX_SND and with S24 PANEL_LIT, and the P2.1-review High fixes (visibility gate on the unlock
  walker, item-eligibility stubs for every package owner, BUF_PTR table for P2.7 buffers, stub-list hash + roster id in
  EXTRA.REG and EXTRA.IDX, publish order registry first / stubs last, overlay-loaded guard).

### P2.2 — Registry builder + validator (S, either)
- **Q:** can the installer turn package manifests into `EXTRA.REG` deterministically?
- **Method:** `tools/pkg/registry.py`: read each package's `features` + `allocations` (values taken from the
  transitional patches where the manifest note is only text — e.g. EX run ×1.40 is the built value, the manifest
  note "1.1" is stale), emit `EXTRA.REG`, refuse duplicates/overlaps; schema in `tools/pkg/schema/`. Extend
  `tools/pkg/validate.py` so a package without a needed feature value fails.
- **Done when:** `registry.py packages/sora` gives a byte-stable `EXTRA.REG` (two runs same sha), host test passes.

### P2.3 — Lookup conversions (S+build, then R)
- **Q:** can every "lookup" site read the registry instead of testing owner 33?
- **Method:** one generic hook per site group (inventory #1-#5, #13-#21 + data tables #22-30; #6-#12 are behaviour = P2.4), smallest first:
  name index (EBOOT FUN_088d6254 + menu FUN_08a1d7f8), scenario names, start preset, Labyrinth face, Records icon,
  menu name keys, party frame, setup banner, the 13 picture remaps, Museum viewer list, OQ face/banner/name, title
  call, Aerith-assist append, record slot. Each conversion lands as its own test disc with the transitional patch of
  that site removed, then `equiv.py` vs the oracle (only the converted site may differ) + a targeted runtime check.
- **Updated 2026-10-20 from the research (notes/phase2/P2.3-lookups.md, 25 lookup items: 14 data rows, 11 code):**
  - **Step 1 = row generator:** the installer/registry tool writes the data-in-code rows (D1-D3, D5-D8, D12, D14) from
    registry values + a machine-readable table spec. Sora's values do not change → `equiv` must say **IDENTICAL**.
    **DONE 2026-10-20 (static):** `tools/pkg/rowgen.py` (spec = owner_tables.json `rowgen`), 18 tables IDENTICAL to
    packages/sora-R4 and to the oracle; test disc dumps/ULUS10566-P23-rowgen.iso = oracle sha (notes/phase2/P2.3-rowgen.md).
    Installer wiring waits for install*.py (P2.3-rowgen §7).
  - **Step 2 = names in place, no helper:** C1 name index (10 words inside FUN_088D6254's own 11, reads the
    scenario_names row) and C2 network name (calls C1). No new space, vanilla cost.
    **DONE 2026-10-20 (static + strict runtime):** `tools/pkg/engine/patches/p23_names.py` (moved 2026-10-21; old path = wrapper); dumps/ULUS10566-P23-names.iso b73af9e1…4e2c;
    equiv = oracle except the 20 site words; Records / Jukebox / Friend Card show "Sora", controls unchanged; per-frame
    cost = oracle (notes/phase2/P2.3-names.md). Allow-list bounds 0x088D6254, 0x088D6270; code_sites range of
    network_name_hook to widen to 0x08a1d83c.
  - **DECIDED 2026-10-20 (Claude, on Mat's go-ahead; Codex review still welcome):** table-shaped lookups (pictures,
    party frame, setup banner, Museum viewer, OQ pairs) use **small per-owner tables written by the installer** ("OXT"),
    not runtime REG_ROW lookups: vanilla cost, offline-checkable, work even if EXTRA.PRX fails to load. REG_ROW stays
    for code that needs it.
  - The other code conversions need space: the menu-overlay gap 0x08B59258–0x08B63170 (static: free; runtime write
    watch still open) or the EBOOT range P2.4 frees. So "P2.3 and P2.4 in parallel" holds for steps 1-2 only.
  - Also P2.3 now: **BGM mode-7 fallback** (inventory #6) in place with an owner bound = REG_ROW (DECIDED 2026-10-20:
    do NOT drop the owner test — vanilla mode 7 also gives −1 for Chaos / Feral Chaos / locked Shantotto, Prishe);
    **Jukebox gates** (inventory #19, REG_FLAG / installer bitmap) — listed here, not under P2.4; **visibility gate**
    on the unlock walker (FUN_088d5ac8 / FUN_088d5ce8: list an owner ≥ 33 only if its registry row exists; P2.1 review).
  - Not P2.3: record slot → P2.5; Aerith-assist append → keep (0x21 there is vanilla's DLC-Aerith owner; the drop
    words 0x7F are an install-time immediate); title call → P2.7, required for real fighters (DECIDED 2026-10-20 (Mat), Q-M2: yes; table full at 35, needs new caller slots); Records list,
    Characters panel, grid/select/EX-page rows → P2.7. (2026-10-20, rowgen: D13 title call is not generated, it moves
    to P2.7 with the new caller slots; D11 ex_mode_page has no row for owner 34 (row 33 = other data) → P2.7 list.)
  - **Steps 3-7 DONE 2026-10-21 (Claude, P2.3 lookups helper; static + PPSSPP A/B + controls + strict):** home = the
    freed EBOOT block 0x089A8B94-0x089A8F0C ("OXT1": PIC_IDX, PARTY_FRAME, SETUP_OFF, VIEWER_OWNER, REC_ICON,
    PANEL_SPRITE, OQ_PAIR, REC_APPEND, KEY_POOL + helpers FLAGPKG / BGM_FB / OQ_BUILD / REC_HELP; menu gap not used —
    notes/phase2/P2.3-home.md); pictures (C3 + C4 + C5 + C9 panel sprite, `P23-pictures` 83ff4ca5…), Museum (C6 viewer,
    D4 Records icon, the Records append, `P23-museum` a105af3c…), OQ face (C7 + OQ_PAIR, `P23-oqface` d810dc20…), flag
    gate (C10 → EXTRA.REG flag-range list published by engine 2.5.0; BGM mode-7 fallback → REG_ROW via BGM_FB,
    `P23-flags` 39d82a75… = everything). One cumulative recipe `tools/pkg/engine/build_p23.sh STEP`, writer
    `tools/pkg/engine/patches/p23_lookups.py`, host test `tools/pkg/engine/test/run_p23_test.py`. **owner-33 compares on the
    final disc = 0**; other owner immediates 14 → 5 (all P2.5 save hooks; assist 0x088D5C7C allow-listed = vanilla
    DLC-Aerith constant). Menus within ±4 % of the oracle. Hand-offs: notes/phase2/P2.3-flags.md §6.
    **Not done here:** the unlock-walker visibility gate (P2.1 review: list an owner ≥ 33 only when its registry row
    exists) — no owner-33 constant, needs REG_ROW in FUN_088d5ac8 / FUN_088d5ce8; do it with P2.8/P2.9 (owner 34).
- **Done when:** all lookup sites converted; `packages/sora/patches/` keeps only behaviour patches; RR menu subset PASS.

### P2.4 — Behaviour modules in C (S+build, then R)
- **Q:** can Sora's special code run from EXTRA.PRX, parameterised by the registry?
- **Method:** port, one at a time, with the old asm as reference: EXRUN (25 words), EXITEMS/item owner (148) +
  SCALE (48) + item effects (EE_B 49 + 12 state, EE_A in the TRI range, HELM in the cave), reflect guard (cave 128
  code words = 512 B, full + hooks), TRI burst controller (520 + table 16). Hooks keep their `jal`, now to a stub.
  Frees the EBOOT dead code (841 words) and the battle-overlay cave (overlay file back to vanilla size).
  (2026-10-20: BGM fallback and Jukebox gates moved to P2.3 — they are lookups; EX_SND is not built, nothing to port;
  PANEL_LIT menu 0x08AFF32C is an item site = stub S24. Sizes from notes/phase2/P2.4-behaviour.md §2.)
- **DECIDED 2026-10-20 (Claude, on Mat's go-ahead; Codex review still welcome):** stub table = **header-indirect
  "XSTB"**: a 6-word header fixed at 0x089A8B24 points at the stub arrays, so the **EXRUN pilot** lands first (header +
  1 stub + REG_ROW in the 28 words EXRUN frees), before TRI moves. Port order: 0 infrastructure + EXRUN pilot → 1 TRI +
  EE_A (frees the TRI range; arrays move there) → 2 reflect cave → 3 SHIELD + EE_B → 4 item ownership + menus.
  Item-eligibility stubs are installed for **every** package owner (owner 34 shares Garland's equip bit).
- **Done when:** no owner-33 compare (a test against the constant 0x21) left in any code image (scan = 0 hits) **and**
  no other new-vs-clean owner-33 or package immediate (owner 33 loaded or compared as a constant — e.g. the TRI
  bar-voice code at 0x089C2184 —, item ids 678-682 / −678, sprite cell 32, voice 21910042, motion 8501, EX-page pictures, multipliers;
  `tools/pkg/owner_scan.py` reports both groups); EX lifecycle, Reflect, Trinity, items, EX run checks PASS on PPSSPP.
  Baseline today: 16 owner-33 compare hits (P2.4 owns 13, P2.3 3). **2026-10-21 (step 4): 2 left, both P2.3; P2.4's part = 0.**
- **Per-step rule (from step 0):** compare each behaviour's measured numbers **disc vs oracle** (same assisted A/B
  steps), never vs a research note; registry values for constants come from the whole built constant (both halves).
- **Step 0 DONE 2026-10-20 (static + PPSSPP):** EXRUN pilot, XSTB v1, `dumps/ULUS10566-P24-exrun.iso` f5c2577c…a16e,
  equiv IDENTICAL (28 allowed words), Sora EX run ×1.400 = oracle, controls PASS, owner-33 compares 16 → 15
  ([P2.4-exrun-pilot.md](../notes/phase2/P2.4-exrun-pilot.md)).
- **Step 1 BUILT 2026-10-21 (P24-tri: static PASS, runtime BLOCKED; FIXED on tri2, see below)** ([P2.4-tri.md](../notes/phase2/P2.4-tri.md)): TRI S0-S4 +
  EE_HIT S5 + TRI_HPROW (and EE_GUARD/EE_PROJ behind temporary stubs 29-31) in C (extra/beh.c), XSTB **v2** in the
  freed TRI range (abi_hash 0x39415849, stub_state −5 on mismatch), registry aux TRI (`voice_bank` 219100) + EE;
  `dumps/ULUS10566-P24-tri.iso` 197ebdf7…688f (+ P2.3 names), equiv IDENTICAL (585 allowed words), owner-33 compares 16 → **7**
  (P2.4 part 9 = plan), host test C vs R4 asm identical (35/35). PPSSPP: Cloud / Garland / module-missing / incomplete
  burst / strict / ticks PASS; **a full Sora EX Burst freezes under the JIT** when stub 5 is routed through the module
  (IR interpreter passes) — root cause open (P2.4-tri §4.3); step 2 waits for it.
  **FIXED 2026-10-21 (freeze helper, P2.4-tri §8):** cause = module C (psp-gcc EABI, 8-byte stack) called the bar-full
  voice with sp = 8 mod 16; the game's sv.q matrix store then faulted forever in PPSSPP's fastmem JIT. Stub 5 was not
  involved (vanilla S5 still froze). Engine 2.1.1 calls every game function through a 16-byte aligning thunk;
  `dumps/ULUS10566-P24-tri2.iso` 52f63297…ae6b (oracle copy, same recipe), equiv IDENTICAL (585 words); JIT full
  burst 3/3, incomplete, Cloud, Garland, Kingdom Key = oracle, module/registry-missing, strict 0 bad accesses: PASS.
  Step 2 may start (rule: ENGINE.md §10 wrapper rule).
- **Step 2 BUILT + TESTED 2026-10-21 (static PASS + PPSSPP PASS)** ([P2.4-reflect.md](../notes/phase2/P2.4-reflect.md)):
  the battle-overlay Reflect cave (IS_SORA_EX, C1, C2, C3, C7, HELM) in C (engine 2.2.0, 666aa688…), C4 = EBOOT fallback
  only, temporary stubs 29-31 gone (STUBS_V2R, abi_hash 0x3B25613D), **OVL_BATTLE_APP.ELF back to the clean 1,596,312 B**.
  Disc `dumps/ULUS10566-P24-reflect.iso` 48977859…49c5 (oracle copy, build_p24_reflect.sh, built twice); equiv IDENTICAL
  with `--allow-shrink OVL_BATTLE_APP:0x08b62f70-0x08b63170` (new, always reported) + 590 allowed words; owner-33 compares 7 → 6 (P2.4
  part 9 → 8 = plan); host v1 14/14, v2 46/46 (cave asm vs C). PPSSPP A/B vs the oracle (CPU Lightning, TYPE Vicious,
  Minimal): HP / melee / projectile reflects, no guard damage, Crown ×0.769, barrier frame-for-frame the same, bursts,
  Cloud / Garland / vanilla guard controls, module/registry-missing (normal guard, no hang), strict 0 bad accesses,
  ticks in noise. tri2 recipe frozen in extra/tri2/ (still 52f63297…). Next: step 3 (SHIELD + EE_B).
- **Step 3 BUILT + TESTED 2026-10-21 (static PASS + PPSSPP PASS)** ([P2.4-shield.md](../notes/phase2/P2.4-shield.md)):
  Save the King's SHIELD in C (engine 2.3.0, stub 20, STUBS_V2S abi_hash 0x3BC585AE), EBOOT SHIELD + EE_B (84 words)
  back to the clean dead-function words, `params.shield_pct` retired (item_fx REFLECT_POWER kept). Disc
  `dumps/ULUS10566-P24-shield.iso` 5267025c…9efb (oracle copy, build_p24_shield.sh, built twice); equiv IDENTICAL with
  the step-2 sites + `p24_freed` + the same `--allow-shrink` (675 allowed words); owner-33 compares 6 (P2.4 part 8 = plan), item-680
  immediate gone (26 others left); host v1 14/14, v2 55/55 (R4 SHIELD asm vs C, 5 planted bugs). PPSSPP A/B: reflected
  hit power 150 with / 100 without Save the King on both discs, reflect / Crown / bursts / controls / strict / ticks
  PASS. step-2 recipe frozen in extra/reflect/ (still 48977859…). Next: step 4 (item ownership + menus; needs list in
  P2.4-shield §8).
- **Step 4 BUILT + TESTED 2026-10-21 (static PASS + PPSSPP PASS)** ([P2.4-items.md](../notes/phase2/P2.4-items.md)):
  item ownership + menu hooks in C (engine 2.4.0 69e02f65…, STUBS_V2I abi_hash 0x2F2EAE84: ENSURE 13, NEWGAME 14, ELIG 15,
  ROWMASK 16, MENU_FIX 17, PICID3/0 18/19, STASH 21, SCALE 22, PANEL_LIT 24; menu-overlay guard), the rest of EXITEMS +
  the dead-jump-table SCALE back to clean words (0x089A8B94-0x089A8F0C = one 222-word unreachable block again). Registry:
  start-owned bit (item_owner bit 7, min engine 2.4.0), aux SCALE + aux EXPAGE (PICID stays a registry lookup, not a
  P2.3 table), `params.crown_drain` retired. Disc `dumps/ULUS10566-P24-items.iso` 807e09fc…1a0f (oracle copy,
  build_p24_items.sh, built twice); equiv IDENTICAL (860 allowed words, new id `p24_freed_items`, same shrink); **owner-33 compares 6
  → 2** (both P2.3), other immediates 26 → 14; host v1 14/14, v2 78/78 (R4 EXITEMS + jump-table asm vs C, 8 planted
  bugs). PPSSPP A/B: lists / □ panel / EX page / Lv42 stats / ENSURE / fresh-save new game = oracle, WoL + Cloud
  unchanged, battles PASS, module/registry-missing = degraded (no hang), strict 0 bad accesses; Shop / Buy heaviest
  frames within ~1 % of the oracle (MENU_FIX asm fast path). step-3 recipe frozen in extra/shield/ (still 5267025c…).
  p24_refscan.py fixed (it never listed pointer tables into EBOOT space).
- **P2.4 DONE 2026-10-21.** Every R4 behaviour runs from EXTRA.PRX behind 23 stubs, parameterised by EXTRA.REG; P2.4's
  own owner-33-compare / package-constant count is 0. Left for others (P2.4-items §10): P2.3 = BGM fallback 0x0888B668 + party
  pictures 0x08B2C520 (the last 2 owner-33 compares) + assist drop / Museum viewer / Records / char panel / Jukebox gates; P2.5 = the
  5 save-record immediates; P2.7 = item ceiling 683 (module `ITEM_CEIL` + registry `ITEM_CEILING`); P2.9 = no new module
  code (items optional: `items.owned/start_owned/scale/fx`, `behaviours.ex_page`, row `panel_sprite`).

### P2.5 — Save slots and the record allocator (S, then R)
- **Q:** how does each extra owner get a save record without breaking old saves?
- **Method:** generalise `spot33_save` + `spot33_savefix`: registry `record_slot` (slot **index** 24 for 33, index 23
  for 34 — 0-based: index 24 = the 25th friend card's space, index 23 = the 24th card's), friend-card limit = 25 − package count, one-time migration per new slot (as the 25-card migration did); define the
  owner-35 limit (stats block "vs" stops at 34). Document what a player loses (one friend card per extra fighter).
- **DECIDED 2026-10-19 (Mat):** one friend-card slot per extra fighter is acceptable (25 → 24 → 23 …).
- **DECIDED 2026-10-20 (Claude, on Mat's go-ahead; Codex review still welcome)** (notes/phase2/P2.5-P2.7-saves-capacity.md §A.2):
  record slot index = **57 − owner** (fixed per owner, never moves when packs are added or removed); friend-card cap =
  lowest installed slot index (written by the installer into both cap words 0x088F523C / 0x088F52A0); the migration
  runs **once for all package slots together** (count > cap → cut the list, re-receive every card that sits in a
  package slot, then set records up lazily per owner) — never per owner. Hard owner limit = **34**: the save stats
  blocks hold owners 0..34 (index 35 = the totals row).
- **Done when:** save/load + friend cards + Records PASS with 1 and 2 packages; old Sora saves load unchanged; tests
  S1-S7 of the P2.5 note §A.4 (incl. "add a 2nd pack later" and "remove / re-add a pack").
- **P2.5 DONE 2026-10-22 (Claude, P2.5 save-records helper; notes/phase2/P2.5-saves.md).** Disc
  dumps/ULUS10566-P25-saves.iso 8f163258…31c7 (`tools/pkg/engine/build_p25.sh` = build_p23.sh flags + `patches/p25_saves.py`,
  built twice). GET_RECORD → PKG_REC (installer-written "SRC1" block in the TRI-range tail: REC_CAP, REC_MARK, REC_FLAGS
  + 94 code words), R4's SORA_REC cave clean again, OQ has-record reads REC_MARK, caps = REC_CAP; registry
  install.record_mark / record_legacy (EXTRA.REG unchanged). equiv IDENTICAL (1214 allowed words, new id `p25_saves`,
  control DIFFERENT); **owner-33 compares 0, other owner immediates 5 → 0**. Host: R4 vs P2.5 944 cases + 2-pack reference 972 cases,
  9/9 planted bugs. PPSSPP A/B = oracle (Records, Max. Level, battle counts, OQ has-record, friend cards, save → reload,
  legacy + 25-card migrations once only), fresh record + battle, pack change on a sora+test34 scratch disc (add / remove /
  re-add), module- and registry-missing = same save bytes, Reflect + full Trinity, strict 0 bad accesses. The flags
  recipe is frozen (extra/flags/, --engine v2-flags; P23-flags and P24-items rebuild). S1 (true new game) and owner-34's
  own record need a selectable test fighter (P2.9); §A.3 decisions D1-D6 in P2.5-saves §3.

### P2.6 — Id and flag allocator with a "vanilla writers" list (S, either)
- **Q:** which numbers can a package safely take?
- **Why:** lesson §F-1: Sora's first KH2 flags (1249-1254) were written by vanilla itself (FUN_08a2b07c: level
  milestones 1250-1252, Lv100 rewards 1253-1262); §F-2: flag 1372 lists everything in the Jukebox.
- **Method:** `tools/pkg/allocate.py` + `tools/pkg/ref/vanilla_ids.json`: for every id space in owner_tables.json
  (`category: id-range`: unlock/NEW/SEEN flags, objentry ids, ablt ids, item ids, uicn icons, picture numbers, sound
  ids, FEP ids, texture keys, voice ids, BGM ids, brain sets, record slots) list (a) vanilla data users, (b) **vanilla
  code writers** (constants in the decompiles: flag setters, override checks), (c) Sora's block. Allocation rules:
  blocks per package (flags: Sora 1263-1270; 1271-1284 are vanilla icon flags, so next packages use the pool 3200-3455, notes/dlc-phase2.md §P2.6), objentry ids < 1338 for owner 34,
  refuse anything in (a)/(b). Emit the package-flag bitmap that `is_package_flag` uses.
- **Done when:** allocator reproduces Sora's numbers from his manifest and gives a clash-free set for a 2nd package;
  the vanilla-writer list covers every flag constant in `dumps/decomp/all.c` + `menu_all.c`.

### P2.7 — Shared capacity (S+build)
- **Q:** where does the game run out of room for a second package?
- **Method (from P0.4 + inventory):** unlock table (1 free row, then relocate), eqpm buffer (full → move or reuse a
  preset), objentry (21 spare rows ≈ 1 fighter), uicn (3 left), ablt cap (installer-computed), Jukebox character list
  + voice-row buffers (full at 34), Records array (32 entries, module-owned array), select/panel list (relocate),
  Museum viewer list (relocate), character-panel sprites (one free sprite = Sora's), menu name-key list terminators.
- **Research 2026-10-20 (notes/phase2/P2.5-P2.7-saves-capacity.md §B, 20 items):** owner 34 fits today in the unlock
  table (last row), objentry (21 spare rows; ids < 1338 and free), uicn, ablt (cap written by the installer), Opponent
  Info row 34 (last), name-key slot 34 (last; new key strings need a fixed home), OQ tables. Needs work: **QB grid rows
  (P0.5 relocation — the one item P2.9 cannot skip)**, eqpm presets (heap-allocating loader FUN_088bcb2c, or start
  preset −1 for the test fighter), Jukebox character list (in-place shift, no buffer move), Records list (32, module
  growth or known limit), Characters panel (31 layout cells → known limit / Phase 3), Museum viewer (34 entries,
  relocate), OQ pair 40 (loop end + pair source), title call (required for real fighters, Mat Q-M2). Moved buffers are
  reached through the REG block's BUF_PTR table (ENGINE.md v2 change). Added 2026-10-20 (P2.3 rowgen): **EX Mode page
  list** (menu 0x08B23F28, −1 at row 32, row 33 = other data at 0x08B24348 → relocate or known limit).
- **Done when:** each item has a chosen fix (relocate / module buffer / accepted limit) and the owner-34 package fits.
- **P2.7 DONE 2026-10-22 (Claude, P2.7 capacity helper; notes/phase2/P2.7-capacity.md).** Disc
  dumps/ULUS10566-P27-capacity.iso 387b0a7e…fb40 (`tools/pkg/engine/build_p27.sh` = build_p25.sh + `patches/p27_words.py`
  + `patches/p27_grid.py`, built twice). **QB / select-grid rows moved** to the EBOOT "GRD1" block 0x089C2140 (34 rows,
  installer data; menu getter → it; GRID_CAP = the 34-entry cap; row bounds = installer immediates): a 34th cell works
  (scratch sora+test34 disc: owner 34 in the 7th bottom cell, random in the 8th; party edit grid 35 → 34 entries).
  **One generic writer** for every installer word (rowgen + OXT + SRC1): unlock row, Opponent Info row, name keys +
  KEY_POOL home, ablt cap, uicn buffer, Jukebox shift (guarded), grid bounds, card caps, **title call generated** (R4's
  layout generalised, 0 new code words, 36 callers; Sora-only = the 155 R4 words → transitional `title_call` retires);
  Sora-only = the P2.5 disc except GRD1. Registry: owner > 34 = ERROR, title-call / grid rules, OQ_FACE for 33/34
  (P2.3 already built OQ pair 40), one item-ceiling source, `--help`. equiv IDENTICAL (1217 allowed words, new id
  `p27_grid`; control DIFFERENT), owner-33 compares 0 / other immediates 0, rowgen 22/22, host v1 14/14 v2 87/87 P2.3 P2.5 P2.7 PASS
  (13/13 planted), PPSSPP A/B = P25 (grids, battle on Order's Sanctuary + Minimal, menus, grid cost within 1 %).
  Every §B item has a decision (P2.7-capacity §3); known limits for test34: Records list, Characters panel, Museum
  record, Jukebox entry, EX Mode page, start preset −1 (better: Chaos's unreferenced preset 78). Open for Mat:
  Q-P27-M1 title-call days, Q-P27-M2 34 entries per page.

### P2.8 — Sora as package #1 on the engine (S+build, then R)
- **Q:** does the engine reproduce the released Sora?
- **Method (updated 2026-10-22 from notes/phase2/P2.8-sora-package.md):** an **engine package** (clean-based,
  820 words = LOADER 53 + ENGINE 624 + ENGINE_R4 143, `tools/pkg/p28_plan.py words`; EXTRA.PRX v2, produce
  eboot_plain, code_cave allocations), a Sora package in **format 1.1** (registry.json in the package,
  identity-keyed rows, 2 transitional patches `save_record_hooks` / `title_call` until P2.5 / P2.7 retire them),
  installer **layout C** → `dumps/ULUS10566-P28-soraC.iso` from the clean dump; `equiv.py --expect-engine` vs the
  oracle (data identical, code differs only at hook sites); full per-package acceptance list (P2.10) on PPSSPP;
  determinism (two builds same sha). Steps E1–E8: notes/phase2/P2.8-sora-package.md §6 (done at E3; Sora-code-free
  at E5).
- **Also (found 2026-10-20, notes/phase2/P2.9-testfighter.md §5):** package-format codecs for the bytes-leaf shared
  tables (acab/amas/chrl/brai/texts store count/offset bytes as rows) and owner-keyed menu-pack picture appends, so two
  packages can install together. Blocks P2.9.
- **Done when:** equivalence + acceptance PASS; result recorded against the oracle sha.
- **In progress.** **E1-E3 BUILT 2026-10-22 (notes/phase2/P2.8-build.md):** `packages/engine` (832 base words + 53 loader + 5
  menu_clock, old = clean; EXTRA.PRX 2.5.0), `packages/sora-C` (format 1.1, identity-keyed rows, registry.json, **no code
  patches**: P2.5 + P2.7 retired both transitional ones = E4 + E5 done), installer layout C → `dumps/ULUS10566-P28-engine.iso`
  (engine only) and `dumps/ULUS10566-P28-soraC.iso`; equiv vs P27-capacity content IDENTICAL with 0 code words, vs the
  oracle IDENTICAL (13 ids, 1217 words); PPSSPP: all three module states live, EX run 1.40, Reflect, full Trinity,
  menus, menu cost = P27. Open: E6 visibility gate, E7 roster_id, E8 two-package dry run, identity codecs for the
  bytes.v1 tables (brai seco, string tables, params, assist), the full acceptance runtime list + Vita.

### P2.9 — Owner 34 test fighter (S+build, then R) — first proof of a 2nd fighter
- **Q:** does a second extra fighter work with **no new owner-specific code**?
- **Method:** package `testfighter`: Cloud's files under a new key, owner 34, objentry ids < 1338 **and free**
  (1335-1337, id_spaces.json) + **fix F6: Cosmos rows 1338/1339 costume byte 1 → 15** (DECIDED 2026-10-20: part of this
  recipe; story loads Cosmos by id but re-resolves `.cosx/.exex` by (owner, costume)), its own name/picture
  rows (placeholder text "Test Fighter", reused pictures), record slot index 23 (= the 24th friend card's space), flags from the P2.6 pool (unlock 3200), grid = 8th bottom cell
  (P0.5: draws and the cursor reaches it). Install Sora + testfighter. Checks: select + fight (vs CPU Minimal, Order's
  Sanctuary), menus that showed owner-33 bugs (OQ slot/party, Records, Museum, Jukebox, Labyrinth, setup banner), save
  + reload, **the Cosmos story scene** (P0.4's open runtime check: owner 34 must not replace Cosmos), Sora unchanged.
- **Done when:** all checks PASS; `grep` of the engine/hook code shows no constant 34 outside the registry data.
- **Note:** test fighter is never released (it reuses Cloud's assets). Cloud vs Test Fighter is not a valid test
  (same FEP id / sound banks). Depends on P2.3 + P2.5 + P2.7 + P2.8 (P2.4 only for the Garland equip-bit alias).
  Recipe + checks: notes/phase2/P2.9-testfighter.md. **DECIDED 2026-10-20 (Mat), Q-M1: yes,** known limits are OK for its PASS (not in
  Records list, Characters panel, Museum viewer, Jukebox list, OQ face); a real fighter must have them.

### P2.10 — Per-package acceptance list + test kit (S, then R)
- **Added 2026-10-19 (Vita crash):** every package must pass `tools/qa/owner_rows.py --owners <its owner>` (static),
  a PPSSPP strict-mode smoke (`--env=STRICT=1`: bad reads stop the game) and the Vita V-list (docs/TEST-ON-VITA.md).
- **Q:** what must every new package pass, and can it be run cheaply?
- **Method:** `docs/PACKAGE-ACCEPTANCE.md` from `notes/dlc.md` §F-8 (unlock/purchase on fresh + 100% saves,
  Jukebox/Museum/Records, Labyrinth BGM, select blurb, Original Quest create/test/save/load/play/return, replay/ghost/
  Friend Card, assist in 4 contexts, EX lifecycle, Data Install on layout B, installer A/B/C) with owner as a
  parameter. Fold the session tools into `tools/qa/runtime/` (BGM-pick breakpoint, unlock-flag word dump, fighter
  finder + teleport, gauge fill, OQ Test → pause → Win), all reading addresses from the registry instead of 33.
- **Done when:** list + tools committed to the tree; one dry run against the oracle R4 reproduces the R4/RC3
  strict-smoke results (docs/PACKAGE-ACCEPTANCE.md §E). (Was "against p17 … RC2"; p17 is superseded by the oracle.)
  **Static part DONE 2026-10-21** (notes/phase2/P2.10-kit-built.md §3: `tools/qa/acceptance/run_static.py`, oracle vs
  itself PASS, P24-items PASS, old P24-tri FAIL for the known reason, a broken copy FAIL; list reviewed and folded into
  PACKAGE-ACCEPTANCE.md 2026-10-22). **Still open:** the runtime dry run = `runtime_plan.py --profile oracle-r4` E smoke
  reproduces the R4 / RC3 results.
  Tool inventory + fold plan (`tools/qa/runtime/qart.py`, address file checked against the oracle with
  `qart.py selfcheck`): notes/phase2/P2.10-testkit.md; session tools preserved in tools/qa/runtime/snapshot-20261020/.

### P2.11 — Delivery with packages (S, M decides)
- **Q:** how do players get Sora + later fighters?
- **Method:** options for Mat: (a) one release per roster (today's flow, one delta per roster); (b) one installer
  with a package list (checkboxes), engine delta + per-package deltas, all from the player's clean ISO; updates via
  `older_outputs`. Keep "no game code shipped" (app-side EBOOT decrypt) and the GPL source sync rule.
- **DECIDED 2026-10-19 (Mat): (b)** one installer with a fighter-pack checklist (Claude's recommendation).
- **Done when:** RELEASE-POLICY.md updated; app change scoped.

### P2.12 — Real-PSP gates (H, Mat)
- P0.2 plain EXTRA.PRX loads on CFW; P0.7 the runtime code write (xidx hook) works on CFW; P0.6 plain-file DLC patch
  (only needed for Phase 4). Phase 2's stub table adds more runtime writes → same check, once, on the P2.8 disc.
- **DECIDED 2026-10-19 (Mat):** real-hardware gate stays, on Mat's **PS Vita with CFW** (PSP mode = Adrenaline;
  runs Sony's PSP firmware on Vita hardware, much closer to a real PSP than PPSSPP). Guide: docs/TEST-ON-VITA.md.
- **Done when:** P2.8 disc boots, fights and saves on the Vita (PSP mode).

### P2.13 — Docs (S)
- "How to add a fighter": [docs/modding/](modding/OVERVIEW.md) (OVERVIEW, MAKE-A-FIGHTER, TESTING, CONTRIBUTING) and
  the learning chapter [learn/15-engine-and-registry.md](learn/15-engine-and-registry.md); ENGINE.md v2,
  PACKAGE-FORMAT.md v1.1 (registry fields), owner_tables.json `phase2_target` → done/pending per entry.

## Order and parallel work
- Done: **P2.0** oracle + inventory, **P2.1** ABI draft (+ Claude review), **P2.2** registry builder, **P2.6** flag/id map,
  research for P2.3 / P2.4 / P2.5 / P2.7 / P2.9 / P2.10 (notes/phase2/).
- **DECIDED 2026-10-20 (Claude, on Mat's go-ahead; Codex review still welcome) — next, in parallel:**
  (a) **P2.4 step 0** = infrastructure + **EXRUN pilot** (XSTB header at 0x089A8B24, REG_ROW, EXTRA.REG loader, stub
  writer, status v2 counters, `equiv.py --allow-site`) — running 2026-10-20 (EXRUN pilot helper);
  (b) **P2.3 steps 1-2** = installer row generator (equiv IDENTICAL), then the two in-place name rewrites (C1, C2).
- Then: rest of P2.3 (pictures, Museum viewer, OQ face, gates, BGM bound, visibility gate) once the pilot has freed
  space / the menu gap is proven; P2.4 steps 1-4 (TRI first, it frees the stub home). After those: **P2.5** (DONE 2026-10-22) **+ P2.7** →
  P2.8 → P2.9. P2.11 decision any time (M). P2.12 after P2.8 (the pilot disc may go to the Vita earlier as a stub
  check). P2.13 last.
- **Fallback:** if a site resists generic code, keep its transitional patch and give it a registry-driven owner
  number instead of 33 (still no per-fighter code). If the real-PSP gate fails, ship engine discs as PPSSPP-only
  until fixed; the Phase-1 release is unaffected.
- **Exit criteria:** P2.8 equivalence + acceptance PASS; P2.9 PASS; 0 owner-33 constants in code; Mat's real-hardware
  (Vita) result (or accepted as pending).

## Risks
- Menu regressions everywhere a lookup replaces a constant → every P2.3 disc gets a vanilla-fighter control check on
  the same screen (lesson §F-5).
- Runtime code writes (stubs) on real PSP CFW — same class as P0.7. 2026-10-20: P0.7's live hook works on the Vita,
  so the class is proven; the stub table itself is still untested on hardware. Watch per-frame cost (menu fps lag on
  the Vita with test353): every hook in a per-frame path must be cheap.
- Save compatibility: each extra owner costs a friend-card slot; owner 35+ needs save relocation (out of scope).
- Cosmos story scene: **confirmed statically 2026-10-20** — story loads Cosmos by id, but `.cosx/.exex` are re-resolved
  by (owner, costume) → fix F6 (2 data bytes, part of P2.9) + one runtime check; tool tools/qa/objentry_resolve.py.
- Capacity: owner 34 fits the unlock table and objentry today; eqpm needs the heap loader or preset −1; the save
  format and the Opponent Info / name-key tables end at owner 34 (35 = hard limit without save work).
- Docs drift: manifest notes can be stale (EX run 1.1 vs built 1.40) → registry values come from built bytes.

## Out of scope
- Grid page 2 / more than 34 select cells (**Phase 3**). Memory Stick drop-in DLC (**Phase 4**). Owners ≥ 35 and a
  save-format redesign. New real fighters (Riku etc.): asset work, planned separately once P2.9 passes.

## 5. Status (owners update this table)
| task | status | owner | evidence |
|---|---|---|---|
| P2.0 oracle + inventory | DONE (static) 2026-10-20 — oracle R4 frozen: dumps/ULUS10566-P2-oracle-R4.iso (read-only, 9d311d17…205f) + packages/sora-R4 (read-only, 6cec661e…749b, UNMATCHED 0, REPRODUCES 255/255); inventory v2 = 86 owner-specific places, all byte-checked (+opp_info_name, OQ consts; EX_SND not built; menu_clock global) | Claude (P2.0 helper) | notes/dlc-phase2.md §P2.0 + "Owner-33 inventory v2"; tools/pkg/owner_scan.py; dumps/p2-oracle-owner-scan.json |
| P2.1 engine ABI | DONE (static) 2026-10-19; **reviewed 2026-10-20 by Claude** (High fixes folded into ENGINE.md "v2 design changes"); Codex review still requested | Claude (P2.1 ABI helper; review: P2.9/P2.10 helper) | docs/ENGINE.md §Registry + stubs v2; notes/dlc-phase2.md §P2.1; notes/phase2/P2.1-review.md |
| P2.2 registry builder | DONE (static) 2026-10-19 | Claude (P2.2 helper) | tools/dlc/registry.py + registry/sora.json, test34.json, tests/cases.json; selftest PASS; notes/dlc-phase2.md §P2.2 |
| P2.3 lookup conversions | **DONE 2026-10-21**: steps 1-2 (2026-10-20) + home decision (OXT in the freed EBOOT block) + pictures / Museum / OQ face / flag gate + BGM fallback (discs P23-pictures / museum / oqface / flags, equiv IDENTICAL by id, PPSSPP A/B + controls + strict PASS); owner-33 compares 0 on the final disc; engine 2.5.0; visibility gate open (P2.8/P2.9) | Claude (P2.3 research / lookups helpers) | notes/phase2/P2.3-lookups.md, P2.3-home.md, P2.3-pictures/museum/oqface/flags.md |
| P2.4 behaviour modules | RESEARCH DONE (static) 2026-10-20; step 0 (EXRUN pilot) DONE 2026-10-20; **step 1 (TRI + EE_HIT) DONE 2026-10-21 on disc tri2 (P24-tri JIT freeze fixed: aligned stack for game calls, engine 2.1.1)**; **step 2 (Reflect cave + HELM) DONE 2026-10-21 on disc P24-reflect (overlay back to clean size)**; **step 3 (SHIELD + EE_B freed) DONE 2026-10-21 on disc P24-shield**; **step 4 (item ownership + menus) DONE 2026-10-21 on disc P24-items → P2.4 DONE** | Claude (P2.4 helper; pilot: EXRUN pilot helper; step 1: P2.4 step-1 helper + freeze helper) | notes/phase2/P2.4-behaviour.md; notes/phase2/P2.4-exrun-pilot.md (pilot); notes/phase2/P2.4-tri.md (step 1, §8 freeze fix); notes/phase2/P2.4-reflect.md (step 2); notes/phase2/P2.4-shield.md (step 3); notes/phase2/P2.4-items.md (step 4, §10 hand-over) |
| P2.5 save slots | RESEARCH DONE (static) 2026-10-20; **DONE 2026-10-22** (P25-saves 8f163258…, notes/phase2/P2.5-saves.md) | Claude (P2.5/P2.7 helper) | notes/phase2/P2.5-P2.7-saves-capacity.md §A |
| P2.6 allocator + vanilla writers | DONE (static: writers list + free map + pools; allocator script + R 100%-save dump open) | Claude (P2.6 helper) | tools/dlc/flag_writers.py → flag_map.json, tools/dlc/id_spaces.py → id_spaces.json, notes/dlc-phase2.md §P2.6 |
| P2.7 shared capacity | RESEARCH DONE (static) 2026-10-20; **DONE 2026-10-22** (grid rows moved + 34-entry cap, one generic installer-word writer, title call generated, registry rules; disc P27-capacity 387b0a7e…; static + host + PPSSPP A/B + 34th-cell scratch PASS) | Claude (P2.5/P2.7 helper; P2.7 capacity helper) | notes/phase2/P2.5-P2.7-saves-capacity.md §B; notes/phase2/P2.7-capacity.md |
| P2.8 Sora on the engine | **IN PROGRESS; E1-E3 BUILT 2026-10-22** (+ E4/E5 by P2.5/P2.7): engine package + format 1.1 Sora package + layout C; P28-soraC = P27 content (equiv IDENTICAL, 0 code words), vs oracle IDENTICAL 1217 words; PPSSPP PASS (idx + reg + stubs live, EX run 1.40, Reflect, Trinity, menus, menu cost); Q-P28-M1 / M2 = yes (Mat). Open: E6, E7, E8, bytes.v1 codecs, full acceptance runtime + Vita | Claude (P2.8 helper, P2.8 build helper) | notes/phase2/P2.8-sora-package.md, notes/phase2/P2.8-build.md; tools/pkg/engine/make_engine_pkg.py, rostergen.py, layoutc.py, pkg11.py |
| P2.9 owner-34 test fighter | RESEARCH DONE (static) 2026-10-20: recipe, Cosmos risk + fix F6 (static PASS), test34.json fixed; blocked by P2.3/P2.5/P2.7/P2.8 | Claude (P2.9/P2.10 helper) | notes/phase2/P2.9-testfighter.md; tools/qa/objentry_resolve.py |
| P2.10 acceptance list + test kit | **static kit DONE 2026-10-21** (`tools/qa/acceptance/`: run_static.py + profiles, stack_rule.py A13, engine_disc.py A14, runtime_plan.py); list reviewed + folded into PACKAGE-ACCEPTANCE.md 2026-10-22; runtime dry run TODO | Claude (P2.0 helper list; P2.9/P2.10 helper kit research; P2.10 kit helper) | docs/PACKAGE-ACCEPTANCE.md; notes/phase2/P2.10-kit-built.md; notes/phase2/P2.10-testkit.md; tools/qa/runtime/snapshot-20261020/ |
| P2.11 delivery with packages | DECIDED 2026-10-19 (b), RELEASE-POLICY update TODO | Mat | – |
| P2.12 real-PSP gates | PARTIAL 2026-10-20: layout B on the Vita (Adrenaline) works = unsigned EXTRA.PRX loads, live file hook serves Sora, plain EBOOT runs (P0.2/P0.7 proven on hardware); test353 V1-V5+V8 PASS; open: menu fps lag, engine discs (after P2.8) | Mat | docs/TEST-ON-VITA.md |
| P2.13 docs | in progress 2026-10-22: README, ROADMAP, docs/modding/, learn/15, glossary | Claude (docs helper) | docs/modding/, docs/learn/ |
