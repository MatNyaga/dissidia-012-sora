"""Dissidia 012 "SSCF" sound banks (fighter file chunk 'snd_', voice/EN/battle/voice_*_00.scd).

Layout (worked out 2026-10-12):
  0x00 "SSCF"  0x04 u16 0x0210, u16 0x0207   0x08 u32 bank size   0x0C u32 sound count   0x10 u16 1, u16 ?
  0x20 count x 32-byte entries: +0 u32 0, +4 u32 data offset (from bank start), +8 u32 data size,
       +0x0C u16 sample rate (Hz), +0x0E u16 ?, +0x10.. playback params (volume 100, ...).
  Data = PSP/PS1 ADPCM ("VAG"): 16-byte blocks of 28 samples (byte 0 = filter<<4 | shift, byte 1 = flags).

Usage:
  python3 -I sscf.py list BANK
  python3 -I sscf.py wav BANK OUT_DIR                 every sound -> OUT_DIR/NN.wav (16-bit mono)
  python3 -I sscf.py replace BANK N IN.wav OUT_BANK   sound N <- IN.wav (mono 16-bit; resampled to the entry's
                                                      rate), fitted to the old size (cut or padded with silence)
  python3 -I sscf.py rebuild BANK MAP.txt OUT_BANK    MAP lines "N path.wav": those sounds get the WAV at its own
                                                      length (rate = WAV rate, 16-bit mono); data re-laid out,
                                                      bank size updated (the bank may grow — pkg_put.py handles it)
"""
import struct
import sys
import wave

FILTERS = [(0, 0), (60, 0), (115, -52), (98, -55), (122, -60)]


def entries(bank):
    assert bank[:4] == b'SSCF', 'not an SSCF bank'
    count, = struct.unpack_from('<I', bank, 12)
    for i in range(count):
        _, off, size, rate = struct.unpack_from('<IIIH', bank, 0x20 + i * 32)
        yield i, off, size, rate


def decode(data):
    out, h1, h2 = [], 0, 0
    for b in range(len(data) // 16):
        blk = data[b * 16:b * 16 + 16]
        shift, filt = blk[0] & 0x0F, min(blk[0] >> 4, 4)
        f0, f1 = FILTERS[filt]
        if blk[1] == 7:                         # end marker block
            break
        for byte in blk[2:]:
            for nib in (byte & 0x0F, byte >> 4):
                s = (nib - 16 if nib > 7 else nib) << 12 >> shift
                s += (h1 * f0 + h2 * f1 + 32) >> 6
                s = max(-32768, min(32767, s))
                out.append(s)
                h2, h1 = h1, s
    return out


def encode(samples, nblocks):
    """Simple ADPCM encoder (filter 0/1 search, best shift). Fills exactly nblocks blocks."""
    out, h1, h2 = bytearray(), 0, 0
    samples = list(samples) + [0] * max(0, nblocks * 28 - len(samples))
    for b in range(nblocks):
        chunk = samples[b * 28:b * 28 + 28]
        best = None
        for filt in range(2):
            f0, f1 = FILTERS[filt]
            for shift in range(13):
                a, c, err, nibs = h1, h2, 0, []
                for x in chunk:
                    pred = (a * f0 + c * f1 + 32) >> 6
                    n = round((x - pred) * (1 << shift) / 4096)
                    n = max(-8, min(7, n))
                    s = max(-32768, min(32767, (n << 12 >> shift) + pred))
                    err += (x - s) ** 2
                    nibs.append(n & 0x0F)
                    c, a = a, s
                if best is None or err < best[0]:
                    best = (err, filt, shift, nibs, a, c)
        _, filt, shift, nibs, h1, h2 = best
        flags = 1 if b == nblocks - 1 else 0
        out += bytes([filt << 4 | shift, flags]) + bytes(nibs[i] | nibs[i + 1] << 4 for i in range(0, 28, 2))
    return bytes(out)


def read_wav(path, rate):
    w = wave.open(path)
    assert w.getsampwidth() == 2, '16-bit WAV please'
    raw = w.readframes(w.getnframes())
    ch = w.getnchannels()
    s = struct.unpack('<%dh' % (len(raw) // 2), raw)[::ch]
    src = w.getframerate()
    if src != rate:                             # linear resample
        n = int(len(s) * rate / src)
        s = [s[min(len(s) - 1, int(i * src / rate))] for i in range(n)]
    return s


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    bank = bytearray(open(path, 'rb').read())
    if cmd == 'list':
        for i, off, size, rate in entries(bank):
            print('%3d  off %7x  size %6d  rate %5d  %.2fs' % (i, off, size, rate, size / 16 * 28 / max(rate, 1)))
    elif cmd == 'wav':
        import os
        os.makedirs(sys.argv[3], exist_ok=True)
        for i, off, size, rate in entries(bank):
            if size < 16 or not rate:           # empty or placeholder slot
                continue
            s = decode(bank[off:off + size])
            w = wave.open(os.path.join(sys.argv[3], '%02d.wav' % i), 'wb')
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
            w.writeframes(struct.pack('<%dh' % len(s), *s))
            w.close()
    elif cmd == 'replace':
        n, wav_in, out = int(sys.argv[3]), sys.argv[4], sys.argv[5]
        i, off, size, rate = list(entries(bank))[n]
        bank[off:off + size] = encode(read_wav(wav_in, rate), size // 16)
        open(out, 'wb').write(bank)
        print('sound %d replaced (%d bytes, %d Hz)' % (n, size, rate))
    elif cmd == 'rebuild':
        new = {}
        for line in open(sys.argv[3]):
            if line.strip() and not line.startswith('#'):
                n, p = line.split(None, 1)
                w = wave.open(p.strip())
                assert w.getsampwidth() == 2 and w.getnchannels() == 1, p + ': 16-bit mono WAV please'
                raw = w.readframes(w.getnframes())
                smp = struct.unpack('<%dh' % (len(raw) // 2), raw)
                new[int(n)] = (encode(smp, (len(smp) + 27) // 28 + 1), w.getframerate())
        ents = list(entries(bank))
        first = min(off for i, off, size, rate in ents if size >= 16)
        data = bytearray()
        layout = []
        for i, off, size, rate in ents:
            if i in new:
                blob, rate = new[i]
            elif size >= 16:
                blob = bytes(bank[off:off + size])
            else:
                layout.append((i, None, None, None))
                continue
            layout.append((i, first + len(data), len(blob), rate))
            data += blob
        out = bytearray(bank[:first]) + data
        for i, off, size, rate in layout:
            if off is not None:
                struct.pack_into('<IIH', out, 0x20 + i * 32 + 4, off, size, rate)
        struct.pack_into('<I', out, 8, len(out))
        open(sys.argv[4], 'wb').write(out)
        print('rebuilt: %d sounds replaced, bank %d -> %d bytes' % (len(new), len(bank), len(out)))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
