"""Sora (owner 33) on the remaining menu screens: Quick Battle party, story "An Untold Tale" party menus, party
setting / arrange, Original Quest grid, level adjust, Labyrinth. Findings: notes/menu-art.md.

1. CODE (OVL_MENU_APP.ELF): every draw that builds a picture id as `base + owner - 1` maps owner 33 to picture 32,
   which is the first picture of the NEXT run (WoL's face strip, a "handicap" banner, the FF1 logo...). Each site
   is rewritten in place (redundant `andi 0xffff` / `andi 0xff` / nop slots freed) so that owner - 1 == 32 becomes
   245 = the picture number Sora's grid row already uses (spot33_qbpics). Party slots (FUN_08b2c330) also play a
   per-owner frame from u16 table 0x08B2D168[owner-1] (31 entries); owner 33 now uses owner 24's entry (frame 14,
   the 012 newcomers' frame) instead of reading the next table.
2. DATA: Labyrinth owner table 0x08B4173C (6-byte rows by owner: u16 wm icon id, u16, i16): owner 33's row is zero
   padding -> no face. Its icon id becomes 0x102D = a new wm_ GIM appended to menu_pk_dungeon_gim_0 (entry 45).
3. PICTURES: each scene gets Sora's pictures at base + 245 (logo base + 148), appended to one of its packs (size-0
   filler entries in between; no existing entry moves or changes). Pixels = Sora's own GIMs from the free-battle
   pack (what Mat approved there), re-encoded into that scene's Cloud template (keep() grey marker texels);
   Original Quest art = the approved portrait. The common name-plate face strip
   menu/JP/common/chara_face_in_name/p_sev120_face_in_name.gim (still Aerith's) gets Sora's face.

Guards: every code/data word must be the original or our value (all checked before anything is written); packs:
each existing entry is compared byte for byte after the rebuild; re-running changes nothing ("already").

4. Aerith leftovers (Mat, test321: Shop showed Aerith): menu_pk_shop_gim_0 entries 68 (face strip) / 101 (icon) and
   menu_pk_level_adjust_gim_0 entry 73 = Aerith's vanilla GIMs in the owner-1 = 32 slot -> Sora's Customization
   pictures, in place (same size).

  python3 -I spot33_menuart.py ISO [--dry] [--renders DIR]
"""
import hashlib
import os
import struct
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import gim as gimlib  # noqa: E402
from comb_patch import SECTOR, pkg_offset, read_at, use_iso  # noqa: E402
from gim_markers import keep  # noqa: E402
from gim_put import put  # noqa: E402
from mips_asm import asm  # noqa: E402
from roster_patch import MENU_FILEOFF, MENU_ISO_SECTOR, MENU_VADDR  # noqa: E402
import spot33_qbpics as Q  # noqa: E402

PIC, LOGO, CLOUD_PIC, CLOUD_LOGO = 245, 148, 12, 6
REMAP = ['addiu t1,{o},-1', 'xori t2,t1,0x20', 'addiu t3,zero,245', 'movz t1,t3,t2']   # t1 = owner==33 ? 245 : owner-1

