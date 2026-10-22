# Cloud vs Sora: missing effects — the FEP id clash (2026-10-14)

Static research: decompile plus disc data from `dumps/ULUS10566-test133-sound.iso`, read-only. Not run in game yet.

**Symptom (Mat, test 133, Cloud vs Sora):** Cloud's weapon effects don't come out:
- sword trails / weapon flashes (Climhazzard and others)
- the weapon-effect sound
- Meteorain's meteors

Cloud's own snd_ / voice banks still play.

## Verdict
Confirmed, but **not** by package name. Each fighter gets its own effect library, keyed by its objentry model name:
`p_sev100` for Cloud and `p_sev120` for #33.

The clash is the **FEP id** inside the effect data. #33's `effe` is a byte copy of Cloud's, so both FEPs carry id
**0x311C0000**. The global FEP store accepts one FEP per id. The second fighter to load gets no FEP, and **every**
effect of that fighter silently does nothing:
- trails 8888 / 9999 (op 0x2a)
- magi visuals (meteors, Firaga)
- effects started by id
- the FXSE effect sounds, which are tied to the effects

So the effects are lost on whichever side loads second. In Mat's test that was Cloud.

## How it works (code)
1. **Loader FUN_088459e0** (fighter file):
   - `effe` chunk → FUN_0883eb10(charData+0x34, name = objentry +0x34 model, data, size).
   - That copies the chunk into a heap block named `"OBJ_FEPAX:%s"` and stores the name.
2. **FUN_0883ebe4** → FUN_088a54b0(DAT_089d6d78, name, data, size) builds the library:
   - FUN_088a59cc looks up an existing library by **name** in 45 slots of 0x68 B. If found, it only adds a reference.
   - Otherwise it parses the MPK. The members are taken **by index** (FUN_088a5914 → FUN_088a99c4): 0 = .fep,
     1 = .feb (FEPA table, version 0x20100205), 2 = .fxseb (FXSE, version 0x20070422).
   - The result is stored at charData+0x5c.

   #33 = "p_sev120" (objentry rows 926 / 1152 / 1153 / PUB), Cloud = "p_sev100". **Separate libraries**, so no clash
   here.
3. **FUN_088a9a80** → FUN_088a6574 → FUN_08941888 → **FUN_08943124** registers the FEP in the global store
   (DAT_089d6d80+8):
   - It first calls **FUN_0894349c(store, fep+0x10)**, which walks the loaded FEPs comparing
     `fep[+0x10] == id & 0xFFFC0000`.
   - **If that id is already loaded, it returns NULL.** The library's FEP handle (lib+0) stays −1.
   - This is the only place in the code that uses the id (`grep 0xfffc0000`).
