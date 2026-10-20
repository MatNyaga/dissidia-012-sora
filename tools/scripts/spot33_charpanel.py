"""□ "Characters" panel (which characters can equip an item) crashed on owner 33 (Sora). Findings: notes/menu-art.md
"Artifacts + □ crash".

Mat, test330: Communications Mode → Artifacts, press □ → crash in FUN_088d9a94 (anim set on a NULL sprite, s4 = 33).
The same panel code serves Customization (group 5), the Shop (group 8) and Artifacts (network scene, group 9):
FUN_08aff218 (menu overlay) walks the owner list 0x08B0119C (test 14's select-swap put 33 where 32 = Feral Chaos
was) and, for each owner, animates / hides sprite array[base + owner + 1] and stores the owner for FUN_08af9880,
which positions sprite base + owner + 1. Every scene creates sprites only for owners 1..32 (one face part each:
seq + texture base + owner) -> owner 33's sprite is NULL -> crash (Customization / Shop would crash the same way).

Fix (owner 32 is no longer in that list, so its sprite is free):
1. CODE, FUN_08aff218, 5 words in place (2 nop delay slots, 1 redundant `ori a1,zero,1`, 2 rewrites):
   t9 = (owner < 33) + owner  (= sprite owner + 1; 33 for Sora), s4 = t9 - 1 after the mask bit test (so the
   equip / unlock bits still use owner 33 = bit 0), hide path indexes with t9. Owners 1..32 behave exactly as before.
2. DATA: owner 32's face part now shows Sora's 32x64 icon:
   Customization parts 0x08AEB130 (from part 6) part 57: texture 3178 -> 3179 (Sora's icon, customize pk entry 107)
   Shop parts 0x08B1B5B8 part 68: texture 7268 -> 7269 (Sora's icon, shop pk entry 101, test325)
   Artifacts parts 0x08A23538 part 53: texture 8240 -> 8321 = NEW entry 129 of menu_pk_network_gim_0 (the network
   packs have no owner-33 icon and no free id; the 32 network icons are byte-identical to the shop ones, so the new
   entry is a copy of Customization's Sora icon). Each of these parts is used only by owner 32's sprite.

Guards: every word / u16 must be the vanilla or our value; the icon source must not be the vanilla Aerith icon;
network pack must have 129 (vanilla) or 130 (ours) entries with entries 0..128 unchanged. Re-run = "already".

  python3 -I spot33_charpanel.py ISO [--dry]
"""
import hashlib
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import SECTOR, pkg_offset, read_at, use_iso  # noqa: E402
from mips_asm import asm  # noqa: E402
from roster_patch import MENU_FILEOFF, MENU_ISO_SECTOR, MENU_VADDR  # noqa: E402
from spot33_qbpics import read_pack, write_pack  # noqa: E402

# (VA, vanilla word, new instruction)
CODE = [
    (0x08AFF2EC, 0x00000000, 'sltiu t9,s4,0x21'),   # bne delay slot (both paths): t9 = owner < 33
    (0x08AFF310, 0x00000000, 'addu t9,t9,s4'),      # beq delay slot (both paths): t9 = sprite owner + 1
    (0x08AFF318, 0x34050001, 'addiu s4,t9,-1'),     # was a redundant `ori a1,zero,1` (a1 is still 1)
    (0x08AFF388, 0x00942021, 'addu a0,a0,t9'),      # hide path: base + sprite owner + 1 ...
    (0x08AFF398, 0x8C840004, 'lw a0,0x0(a0)'),      # ... so no +4 here
]
CUST_PACK = 'menu/menu_pk_customize_gim_0.bin'
CUST_ICON = 107                                      # id 3179 = owner-1 slot 32 (spot33_qbpics customize_inplace)
AERITH_ICON_SHA = '69d6a22abef201f61c01d39ecdb1bfd52813431f97cd2727be84647b242b5ec8'   # vanilla entry 107
NET_PACK = 'menu/menu_pk_network_gim_0.bin'
NET_LPK = 'menu/EN/menu_lpk_network_gim_0.bin'
NET_COUNT, NET_BASE = 129, 8192
NET_ID = NET_BASE + NET_COUNT                        # 8321, entry 129
NET_LIMIT = 0x100000                                 # FUN_08a20ae8 load buffer (FUN_088d00fc 0x100000, group 9)
# (VA of the texture u16 in a part pair, seq id, vanilla texture, new texture, label)
PARTS = [
    (0x08AEB130 + (57 - 6) * 4 + 2, 3698, 3178, 3179, 'customize part 57'),
    (0x08B1B5B8 + 68 * 4 + 2, 7746, 7268, 7269, 'shop part 68'),
    (0x08A23538 + 53 * 4 + 2, 8756, 8240, NET_ID, 'artifacts part 53'),
]


