#!/bin/sh
# P0.6 runtime launcher: PPSSPP on a DISPOSABLE profile + memory stick (Mat's real profile/saves are never written).
# Based on Codex's proven launcher tools/codex/20261017-hp-projectile-refill/runtime/launch-isolated-336.sh.
# Run INSIDE the existing Flatpak (host first checks `pgrep -x PPSSPPSDL` = nothing running):
#   flatpak run --command=sh org.ppsspp.PPSSPP ./tools/dlc/p06_launch_isolated.sh STAGE ISO
#   STAGE = A (costume-4 row, disc model) | B (costume-4 row + ms0 model copies) | none (no DLC file = control)
#   ISO   = ./dumps/ULUS10566-p06-plaindlc.iso (patched)  or  ...-test338-voicesloud.iso
# Env: LOGLEVEL (default 4 = info), TRIAL (default: new mktemp dir under /tmp).
# The memory stick root of this profile is $TRIAL/config/ppsspp/ (XDG_CONFIG_HOME redirect), so the DLC files land in
# $TRIAL/config/ppsspp/PSP/GAME/ULUS10566/. Mat's ppsspp.ini/controls.ini are only READ (copied into the trial).
set -eu
stage=${1:?STAGE A|B|none}
shift
P=.
trial=${TRIAL:-$(mktemp -d /tmp/claude-p06.XXXXXX)}
mkdir -p "$trial/config/ppsspp/PSP/SYSTEM" "$trial/config/ppsspp/PSP/GAME/ULUS10566" "$trial/cache"
cp -r "$P/tools/codex/20261017-takeover/disposable-profile/PSP/SAVEDATA" "$trial/config/ppsspp/PSP/"
for name in ppsspp.ini controls.ini; do
  cp "${PPSSPP_SOURCE_PSP:?Set PPSSPP_SOURCE_PSP to your source PSP profile directory}/SYSTEM/$name" "$trial/config/ppsspp/PSP/SYSTEM/$name"
done
sed -i "s/RemoteISOPort = 41335/RemoteISOPort = 41336/;s@CurrentDirectory = .*@CurrentDirectory = $trial@" \
  "$trial/config/ppsspp/PSP/SYSTEM/ppsspp.ini"
case "$stage" in
  A) cp "$P/tools/dlc/p06_files/A-costume4-disc/PSP/GAME/ULUS10566/"*.edat "$trial/config/ppsspp/PSP/GAME/ULUS10566/" ;;
  B) cp "$P/tools/dlc/p06_files/B-costume4-ms0/PSP/GAME/ULUS10566/"*.edat "$trial/config/ppsspp/PSP/GAME/ULUS10566/" ;;
  none) ;;
  *) echo "STAGE must be A, B or none" >&2; exit 2 ;;
esac
printf 'ISOLATED_ROOT=%s\nSTICK=%s\n' "$trial" "$trial/config/ppsspp/PSP/GAME/ULUS10566"
ls -l "$trial/config/ppsspp/PSP/GAME/ULUS10566/"
XDG_CONFIG_HOME="$trial/config" XDG_CACHE_HOME="$trial/cache" /app/bin/PPSSPPSDL --windowed \
  --loglevel="${LOGLEVEL:-4}" --log="$trial/ppsspp.log" "$@"
