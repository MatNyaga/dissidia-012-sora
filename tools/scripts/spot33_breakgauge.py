"""Owner 33's EX Burst gauge = KH2-style yellow "BREAK" gauge (Mat/Codex, Q-20261015-CODEX-004).

The "Rapidly tap ◯" burst UI (◯ icons, gauge frame, gauge fill, gauge label) is drawn from the ATTACKER's own fighter
file (controller ctrl[3] = *(fighter+0x390)+0xd0; FUN_088daa40/68 create the sprites), so editing Sora's
obj/p_sev120.objx changes only his gauge — Cloud and everyone else keep theirs (no code):
  * spec chunk type 3 ("mlng", 6 language blocks, all the same GIM): 64x128 INDEX8 atlas; the label sprite is
    (29,118)-(63,127) = "LIMIT" -> redrawn as "BREAK" in the same 2-px stroke / black outline / right-bottom shadow /
    drop-shadow palette indices (130 core, 8 outline, 12 shadow, 3 drop, 222 background);
  * spec chunk type 17 ("mlng", 6 SEQ layouts): sprite records 9-15 = the gauge FILL sprite (3,116)-(4,123) in seven
    vertex colours (pink, orange, yellow, green, blue, blue, violet: the fill changes colour as it grows) -> all
    yellow (TINT, 0x80 = 1.0 like the other sprites' 0x80808080).
Re-runnable; asserts the original (Cloud copy) bytes or our own result before writing; sizes never change.

  python3 -I spot33_breakgauge.py ISO [--dry] [--png OUT.png]
"""
import hashlib
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from spot33_combos import rebuild_arc  # noqa: E402

FILE = 'obj/p_sev120.objx'
GIM_SHA = '9bfd531db00c'                    # original atlas (each language block), sha256 prefix
SEQ_SHA = '4adc9ce5caa9'                    # original layout (each language block)
TINT = bytes((0xff, 0xdc, 0x28, 0xff))      # KH2 Limit-gauge yellow (R, G, B, A; 0x80 = 1.0)
FILL_RECORDS = range(9, 16)
LABEL = (29, 117, 63, 126)                  # x0, y0 (top outline row), x1 (exclusive), y1 (drop-shadow row, incl.)
CORE, OUTLINE, SHADOW, DROP, BG = 0x82, 0x08, 0x0C, 0x03, 0xDE
GLYPHS = {'B': ['XXXX.', 'XX.XX', 'XXXX.', 'XX.XX', 'XX.XX', 'XXXX.'],
          'R': ['XXXX.', 'XX.XX', 'XX.XX', 'XXXX.', 'XX.XX', 'XX.XX'],
          'E': ['XXXXX', 'XX...', 'XXXX.', 'XX...', 'XX...', 'XXXXX'],
          'A': ['.XXX.', 'XX.XX', 'XX.XX', 'XXXXX', 'XX.XX', 'XX.XX'],
          'K': ['XX.XX', 'XX.XX', 'XXXX.', 'XXXX.', 'XX.XX', 'XX.XX']}


def label_pixels(word='BREAK'):
    """-> {(x, y): index} for the label rows y 117..125 inside x 29..62"""
    w = len(word) * 6 - 1
    x_start = LABEL[0] + 1 + ((LABEL[2] - LABEL[0] - 2) - w) // 2
    core = set()
    for i, ch in enumerate(word):
        for r, row in enumerate(GLYPHS[ch]):
            for c, v in enumerate(row):
                if v == 'X':
                    core.add((x_start + i * 6 + c, 118 + r))
    out = {}
    for y in range(LABEL[1], LABEL[3] + 1):
        for x in range(LABEL[0], LABEL[2]):
            out[(x, y)] = BG
    for (x, y) in core:
        out[(x, y)] = CORE
    for (x, y) in core:                       # outline: black above/left, shadow right/below (like "LIMIT")
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                p = (x + dx, y + dy)
                if p in core or p not in out:
                    continue
                shade = SHADOW if (dx > 0 or dy > 0) and not (dx < 0 or dy < 0) else OUTLINE
                if out[p] in (BG, DROP) or (out[p] == SHADOW and shade == OUTLINE):
                    out[p] = shade
    for (x, y), v in list(out.items()):       # drop shadow one row under the lowest outline/shadow
        if v in (OUTLINE, SHADOW) and (x, y + 1) in out and out[(x, y + 1)] == BG and y + 1 == 125:
            out[(x, y + 1)] = DROP
    return out


