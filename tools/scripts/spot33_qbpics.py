"""#33's own Quick Battle select pictures (grid icon, big art, name, game logo, face strips) — notes/qb-grid-pictures.md.

Textures in the free-battle scene have id = pack id_base + entry index; each screen slot draws id = slot base +
a field of the grid row (table 0x08A864D0 in OVL_MENU_APP.ELF: i16 pic, i16 name_pic, i16 logo, i16 ?, i32 owner).
All ids 28672..28928 are taken, so new GIMs are APPENDED to menu/menu_pk_free_battle_gim_3.bin (id_base 28799,
130 entries) at the indexes that the row values below select (size-0 entries fill the gaps):
  PIC 245: art 0x700C+245 = idx 130, icon 0x702F+245 = idx 165, face 0x70B2+245 = idx 296, face_r 0x70D2+245 = idx 328
  NAME 245: 0x704F+245 = idx 197 (same number as PIC: the setup screen uses ONE number)   LOGO 148: idx 132
Setup screen (Enter Battle list): its banners use owner-1 as the number (owner 33 → 32 = wrong textures), so
SETUP_PATCH remaps 32 → 245 in FUN_08aa44ac / FUN_08aa6148 of OVL_MENU_APP.ELF (notes/qb-grid-pictures.md;
the three spare words come from removing redundant `lw a0,0x1EE4(s0)` reloads).
New GIMs = Cloud's GIM of the same slot (same size/format) with Sora's pixels (gim_put.put, tools/art/qb_*.png from
make_select_art.py). Pack must stay <= 0xE1000 bytes (load buffer).

  python3 -I spot33_qbpics.py ISO
"""
import os
import struct
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from gim_put import put  # noqa: E402
from gim_markers import keep  # noqa: E402
from roster_patch import MENU_FILEOFF, MENU_ISO_SECTOR, MENU_VADDR, QB_TABLE  # noqa: E402
from comb_patch import SECTOR  # noqa: E402

PACKS = ['menu/menu_pk_free_battle_gim_0.bin', 'menu/menu_pk_free_battle_gim_1.bin',
         'menu/menu_pk_free_battle_gim_2.bin', 'menu/menu_pk_free_battle_gim_3.bin',
         'menu/EN/menu_lpk_free_battle_gim_0.bin']
TARGET = 'menu/menu_pk_free_battle_gim_3.bin'
PIC, NAME, LOGO, CLOUD_PIC, CLOUD_LOGO = 245, 245, 148, 12, 6
SLOTS = {'art': (0x700C, 'pic'), 'icon': (0x702F, 'pic'), 'face': (0x70B2, 'pic'), 'face_r': (0x70D2, 'pic'),
         'name': (0x704F, 'name'), 'logo': (0x706F, 'logo')}
LIMIT = 0xE1000


SETUP_PATCH = [   # (VA, old word, new word)
    (0x08AA4570, 0x8E041EE4, 0x3405002A), (0x08AA4574, 0x3405002A, 0xA4851E5A), (0x08AA4578, 0xA4851E5A, 0x34050003),
    (0x08AA457C, 0x8E041EE4, 0xA4851E5E), (0x08AA4580, 0x34050003, 0x3A880020), (0x08AA4584, 0xA4851E5E, 0x240900F5),
    (0x08AA4588, 0x8E041EE4, 0x0128A00A),
    (0x08AA6268, 0x8E041EE4, 0x34050018), (0x08AA626C, 0x34050018, 0xA4851E60), (0x08AA6270, 0xA4851E60, 0x96C50008),
    (0x08AA6274, 0x96C40008, 0xA4851E64), (0x08AA6278, 0x8E051EE4, 0x3AA80020), (0x08AA627C, 0xA4A41E64, 0x240900F5),
    (0x08AA6280, 0x8E041EE4, 0x0128A80A)]
# player banner frame row (table 0x08AA8864, 10-byte rows, owner-1 index; owner 33 read past the end → no blue band):
# rewrite 0x08AA44F8..453C so owner-1 == 32 uses row 12 = owner 13 Cloud's frames 24/26/25/27/11 (fixes the art position; the blue name band is still missing).
# Room: load the frame into a1 and obj+0xA8 into a0 directly instead of loading swapped + a 3-instruction swap.
FRAME_PATCH = [
    (0x08AA44F8, 0xAFB10004, 0xAFB10004),  # sw s1,4(sp)
    (0x08AA44FC, 0xAFBF0018, 0xAFBF0018),  # sw ra,24(sp)
    (0x08AA4500, 0x14A00007, 0x3A820020),  # xori v0,s4,0x20
    (0x08AA4504, 0x00E08825, 0x26A3FF38),  # addiu v1,s5,-200       (row 32 address - 20 rows = row 12, Cloud's)
    (0x08AA4508, 0x0E23673F, 0x0062A80A),  # movz s5,v1,v0
    (0x08AA450C, 0x00000000, 0x14A00007),  # bne a1,zero,0x08AA452C
    (0x08AA4510, 0x96A40000, 0x00E08825),  # or s1,a3,zero (delay)
    (0x08AA4514, 0x8E051EE4, 0x0E23673F),  # jal 0x088d9cfc
    (0x08AA4518, 0x10000006, 0x00000000),  # nop
    (0x08AA451C, 0x8CA500A8, 0x96A50000),  # lhu a1,0(s5)
    (0x08AA4520, 0x0E236736, 0x8E041EE4),  # lw a0,0x1EE4(s0)
    (0x08AA4524, 0x00000000, 0x10000006),  # b 0x08AA4540
    (0x08AA4528, 0x96A40004, 0x8C8400A8),  # lw a0,0xA8(a0) (delay)
    (0x08AA452C, 0x8E051EE4, 0x0E236736),  # jal 0x088d9cd8
    (0x08AA4530, 0x8CA500A8, 0x00000000),  # nop
    (0x08AA4534, 0x00803025, 0x96A50004),  # lhu a1,4(s5)
    (0x08AA4538, 0x00A02025, 0x8E041EE4),  # lw a0,0x1EE4(s0)
    (0x08AA453C, 0x00C02825, 0x8C8400A8)]  # lw a0,0xA8(a0)   → 0x08AA4540 jal 0x088d9f5c (a2 = 1 in its delay slot)

