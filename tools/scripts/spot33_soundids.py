"""Give #33 its own sound-bank ids, so Cloud and #33 can be in the same fight (see notes/sound-bank-ids.md).

#33's banks and scripts are copies of Cloud's. A sound is requested by an ABSOLUTE id = bank base + slot, and the
base is written into the fighter's own DATA (not computed from the owner):
  - SSCF header (bank -> base): base = h10*10000 + h12*100 - 10000 (h10 = u16 +0x10 = 1, h12 = u16 +0x12), or
    if h12 == 0 and u32 +0x14 > 599: base = (u32 +0x14) * 100           (FUN_0899075c; the 012 newcomers use this)
  - p_se type-8 script events: op 0x03 p0 / op 0x11 p1 = snd_ id, op 0x15 p0 = voice id (Cloud 2200000+slot,
    2210000+slot); the game adds 0 / +10000 manikin voice / +50000 assist (FUN_08842828)
  - effe chunk member p_sev100.fxseb (FXSE effect sounds): records u32 base 2200000, u32 slot (FUN_088a6aa4)
  - system.bin/chrp row +0x7c/+0x80/+0x84/+0x88: 4 voice ids (KO 2210004, EX Mode 2210030, 2210042, 2210041)
Changing only the headers (old version of this script, test 82) made every request miss -> #33 silent.

This version moves ALL of them, in place (same sizes):
  snd_ 22000 -> 219000 (base 2,200,000 -> 21,900,000), voice 22100 -> 219100 (2,210,000 -> 21,910,000).
219xxx = owner 33's own range (Aerith's assist banks are 219500/219600, her old chrp voice id 21910005).
Not changed: Cloud's EX Burst code (battle overlay FUN_08a3a0b8) plays 2200053 / 2200054 directly -> #33 (who runs
Cloud's EX Burst code) gets those two sounds only when Cloud's bank is loaded.

  python3 -I spot33_soundids.py ISO [--dry-run]      run LAST (after every step that writes p_sev120.objx / voice)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from ablt_patch import arc_chunk, mpk_member  # noqa: E402

OLD_SND, OLD_VOICE = 22000, 22100
NEW_SND, NEW_VOICE = int(os.environ.get('SND_ID', 219000)), int(os.environ.get('VOICE_ID', 219100))


def bank_base(h):
    h10, h12, h14 = struct.unpack_from('<HHI', h, 0x10)
    if h12 == 0 and h14 > 599:
        return h14 * 100
    return h10 * 10000 + h12 * 100 - 10000


def new_header(new_id):
    """bytes for SSCF +0x10..+0x18 (h10, h12, h14)."""
    if new_id <= 0xFFFF:
        return struct.pack('<HHI', 1, new_id, 0)
    return struct.pack('<HHI', 1, 0, new_id)


class Patch:
    def __init__(self, f, dry):
        self.f, self.dry, self.n = f, dry, 0

    def put(self, at, data):
        self.n += 1
        if not self.dry:
            self.f.seek(at)
            self.f.write(data)


def main():
    iso, dry = sys.argv[1], '--dry-run' in sys.argv
    use_iso(iso)
    with open(iso, 'rb' if dry else 'r+b') as f:
        p = Patch(f, dry)
        st, sz = pkg_offset('obj/p_sev120.objx')
        d = read_at(f, st, sz)
        chunks = {}
        n, = struct.unpack_from('<I', d, 4)
        for k in range(n):
            t, tag, off, size = struct.unpack_from('<I4sII', d, 16 + k * 16)
            chunks[(tag, t)] = (off, size)
        vst, _ = pkg_offset('voice/EN/battle/voice_P_SEV120_00.scd')
        heads = [('snd_', st + chunks[(b'snd_', 14)][0], OLD_SND, NEW_SND),
                 ('voice', vst, OLD_VOICE, NEW_VOICE)]
        remap = []                                  # (old base, count, new base)
        for what, at, old, new in heads:
            h = read_at(f, at, 0x20)
            assert h[:4] == b'SSCF', what
            count, = struct.unpack_from('<I', h, 0xC)
            cur = bank_base(h)
            if cur == new * 100:
                print('%s bank: already %d (base %d)' % (what, new, cur))
            else:
                assert cur == old * 100, '%s bank base %d, expected %d' % (what, cur, old * 100)
                p.put(at + 0x10, new_header(new))
                print('%s bank: %d -> %d (base %d -> %d, %d slots)' % (what, old, new, cur, new * 100, count))
            remap.append((old * 100, count, new * 100))

        def mapped(v):
            for ob, cnt, nb in remap:
                if ob <= v < ob + cnt:
                    return nb + v - ob
            return None

        # p_se type 8 scripts: every event parameter that is a #33 sound id
        off8, _ = chunks[(b'p_se', 8)]
        c8 = d[off8:]
        cnt, = struct.unpack_from('<I', c8, 4)
        ops = {}
        for bo in struct.unpack_from('<%dI' % cnt, c8, 8):
            nm, no = c8[bo + 2], c8[bo + 3]
            q = bo + 8
            evs = []
            for _ in range(nm):                                     # u16 from, u16 to, u8 op, u8 n, 6 B cond
                evs.append((c8[q + 4], c8[q + 5], q + 12))
                q += 12 + 4 * c8[q + 5]
            for _ in range(no):                                     # u16 frame, u8 op, u8 n, 4 B cond
                evs.append((c8[q + 2], c8[q + 3], q + 8))
                q += 8 + 4 * c8[q + 3]
            for op, npar, pq in evs:
                for i in range(npar):
                    v, = struct.unpack_from('<I', c8, pq + 4 * i)
                    m = mapped(v)
                    if m is not None:
                        p.put(st + off8 + pq + 4 * i, struct.pack('<I', m))
                        ops['op 0x%02x p%d' % (op, i)] = ops.get('op 0x%02x p%d' % (op, i), 0) + 1
        print('p_se 8 script ids:', ops or 'none left')

        # effe -> member *.fxseb: FXSE records (u32 base, u32 slot) -> played as base + slot
        effe, _ = chunks[(b'effe', 4)]
        e = d[effe:]
        fx = 0
        for i in range(struct.unpack_from('<I', e, 8)[0]):
            noff, doff, size, _ = struct.unpack_from('<IIII', e, 16 + i * 16)
            if not e[noff:noff + 32].split(b'\0')[0].endswith(b'.fxseb'):
                continue
            for o in range(doff, doff + size - 7, 4):
                base, slot = struct.unpack_from('<II', e, o)
                for ob, cnt_, nb in remap:
                    if base == ob and slot < cnt_:
                        p.put(st + effe + o, struct.pack('<I', nb))
                        fx += 1
        print('effe fxseb sound records:', fx)

        # chrp row 33: +0x7c..+0x88 voice ids
        mst, _ = pkg_offset('general_archive/main/main.bin')
        sysbin, _ = mpk_member(f, mst, 'system.bin')
        chrp, _ = arc_chunk(f, sysbin, 'chrp')
        _, rows = struct.unpack('<II', read_at(f, chrp, 8))
        for r in range(rows):
            at = chrp + 8 + r * 144
            row = read_at(f, at, 144)
            if row[0] != 33:
                continue
            for fo in (0x7c, 0x80, 0x84, 0x88):
                v, = struct.unpack_from('<I', row, fo)
                m = mapped(v)
                if m is not None:
                    p.put(at + fo, struct.pack('<I', m))
                    print('chrp 33 +0x%x: %d -> %d' % (fo, v, m))
        print('%s %d writes' % ('would make' if dry else 'made', p.n))


if __name__ == '__main__':
    main()
