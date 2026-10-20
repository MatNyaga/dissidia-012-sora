"""Offline preview of the Thundaga redo (spot33_thundaga.py; notes/thunder.md). NOT gameplay footage.

  python3 preview_thundaga.py ISO OUTDIR

thundaga_paths.png  side views (ground cast / air cast, foe 8 m away) + top view around the foe:
                    canonical path (from 7 m above Sora, down-forward), Codex v1 (started above the foe, went UP),
                    new bolts (9 m above the foe, straight down, ring offsets), hit radii (bolt 0.7 m, impact 2 m).
thundaga_fall.png   the disc's real bolt mesh (MDL 30, leaf 22) + bolt texture (o12), stood vertical, falling onto a
                    1.7 m target, 3 bolts; ~1 m per 1/60 s (canonical speed measured in the Q005 trace).
Speeds / timings are estimates from the Q005 trace (canonical 0x7C4 ~1.06 m per tick); the spawn geometry follows the
decoded FUN_08ad5d70 (notes/thunder.md section 2) with the row values read from the ISO.
"""
import math
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fep as F  # noqa: E402
import fep_edit as E  # noqa: E402
import spot33_thundaga as T  # noqa: E402

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BG, FG = (16, 18, 28), (230, 232, 240)
SORA, FOE, OLD, V1, NEW, IMP = (90, 150, 255), (255, 90, 90), (150, 150, 150), (255, 150, 40), (255, 245, 120), (120, 200, 255)


def font(n):
    try:
        return ImageFont.truetype(FONT, n)
    except OSError:
        return ImageFont.load_default()


def rows(objx):
    ch = T.chunks(objx)
    mi = next(k for k, c in enumerate(ch) if c[1] == b'magi')
    return T.Magi(objx[ch[mi][2]:ch[mi][2] + ch[mi][3]])


def strike(mg):
    """v2: 0x7C4 = marker (no hit) -> its kid 0x7C5 strikes; v1: 0x7C4 strikes"""
    return 0x7C5 if mg.u16(0x7C4, 0x0a) == 0xffff else 0x7C4


def warn_delay(mg):
    return mg.triple(0x7C4, 43)[0] if strike(mg) == 0x7C5 else 0.0


def bolt_offsets(mg, row):
    """(right, fwd) ring offset + height for each bolt, as FUN_08ad0694/FUN_08ad5d70 roll them."""
    n = int(mg.triple(row, 0)[0])
    r0, _, dr = mg.triple(row, 3)
    a0, _, da = mg.triple(row, 4)
    h = mg.triple(row, 6)[0]
    out = []
    for k in range(n):
        r, a = r0 + dr * k, math.radians(a0 + da * k)
        out.append((r * math.sin(a), r * math.cos(a), h))   # rotY(a) * (0,0,r) in (right, up, fwd)
    return out