def mlng_blocks(c):
    n = struct.unpack_from('<I', c, 4)[0]
    offs = struct.unpack_from('<%dI' % (2 * n), c, 8)
    return [(offs[i], offs[n + i]) for i in range(n)]


def patch_gim(g):
    hb = 0x30
    assert struct.unpack_from('<H', g, hb)[0] == 4, 'image block'
    h0 = hb + struct.unpack_from('<I', g, hb + 12)[0]
    fmt, order, w, h = struct.unpack_from('<4H', g, h0 + 4)
    assert (fmt, order, w, h) == (5, 0, 64, 128), (fmt, order, w, h)
    px = h0 + struct.unpack_from('<I', g, h0 + 0x1C)[0]
    g = bytearray(g)
    for (x, y), v in label_pixels().items():
        g[px + y * 64 + x] = v
    return bytes(g)


def patch_seq(q):
    assert q[:4] == b'SEQ ' and struct.unpack_from('<I', q, 8)[0] == 17
    q = bytearray(q)
    for r in FILL_RECORDS:
        o = 0x24 + r * 0x20
        assert struct.unpack_from('<4H', q, o) == (3, 116, 4, 123), 'record %d is not the gauge fill' % r
        q[o + 16:o + 32] = TINT * 4
    return bytes(q)


def main():
    iso, dry = sys.argv[1], '--dry' in sys.argv
    use_iso(iso)
    st, sz = pkg_offset(FILE)
    with open(iso, 'rb') as f:
        d = read_at(f, st, sz)
    n, = struct.unpack_from('<I', d, 4)
    ch = [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]
    ig = next(k for k, c in enumerate(ch) if c[0] == 3 and c[1] == b'spec')
    iq = next(k for k, c in enumerate(ch) if c[0] == 17 and c[1] == b'spec')
    news = {}
    for idx, fn, sha in ((ig, patch_gim, GIM_SHA), (iq, patch_seq, SEQ_SHA)):
        c = bytearray(d[ch[idx][2]:ch[idx][2] + ch[idx][3]])
        for o, size in mlng_blocks(c):
            blk = bytes(c[o:o + size])
            if hashlib.sha256(blk).hexdigest()[:12] == sha:
                new = fn(blk)
            else:
                new = fn(blk)
                assert new == blk, 'spec type %d block at %#x is neither the original nor ours' % (ch[idx][0], o)
            c[o:o + size] = new
        if bytes(c) != d[ch[idx][2]:ch[idx][2] + ch[idx][3]]:
            news[idx] = bytes(c)
    if '--png' in sys.argv:
        from PIL import Image
        c = news.get(ig, d[ch[ig][2]:ch[ig][2] + ch[ig][3]])
        o, size = mlng_blocks(c)[0]
        tmp = tempfile.mktemp(suffix='.gim')
        open(tmp, 'wb').write(c[o:o + size])
        out = sys.argv[sys.argv.index('--png') + 1]
        subprocess.run([sys.executable, '-I', os.path.join(HERE, 'gim.py'), tmp, out], check=True, capture_output=True)
        os.unlink(tmp)
        im = Image.open(out).convert('RGBA')
        bg = Image.new('RGBA', im.size, (40, 40, 70, 255))
        bg.alpha_composite(im)
        bg.resize((im.size[0] * 4, im.size[1] * 4), Image.NEAREST).save(out)
        print('preview', out)
    if not news:
        print('BREAK gauge: already there')
        return
    print('BREAK gauge: label "BREAK" (6 language atlases) + yellow fill (7 records x 6 layouts)%s' % (' (dry)' if dry else ''))
    if dry:
        return
    out = rebuild_arc(d, news)
    assert len(out) == len(d)
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'f.objx')
        open(p, 'wb').write(out)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main()
