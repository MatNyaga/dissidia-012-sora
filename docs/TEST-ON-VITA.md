# Testing the Sora disc on Mat's PS Vita (PSP mode)

Written 2026-10-19, updated 2026-10-22. The Vita runs PSP games through Adrenaline (custom firmware): Sony's own PSP firmware on Vita
hardware. That is much closer to a real PSP than PPSSPP, so this is our real-hardware gate (PHASE2-PLAN P2.12).

## Why this disc proves a lot at once
The release disc (layout B) keeps the game's own file list untouched. Sora's files are found **only** through our
code module `EXTRA.PRX` and its file list `EXTRA.IDX`. So if Sora shows up and fights on the Vita, then:
- the unsigned module loads on hardware (P0.2),
- the decrypted (plain) EBOOT runs (needs CFW, expected fine),
- the module's live code hook that serves Sora's files works on hardware (P0.7).

## Steps
1. **Back up your Vita save first.** Copy `ux0:pspemu/PSP/SAVEDATA/ULUS10566*` to your PC (VitaShell → USB or FTP).
   The Sora version writes Sora's record into the save.
2. **Copy the disc** to `ux0:pspemu/ISO/`:
   - **the current test disc = whatever the latest phase note names** (Claude says the exact path + sha before
     copying). Today (2026-10-22): `dumps/ULUS10566-P25-saves.iso` (sha256 8f163258…31c7,
     [P2.5-saves.md](../notes/phase2/P2.5-saves.md); 1.8 GB). The P2.8 engine disc is next (P2.8 is in progress).
   - for comparing menu speed: `Dissidia012-Original.iso` (the clean game).
   - history (do not copy for new tests): `ULUS10566-p17-installB.iso` (release candidate 2) and
     `Dissidia012-Sora-test353.iso` (2026-10-19 Vita crash fix) are superseded.
   Optional: a 100 % save can go into `ux0:pspemu/PSP/SAVEDATA/`. That way all fighters and menus are unlocked.
   Copy it; never move it.
3. **Adrenaline settings:** CPU clock 333 MHz for normal play (Dissidia is heavy). **For menu-speed checks use CPU
   clock Default** (the 333 setting hid the menu-clock difference, 2026-10-20; the five-minute check above uses
   Default).
   **Turn off game plugins** (Adrenaline → hold R at start → Recovery → Plugins → set every "game" line to
   Disabled). Seen 2026-10-20: with several game plugins on, neither the original nor the Sora disc started; with
   them off both started.
4. Start Adrenaline → Game → Memory Stick → "DISSIDIA 012".

## Copying safely (learned 2026-10-19)
- Keep the Vita on the charger and the USB cable firm; if the PC shows the Vita connecting/disconnecting, stop.
- Claude verifies each copy by unmounting, remounting and re-reading the file from the card (a hash taken right after
  copying can come from the PC's memory, not the card).
- Always eject before unplugging (only unplug after Claude says the card is ejected). An interrupted write can damage the card's file system (it happened once: a disc
  file got overwritten by folder records, and the Vita crashed at boot with that card).
- With a card reader on the PC it is faster and safer than VitaShell USB mode.
- A card can silently drop writes (seen 2026-10-20: one 16 KB block kept old data, no error shown). Only the
  re-read after remount catches it. Cheap or old cards: test them with `f3write`/`f3read` first.

## Five-minute check for a new fighter disc (C items), for Mat
Before you start: Claude copies the disc to the card, checks it after a remount and ejects it. Keep your old Dissidia
save backed up (it is already on your PC). In Adrenaline: game plugins **off**, CPU clock **Default**.

1. **Start the game** (Adrenaline → Memory Stick → the disc Claude named). It reaches the title screen and loads your
   save. *Fail = black screen or freeze → stop here and tell Claude.*
