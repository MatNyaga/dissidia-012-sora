#!/bin/bash
# Record ONLY the PPSSPP game window (no other windows, no desktop) to a video.
#   tools/scripts/record_game.sh [SECONDS]        (default 20; stop early with Ctrl+C)
# Output: dumps/screens/rec_<date-time>.mp4  (Claude can read frames from it)
cd "$(dirname "$0")/../.."
export DISPLAY=${DISPLAY:-:1}
win=$(xwininfo -root -tree | grep -i 'duodecim' | head -1 | awk '{print $1}')
[ -z "$win" ] && { echo "PPSSPP game window not found"; exit 1; }
geo=$(xwininfo -id $win | awk '/Width:/{w=$2} /Height:/{h=$2} END{print w"x"h}')
mkdir -p dumps/screens
out=dumps/screens/rec_$(date +%Y%m%d-%H%M%S).mp4
echo "recording the game window ($geo) for ${1:-20} s -> $out"
ffmpeg -hide_banner -loglevel error -f x11grab -window_id $win -video_size $geo -framerate 30 -i $DISPLAY \
    -t ${1:-20} -vf "scale=trunc(iw/4)*2:trunc(ih/4)*2" -c:v libx264 -preset veryfast -crf 26 -pix_fmt yuv420p "$out"
echo "saved $out"