4. Every effect spawn ends in FUN_088a68fc → FUN_088a4d7c(lib handle, FEP resource):
   when the library's FEP handle is −1 it returns 0 at once. The effect gets no instance (state 2) and plays nothing.
   That covers all of these, for that library:
   - weapon trails: main op 0x2a → FUN_0884e660 → FUN_088a9e24 with filter FUN_0884e888 (FEPA id 8888 / 9999 +
     variant mask + node `r_wep` found on the fighter's model)
   - magi visuals (row +0x04)
   - one-shot op 0x19, main op 0x66
   - effects tied to a motion slot (FUN_088aa844)
   - the FXSE sound rows attached to effects (effect+0xc4 = lib+0x28 + row × 0x140)

   Trails are bound per fighter: the slot table DAT_09b166f0 (+0x48 per fighter) plus that fighter's own library.
   Nothing is shared by weapon model or slot; they die only because the library has no FEP.

## FEP ids on the disc
FEP header +0x10 is the id; the game compares the top 14 bits only. There are 363 distinct ids over all packages and no
duplicates, except Cloud's copy in #33's file.

| fighter | id >> 18 |
|---|---|
| sev100 (Cloud) | 3143 |
| sev200 (Sephiroth) | 3144 |
| sev110 (Tifa) | 3145 |
| eht100 / eht200 / eht110 | 3153 / 3154 / 3155 |
| fiv210 | 3126 |

**3146–3152 are free.** sev120 → **3146 = 0x31280000**, which also fits the series.

Inside the FEP, resources refer to each other by **id | (index << 10)**. In Cloud's FEP there are 226 such u32:
- the header at +0x10
- a 12-byte table from +0x9C4
- 0xA0-byte records up to +0x5840

All 33 fighter FEPs follow the same rule (aligned u32, top bits = own id, low 10 bits 0), every match is below +0x7600,
and there are 0 matches past +0x10000. Four "0x311C…" values deeper in are texture data with nonzero low bits; leave
them. Only Cloud's own file has structured references to 0x311C.

## Fix: `tools/scripts/spot33_effects.py`
Dry-run by default. It writes only a patched copy of the file with `--out`; then use pkg_put. Same size, rerun-safe.
```
python3 -I tools/scripts/spot33_effects.py ISO                    # lists 226 changes (file + ISO offsets)
python3 -I tools/scripts/spot33_effects.py ISO --out OUT.objx   # patched copy, then: pkg_put.py ISO obj/p_sev120.objx OUT.objx
```
- It rewrites the FEP header id and the 225 internal references from 0x311C0000 to 0x31280000:
  `new = (old & 0x3FFFF) | 0x31280000`.
- Test 133: the effe chunk is at file +0xCC70 and p_sev100.fep at +0xCCE0. The first change is at file **+0xCCF0**
  (ISO 0x6A013CF0): `00 00 1c 31` → `00 00 28 31`. The rest run from +0xD6A4 to +0x12520.
- Checked on a copy: exactly 226 bytes differ (all the `1c` → `28` byte). The header now reads 0x31280000, and only the
  4 texture-noise values keep the old prefix.

Add it to build_sora.sh after the step that copies Cloud's file; it is idempotent.

## Optional flags (cosmetic or risky)
- `--names`: renames MPK member names `p_sev100.fep/.feb/.fxseb` → `p_sev120.*` and the 69 `P_SEV100_*_LEAF_0`
  effect names in the FEP. Same length. No lookup by these was found (members are taken by index), so it is cosmetic.
- `--fepa-model`: renames FEPA +0x88 `p_sev100_1p` → `p_sev120_1p` (46 entries). FUN_088aa844 auto-spawns FEPA
  entries whose model name matches the fighter's model (case-insensitive, first 8 chars when it starts with 'P') and
  whose +0xC8 motion slot is the motion being started.
  - With Cloud's name they probably never match on Sora, so Cloud's slot-bound effects (Meteorain on _705A,
    Cross-slash on _700A, …) don't play on Sora's KH2 moves.
  - Renaming would turn them on, which is probably unwanted while Sora reuses Cloud's slots. **Leave off** unless you
    want Cloud's slot-bound effects back.
  - Effects started by id (trails, magi, op 0x19) attach regardless of this name.

## Other things in #33's file still keyed to Cloud (none clash the same way)
| item | clash? |
|---|---|
| FEP id | **yes** (fixed above) |
| snd_ bank / FXSE sound ids | fixed already (219000 / 219100, spot33_soundids.py) |
| effect library name | no (taken from objentry model `p_sev120`) |
| MPK member names, FEP leaf names, FEPA model names `p_sev100*` | no (see flags above) |
| `wind` GIM `window7.tm2`, `spec` menu pictures, `d_se` dummy GMO (`_010A`, camera nodes) | not seen used by name in a global table; identical content anyway |
| magi / atkp / plya / comb / p_se ids | per fighter (charData), no clash |
| GMO P_SEV120_1P part names `p_sev100*` | model side, not part of the effect system |

Rule for any future fighter built from a copy: **give its FEP a new id** (and new sound ids). Otherwise the two
fighters can't both have effects in the same battle.
