#!/bin/bash
# Start PPSSPP with ISO and drive into a Quick Battle (#33 vs Lightning, 100% test save) with go_battle.py, which
# recognises every screen before pressing (stops on unknown / Extras / Data Install / Story Mode).
#   tools/scripts/go_battle.sh dumps/ULUS10566-testNN.iso [T]     pictures: dumps/screens/$T/go_*.png
cd "$(dirname "$0")/../.."
ISO=$1; export T=${2:-$(basename $ISO .iso | sed 's/ULUS10566-//')} DISPLAY=${DISPLAY:-:1}
pid=$(pgrep -x PPSSPPSDL || true); [ -n "$pid" ] && { kill -TERM $pid; sleep 4; }
(setsid nohup flatpak run org.ppsspp.PPSSPP $PPARGS $PWD/$ISO >${PPLOG:-/dev/null} 2>&1 < /dev/null &)
sleep 20
python3 -I tools/scripts/go_battle.py dumps/screens/$T   # env STOP_AFTER passes through
