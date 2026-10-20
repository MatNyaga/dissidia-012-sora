"""P2.6 (Phase 2): id spaces a package installer must allocate, measured on a disc (default: the clean dump).

  python3 -I tools/dlc/id_spaces.py [ISO] [--json OUT]        read-only; writes only the JSON (tools/dlc/id_spaces.json)

- FEP effect-package ids: every "FEP\\xCD" header in every PACKAGE_INFO file, u32 +0x10, the game compares the top 14
  bits (id >> 18) and refuses a second FEP with a loaded id (notes/effects-clash.md).
- Sound banks: every "SSCF" header, base = h14*100 if h12 == 0 and h14 > 599 else h10*10000 + h12*100 - 10000
  (FUN_0899075c, notes/sound-bank-ids.md); reported as bank ids (base / 100).
- objentry ids (main.bin objentry.bin, 68-B rows, u16 id +0): used ids, free ids below 1338 (owner-34 rule:
  FUN_08846ccc returns the first id-ordered row for owner+costume, Cosmos P_ORG800_1P = 1338), RAM room 1194 rows.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools/scripts'))
sys.dont_write_bytecode = True
from comb_patch import PACKAGE_ISO_SECTOR, pkg_offset, read_at, use_iso  # noqa: E402
from ablt_patch import mpk_member  # noqa: E402

SECTOR = 0x800
PKG_INFO_SECTOR = 26000                                # PACKAGE_INFO.BIN (comb_patch.pkg_offset_by_path)


def ranges(nums):
    out, s, p = [], None, None
    for n in sorted(nums):
        if s is None:
            s = p = n
        elif n == p + 1:
            p = n
        else:
            out.append([s, p])
            s = p = n
    if s is not None:
        out.append([s, p])
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    iso = args[0] if args else os.path.join(ROOT, 'dumps/ULUS10566.iso')
    out = os.path.join(HERE, 'id_spaces.json')
    if '--json' in sys.argv:
        out = sys.argv[sys.argv.index('--json') + 1]
    use_iso(iso)
    st, _ = pkg_offset('general_archive/main/main.bin')
    feps, banks = {}, {}
    with open(iso, 'rb') as f:
        info_at = PKG_INFO_SECTOR * SECTOR
        count, = struct.unpack('<I', read_at(f, info_at + 8, 4))
        rows = read_at(f, info_at + 16, count * 12)
        for i in range(count):
            h, sec, sf = struct.unpack_from('<III', rows, 12 * i)
            size = sf & 0x0FFFFFFF
            if not size:
                continue
            d = read_at(f, PACKAGE_ISO_SECTOR * SECTOR + (sec & 0xFFFFF) * SECTOR, size)
            k = d.find(b'FEP\xcd')
            while k >= 0:
                if k + 0x14 <= len(d):
                    v, = struct.unpack_from('<I', d, k + 0x10)
                    feps.setdefault(v >> 18, set()).add('%08x' % h)
                k = d.find(b'FEP\xcd', k + 4)
            k = d.find(b'SSCF')
            while k >= 0:
                if k + 0x18 <= len(d):
                    h10, h12, h14 = struct.unpack_from('<HHI', d, k + 0x10)
                    base = h14 * 100 if (h12 == 0 and h14 > 599) else h10 * 10000 + h12 * 100 - 10000
                    banks.setdefault(base // 100, set()).add('%08x' % h)
                k = d.find(b'SSCF', k + 4)
        o, n = mpk_member(f, st, 'objentry.bin')
        ob = read_at(f, o, n)
    _, no = struct.unpack_from('<II', ob, 0)
    ids = sorted(struct.unpack_from('<H', ob, 8 + 68 * i)[0] for i in range(no))
    free_lt_1338 = [i for i in range(1, 1338) if i not in set(ids)]
    fep_ids = sorted(feps)
    fighter_feps = [i for i in fep_ids if 3100 <= i < 3200]
    bank_ids = sorted(banks)
    newcomer = [b for b in bank_ids if 210000 <= b < 230000]
    doc = {
        'format': 'id_spaces v1 (P2.6)', 'iso': os.path.basename(iso),
        'fep': {'distinct_ids': len(fep_ids), 'min': fep_ids[0], 'max': fep_ids[-1],
                'fighter_series_3100_3199': fighter_feps,
                'free_in_3100_3199': [i for i in range(3100, 3200) if i not in feps],
                'dupes': {str(i): sorted(v) for i, v in feps.items() if len(v) > 1}},
        'sound_banks': {'distinct': len(bank_ids), 'newcomer_h14_form_210000_229999': newcomer,
                        'free_owner_slots_from_owner34': [
                            {'owner': o_, 'base': 210000 + 1000 * (o_ - 24),
                             'free': all(210000 + 1000 * (o_ - 24) + d not in banks for d in (0, 100, 500, 600))}
                            for o_ in range(33, 41)],
                        'h12_form_free_36000_39900': [b for b in range(36000, 40000, 100) if b not in banks][:40]},
        'objentry': {'rows': no, 'ram_room_rows': 1194, 'free_rows': 1194 - no, 'max_id': ids[-1],
                     'free_ids_below_1338': len(free_lt_1338), 'free_id_ranges_below_1338': ranges(free_lt_1338)},
    }
    with open(out, 'w') as fo:
        json.dump(doc, fo, indent=1)
    print(json.dumps({k: (v if k != 'objentry' else {kk: vv for kk, vv in v.items() if kk != 'free_id_ranges_below_1338'})
                      for k, v in doc.items()}, indent=1)[:3000])


if __name__ == '__main__':
    main()
