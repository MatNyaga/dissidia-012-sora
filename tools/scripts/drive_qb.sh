#!/bin/bash
# Launch PPSSPP on an ISO and drive: title -> Load Game -> Battle Mode -> Quick Battle 1-on-1 -> pick a grid
# cell -> CPU Lightning -> Order's Sanctuary + Minimal -> battle. Screenshots go to OUT_DIR.
# Usage: drive_qb.sh ISO OUT_DIR [CELL_MOVES]   (CELL_MOVES from Lightning, default "down down" = #33's cell;
#                                                 real Cloud = "down right right right right right right")
# Needs: PPSSPP settings "Allow remote debugger" + cheats on (they persist), DISPLAY=:1, tools/scripts/ppctl.py.
ISO=$1; OUT=$2; MOVES=${3:-down down}
HERE=$(cd "$(dirname "$0")" && pwd)
export DISPLAY=${DISPLAY:-:1}
mkdir -p "$OUT"
pid=$(pgrep -x PPSSPPSDL); [ -n "$pid" ] && kill -TERM $pid && sleep 5
setsid nohup flatpak run org.ppsspp.PPSSPP "$ISO" >/dev/null 2>&1 < /dev/null &
sleep 20
port=$(ss -ltnp 2>/dev/null | grep PPSSPPSDL | grep -o ':[0-9]*' | head -1 | tr -d :)
win() { xwininfo -root -tree | grep -i 'duodecim' | head -1 | awk '{print $1}'; }
p() { for i in 1 2 3 4 5; do timeout 60 python3 -I "$HERE/ppctl.py" "$port" press "$@" >/dev/null 2>&1 && return 0; sleep 3; done; echo "press $* failed"; }
shot() { import -window "$(win)" -resize 40% "$OUT/$1.png"; }
p cross; sleep 6; p start; sleep 8; p start; sleep 5; shot 01-load
p cross; sleep 7; p circle; sleep 8; shot 02-menu
p down cross; sleep 3; p cross; sleep 6; shot 03-select
p $MOVES; sleep 1; shot 04-cell
p cross; sleep 2; p cross; sleep 3; p cross; sleep 2; p cross; sleep 4
p down left left left left; sleep 0.5; p down left left left left; sleep 0.5; p up up; sleep 1; shot 05-setup
p cross; sleep 8; p cross; sleep 6; p cross; sleep 22; shot 06-battle
echo "port=$port"
