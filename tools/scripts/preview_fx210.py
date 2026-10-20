import sys, struct, math
sys.path.insert(0, './tools/scripts')
import fep as F, fep_edit as E
from PIL import Image, ImageDraw
R = './'
o = E.load_objx(R + 'dumps/ULUS10566-test210-fx.iso', 'obj/p_sev120.objx')
d = E.split(o)[3]; f = F.Fep(d)
rec, blob = f.resources('MDL')[30]; m = bytes(blob.data)
prim, vt, st, _, cnt, off = struct.unpack_from('<6I', m, F.u32(m, 0x38))
vs = [struct.unpack_from('<BBHbbb', m, off + 8 * j) for j in range(cnt)]
tex = Image.open(R + 'dumps/renders/kh2fx/test210/tex/fep_98012812.png').convert('RGB')
tw, th = tex.size
W, H = 900, 520
img = Image.new('RGB', (W, H), (18, 18, 28))
dr = ImageDraw.Draw(img)
dr.text((10, 8), 'Thundaga test210: Lightning\'s bolt mesh (her MDL 57, 198-vertex strip) in Sora MDL 30, her bolt texture o12. Views: side (z down), front, top', fill=(230, 230, 230))
def panel(ox, oy, sc, proj, label):
    dr.text((ox - 60, oy - 230), label, fill=(200, 200, 255))
    for j in range(cnt - 2):
        tri = vs[j:j + 3]
        pts = [proj(v) for v in tri]
        if len(set(pts)) < 3: continue
        u = sum(v[0] for v in tri) / 3 / 128; vv = sum(v[1] for v in tri) / 3 / 128
        col = tex.getpixel((min(tw - 1, int(u * tw)), min(th - 1, int(vv * th))))
        col = tuple(min(255, int(c * 1.6) + 30) for c in col)
        dr.polygon([(ox + p[0] * sc, oy + p[1] * sc) for p in pts], fill=col)
# after the swap: z = long axis (flight = straight down in game)
panel(150, 260, 1.7, lambda v: (v[3], v[5]), 'side x/z')
panel(450, 260, 1.7, lambda v: (v[4], v[5]), 'side y/z')
panel(750, 260, 1.7, lambda v: (v[3], v[4]), 'top x/y')
img.save(R + 'dumps/renders/kh2fx/test210/thundaga_bolt_preview.png')

# Firaga schedule preview (top view, ring around Sora, frames)
sys.path.insert(0, R + 'tools/scripts')
import spot33_firefx as FF
img = Image.new('RGB', (W, 330), (18, 18, 28)); dr = ImageDraw.Draw(img)
fire = Image.open(R + 'dumps/renders/kh2fx/test210/tex/fep_9801280f.png').convert('RGB').crop((0, 0, 64, 64)).resize((26, 26))
dr.text((10, 8), 'Firaga test210 (top view, Sora = blue dot): two comets race round (5 frames each), ring flies out at 47, burst at 48', fill=(230, 230, 230))
sched = FF.swirl_schedule()
pos = {}
for k in range(len(FF.SWIRL_ROWS)):
    a = 2 * math.pi * k / len(FF.SWIRL_ROWS); pos[FF.SWIRL_ID0 + k] = (FF.SWIRL_RADIUS * math.cos(a), FF.SWIRL_RADIUS * math.sin(a), FF.SWIRL_LIFE)
for k in range(len(FF.OUTER_ROWS)):
    a = 2 * math.pi * k / len(FF.OUTER_ROWS) + math.pi / len(FF.OUTER_ROWS); pos[FF.OUTER_ID0 + k] = (FF.OUTER_RADIUS * math.cos(a), FF.OUTER_RADIUS * math.sin(a), FF.OUTER_LIFE)
for n, t in enumerate((18, 26, 34, 42, 50, 56)):
    cx, cy = 80 + n * 145, 180
    dr.text((cx - 20, 60), 'frame %d' % t, fill=(200, 200, 255))
    dr.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=(80, 120, 255))
    for fr, i in sched:
        if i in pos and fr <= t < fr + pos[i][2]:
            x, y, _ = pos[i]
            img.paste(fire, (int(cx + x * 30) - 13, int(cy + y * 30) - 13))
        if i == FF.BURST[1] and fr <= t < fr + 20:
            dr.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), outline=(255, 150, 60), width=3)
img.save(R + 'dumps/renders/kh2fx/test210/firaga_preview.png')
print('ok')
