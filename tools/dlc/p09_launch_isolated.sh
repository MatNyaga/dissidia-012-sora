#!/bin/sh
# P0.9 runtime launcher: PPSSPP on a DISPOSABLE profile + memory stick, for the Data Install test.
# Same isolation as tools/dlc/p06_launch_isolated.sh (based on Codex's proven
# codex/inbox/20261017-hp-projectile-refill/runtime/launch-isolated-336.sh). Mat's ppsspp.ini/controls.ini are only
# READ (copied into the trial); his memory stick and saves are never used.
# Run INSIDE the existing Flatpak (host first checks `pgrep -x PPSSPPSDL` = nothing running):
#   flatpak run --command=sh org.ppsspp.PPSSPP ./tools/dlc/p09_launch_isolated.sh ISO
#   ISO = ./dumps/ULUS10566-test338-voicesloud.iso (or the clean dumps/ULUS10566.iso)
# Env: TRIAL = reuse an existing trial dir (REQUIRED for the 2nd launch, so the installed data is still there);
#      default = new mktemp dir under /tmp (needs ~0.6 GB free for level 1/2, ~0.9 GB for level 3).
#      LOGLEVEL (default 4 = info: sceIoOpen/sceIoGetstat lines of ms0:/PSP/SAVEDATA/ULUS10566Data are visible).
# Memory stick root = $TRIAL/config/ppsspp/ → the install lands in $TRIAL/config/ppsspp/PSP/SAVEDATA/ULUS10566Data/.
set -eu
P=.
if [ -n "${TRIAL:-}" ] && [ -d "$TRIAL/config/ppsspp/PSP/SYSTEM" ]; then
  trial=$TRIAL
  echo "reusing $trial"
else
  trial=${TRIAL:-$(mktemp -d /tmp/claude-p09.XXXXXX)}
  mkdir -p "$trial/config/ppsspp/PSP/SYSTEM" "$trial/cache"
  cp -r "$P/codex/inbox/20261017-takeover/disposable-profile/PSP/SAVEDATA" "$trial/config/ppsspp/PSP/"
  for name in ppsspp.ini controls.ini; do
    cp "${PPSSPP_SOURCE_PSP:?Set PPSSPP_SOURCE_PSP to your source PSP profile directory}/SYSTEM/$name" "$trial/config/ppsspp/PSP/SYSTEM/$name"
  done
  sed -i "s/RemoteISOPort = 41335/RemoteISOPort = 41336/;s@CurrentDirectory = .*@CurrentDirectory = $trial@" \
    "$trial/config/ppsspp/PSP/SYSTEM/ppsspp.ini"
fi
stick="$trial/config/ppsspp/PSP/SAVEDATA"
printf 'ISOLATED_ROOT=%s\nSAVEDATA=%s\n' "$trial" "$stick"
ls -la "$stick" "$stick/ULUS10566Data" 2>/dev/null || true
n=1
while [ -e "$trial/ppsspp-$n.log" ]; do n=$((n + 1)); done
XDG_CONFIG_HOME="$trial/config" XDG_CACHE_HOME="$trial/cache" /app/bin/PPSSPPSDL --windowed \
  --loglevel="${LOGLEVEL:-4}" --log="$trial/ppsspp-$n.log" "$@"
