#!/bin/bash
# Animated GIF of one motion slot of a GMO on Sora's skin.  tools/scripts/preview_slot.sh MODEL.gmo SLOT LABEL [STEP] [VIEW]
set -e
cd "$(dirname "$0")/../.."
gmo=$1; slot=$2; label=$3; step=${4:-3}; view=${5:-q}
out=dumps/renders/poses; tmp=$out/tmp_slot_$label; mkdir -p $out $tmp
cp dumps/models/sora/rtn/*.png dumps/models/sora/rtn/sora_final.bin dumps/models/sora/rtn/sora_final.gltf $tmp/
python3 -I tools/scripts/gmo_anim2gltf.py $gmo $tmp/sora_final.gltf $tmp/anim.gltf $slot | head -1
n=$(python3 -I tools/scripts/gmo_motion.py list $gmo | awk -v s=$slot '$2==s{split($4,a,"-"); print a[2]}')
frames=$(python3 -c "print(','.join(str(f) for f in range(0,int($n)+1,$step)))")
VIEWS=$view flatpak run org.blender.Blender -b --python $PWD/tools/blender/render_anim.py -- $PWD/$tmp/f $PWD/$tmp/anim.gltf $slot $frames ${DIST:-3.4} > $tmp/blender.log 2>&1
python3 -I - "$tmp" "$out/slot_$label.gif" "$label" "$step" "$view" <<'PY'
import sys, glob
from PIL import Image, ImageDraw
tmp, out, label, step, view = sys.argv[1:6]
ims = []
for f in sorted(glob.glob(tmp + '/f_f*_%s.png' % view)):
    im = Image.open(f).convert('RGB').resize((300, 372))
    ImageDraw.Draw(im).text((8, 8), label, fill=(255, 255, 255))
    ims.append(im)
ims[0].save(out, save_all=True, append_images=ims[1:], duration=int(1000 / 30 * int(step)), loop=0)
print(out, len(ims), 'frames')
PY
[ -n "$KEEP" ] || rm -rf $tmp