# (start VA, original words, new code). New code is assembled at run time and must have the same length.
SITES = [
    # story FUN_08a8d0d8: face_r (DAT_08a93b1a) and name (DAT_08a93b1c) of the current character (owner s1)
    (0x08A8D130, '86463b1a 8c880118 30a400ff 00d12821 24a5ffff 30a7ffff 308600ff 3c13089d 8e647830 30e7ffff '
                 '0e234261 01002825',
     ['lh a2,0x3b1a(s2)', 'lw t0,0x118(a0)'] + [s.format(o='s1') for s in REMAP] +
     ['addu a3,a2,t1', 'andi a2,a1,0xff', 'lui s3,0x89d', 'lw a0,0x7830(s3)', 'jal 0x088d0984', 'move a1,t0']),
    (0x08A8D184, '8e060004 84a50002 8c88011c 00b12021 2484ffff 30c600ff 3087ffff 8e647830 30c600ff 30e7ffff '
                 '0e234261 01002825',
     ['lw a2,4(s0)', 'lh a1,2(a1)', 'lw t0,0x11c(a0)'] + [s.format(o='s1') for s in REMAP] +
     ['addu a3,a1,t1', 'andi a2,a2,0xff', 'lw a0,0x7830(s3)', 'jal 0x088d0984', 'move a1,t0']),
    # free-battle party module (bases at obj+0x66C grid / +0x66E face / +0x670 face_r)
    (0x08AAC364, '00d13021 9084000a 24c6ffff 30c7ffff 308600ff 3c04089d 8c847830 0e234261 30e7ffff',
     [s.format(o='s1') for s in REMAP] +
     ['addu a3,a2,t1', 'lbu a2,10(a0)', 'lui a0,0x89d', 'jal 0x088d0984', 'lw a0,0x7830(a0)']),
    (0x08AAC49C, '9227000a 00c42021 30e600ff 2484ffff 3c07089d 3084ffff 8ce87830 3087ffff 0e234261 01002025',
     [s.format(o='a0') for s in REMAP] +
     ['addu a3,a2,t1', 'lbu a2,10(s1)', 'lui a0,0x89d', 'jal 0x088d0984', 'lw a0,0x7830(a0)', 'nop']),
    (0x08AACCDC, '00d03021 9084000a 24c6ffff 30c7ffff 308600ff 8fc47830 0e234261 30e7ffff',
     [s.format(o='s0') for s in REMAP] + ['addu a3,a2,t1', 'lbu a2,10(a0)', 'jal 0x088d0984', 'lw a0,0x7830(fp)']),
    (0x08AACE8C, '00e52021 2484ffff 3087ffff 8fc47830 30c600ff 30e7ffff 0e234261 01002825',
     [s.format(o='a1') for s in REMAP] + ['addu a3,a3,t1', 'lw a0,0x7830(fp)', 'jal 0x088d0984', 'move a1,t0']),
    # level adjust: face (0x8029) and name (0x8009) bases from 0x08B27EF0, owner s0
    (0x08B263A0, '00d03021 24c6ffff 00b42821 308400ff 30c7ffff 8ca5000c 308600ff 3c12089d 8e447830 0e234261 '
                 '30e7ffff',
     [s.format(o='s0') for s in REMAP] +
     ['addu a3,a2,t1', 'addu a1,a1,s4', 'lw a1,12(a1)', 'andi a2,a0,0xff', 'lui s2,0x89d', 'jal 0x088d0984',
      'lw a0,0x7830(s2)']),
    (0x08B26400, '00b02021 2484ffff 3087ffff 8e447830 30c600ff 30e7ffff 0e234261 01002825',
     [s.format(o='s0') for s in REMAP] + ['addu a3,a1,t1', 'lw a0,0x7830(s2)', 'jal 0x088d0984', 'move a1,t0']),
    # party list FUN_08b2aa04: grid icon of each party (owner a1; a1 is reloaded each loop)
    (0x08B2AB64, '00e52021 2484ffff 3087ffff 8e647830 30c600ff 30e7ffff',
     ['addiu a1,a1,-1', 'xori t1,a1,0x20', 'addiu t2,zero,245', 'movz a1,t2,t1', 'addu a3,a3,a1',
      'lw a0,0x7830(s3)']),
    # party member slots FUN_08b2c330 (owner s0): s6 = owner==33 ? 246 : owner (s6 is free until 0x08B2C654),
    # used by grid / face_r / name; frame table index = owner==33 ? 24 : owner. Blocks re-laid out without the
    # duplicate andi's (no branch targets inside 0x08B2C520..0x08B2C630).
    (0x08B2C520, '00000000 94850014 8c860018 00b72821 00052880 00c52821 94860734 8ca50004 00d03021 90840016 '
                 '24c6ffff 30c7ffff 308600ff 3c12089d 8e447830 0e234261 30e7ffff 8e240a18 00149880 00932021 '
                 '8c840074 34050001 0e2367d7 34060001 8e240a18 94850014 8c860018 00b72821 00052880 00c52821 '
                 '94860738 8ca50020 00d03021 90840016 24c6ffff 30c7ffff 308600ff 8e447830 0e234261 30e7ffff '
                 '8e240a18 00932021 0e236736 8c84008c 8e240a18 94850014 8c860018 00b72821 00052880 00c52821 '
                 '9486073a 8ca50038 00d03021 90840016 24c6ffff 30c7ffff 308600ff 8e447830 0e234261 30e7ffff '
                 '8e240a18 8fa50784 00932021 02103021 8c840084 00c52821 94a5fffe 0e2367d7 34060001',
     ['xori t0,s0,0x21',                                                       # beq delay slot (was nop)
      'lhu a1,0x14(a0)', 'lw a2,0x18(a0)', 'addu a1,a1,s7', '.word 0x00052880', 'addu a1,a2,a1', 'lhu a2,0x734(a0)',
      'lw a1,4(a1)', 'addiu s6,zero,246', 'movn s6,s0,t0', 'addu a2,a2,s6', 'addiu a2,a2,-1', 'andi a3,a2,0xffff',
      'lbu a2,0x16(a0)', 'lui s2,0x89d', 'jal 0x088d0984', 'lw a0,0x7830(s2)',
      'lw a0,0xa18(s1)', '.word 0x00149880', 'addu a0,a0,s3', 'lw a0,0x74(a0)', 'ori a1,zero,1', 'jal 0x088d9f5c',
      'ori a2,zero,1',
      'lw a0,0xa18(s1)', 'lhu a1,0x14(a0)', 'lw a2,0x18(a0)', 'addu a1,a1,s7', '.word 0x00052880', 'addu a1,a2,a1',
      'lhu a2,0x738(a0)', 'lw a1,0x20(a1)', 'addu a2,a2,s6', 'addiu a2,a2,-1', 'andi a3,a2,0xffff',
      'lbu a2,0x16(a0)', 'jal 0x088d0984', 'lw a0,0x7830(s2)',
      'lw a0,0xa18(s1)', 'addu a0,a0,s3', 'jal 0x088d9cd8', 'lw a0,0x8c(a0)',
      'lw a0,0xa18(s1)', 'lhu a1,0x14(a0)', 'lw a2,0x18(a0)', 'addu a1,a1,s7', '.word 0x00052880', 'addu a1,a2,a1',
      'lhu a2,0x73a(a0)', 'lw a1,0x38(a1)', 'addu a2,a2,s6', 'addiu a2,a2,-1', 'andi a3,a2,0xffff',
      'lbu a2,0x16(a0)', 'jal 0x088d0984', 'lw a0,0x7830(s2)',
      'xori t0,s6,246', 'addiu a2,zero,48', 'addu t1,s0,s0', 'movn a2,t1,t0',        # frame row: Sora -> owner 24
      'lw a0,0xa18(s1)', 'lw a1,0x784(sp)', 'addu a0,a0,s3', 'lw a0,0x84(a0)', 'addu a1,a2,a1', 'lhu a1,-2(a1)',
      'jal 0x088d9f5c', 'ori a2,zero,1', 'nop']),
    # party select (obj+0x844, face_r base +0x558), owner s4
    (0x08B2DBA4, '00d43021 90840014 24c6ffff 30c7ffff 308600ff 8e447830 0e234261 30e7ffff',
     [s.format(o='s4') for s in REMAP] + ['addu a3,a2,t1', 'lbu a2,0x14(a0)', 'jal 0x088d0984', 'lw a0,0x7830(s2)']),
    # module at obj+0x9d8 (config copied at +0x7A0): face (+0x7CA) and name (+0x7CE), owner s1
    (0x08B30BE0, '00d13021 9084000a 24c6ffff 30c7ffff 308600ff 3c12089d 8e447830 0e234261 30e7ffff',
     [s.format(o='s1') for s in REMAP] +
     ['addu a3,a2,t1', 'lbu a2,10(a0)', 'lui s2,0x89d', 'jal 0x088d0984', 'lw a0,0x7830(s2)']),
    (0x08B30C24, '00d13021 9084000a 24c6ffff 30c7ffff 308600ff 8e447830 0e234261 30e7ffff',
     [s.format(o='s1') for s in REMAP] + ['addu a3,a2,t1', 'lbu a2,10(a0)', 'jal 0x088d0984', 'lw a0,0x7830(s2)']),
]

