# Sora's EX Mode Bravery damage (2026-10-16, Claude helper; static only)

Mat: "the brv attacks in Sora's EX mode do very little damage, can this be changed?"

## How the game scales Bravery damage in EX Mode
- Bravery damage (FUN_08ae45b8): atkp power (+0x10) × **EX multiplier FUN_08b34244** × attack/defence curve
  (fighter +0x109c attack, +0x10a0 defence) × per-record combo factor. There are no EX copies of atkp rows and no
  EX-only hit events in Sora's blocks: the same hits are used in both modes.
- EX multiplier, only while in EX Mode (FUN_08b34378: fighter +0x5b2 & 4, objentry +8 bit 4 clear), chosen by the
  **chrp +0x0C** bits:
  - 0x1 → × (1 + HP% × spec[+9] / 100) ("Ultima Weapon": stronger the more HP you have left)
  - 0x80000 → × (1 + EX gauge% × spec[+10] / 100)
  - 0x400 → × 1.5 flat (overlay float 0x08b3abd8; only owner 7 had it)
  - spec = battle.bin (in main.bin) chunk `spec`, 40 rows × 0x17C B, key = chrp +4; buffer 0x09b12b88 is exact
    size (next global at its end) and every key 0..39 is used → no room for an own row.
- Sora is a Cloud copy: chrp +0x0C 0x803 (bit 0x1, plus 0x2 = EX stance from spot33_exguard), chrp +4 = 1 = Cloud's
  spec row (+9 = 1). So his EX bonus = Cloud's: ×2.0 at full HP, ×1.5 at half HP, ≈×1.0 near KO. With his small
  KH2 per-hit powers (3-15 per swing, many swings) the EX bonus is easy to miss, and at low HP it is almost nothing.

## Change (tools/scripts/spot33_exdamage.py, test295-exdmg = test294 + this)
- chrp row of owner 33: +0x0C 0x803 → **0xC03** (adds the flat ×1.5). One byte; Cloud and everyone else unchanged.
- EX Bravery multiplier now: ×3.0 at full HP (Cloud ×2.0), ×2.25 at half, ×1.5 near KO (Cloud ×1.0).
  E.g. Combo Plus first swing (power 6): normal 6, EX full HP 12 → 18. Normal mode unchanged.
- Guard: accepts 0x803 (stock Sora) or 0xC03 (done); anything else stops. spot33_exguard ORs bit 0x2, so running
  it again later keeps 0x400.
- Check in game: EX Mode Bravery hits clearly bigger than outside EX (most at high HP); outside EX unchanged; HP
  attacks unchanged (they use Bravery as damage); Reflect still returns the move with Sora's multiplier (bigger now).
