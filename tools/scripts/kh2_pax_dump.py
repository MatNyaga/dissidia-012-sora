"""Read-only dump of a KH2 PAX effect pack (BAR entry type 18, e.g. obj/P_EX100.a.us) -- notes/kh2-effects.md.

  python3 -I kh2_pax_dump.py FILE                     # elements, DPX effects, DPD contents summary
  python3 -I kh2_pax_dump.py FILE --elem 44 45 48     # + full particle programs of those PAX elements
  python3 -I kh2_pax_dump.py FILE --png OUTDIR        # textures of every DPD as PNG (+ shapes.txt)

Layout (OpenKH OpenKh.Kh2 Pax/Dpx/Dpd/DpdPData, decompiled from tools/openkh):
  PAX  "PAX_", u32 nameOff, u32 nElem, u32 dpxOff; nElem x 80 B elements; char[128] name; DPX
  elem u16 effectNo (-> DPX effect), u16 id (= motion trigger t1 param), u8 group, u8 fadeFrames, s16 bone
       (0x4000|n = special: root/world ...), u64 category, u32 flags, f32 startWait, s32 se, f32 T xzy, R xzy, S xzy, bonepos
  DPX  i32 ver(130), 2 res, nEffects; nEffects x 32 B {u32 dpdOff, u32 pdataIndex, u32 effectNo, ...}; u32 nDpd, offs[]
  DPD  u32 150; 5 offset lists: particle-data, textures, shapes(sprite anims), models(OMD meshes), vsf; EtcData
  pdata = 272 B header (bbox, offset, angle, scale, abUseTexture[16], abUseShape[16], abUseRsd[16](models),
          abUseVsf[16], ...) + program file: entries (= emitter/particle layers) each with a list of
          "ppp" programs (type, paramSize, nEntries, params, useVal) = the per-frame behaviour script.
  texture = PS2 GS: 0x13 PSMT8 (256-colour CLUT, CSM1 swizzled) / 0x14 PSMT4, alpha 0x80 = opaque.
"""
import struct, sys, os