def paths_sheet(mg, path):
    W, H = 1500, 800
    im = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(im)
    f1, f2 = font(20), font(14)
    dr.text((16, 10), 'Thundaga redo (spot33_thundaga) - offline geometry, not gameplay. Side views: Sora left, foe 8 m '
            'right. 1 grid = 1 m.', fill=FG, font=f1)
    S = 34

    def side(ox, oy, title, sora_y, launcher):
        dr.text((ox, oy - 440), title, fill=FG, font=f1)
        for gx in range(-1, 12):
            dr.line([(ox + gx * S, oy - 11 * S), (ox + gx * S, oy)], fill=(34, 36, 50))
        for gy in range(0, 12):
            dr.line([(ox - S, oy - gy * S), (ox + 11 * S, oy - gy * S)], fill=(34, 36, 50))
        dr.line([(ox - S, oy), (ox + 11 * S, oy)], fill=(120, 120, 130), width=2)

        def P(x, y):
            return (ox + x * S, oy - y * S)
        dr.rectangle([P(-0.25, sora_y + 1.7), P(0.25, sora_y)], fill=SORA)
        dr.rectangle([P(7.75, 1.7), P(8.25, 0)], fill=FOE)
        dr.text(P(-0.6, sora_y + 2.3), 'Sora', fill=SORA, font=f2)
        dr.text(P(7.6, 2.3), 'foe', fill=FOE, font=f2)
        # canonical: from 7 m above Sora (or the launcher top) down-forward to the ground at the foe (Q005 trace)
        sy = sora_y + (7 if not launcher else 3.5)
        dr.line([P(0.5, sy), P(7.6, 0)], fill=OLD, width=3)
        dr.text(P(0.7, sy + 0.4), 'canonical: down-forward from above Sora', fill=OLD, font=f2)
        # Codex v1: 3 m above the foe, pitch -89.9 = UP
        dr.line([P(9.6, 3), P(9.6, 10.5)], fill=V1, width=3)
        dr.polygon([P(9.6, 10.9), P(9.35, 10.3), P(9.85, 10.3)], fill=V1)
        dr.text(P(9.8, 9.0), 'Codex v1:', fill=V1, font=f2)
        dr.text(P(9.8, 8.4), 'pitch -89.9 = UP', fill=V1, font=f2)
        # new bolts (side view: x = 8 + fwd offset)
        for k, (rt, fw, h) in enumerate(bolt_offsets(mg, strike(mg))):
            x = 8 + fw
            dr.line([P(x, min(11, h + 3.1)), P(x, 0)], fill=NEW, width=5 if k == 0 else 3)
            dr.polygon([P(x, -0.1), P(x - 0.25, 0.5), P(x + 0.25, 0.5)], fill=NEW)
            dr.ellipse([P(x - 2, 0.25), P(x + 2, -0.25)], outline=IMP)
        dr.text((ox, oy - 412), 'NEW: %d bolts from %.0f m above the foe, straight down' % (
            len(bolt_offsets(mg, strike(mg))), bolt_offsets(mg, strike(mg))[0][2]), fill=NEW, font=f2)
        if launcher:
            dr.line([P(0, sora_y + 1), P(0, sora_y + 3.5)], fill=(110, 110, 160), width=2)
            dr.text(P(0.2, sora_y + 2.6), 'launcher 0x7C8 (unchanged, delay only)', fill=(150, 150, 200), font=f2)

    side(60, 760, 'GROUND cast (block 98, magi 0x7C4)', 0.0, False)
    side(560, 760, 'AIR cast (block 101, 0x7C8 -> 0x7C9)', 4.0, True)
    # top view around the foe
    ox, oy, s = 1250, 400, 60
    dr.text((1080, 120), 'TOP view around the foe (Sora below)', fill=FG, font=f1)
    for g in range(-3, 4):
        dr.line([(ox + g * s, oy - 3 * s), (ox + g * s, oy + 3 * s)], fill=(34, 36, 50))
        dr.line([(ox - 3 * s, oy + g * s), (ox + 3 * s, oy + g * s)], fill=(34, 36, 50))
    dr.ellipse([ox - 10, oy - 10, ox + 10, oy + 10], fill=FOE)
    dr.polygon([(ox, oy + 3.4 * s), (ox - 10, oy + 3.4 * s + 18), (ox + 10, oy + 3.4 * s + 18)], fill=SORA)
    dr.text((ox + 14, oy + 3.4 * s), 'to Sora', fill=SORA, font=f2)
    for k, (rt, fw, h) in enumerate(bolt_offsets(mg, strike(mg))):
        x, y = ox + rt * s, oy - fw * s
        dr.ellipse([x - 2 * s, y - 2 * s, x + 2 * s, y + 2 * s], outline=IMP)
        dr.ellipse([x - 0.7 * s, y - 0.7 * s, x + 0.7 * s, y + 0.7 * s], outline=NEW, width=2)
        dr.text((x + 6, y - 22), 'bolt %d' % (k + 1), fill=NEW, font=f2)
    dr.text((1080, 640), 'yellow = bolt hit r 0.7 m (falls through the foe)', fill=NEW, font=f2)
    dr.text((1080, 660), 'blue = landing impact 0x7C6/0x7C7 r 2 m (HP hit too)', fill=IMP, font=f2)
    dr.text((1080, 680), 'each bolt re-reads the target position (follows the foe)', fill=FG, font=f2)
    im.save(path)


def bolt_mesh(objx):
    d = E.split(objx)[3]
    f = F.Fep(d)
    rec, blob = f.resources('MDL')[30]
    m = bytes(blob.data)
    prim, vt, st, _, cnt, off = struct.unpack_from('<6I', m, F.u32(m, 0x38))
    ext = struct.unpack_from('<3f', m, 0x40)
    vs = [struct.unpack_from('<BBHbbb', m, off + 8 * j) for j in range(cnt)]
    # local metres: x, y = across, z = long axis (= flight direction = straight down in game)
    return [(v[0] / 128, v[1] / 128, v[3] / 127 * ext[0], v[4] / 127 * ext[1], v[5] / 127 * ext[2]) for v in vs]


