# usage: pp.sh press BUTTONS... | pp.sh shot NAME
cd .; export DISPLAY=${DISPLAY:-:1}

port=$(ss -ltnp 2>/dev/null | grep PPSSPPSDL | grep -o ':[0-9]*' | head -1 | tr -d :)
win() { xwininfo -root -tree | grep -i 'duodecim' | head -1 | awk '{print $1}'; }
if [ "$1" = shot ]; then mkdir -p dumps/screens/${T:-run}; import -window "$(win)" -resize 50% dumps/screens/${T:-run}/$2.png; echo dumps/screens/${T:-run}/$2.png; exit; fi
shift
for b in "$@"; do for i in 1 2 3 4 5; do timeout 60 python3 -I tools/scripts/ppctl.py $port press $b >/dev/null 2>&1 && break; sleep 3; done; sleep 0.6; done