PPP = ('DummyFunc', 'KeThRes', 'KeThRes8', 'KeThRes8x4', 'KeThRes8x128', 'KeThRes16', 'KeThRes16x4', 'KeThRes16x64',
       'KeThRes24', 'KeThRes24x4', 'KeThRes32', 'KeThRes32x4', 'KeThRes32x32', 'KeThRes40', 'KeThRes40x4',
       'KeThRes48', 'KeThRes48x4', 'KeThRes64', 'KeThRes64x4', 'KeThRes64x16', 'KeThRes128', 'KeThRes128x4',
       'KeThRes128x8', 'KeThRes255', 'KeThRes255x4', 'KeHitBall', 'KeGrvTgt', 'Accele', 'AngAccele', 'SclAccele',
       'ColAccele', 'EiWfacc', 'KeHmgEff', 'KeGrvEff', 'KeHitChkPxB', 'Move', 'AngMove', 'SclMove', 'ColMove',
       'Point', 'Angle', 'Scale', 'Color', 'PObjPoint', 'VertexAttend', 'EiWindFun', 'KeMvYpEff', 'KeDrct', 'VtMime',
       'KeTkFade', 'RandFloat', 'RandUpFloat', 'RandDownFloat', 'RandChar', 'RandUpChar', 'RandDownChar', 'RandShort',
       'RandUpShort', 'RandDownShort', 'RandInt', 'RandUpInt', 'RandDownInt', 'RandFV', 'RandUpFV', 'RandDownFV',
       'RandIV', 'RandUpIV', 'RandDownIV', 'RandCV', 'RandUpCV', 'RandDownCV', 'RandHCV', 'RandUpHCV', 'RandDownHCV',
       'SRandFV', 'SRandUpFV', 'SRandDownFV', 'SRandCV', 'SRandUpCV', 'SRandDownCV', 'SRandHCV', 'SRandUpHCV',
       'SRandDownHCV', 'SMatrix', 'KeMatSN', 'Matrix', 'MatrixXYZ', 'MatrixXZY', 'MatrixYZX', 'MatrixYXZ',
       'MatrixZXY', 'MatrixZYX', 'MatrixLoc', 'MatrixScl', 'MatrixFront', 'RyjMatrixNoRot', 'KeMatPht',
       'RyjMatrixWorld', 'RyjMatrixWorldXYZ', 'RyjMatrixWorldXZY', 'RyjMatrixWorldYXZ', 'RyjMatrixWorldYZX',
       'RyjMatrixWorldZXY', 'RyjMatrixWorldZYX', 'ParMatrix', 'KeParMatR', 'ChrSclXYZMatrix', 'ChrSclXZMatrix',
       'ChrSclYMatrix', 'ChrYSclXYZMatrix', 'ChrXSclXYZMatrix', 'DrawMatrix', 'DrawMatrixFront', 'DrawMatrixNoRot',
       'DrawMatrixWood', 'KeDMat', 'KeDMatFr', 'KeDMatPht', 'KeDMatPhtFr', 'RyjDrawMatrixWorld',
       'RyjDrawMatrixWorldFront', 'RyjDrawMatrixWorldNoRot', 'RyjDrawMatrixWorldWood', 'KeZCrct', 'KeZCrctShp',
       'KeThTp', 'KeThTp2', 'KeThSft', 'KeTh', 'DrawMdlBS', 'DrawMdl', 'DrawMdlSemi', 'DrawMdlTs', 'DrawMdl2',
       'DrawMdlSemi2', 'DrawMdlTs2', 'DrawMdl3', 'DrawMdlSemi3', 'DrawMdlTs3', 'DrawMdlSea', 'DrawShape',
       'DrawShapeX', 'DrawShapeField', 'KeMdlBmp', 'KeMdlDtt', 'KeMdlTfd', 'KeMdlTfdUv', 'KeMdlTfd2', 'KeMdlTfdUv2',
       'KeMdlTfd3', 'KeMdlTfdUv3', 'KeShpTail', 'KeShpTailX', 'KeShpTail2', 'KeShpTail2X', 'KeShpTail3',
       'KeShpTail3X', 'KeShpTailPht', 'KeShpTailLc', 'KeShpDtt', 'RyjDrawShipoly', 'DrawHook', 'SDMatrix', 'SCMatrix',
       'WMatrix', 'WMatrixXYZ', 'WMatrixXZY', 'WMatrixYZX', 'WMatrixYXZ', 'WMatrixZXY', 'WMatrixZYX', 'PointAp',
       'PointRAp', 'VertexAp', 'SegmentAp', 'FaceAp', 'VertexApLc', 'VertexApAt', 'KeBornRnd', 'KeBornRnd2',
       'KeBornRnd3', 'KeBornRnd4', 'KeBornRnd5', 'KeBornRnd6', 'KeBornPtCmpl', 'KeHitBorn', 'KeThHitBorn',
       'KeLnsLpSft', 'KeLnsLp', 'KeLnsArnd', 'KeLnsClm', 'KeLnsCrn', 'KeLnsFls', 'KeAcmSolid', 'KeHitChk', 'KeThLz',
       'KeThCp', 'KeThCpSft', 'KeAccSpdSv', 'RyjDrawShipolyBone', 'RyjMegaBirth', 'RyjMngFlag', 'RyjMegaBirthPrize',
       'RyjMegaPlace', 'RyjMegaPlaceShape', 'RyjMegaPlaceModel', 'RyjMegaPlaceLamp', 'RyjMegaBirthModel',
       'RyjDrawKekoto', 'MoveLoop', 'AngMoveLoop', 'SclMoveLoop', 'PointLoop', 'AngleLoop', 'ScaleLoop', 'MatrixLoop',
       'DrawMatrixLoop', 'DrawMdlLoop', 'DrawMdlLoopZ', 'RyjLight', 'KeLnsLpT', 'KeLnsArndT', 'KeLnsClmT',
       'KeLnsCrnT', 'KeLnsFlsT', 'RyjDrawMatrixWorldDtt', 'RyjDrawMatrixWorldDttFr', 'RyjMegaBirthFilter',
       'RyjMegaBirthModelFilter', 'MatrixLoopXYZ', 'MatrixLoopXZY', 'MatrixLoopYXZ', 'MatrixLoopYZX', 'MatrixLoopZXY',
       'MatrixLoopZYX', 'VertexApLcLoop', 'SnoScaleAll', 'SnoMdlDttNorm', 'RyjMegaBirthUserCtrl',
       'RyjMegaBirthUserCtrl2', 'EiDrawShipoly', 'RyjMegaBirthUserCtrl3')

