#!/bin/bash
# Animated GIF of a hand-made pose script (tools/poses/*.py) on Sora.
#   tools/scripts/preview_pose.sh tools/poses/win_fire.py LABEL [STEP] [VIEW]
# Output: dumps/renders/poses/pose_<LABEL>.gif   (VIEW: q = front 3/4 (default), front, side, rside)
set -e
cd "$(dirname "$0")/../.."
script=$1; label=$2; step=${3:-3}; view=${4:-q}
out=dumps/renders/poses; tmp=$out/tmp_pose_$label; mkdir -p $out $tmp
python3 -I tools/scripts/pose_author.py $script dumps/models/sora_final.gmo $tmp/m.gmo ${SLOT:-_910A}
cp dumps/models/sora/rtn/*.png dumps/models/sora/rtn/sora_final.bin dumps/models/sora/rtn/sora_final.gltf $tmp/
python3 -I tools/scripts/gmo_anim2gltf.py $tmp/m.gmo $tmp/sora_final.gltf $tmp/anim.gltf ${SLOT:-_910A} | head -1
n=$(python3 -I tools/scripts/gmo_motion.py list $tmp/m.gmo | awk -v s=${SLOT:-_910A} '$2==s{split($4,a,"-"); print a[2]}')
frames=$(python3 -c "print(','.join(str(f) for f in range(0,$n+1,$step)))")
VIEWS=$view flatpak run org.blender.Blender -b --python $PWD/tools/blender/render_anim.py -- $PWD/$tmp/f $PWD/$tmp/anim.gltf ${SLOT:-_910A} $frames ${DIST:-3.4} > $tmp/blender.log 2>&1
python3 -I - "$tmp" "$out/pose_$label.gif" "$label" "$step" "$view" <<'EOF'
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
EOF
[ -n "$KEEP" ] || rm -rf $tmp