# Labyrinth owner table row 33: u16 wm icon id (0 = none) -> our new wm GIM
DUNGEON_ROW33 = 0x08B4173C + 33 * 6
DUNGEON_PACK = 'menu/menu_pk_dungeon_gim_0.bin'
WM_ID, WM_TEMPLATE_ID = 0x102D, 0x1016            # 0x1016 = wm_sev100 (Cloud, table row 13)

# scene picture runs: name -> (target pack, all packs of the scene, load buffer, {tag: base})
SCENES = {
    'story': ('menu/menu_pk_upper_story_mode_gim_2.bin',
              ['menu/menu_pk_upper_story_mode_gim_0.bin', 'menu/menu_pk_upper_story_mode_gim_1.bin',
               'menu/menu_pk_upper_story_mode_gim_2.bin', 'menu/EN/menu_lpk_upper_story_mode_gim_0.bin'],
              0x100000, {'icon': 0x74AB, 'face': 0x744A, 'face_r': 0x746A, 'name': 0x742A, 'logo': 0x748A}),
    'party_setting': ('menu/menu_pk_party_setting_gim_1.bin',
                      ['menu/menu_pk_party_setting_gim_0.bin', 'menu/menu_pk_party_setting_gim_1.bin',
                       'menu/EN/menu_lpk_party_setting_gim_0.bin'],
                      0xB6800, {'icon': 0x600F, 'face': 0x602F, 'face_r': 0x604F, 'name': 0x606F, 'logo': 0x608F}),
    'party_arrange': ('menu/menu_pk_party_arrange_gim_1.bin',
                      ['menu/menu_pk_party_arrange_gim_0.bin', 'menu/menu_pk_party_arrange_gim_1.bin',
                       'menu/EN/menu_lpk_party_arrange_gim_0.bin'],
                      0xB6800, {'icon': 0x940C, 'face_r': 0x942C, 'name': 0x944C, 'logo': 0x946C}),
    'original_quest': ('menu/menu_pk_original_quest_gim_3.bin',
                       ['menu/menu_pk_original_quest_gim_0.bin', 'menu/menu_pk_original_quest_gim_1.bin',
                        'menu/menu_pk_original_quest_gim_2.bin', 'menu/menu_pk_original_quest_gim_3.bin',
                        'menu/EN/menu_lpk_original_quest_gim_0.bin'],
                      0x100000, {'icon': 0x6434, 'art': 0x6411, 'face': 0x64DA, 'face_r': 0x64B7, 'name': 0x6454,
                                 'logo': 0x6474}),
    'level_adjust': ('menu/menu_pk_level_adjust_gim_0.bin',
                     ['menu/menu_pk_level_adjust_gim_0.bin', 'menu/EN/menu_lpk_level_adjust_gim_0.bin'],
                     0xB6800, {'face': 0x8029, 'name': 0x8009}),
}
# Sora's approved free-battle GIMs (spot33_qbpics / spot33_portrait) = pixel source for every scene
FREE_IDS = {'icon': 0x702F + PIC, 'face': 0x70B2 + PIC, 'face_r': 0x70D2 + PIC, 'name': 0x704F + PIC,
            'logo': 0x706F + LOGO}
