# Chapter 9 — How we test

**The big idea:** every change is checked in the real game, running in the **PPSSPP** emulator.
Claude can drive PPSSPP like a remote control: press buttons, read the game's memory, set
"pause here" markers, and take pictures of only the game window. But the final judge of how
things *look* and *sound* is Mat.

> This chapter is the test method of the Sora build (to 2026-10-16). Since Phase 2 every disc also goes through
> throw-away PPSSPP profiles, strict mode, the acceptance kit and host tests: [modding/TESTING.md](../modding/TESTING.md).

---

## 9.1 Words you need first

- **Emulator:** a program that pretends to be a PSP, so the game runs on a PC. Ours is
  **PPSSPP**, installed as a Flatpak: `flatpak run org.ppsspp.PPSSPP <iso>`.
- **Debugger:** a tool that lets you look inside a running program: read its memory, pause it,
  step through it.
- **Remote debugger:** PPSSPP's debugger can be talked to over the network (a "websocket") on
  your own PC. Our Python tools connect to it. Turn it on in PPSSPP: Settings → Tools →
  Developer tools → Allow remote debugger.
- **Breakpoint:** a "pause here" marker.
  - **CPU breakpoint:** pause when the CPU reaches an instruction address. Example:
    `0x08991A70` runs once per sound played → a perfect sound logger.
  - **Memory breakpoint:** pause when a memory address is read or written. Example: "who
    writes the camera position?"
  After pausing, a tool reads registers (`a0`, `s0`, `ra` …), writes down what it sees, and
  resumes. The game only stops for a split second.
- **RAM dump:** a copy of the PSP's whole memory saved to a file (`ppsnap.py`). You can search
  it later for a name or a pattern.
- **Bisect:** find which change broke something by testing halves. Ten changes, one is bad:
  test the first five; if they're fine, the bad one is in the other five; split again.
  Four tests instead of ten. We used this for the finisher misses, the effects freeze,
  and Lightning's thunder.

---

## 9.2 Running a test

1. Build a test disc (Chapter 10): `dumps/ULUS10566-testNN-name.iso`.
2. Close PPSSPP if it's open: `kill -TERM $(pgrep -x PPSSPPSDL)` (kill by the process number,
   not by a name pattern).
3. Start it: `flatpak run org.ppsspp.PPSSPP dumps/ULUS10566-testNN-name.iso`.
4. Go to a battle. From the title: Cross, Start, Start, Cross (load), Circle, Down+Cross
   (Battle Mode), Cross (Quick Battle) → grid. In the 100% save the cursor starts on
   Lightning; #33 = Down ×3, Right ×5.
5. Usual test fight: **CPU Lightning, strength Minimal, stage Order's Sanctuary**.
   For combo tests: **CPU Sora** — it barely attacks, so you can land long combos.
   For realistic tests: **Average** CPU (CPU Sora escaped combos there, which found real bugs).