# CPU banner (FUN_08aa6148): frame row also owner-1 indexed → owner 33 uses Cloud's row 12 (frames 26/27, locator 11)
# (research note "CPU-side art"; field offset in t2 = 2/6, both branches share one row block)
CPU_FRAME_PATCH = [
    (0x08AA6194, 0x14C00012, 0x14C0000D), (0x08AA61B0, 0x10A00005, 0x10A00009), (0x08AA61B4, 0x8C8400AC, 0x340A0002),
    (0x08AA61B8, 0x16200003, 0x16200007), (0x08AA61C4, 0x34140001, 0x10000004), (0x08AA61C8, 0x001528C0, 0x34140001),
    (0x08AA61CC, 0x02A52821, 0x0E236736), (0x08AA61D0, 0x02A52821, 0x00000000), (0x08AA61D4, 0x00B6B021, 0x340A0006),
    (0x08AA61D8, 0x1000000A, 0x001528C0), (0x08AA61DC, 0x96C50002, 0x02A52821), (0x08AA61E0, 0x0E236736, 0x02A52821),
    (0x08AA61E4, 0x00000000, 0x00B6B021), (0x08AA61E8, 0x001520C0, 0x3AA80020), (0x08AA61EC, 0x02A42021, 0x26C9FF38),
    (0x08AA61F0, 0x02A42021, 0x0128B00A), (0x08AA61F4, 0x0096B021, 0x02CA2821), (0x08AA61F8, 0x96C50006, 0x94A50000)]


def setup_patch(iso):
    with open(iso, 'r+b') as f:
        for va, old, new in SETUP_PATCH + FRAME_PATCH + CPU_FRAME_PATCH:
            at = MENU_ISO_SECTOR * SECTOR + va - MENU_VADDR + MENU_FILEOFF
            f.seek(at)
            cur, = struct.unpack('<I', f.read(4))
            if cur == new:
                continue
            assert cur == old, 'unexpected word %08x at %08x' % (cur, va)
            f.seek(at)
            f.write(struct.pack('<I', new))
    print('setup screen: owner-1 = 32 -> %d patched in FUN_08aa44ac / FUN_08aa6148 (+ player banner frame row 12)'
          % PIC)


def read_pack(d):
    assert d[:8] == b'menu pak', d[:8]
    cnt, base = struct.unpack_from('<HH', d, 0x0A)
    ents = [struct.unpack_from('<II', d, 0x10 + i * 8) for i in range(cnt)]
    return base, [d[o:o + s] if s else b'' for o, s in ents]


def write_pack(d, base, blobs):
    head = bytearray(d[:0x10])
    struct.pack_into('<HH', head, 0x0A, len(blobs), base)
    pos = 0x10 + 8 * len(blobs)
    pos += (-pos) % 16
    table, data = bytearray(), bytearray()
    for b in blobs:
        if b:
            table += struct.pack('<II', pos + len(data), len(b))
            data += b + b'\0' * ((-len(b)) % 16)
        else:
            table += struct.pack('<II', 0, 0)
    out = bytes(head + table)
    return out + b'\0' * ((-len(out)) % 16) + bytes(data)


# Customization → Character Select (scene group 0x22, notes/qb-grid-pictures.md): same grid row, bases at 0x400,
# packs below; our GIMs are appended to upper_chara_select_gim_1 (base 1059). Template ids = Cloud's (pic 12, logo 6).
CS_PACKS = ['menu/menu_pk_upper_chara_select_gim_0.bin', 'menu/menu_pk_upper_chara_select_gim_1.bin',
            'menu/EN/menu_lpk_upper_chara_select_gim_0.bin']
CS_TARGET = 'menu/menu_pk_upper_chara_select_gim_1.bin'
CS_SLOTS = {'art': (0x40E, 'pic'), 'icon': (0x431, 'pic'), 'name': (0x451, 'name'), 'logo': (0x471, 'logo')}
# Customization menu (group 5) uses owner-1 = Aerith's old slot 32: replace in place (entry index in the pack)
CUST_PACK = 'menu/menu_pk_customize_gim_0.bin'
CUST_INPLACE = {74: 'custface', 107: 'icon'}


