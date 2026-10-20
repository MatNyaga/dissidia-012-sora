#!/bin/bash
# Contact sheets of KH2 Limit Form (P_EX100_KH1F.mset) animations on Sora's Dissidia model (notes/kh2-limit.md).
#   tools/scripts/kh2limit_sheets.sh IDX [IDX...]      (bins from dumps/kh2anim_kh1f/, baked with P_EX100.mdlx: same 228 bones)
# Output: dumps/renders/kh2limit/<IDX>_<NAME>.png (12 frames, 3/4 view, frame numbers) + .gif
set -e
cd "$(dirname "$0")/../.."
out=dumps/renders/kh2limit; mkdir -p $out
base=$PWD/$out/tmp_$$; mkdir -p $base; cp dumps/models/sora_final.gmo $base/model.gmo        # private copy (a parallel build rewrites it); inside the project: flatpak Blender cannot read /tmp
cp dumps/models/sora/rtn/*.png dumps/models/sora/rtn/sora_final.bin dumps/models/sora/rtn/sora_final.gltf $base/
for idx in "$@"; do
    bin=$(ls dumps/kh2anim_kh1f/$(printf %03d $idx)_*.bin | head -1); name=$(basename $bin .bin)
    tmp=$base/$idx; mkdir -p $tmp
    python3 -I tools/scripts/kh2_retarget.py $base/model.gmo dumps/models/sora/fitn/sora_fit.map.json $bin $tmp/m.gmo _910A >/dev/null
    cp $base/*.png $base/sora_final.bin $base/sora_final.gltf $tmp/
    python3 -I tools/scripts/gmo_anim2gltf.py $tmp/m.gmo $tmp/sora_final.gltf $tmp/anim.gltf _910A >/dev/null
    n=$(python3 -c "import struct;print(struct.unpack('<ii',open('$bin','rb').read(8))[1])")
    frames=$(python3 -c "n=$n;k=min(12,n);print(','.join(str(round(i*(n-1)/max(1,k-1))) for i in range(k)))")
    VIEWS=q flatpak run org.blender.Blender -b --python $PWD/tools/blender/render_anim.py -- $tmp/f $tmp/anim.gltf _910A $frames 3.4 > $tmp/blender.log 2>&1
    python3 -I - "$tmp" "$out/$name" "$name" "$frames" <<'PY'
import sys, glob, re
from PIL import Image, ImageDraw
tmp, out, label, frames = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(',')
fs = sorted(glob.glob(tmp + '/f_f*_q.png'), key=lambda f: int(re.search(r'_f(\d+)_q', f).group(1)))
ims = []
for f in fs:
    im = Image.open(f).convert('RGB').resize((210, 260))
    ImageDraw.Draw(im).text((6, 6), '%s f%s' % (label, re.search(r'_f(\d+)_q', f).group(1)), fill=(255, 255, 255))
    ims.append(im)
cols = 6; rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * 212, rows * 262), (40, 40, 40))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * 212, (i // cols) * 262))
sheet.save(out + '.png')
ims[0].save(out + '.gif', save_all=True, append_images=ims[1:], duration=150, loop=0)
print(out + '.png', len(ims))
PY
done
rm -rf $base
