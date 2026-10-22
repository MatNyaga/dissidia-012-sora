# Release 1.0: how it was shipped, and lessons (2026-10-20)

Release 1.0 went out on 2026-10-20. Mat pressed Publish at 05:44 UTC.

## What is where
- **Patch app source + downloads:** https://github.com/MatNyaga/sora-fan-patch (GPL-3.0-or-later). Built from a
  local staging clone. Release v1.0.0 = tag at commit 0a0a7f1 (the commit the apps were built from).
- **Landing page:** https://matnyaga.github.io/sora-fan-patch (source: sorapatch-public/site/, deployed by
  .github/workflows/pages.yml).
- **Research repo:** https://github.com/MatNyaga/dissidia-012-sora (MIT, except tools/installer/ = GPL).
  Exported from a local clone with a small sanitize script. Export rules: rename to "Mat", no email address, no
  local paths; commit as Mat's GitHub noreply address.
- **Game build shipped:** R3 (dumps/ULUS10566-R3.iso, sha 4cabe666…) → installed p18 (36b6bc40…0cdd).
  Release data: dumps/release-1.0-rc3/ (patch.vcdiff 8f657ff8…, release.json 620a9748…), zipped as
  dumps/release-1.0-zip/sora-release-1.0.zip (sha 5e485bd9…ff75).
- **Posting:** release/github-release-notes.md (the text on the release page),
  release/posting-guide-for-chatgpt.md (Mat gives this to ChatGPT; Mat posts everything), notes/release-venues.md,
  the release media folder (10 screenshots + the 60 s trailer, media.md).

## How the apps get built with real data (repeat this for 1.0.1)
1. Make the release with tools/pkg/make_release.py → release.json + patch.vcdiff + README.txt.
2. Zip the three files as `sora-release-<ver>.zip` (top level only), note its sha256.
3. Bump the app version in sorapatch-public: app/src-tauri/tauri.conf.json, the 3 Cargo.toml files, and both
   Cargo.lock entries. Check with `cargo metadata --locked`. Commit + push (with Mat's OK).
4. `gh release create v<ver> --draft --target main --notes-file … sora-release-<ver>.zip`. Drafts stay hidden.
5. `gh workflow run build.yml -f release_tag=v<ver> -f release_zip_sha256=<sha>`. The `attach` job puts the 5 apps +
   SHA256SUMS.txt + LICENSE.txt + SOURCE.txt on the draft. It never publishes.
6. Test: download the AppImage from the draft, run it with SORAPATCH_AUTOTEST=<copy of clean ISO>
   SORAPATCH_AUTOTEST_OUT=<dir>; the output sha must equal the expected installed-disc sha. Kill the app by PID.
7. Mat checks the draft and presses Publish (Edit → Publish release; the button is hidden behind Edit).

## Lessons
- **GitHub renames release assets:** spaces become dots and brackets are dropped
  ("Sora Fan Patch (portable).exe" → "Sora.Fan.Patch.portable.exe"). SHA256SUMS.txt must use the GitHub names.
  build.yml's attach job now renames before hashing (commit dd11aa5). For 1.0 the sums file was fixed by hand.
- **A release event runs the workflow files as they are at the TAG,** not at main. v1.0.0's tag (0a0a7f1) had no
  pages.yml, so publishing didn't deploy the page; it was started by hand (`gh workflow run pages.yml`). Future
  tags contain pages.yml, so it will run by itself.
- **Pin a draft's target** to the commit the apps were built from (`gh release edit --target <sha>`), so the tag
  matches SOURCE.txt.
- **Turning on GitHub Pages** (repo Settings → Pages → Source: GitHub Actions) was blocked for Claude by the auto-mode
  safety check (it opens a public site). Mat did it by hand. Don't work around this.
- **In a public repo, workflow artifacts can be downloaded by anyone logged in.** A real-data CI run makes the patch
  semi-public before launch. Mat accepted that for 1.0.
- **Dependabot alert #1 (glib 0.18.5, GHSA-wrw7-89jp-8q8g)** comes from Tauri's Linux GTK stack; no fix possible
  until Tauri moves to glib ≥ 0.20. Dismissed as tolerable risk with Mat's OK. Revisit when Tauri updates.
- **CI actions moved to Node 24 versions** (commit 083c433): checkout v6, upload-artifact v7, download-artifact v8,
  cache v5, configure-pages v6, deploy-pages v5, upload-pages-artifact v5. Builds and Pages green after.
- **Never put Mat's Gmail in public commits.** The research repo history was replaced once (orphan commit) because a
  commit used it. Check `git config user.email` in every clone before committing.
- **Vita lessons** (silent dropped SD writes, license folder, game plugins block discs, PPSSPP-made saves rejected by
  real firmware): docs/TEST-ON-VITA.md and notes/dlc-phase1.md.

## Decisions by Mat (2026-10-20)
- Credit "Mat". Required lines: "No Dissidia files are included. Sora's model and sounds are fan-ported from
  Kingdom Hearts II. Fan-made, not affiliated with Square Enix or Disney." and "Built by Mat with help from AI tools
  (Claude, Codex)."
- The trailer post doesn't mention the gauge refills between takes. The select screenshot keeps the KH2 logo.
- Research repo: MIT licence. Landing page live at publish.

## Open after 1.0
- **1.0.1 candidate:** R4 test disc (dumps/ULUS10566-R4-test.iso, 9d311d17…) = R3 + the Opponent Info name fix
  (spot33_oppinfo.py). Not released yet.
- **Menu slowness** on the Vita: better than before (test354), not perfect. Next: compare against the untouched game
  at the same Adrenaline CPU setting (needs Mat's Vita). Mat is testing this on their end (2026-10-20).
- **Ink splats over both Bravery numbers** (R4 test, dumps/screens/r4/06-*.png): Mat says probably the summon
  (normal game). Closed, not a bug.
- Vita card: run an f3 test on the card/reader; restore the other ~16 GB when Mat wants.