APPROVED_ART = os.path.join(ROOT, 'tools', 'art', 'approved', 'qb_art.png')
APPROVED_ART_SHA = '4df846c07b44fd74ab8bc9a66008ec8920f7f226f564fd326596f6cca1fb7e6c'
WM_PNG = os.path.join(ROOT, 'tools', 'art', 'sora_wm.png')
COMMON_FACE = 'menu/JP/common/chara_face_in_name/p_sev120_face_in_name.gim'
COMMON_FACE_CLOUD = 'menu/JP/common/chara_face_in_name/p_sev100_face_in_name.gim'
COMMON_FACE_AERITH_SHA = 'a5d83c5582480e5c8e7e153822dbc3a1187ad70884deff392bb7984f9ebc7995'   # vanilla (Aerith)


def ovl_off(va):
    return MENU_ISO_SECTOR * SECTOR + va - MENU_VADDR + MENU_FILEOFF


def words_at(f, va, n):
    f.seek(ovl_off(va))
    return list(struct.unpack('<%dI' % n, f.read(4 * n)))


def code_plan(iso):
    """-> list of (va, old words, new words, state) ; state 'old' / 'new'"""
    plan = []
    with open(iso, 'rb') as f:
        for va, old, lines in SITES:
            old = [int(x, 16) for x in old.split()]
            new = asm(lines, va)
            assert len(new) == len(old), (hex(va), len(new), len(old))
            cur = words_at(f, va, len(old))
            if cur == new:
                state = 'new'
            elif cur == old:
                state = 'old'
            else:
                bad = [(hex(va + 4 * i), '%08x' % c) for i, c in enumerate(cur) if c not in (old[i], new[i])]
                sys.exit('code site %08x: unexpected words %s' % (va, bad[:4]))
            plan.append((va, old, new, state))
        f.seek(ovl_off(DUNGEON_ROW33))
        row = struct.unpack('<HHh', f.read(6))
    assert row in ((0, 0, -1), (WM_ID, 0, -1)), 'Labyrinth row 33 = %r' % (row,)
    return plan, row


