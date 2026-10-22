# Chapter 10 — The build pipeline and the release

**The big idea:** we never hand-edit a disc and hope to remember what we did. Every change is a
**script**. One master script, `tools/scripts/build_sora.sh`, runs them all in the right order
and turns a base disc into a full Sora disc. Re-running a step changes nothing ("nothing to
do"). At the very end we don't share the disc — only an **xdelta patch**, a small file that
says "change these bytes".

---

## 10.1 Words you need first

- **Build:** running all the steps that make the final files.
- **Build step:** one script that makes one change, e.g. `spot33_sndtrim.py ISO`.
- **Idempotent / re-runnable:** running it twice gives the same result as once. Our steps check
  what's already there and print "nothing to do" / "already patched".
- **Dry run:** the script says what it *would* change, but writes nothing (`--dry`, or tools
  that only write with `--out`).
- **Base disc:** the disc the build starts from.

---

## 10.2 The one command

From the **clean dump** (the release path, 2026-10-16):

```
tools/scripts/bootstrap_base.sh dumps/ULUS10566-base-fromclean.iso
tools/scripts/build_sora.sh dumps/ULUS10566-base-fromclean.iso dumps/ULUS10566-testNN-name.iso
```

- **Step 0, the base disc** (`bootstrap_base.sh`, ~1 min): copies `dumps/ULUS10566.iso` (only read,
  never written; the output must be a new file) and replays the slot-#33 setup of tests 14–28:
  roster rows (chrp, objentry, select list, Quick Battle row), ablt rows 617–620, own battle file
  `obj/p_sev120.objx`, own model/costume/portrait files, **plain EBOOT** (`eboot_plain.py`:
  `tools/pspdecrypt` + unlock row 22 → owner 33), own save record (`spot33_save.py`), name key
  (`spot33_names.py`), voice files (`spot33_voice.py`), own line ids (`voice_lines.py test28`).
  Sora's battle file is a copy of Cloud's file *with* the test 4–10 move experiment (his Combo
  Plus is action 1020), so the experiment is replayed on Cloud's files, copied, and then
  `spot33_cloudvanilla.py` puts Cloud back to the clean bytes.
  Proof: the bootstrap output = `test28-lines` except Cloud's two files + ablt row 209 (now vanilla)
  and `obj/P_SEV120_1P.gmo` (Cloud's 2P model instead of the test-19 pink skin; build_sora replaces it).
- The old base `dumps/ULUS10566-test28-lines.iso` still works as ISO_IN. It carries the test-24
  Cloud experiment (QA D-313-01); `spot33_cloudvanilla.py`, the first ISO step of `build_sora.sh`,
  removes it (Cloud's `p_sev100.objx` + `_w` = clean copy, ablt 0x0d00 → action 313).
- A full build takes about **19 minutes**.
- Without arguments it only builds the model `dumps/models/sora_final.gmo` (handy for previews).
- Never run it onto a disc PPSSPP has open.

---

## 10.3 What it does, in order

### Part A — the model and its animations (into `dumps/models/`)

| # | step | what |
|---|---|---|
| 1 | `gmo_resize.py` | Cloud's skeleton + all 86 motions get Sora's bone lengths |
| 2 | `gim.py`, `gmo2gltf.py` | that skeleton → glTF |
| 3 | `fit_sora.py` (NATURAL=1) | Sora's KH2 mesh fitted on, fist, 256 px textures |
| 4 | `add_keyblade.py` ×2 | Kingdom Key → wep0; Ultima Weapon (×0.685) → wep1 |
| 5 | `gltf2gmo.py` | back to GMO → `sora_natural.gmo` |
| 6 | `gmo_motion.py append` | new slots `_719A`–`_736A` (SLOTS list) |
| 7 | the **MOTIONS loop** | every slot filled: KH2 retarget, `atk:`, `nat:`, `combo:`, `burst:`, `pose:` (Chapter 3) |
| 8 | `gmo_motion.py copy` (STUBS) | empty Cloud slots Sora no longer plays (saves memory) |
| 9 | `gmo_motion.py take` ×5 | Codex's animations: EX activation, burst opening, charge loop, finisher, timed Trinity `_812A/B/C` |
| 10 | `gmo_thin.py _719A:2` | thin the win-camera copy (−27 KB; model must stay ≤ ~2,506,640 B) |

KH2 animations that haven't been baked yet are baked on the fly (`tools/kh2bake/bake`).

### Part B — onto the disc (only with ISO_IN ISO_OUT)

The disc is copied first (`cp ISO_IN ISO_OUT`), then:

| # | step | what | chapter |
|---|---|---|---|
| 10b | `spot33_cloudvanilla.py` | Cloud = vanilla (no change on a bootstrap base) | 10 |
| 11 | `keychain.py` → `pkg_put.py` | keychain v3, then the model goes on the disc | 3 |
| 12 | `sscf.py rebuild`, `spot33_voicex.py`, `pkg_put.py` | voice bank with Sora's KH2 clips + "Freeze!"/"Thunder!" | 5 |
| 13 | `spot33_movenames.py` | menu move names | 8 |
| 14 | `spot33_amas.py` | Customization doesn't freeze | 8 |
| 15 | `spot33_banner.py` | "Sora" header | 8 |
| 16 | `spot33_battlenames.py` | in-battle banners | 8 |
| 17 | `spot33_vsname.py` | VS / loading names | 8 |
| 18 | `make_title_art.py`, `spot33_faces.py` | face pictures | 8 |
| 19 | `spot33_2p.py` | 2P/3P outfits = Sora (mirror match) | 2 |
| 20 | `spot33_qbpics.py` | Quick Battle pictures + setup-screen patch | 8 |
| 21 | `spot33_combos.py` | actions, pieces, hit power, the four combos | 4 |
| 22 | `spot33_moves.py` | extra equippable abilities (ablt + text + chrl) | 8 |
| 23 | `spot33_desc.py` | descriptions | 8 |
| 24 | `spot33_speed.py` | later combo hits come out sooner | 4 |
| 25 | `spot33_chain.py` | SLOTS / COPY / ADVANCE / AUTHOR / WINDOWS / VARIANTS script blocks | 4 |
| 26 | `spot33_magic.py` → `pkg_put.py` | Firaga / Thundaga / Blizzaga HP magic (from the clean disc) | 4 |
| 27 | `spot33_spellsfx.py` | spell cast sounds | 5 |
| 28 | `spot33_thunder.py` | Thundaga straight down, Blizzaga one fast shard | 4 |
| 29 | `spot33_exmode.py` | own EX Mode start slot `_736A` | 4 |
| 30 | `spot33_ablt_cap.py` | ability table 808 → 832 | 7 |
| 31 | `spot33_lines.py` | spoken lines (.at3) + subtitles | 5 |
| 32 | `spot33_effects.py` → `pkg_put.py` | own FEP id (no clash with Cloud) | 6 |
| 33 | `spot33_fx.py` | rekey + Explosion orbs/flash | 6 |
| 34 | `spot33_introcam.py` | intro camera at Sora's height | 3 |
| 35 | `spot33_burstfx.py` | KH2 colours for the EX Burst | 6 |
| 36 | `spot33_firefx.py` | KH2 Firaga look | 6 |
| 37 | `spot33_sfx.py` → `pkg_put.py` | new sound slots 70–95 | 5 |
| 38 | `spot33_magicfx.py` | Thundaga/Blizzaga looks + impact sounds | 6 |
| 39 | `spot33_lightningfx.py` | Lightning's bolt (safe version) | 6 |
| 40 | `spot33_weaponsfx.py` | Keyblade, finisher, EX Burst sounds wired in | 5 |
| 41 | `spot33_reflect.py --apply-code` | Reflect hooks + cave | 7 |
| 42 | `spot33_sndtrim.py` | silence unused Cloud slots (bank ≤ ~540 KB) | 5 |
| 43 | **`spot33_soundids.py`** | **LAST:** own sound ids 219000 / 219100 | 5 |
| … | (later steps: EX, AI, Thundaga, Codex objx candidates, outfits, assist — see the script) | |
| 44 | `spot33_music.py` | very last: KH2 music tracks KH2TR/KH2WT/KH2SS.AT3 (new ISO files in DATA/BGM + BGM table/names/Museum rows; `notes/music.md`) | 10 |

### Order rules (why it's in this order)

- `spot33_chain` **before** `spot33_magic` (magic appends script blocks after chain's).
- `spot33_firefx` after `spot33_magic` (it edits the Firaga blocks magic creates).
- `spot33_effects` before the other effect steps (they work on the renamed FEP).
- `spot33_sfx` **before** `spot33_magicfx` and `spot33_weaponsfx` (they use the new slots).
- `spot33_sndtrim` just before `spot33_soundids`.
- **`spot33_soundids` always LAST** — any step that copies Cloud's script blocks brings
  Cloud's sound numbers back.
- `spot33_music.py` at the very end: it appends the audio files at the ISO end and adds their directory records
  (the only step that adds plain ISO files; `pkg_put.py` appends after it would just overlap PACKAGE.BIN's range, which is
  harmless). `--rollback` removes it again byte-exactly when it was the last step.
- `spot33_cloudvanilla.py` right after the disc copy (it only touches Cloud's files + ablt row 0x0d00).
- The Mat-approved tumble `_400A/_410A` (`dumps/models/tumble_approved.gmo`, a FINAL model with
  keychain curves) is taken again AFTER `keychain.py`; taken only before it, the clips gain +156 B
  each and the model no longer matches the played discs (found in the test316 check).
- `keychain.py` after every other model step, into a separate file (`sora_final_kc.gmo`), so
  preview tools that read `sora_final.gmo` don't meet the re-parented bone.
- Not re-runnable: `spot33_speed.py`'s SHIFT moves frames again on every run → only on fresh
  builds (that's why every build starts from the base disc).

### How a step edits Sora's battle file

Most `spot33_*.py` steps do the same dance: read `obj/p_sev120.objx` from the ISO, change one
or more chunks, rebuild the ARC (`spot33_combos.rebuild_arc`), and write it back with
`pkg_put.py` (in place if it fits, else at the end of the disc). They print one line per
change. Sizes are asserted where it matters (`effe` = 848,640 B).

---

## 10.4 After a build

1. A quick **smoke test**: battle starts, a ◯ combo and a □ attack land, no freeze
   (`ppcombo.py` logs).
2. Write the result into `docs/CURRENT-BUILD.md` (newest disc vs last smoke-tested disc).
3. Mat plays and judges looks/sounds.
4. Notes and `HANDOFF.md` get the finding right away (Mat's rule: update notes often).

Check: a fresh full build should reproduce the hand-made test discs. Once (test212) the full
build differed by a few bytes from the step-by-step disc → the effects helper fixed the scripts
until they matched (test214 = test213 byte-identical).

---

## 10.5 The release: an xdelta patch (the early path)

*This was the release path during the Sora build (tests up to 2026-10-17). Release 1.0 used the
package path in §10.7: a VCDIFF patch made by `tools/pkg/make_release.py` and a patch app.*

**Rule 1 of the project: never share game files.** So the release is an **xdelta patch**:
a file that holds only *the differences* between the clean disc and the modded disc. A player
applies it to their **own** clean copy and gets the modded disc. Analogy: instead of giving
someone your edited book, you give them a list "page 12, line 3: change 'cat' to 'dog'".

```
tools/scripts/make_release.sh dumps/ULUS10566-testNN.iso [NAME]
```

- Makes `dumps/release/NAME.xdelta` with `xdelta3 -e -9 -S djw` (strong compression).
- **Self-check:** applies the patch to the clean disc again and compares with the modded disc.
  Must be identical.
- Writes `NAME.txt` with checksums (md5) of the clean disc, the result and the patch, plus how
  to apply it:
  ```
  xdelta3 -d -s ULUS10566.iso NAME.xdelta Dissidia012-Sora.iso
  ```
  (or xdeltaUI / DeltaPatcher on Windows).
- Test 141's patch was 9.2 MB.

Clean disc → full mod now works in two commands (`bootstrap_base.sh` + `build_sora.sh`, §10.2;
test316-fromclean, 2026-10-16). **[OPEN]** Make the real release from such a fresh full build
(then `make_release.sh`), and test on a real PSP.

**A note on content:** the patch carries data derived from KH2's Sora (model, voices, sounds,
textures). It contains only our changes, never a disc. Fan-mod norms apply; be aware of it.

---

## 10.6 Where to look

- `tools/scripts/build_sora.sh` — the build, with comments on every line.
- `tools/scripts/make_release.sh` (early xdelta path), `tools/pkg/make_release.py` (release 1.0).
- `docs/CURRENT-BUILD.md` — the discs up to release 1.0 (private working file); newer discs are in the
  [phase notes](../../notes/phase2/).
- `HANDOFF.md` (bottom = newest; private work log).

---

## 10.7 Since Phase 1: packages, the installer and release 1.0

**The big idea:** `build_sora.sh` still makes the **reference build** (layout R), but players never
get that disc. Instead the difference between it and the clean disc becomes a **package**, and one
generic installer puts packages onto any clean disc. The release is a patch from the clean disc to
the installed result.

```
clean disc ──► bootstrap_base.sh + build_sora.sh ──► reference disc R3 (layout R)
                                                          │ tools/pkg/extract.py  (R3 − clean)
                                                          ▼
                                                   packages/sora
clean disc + packages/sora ──► tools/pkg/install.py --layout B ──► installed disc
installed disc ──► tools/pkg/make_release.py ──► patch.vcdiff + release.json + README.txt
```

- **Package** = a folder with `manifest.json`, `files/` and `rows/` (and in format 1.0 also
  `patches/`, the owner-33 code words). Spec: [PACKAGE-FORMAT.md](../PACKAGE-FORMAT.md).
- **Layout B** = the game's own file list (`PACKAGE_INFO.BIN`) stays exactly as shipped; Sora's
  files are found through our list `EXTRA.IDX`, served by the module `EXTRA.PRX`. So a player's
  old Data Install stays valid.
- **Checks:** `tools/pkg/pkgapply.py verify` (the package reproduces the reference disc's content),
  `tools/pkg/equiv.py` (two discs give the game the same bytes), and `make_release.py` refuses a
  patch that would carry vanilla executable bytes or unchanged disc sectors.
- **Release 1.0** (published 2026-10-20): reference build R3 → `packages/sora` → installed disc
  (SHA-256 `36b6bc40d014fe6296c7061b4a2538bd26e8384a0ef6f478e6e133b4a05a0cdd`) → a 14.7 MB
  `patch.vcdiff`. The patch app (Windows, macOS, Linux; <https://github.com/MatNyaga/sora-fan-patch>)
  decrypts the player's own EBOOT first, so no game code is shipped, then applies the patch and
  checks the result's SHA-256. How it shipped: [notes/release-1.0-lessons.md](../../notes/release-1.0-lessons.md).
- **Phase 2 adds layout C:** the engine is a package of its own (`packages/engine`), Sora is a
  format-1.1 package without code patches (`packages/sora-C`), and the installer builds the
  per-fighter tables for the whole roster:
  `python3 -I tools/pkg/install.py dumps/ULUS10566.iso OUT.iso packages/engine packages/sora-C --layout C`.
  In progress (P2.8). Picture: [modding/OVERVIEW.md](../modding/OVERVIEW.md); making a fighter:
  [modding/MAKE-A-FIGHTER.md](../modding/MAKE-A-FIGHTER.md).

Next: [Chapter 11 — Working with Codex](11-working-with-codex.md).
