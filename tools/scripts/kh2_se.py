"""KH2 (PC) sound-effect ids -> SCD bank / subsong / WAV, and which Sora motion plays which SE (notes/kh2-sounds.md).

KH2 SE id = bank * 1000 + sound index (e.g. 999042 = se999 sound 42; 102 = se000 sound 102).
Bank file: kh2_export/raw/*/original/se/seNNN.win32.scd (se999 = Sora's own bank, se000 = common/system,
se500 = Kingdom Key, also in remastered/obj/W_EX010.a.us/se/obj/se500).
SCD (SEDB/SSCF) tables at 0x30: u16 nSound, nTrack, nAudio, bankId; u32 trackOff, audioOff, layoutOff, ?, attrOff;
sound offsets start at 0x50. Sound entry: u8 nTrack, bus, prio, type, u16 attr, u16 ?, f32 volume, u16 localNo, u16 ?,
[optional blocks], then u16 trackIdx, u16 audioIdx per track at the END of the entry. vgmstream subsong = rank of audioIdx among non-empty audio entries (se999: audioIdx + 1). Track = command list;
cmd 0x07 [u16 3, u32 ms] = play length.

  python3 -I kh2_se.py bank SCD                 # sound -> audio/subsong table
  python3 -I kh2_se.py id 999042 [--wav OUT]    # resolve (and decode) one SE id
  python3 -I kh2_se.py refs [IDX ...]           # SE played by P_EX100 motions (PAX effect se + t8 triggers)
"""
import glob
import os
import struct
import subprocess
import sys

ROOT = '.'
RAW = ROOT + '/kh2_export/raw'
VGM = ROOT + '/tools/vgmstream/vgmstream-cli'
MSET = RAW + '/kh2_sixth/original/obj/P_EX100.mset'
AUS = RAW + '/kh2_sixth/original/obj/P_EX100.a.us'


def bank_file(bank):
    for f in sorted(glob.glob(RAW + '/*/original/se/se%03d.win32.scd' % bank)) + \
            sorted(glob.glob(RAW + '/*/remastered/obj/*/se/obj/se%03d' % bank)):
        return f
    return None


def scd_sounds(path):
    d = open(path, 'rb').read()
    ns, nt, na, bank, to, ao, lo, ro, at = struct.unpack_from('<4H5I', d, 0x30)
    S = struct.unpack_from('<%dI' % ns, d, 0x50)
    T = struct.unpack_from('<%dI' % nt, d, to)
    A = struct.unpack_from('<%dI' % na, d, ao)
    sub, k = {}, 0
    for j, a in enumerate(A):  # vgmstream skips dummy audio entries (size 0, codec -1)
        if struct.unpack_from('<I', d, a)[0]:
            k += 1
            sub[j] = k
    out = []
    for i, o in enumerate(S):
        ntr, bus, prio, typ, attr, _u, vol, local = struct.unpack_from('<4BHHfH', d, o)
        tracks = []
        end = S[i + 1] if i + 1 < ns else to
        if ntr and typ == 1:
            for k in range(ntr):  # track list = last 4*nTrack bytes (se000 entries carry an extra 0x30-B block)
                ti, ai = struct.unpack_from('<HH', d, end - 4 * (ntr - k))
                ms = None
                if ti < nt:
                    tb = d[T[ti]:(T[ti + 1] if ti + 1 < nt else ao)]
                    p = tb.find(b'\x07\x00\x03\x00')
                    if p >= 0:
                        ms = struct.unpack_from('<I', tb, p + 4)[0]
                tracks.append((ti, ai, ms, sub.get(ai)))
        out.append(dict(sound=i, type=typ, ntrack=ntr, vol=round(vol, 3), tracks=tracks))
    return bank, out


def resolve(seid):
    bank, idx = divmod(seid, 1000)
    f = bank_file(bank)
    if not f:
        return None
    b, snd = scd_sounds(f)
    if idx >= len(snd):
        return dict(file=f, bank=bank, sound=idx, tracks=[])
    return dict(file=f, bank=bank, **snd[idx])


def decode(path, subsong, out):
    subprocess.run([VGM, '-s', str(subsong), '-o', out, path], check=True, stdout=subprocess.DEVNULL)


def bar(d):
    n = struct.unpack_from('<I', d, 4)[0]
    return [struct.unpack_from('<HH4sII', d, 16 + 16 * i) for i in range(n)]


def pax_se(path):
    d = open(path, 'rb').read()
    for t, _dup, _name, off, size in bar(d):
        if t == 18:
            p = d[off:off + size]
            n = struct.unpack_from('<I', p, 8)[0]
            m = {}
            for i in range(n):
                o = 16 + 80 * i
                _en, eid = struct.unpack_from('<HH', p, o)
                wait, se = struct.unpack_from('<fi', p, o + 0x14)
                m.setdefault(eid, (se, wait))
            return m
    return {}


def frame_triggers():
    d = open(MSET, 'rb').read()
    out = {}
    for i, (t, _dup, name, off, size) in enumerate(bar(d)):
        if t != 17 or size == 0:
            continue
        sub = d[off:off + size]
        for s in bar(sub):
            if s[0] != 16:
                continue
            tr = sub[s[3]:s[3] + s[4]]
            nr, nf, fo = struct.unpack_from('<BBH', tr, 0)
            F, p = [], fo
            for _ in range(nf):
                f, ty, ps = struct.unpack_from('<hBB', tr, p)
                p += 4
                F.append((f, ty, list(struct.unpack_from('<%dh' % ps, tr, p))))
                p += 2 * ps
            out[i] = (name.decode(), F)
    return out


def refs(want):
    pax = pax_se(AUS)
    trig = frame_triggers()
    rows = []
    for i in sorted(trig):
        if want and i not in want:
            continue
        name, F = trig[i]
        for f, ty, p in F:
            if ty == 1 and p and pax.get(p[0], (-1,))[0] >= 0:   # effect caster -> PAX element se
                rows.append((i, name, f, 'pax elem %d' % p[0], pax[p[0]][0]))
            elif ty == 8 and len(p) >= 2:                          # play sound effect [bank, index, ...]
                rows.append((i, name, f, 't8 %s' % p, p[0] * 1000 + p[1]))
            elif ty == 14 and want:
                rows.append((i, name, f, 't14 voice type %s' % p, -1))
    return rows


def main(a):
    if a[0] == 'bank':
        bank, snd = scd_sounds(a[1])
        print('bank', bank, len(snd), 'sounds')
        for s in snd:
            print('%3d type %d vol %.2f %s' % (s['sound'], s['type'], s['vol'],
                  ' '.join('track %d audio %d (subsong %s, %s ms)' % (t, au, sb, ms) for t, au, ms, sb in s['tracks'])))
    elif a[0] == 'id':
        r = resolve(int(a[1]))
        print(r)
        if '--wav' in a and r and r['tracks']:
            out = a[a.index('--wav') + 1]
            decode(r['file'], r['tracks'][0][3], out)
            print('->', out)
    elif a[0] == 'refs':
        for i, name, f, how, se in refs({int(x) for x in a[1:]}):
            r = resolve(se) if se >= 0 else None
            sub = ('se%03d subsong %s' % (r['bank'], r['tracks'][0][3])) if r and r['tracks'] else '-'
            print('%4d %s tick %3d  %-22s se %7d  %s' % (i, name, f, how, se, sub))


if __name__ == '__main__':
    main(sys.argv[1:])
