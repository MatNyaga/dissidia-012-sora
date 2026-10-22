# Contributing: how to work with this project

For modders who want to help, build on the research, or share a finding. Read [OVERVIEW.md](OVERVIEW.md) first.
Terms: [glossary](../learn/GLOSSARY.md).

---

## Sharing rules

- **Patch only.** What we share is our own changes: a patch (a VCDIFF delta against the clean disc), our own tools
  and our own docs. People apply the patch to their **own** copy of the game.
- **Own disc only.** The patch is made for the unmodified US disc ULUS-10566 (1,754,529,792 bytes, SHA-256
  `df94177d3e194e82800a574b50b61ee3c7be6caa877c8e82242a41af75d1ab6e`). Other regions are different builds and are
  not supported.
- **Credit and wording.** Wherever credits or legal text appear, use exactly:
  - "No Dissidia files are included. Sora's model and sounds are fan-ported from Kingdom Hearts II. Fan-made, not
    affiliated with Square Enix or Disney."
  - "Built by Mat with help from AI tools (Claude, Codex)."
  Never write "no game data at all": the patch does carry Sora's model and sounds, ported from KH2.
- **No trademarks, no "official".** No company names or logos in names, icons or images, no lettering that imitates
  the games' titles, and never "official", "update" or "DLC" in a way that suggests the makers of the games are
  involved. The game's name appears only as plain text, to say which game this works with.
- **Mat decides what gets published**, where, and when. Mat posts releases; nothing is posted on their behalf.

## What never goes in a patch or a repository

| never | why |
|---|---|
| an ISO, or any file extracted from the disc | it is the game; everyone uses their own copy |
| the EBOOT, encrypted or decrypted | game code; the patch app decrypts the player's own EBOOT on their machine |
| decompiled or disassembled game code (listings, `dumps/decomp/`, `notes/decomp/`) | game code in another form |
| text or data dumped from the game's files (`notes/strings-*.txt`) | game file contents |
| a `packages/` folder, raw | packages hold data derived from the game ("never-publish-raw" in every manifest) |
| unchanged game bytes inside the patch | `tools/pkg/make_release.py` refuses a release that would store vanilla executable bytes or unchanged disc sectors |
| personal data: email addresses, local paths, save contents, device details | privacy |

Short addresses, table layouts and single instructions in notes are research findings, not game code; whether a
note goes public is still Mat's call (the project keeps a reviewed list of every file). Public copies say the
address and what changes instead of quoting the game's own instructions.

## Naming

| thing | pattern | example |
|---|---|---|
| fighter key | 6 letters + digits, like the game's own | `sev120` (Sora), `tst034` (test fighter) |
| fighter files | the game's pattern with the key | `obj/p_sev120.objx`, `obj/P_SEV120_1P.gmo` |
| package folder | `packages/<id>` | `packages/sora-C`, `packages/engine` |
| registry source | `tools/dlc/registry/<id>.json` (in a 1.1 package: `registry.json`) | `tools/dlc/registry/test34.json` |
| test disc | `dumps/ULUS10566-<step>-<what>.iso`; never reuse a name | `dumps/ULUS10566-P27-capacity.iso` |
| research note | `notes/<topic>.md`; Phase 2 steps `notes/phase2/P2.<n>-<topic>.md` | `notes/phase2/P2.7-capacity.md` |
| code site | an id in `tools/pkg/code_sites.json` (append only; never change an existing id) | `p27_grid` |
| table | an id in `tools/dlc/owner_tables.json` | `objentry`, `grwp` |

Tool habits:
- Python always with `python3 -I`. Never name a scratch script after a standard-library module (a stray `ast.py` or
  `dis.py` in a folder breaks imports for every script started there).
- A tool that writes checks the original bytes first, prints "already" when run again, has `--dry` (writes nothing)
  and, where it makes sense, `--rollback`. It never writes the clean dump and refuses to overwrite an output.
- Times in UTC.

## How to report a finding

1. **Write it down right away**, in a note: `notes/<topic>.md`, or the phase note of the task you are on.
2. Start with **"In plain words"**: a few short lines anyone can follow. Then: the question, the method, the evidence
   (disc path and sha256, the exact command and its output, screenshots under `dumps/screens/…`), the answer, what it
   means for other fighters.
3. Say how sure you are: **PROVEN** (seen in the game), **BUILT** (made and checked in the files, not seen in the
   game), **GUESS** (from code or data, may be wrong), **OPEN**.
4. If it is a lesson every future fighter must respect, add it to [notes/dlc.md](../../notes/dlc.md) §F.
5. Inside the project, add one line with a UTC timestamp to the end of the project's running work log.
6. From outside the project: open an issue on the public research repository,
   <https://github.com/MatNyaga/dissidia-012-sora>, with the same parts (plain words, evidence, how sure).

Before you "fix" something, check how the vanilla game behaves. Several things that looked like bugs matched all
30 vanilla fighters ([notes/dlc.md](../../notes/dlc.md) §F 4).

## How questions and claims are tracked

Inside the project there is **one question queue** (the project's internal question queue) and one set of
collaboration rules; both stay in the private working project. It is how the two AI helpers (Claude and Codex) and Mat
keep track of work:

- **CLAIM** before you start: what you will touch, which base disc (path + sha256), what you will not touch. **DONE**
  when you finish, with the results. Other helpers do not edit files someone has claimed.
- **Questions** get a permanent id (`Q-YYYYMMDD-CODEX-NNN` or `Q-YYYYMMDD-CLAUDE-NNN`) and move
  OPEN → ANSWERED → VERIFIED → CLOSED. An answer is not verified until the asker checks it.
- **Base-image rule:** before any build or patch, the exact base ISO (path and sha256) is confirmed in the queue.
- Append; never rewrite someone else's entry.
- Questions only Mat can answer (priorities, publishing, anything that runs on Mat's devices) are listed for Mat;
  nobody guesses them.

## Credits

- Built by Mat with help from AI tools (Claude, Codex).
- No Dissidia files are included. Sora's model and sounds are fan-ported from Kingdom Hearts II. Fan-made, not
  affiliated with Square Enix or Disney.
- Tools we rely on are credited in the [README](../../README.md#licence-and-credits).
