# Sound bank ids — why Cloud loses sounds next to #33, and the fix (2026-10-14, desk research, not run in game)

## How a sound is found
1. **Bank registered** (FUN_088a15b8 → FUN_0899075c, 20 bank slots at DAT_089da420+0x34+i·0x10): the game
   takes the bank's **base** from its own SSCF header:
   - `h10 = u16 +0x10` (always 1), `h12 = u16 +0x12`, `h14 = u32 +0x14`
   - `base = h10·10000 + h12·100 − 10000` (= h12·100), or, **if h12 == 0 and h14 > 599: base = h14·100**
   - range = base … base + count (u32 +0xC).
2. **Sound played** (FUN_088a24d4(…, id, …) → … → FUN_089918c0(vol, id, …)): the first registered bank whose range
   holds `id` plays slot `id − base`. With Cloud + #33 both have base 2,200,000 → one bank answers for both →
   Cloud's Braver sound came from #33's bank (Mat, test 80).
3. **The id is ABSOLUTE data inside the fighter's own files** — there is no per-owner table:
   | where | what | Cloud's value |
   |---|---|---|
   | fighter file `p_se` type 8 scripts, one-shot **op 0x03 p0** (FUN_0883834c) | weapon/body sound | 2200000 + slot |
   | same, one-shot **op 0x11 p1** (FUN_088384a0, plays only if FUN_0886cc38(..)==1) | weapon/body sound | 2200000 + slot |
   | same, one-shot **op 0x15 p0** (FUN_08b33f8c) | voice (grunts, hurt cries) | 2210000 + slot |
   | `effe` chunk → MPK member **p_sev100.fxseb** ("FXSE", 75 rows): u32 base, u32 slot (FUN_088a6aa4 plays base+slot) | effect sounds | 2200000 |
   | **system.bin/chrp row +0x7c / +0x80 / +0x84 / +0x88** (fighter+0x5a4 = chrp row) | voice: +0x7c KO (FUN_08b06370), +0x80 EX Mode (FUN_08acafac), +0x84 (FUN_08aca66c, also EX-Mode-like), +0x88 (no reader found) | 2210004, 2210030, 2210042, 2210041 |
   | battle overlay **FUN_08a3a0b8** (Cloud's Omnislash EX Burst code): the sound id is built as a constant from two instruction halves (high 0x22, low 0x91f5) at VA 0x08A3A14C/0x08A3A160 and 0x08A3A364/0x08A3A378 (OVL_BATTLE_APP.ELF file 0x5cce0/0x5ccf4, 0x5cef8/0x5cf0c) | Omnislash sounds | 2200053, 2200054 |
   Scripts get a runtime offset from FUN_08842828(objentry row): +50000 if objentry +8 bit 3 (assist/_A rows),
   voice only: +10000 if bit 0 (manikin/ZAKO rows), +30000 if fighter+0x5b8 & 0x20. So Cloud's banks:
   22000 snd_, 22100 voice, 22200 manikin voice, 22500 assist snd_ (p_sev100_a/_w.objx), 22600 assist voice
   (voice_P_SEV100_A_00.scd), 22700 manikin assist voice. Assist files keep the MAIN ids in their scripts
   (Aerith's p_sev120_a.objx: 21900001, 21910004) and get +50000 at run time; their fxseb has the final 21950000.
   No code builds an id from the owner number (checked: no ×100000/×10000 owner math; only the 2 EX Burst immediates;
   no 2200000–2219999 data words in EBOOT/overlays).
4. **Why test 82 went silent**: it changed only the headers (+0x12 = 33000/33100) → the bank moved, the script /
   chrp / fxseb requests still asked for 2200xxx/2210xxx → nothing answered (unless Cloud was in the fight).
   Also 33000/33100 is **taken** (pkg 4351 fighter-size file, pkg 6875).

## Used bank ids (clean disc, all 504 SSCF banks scanned)
Fighters 10000–31700 (h12 form, FF heroes/villains), 32000/32100, 33000/33100, 34000/34100, 35000, 40000…, and
the 012 newcomers in the h14 form: **210000 … 218000** (owners 24 … 32: +0 snd_, +100 voice, +500/+600 assist).
**Owner 33 (Aerith) = 219xxx**: p_sev120_a.objx snd_ = 219500, voice_P_SEV120_A_00.scd = 219600, her original
chrp row had voice id 21910005. **219000 and 219100 are unused** → the devs' own slot for owner 33's main banks.
(66xxx is NOT free: 6,600,000 is used. 36000–39000 h12 are also free, as a second choice.)

## Fix = move everything at once (`tools/scripts/spot33_soundids.py ISO [--dry-run]`, rewritten 2026-10-14)
In place, sizes unchanged, idempotent. Run it **last** (after every step that rewrites obj/p_sev120.objx or
voice_P_SEV120_00.scd — sscf rebuild, pkg_put of the objx, script/hit tools that copy Cloud blocks).
Dry run on test 132 (read-only) = 326 writes:
| # | file | ISO offset (test 132) | change |
|---|---|---|---|
| 1 | obj/p_sev120.objx snd_ header +0x10 (objx at 0x6a007000, snd_ chunk +0xdbf70) | 0x6a0e2f80 | `01 00 f0 55 00 00 00 00` → `01 00 00 00 78 57 03 00` (h12 0, h14 219000) |
| 2 | voice/EN/battle/voice_P_SEV120_00.scd header +0x10 | 0x695be010 | `01 00 54 56 00 00 00 00` → `01 00 00 00 dc 57 03 00` (h14 219100) |
| 3 | objx p_se type 8 (chunk +0x530): op 0x03 p0 ×69, op 0x11 p1 ×94 | — | 2200000+s → 21900000+s |
| 4 | same, op 0x15 p0 ×92 | — | 2210000+s → 21910000+s |
| 5 | objx effe (+0xcc70) → p_sev100.fxseb (member +0xc9530): 65 rows | — | u32 2200000 → 21900000 |
| 6 | system.bin chrp row 33 +0x7c..+0x88 | 0x6945a4b4 | 2210004, 2210030, 2210042, 2210041 → 21910004, 21910030, 21910042, 21910041 |
(`SND_ID=… VOICE_ID=…` env vars pick other ids; ≤ 65535 → h12 form, bigger → h14 form.)

Expected after the patch: Cloud vs #33 → both have all sounds; #33 alone → unchanged (all sounds play).
Test: Cloud vs #33, Cloud does Braver / Cross-slash (his weapon sounds), #33 attacks, gets hit, KO, EX Mode.
`ppsoundseq.py` now prints the h14 id too (it read only +0x12 → would show 0).

## Left over / watch out
- **EX Burst**: #33 runs Cloud's Omnislash code, which plays 2200053 / 2200054 by immediate → after the move those
  two play only if Cloud is in the fight (from Cloud's bank), else silent. Fix later with Sora's own burst: a code
  cave at those two sites (s0 = state, *s0 = fighter; e.g. a1 = chrp[+0x7c] − 9951 gives 2200053 for Cloud and
  21900053 for #33 because both keep KO voice = voice slot 4), or give the burst motions op 0x03 script events.
- Assist: #33's _A objentry rows (b8 = 08) load Aerith's p_sev120_a.objx (219500/219600) → unaffected. If Sora ever
  gets an own assist/alt costume file, its banks must be 219500/219600 (+50000) — i.e. replace Aerith's.
- Manikin voice (+10000 → 219200) does not exist; #33 has no ZAKO rows, so not reachable.
- Tools that copy script blocks from Cloud's file into #33's after this patch bring 2200xxx ids back → rerun
  spot33_soundids.py (it only touches ids inside #33's old ranges).
