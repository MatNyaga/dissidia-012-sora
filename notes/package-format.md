# Dissidia 012 (ULUS10566) — file layout

Dump: `dumps/ULUS10566.iso` (1,754,529,792 bytes). `UMD_DATA.BIN`: `ULUS-10566|148D27E345A5C063|0001|G`.

## Code

| File | What | Notes |
|------|------|-------|
| `SYSDIR/EBOOT.BIN` | main program, encrypted (`~PSP`, tag D91613F0) | decrypted with `tools/pspdecrypt` → `dumps/extracted/EBOOT.elf` |
| `SYSDIR/BOOT.BIN` | all zeros | dummy |
| `USRDIR/DATA/OVL_BATTLE_APP.ELF` | battle code overlay, **not encrypted** | 0x185AB0 bytes loaded at **0x089DD4C0** |
| `USRDIR/DATA/OVL_MENU_APP.ELF` | menu code overlay, not encrypted | 0x17BD98 bytes, **same address** 0x089DD4C0 |
| `USRDIR/DATA/OVL_EXTRA_APP.ELF` | small overlay | |
| `USRDIR/DATA/MODULE/*.PRX` | font + misc libs | |

Overlays: ELF type 0xFFA8, one LOAD segment at a fixed address, no relocations.
Battle and menu swap into the same memory, so they get separate Ghidra programs.

EBOOT.elf memory:
- 0x08804040 – 0x089DD3C0: code + data (0x1D9380 bytes)
- 0x089DD4C0 – ~0x08B63170: overlay slot
- 0x08B63170 +0x100DB90: more data / bss

## PACKAGE.BIN + PACKAGE_INFO.BIN

`PACKAGE.BIN` (1,034,358,784 bytes) holds 11,043 files. Index is `PACKAGE_INFO.BIN`:

```
0x00 u32  0x20090218   (a date: 2009-02-18)
0x04 char "pack"
0x08 u32  count = 11043
0x0C u32  0
0x10 entry[count], 12 bytes, sorted by hash:
     u32 hash         file-name hash (algorithm: unknown)
     u32 sector       offset / 0x800
     u32 size_flags   size = low 28 bits, flag = top 4 bits (values 0..3)
```

Verified: sorted by sector, every size fits its gap with <0x800 padding (11042/11042).
Flag counts: 0 → 7010, 1 → 1547, 2 → 1510, 3 → 976. Meaning of flag (P0.9, 2026-10-18): **Data Install tier** —
install size L (1..3) copies rows with 1 ≤ flag ≤ L; max 4050 entries, 0x280000 B per file (notes/dlc-phase0.md P0.9).

Unpacker: `tools/scripts/unpack_package.py` → `dumps/package/` + `dumps/package/index.tsv`.