6. Give Mat **one clear thing** to press and look for ("Circle = Bravery, Square = HP; watch the
   last hit"). Don't send button presses while Mat is playing.

### The screen-recognising driver

`tools/scripts/go_battle.sh ISO [NAME]` starts PPSSPP and drives into a Quick Battle. Before
each press, `go_battle.py` **recognises the screen** (compares a tiny grey thumbnail with
reference pictures in `tools/scripts/screen_ref/`). On an unknown or forbidden screen (Extras,
Data Install, Story Mode) it stops and presses nothing. `EASY=1` picks the lowest CPU strength.

Why it exists: **blind press lists wandered.** One opened Extras → Data Install (cancelled
just in time); another walked into the Mognet calendar. And **never press Square on the results
screen** — that's "Save Replay".

---

## 9.3 The tools that talk to PPSSPP

| tool | what it does |
|---|---|
| `ppdbg.py PORT read ADDR SIZE` | read memory |
| `ppctl.py PORT press BUTTON…` | press buttons (`DUR=frames`; battle needs ≥ 12, pause = 20) |
| `ppplay.py` | play an input list **and** log the fighter's motion ids |
| `ppcombo.py` | put Sora N metres in front of the foe, press a sequence, log both fighters' motions (foe 5xx/7xx = got hit) |
| `ppanimlog.py` | log motion ids while *Mat* plays |
| `ppsoundwatch.py`, `ppsoundseq.py`, `ppslotwatch.py` | which sound slot plays (breakpoint 0x08991A70) |
| `ppbpwatch.py PORT SECS ADDR…` | log every time code at ADDR runs (e.g. projectile spawn 0x08AD0978) |
| `ppwatch.py`, `ppwatch2.py` | which functions run |
| `ppnames.py` | every file the game opens |
| `ppsnap.py` | dump all RAM |
| `ppexburst.py` | fill the EX gauge, enter EX Mode, start an EX Burst, mash Circle |
| `ppwinwatch.py` | log win/loss scenes |
| `ppmagi.py`, `ppmagipatch.py` | watch / live-patch projectile rows |
| `ppparry.py` | block-timing test |
| `test_combo.sh` | build a disc + drive + run ppcombo |

How tools find a fighter: scan memory for the fighter vtable `0x08B3A9A8` at +0x544, read the
owner, then read the motion id at +0x180 (Chapter 7 has the full list).

**Live tuning:** you can change numbers in memory while the game runs (a hit's power, a
projectile's spawn mode, the equipped moves) and see the effect immediately. Then bake the good
value into a build script. Example: "Explosion on plain □" = write into the live loadout before
the battle; restore afterwards.

---

## 9.4 Debugger gotchas (each one cost time)

- **One connection at a time.** Two tools connected at once jam PPSSPP. Combine logging and
  pressing into one tool.
- **Handshakes time out** → retry. A jammed PPSSPP may ignore TERM → `kill -KILL` its process id.
- **The port changes** every start: `ss -ltnp | grep PPSSPP`.
- **Slow handshakes (~25 s):** caused by the Origin header the Python websocket library sends.
  All tools now connect with `suppress_origin=True` → instant.
- **Debug log flood:** PPSSPP's log levels were all at "debug" → reads crawled. `ppsspp.ini`
  [Log] now 3. Never send the debug log to a file during normal tests (5 MB in 20 s).
- **WARNING — leftover breakpoint = frozen game.** If `timeout` kills a breakpoint tool before it
  cleans up, the CPU breakpoint stays in PPSSPP. The game then pauses on **every sound** — it
  looked like "test 116 crashes at the main menu". `ppsoundwatch` now cleans up on exit.
  If it happens: restart PPSSPP.
- Breakpoints must be handled **after** each request's reply, or replies get swallowed.

---

## 9.5 Seeing the game: screenshots and recordings

- **Only grab the game window.** Never the whole screen: a whole-screen recording once caught
  Mat's private browser (deleted). Get the window id from `xwininfo -root -tree | grep duodecim`,
  then `import -window <id>`.
- `tools/scripts/record_game.sh 20` records only the PPSSPP window for 20 s →
  `dumps/screens/rec_….mp4`. Claude reads frames from it.
- PPSSPP's own screenshot API fails on this setup ("Could not download output").
- Captures only work while Mat's screen is on.
- After a reboot the display is `:0` instead of `:1`: run tools with `DISPLAY=:0`.
- Frame-by-frame look at a fast effect: pause → screenshot → resume, repeat.

### Offline previews (no game needed)

Before a game test, check animations in Blender (runs hidden):
`gmo2gltf.py` + `gmo_anim2gltf.py` + `tools/blender/render_anim.py` → pictures in
`dumps/renders/`. GIF previews: `preview_kh2_motion.sh`, `preview_pose.sh`, `preview_slot.sh`.
Gallery: `dumps/renders/poses/index.html`. Effect mock-ups: `dumps/renders/kh2fx/`.
These are *previews*: they don't prove the game will show it the same way.

---

## 9.6 Saves

- Mat's own save is kept apart and backed up; a downloaded 100 % save is used for tests, always as a copy.
- The game autosaves when leaving Data Config.
- Claude changed the test save's equipment for tests (noted in `notes/abilities-owner33.md`).
  A backup of Mat's real loadout is kept before poking.

---

## 9.7 How we know something is PROVEN

| level | means |
|---|---|
| **static** | checked in the files only (the script ran, sizes OK, round trip byte-identical) |
| **logged** | the game ran and a tool saw it happen (motion ids, sound slots, breakpoint hits) |
| **seen** | a screenshot or recording shows it |
| **Mat** | Mat played it and said it's right ("perfect", "it works") |

The notes say which one. A static check is never enough for looks or sounds.

---

## 9.8 Test disc naming and cleanup

- `dumps/ULUS10566-testNN-what.iso`, numbered up (test 1 … test 215+). The name says what's new
  (`-voice`, `-combos`, `-fxsafe`, `-full` = a complete fresh build).
- Old test discs are deleted when newer ones work (they're big). Every step is in the notes
  and the tools, so nothing is lost. Kept: the clean dump, `test28-lines` (the build base), and
  the newest good discs.
- `docs/CURRENT-BUILD.md` names the newest disc and the last one that passed a battle smoke test.

---

## 9.9 Where to look

- [modding/TESTING.md](../modding/TESTING.md) — the check ladder used today.
- `HANDOFF.md` §7 — running tests (private work log).
- `tools/scripts/pp*.py`, `go_battle.sh/.py`, `record_game.sh`, `test_combo.sh`.
- `notes/research.md` — sources and early research (private working note).

Next: [Chapter 10 — The build pipeline and the release](10-build-pipeline.md).