def ovl_off(va):
    return MENU_ISO_SECTOR * SECTOR + va - MENU_VADDR + MENU_FILEOFF


def pack(f, path):
    st, sz = pkg_offset(path)
    return read_at(f, st, sz)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry' in sys.argv
    iso = args[0]
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the vanilla ISO'
    use_iso(iso)
    with open(iso, 'rb') as f:
        code = []
        for va, old, line in CODE:
            new, = asm([line], va)
            f.seek(ovl_off(va))
            cur, = struct.unpack('<I', f.read(4))
            if cur not in (old, new):
                sys.exit('code %08x: unexpected word %08x (want %08x or %08x)' % (va, cur, old, new))
            code.append((va, new, cur == new, line))
        parts = []
        for va, seq, old, new, label in PARTS:
            f.seek(ovl_off(va - 2))
            s, t = struct.unpack('<hh', f.read(4))
            if s != seq or t not in (old, new):
                sys.exit('%s @%08x: (%d, %d), want (%d, %d or %d)' % (label, va, s, t, seq, old, new))
            parts.append((va, old, new, t == new, label))
        _, cust = read_pack(pack(f, CUST_PACK))
        icon = cust[CUST_ICON]
        assert icon[:4] == b'MIG.' and len(icon) == 3360, 'customize entry %d is not a 32x64 icon GIM' % CUST_ICON
        assert hashlib.sha256(icon).hexdigest() != AERITH_ICON_SHA, \
            'customize entry %d is still Aerith: run spot33_qbpics first' % CUST_ICON
        net_raw = pack(f, NET_PACK)
        lpk_raw = pack(f, NET_LPK)
    base, net = read_pack(net_raw)
    lbase, lpk = read_pack(lpk_raw)
    assert base == NET_BASE and lbase == NET_BASE and len(lpk) == NET_COUNT, 'network packs moved'
    assert len(net) in (NET_COUNT, NET_COUNT + 1), 'network pk has %d entries (another script?)' % len(net)
    assert len(net[48]) == len(icon), 'network icon size differs from the customize icon'
    net_done = len(net) == NET_COUNT + 1 and net[NET_COUNT] == icon
    for va, new, done, line in code:
        print('  code %08x %-18s %s' % (va, line, 'already' if done else 'patch'))
    for va, old, new, done, label in parts:
        print('  %-18s texture %d -> %d%s' % (label, old, new, ' already' if done else ''))
    print('  %s entry %d (id %d) = Customization Sora icon (sha %s)%s' % (
        NET_PACK, NET_COUNT, NET_ID, hashlib.sha256(icon).hexdigest()[:12], ' already' if net_done else ''))
    new_net = None
    if not net_done:
        blobs = net[:NET_COUNT] + [icon]
        new_net = write_pack(net_raw, base, blobs)
        nb, chk = read_pack(new_net)
        assert nb == base and chk[:NET_COUNT] == net[:NET_COUNT] and chk[NET_COUNT] == icon, 'network pk rebuild'
        assert len(new_net) <= NET_LIMIT, 'network pk %d > load buffer %d' % (len(new_net), NET_LIMIT)
        print('  %s: %d -> %d entries, %d -> %d bytes' % (NET_PACK, len(net), len(blobs), len(net_raw), len(new_net)))
    if dry:
        print('dry run, nothing written')
        return
    with open(iso, 'r+b') as f:
        for va, new, done, line in code:
            if not done:
                f.seek(ovl_off(va))
                f.write(struct.pack('<I', new))
        for va, old, new, done, label in parts:
            if not done:
                f.seek(ovl_off(va))
                f.write(struct.pack('<h', new))
    if new_net is not None:
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, 'net.bin')
            open(p, 'wb').write(new_net)
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, NET_PACK, p],
                               check=True, capture_output=True, text=True)
            print('   ', r.stdout.strip())
    print('done')


if __name__ == '__main__':
    main()
