# Contributing

Thanks for your interest! Bug reports, test results and fixes are all welcome.

## Reporting a bug or a test result

Open an issue on GitHub and include:

- the mod version (or release candidate) and how you play it: PPSSPP version and OS, or PS Vita / PSP with its
  firmware;
- what you did, what you expected, and what happened;
- a screenshot or a short clip if something looks wrong.

Results from a **real PSP** are especially useful, because nobody has tested one yet.

**Never attach** an ISO, a save you care about, extracted game files or anything you got from someone else's game
copy. No download links to game files, please.

## Changing code

- Work in a branch or your own fork. Check the current state of the files before editing.
- Prefer scripts that make a change in a repeatable, checked way over handing in a changed binary file. A good
  patcher checks the original bytes first, can be run twice safely, and stops cleanly if the input is wrong.
- Test with made-up (synthetic) data where you can. Never point a test at your only copy of the game.
- New sound IDs, motion slots or free code areas in the game are shared resources. Open an issue before taking new
  ones, so two changes don't claim the same numbers.

## Describing your change

Say what the problem was, what your change does, and how you checked it. Keep "checked without the game"
(syntax, unit tests, hashes) separate from "tested in the game". If a file's exact bytes matter, give its SHA-256
rather than the file itself.

## Before you commit

- Run `bash tools/repository/smoke.sh`.
- Look at the list and sizes of staged files. Nothing from a game, no build outputs, no personal paths or secrets.
- Don't add third-party assets. New code is MIT like the rest of the repository; changes in `tools/installer/` are
  GPL-3.0-or-later (see [LICENSE](LICENSE)).