def read_scene(iso, packs):
    by_id, raw = {}, {}
    use_iso(iso)
    with open(iso, 'rb') as f:
        for p in packs:
            st, sz = pkg_offset(p)
            raw[p] = read_at(f, st, sz)
            base, blobs = Q.read_pack(raw[p])
            for i, b in enumerate(blobs):
                if b:
                    by_id.setdefault(base + i, (p, i, b))
    return by_id, raw


def gim_size(g):
    return struct.unpack_from('<HH', g, 0x48)


def picture(tag, src):
    """RGBA picture for a tag: decoded free-battle GIM (exact, <= 256 colours) / approved portrait / wm PNG"""
    if tag == 'art':
        assert hashlib.sha256(open(APPROVED_ART, 'rb').read()).hexdigest() == APPROVED_ART_SHA, 'approved art changed'
        return Image.open(APPROVED_ART).convert('RGBA')
    if tag == 'wm':
        return Image.open(WM_PNG).convert('RGBA')
    return gimlib.decode(src[tag]).convert('RGBA')


def scene_plan(iso, name, src):
    target, packs, limit, bases = SCENES[name]
    by_id, raw = read_scene(iso, packs)
    base, blobs = Q.read_pack(raw[target])
    adds = {}
    for tag, b0 in bases.items():
        new_id = b0 + (LOGO if tag == 'logo' else PIC)
        tpl_id = b0 + (CLOUD_LOGO if tag == 'logo' else CLOUD_PIC)
        tpl = by_id[tpl_id][2]
        img, nmark = keep(tpl, picture(tag, src))
        assert img.size == gim_size(tpl), (name, tag, img.size, gim_size(tpl))
        gim = put(tpl, img)
        idx = new_id - base
        owner = by_id.get(new_id)
        if owner and (owner[0] != target or owner[2] != gim):
            sys.exit('%s: id %d already used by %s[%d]' % (name, new_id, os.path.basename(owner[0]), owner[1]))
        adds[idx] = (tag, new_id, tpl_id, gim, nmark)
    return target, raw[target], base, blobs, adds, limit


def apply_pack(iso, target, raw, base, blobs, adds, limit, dry, label):
    orig_n = len(blobs)
    new_blobs = list(blobs)
    for idx in sorted(adds):
        while len(new_blobs) <= idx:
            new_blobs.append(b'')
        assert idx >= orig_n or blobs[idx] in (b'', adds[idx][3]), (label, idx)
        new_blobs[idx] = adds[idx][3]
    todo = [i for i in adds if i >= orig_n or blobs[i] != adds[i][3]]
    for idx in sorted(adds):
        tag, new_id, tpl_id, gim, nmark = adds[idx]
        print('  %-14s %-6s id %5d (0x%04x) -> %s[%d] (template id %d, %d marker px)%s' % (
            label, tag, new_id, new_id, os.path.basename(target), idx, tpl_id, nmark,
            '' if idx in todo else ' already'))
    if not todo:
        return False
    new = Q.write_pack(raw, base, new_blobs)
    assert len(new) <= limit, '%s: pack %d > load buffer %d' % (label, len(new), limit)
    nb, chk = Q.read_pack(new)
    assert nb == base and all(chk[i] == blobs[i] for i in range(orig_n) if i not in adds), 'existing entry changed'
    print('  %s: %d -> %d entries, %d -> %d bytes (buffer %d)' % (os.path.basename(target), orig_n, len(new_blobs),
                                                                    len(raw), len(new), limit))
    if not dry:
        put_file(iso, target, new)
    return True


def put_file(iso, path, data):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'x.bin')
        open(p, 'wb').write(data)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                           check=True, capture_output=True, text=True)
        print('   ', r.stdout.strip())


