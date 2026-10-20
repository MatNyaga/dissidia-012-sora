#!/bin/bash
# Animated GIF of Sora (his Dissidia model) doing a KH2 motion, to choose poses/moves.
#   tools/scripts/preview_kh2_motion.sh KH2_INDEX LABEL [STEP]
# KH2_INDEX = slot in dumps/kh2anim/list_named.txt (baked first if missing). Output: dumps/renders/poses/<INDEX>_<LABEL>.gif
set -e
cd "$(dirname "$0")/../.."
idx=$1; label=$2; step=${3:-3}
out=dumps/renders/poses; tmp=$out/tmp_$idx; mkdir -p $out $tmp
bin=${BIN:-$(ls dumps/kh2anim/$(printf %03d $idx)_*.bin 2>/dev/null | head -1)}
if [ -z "$bin" ]; then
    DOTNET_ROOT=$PWD/tools/dotnet-sdk DOTNET_ROLL_FORWARD=Major tools/dotnet-sdk/dotnet tools/kh2bake/bake/out/bake.dll \
        kh2_export/model/P_EX100.mdlx kh2_export/raw/kh2_sixth/original/obj/P_EX100.mset dumps/kh2anim $idx >/dev/null
    bin=$(ls dumps/kh2anim/$(printf %03d $idx)_*.bin | head -1)
fi
python3 -I tools/scripts/kh2_retarget.py dumps/models/sora_final.gmo dumps/models/sora/fitn/sora_fit.map.json $bin $tmp/m.gmo _910A >/dev/null
cp dumps/models/sora/rtn/*.png dumps/models/sora/rtn/sora_final.bin dumps/models/sora/rtn/sora_final.gltf $tmp/
python3 -I tools/scripts/gmo_anim2gltf.py $tmp/m.gmo $tmp/sora_final.gltf $tmp/anim.gltf _910A >/dev/null
n=$(python3 -c "import struct;d=open('$bin','rb').read(12);print(struct.unpack('<ii',d[:8])[1])")
frames=$(python3 -c "print(','.join(str(f) for f in range(0,$n,$step)))")
VIEWS=q flatpak run org.blender.Blender -b --python $PWD/tools/blender/render_anim.py -- $PWD/$tmp/f $PWD/$tmp/anim.gltf _910A $frames 2.8 > $tmp/blender.log 2>&1
python3 -I - "$tmp" "$out/$(printf %03d $idx)_$label.gif" "$label" "$step" <<'EOF'
import sys, glob
from PIL import Image, ImageDraw
tmp, out, label, step = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
ims = []
for f in sorted(glob.glob(tmp + '/f_f*_q.png')):
    im = Image.open(f).convert('RGB').resize((300, 372))
    ImageDraw.Draw(im).text((8, 8), label, fill=(255, 255, 255))
    ims.append(im)
ims[0].save(out, save_all=True, append_images=ims[1:], duration=int(1000 / 30 * step), loop=0)
print(out, len(ims), 'frames')
EOF
[ -n "$KEEP" ] || rm -rf $tmp
