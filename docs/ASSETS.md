# Assets and sources

This repository contains our own source code and research notes. It does **not** contain game content, and it
never will.

## What goes in Git and what doesn't

| Kind of file | In Git? | How to handle it locally |
|---|---|---|
| Our own source code, schemas and docs | Yes | Keep authorship clear |
| Game discs, decrypted EBOOT, extracted Dissidia files | No | Use your own copy; record its SHA-256; never change the original |
| KH2 models, animations, textures, effects, music | No | Extract them yourself from your own copy with the upstream tools |
| Voice reference clips and anything made from them | No | Keep them local, with your own notes on where each clip came from |
| Built files (GMO, OBJX, ELF, PRX, patched ISO), screenshots, logs | No | Build them locally; keep test evidence separate |
| Third-party tools (binaries, source, decompiled output) | No | Download from the upstream project; note version, hash and licence |
| Chat logs, personal notes, logins, configuration | No | Keep them local; write the useful findings into the docs |
| Release patches | No | They are published as downloads of the patch app, not in this repository |

## Getting your local inputs

1. Note the game's edition and region and its SHA-256 in a local file. Don't put receipts, account names or personal
   paths in Git. The build targets the US disc ULUS-10566 only; other regions are not supported.
2. Extract files read-only into the local `dumps/` and `kh2_export/` folders. Keep originals apart from anything
   you make from them.
3. Get OpenKH, vgmstream, pspdecrypt, an ATRAC3 encoder and the other tools from their own projects. Note exact
   versions, archive hashes and licences. Don't copy a whole local tools folder into Git.
4. Export Sora, the Keyblades, animations and effects in the formats the scripts expect
   ([REPRODUCIBILITY.md](REPRODUCIBILITY.md) lists them). A fully checked, start-to-finish KH2 extraction recipe is
   still being written, so treat older extraction commands as a starting point, not a guarantee.
5. For each file you make, note the input hash, output hash, the command and settings you used. A matching hash
   proves the file is the same, not that it plays well in the game.
6. Build only from known inputs and a confirmed clean disc. Check the result structurally first, then test it in
   the emulator on a copy. Write down failures as well as passes.

## Licence

This repository is under the [MIT License](../LICENSE), except `tools/installer/`: that folder is a copy of the
patch app, contains code ported from pspdecrypt and libkirk, and stays GPL-3.0-or-later
([tools/installer/LICENSE](../tools/installer/LICENSE); its Cargo files say so too). The maintained patch app is
GPL-3.0-or-later in its own repository. Third-party tools keep their own licences.

## Before every push

`.gitignore` is a safety net, not a scanner: it can't remove files that are already tracked. Review `git ls-files`,
file sizes and contents before you push.