def make_wm():
    """tools/art/sora_wm.png (64x32 Labyrinth face): the same KH2 menu-art cut-out as the other faces
    (make_title_art), profile eye-to-chin crop (Cloud's wm_ icon is a tight face too), on a dark backdrop like the game's wm_
    icons; the template's own alpha (cut corner) is applied by keep()/put via the template in main()."""
    import make_title_art as T
    import numpy as np
    sora = T.cutout(T.REF)
    face = sora.crop((30, 60, 158, 124)).resize((64, 32), Image.LANCZOS)   # eye x85 y85, nose x70 y107, chin y123
    face = T.deepen(face)
    bg = Image.new('RGBA', (64, 32), (38, 36, 52, 255))
    g = np.asarray(bg).astype(float)
    yy, xx = np.mgrid[:32, :64]
    g[..., :3] *= (0.75 + 0.35 * (xx / 63.0))[..., None]            # darker towards the left like Cloud's
    bg = Image.fromarray(g.astype(np.uint8))
    bg.alpha_composite(face)
    T.quant256(bg).save(WM_PNG)
    print('wrote', WM_PNG)


def wm_gim(iso):
    by_id, raw = read_scene(iso, [DUNGEON_PACK, 'menu/EN/menu_lpk_dungeon_gim_0.bin'])
    tpl = by_id[WM_TEMPLATE_ID][2]
    t = gimlib.decode(tpl).convert('RGBA')
    img = Image.open(WM_PNG).convert('RGBA')
    assert img.size == t.size == (64, 32)
    a = img.copy()
    a.putalpha(t.getchannel('A'))                                    # the game's cut-corner shape
    img, nmark = keep(tpl, a)
    return put(tpl, img), nmark, raw[DUNGEON_PACK]


def common_face(iso, src):
    use_iso(iso)
    with open(iso, 'rb') as f:
        st, sz = pkg_offset(COMMON_FACE)
        cur = read_at(f, st, sz)
        cst, csz = pkg_offset(COMMON_FACE_CLOUD)
        cloud = read_at(f, cst, csz)
    img, nmark = keep(cloud, picture('face', src))
    new = put(cur, img)
    assert len(new) == len(cur)
    assert cur == new or hashlib.sha256(cur).hexdigest() == COMMON_FACE_AERITH_SHA, \
        '%s is neither the vanilla file nor ours' % COMMON_FACE
    return cur, new, nmark


# 5. Aerith leftovers: packs that index pictures by owner - 1 keep Aerith's vanilla GIM in slot 32 (owner 33).
# Replaced in place by Sora's Customization pictures (customize pack entries 74 face strip / 107 icon, made by
# spot33_qbpics from qb_custface / qb_icon), re-encoded into each pack's own Cloud template (keep() markers).
CUSTOMIZE_PACK = 'menu/menu_pk_customize_gim_0.bin'
AERITH = [  # (pack, entry, Cloud template entry, customize source entry, vanilla Aerith sha256)
    ('menu/menu_pk_shop_gim_0.bin', 68, 48, 74, 'a5d83c5582480e5c8e7e153822dbc3a1187ad70884deff392bb7984f9ebc7995'),
    ('menu/menu_pk_shop_gim_0.bin', 101, 81, 107, '69d6a22abef201f61c01d39ecdb1bfd52813431f97cd2727be84647b242b5ec8'),
    ('menu/menu_pk_level_adjust_gim_0.bin', 73, 53, 74,
     'a5d83c5582480e5c8e7e153822dbc3a1187ad70884deff392bb7984f9ebc7995'),
]


def aerith_fix(iso, dry, rdir):
    use_iso(iso)
    with open(iso, 'rb') as f:
        st, sz = pkg_offset(CUSTOMIZE_PACK)
        cust = Q.read_pack(read_at(f, st, sz))[1]
    for pack in sorted({a[0] for a in AERITH}):
        with open(iso, 'rb') as f:
            st, sz = pkg_offset(pack)
            raw = read_at(f, st, sz)
        base, blobs = Q.read_pack(raw)
        new_blobs = list(blobs)
        for pk_, idx, tpl_idx, src_idx, sha in [a for a in AERITH if a[0] == pack]:
            cur, tpl = blobs[idx], blobs[tpl_idx]
            assert b'sev120' in cur and b'sev100' in tpl, (pack, idx)
            img, nmark = keep(tpl, gimlib.decode(cust[src_idx]).convert('RGBA'))
            assert img.size == gim_size(cur)
            gim = put(cur, img)
            assert cur == gim or hashlib.sha256(cur).hexdigest() == sha, '%s[%d] is neither Aerith nor ours' % (pack, idx)
            new_blobs[idx] = gim
            render(gim, os.path.join(rdir, 'aerith_fix_%s_%d.png' % (os.path.basename(pack)[8:-10], idx)))
            print('  %s[%d] (id %d): Aerith -> Sora (customize entry %d, %d marker px)%s' % (
                os.path.basename(pack), idx, base + idx, src_idx, nmark, ' already' if cur == gim else ''))
        if new_blobs == blobs:
            continue
        new = Q.write_pack(raw, base, new_blobs)
        assert len(new) == len(raw) and all(Q.read_pack(new)[1][i] == blobs[i] for i in range(len(blobs))
                                            if new_blobs[i] == blobs[i])
        if not dry:
            put_file(iso, pack, new)