def u32(d, o): return struct.unpack_from('<I', d, o)[0]
def i32(d, o): return struct.unpack_from('<i', d, o)[0]

def bar(d):
    assert d[:4] == b'BAR\x01', 'not a BAR'
    return [struct.unpack_from('<HH4sII', d, 16 + 16 * i) for i in range(u32(d, 4))]

FLAGS = ['Bind', 'BindOnlyStart', 'BindOnlyPos', 'GetColor', 'GetBrightness', 'DestroyWhenMotionChange',
         'DestroyFadeout', 'DestroyLoopend', 'BindScale', 'DestroyWhenObjectLeaves', 'DestroyWhenBindEffectOff',
         'GetObjectFade', 'BonePos', 'BindCamera']

def pax_elements(p):
    sig, nameoff, n, dpx = struct.unpack_from('<4sIII', p, 0)
    assert sig == b'PAX_'
    E = []
    for i in range(n):
        o = 16 + 80 * i
        en, eid, grp, fade, bone, cat, fl, wait, se = struct.unpack_from('<HHBBhQIfi', p, o)
        trs = struct.unpack_from('<9f', p, o + 28)
        E.append(dict(i=i, effect=en, id=eid, group=grp, fade=fade, bone=bone, cat=cat, flags=fl, wait=wait, se=se,
                      T=trs[0:3], R=trs[3:6], S=trs[6:9]))
    return E, p[nameoff:nameoff + 128].split(b'\0')[0].decode('latin1'), dpx

def dpx_parse(X):
    ver, _, _, n = struct.unpack_from('<iiii', X, 0)
    effs = [struct.unpack_from('<III', X, 16 + 32 * i) for i in range(n)]
    o = 16 + 32 * n
    nd = u32(X, o)
    offs = list(struct.unpack_from('<%dI' % nd, X, o + 4))
    dpds = [X[off:(offs[k + 1] if k + 1 < nd else len(X))] for k, off in enumerate(offs)]
    return [dict(dpd=offs.index(a), pdata=b, effect=c) for a, b, c in effs], dpds

def dpd_lists(D):
    assert u32(D, 0) == 150, 'DPD version'
    q, L = 4, []
    for _ in range(5):
        c = u32(D, q); L.append(list(struct.unpack_from('<%dI' % c, D, q + 4))); q += 4 + 4 * c
    return L  # pdata, textures, shapes, models, vsf

def pdata_header(D, off):
    h = D[off:off + 272]
    use = lambda a: [b * 8 + k for b in range(16) for k in range(8) if h[a + b] >> k & 1]  # 128-bit index sets
    se, sevol = struct.unpack_from('<HH', h, 0xF8 + 4)
    return dict(offset=struct.unpack_from('<3f', h, 128), angle=struct.unpack_from('<3i', h, 144),
                scale=struct.unpack_from('<3f', h, 160), tex=use(176), shape=use(192), model=use(208), vsf=use(224),
                work=i32(h, 240), packet=i32(h, 244), se=se, sewait=struct.unpack_from('<f', h, 0x100)[0],
                bone=i32(h, 0x104), wait=struct.unpack_from('<f', h, 0x108)[0])

