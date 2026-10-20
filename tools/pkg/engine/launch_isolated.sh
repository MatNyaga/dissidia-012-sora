#!/bin/sh
# Runtime launcher for engine/package test discs: PPSSPP on a DISPOSABLE profile.
# Mat's ppsspp.ini/controls.ini and his ULUS10566GameData* saves are only READ (copied into the trial), so Sora
# and the rest of his unlocks are available; nothing of his is ever written.
# Run INSIDE the Flatpak (host first checks `pgrep -x PPSSPPSDL` = nothing running):
#   flatpak run --command=sh org.ppsspp.PPSSPP ./tools/pkg/engine/launch_isolated.sh ISO
# The flatpak /tmp is wiped when the last PPSSPP instance exits -> everything is copied here, right before the start.
set -eu
iso=${1:?ISO}
M=${PPSSPP_SOURCE_PSP:?Set PPSSPP_SOURCE_PSP to your source PSP profile directory}
trial=${TRIAL:-$(mktemp -d /tmp/claude-eng.XXXXXX)}
mkdir -p "$trial/config/ppsspp/PSP/SYSTEM" "$trial/config/ppsspp/PSP/SAVEDATA" "$trial/cache"
for name in ppsspp.ini controls.ini; do cp "$M/SYSTEM/$name" "$trial/config/ppsspp/PSP/SYSTEM/$name"; done
# SAVES = folder holding ULUS10566GameData* (default: Mat's real saves, read-only). Sora-bought copy (disposable,
# PP poked): ./dumps/runtime-saves/sora-bought
cp -r "${SAVES:-$M/SAVEDATA}/"ULUS10566GameData* "$trial/config/ppsspp/PSP/SAVEDATA/"
sed -i "s/RemoteISOPort = 41335/RemoteISOPort = 41336/;s@CurrentDirectory = .*@CurrentDirectory = $trial@" \
  "$trial/config/ppsspp/PSP/SYSTEM/ppsspp.ini"
printf 'ISOLATED_ROOT=%s\n' "$trial"
ls "$trial/config/ppsspp/PSP/SAVEDATA/"
exec env XDG_CONFIG_HOME="$trial/config" XDG_CACHE_HOME="$trial/cache" /app/bin/PPSSPPSDL --windowed \
  --loglevel="${LOGLEVEL:-4}" --log="$trial/ppsspp.log" "$iso"