def fall_sheet(objx, tex_png, path, mg):
    vs = bolt_mesh(objx)
    tex = Image.open(tex_png).convert('RGBA')
    tw, th = tex.size
    scale = 1.2                                  # FEPA row 31 (leaf 22) scale
    frames = [0, 10, 20, 30, 35, 38, 44, 50, 56]
    speed = 22 / 22 * 1.06                       # m per tick at K19 22 (Q005 canonical trace)
    gap_ticks = mg.triple(strike(mg), 2)[0]       # magi times = 60/s frames (notes/thunder.md 6)
    delay = warn_delay(mg)
    offs = bolt_offsets(mg, strike(mg))
    Wp, Hp, S = 170, 520, 34
    im = Image.new('RGB', (Wp * len(frames), Hp + 60), BG)
    dr = ImageDraw.Draw(im)
    dr.text((10, 8), 'Bolt mesh MDL 30 + texture o12 (from the disc), vertical, falling onto a 1.7 m foe; '
            'frames after the cast spawn (marker); v2: warning, then bolts on the LOCKED spot', fill=FG, font=font(16))
    for i, t in enumerate(frames):
        ox, oy = i * Wp + Wp // 2, Hp + 20
        dr.line([(i * Wp + 6, oy), ((i + 1) * Wp - 6, oy)], fill=(120, 120, 130), width=2)
        dr.rectangle([ox - 8, oy - 1.7 * S, ox + 8, oy], fill=FOE)
        dr.text((i * Wp + 8, 34), 't = %d' % t, fill=FG, font=font(18))
        if t < delay:                                # v2 warning: half-size bolt column standing on the spot
            for j in range(len(vs) - 2):
                tri = vs[j:j + 3]
                pts = [(ox + v[2] * 0.6 * S, oy - (0 - v[4] * 0.6) * S) for v in tri]
                if len(set(pts)) < 3:
                    continue
                dr.polygon(pts, fill=(120, 150, 230))
            dr.text((i * Wp + 8, 60), 'warning', fill=(150, 180, 255), font=font(14))
        for k, (rt, fw, h) in enumerate(offs):
            tk = t - delay - k * gap_ticks
            if tk < 0:
                continue
            y0 = h - speed * tk                      # bolt centre height
            if y0 < -0.2:                             # landed: impact flash
                if tk * speed - h < 6:
                    x = ox + rt * S
                    dr.ellipse([x - 30, oy - 40, x + 30, oy + 6], fill=(200, 225, 255))   # leaf-23 flash (approx.)
                continue
            x = ox + rt * S
            for j in range(len(vs) - 2):
                tri = vs[j:j + 3]
                pts = [(x + v[2] * scale * S, oy - (y0 - v[4] * scale) * S) for v in tri]
                if len(set(pts)) < 3:
                    continue
                u = sum(v[0] for v in tri) / 3
                vv = sum(v[1] for v in tri) / 3
                c = tex.getpixel((min(tw - 1, int(u * tw)), min(th - 1, int(vv * th))))
                a = c[3] / 255
                col = tuple(int(min(255, BG[n] + ch * a * 2.2 + 60 * a)) for n, ch in enumerate(c[:3]))   # additive
                dr.polygon([(px, max(48, py)) for px, py in pts], fill=col)
            dr.ellipse([x - 4, oy - y0 * S - 4, x + 4, oy - y0 * S + 4], fill=NEW)
        dr.rectangle([i * Wp, oy + 1, (i + 1) * Wp, Hp + 60], fill=(30, 30, 38))      # the floor hides the rest
        dr.line([(i * Wp + 6, oy), ((i + 1) * Wp - 6, oy)], fill=(120, 120, 130), width=2)
    im.save(path)


def main():
    iso, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    from comb_patch import pkg_offset, read_at, use_iso
    use_iso(iso)
    st, sz = pkg_offset(T.FILE)
    with open(iso, 'rb') as f:
        objx = read_at(f, st, sz)
    mg = rows(objx)
    paths_sheet(mg, os.path.join(outdir, 'thundaga_paths.png'))
    # bolt texture o12 (TEX key 0x98012812) as PNG via fep_dump
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'f.objx')
        open(p, 'wb').write(objx)
        subprocess.run([sys.executable, '-I', os.path.join(HERE, 'fep_dump.py'), p, '--png', t], check=True,
                       capture_output=True)
        fall_sheet(objx, os.path.join(t, 'fep_98012812.png'), os.path.join(outdir, 'thundaga_fall.png'), mg)
    print('previews ->', outdir)


if __name__ == '__main__':
    main()
