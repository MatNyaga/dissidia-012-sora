#!/bin/bash
# Release = an xdelta patch only (never the ISO): clean US disc (ULUS10566) → modded disc.
#   tools/scripts/make_release.sh MODDED.iso [NAME]
# Writes dumps/release/NAME.xdelta (+ NAME.txt with checksums and how to apply). The clean disc is only READ.
# Players apply it with xdelta3 / xdeltaUI / DeltaPatcher:  xdelta3 -d -s ULUS10566.iso NAME.xdelta OUT.iso
#
# SUPERSEDED (2026-10-18, P1.9) for real releases by tools/pkg/make_release.py:
#   python3 -I tools/pkg/make_release.py dumps/ULUS10566.iso TARGET.iso dumps/release-VER --version VER
# That one makes the `-S none` patch the player app needs (this script's -S djw patch is refused by the app with
# E-PATCH), writes release.json (docs/INSTALLER-TECH.md §4) + README, checks ADD content and verifies with xdelta3 AND
# the app's own decoder. Keep this script only for quick test-build patches for xdelta3/DeltaPatcher users.
set -e
echo "NOTE: superseded by tools/pkg/make_release.py for releases (this -S djw patch does not work in the player app)" >&2
cd "$(dirname "$0")/../.."
CLEAN=dumps/ULUS10566.iso
MOD=$1
NAME=${2:-dissidia012-sora-$(date +%Y%m%d)}
[ -f "$MOD" ] || { echo "usage: $0 MODDED.iso [NAME]"; exit 1; }
mkdir -p dumps/release
OUT=dumps/release/$NAME.xdelta
xdelta3 -e -9 -f -S djw -s "$CLEAN" "$MOD" "$OUT"
# self-check: apply the patch to the clean disc and compare with the modded one
TMP=$(mktemp -p dumps/release --suffix=.iso.tmp)   # on /data: the root disk (/tmp) is nearly full
xdelta3 -d -f -s "$CLEAN" "$OUT" "$TMP"
cmp -s "$TMP" "$MOD" && echo "self-check OK: patch rebuilds $MOD exactly" || { echo "SELF-CHECK FAILED"; rm -f "$TMP"; exit 1; }
rm -f "$TMP"
{
  echo "Dissidia 012 Duodecim Final Fantasy (US, ULUS10566) — Sora mod patch $NAME"
  echo
  echo "Apply to a clean ULUS10566 ISO:"
  echo "  xdelta3 -d -s ULUS10566.iso $NAME.xdelta Dissidia012-Sora.iso"
  echo "  (or xdeltaUI / DeltaPatcher on Windows)"
  echo
  echo "clean ISO   md5 $(md5sum "$CLEAN" | cut -d' ' -f1)  size $(stat -c %s "$CLEAN")"
  echo "patched ISO md5 $(md5sum "$MOD" | cut -d' ' -f1)  size $(stat -c %s "$MOD")"
  echo "patch       md5 $(md5sum "$OUT" | cut -d' ' -f1)  size $(stat -c %s "$OUT")"
} > dumps/release/$NAME.txt
cat dumps/release/$NAME.txt
