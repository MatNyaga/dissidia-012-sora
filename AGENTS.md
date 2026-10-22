# Notes for AI coding assistants

This repository is a source-only snapshot of a fan mod for Dissidia 012 (PSP). If you are an AI assistant working in
it, read these first:

1. [README.md](README.md): what the project is, its status and the sharing rules.
2. [docs/modding/OVERVIEW.md](docs/modding/OVERVIEW.md): how the disc, the engine module, the registry, packages and
   the installer fit together.
3. [docs/SETUP.md](docs/SETUP.md) and [docs/ASSETS.md](docs/ASSETS.md): what you need and what never goes in Git.
4. [docs/modding/TESTING.md](docs/modding/TESTING.md): which checks run without game files, and the full ladder.
5. [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md): what is missing from this snapshot, including the
   [Phase 2 tools not published yet](docs/REPRODUCIBILITY.md#phase-2-tools-not-in-this-snapshot).

Then, as needed: [docs/ROADMAP.md](docs/ROADMAP.md) (status), [docs/learn/GLOSSARY.md](docs/learn/GLOSSARY.md)
(terms), [docs/modding/CONTRIBUTING.md](docs/modding/CONTRIBUTING.md) (naming and how to report a finding),
[notes/README.md](notes/README.md) (the research notes). Docs and notes name some private working files (a work
log, the `codex/` folder, test discs under `dumps/`); they are not in this repository, so don't look for them here.

## Never commit

- Game files of any kind: ISOs, EBOOTs, extracted Dissidia or Kingdom Hearts files, models, textures, audio.
- Built outputs: patched discs, `.prx`/`.gmo`/`.objx` files, release patches, screenshots or recordings.
- Saves, credentials, chat logs, or paths from someone's own machine.
- Decompiled or disassembled game code, text dumped from game files, or notes that quote the game's own
  instructions. Write the address and what changes instead; our own patch code (stubs, thunks, hooks) is fine.

`.gitignore` blocks most of these, but it is a safety net, not a scanner. Check `git status` and the file list before
every commit.

## Work safely

- **Never change the clean game file.** Work on copies. Check that the input is the clean US disc
  (ULUS-10566, SHA-256 `df94177d3e194e82800a574b50b61ee3c7be6caa877c8e82242a41af75d1ab6e`) before you build.
- **Read a script before you run it.** Not every tool has a safe `--help` or `--dry` mode; some read game files as
  soon as they start, and the runtime tools can change emulator memory or profiles.
- Don't start an emulator, an installer or a full build just to check that the docs are right. Use
  `bash tools/repository/smoke.sh` for checks that need no game files.
- Never open an ISO for writing while PPSSPP has it loaded.

## Report honestly

Keep these apart: *written* (code exists), *checked without the game* (syntax, unit tests, hashes), *tested in the
emulator*, *tested on hardware*, and *accepted by the project owner*. An old test result doesn't prove a newer build
works. Say what you ran and what you didn't.

## Ask first

Licensing, publishing releases and changing who can access the repository are the project owner's decisions.
