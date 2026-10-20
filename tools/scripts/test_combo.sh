#!/bin/bash
# Put MODEL.gmo on a copy of BASE.iso as #33's model, start PPSSPP, drive into a Quick Battle (#33 vs Lightning,
# Order's Sanctuary, Minimal) and run ppcombo.py with BUTTONS (default ground combo). Prints which tries hit.
#   tools/scripts/test_combo.sh BASE.iso MODEL.gmo [BUTTONS] [TRIES]
set -e
cd "$(dirname "$0")/../.."
BASE=$1; MODEL=$2; BUTTONS=${3:-circle,circle,circle,circle,circle}; TRIES=${4:-4}
ISO=dumps/ULUS10566-exp-run.iso
for p in $(pgrep -x PPSSPPSDL); do kill -TERM $p; done; sleep 4; for p in $(pgrep -x PPSSPPSDL); do kill -KILL $p; done
cp "$BASE" $ISO
python3 -I tools/scripts/pkg_put.py $ISO obj/P_SEV120_1P.gmo "$MODEL" >/dev/null
export DISPLAY=:1 T=exp
(setsid nohup flatpak run org.ppsspp.PPSSPP $PWD/$ISO >/dev/null 2>&1 < /dev/null &)
sleep 22
P=tools/scripts/pp.sh
$P press cross; sleep 6; $P press start; sleep 8; $P press start; sleep 5; $P press cross; sleep 7; $P press circle; sleep 8
$P press down cross; sleep 4; $P press cross; sleep 7; $P press down down down right right right right right; sleep 2
$P press cross; sleep 2; $P press cross; sleep 3; $P press cross; sleep 2; $P press cross; sleep 4
$P press down right right right right right right right right right right right down left left left left up up; sleep 1
$P press cross; sleep 8; $P press cross; sleep 4; $P press cross; sleep 12
port=$(ss -ltnp 2>/dev/null | grep PPSSPPSDL | grep -o ':[0-9]*' | head -1 | tr -d :)
GAP=${GAP:-0.6} timeout 300 python3 -I tools/scripts/ppcombo.py $port 33 31 ${DIST:-1.5} $TRIES $BUTTONS
