"""Sora (owner 33) in Museum > Character Files (notes/menu-art.md "Museum").

The Character Files list is data, not code: package file `collection_param.bin` (loaded by the collection scene,
FUN_08a3be70): u16 version 2, u16 9 sections, 9 x u16 counts, 9 x u16 byte sizes, then the sections back to back,
then 9 x 64-byte path/name strings. Section 0 = 34 character records of 48 bytes:
  +0 list-name text id, +2 name, +4 subtitle, +6 profile (text/EN/mess_pk_collection_0.bin group 1, entry k+1),
  +8 unlock flag bit (DAT_089d726c; 0xFFFF = always), +10 "viewed" flag bit (3651..3685; 3681 is the free one),
  +12..+18 objentry ids of the 1P/2P/3P/manikin models for "View Character" (-1 = none), +20/+22 DLC costume ids,
  +24..+28 viewer camera numbers (height-ish; Tidus 370/210/72), +30 -1, +32 char[16] picture name -> list
  picture menu/JP/character_select/chara2/<name>.gim (p_sev120_1p, re-encoded here from the approved select portrait
  tools/art/approved/qb_art.png; arcade mode reads the same file).
Owner 33 had no record (the list is every record whose unlock flag is set), so he never appeared.

This script appends record 34 for Sora (always unlocked, viewed flag 3681, models P_SEV120_1P/2P/3P objentry
1187/1436/1437) and four group-1 text entries (list name, name, blank subtitle, profile). Every other record /
text entry stays byte-identical; re-running changes nothing. VIEWER=0 env = no model viewer for Sora.

Also (2026-10-16 evening, Mat: "his icon is not available there"):
- Player Icon No. 414 "Sora" (KINGDOM HEARTS II): new menu/JP/Collection/user_icon/user_icon414.gim (64x64, the
  approved VS face from menu/JP/story_mode/chara2/p_sev120_1p.gim on white, 52x52 at (1,1) like the character
  icons), the same picture appended to the friend-card archive general_archive/menu/user_icon12.bin (icons
  385..416, looked up by member name), a 414th row in collection_param section 4 (series text id 212, format 128),
  group-0 text 212 "KINGDOM HEARTS II" + group-4 text 413 "Sora", and a 414th row in system.bin "uicn"
  (index 413, icon 414, unlock flag 1 = owned from the start like icons 1-6, viewed flag 2993 (2580+413, unused)).
  The EBOOT copies uicn into a 0xD24-byte buffer: 4 + 414*8 = 3316 fits.
- Records: the list is the u8 owner table 0x08A40880 (26) + six hard-coded `jal 0x08a3d790` appends; the record
  array (obj+0x4B8, 0x10C each) holds exactly 32 and is followed by the sort list at +0x2638, so there is no room
  for a 33rd. Chaos (owner 23) is not playable in this mod (his Quick Battle row is Sora's), so his append
  `ori a1,zero,0x17` at 0x08A3D8F4 becomes 0x21 (same size). Records icon id table 0x08A40720[owner]: owner 33's
  word 0x08A407A4 (alignment padding, 0) -> 0x4060 = Sora's 64x64 face appended to menu_pk_collection_gim_0.

  python3 -I spot33_museum.py ISO [--dry]
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from voice_text import KEY  # noqa: E402
import gim as gimlib  # noqa: E402
from gim_put import put  # noqa: E402
from mpk import entries as mpk_entries  # noqa: E402
from roster_patch import MENU_FILEOFF, MENU_ISO_SECTOR, MENU_VADDR  # noqa: E402
from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, mpk_member, package_entry  # noqa: E402
from pkg_put import PACKAGE_INFO_ISO_SECTOR  # noqa: E402
from spot33_save import arc_join, arc_split  # noqa: E402
import spot33_qbpics as Q  # noqa: E402
from PIL import Image  # noqa: E402

PARAM = 'collection_param.bin'
TEXT = 'text/EN/mess_pk_collection_0.bin'
TEXT_GROUP, TEXT_COUNT = 1, 137                      # vanilla group-1 entry count (ids 0..136)
REC_SIZE, REC_COUNT = 48, 34
ESC = '\x10䄁！'                              # colour escape used before "▼ ..." headers (Cloud's text)
NAME = 'Sora'
PROFILE = ('A cheerful boy chosen by the\nKeyblade. He travels between\nworlds with Donald and Goofy\n'
           'to find his friends Riku and\nKairi.\n\n'
           + ESC + '▼ KINGDOM HEARTS II\x1b\n'
           'A year after the events in\nCastle Oblivion, Sora awakens\nfrom a long sleep. Reunited\n'
           'with Donald and Goofy, he sets\nout again to find Riku and\nKairi and to stand against the\n'
           'Heartless, the Nobodies and\nthe mysterious Organization\nXIII.\n\n'
           'His bright, simple heart wins\nfriends in every world he\nvisits, and those bonds become\n'
           'his greatest power.')
VIEWED_FLAG = 3681
MODELS = (1187, 1436, 1437, -1)                       # objentry P_SEV120_1P / _2P / _3P (no manikin)
CAMERA = (370, 210, 72)                               # Tidus's numbers (similar build)
PICTURE = b'p_sev120_1p'


def decode(g):
    """mess pak group (spot33_desc layout) -> list of raw entries; offset 0 = no string (None)"""
    n, = struct.unpack_from('<H', g, 0)
    offs = struct.unpack_from('<%dH' % (n + 1), g, 0)
    out = []
    for lid in range(1, n + 1):
        if offs[lid] == 0:
            out.append(None)
            continue
        p = offs[lid] * 2
        ln, = struct.unpack_from('<H', g, p)
        out.append(bytes(c ^ KEY[(2 * lid + 18 + j) % 32] for j, c in enumerate(g[p + 2:p + 2 + ln])))
    return out


def encode(raws):
    n = len(raws)
    out = bytearray(2 * (n + 1))
    struct.pack_into('<H', out, 0, n)
    for lid, raw in enumerate(raws, 1):
        if raw is None:
            continue
        out += b'\0' * (len(out) % 2)
        struct.pack_into('<H', out, 2 * lid, len(out) // 2)
        out += struct.pack('<H', len(raw)) + bytes(c ^ KEY[(2 * lid + 18 + j) % 32] for j, c in enumerate(raw))
    out += b'\0' * (len(out) % 2)
    return bytes(out)


def get(iso, path):
    use_iso(iso)
    st, sz = pkg_offset(path)
    with open(iso, 'rb') as f:
        return read_at(f, st, sz)


def put_file(iso, path, data):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'x.bin')
        open(p, 'wb').write(data)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                           check=True, capture_output=True, text=True)
        print('   ', r.stdout.strip())


def text_ids():
    return tuple(range(TEXT_COUNT, TEXT_COUNT + 4))   # list name, name, subtitle, profile


def record():
    models = MODELS if os.environ.get('VIEWER', '1') != '0' else (-1, -1, -1, -1)
    ids = text_ids()
    r = struct.pack('<4H2H4h2h3hh', ids[0], ids[1], ids[2], ids[3], 0xFFFF, VIEWED_FLAG, *models, -1, -1,
                    *CAMERA, -1)
    return r + PICTURE.ljust(16, b'\0')


def patch_param(d):
    h = list(struct.unpack_from('<20H', d, 0))
    assert h[0] == 2 and h[1] == 9, h[:2]
    n, size = h[2], h[11]
    end0 = 40 + size
    rec = record()
    if n == REC_COUNT + 1:
        assert d[end0 - REC_SIZE:end0] == rec, 'record 34 exists but differs (re-run with the same settings?)'
        return d, False
    assert n == REC_COUNT and size == REC_COUNT * REC_SIZE, (n, size)
    names = [d[40 + i * REC_SIZE + 32:40 + i * REC_SIZE + 48].split(b'\0')[0] for i in range(n)]
    assert PICTURE not in names and b'p_org800_1p' == names[-1], names[-3:]
    flags = {struct.unpack_from('<H', d, 40 + i * REC_SIZE + 10)[0] for i in range(n)}
    assert VIEWED_FLAG not in flags
    h[2], h[11] = n + 1, size + REC_SIZE
    out = struct.pack('<20H', *h) + d[40:end0] + rec + d[end0:]
    return out, True


def text_adds():
    """group -> (vanilla entry count, new raw entries appended at that index)"""
    enc = lambda t: (t + '\0').encode('utf-16-le')  # noqa: E731
    return {1: (TEXT_COUNT, [enc(t) for t in (NAME, NAME, '　', PROFILE)]),
            0: (ICON_SERIES_TEXT, [enc('KINGDOM HEARTS II')]),
            4: (ICON_INDEX, [enc(i[5]) for i in ICONS])}


def patch_text(d):
    assert d[:8] == b'mess pak', d[:8]
    ng, = struct.unpack_from('<H', d, 10)
    groups = [struct.unpack_from('<II', d, 0x10 + 8 * i) for i in range(ng)]
    bodies = [d[go:go + gs] for go, gs in groups]
    changed = []
    for gi, (n0, new) in sorted(text_adds().items()):
        g = bodies[gi]
        raws = decode(g)
        e = encode(raws)
        assert e == g[:len(e)] and not g[len(e):].strip(b'\0'), 'group %d does not re-encode exactly' % gi
        if len(raws) == n0 + len(new):
            assert raws[n0:] == new, 'group %d entries %d.. exist but differ' % (gi, n0)
            continue
        assert n0 <= len(raws) < n0 + len(new) and raws[n0:] == new[:len(raws) - n0], (gi, len(raws), n0)
        raws = raws[:n0]
        bodies[gi] = encode(raws + new)
        changed.append(gi)
    if not changed:
        return d, []
    out = bytearray(d[:groups[0][0]])
    for i, b in enumerate(bodies):
        out += b'\0' * ((-len(out)) % 16)
        struct.pack_into('<II', out, 0x10 + 8 * i, len(out), len(b))
        out += b
    out += b'\0' * ((-len(out)) % 16)
    for i, (go, gs) in enumerate(groups):
        no, ns = struct.unpack_from('<II', out, 0x10 + 8 * i)
        if i in changed:
            n0, new = text_adds()[i]
            chk = decode(bytes(out[no:no + ns]))
            assert chk[:n0] == decode(d[go:go + gs])[:n0] and chk[n0:] == new, 'group %d check' % i
        else:
            assert out[no:no + ns] == d[go:go + gs], 'group %d changed' % i
    return bytes(out), changed


# ---- Player Icons 414..417 (KINGDOM HEARTS II) ----
# 2026-10-17 (Mat: "Kingdom Hearts icons ... unlocking Sora, Riku and Kairi" + "a Sora avatar"): icons are owned when
# their uicn unlock flag is set; the PP Catalog item of a set sets that flag (update_list_param, spot33_catalog.py).
# 414 Sora (approved VS face, was "owned from start" = flag 1 in test302..325 -> now part of the KH set), 415 Riku,
# 416 Kairi (KH2 Jiminy's Journal faces jmface_ex8 / jmface_ex4), all on white like the character icons; 417 = Sora
# avatar (gold card like the "[Avatar]" icons 394..411, smiling journal face jmface_ex1). ICONS_FREE=1 env = old
# behaviour (all owned from the start, flag 1).
ICON_INDEX = 413                                     # first new 0-based index (icon 414)
ICON_SERIES_TEXT = 212                               # new collection group-0 text "KINGDOM HEARTS II"
KH_ICON_FLAG, AVATAR_ICON_FLAG = 1266, 1267          # never set by vanilla (spot33_unlockflags.py, notes/unlocks.md §7)
OLD_ICON_FLAGS = {1266: 1253, 1267: 1254}            # test327..test348; vanilla sets 1253/1254 (Lv100 owners 8/10)
KH2_MENU = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'kh2_export', 'raw', 'kh2_fifth', 'remastered',
                        'menu')
FREE = os.environ.get('ICONS_FREE') == '1'
# (index, icon no., uicn unlock flag, viewed flag, collection section-4 row, name, picture kind, source)
ICONS = [(413, 414, 1 if FREE else KH_ICON_FLAG, 2993, (ICON_SERIES_TEXT, 0, 128, -1), 'Sora', 'card', 'vs'),
         (414, 415, 1 if FREE else KH_ICON_FLAG, 2994, (ICON_SERIES_TEXT, 0, 128, -1), 'Riku', 'card', 'jmface_ex8'),
         (415, 416, 1 if FREE else KH_ICON_FLAG, 2995, (ICON_SERIES_TEXT, 0, 128, -1), 'Kairi', 'card', 'jmface_ex4'),
         (416, 417, 1 if FREE else AVATAR_ICON_FLAG, 2996, (-1, 0, 130, -1), 'Sora', 'avatar', 'jmface_ex1')]
OLD_UICN_414 = struct.pack('<HHHH', 413, 414, 1, 2993)   # test302..test325 (owned from the start)


def old_uicn_row(ic):
    return struct.pack('<HHHH', ic[0], ic[1], OLD_ICON_FLAGS.get(ic[2], ic[2]), ic[3])
ICON_FILE = 'menu/JP/Collection/user_icon/user_icon%03d.gim'
ICON_TEMPLATE = 413                                  # user_icon413.gim: 64x64 index8, same size (5408)
AVATAR_BG = (159, 130, 65, 255)                      # gold of the avatar icons
VS_FACE = 'menu/JP/story_mode/chara2/p_sev120_1p.gim'   # Sora's approved 64x64 VS face
UICN_MAX = (0xD24 - 4) // 8                          # EBOOT buffer FUN_088cc1d0 (420 rows)
VAN_ICONS = 413
# ---- Records ----
REC_LI_VA, REC_LI_OLD, REC_LI_NEW = 0x08A3D8F4, 0x34050017, 0x34050021   # ori a1,zero,23 -> 33
REC_ICON_VA, REC_ICON_ID = 0x08A40720 + 33 * 4, 0x4060
COLL_PACK, COLL_TEMPLATE = 'menu/menu_pk_collection_gim_0.bin', 0x4011 + 12     # Cloud's 64x64 face


def uicn_row(ic):
    return struct.pack('<HHHH', ic[0], ic[1], ic[2], ic[3])


def icon_archive(no):
    return 'general_archive/menu/user_icon%02d.bin' % ((no - 1) // 32)


def ovl_off(va):
    return MENU_ISO_SECTOR * SECTOR + va - MENU_VADDR + MENU_FILEOFF


def sora_face(iso):
    return gimlib.decode(get(iso, VS_FACE)).convert('RGBA')


def journal_face(name):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'f.png')
        subprocess.run(['convert', os.path.join(KH2_MENU, name + '.imd', '-0.dds'), p], check=True)
        im = Image.open(p).convert('RGBA')
    return im.crop((24, 8, 232, 216))                 # 256x256 journal face -> head close-up (square)


def icon_gim(iso, ic):
    tpl = get(iso, ICON_FILE % ICON_TEMPLATE)
    face = sora_face(iso) if ic[7] == 'vs' else journal_face(ic[7])
    face = face.resize((52, 52), Image.LANCZOS)
    card = Image.new('RGBA', (52, 52), AVATAR_BG if ic[6] == 'avatar' else (255, 255, 255, 255))
    card.alpha_composite(face)
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    img.paste(card, (1, 1))
    img = img.quantize(255, method=2).convert('RGBA')
    return put(tpl, img), img


def patch_param_icons(d):
    """collection_param section 4 (player icons, 8-byte rows): rows 414..417 after the vanilla 413"""
    h = list(struct.unpack_from('<20H', d, 0))
    offs = [40]
    for sz in h[11:19]:
        offs.append(offs[-1] + sz)
    n, size, o4 = h[6], h[15], offs[4]
    rows = [struct.pack('<hhhh', *ic[4]) for ic in ICONS]
    have = [d[o4 + 8 * i:o4 + 8 * i + 8] for i in range(VAN_ICONS, n)]
    assert size == 8 * n and VAN_ICONS <= n <= VAN_ICONS + len(rows) and have == rows[:len(have)], (n, size)
    if len(have) == len(rows):
        return d, False
    h[6], h[15] = VAN_ICONS + len(rows), 8 * (VAN_ICONS + len(rows))
    end = o4 + size
    return struct.pack('<20H', *h) + d[40:o4 + 8 * VAN_ICONS] + b''.join(rows) + d[end:], True


def mpk_add(d, name, data):
    """MPK with one more member at the end (names and data of the others unchanged, 16-aligned like the original)"""
    ents = list(mpk_entries(d))
    names = [n for n, _, _ in ents]
    if name in names:
        n_, o, sz = ents[names.index(name)]
        assert d[o:o + sz] == data, '%s already in the archive but differs' % name
        return d, False
    items = [(n, d[o:o + sz]) for n, o, sz in ents] + [(name, data)]
    head = bytearray(d[:16])
    struct.pack_into('<I', head, 8, len(items))
    table = bytearray(16 * len(items))
    namebuf = bytearray()
    base = 16 + len(table)
    noffs = []
    for n, _ in items:
        noffs.append(base + len(namebuf))
        namebuf += n.encode() + b'\0'
    out = head + table + namebuf
    for i, (n, blob) in enumerate(items):
        out += b'\0' * ((-len(out)) % 16)
        struct.pack_into('<IIII', out, 16 + 16 * i, noffs[i], len(out), len(blob), 0)
        out += blob
    out += b'\0' * ((-len(out)) % 16)
    chk = {n: out[o:o + sz] for n, o, sz in mpk_entries(bytes(out))}
    assert all(chk[n] == blob for n, blob in items)
    return bytes(out), True


def patch_uicn(iso, dry):
    with open(iso, 'rb') as f:
        info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
        pkg = PACKAGE_ISO_SECTOR * SECTOR
        off, size = package_entry(info, 'general_archive/main/main.bin')
        main_bin = read_at(f, pkg + off, size)
        sys_off, sys_size = mpk_member(f, pkg + off, 'system.bin')
        sys_off -= pkg + off
    head, chunks = arc_split(main_bin[sys_off:sys_off + sys_size])
    c = next(c for c in chunks if c[1] == b'uicn')
    u = c[2]
    one, n = struct.unpack_from('<HH', u, 0)
    assert one == 1 and len(u) == 4 + 8 * n and VAN_ICONS <= n <= VAN_ICONS + len(ICONS), (one, n, len(u))
    want = [uicn_row(ic) for ic in ICONS]
    have = [u[4 + 8 * i:4 + 8 * i + 8] for i in range(VAN_ICONS, n)]
    for k, hv in enumerate(have):     # ours, test327..348 flag numbers, or test302's "owned from start" row 414
        assert hv in (want[k], old_uicn_row(ICONS[k])) or (k == 0 and hv == OLD_UICN_414), 'uicn row %d is not ours: %s' % (
            VAN_ICONS + k, struct.unpack('<4H', hv))
    if have == want:
        print('  system.bin uicn: already %d rows (flags %s)' % (n, [ic[2] for ic in ICONS]))
        return
    assert VAN_ICONS + len(want) <= UICN_MAX
    vflags = {struct.unpack_from('<H', u, 4 + 8 * i + 6)[0] for i in range(VAN_ICONS)}
    assert not vflags & {ic[3] for ic in ICONS}
    uflags = {struct.unpack_from('<H', u, 4 + 8 * i + 4)[0] for i in range(VAN_ICONS)}
    assert not uflags & {KH_ICON_FLAG, AVATAR_ICON_FLAG}, 'a vanilla icon uses our unlock flag'
    c[2] = struct.pack('<HH', one, VAN_ICONS + len(want)) + u[4:4 + 8 * VAN_ICONS] + b''.join(want)
    sysbin = arc_join(head, chunks)
    delta = -(-(len(sysbin) - sys_size) // 16) * 16
    count, = struct.unpack_from('<I', main_bin, 8)
    out = bytearray(main_bin[:sys_off]) + sysbin + b'\0' * (delta - (len(sysbin) - sys_size))
    out += main_bin[sys_off + sys_size:]
    for i in range(count):
        noff, doff, msize, z = struct.unpack_from('<IIII', out, 16 + i * 16)
        if doff == sys_off:
            struct.pack_into('<I', out, 16 + i * 16 + 8, len(sysbin))
        elif doff > sys_off:
            struct.pack_into('<I', out, 16 + i * 16 + 4, doff + delta)
    # every other system.bin chunk and main.bin member byte-identical
    h2, ch2 = arc_split(sysbin)
    assert all(a[2] == b[2] for a, b in zip(chunks, ch2)) and h2 == head
    old = {n_: main_bin[o:o + sz] for n_, o, sz in mpk_entries(main_bin)}
    new = {n_: bytes(out[o:o + sz]) for n_, o, sz in mpk_entries(bytes(out))}
    assert all(new[k] == v for k, v in old.items() if k != 'system.bin')
    print('  system.bin uicn: %d -> %d rows (rows %s); system.bin %d -> %d, main.bin %d -> %d bytes' % (
        n, VAN_ICONS + len(want), [struct.unpack('<4H', w) for w in want], sys_size, len(sysbin), len(main_bin),
        len(out)))
    if not dry:
        put_file(iso, 'general_archive/main/main.bin', bytes(out))


def patch_records(iso, dry):
    with open(iso, 'rb') as f:
        f.seek(ovl_off(REC_LI_VA))
        li, = struct.unpack('<I', f.read(4))
        f.seek(ovl_off(REC_ICON_VA))
        ic, = struct.unpack('<I', f.read(4))
    assert li in (REC_LI_OLD, REC_LI_NEW), hex(li)
    assert ic in (0, REC_ICON_ID), hex(ic)
    print('  Records: last append owner %d -> 33%s; icon id table[33] %d -> %d%s' % (
        li & 0xffff, ' already' if li == REC_LI_NEW else '', ic, REC_ICON_ID, ' already' if ic else ''))
    if not dry:
        with open(iso, 'r+b') as f:
            f.seek(ovl_off(REC_LI_VA))
            f.write(struct.pack('<I', REC_LI_NEW))
            f.seek(ovl_off(REC_ICON_VA))
            f.write(struct.pack('<I', REC_ICON_ID))
    # 64x64 face in the collection pack at id 0x4060
    use_iso(iso)
    st, sz = pkg_offset(COLL_PACK)
    with open(iso, 'rb') as f:
        raw = read_at(f, st, sz)
    base, blobs = Q.read_pack(raw)
    gim = put(blobs[COLL_TEMPLATE - base], sora_face(iso))
    idx = REC_ICON_ID - base
    if idx < len(blobs):
        assert blobs[idx] == gim, 'collection entry %d exists but differs' % idx
        print('  %s[%d] (id 0x%04x): already Sora' % (COLL_PACK, idx, REC_ICON_ID))
        return gim
    assert idx == len(blobs), (idx, len(blobs))
    new = Q.write_pack(raw, base, blobs + [gim])
    nb, chk = Q.read_pack(new)
    assert chk[:len(blobs)] == blobs and len(new) <= 0x180000
    print('  %s: + entry %d (id 0x%04x, Sora 64x64 face), %d -> %d bytes' % (COLL_PACK, idx, REC_ICON_ID,
                                                                          len(raw), len(new)))
    if not dry:
        put_file(iso, COLL_PACK, new)
    return gim


# ---- Character Files list picture = the approved select portrait (Mat on test301: "use the image in the
# character select screen") ----
PORTRAIT_FILE = 'menu/JP/character_select/chara2/p_sev120_1p.gim'   # also read by arcade mode (FUN_089ea4d0)
PORTRAIT_CLOUD = 'menu/JP/character_select/chara2/p_sev100_1p.gim'
APPROVED = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'tools', 'art', 'approved', 'qb_art.png')
APPROVED_SHA = '4df846c07b44fd74ab8bc9a66008ec8920f7f226f564fd326596f6cca1fb7e6c'


def patch_portrait(iso, dry):
    import hashlib
    from gim_markers import keep
    assert hashlib.sha256(open(APPROVED, 'rb').read()).hexdigest() == APPROVED_SHA, 'approved portrait changed'
    cur = get(iso, PORTRAIT_FILE)
    cloud = get(iso, PORTRAIT_CLOUD)
    assert len(cur) == len(cloud) == 66848 and struct.unpack_from('<HH', cur, 0x48) == (256, 256)
    img, nmark = keep(cloud, Image.open(APPROVED).convert('RGBA'))
    new = put(cur, img)
    print('  %s <- approved portrait (%d marker px)%s' % (PORTRAIT_FILE, nmark, ' already' if new == cur else ''))
    if new != cur and not dry:
        put_file(iso, PORTRAIT_FILE, new)
    return new


def main():
    iso = [a for a in sys.argv[1:] if not a.startswith('--')][0]
    dry = '--dry' in sys.argv
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the vanilla ISO'
    for p in ('menu/JP/character_select/chara2/p_sev120_1p.gim',):
        assert len(get(iso, p)) == 66848, 'list picture %s missing (spot33_faces)' % p
    rdir = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'dumps', 'renders', 'menuart')
    os.makedirs(rdir, exist_ok=True)
    pg = patch_portrait(iso, dry)
    gimlib.decode(pg).convert('RGBA').save(os.path.join(rdir, 'museum_portrait_p_sev120_1p.png'))
    d = get(iso, PARAM)
    nd, ch = patch_param(d)
    nd, chi = patch_param_icons(nd)
    print('%s: record 34 (Sora) %s, player-icon rows 414..417 %s; %d -> %d bytes' % (
        PARAM, 'added' if ch else 'already', 'added' if chi else 'already', len(d), len(nd)))
    if (ch or chi) and not dry:
        put_file(iso, PARAM, nd)
    t = get(iso, TEXT)
    nt, groups = patch_text(t)
    print('%s: groups changed %s (1: 137..140 Sora file, 0: 212 series, 4: 413..416 icon names); %d -> %d bytes' % (
        TEXT, groups or 'none (already)', len(t), len(nt)))
    if groups and not dry:
        put_file(iso, TEXT, nt)
    # player icon files + friend-card archives (32 icons per archive, member user_iconNNN.gim; the game loads
    # ceil(icon count / 32) archives -> 417 icons = archives 0..13, archive 13 is new)
    arcs = {}
    for ic in ICONS:
        gim, img = icon_gim(iso, ic)
        img.resize((256, 256), Image.NEAREST).save(os.path.join(rdir, 'user_icon%03d.png' % ic[1]))
        path = ICON_FILE % ic[1]
        try:
            cur = get(iso, path)
        except SystemExit:
            cur = None
        assert cur in (None, gim), '%s exists but differs' % path
        print('  %s (%s): %s' % (path, ic[5], 'already' if cur == gim else 'new (%d bytes)' % len(gim)))
        if cur is None and not dry:
            put_file(iso, path, gim)
        an = icon_archive(ic[1])
        if an not in arcs:
            try:
                arcs[an] = [get(iso, an), None]
            except SystemExit:                        # new archive (icons 417..448)
                arcs[an] = [b'MPK \x06\x06\x07\x20' + bytes(8), 'new']
            arcs[an][1] = arcs[an][1] or arcs[an][0]
        arcs[an][0], _ = mpk_add(arcs[an][0], 'user_icon%03d.gim' % ic[1], gim)
    for an, (data, orig) in arcs.items():
        if data == orig:
            print('  %s: already' % an)
            continue
        print('  %s: %s (%d bytes)' % (an, 'NEW archive' if orig == 'new' else 'members added', len(data)))
        if not dry:
            put_file(iso, an, data)
    patch_uicn(iso, dry)
    rec_gim = patch_records(iso, dry)
    gimlib.decode(rec_gim).convert('RGBA').resize((256, 256), Image.NEAREST).save(
        os.path.join(rdir, 'records_icon_0x4060.png'))
    print('dry run, nothing written' if dry else 'done')


if __name__ == '__main__':
    main()