def pdata_programs(D, off):
    """Entries (layers) of the particle program file that follows the 272-B header."""
    F = D[off + 272:]
    unk_at, ent_at = struct.unpack_from('<ii', F, 8)
    n = u32(F, ent_at)
    eoffs = struct.unpack_from('<%dI' % n, F, ent_at + 4)
    out = []
    for k, eo in enumerate(eoffs):
        nxt, cvoff, flag, status, start, total, loop0, loop1, valbytes, prio, npr = struct.unpack_from('<9ihh', F, eo)
        progs = []
        for j in range(npr):
            typ, psize, cnt, pp, uv = struct.unpack_from('<iHHii', F, eo + 40 + 16 * j)
            ents = [F[pp + e * psize: pp + (e + 1) * psize] for e in range(cnt)]
            progs.append(dict(type=typ, name=PPP[typ - 1] if 0 < typ <= len(PPP) else '?%d' % typ,
                              psize=psize, entries=ents, useval_at=uv))
        out.append(dict(flag=flag, start=start, total=total, loop=(loop0, loop1), valbytes=valbytes, prio=prio,
                        programs=progs))
    return out

def fmt_words(b, name=''):
    if name.startswith('Col') and len(b) == 12:   # time, then RGBA as s16 (0x4000 = 128 = PS2 full intensity)
        return '%gf rgba(%s)' % (i32(b, 0) / 4096, ','.join('%g' % (v / 128) for v in struct.unpack_from('<4h', b, 4)))
    s = []
    for o in range(0, len(b), 4):
        v = struct.unpack_from('<i', b, o)[0]
        if o == 0 and v % 4096 == 0 and 0 <= v < 0x7000000: s.append('%gf' % (v / 4096)); continue
        f = struct.unpack_from('<f', b, o)[0]
        s.append('%g' % f if (0.0005 < abs(f) < 1e5 and v not in (-1,)) else str(v))
    return ' '.join(s)

