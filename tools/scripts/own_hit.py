"""Give one step of a comb action its OWN hit: a new plya piece + a new atkp hit entry, sharing the old animation.

How the chain works (notes/character-file.md):
  comb step -> plya piece -> +0x1c motion id -> p_se type 7 table (motion id -> script block, variant)
  -> script block (p_se type 8) event op 0x00 "hitbox" -> param0 = atkp hit id -> atkp entry (damage, knockback)
Events have a variant condition byte (+6, 0 = any). So we:
  1. atkp: append a copy of the old hit with NEW_ATK id (ids are binary-searched, so NEW_ATK must be the biggest).
  2. plya: append a copy of the old piece with NEW_PIECE id and NEW_MOTION motion id.
  3. type 7: old motion id -> variant 1, insert NEW_MOTION -> same block, variant 2 (table is sorted).
  4. type 8: in that block, the op 0x00 event for the old hit gets variant 1; a copy with variant 2 hits NEW_ATK.
  5. comb: ACTION's steps using OLD_PIECE now use NEW_PIECE.
Steps 3-4 only in files that have the script block (3394); 1, 2, 5 in every file given.

Usage: python3 -I own_hit.py ISO OLD_PIECE NEW_PIECE NEW_MOTION NEW_ATK NAME ACTION PKG [PKG ...]
   e.g. python3 -I own_hit.py X.iso 0x5c3 0xff0 0x27f0 0xff0 NEW_MIDDLE3 1020 3394 5973
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcfile import ArcFile  # noqa: E402

PLYA, ATKP = 116, 68


def add_atkp(arc, old_hit, new_atk, name):
    i = arc.find('atkp')
    c = arc.get(i)
    n, = struct.unpack_from('<I', c, 4)
    rows = [c[8 + k * ATKP:8 + (k + 1) * ATKP] for k in range(n)]
    ids = [struct.unpack_from('<I', r, 0)[0] for r in rows]
    if new_atk <= max(ids):
        sys.exit('NEW_ATK must be bigger than every hit id (max 0x%x)' % max(ids))
    row = bytearray(rows[ids.index(old_hit)])
    struct.pack_into('<I', row, 0, new_atk)
    row[0x34:0x44] = name.encode().ljust(16, b'\0')[:16]
    c = c[:8 + n * ATKP] + row + c[8 + n * ATKP:]
    struct.pack_into('<I', c, 4, n + 1)
    arc.put(i, c)


def add_piece(arc, old_piece, new_piece, new_motion, name):
    i = arc.find('plya')
    c = arc.get(i)
    n, = struct.unpack_from('<I', c, 4)
    rows = [c[8 + k * PLYA:8 + (k + 1) * PLYA] for k in range(n)]
    ids = [struct.unpack_from('<H', r, 0)[0] for r in rows]
    if new_piece in ids:
        sys.exit('piece 0x%x already exists' % new_piece)
    row = bytearray(rows[ids.index(old_piece)])
    old_motion, = struct.unpack_from('<H', row, 0x1c)
    struct.pack_into('<H', row, 0, new_piece)
    struct.pack_into('<H', row, 0x1c, new_motion)
    row[0x64:0x74] = name.encode().ljust(16, b'\0')[:16]
    c = c[:8 + n * PLYA] + row + c[8 + n * PLYA:]
    struct.pack_into('<I', c, 4, n + 1)
    arc.put(i, c)
    return old_motion


def set_comb(arc, action, old_piece, new_piece):
    i = arc.find('comb')
    c = arc.get(i)
    n, = struct.unpack_from('<H', c, 2)
    for o in struct.unpack_from('<%dI' % n, c, 4):
        aid, steps = struct.unpack_from('<HH', c, o)
        if aid == action:
            for k in range(steps):
                if struct.unpack_from('<H', c, o + 8 + k * 8)[0] == old_piece:
                    struct.pack_into('<H', c, o + 8 + k * 8, new_piece)
            arc.put(i, c)
            return
    sys.exit('no action %d' % action)


def add_variant(arc, old_motion, new_motion, old_hit, new_atk):
    """Returns False if this file has no script for old_motion (e.g. pkg 5973)."""
    t7 = arc.find('p_se', 7)
    c = arc.get(t7)
    n, = struct.unpack_from('<I', c, 4)
    rows = [list(struct.unpack_from('<HHHH', c, 8 + k * 8)) for k in range(n)]
    hit = [r for r in rows if r[0] == old_motion]
    if not hit:
        return False
    block = hit[0][1]
    if hit[0][2] != 0:
        sys.exit('motion 0x%x already uses variant %d' % (old_motion, hit[0][2]))
    hit[0][2] = 1
    rows.append([new_motion, block, 2, 0])
    rows.sort()
    c = bytearray(c[:8]) + b''.join(struct.pack('<HHHH', *r) for r in rows) + c[8 + n * 8:]
    struct.pack_into('<I', c, 4, n + 1)
    arc.put(t7, c)

    t8 = arc.find('p_se', 8)
    c = arc.get(t8)
    m, = struct.unpack_from('<I', c, 4)
    offs = list(struct.unpack_from('<%dI' % m, c, 8))
    o = offs[block]
    events, = struct.unpack_from('<B', c, o + 2)
    k = o + 8
    for _ in range(events):
        op, np = c[k + 4], c[k + 5]
        size = 12 + 4 * np
        if op == 0x00 and struct.unpack_from('<I', c, k + 12)[0] == old_hit and c[k + 6] == 0:
            ev = bytearray(c[k:k + size])
            c[k + 6] = 1                      # old hit: variant 1 only
            ev[6] = 2                         # new hit: variant 2 only
            struct.pack_into('<I', ev, 12, new_atk)
            c = c[:k + size] + ev + c[k + size:]
            c[o + 2] = events + 1
            s1, s2 = struct.unpack_from('<HH', c, o + 4)
            struct.pack_into('<HH', c, o + 4, s1 + size, s2 + size)
            offs = [x + size if x > o else x for x in offs]
            struct.pack_into('<%dI' % m, c, 8, *offs)
            arc.put(t8, c)
            return True
        k += size
    sys.exit('no op 0x00 event for hit 0x%x in block %d' % (old_hit, block))


def main():
    iso = sys.argv[1]
    old_piece, new_piece, new_motion, new_atk = (int(x, 0) for x in sys.argv[2:6])
    name, action, pkgs = sys.argv[6], int(sys.argv[7]), [int(x) for x in sys.argv[8:]]
    with open(iso, 'r+b') as f:
        for p in pkgs:
            arc = ArcFile(f, p)
            # the old piece's hit id comes from its script; find it from the atkp name = plya name
            pl = arc.get(arc.find('plya'))
            n, = struct.unpack_from('<I', pl, 4)
            piece_name = next(pl[8 + k * PLYA + 0x64:8 + k * PLYA + 0x74].split(b'\0')[0]
                              for k in range(n) if struct.unpack_from('<H', pl, 8 + k * PLYA)[0] == old_piece)
            at = arc.get(arc.find('atkp'))
            na, = struct.unpack_from('<I', at, 4)
            old_hit = next(struct.unpack_from('<I', at, 8 + k * ATKP)[0] for k in range(na)
                           if at[8 + k * ATKP + 0x34:8 + k * ATKP + 0x44].split(b'\0')[0] == piece_name)
            add_atkp(arc, old_hit, new_atk, name)
            old_motion = add_piece(arc, old_piece, new_piece, new_motion, name)
            set_comb(arc, action, old_piece, new_piece)
            scripts = add_variant(arc, old_motion, new_motion, old_hit, new_atk)
            print('pkg %d: hit 0x%x -> new hit 0x%x, piece 0x%x -> 0x%x, motion 0x%x -> 0x%x, scripts %s' % (
                p, old_hit, new_atk, old_piece, new_piece, old_motion, new_motion, 'changed' if scripts else 'none here'))
            arc.save()


if __name__ == '__main__':
    main()
