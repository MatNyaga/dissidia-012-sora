# DLC research: could new fighters be "DLC packages"? (Claude DLC research helper, 2026-10-18)

Mat asked: *"Right now we make many changes to insert one character. What if I want more? Could an external
character be a DLC package (with a modified ISO, of course)? Seems more convenient and cleaner."*
Clarification (Mat via coordinator): a DLC character must have **everything Sora has**, as complete as possible.

Static research only (decompiles, ELFs, the clean dump and test338). Nothing was written to any ISO and the emulator
was not used. Addresses and proof are in the **Technical appendix** at the end.

---

## TL;DR (the short answer)

1. **The game's own DLC system can't add a fighter.** It was built for exactly two things: **extra costumes**
   and **extra music**. At boot the game looks on the Memory Stick for up to 256 small "costume row" files and
   20 + 20 "music" files (that's the long list of `FILE NOT FOUND ….edat` lines in the PPSSPP log). A costume file
   can only **overwrite one existing row** of the model table; it can't add a new owner, a moveset, menus or voices.
   Even for DLC costumes the game always loads the battle file (`.objx`) from the disc.
2. **But the idea is right.** The clean way to have many new fighters is:
   - patch the ISO **once** with *generic* engine changes (every place that today says "if owner is 33" becomes
     "look this owner up in a table"), and
   - make each fighter a **self-contained package folder** (model, battle file, voices, pictures, text, table rows,
     plus a small "registry row" that fills those tables), installed by **one generic tool**.
3. **The packages should be merged into the ISO by a tool at build time first** (cheap, safe, works on a real PSP),
   not loaded from the Memory Stick at runtime. Runtime Memory Stick DLC is possible later, but needs much more code.
4. **Two hard walls block a second fighter even with today's approach:**
   - the disc's file index is almost full: **74 free file slots left, Sora used 136**;
   - **code room is gone**: every safe spot for new game code is used up.
   Both are fixable once, and the fix is the same for "Riku today" and "the package system".
5. **The big unlock for code room is our own code module** (a `.PRX` file on the disc that the game loads at boot
   with its own module loader). That gives us as much code space as we want, written in C instead of
   hand-assembled MIPS. Needs a PSP compiler set up (not installed yet) and one probe test on PPSSPP + a real PSP.
6. **Realistic slot count:** owner 34 (Cosmos's unused fighter number) is usable like 33 was; owner 35 still fits the
   save's stat arrays; beyond that the save data, Records list and select grid need real relocation work. The
   **select grid is full** (Sora took Chaos's cell), so each extra fighter needs either a bigger grid (unknown size of
   work) or to replace someone.
7. **Riku cost:** (a) today's way = copy-paste ~60 scripts and hit both walls plus a dozen "only one extra fighter"
   limits; (b) package way = a one-time engine phase (roughly 1.5–3 weeks of helper work) and then Riku is mostly
   asset work (model/animations/voices/effects). Asset work is the same either way; (b) saves the plumbing and makes
   fighter #3, #4 … cheap.

---

## 1. How Dissidia 012's DLC really works (plain English)

### 1.1 Where the game looks
At boot (when the menu program starts) the game runs a little loader with **three lists**:

| list | file names it asks for (internal) | how many | what one file holds |
|---|---|---|---|
| costume rows | `dlc/obj/dlc_000oe.bin` … `dlc_255oe.bin` | 256 | **one** 68-byte row of the model table (objentry) |
| music rows | `dlc/bgm/dlc_000.bin` … `dlc_019.bin` | 20 | a list of 44-byte music-table rows |
| music names | `text/jp/dlc/bgm_000t.bin` … `bgm_019t.bin` | 20 | the names shown for those tracks |

Plus one special check: the disc has `dlc/aerith.txt`; if the Memory Stick has a matching `dlc/aerith.bin`, Aerith
(the assist) is unlocked. (That's why our assist fix had to stop the game dropping owner 33 "unless Aerith is
unlocked".)

**File names on the Memory Stick are scrambled the same way as the disc's file index**: the internal name is
lower-cased and run through a checksum (CRC-32), printed as 8 hex digits. So `dlc/obj/dlc_000oe.bin` becomes
`ms0:/PSP/GAME/ULUS10566/a590d742.edat`. That is exactly the ~296 `FILE NOT FOUND` lines PPSSPP prints at boot.
Everything is skipped on demo/"no DLC" builds (two flags read from `language.bin`).

### 1.2 What the files do once loaded
- **Costume row:** the loader finds the row in the model table **with the same id** and **overwrites it**. It can't
  append (the table is a sorted, fixed list searched by id; a row with a new id would make the game write to
  address 0). So the disc must already contain a placeholder row for every future DLC costume. (The 13 `*_4P_PUB`
  rows on the disc match the real DLC 4th-costume list, so they are very likely those placeholders.)
  The overwritten row says "costume 4" and sets a **"load from Memory Stick" flag** (row byte +9). From then on
  that costume's `.gmo` (model), `.cosx` and `.exex` are read from the Memory Stick (same scrambled names, e.g.
  `obj/P_SEV100_4P.gmo` → its CRC). **The battle file `.objx` is never taken from the Memory Stick for fighters**
  (the code explicitly skips names starting with `P_`).
- **Music rows:** these really are **added** (appended, up to 256 tracks total), with their names, and the music file
  itself is read from the Memory Stick (`bgm/<name>`). This is the only "true add" in the DLC system.
- Costumes 4–12 then appear by themselves: the game offers costume k if any model row has costume number k (that's
  how our Valor/Wisdom/Final outfits work without DLC files).

### 1.3 Encryption
- The files are **EDATs** (Sony's PSN DLC wrapper). The game opens them with the "DRM" open flag and then calls
  `sceNpDrmEdataSetupKey`; if that fails the file is treated as missing. The 16-byte game key (licensee key) is in
  the EBOOT and set at boot with `sceNpDrmSetLicenseeKey`.
- PPSSPP decrypts real EDATs itself. Fan costume packs for 012 (e.g. the old Sora-as-Cloud costume packs) were made
  by re-wrapping files as EDATs; whether a self-made EDAT passes on a real PSP without a plugin is **not proven**.
- **Since our EBOOT is already plain (decrypted), we don't need EDATs at all**: 2 open-flag words and 5 "setup key"
  checks can be patched so the game reads **plain files**. Small, safe, well-understood change.

### 1.4 What DLC can and can't add (native system)
| can (natively) | can't |
|---|---|
| a new costume for an existing owner (overwrites a placeholder row; model/cosx/exex from Memory Stick) | a new owner (fighter), a new battle file, moves, abilities |
| new music tracks + names | voices, voice lines, subtitles, text, menus, pictures, unlock flags, catalog items, AI, assist |
| unlock Aerith (assist) | anything in the per-owner tables listed in §1.5 |

So: **reuse the native system only for costumes and music** (e.g. Sora's outfits 4–6 or KH2 music could even ship
as Memory-Stick files). For whole fighters we need our own system.

### 1.5 The hard limits a new fighter runs into (what we had to patch for Sora)
"Owner" = fighter number (Sora = 33). Owner is a byte everywhere (max 255) but almost every table is sized for
32–35 owners.

| limit | size | Sora's state | what a 2nd new fighter needs |
|---|---|---|---|
| **disc file index** (PACKAGE_INFO, fixed RAM buffer) | 11,253 files max | 11,179 used (Sora +136) → **74 left** | 🔴 code: bigger index or 2nd index |
| **free code room** | battle cave 512/512, EBOOT dead code ~all used | ~30 loose words left | 🔴 new code home (PRX) |
| model table (objentry, RAM buffer 0x13D30) | 1,194 rows | 1,173 (Sora 12 rows) → 21 left | 🟠 ~9–12 rows per fighter → 1 more fits, then code |
| character params (chrp) | 34 rows (owners 1–34) | row 33 reused | owner 34 has a row; 35+ need a bigger table |
| unlock table (EBOOT, −1 terminated) | 32 rows + 28 zero bytes = room for exactly 1 more row | Chaos's row → Sora | 🟢 one more fits; then relocate |
| unlock / item / AI-item **masks** | 32 bits, bit = (owner−1)&31 | Sora shares bit 0 with WoL | aliasing: 34 = Garland's bit → code checks |
| music owner mask | 64 bits | bit 33 | fine up to owner 63 |
| Quick Battle grid table | 32 rows + random, index check `< 0x21` | Sora replaced Chaos's row | 🔴 grid is full: expand (layout + code) or replace someone |
| "Characters" panel owner list + sprites | 31 owners, sprites for 1–32 | Sora borrows owner 32's sprite | 🔴 no sprite left |
| picture runs in 5 menu scenes | 32 pictures, `owner−1` | 13 sites remap 32 → 245 | 🟠 generic remap table |
| saved fighter records | 31 + friend-card trick | Sora in friend card 24 (limit 25→24) | each fighter costs 1 friend-card slot |
| save stats (wins/losses per owner) | "as" block owners 0–35, "vs" block 0–34 | 33 fits | 34 fits both, 35 only one, 36+ need save work |
| Records list | 32 entries | Chaos's append → Sora | 🔴 array must grow (code) |
| name tables by owner | 33–35 entries (6 tables) | patched for 33 | 34/35 rows mostly padding → patch again |
| ability table (ablt) runtime cap | 832 rows (one EBOOT word) | 809 (Sora 23) | raise the cap again (easy) |
| initial equip presets (eqpm buffer) | room for exactly 1 extra | used by Sora | 🟠 buffer move or reuse a preset |
| player icons (uicn buffer) | 420 | 417 | 3 left |
| Jukebox voice groups | 33 groups | Sora has none | data (add group) |
| CPU brain owner table (seco) | data, appendable | row appended | fine |
| fighter load budget | ~2.5 MB work block per object | Sora model ≈ limit | same for every fighter (assets) |
| model costumes | 12 per owner (1–3 disc + 4–12 "DLC slots") | 6 used | fine |

---

## 2. What a NEW fighter needs today (the full Sora list)

Legend: **D** = pure data (files/rows), **C** = game code we wrote (owner-33-specific), **D+C** = data plus a
code fix for "owner 33 missing from a table".
Package column: **P** = ships in the package as data; **H** = handled by a generic hook patched once, the package
just supplies a registry/table row; **B** = character-specific behaviour code (a "behaviour module", parameterised);
**✗** = hard limit / not feasible without big work (workaround given).

| # | Sora feature | today | package design |
|---|---|---|---|
| 1 | Owner slot: chrp row, objentry rows, name key, unlock row, save record | D+C | P rows + **H** (registry: owner → key, record slot, preset, unlock flag) |
| 2 | Model + **6 outfits** (Drive variants) + per-outfit `.cosx`/`.exex` (EX banner/aura), HUD face per outfit | D | **P** (objentry rows + files). Outfits 2/3 need unlock-row costume flags (H). Museum viewer outfits 4+ need the viewer's owner table (H). Native DLC could even deliver outfits 4–12 from the Memory Stick |
| 3 | Moveset: comb/plya/atkp/magi/p_se/hit shapes/brat inside the `.objx`, long chains, HP moves, magic | D | **P** (it's all inside the fighter's own battle file) |
| 4 | Abilities: ablt rows, names/descriptions, chrl learn levels, amas (Customization), eqpm start kit, default preset table | D+C | **P** rows; ablt cap + eqpm room + preset table = **H** |
| 5 | Effects: own FEP/FEPA id, own texture keys, KH2 effects (Reflect barrier, Magnet, Firaga…), 16-byte alignment + dense serial rules | D | **P**. Installer **allocates per-owner id ranges** (FEP id, texture key prefix, sound bank ids) and runs the effect-rule checks automatically |
| 6 | Sounds: own snd_ bank + ids (219000/219100), KH2 swing/finisher/spell sounds | D | **P** with per-owner sound-id range from the installer |
| 7 | EX Mode: weapon swap (wep1), EX start animation, EX damage ×1.5 | D | **P** |
| 8 | EX Mode run speed ×1.40 (EXRUN) | C | **H**: per-owner multiplier table (0 = off) |
| 9 | EX Reflect guard (+ HP-projectile refill, Protect Belt gain, voice "Back off!") | C (+D) | **B** "reflect guard" module, switched on per owner with parameters; voice/animation = P |
| 10 | EX Burst: controller choice (chrp +6/+7), Trinity controller TRI (own code), bar-full voice, yellow BREAK gauge, banner text, burst animations | D + C | Choice = P. A fighter that uses one of the game's **20 existing controllers** needs **no code** (pure P). A custom controller like TRI = **B** module + **H** dispatcher (owner → controller code). Gauge look/texts = P |
| 11 | CPU AI: brain owner row (seco), brat weights, styles, reaction rows, acab auto-equip, magi threat tags | D | **P** (installer appends rows to the shared AI file) |
| 12 | Assist version: assist.bin row, `_a.objx`, `_A.gmo` ×3, assist voice bank, eqaa preset, kind-8 objentry rows, "drop owner 33" fix | D + C | **P** files/rows; drop check = **H** (3 words become "any registered owner") |
| 13 | Character-only equipment: items 678–681, level scaling, special effects (EX gain, ×1.5 reflect, EX drain) | D + C | Item rows = P; effects = **B** (item → effect table); "Sora only" equip = **H** (owner table, because the 32-bit equip mask aliases WoL) |
| 14 | Voice: grunt bank, voice_load list (VOLD), spoken lines `.at3`, subtitles, extra lines | D | **P** (files by path) — but each `.at3` is one disc file → the file-index wall (§1.5) |
| 15 | Vs-lines both directions (his lines vs everyone + everyone's line vs him) | D | **P**: installer merges VOLD rows into **other fighters'** voice lists (shared files) |
| 16 | Title call (Sora calls the title) | C (bound + table) | **H**: generic table indexed by caller id |
| 17 | Menus: select grid cell | D+C | ✗ today (grid full) → **H** after grid expansion (biggest unknown) |
| 18 | Portraits, faces, name banners loaded by name (`p_<key>_*.gim`, HUD, VS, encount, arcade) | D | **P** |
| 19 | Pictures picked by number in shared menu packs (Quick Battle, story party, party setting/arrange, Original Quest, Shop, Level Adjust, Customization) | D + C (13 remap sites) | Pictures = **P** (installer appends to packs); remap = **H** (owner → picture index table) |
| 20 | Customization pages: ability text, □ command charts, Battle Tips, EX Mode page | D (+C for tables) | **P** + **H** where a per-owner table exists |
| 21 | Museum: Character Files record + 3D viewer, Player Icons, Jukebox | D | **P** (data files grow; loaded by size) |
| 22 | Records (wins/losses/time) | C | ✗ for more than one new fighter until the 32-entry list grows (**H**) |
| 23 | Friend Card names/icons, Ghost names | C | **H** (name-by-owner tables) |
| 24 | PP Catalog: unlock purchase, icons, avatar, BGM items | D | **P** (installer allocates unused unlock flags) |
| 25 | Labyrinth face, party frames, Shop/Level Adjust art | D+C | **P** + **H** (owner rows past 33 are other data) |
| 26 | "Characters" panel (Artifacts/Equipment/Shop □) | C | ✗ → **H** after giving the panel more sprites/cells |
| 27 | Music: KH2 tracks, auto-music by owner bit | D | **P** (64-bit owner mask fine to owner 63) |
| 28 | Save data: record, stats by owner, unlock flags | D+C | **H** (record slot allocator); owners > 35 ✗ without save work |
| 29 | Original Quest menus: slot face + full name, party banner, party title (RR-18, 2026-10-19: owner 33 showed a black face, "Play as this character?", a dark red banner, "Warrior of Light") | D+C | Fixed for Sora by spot33_oqslot (test352): full name = text entry 122 in 4 packs, face = 39th handle built in FUN_08a62530 (handle list was full at 38), banner/party row → existing pictures. Package: names/pictures = **P**; owner → full-name (0x08A544E0) / face (0x08A54638) / banner (0x08A6B394) / party row (0x08A6CAD0) = **H**; the face-handle list needs room for N extra fighters |
| 30 | Labyrinth / any "opponent-owner-only" BGM pool (mode 7) | C | **H**: empty pool → stage music fallback (spot33_bgmfallback); a fighter without own tracks then needs nothing |
| 31 | Character-select style blurb ("[Keyblade Master] …") in 5 text packs | D | **P** (entry = owner index; spot33_selectblurb) |
| 32 | Purchase/unlock flags (BGM, icons, avatar, Encounter Voice) and the Jukebox "show all" flag 1372 | D+C | **H**: installer allocates from a *verified-free* block (vanilla writes 1250-1262 itself); list gates skip 1372 for package flags (spot33_jukeboxgate) |
| 33 | Max CP growth row (system.bin `grwp`, 0x1C B, linear owner scan; RAM buffer has room for 64 rows) | D | **P** row appended by the installer. Missing row = NULL read in battle setup → crash on real hardware (Vita C1-2858-3), silent in PPSSPP. Sora: spot33_grwp (test353) |
| 34 | Opponent Info / battle-loading name (battle overlay s32 table 0x08AFB6E8, 8 B per owner = name + manikin name index into the 63-name list; −1 = no name) | D (in code image) | **H** (registry lookup) / **P** row today. Missing row = blank name, no crash. Sora: spot33_oppinfo (R4 test, RR-22 #5) = (63, 63); owner 34 row also −1 |

Count: of Sora's ~61 build scripts, about **45 are pure data** (they edit his own files or append rows) and
**~20 patch game code** (EBOOT / battle overlay / menu overlay; list in appendix E). Almost every code patch is "owner 33 is missing
from a fixed table" or "only owner 33 does X". That is exactly what a once-only generic patch can absorb.

---

## 3. Feasibility of "external character packages"

### 3.1 The design in one picture
```
 clean ISO ──(once)──► ENGINE PATCH ──► + package "sora/" ──► + package "riku/" ──► ISO for playing
                       • plain EBOOT                 (installer)            (installer)
                       • our code module (PRX)
                       • owner-generic hooks + empty registry
                       • extra file index
```
- **Engine patch (once):** everything generic. Contains no character.
- **Package (per fighter):** a folder with a manifest (owner number, key like `sev120`, names, ids it needs), its
  files (objx, gmo ×N, cosx/exex, voice bank + list + `.at3`, GIMs, music), its table rows (ablt, amas, eqpm,
  chrl, acab, AI rows, assist row, Museum record, catalog items, icons, VOLD rows for other fighters), and one
  **registry row** (picture indexes, save slot, feature switches: reflect guard on/off, EX speed, burst controller…).
- **Installer:** one generic tool (what the 61 `spot33_*` scripts do today, but parameterised by the manifest),
  with the same guard rules we use now (re-runnable, `--dry`, accepts stock or own output).

### 3.2 Where would packages live?
| option | how | good | bad |
|---|---|---|---|
| **A. merged into the ISO by the installer (recommended first)** | installer writes files + rows into the ISO | no runtime code for loading; works on real PSP; same as today's proven path | still "an ISO per roster" (release = one xdelta per roster) |
| B. extra container file on the disc (`USRDIR/DATA/EXTRA.BIN`) + extra index | our hook: if a file isn't in the disc index, look in our index and read from EXTRA.BIN | removes the 74-file wall; packages become 1 file each | needs the code module (≈6 hook sites in the file reader) |
| C. Memory Stick (`ms0:/PSP/GAME/ULUS10566/…`, like real DLC) | same as B, but the container is on the Memory Stick, plain files (EDAT check patched) | real "drop-in DLC": base ISO never changes | every table that lives in a fixed RAM buffer must be merged at boot; menu picture packs need a merge hook; much more code and testing |
| D. reuse the game's own DLC loader | – | only costumes/music | can't add a fighter (see §1) |

Recommendation: **A now, B as part of the engine patch (it fixes the file wall anyway), C only if Mat really wants
drop-in DLC later.**

### 3.3 How many extra fighters are realistic?
- **Owner 34** (`org800` = Cosmos's number) is the next easy slot: it has a chrp row and save space, no battle file,
  and isn't playable. Caveat: Cosmos's own model rows (1338/1339) stay; our rows must come first in the lookup or use
  their own ids (check the story still shows Cosmos).
- **Owner 23 is NOT free:** it's Chaos (story boss; files `p_org200_00..02`). Sora reused Chaos's **grid row**,
  **unlock row**, **unlock flag 925** and **catalog item**, not owner 23 itself.
- **Owner 35** fits the "as character" stats block but not the "vs opponent" block; **36+** need save relocation.
- **Hard ceiling with the generic engine:** about owner 63 (64-bit music mask), realistically **2–4 extra fighters**
  without touching the save format, and only once the grid can grow.
- **Memory:** fighters on the disc cost no RAM until picked (each battle loads 2 fighters + 2 assists, each with the
  same ~2.5 MB budget). Per fighter the RAM tables grow a little (model rows 68 B, abilities 40 B, index 12 B/file).
  Disc size: test338 is 1.81 GB; Sora added ~58 MB (part of it is dead old copies from in-place rebuilds — a fresh
  build is smaller). Disc file offsets can go up to ~2 GB past PACKAGE.BIN's start, so space is fine for several fighters.

### 3.4 The code-room problem and the fix
- Today: battle-overlay cave **full**; EBOOT dead functions **used** (TRI 519/523 words; the second one has EXRUN +
  the reserved EX-gain block); free leftovers ≈ 30 words; the EBOOT gap after 0x089DD3C0 is not loaded.
- Every hand-written routine also costs assembly by hand (no Allegrex C compiler on this machine).
- **Fix: our own code module.** The game already loads `libfont.prx` / `libsuppreacc.prx` from
  `USRDIR/DATA/MODULE/` with its own loader (EBOOT FUN_0886eebc). One extra call at boot loads `EXTRA.PRX`.
  It stays in memory for menus *and* battles (unlike the overlays), can be written in **C**, and gives all the room
  we need for the generic hooks, the extra file index, the registry and per-fighter behaviour modules (TRI, reflect…).
  Hooks into the game stay tiny (`jal` into the module). Unknowns to probe: free RAM for the module (expect tens of
  KB needed), loading an unsigned PRX on a real PSP with CFW (same situation as our plain EBOOT, expected OK).
- Without a module: more probe-proven dead code could be found (the method in notes/ex-burst-controller.md §21), and
  the menu overlay is 40 KB smaller than the battle one (gap 0x08B59258–0x08B63170) — but the overlay header points
  at that gap, so it may be menu heap. Only small wins; not enough for N fighters.
  (2026-10-20, P2.3 research: that header word is the end of the overlay's constructor list, not a heap pointer, and
  no menu code refers into the gap, so it is the best home for P2.3 tables/helpers. Still to confirm with a PPSSPP
  write watch through the menus: notes/phase2/P2.3-lookups.md.)

### 3.5 How owner-33 code generalises to N fighters
Today each of our routines starts with an `owner == 33` compare (against 0x21). Generic version:
```
feat = FEATURE_TABLE[owner]      ; one byte per owner (64 bytes for owners 0..63)
if !(feat & REFLECT) → vanilla path
params = PARAM_TABLE[owner]      ; multiplier, item ids, controller id, voice slot…
```
- Cost: one shared lookup helper (~15–25 words) + tables (64 B per byte-flag table, 256 B per word-param table).
  The vanilla hook sites stay a single `jal`. The routines themselves (TRI ~370 words, reflect/EE ~250, items ~100,
  EXRUN 25) are written once and read their numbers from the table.
- Features that are **Sora-specific logic** (Trinity Limit's timing, KH2 Reflect barrier rules) stay "behaviour
  modules"; a new fighter either reuses one with other numbers, uses a vanilla controller (no code), or gets its
  own module (new code — easy only with the PRX).
- Menu fixes (owner−1 picture remaps, name tables, Labyrinth rows, panel sprites, Records, title call) become
  **lookups in the registry** instead of special cases for 33.

---

## 4. Recommendation

### 4.1 Phases (rough helper effort, assuming the current pace)
| phase | what | effort | risk |
|---|---|---|---|
| 0. Probes | PRX load probe (PPSSPP + real PSP), free-RAM check, Cosmos-row check for owner 34, grid layout study (how many cells the scene really supports), plain-file DLC patch probe | 1–2 days | low |
| 1. Tooling | turn the 61 `spot33_*` scripts into one installer that takes a package manifest (owner, key, ids); re-build Sora **as a package** and prove the result is byte-identical to the current build | 3–5 days | low (pure refactor, checkable by diff) |
| 2. Engine patch | PRX toolchain + module; registry; replace every owner-33 special case with lookups; extra file index (fixes the 74-file wall); unlock/item mask aliasing; record-slot allocator; Records/name/panel/Labyrinth/title tables generic; eqpm/objentry/ablt room | 5–10 days | medium (touches menus everywhere → full menu regression pass) · plan: `docs/PHASE2-PLAN.md` (draft 2026-10-19), inventory `notes/dlc-phase2.md` (80 owner-33 sites) |
| 3. Grid | more cells on Quick Battle / story / party grids (layout + 33-index bounds) | 2–5 days, **least known** | medium-high |
| 4. (optional) Memory Stick DLC | load packages at boot from `ms0:` and merge tables in RAM | 3–6 days | high |

### 4.2 What Riku would cost
| | (a) today's approach | (b) package approach |
|---|---|---|
| assets (model fit, KH2 animations, moves, effects, voices, menu art) | same | same — this is most of Sora's 6 days |
| plumbing | copy/adapt ~60 scripts to owner 34, every table again | write one manifest + registry row |
| blockers | 🔴 file index (needs ~130 files, 74 left) · 🔴 no code room for his EX Burst/specials · 🔴 grid full · 🔴 char panel sprite · 🔴 Records list · 🟠 eqpm/objentry/uicn room · 🟠 unlock/item bit = Garland's | solved once in phases 2–3 |
| fighter #3 | all of the above again, and the walls get worse | manifest + assets only |
| verdict | possible for ONE more fighter only with the same wall fixes, and messier each time | ~2–3 weeks up front, then each fighter ≈ asset work only |

**Recommendation:** do Phase 0 + Phase 1 next (cheap, no risk, and it makes Sora's build cleaner too: Mat's
"one tool from a clean ISO" wish). Decide on Phase 2 after the PRX probe. Don't spend time on Memory-Stick DLC
until the generic engine exists — it adds runtime risk for little extra benefit over "install a package with a tool".

### 4.3 Risks
- **Real PSP:** module loading and plain files must be tested on hardware (PPSSPP is more forgiving).
- **Save compatibility:** each extra fighter takes a friend-card slot (lowering the limit hides/overwrites
  friend card 23, 22 …). A full save redesign is much bigger.
- **Menu regressions:** the generic hooks touch many vanilla screens; needs a full menu pass with vanilla fighters.
- **Data Install:** the game's optional "install to Memory Stick" layer caches disc files by index entry — test with
  install on/off.
- **Mirror/cross matches:** with N fighters the id ranges (effects, sounds, texture keys) must never overlap — the
  installer must allocate and check them.
- **Legal/content:** each package carries KH-derived assets; same fan-mod caveat as Sora; release stays xdelta.

---

## Technical appendix

### A. DLC loader (EBOOT, VA = ELF file offset + 0x08803028)
- Name hash FUN_08861b84 = same as the disc index hash FUN_08871288 (CRC-32/BZIP2 of the lower-cased path,
  `tools/scripts/pkghash.py`), printed with `%08x` (0x089C8ED8) into 0x08B634EF.
- Directory FUN_08862678: `"%s/%s"` with `ms0:/PSP/GAME` (0x089C8EB8, ptr 0x089D5E90) and the game id
  DAT_089D6010 = language.bin +0x14 (set in FUN_08867bd4) → `ms0:/PSP/GAME/ULUS10566/<crc>.edat`.
- Name builders (vtable +0x14): FUN_08861f78 bgm `dlc/bgm/dlc_%03d.bin` (index < 0x14); FUN_088621a4 bgm text
  `text/jp/dlc/bgm_%03dt.bin` (< 0x14); FUN_08862288 obj `dlc/obj/dlc_%03doe.bin` (< 0x100); FUN_08862338 aerith
  `dlc/aerith.bin`; FUN_088626ac generic "any internal name" (used by the file manager when a caller asks for DLC);
  FUN_08862028 `bgm/%s`.
- Apply functions (vtable +0xC): FUN_08861ee0 bgm (count at +8, 0x2C-byte rows from +0x10 → FUN_0889f040 appends
  to the BGM table, max 0x100 rows); FUN_088620ac bgm names (→ FUN_0889f18c, 0x7E-byte name per (file, row));
  FUN_08862254 obj (→ FUN_08847068: bsearch FUN_08934944 by u16 id over objentry, memcpy 0x44 = overwrite).
- Vtables 0x089C8E70 (bgm), 0x089C8E88 (bgm text), 0x089C8EA0 (obj), 0x18 B each; installed by the menu overlay
  FUN_089dd4d0 (+0x1F8/+0x214/+0x230); stepped by FUN_08862450 / FUN_088625d4 / FUN_08861c64 (probe size →
  allocate → async open → read → apply; missing = next index). Skipped when DAT_089D5F20 ("prologus" demo) is set
  (FUN_089dd5dc). DAT_089D5F1F = no-DLC flag (language.bin +0x0E or FUN_08860d88) also gates the costume 4–12 loop.
- Aerith: a function in the EBOOT reads disc `dlc/aerith.txt` (pkg 6589) and ms0 `dlc/aerith.bin` EDAT (crc 2f9c99ab),
  compares byte-wise after a rotate/subtract/xor transform → unlock byte at 0x08BAEBB4 (set through FUN_0885c304 with DAT_089d4e14).
- Example hashes: dlc/obj/dlc_000oe.bin a590d742, dlc_001oe eac7bf53, dlc/bgm/dlc_000.bin 72385981,
  text/jp/dlc/bgm_000t.bin c5534db4, dlc/aerith.bin 2f9c99ab. Probe count per boot = 256 + 20 + 20.
- DRM: imports scePspNpDrm_user NID 0xA1336091 SetLicenseeKey (stub 0x089C5D58; called 0x08862664 with the 16-byte
  key at 0x089C8EC6) and NID 0x08D98894 EdataSetupKey (stub 0x089C5D50; calls at 0x08861DA0, 0x08863A9C,
  0x08863F88, 0x0889FE38, 0x088A0204). sceIoOpen (stub 0x089C5EA8) with flags 0x40000001 for DLC
  (the flag's high half is built at 0x08864570 in FUN_0886453c and 0x088646A4 in FUN_0886465c). Plain-file patch = those 2 flag
  words + 5 setup-key result checks. (Key bytes intentionally not copied here.)
- objentry +9 = "from Memory Stick": FUN_088450a8 gets "row byte +9 is non-zero" as its from-Memory-Stick argument for `gmo` (0x089C88A8), `cosx` (0x089C8898),
  `exex` (0x089C88A0); `objx` (0x089C8850) only if +9 set AND the name does not
  start with `P_`. Read path: FUN_088fe708 (with that argument) → FUN_08862984 (file manager vtable +0x3C = DLC read by name
  hash) instead of FUN_08862854 (PACKAGE).
- objentry buffer: 0x09AFEE58, 0x13D30 B (1,194 rows) loaded by FUN_08847158 (from PACKAGE, or from an archive
  member when given); battle.bin spec buffer follows at 0x09B12B88. Clean disc: 1,170 rows, byte +9 = 0 on all.
  test338: 1,173 rows (owner 33: 12 rows; owner 34: 1338 P_ORG800_1P / 1339 P_ORG800_1P_W; owner 23: 285–287
  P_ORG200_NORMAL/HARD/S_HARD).

### B. Disc file index (PACKAGE_INFO) and read path
- Loaded by FUN_08871938 into 0x09B26BC0, max 0x20F8C B (count 0x09B26BC8, rows 0x09B26BD0, 12 B: hash, sector,
  size|flags) → 11,253 rows max. Clean 11,043; test338 11,179 → 74 free.
- Lookup FUN_088713e4 (bsearch by hash; caches last name). Reads: FUN_088714f4 (sync), FUN_08871718 / FUN_08871818
  (async), size FUN_088716c8/FUN_088716f0. Sector field uses only the low 20 bits (`& 0xFFFFF`) → bits 20–31 free
  for a "container id" in an extra index (hook = lookup miss + the 3 read sites + size).
- Data Install layer: FUN_088704d0 / FUN_088701f8 (DAT_089D5FB4) look up the same index entry and read the
  installed copy first when installed.

### C. Code home candidates
- Module loader FUN_0886eebc (arguments: heap DAT_089D5F98, file name, 0) → `disc0:/PSP_GAME/USRDIR/data/module/%s`;
  existing calls for libsuppreacc.prx (in FUN_0886f23c) and libfont.prx.
  Disc folder `/PSP_GAME/USRDIR/DATA/MODULE` has LIBFONT.PRX + LIBSUPPREACC.PRX.
- Existing allocation: notes/ex-equipment.md (0x089A8B14 block), notes/ex-burst-controller.md §21 (0x089C1C8C TRI),
  docs/HANDOFF-TO-CODEX-20261017.md §5 (leftovers). Menu overlay ends 0x08B59258 (file size 0x17BD98) vs battle
  0x08B62F70; the menu overlay header word at 0x089DD4CC points at 0x08B59258 → probably heap start, unproven.

### D. Per-owner tables touched for Sora (where a 2nd fighter needs work)
EBOOT: unlock table 0x089D7BE0 (32 × 5 i32 rows, −1 at 0x089D7E60, zeros to 0x089D7E80 = room for 1 row; row 22 = (33, 925, 1, 1, 3623)); save owner list 0x089CBC98
(31) + spot33_save code (record = friend card 24, limit sites 0x088F523C/0x088F52A0); preset table 0x089CB7E8[owner];
names 0x089CC020[owner] (bound 35, FUN_088d6254), 0x089CF350[owner] (1..31); assist drop words 0x088F9CA4,
0x088F6C04, 0x08929060; ablt cap word 0x088B1CF0; uicn buffer 0xD24 (420 rows); eqpm buffer 0x09B59AF8..0x09B5DA00.
Menu overlay: QB grid 0x08A864D0 (12-B rows, 32 + random, bound `< 0x21` e.g. FUN_08a7f2b4; data at 0x08A8665C
follows); select/panel list 0x08B0119C (31) + cells 0x08B0121C + row sizes 0x08B0125C; panel parts per scene
(owners 1..32); owner−1 picture runs (5 scenes; 13 remap sites in spot33_menuart); party frame table 0x08B2D168
(31); Labyrinth 0x08B4173C (6-B rows); Records array obj+0x4B8 (32 × 0x10C) + list 0x08A40880 + icon table
0x08A40720; network names 0x08A23ACC (32); setup banner frames 0x08AA8864 (32); title call bound 0x089DEC04 +
DDD table; Museum viewer owner table 0x08A358FC; amas (system.bin); name key table 0x08B57FBC.
Battle overlay: name key table 0x08AFBC68 (33); names file 0x11E284; burst controller pick = chrp +6/+7; TRI/EE/
EXRUN/items owner-33 checks (spot33_reflect, spot33_exspeed, spot33_exitems).
Data (append-friendly): chrp (34 rows), objentry, ablt, amas, chrl, acab, eqaa, assist.bin, brai seco/brat,
collection_param (Museum), collection_voice_param (Jukebox, 33 groups), update_list_param (PP Catalog),
bgm_entry (64-bit owner mask), VOLD lists, menu packs (append entries), text groups.

### E. Scripts that patch code today (to absorb into the engine patch)
eboot_plain, roster_patch (menu tables), spot33_save, spot33_names, spot33_ablt_cap, spot33_amas (menu read),
spot33_qbpics (setup patch), spot33_menuart, spot33_charpanel, spot33_cmdlist, spot33_tips, spot33_museum,
spot33_ownername, spot33_catalog, spot33_assist, spot33_outfits (unlock row), spot33_reflect (TRI/EE/cave),
spot33_exspeed, spot33_exitems, spot33_soundids, spot33_vsvoices (title call), spot33_bgmfallback (Labyrinth
BGM, 2026-10-19), spot33_jukeboxgate (list gates vs flag 1372, 2026-10-19), spot33_oqslot (OQ menus, RR-18, test352). All others are data-only edits of
Sora's own files or appended rows.

---

## F. Lessons from the Phase 1 release tests (2026-10-19) — what the DLC engine must do for EVERY new fighter

Source: RR runtime tests on test348-351, RC2 (p17) and rr18; details in notes/dlc-phase1.md, registry rows in
tools/dlc/owner_tables.json.

1. **Free flags must be proven free against game code, not just data.** Sora's first KH2 flags (1249-1251, 1253/54)
   were set by vanilla itself (FUN_08a2b07c: Lv30/50/70 → 1250-1252, Lv100 rewards → 1253-1262), so items showed
   as bought on old saves. Fixed by moving to the block 1263-1270. The installer's flag allocator needs a
   "vanilla writers" list, and the engine must migrate flags when a package moves them.
2. **Vanilla "show everything" switches leak package items.** Flag 1372 lists every Jukebox row on 100% saves.
   Generic rule: every list gate the engine owns must ignore such overrides for package-owned flags.
3. **Opponent-owner pools can be empty.** Labyrinth (mode 7) plays only the opponent's own BGM; a fighter with no
   tracks there gave silence. Generic fallback to stage music = done once, covers all future fighters.
4. **Native behaviour first, then call it a bug.** Sora's "vs Feral Chaos" Jukebox row on flag 886 looked wrong
   but matches all 30 vanilla fighters. Check the vanilla pattern before "fixing".
5. **Original Quest has its own per-owner name/face/banner/title tables** (row 29 above). Every menu that shows a
   fighter needs a test with a vanilla fighter on the same screen as the control.
6. **Release path works for packages:** the app decrypts the player's own EBOOT (no game code shipped), the patch
   is a vcdiff from the clean US ISO, layout B keeps the game's Data Install working (RC2 smoke: 492 MB install
   COMPLETE, battle with installed data). A future "DLC pack" release can reuse this path unchanged.
7. **Installer builds:** Linux AppImage builds in Docker (Ubuntu 22.04 box). Docker storage is now on /data (a
   spinning disk): dpkg needs force-unsafe-io (in app/Dockerfile) and GUI tests need more time (BWAIT=900).
   Windows/macOS still need CI. GPL source sync before any installer is shared.
8. **Per-fighter acceptance list = the RR list.** For each new package, rerun: unlock/purchase on fresh and 100%
   saves, Jukebox/Museum/Records, Labyrinth BGM, select blurb, Original Quest (create/test/save/load/play/return),
   replay/ghost/Friend Card, assist in 4 contexts, EX lifecycle, Data Install on layout B, installer A/B/C.
10. **PPSSPP hides NULL reads; real hardware crashes.** system.bin `grwp` (Max CP growth) had no owner-33 row: PPSSPP
   read 0 for two years of testing, the PS Vita crashed on every Sora battle. Every per-owner table needs a row for
   every package owner. Tests: tools/qa/owner_rows.py (static) + PPSSPP strict mode (`--env=STRICT=1`) for every
   smoke + Vita V-list for release candidates. The package installer must append rows to ALL per-owner chunks
   (chrp, grwp, eqpm, acas, amas, chrl, ...), driven by the registry, never by hand.
11. **The battle overlay owns its own owner tables, even on "menu-looking" screens.** Quick Battle "Opponent Info"
   (before the fight) is drawn by OVL_BATTLE_APP, loaded at the SAME base 0x089DD4C0 as the menu overlay, so the
   menu decompile shows unrelated code at those VAs. It keeps a private copy of the owner → name-index map
   (0x08AFB6E8, row 33 = −1 → blank name). Lesson: find a screen's code by a live breakpoint (ra of the text
   call), not by the decompile of whatever overlay usually sits there; and the registry needs every copy of the
   owner → name map (EBOOT 0x089CC020, 0x089CF350, menu 0x08A23ACC, 0x08A544E0, battle 0x08AFB6E8).
12. **Inventory from bytes, not from script names or old surveys** (P2.0, 2026-10-20). The owner-33 list is re-made by
   decoding the package's patch words (tools/pkg/owner_scan.py): it showed the EX Burst sound skip was never built
   (TRINITY_CTL=1), and that the registry had the battle owner → name table twice under two names, one with a wrong
   "owner 33 row" note (it was the blank-name bug). Phase 2 converts what the oracle disc actually contains.
13. **One name function, one installer row** (P2.3 step 2, 2026-10-20, notes/phase2/P2.3-names.md). EBOOT FUN_088D6254
   (Records, Jukebox voices, and via menu FUN_08A1D7F8 the Friend Card / ghost names) now reads owners 33..34 from
   the scenario_names row 0x089CF350[owner] (rowgen D1), no Sora constant left. So the installer MUST write the D1
   row for every package owner: a missing row shows "Warrior of Light" (name 0) on those screens, not a blank.
9. **Test tooling that made this cheap:** disposable PPSSPP profiles (launch_isolated.sh), window-only screenshots,
   debugger scripts (BGM pick breakpoint, flag word dump, fighter finder + teleport), OQ editor's Test → pause →
   Win to skip a fight. Fold these into tools/ for the Phase 2 test kit.
13. **Behaviour stubs work, and runtime A/B against the oracle is the gate** (P2.4 step 0, 2026-10-20,
   notes/phase2/P2.4-exrun-pilot.md). EX run moved from hand asm into EXTRA.PRX through a data-indirect EBOOT stub
   (XSTB header 0x089A8B24, FN_PTR written by the module): same speed as the oracle, vanilla without module or
   registry, no bad access in strict mode, cost lost in the noise. But the first pilot ran ×1.3984 instead of ×1.40:
   the registry value had been copied from the `lui` half of a `lui/ori` float constant. equiv cannot see such errors
   once a constant moves from code into EXTRA.REG — every converted behaviour needs a measured pilot-vs-oracle
   comparison with identical (assisted) steps, and registry constants must be decoded from the whole instruction pair.
14. **Prove the port offline, but only the target runtime proves the route** (P2.4 step 1, 2026-10-21,
   notes/phase2/P2.4-tri.md). Running R4's original Trinity / item-effect asm in a small MIPS emulator next to the new
   C code on the same fake game memory (tools/pkg/engine/test/mips_emu.py) showed identical game calls — yet a full
   Sora EX Burst froze PPSSPP's JIT on the step-1 disc, only when the Kingdom Key hook (stub 5) jumped anywhere other
   than its own disc fallback; the IR interpreter, the oracle, Cloud and Garland were fine. For every DLC engine step:
   bisect with a test-only registry switch (leave chosen stubs vanilla), test JIT **and** IR, keep the module-missing
   control (it proved the generic "owner ≥ 33 → Cloud controller" fallback), and finish on the Vita before shipping.
   **Correction 2026-10-21 (freeze helper, P2.4-tri §8):** stub 5 was NOT the cause; the bisection had one burst per
   variant and the trigger is not every burst — repeat each bisection case at least 3× before believing it.
15. **Module C must call game code with a 16-byte aligned stack** (P2.4 freeze helper, 2026-10-21,
   notes/phase2/P2.4-tri.md §8). psp-gcc's EABI keeps sp only 8-byte aligned; the game's own code keeps vectors and
   matrices on its stack and stores them with VFPU sv.q, which needs 16. Sora's bar-full voice, called from a C function
   with an 8-byte frame, reached such a store at sp = 8 mod 16: PPSSPP's JIT turns sv.q into an aligned `movaps`, the
   alignment fault re-runs forever in PPSSPP 1.20.4's fault handler (100 % CPU, debugger and SIGTERM dead), while the IR
   interpreter (four plain stores) and the hand-written R4 asm (0x20-byte frames) were fine. Real hardware is not safe
   with a misaligned sv.q either. Rule for every DLC engine module: every call from module C into game code goes
   through the aligning thunk (beh.c `GFN` → `gt_<address>`, the function must be listed in `GAME_FNS`); asm wrappers
   keep sp a multiple of 16. How it was found: gdb attached from the launching shell (ptrace_scope 1), `stepi` showed a
   12-instruction host loop, a RAM + MIPS-context dump gave the guest stack. Settings check: see P2.4-tri §8.
16. **A package's code must not live in a game file, and a size change must never pass silently** (P2.4 step 2,
   2026-10-21, notes/phase2/P2.4-reflect.md). Sora's Reflect cave was 512 B appended to OVL_BATTLE_APP.ELF (ELF sizes,
   section headers and the ISO record grown). Moved into EXTRA.PRX, the file is byte-for-byte the clean layout again
   (only hook words differ); `equiv.py --allow-shrink IMAGE:LO-HI` is the one declared, printed way to accept the cut.
   EBOOT hooks that call battle-overlay code check which overlay is resident first (the copied ELF header at 0x089DD46C:
   battle p_filesz 0x185AB0, menu 0x17BD98). A hook whose only job reacts to a mark another hook sets (C4) can be the
   stub's EBOOT fallback itself (no module needed). Runtime A/B for guard/reflect needs an attacking CPU: TYPE Vicious
   with strength Minimal, an attacker with melee + HP + projectiles (Lightning), the attacker's Bravery capped so a
   reflected HP attack cannot end the battle, few debugger reads per poll (they can stop the game), and frame-exact
   screenshots (vblank breakpoints) for "looks the same".
17. **An item's effect lives once, in the item table; free code only after a reference scan** (P2.4 step 3, 2026-10-21,
   notes/phase2/P2.4-shield.md). Save the King's ×1.5 existed twice (row `params.shield_pct` 192 and item_fx
   REFLECT_POWER 1.5); the module reads item_fx only (like every other item effect) and the registry now refuses the row
   copy. Before code words go back to vanilla, `tools/pkg/engine/p24_refscan.py` lists every j/jal, branch, lui pair and
   data word that still points into them (P24-reflect: EE_B's only user was SHIELD). "Free" EBOOT space here means a
   never-called vanilla function: restoring its clean bytes makes the image vanilla again there, it does not make zeros.
   Runtime proof of a hit-power effect without code breakpoints: a write breakpoint on a fixed global the code writes
   right after (the hit-list tail) gives the object in a register; compare the stored power disc vs oracle (150 / 100).
18. **Items are package data end to end; menu hooks must be cheap in the frames that build lists** (P2.4 step 4,
   2026-10-21, notes/phase2/P2.4-items.md). Who may equip an item, the list masks, the □ "Can be equipped by" panel, the
   new-game / old-save gift, level-scaled stats and the fighter's EX-page pictures all come from EXTRA.REG now: the
   item_owner byte (owner + bit 7 "start-owned"), aux SCALE, aux EXPAGE, plus the row's `panel_sprite`. A new fighter with
   items needs `items.owned` (+ `start_owned`, `scale`, `fx`) and `behaviours.ex_page`; eligibility is by owner number,
   so a fighter sharing a vanilla equip bit (Sora / WoL bit 0, owner 34 / Garland bit 1) does not leak items to that
   vanilla fighter while the module runs. Without the module the shared bit wins (WoL's panel lights Sora; EX page shows
   WoL's art) — no crash. Menu cost: these hooks are idle on still screens, but opening the Shop / Buy list calls the
   item mask ~29,600 times in ONE frame (already ≈ 0.35 s of CPU in the original game). Give such hooks an asm fast path
   that skips the C call for non-package items and keeps the frame minimal, and compare the worst frame of each action
   with the oracle (tools/qa/runtime/p24/menu_cost.py), not only still screens. Before freeing code, scan for data
   pointers too (p24_refscan used to skip every EBOOT pointer word).
19. **Menu lookups are install-time tables in the freed EBOOT block; only list builders read the registry** (P2.3
   steps 3-7, 2026-10-21, notes/phase2/P2.3-home.md + P2.3-pictures/museum/oqface/flags.md). Every "which picture /
   frame / setup row / Museum owner / Records icon / panel sprite / OQ face belongs to fighter N" is a small per-owner
   table (OXT) at EBOOT 0x089A8B94.. that the installer writes (vanilla column copied from the clean image + the
   package's registry values): same cost as vanilla, works without the module, checkable on the disc. A new fighter
   needs only its registry values (pic_slot, party_frame, setup_frame, museum_record, panel_sprite, oq_face_*,
   install.records_icon / records_append) — no code. The Jukebox purchase gates read the EXTRA.REG flag-range list
   (engine 2.5.0), the Labyrinth BGM fallback asks REG_ROW: both only when a list is built / a battle starts. Lessons:
   compare a rewritten block's CALL ARGUMENTS in the host test (a "spare" addiu was the next call's argument); a
   registry format change must keep decoding the frozen recipes' older files; owner 34 gets its table entries for
   free, but still needs P2.7 for sprite cells, the Records array, the Museum record and the grid row.
20. **Save records: the slot comes from the owner number, the data from an installer table, and old saves migrate once
   for all packs together** (P2.5, 2026-10-22, notes/phase2/P2.5-saves.md). A package fighter's record lives in friend
   card slot 57 − owner (Sora 24, owner 34 23) — never "the n-th pack", or removing a pack would hand its slot to the
   next one. The installer writes the friend-card cap (lowest installed slot) into both cap words AND a data copy, plus
   one catch-up marker per record owner (install.record_mark) into the EBOOT "SRC1" block; the game code has no owner
   number left. The migration (count > cap) runs once for every package slot together and re-receives real cards with
   the game's own receive function before any record is set up (per-owner migration silently loses a card). Lessons:
   host-test asm against the old code on EVERY input incl. register / sp preservation (a frame push in a branch delay
   slot leaked 32 bytes of stack per blank-record read); check what the player's save FILE really holds (Mat's was still
   in the pre-fix state: the fix had only run in RAM); the Friend Card menu commit re-initialises the card slots below
   the cap, so a removed pack's record does not survive it; save records must not depend on the module.
21. **Derive the engine package from a clean diff, and store package edits by identity** (P2.8 design, 2026-10-21,
   notes/phase2/P2.8-sora-package.md). Tools that patch on top of a reference disc hide words the clean install
   needs: the P2.3 / P2.4 writers guard against the R4 oracle, so 143 generic engine words exist only inside Sora's old
   patches and come from nowhere on a clean dump — the engine package must be cut from a clean → engine-disc diff
   (old = clean words). Store every package edit by **what it is** (owner, text entry, model id, picture id, allocated
   id), never by final row position or byte offset: final indexes shift when a second package adds rows (a synthetic
   owner 34 moves Sora's objentry rows 1170..1172 → 1173..1175), and count bytes / offset tables / picture fillers are
   then edited by both packages. The installer derives counts, offsets, final indexes and fillers from the clean game
   plus all packages (codec prototypes: clean + Sora's re-keyed rows = the oracle bytes, 82/82).
22. **Every acceptance check a helper ran by hand is now a profile line** (P2.10 kit, 2026-10-21,
   notes/phase2/P2.10-kit-built.md). The disc is checked against what its recipe says — sha, frozen module, EXTRA.REG,
   equiv allow-sites + the **exact** allowed-word count (allow-site ids only grow), xori site list + immediate budget —
   by one command (`tools/qa/acceptance/run_static.py --profile P`), and the 16-byte stack rule is checked statically
   (stack_rule.py found the P24-tri freeze cause without the emulator). Do not trust a check tool's exit code until it
   is tested: static_checks.py / owner_scan.py used to exit 0 with FAIL rows (fixed 2026-10-22; the runner still judges
   their output).
23. **A fighter package holds no game code; the engine package and the installer do** (P2.8 build, 2026-10-22,
   notes/phase2/P2.8-build.md). Sora is now `packages/sora-C` (format 1.1) on `packages/engine`: every code word Sora
   once needed is either engine base (the same for every roster, old = clean words) or an installer word computed
   from the roster's registry files (`tools/pkg/rostergen.py`). Prove a re-keyed package before trusting it: apply the
   old rows and the new rows to the clean bytes and compare (pkg11.py), then compare the whole install in memory with
   the tested disc (layoutc.py verify) before writing an ISO. Two table facts found on the way: eqpm presets are sorted
   by preset id (Sora's row is inserted at 34), and collection_param sec8 puts a fighter's row at owner − 1 before the
   last clean row — a second fighter's rows must line up with these rules (positional.v1 refuses a gap).