def texture(D, off):
    dbp, cbp, dbw, fmt, x, y, w, h, t0l, t0h, cst, tvs, cvs = struct.unpack_from('<hhhhhhhhIIihh', D, off)
    o = off + 32
    if fmt == 0x14:
        idx = D[o:o + w * h // 2]; pal = D[o + w * h // 2: o + w * h // 2 + 64]
        pix = []
        for b in idx: pix += [b & 15, b >> 4]
    else:
        pix = list(D[o:o + w * h]); pal = D[o + w * h: o + w * h + 1024]
        rep = lambda i: (i & 0xE7) | (8 if i & 0x10 else 0) | (16 if i & 8 else 0)
        pix = [rep(i) for i in pix]
    return dict(fmt=fmt, w=w, h=h, dbp=dbp, cbp=cbp, tex0=(t0h << 32) | t0l), pix, pal

def save_png(path, w, h, pix, pal):
    from PIL import Image
    a = lambda v: min(255, v * 2)
    rgba = bytearray()
    for i in pix:
        r, g, b, al = pal[4 * i:4 * i + 4]; rgba += bytes((r, g, b, a(al)))
    Image.frombytes('RGBA', (w, h), bytes(rgba)).save(path)

def shapes(D, off):
    """Sprite animation: frames, each = wait + quads (x0,y0,x3,y3 screen rect; s,t,w,h texel rect) + RGBA."""
    shp, texb, clb, _, _, psize = struct.unpack_from('<hhhBBi', D, off)
    aid, ver, flag, cnt, seqc, x, y = struct.unpack_from('<BBhhhhh', D, off + 16)
    q = off + 32
    seqs = [struct.unpack_from('<hhB', D, q + 8 * i) for i in range(cnt)]
    q += 8 * cnt
    if (q - off) % 16: q += 8
    frames = []
    for addr, wait, fl in seqs:
        vfl, n, _ = struct.unpack_from('<hhi', D, q)
        t0 = struct.unpack_from('<Q', D, q + 16)[0]
        q += 32
        big = vfl & 8
        quads = []
        for _ in range(n):
            if big: v = struct.unpack_from('<12h', D, q); q += 24; quads.append(dict(xy=v[:8], st=v[8:12]))
            else: v = struct.unpack_from('<8h', D, q); q += 16; quads.append(dict(xy=v[:4], st=v[4:8]))
        for k in range(n):
            quads[k]['rgba'] = tuple(D[q:q + 4]); quads[k]['alpha'] = tuple(D[q + 4:q + 8]); q += 8  # 128 = 1.0
        if (q - off) % 16: q += 8
        frames.append(dict(wait=wait, tbp=t0 & 0x3FFF, quads=quads))
    return dict(texbase=texb, clutbase=clb, frames=frames)

def main(a):
    path = a[0]
    d = open(path, 'rb').read()
    pax = None
    for t, dup, name, off, size in bar(d):
        if t == 18: pax = d[off:off + size]; break
    E, name, dpxoff = pax_elements(pax)
    effs, dpds = dpx_parse(pax[dpxoff:])
    print('PAX %s: %d elements, %d DPX effects, %d DPDs' % (name, len(E), len(effs), len(dpds)))
    for e in E:
        f = '|'.join(n for b, n in enumerate(FLAGS) if e['flags'] >> b & 1)
        bone = 'sp%d' % (e['bone'] & 0xFFF) if e['bone'] >= 0x4000 else str(e['bone'])
        ef = effs[e['effect']]
        print(' elem %2d id %3d -> effect %2d (dpd %d pdata %2d) bone %-5s fade %2d se %7d T %s S %.2f %s' % (
            e['i'], e['id'], e['effect'], ef['dpd'], ef['pdata'], bone, e['fade'], e['se'],
            ' '.join('%.1f' % v for v in e['T']), e['S'][0], f))
    for k, D in enumerate(dpds):
        L = dpd_lists(D)
        print('DPD %d: %d pdata, %d textures, %d shapes, %d models, %d vsf, %d bytes' % (k, *map(len, L), len(D)))
        for j, t in enumerate(L[1]):
            info, _, _ = texture(D, t)
            print('   tex %d: %dx%d fmt %#x dbp %d cbp %d' % (j, info['w'], info['h'], info['fmt'], info['dbp'], info['cbp']))
    if '--shapes' in a:
        for k, D in enumerate(dpds):
            L = dpd_lists(D)
            tb = {texture(D, o)[0]['dbp']: j for j, o in enumerate(L[1])}
            for j, o in enumerate(L[2]):
                try: s = shapes(D, o)
                except struct.error: print('  dpd %d shape %d: parse error' % (k, j)); continue
                f0 = s['frames'][0] if s['frames'] else None
                print('  dpd %d shape %2d: %2d frames, texbase %d (tex %s) first: %s' % (k, j, len(s['frames']), s['texbase'],
                      tb.get(f0['tbp'] if f0 else -1, '?'), f0 and [(q['st'], q['rgba']) for q in f0['quads']]))
    want = [int(x) for x in a[a.index('--elem') + 1:] if x.isdigit()] if '--elem' in a else []
    for wi in want:
        e = next(x for x in E if x['id'] == wi)
        ef = effs[e['effect']]; D = dpds[ef['dpd']]; L = dpd_lists(D)
        h = pdata_header(D, L[0][ef['pdata']])
        print('\n=== element id %d: effect %d = DPD %d pdata %d' % (wi, e['effect'], ef['dpd'], ef['pdata']))
        print('  header: tex %s shapes %s models %s vsf %s se %d bone %d offset %s scale %s' % (
            h['tex'], h['shape'], h['model'], h['vsf'], h['se'], h['bone'], h['offset'], h['scale']))
        for li, ent in enumerate(pdata_programs(D, L[0][ef['pdata']])):
            print('  layer %d: start %d total %d loop %s prio %d flag %#x' % (li, ent['start'], ent['total'],
                  ent['loop'], ent['prio'], ent['flag']))
            for pr in ent['programs']:
                print('    %-24s x%d: %s' % (pr['name'], len(pr['entries']),
                      ' / '.join(fmt_words(b, pr['name']) for b in pr['entries'][:6]) + (' ...' if len(pr['entries']) > 6 else '')))
    if '--png' in a:
        out = a[a.index('--png') + 1]; os.makedirs(out, exist_ok=True)
        for k, D in enumerate(dpds):
            for j, t in enumerate(dpd_lists(D)[1]):
                info, pix, pal = texture(D, t)
                save_png(os.path.join(out, 'dpd%d_tex%d_%dx%d.png' % (k, j, info['w'], info['h'])), info['w'], info['h'], pix, pal)
        print('PNGs ->', out)

if __name__ == '__main__':
    main(sys.argv[1:])