2. **Character select** (Quick Battle): the new fighter is on the bottom row with his own face and his own text.
3. **One battle**: the new fighter against any CPU (CPU strength Minimal, stage Order's Sanctuary is fine). Use a
   few attacks for about a minute. You see his own moves and hear his own voice, not Cloud's.
4. In the same battle: fill the EX gauge, press **R + □** (EX Mode), then do his **full EX Burst** (hit with an HP
   attack in EX Mode, then mash ○ as fast as you can). It plays to the end and the battle goes on. *A freeze here is
   important — tell Claude.*
5. **Finish the battle** (win or forfeit) and go back to the menu. No freeze, the result screen looks normal.
6. **Shop → Buy**: open the item list and scroll a bit. It should feel as fast as on the original game.

Write one line per step: OK / not OK (a phone photo of anything odd helps). That's it.
If you have more time (only when Claude asks for it): Original Quest slot with the fighter (V6), Data Install and a
battle again (V7, only on release discs), the fighter as an assist (V8, only if he has one).
(From [P2.10-kit-built.md](../notes/phase2/P2.10-kit-built.md) §5, added 2026-10-21.)

## What to check (write down pass/fail, a phone photo is fine for anything odd)
| # | check | pass looks like |
|---|---|---|
| V1 | game boots to the title and loads your save | no black screen / freeze |
| V2 | Sora on the character select (bottom row) | his face + "Keyblade Master" text |
| V3 | Quick Battle: Sora vs a CPU, any stage, fight 1 minute | his model, moves, sounds, voice |
| V4 | EX Mode: fill the gauge, press R + □ | Sora's EX look, Reflect barrier |
| V5 | Win a battle, then quit to the menu | no freeze, result screen OK |
| V6 | Original Quest → Create New Quest → put Sora in battle 1 (RC3 disc) | his face + "Sora" (RC2 shows a black square, known) |
| V7 | Data Config → Data Install (any size), then a Sora battle again | install finishes, Sora still loads |
| V8 | Sora as an assist (Customization → assist), call him in battle with R + ○ / R + □ | Sora jumps in |

If V1 fails (freeze at boot), stop there and tell Claude what you saw. That would point at the plain EBOOT or the
module, not at Sora.

## After the test
Results go into the project's Phase 1 notes (not published) and [PHASE2-PLAN.md](PHASE2-PLAN.md) P2.12. V1–V5
passed for release 1.0, so the README says "Tested on PS Vita (Adrenaline)".

## Results log
- 2026-10-19, p17 (RC2): V1 boot OK, menus OK (slow, CPU clock unclear), Cloud vs CPU Cloud full match OK.
  **Any battle with Sora crashed at the white loading screen (C1-2858-3).** Cause: missing Sora row in the game's
  Max CP growth table (`grwp`); fixed by spot33_grwp → test disc test353, then release candidate 3.
  Also seen in the emulator: "Opponent Info" shows no name for Sora (cosmetic).
- 2026-10-20: test353 and the original disc verified on the memory card (sha256 after remount).
- 2026-10-20: both discs start after disabling the game plugins (see step 3).
- 2026-10-20, test353: Sora battles load and play (crash fixed). Menus: slight but noticeable lag vs the original
  disc (same Vita, card, settings) → open, ours. Mat: "everything is slightly slow like low fps in menus,
  gameplay seems fine" (steady, all menus, no freezes → per-frame cost, not file loading). Save slot 1 (GameData00, made in PPSSPP) shows no icon and
  "corrupted" in test353; slot with the real-PSP save loads. Next: same slot in the original disc; save made by the
  original disc on the Vita → load in test353.
  Result: slot 1 (GameData00) is also "corrupted" on the ORIGINAL disc → the PPSSPP-made save is bad on hardware,
  not our bug. Carry-over test: a NEW save made by the original disc on the Vita loads fine in test353 → PASS.
- 2026-10-20, test353 V-list: V1 boot PASS, V2 roster PASS, V3 Sora battle PASS, V4 EX Mode PASS, V5 win + back to
  menu, no freezes PASS, V8 Sora as assist PASS. V7 Data Install + Sora battle PASS (2026-10-20). Not run: V6 (needs RC3 disc). Open: menu fps lag.
- 2026-10-20 lag check: Adrenaline game CPU was 333 during the lag report; Mat now tries Default on both discs
  ("I think it's the speed difference"). test354 (menus forced 333/166) being built/checked.
  Result: on Default both discs feel equally slow → CONFIRMED: Adrenaline's game CPU 333 speeds up the original's
  menus but not ours (game drops to 222/111 in menus). Fix: test354 (spot33_menuclock).
- 2026-10-20: test354 (4cabe666…91fa) copied to the card as Dissidia012-Sora-test354.iso, verified after remount, ejected. Mat: compare menus vs original with CPU Default, also after a battle.
- 2026-10-20 test354 on the Vita (CPU Default): menus "not perfect but much better" than test353 → menuclock goes into RC3. Possible rest: compare vs the original with Adrenaline 333 again later.
- 2026-10-21: P24-shield (5267025c…) and P24-items (807e09fc…) copied to the card, verified after remount, ejected. Mat: full Trinity Limit (freeze check), Reflect, Shop/Buy list speed vs the original.
- 2026-10-21 Mat tested P24-items on the Vita: "works just like before" (full + short Trinity Limit, Reflect, Shop/Buy menu) → P2.4 module code PASSES on real hardware.