def render(gim, path, scale=3):
    im = gimlib.decode(gim).convert('RGBA')
    bg = Image.new('RGBA', im.size, (40, 40, 60, 255))
    bg.alpha_composite(im)
    bg.resize((im.width * scale, im.height * scale), Image.NEAREST).save(path)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry' in sys.argv
    if '--make-wm' in sys.argv:
        make_wm()
        if not args:
            return
    iso = args[0]
    rdir = os.path.join(ROOT, 'dumps', 'renders', 'menuart')
    if '--renders' in sys.argv:
        rdir = sys.argv[sys.argv.index('--renders') + 1]
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the vanilla ISO'
    if not os.path.exists(WM_PNG):
        make_wm()
    plan, row = code_plan(iso)
    print('code: %d sites, %d to patch' % (len(plan), sum(s == 'old' for *_, s in plan)))
    # Sora's free-battle GIMs = pixel source
    fb, _ = read_scene(iso, Q.PACKS)
    src = {}
    for tag, i in FREE_IDS.items():
        assert i in fb, 'free-battle id %d missing: run spot33_qbpics first' % i
        src[tag] = fb[i][2]
    # plan everything before writing
    scenes = {n: scene_plan(iso, n, src) for n in SCENES}
    wm, wm_marks, dpk = wm_gim(iso)
    cur_face, new_face, face_marks = common_face(iso, src)
    os.makedirs(rdir, exist_ok=True)
    for n, (target, raw, base, blobs, adds, limit) in scenes.items():
        for idx, (tag, new_id, tpl_id, gim, nmark) in adds.items():
            render(gim, os.path.join(rdir, '%s_%s_%d.png' % (n, tag, new_id)))
    render(wm, os.path.join(rdir, 'labyrinth_wm_%d.png' % WM_ID), 4)
    render(new_face, os.path.join(rdir, 'common_p_sev120_face_in_name.png'))
    print('previews ->', rdir)
    # 1. code
    with open(iso, 'rb' if dry else 'r+b') as f:
        for va, old, new, state in plan:
            print('  %08x %2d words %s' % (va, len(new), 'already' if state == 'new' else 'patch'))
            if state == 'old' and not dry:
                f.seek(ovl_off(va))
                f.write(struct.pack('<%dI' % len(new), *new))
        # 2. Labyrinth table
        print('  Labyrinth owner-33 row 0x%08x: icon id %d -> %d%s' % (DUNGEON_ROW33, row[0], WM_ID,
                                                                     ' already' if row[0] == WM_ID else ''))
        if row[0] != WM_ID and not dry:
            f.seek(ovl_off(DUNGEON_ROW33))
            f.write(struct.pack('<H', WM_ID))
    # 3. packs
    base, blobs = Q.read_pack(dpk)
    apply_pack(iso, DUNGEON_PACK, dpk, base, blobs, {WM_ID - base: ('wm', WM_ID, WM_TEMPLATE_ID, wm, wm_marks)},
               0xC8000, dry, 'labyrinth')
    for n, (target, raw, base, blobs, adds, limit) in scenes.items():
        apply_pack(iso, target, raw, base, blobs, adds, limit, dry, n)
    # 4. common name-plate face strip (was Aerith's)
    if cur_face == new_face:
        print('  %s: already Sora' % COMMON_FACE)
    else:
        print('  %s <- Sora face (%d marker px)' % (COMMON_FACE, face_marks))
        if not dry:
            put_file(iso, COMMON_FACE, new_face)
    # 5. Aerith leftovers at owner-33 slots (shop, level adjust)
    aerith_fix(iso, dry, rdir)
    print('dry run, nothing written' if dry else 'done')


if __name__ == '__main__':
    main()