def add_scene(iso, packs, target, slots, min_idx):
    f = open(iso, 'rb')
    by_id, raw = {}, {}
    for p in packs:
        st, sz = pkg_offset(p)
        raw[p] = read_at(f, st, sz)
        base, blobs = read_pack(raw[p])
        for i, b in enumerate(blobs):
            if b:
                by_id[base + i] = b
    f.close()
    vals = {'pic': PIC, 'name': NAME, 'logo': LOGO}
    cloud = {'pic': CLOUD_PIC, 'name': CLOUD_PIC, 'logo': CLOUD_LOGO}
    base, blobs = read_pack(raw[target])
    for tag, (slot, field) in slots.items():
        new_id, old_id = slot + vals[field], slot + cloud[field]
        idx = new_id - base
        assert idx >= min_idx, (tag, new_id)
        img, nmark = keep(by_id[old_id], Image.open(os.path.join(ROOT, 'tools/art/qb_%s.png' % tag)).convert('RGBA'))
        gim = put(by_id[old_id], img)
        while len(blobs) <= idx:
            blobs.append(b'')
        blobs[idx] = gim
        print('%-6s id %d -> %s entry %d (template id %d, %d marker px)' % (tag, new_id, os.path.basename(target), idx, old_id, nmark))
    new = write_pack(raw[target], base, blobs)
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'pack.bin')
        open(p, 'wb').write(new)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, target, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip(), '(%d entries, %d bytes)' % (len(blobs), len(new)))


def customize_inplace(iso):
    st, sz = pkg_offset(CUST_PACK)
    with open(iso, 'rb') as f:
        raw = read_at(f, st, sz)
    base, blobs = read_pack(raw)
    for idx, tag in CUST_INPLACE.items():
        tpl = blobs[idx]
        img, nmark = keep(tpl, Image.open(os.path.join(ROOT, 'tools/art/qb_%s.png' % tag)).convert('RGBA'))
        blobs[idx] = put(tpl, img)
        print('customize entry %d (id %d) <- qb_%s (%d marker px)' % (idx, base + idx, tag, nmark))
    new = write_pack(raw, base, blobs)
    assert len(new) <= sz + 2048, (len(new), sz)
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'pack.bin')
        open(p, 'wb').write(new)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, CUST_PACK, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


def main():
    iso = sys.argv[1]
    use_iso(iso)
    add_scene(iso, CS_PACKS, CS_TARGET, CS_SLOTS, 104)
    customize_inplace(iso)
    f = open(iso, 'rb')
    by_id, raw = {}, {}
    for p in PACKS:
        st, sz = pkg_offset(p)
        raw[p] = read_at(f, st, sz)
        base, blobs = read_pack(raw[p])
        for i, b in enumerate(blobs):
            if b:
                by_id[base + i] = b
    f.close()
    vals = {'pic': PIC, 'name': NAME, 'logo': LOGO}
    cloud = {'pic': CLOUD_PIC, 'name': CLOUD_PIC, 'logo': CLOUD_LOGO}
    base, blobs = read_pack(raw[TARGET])
    for tag, (slot, field) in SLOTS.items():
        new_id, old_id = slot + vals[field], slot + cloud[field]
        idx = new_id - base
        assert idx >= 130 and (new_id not in by_id or new_id >= 28929), (tag, new_id)
        img, nmark = keep(by_id[old_id], Image.open(os.path.join(ROOT, 'tools/art/qb_%s.png' % tag)).convert('RGBA'))
        gim = put(by_id[old_id], img)                       # grey marker texels kept (name band!)
        while len(blobs) <= idx:
            blobs.append(b'')
        blobs[idx] = gim
        print('%-6s id %d -> %s entry %d (template id %d, %d marker px)' % (tag, new_id, os.path.basename(TARGET), idx, old_id, nmark))
    new = write_pack(raw[TARGET], base, blobs)
    assert len(new) <= LIMIT, 'pack too big: %d > %d' % (len(new), LIMIT)
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'pack.bin')
        open(p, 'wb').write(new)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, TARGET, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip(), '(%d entries, %d bytes)' % (len(blobs), len(new)))
    # grid row of owner 33: picture / name picture / logo
    tab = MENU_ISO_SECTOR * SECTOR + QB_TABLE - MENU_VADDR + MENU_FILEOFF
    with open(iso, 'r+b') as f:
        for i in range(40):
            f.seek(tab + i * 12)
            row = f.read(12)
            pic, npic, logo, x, owner = struct.unpack('<4hi', row)
            if owner == 33:
                f.seek(tab + i * 12)
                f.write(struct.pack('<3h', PIC, NAME, LOGO))
                setup_patch(iso)
                print('grid row %d (owner 33): pic %d->%d, name %d->%d, logo %d->%d' % (i, pic, PIC, npic, NAME, logo, LOGO))
                break
            if owner <= 0:
                sys.exit('owner 33 not in the grid table')


if __name__ == '__main__':
    main()
