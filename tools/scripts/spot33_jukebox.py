"""Sora's voices in Museum > Jukebox + "Encounter Voice - Sora" in the PP Catalog (2026-10-18, RR-10, Mat: "Add Sora
voice to jukebox as well, make this as legitimate feeling as possible"). notes/unlocks.md §6.

How the native Jukebox voices work (static, menu overlay OVL_MENU_APP + EBOOT):
- Character list = collection_param.bin section 8 (4-B entries: u16 unlock flag, u8 owner, u8 0xFF; 33 entries =
  owners 31,30,27,28,24,26,1..22,29,25,23,32 + 255 "system"). FUN_08a36ee8 lists the entries whose flag is set into
  obj+0x710 (cap 0x21, memset 0x42); the voice rows of the chosen fighter go to obj+0x752 (FUN_08a37024, cap 0x200,
  memset 0x400); obj+0xb52 = file-name buffer. A 34th fighter needs 10 code words (below).
- Voice rows = collection_voice_param.bin: u16 1, u16 group count, groups (u16 owner, u16 rows, u16 bytes, -1), then
  44-B rows: s16 category (text = collection text group 6: 2 "Encounter %s", 3 "Victory (%s)", 4 "Loss (%s)",
  5 "Battle (%s)", 11..42 "vs <fighter>", 44 "Loss - Battle", 45 "Assist", ...), s16 unlock flag (-1 = always),
  s16 index (the %s; 0 = none), s16 bank slot, s16 kind (0 = battle .at3, 1 = .scd bank slot, 2 = event .at3),
  s16 -1, char[32] file. Group lookup by owner byte (FUN_08a3c360).
- Label shown = "<name>：<category>" (text 55; name by FUN_088d6254(owner) = collection group 3, owner 33 -> 63
  "Sora" since spot33_ownername). The Jukebox shows no line text (no subtitle) for any fighter.
- Kind-0 rows play only if the clip is found in the owner's MUSEUM copy of its VOLD list: voice_load_parameter.mpk
  member voice_load_p_<key>.bin (EBOOT FUN_088a3a94, key table 0x089D6CA8[owner], [33] = "sev120"); volume = the
  row's moment low byte (0x46 = 70 %). Vanilla: every member is byte-identical to the loose voice_load_<KEY>.bin.
- Native pattern (checked for all 30 regular fighters vs their VOLD lists): Encounter N = the moment-0x46 rows with
  cond 0/5/7/8 (unique clips, list order), "vs X" = the cond-2 row for opponent X (category 10 + display order),
  Victory N = all moment-0x146 rows, Loss N = all moment-0x246 rows (unique clips), Battle N = chosen voice-bank
  slots, Loss - Battle = the KO slot, Assist = an assist-bank slot. Encounter + vs rows need the fighter's
  "Encounter Voice" flag (856..887 = the PP Catalog item), "vs Feral Chaos" rows need Feral Chaos's flag 886;
  Victory/Loss/Battle are always listed (-1).
- PP Catalog tab 0 items 77..108 = "Encounter Voice - <name>" (180 PP, Feral Chaos 10 PP), text 30 + help 4
  ("Unlocks encounter voice data for %s. Playable in the Jukebox."), villains: listed after their unlock flag with
  a "new" flag 2061..2092.

What this script writes (every site vanilla or already ours; re-runnable; --dry writes nothing):
1. update_list_param.bin tab 0: + "Encounter Voice - Sora" (180 PP, sets flag 888 = next free after 856..887) right
   after "Encounter Voice - Feral Chaos" (Sora's own character item follows Feral Chaos's too). Listed after Sora's
   unlock flag 925 with "new" flag 2093 (next after Chaos's 2092), like the villains; UNLOCK=0 builds (unlock row
   flag -1) -> always listed, no new flag, like the heroes. Texts are the game's own (30/4 + name 63 "Sora").
2. collection_param.bin section 8: + (925|-1, owner 33) after Feral Chaos, before the system entry.
3. collection text group 6: + #78 "vs Sora" (category for the mirror line and the other fighters' lines vs Sora).
4. collection_voice_param.bin: + group 33 (after 32) from Sora's own loose VOLD list (Encounter, vs X by category +
   "vs Sora" mirror, Victory, Loss; same-audio copies of an already listed line skipped: so_battle_30/39/40 and the
   generic vs-Chaos fallback so_battle_71 -> no "vs Chaos" row until a real line is routed) and voice bank voice_p_sev120_00 (Battle N = the slots Cloud's
   native group lists (Sora's bank uses Cloud's slot layout), empty / identical-audio slots skipped; Loss - Battle =
   Cloud's KO slot 4). Flags: Encounter/vs 888, vs Feral Chaos 886, others -1. No Assist row (Sora's assist bank has
   no line in Cloud's assist slot 41). Every other fighter whose loose VOLD has a vs-Sora row (cond 2 value 33) gets
   a "vs Sora" row after its "vs Feral Chaos" row, flag = that fighter's own Encounter Voice flag.
5. voice_load_parameter.mpk: every member = its loose list again (the vs-Sora rows added by spot33_vsvoices), +
   voice_load_p_sev120.bin = Sora's loose list (museum slot 33 was empty).
6. OVL_MENU_APP 10 words: character list cap 0x21 -> 0x22 (+ memset 0x42 -> 0x44), voice-row list moved 0x752 ->
   0x754 (4 sites) with cap 0x200 -> 0x1FF and memset 0x400 -> 0x3FE (still ends at 0xB52; largest group 292 rows).

Flags 888 / 2093 are checked free on every run (catalog fields, unlock table, collection_param sections 0/6/8,
collection_voice_param, system.bin uicn, bgm_entry, and ori/addiu-from-zero immediates in EBOOT/menu/battle code).
Completion note: the Jukebox "complete" check FUN_08a3c9c8 walks every section-8 entry and row, so a 100 % Museum now
also needs "Encounter Voice - Sora" (like the KHII BGM items for music).

Run after spot33_vsvoices/spot33_lines (VOLD lists), spot33_ownername (name 63), spot33_catalog (Sora item, unlock
row), spot33_music; before spot33_installfix (no PACKAGE_INFO rows are added).

  python3 -I spot33_jukebox.py ISO [--dry]
"""
import hashlib
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from voice_lines import VoiceISO  # noqa: E402
from spot33_museum import decode, encode  # noqa: E402
from roster_patch import MENU_FILEOFF, MENU_ISO_SECTOR, MENU_VADDR  # noqa: E402
from spot33_save import arc_split  # noqa: E402
import mpk  # noqa: E402
import sscf  # noqa: E402

SORA = 33
SECTOR = 0x800
EV_FLAG = 888                 # "Encounter Voice - Sora" bought (856..887 = owners' items, 888 next, unused)
NEW_FLAG = 2093               # catalog "new" flag (villain EV items 2061..2092; 2093 unused)
FC_EV_FLAG = 886              # Feral Chaos's Encounter Voice flag (native: every "vs Feral Chaos" row)
SORA_UNLOCK = 925             # spot33_catalog (unlock row 22)
EV_PRICE = 180
EV_NAME, EV_HELP, NAME63 = 30, 4, 63
VS_SORA_CAT = 78              # new collection text group 6 entry
VS_SORA_TEXT = 'vs Sora'
G6_COUNT = 78
SORA_KEY = 'P_SEV120'
SORA_BANK = 'voice/EN/battle/voice_p_sev120_00.scd'
SORA_BANK_NAME = 'voice_p_sev120_00'
SORA_ABANK = 'voice/EN/battle/voice_p_sev120_a_00.scd'
CLOUD = 13                    # Sora's voice bank = Cloud's slot layout (notes/voice-and-sound.md §8)
EBOOT_ISO = 560 * SECTOR
UNLOCK_ROW_VA = 0x089D7BE0 + 22 * 20
CODE_FILES = {'EBOOT': (560, 4640948), 'OVL_BATTLE_APP': (185824, 1596824), 'OVL_MENU_APP': (185056, 1556096)}

PARAM = 'update_list_param.bin'
UTEXT = 'text/EN/mess_pk_update_list_0.bin'
CPARAM = 'collection_param.bin'
CTEXT = 'text/EN/mess_pk_collection_0.bin'
CVP = 'collection_voice_param.bin'
VMPK = 'voice/EN/voice_load_parameter.mpk'
MAIN = 'general_archive/main/main.bin'

# vanilla fingerprints (sha256[:16], clean dump df94177d...ab6e)
VAN_CVP_GROUPS = {
    1: 'bf2227bb3af81952', 2: 'e04ef5def4dbb480', 3: '65a1cabb6c699350', 4: '01d4001b8261c043', 5: '49b67c9936b44f60',
    6: '43c57adee82845ef', 7: 'ad3a39714022acda', 8: '7d934b9b114bada2', 9: 'd4cb5090762a459b', 10: 'a3d7df1087a5e188',
    11: '855b1f06e7caf2fb', 12: '940296f161cf7dbe', 13: '19615ac336160231', 14: '172609476cc624b2',
    15: '18b61bfde443579d', 16: 'd7a3a9d9960e2260', 17: '7e90e0e354200631', 18: '186553bc2f4b2436',
    19: '7acfa5cc51d2b7d4', 20: 'a76925d4bd45e8a8', 21: '5e4fa077a4a53739', 22: '60d5e091d640f93e',
    23: '3ff695cf3800c3d4', 24: 'e13ae23a35490ad9', 25: 'ffa08a08e7b00c40', 26: '37863a304cd021a5',
    27: '84f06fd2d85c71b3', 28: '8e98649514bff491', 29: 'fc198e855002820a', 30: 'c19ab37197201756',
    31: '55d772ddf14cc612', 32: '772246894f3d2b24', 255: '31a22fa2ba6e637f'}
VAN_MPK_MEMBERS = {
    'gst130': '58b7ae54a0a75037', 'gst120': 'a5655b8a9ec2a12d', 'eht110': 'a9bc98c7b536b807', 'ten110': 'fdec7fa4a750d22d',
    'for110': 'c83811b73b1f95b9', 'sev110': 'd2d210d5bbabc8a3', 'gst110': '720253a2a2168de6', 'fiv210': '799d94951a2a9006',
    'org210': 'de77e5b9d9169cf8', 'one100': '36e2fde25cdbbc33', 'one200': 'e04f0d98ec64b5cd', 'two100': 'bcc4356bfabc7e23',
    'two200': '032834156870446c', 'thr100': '4d3f89e229b0a248', 'thr200': '2da894973ab57b38', 'for100': '7f31fa4088925f2c',
    'for200': 'a13b98d2fe474e41', 'fiv100': '753be8c40f677bc6', 'fiv200': '1b0fcfb085fffa9e', 'six100': '67414c40e4edf427',
    'six200': 'b71263406c19d998', 'sev100': '63b91bcd8b9d08ed', 'sev200': '6c29952028ef3dea', 'eht100': 'd69f89c32134908e',
    'eht200': '039616180f39bc1a', 'nin100': '8c8aa54f271e2827', 'nin200': 'e0dd2bb23d34de18', 'ten100': '5677b20c030493f0',
    'ten200': 'bf9a16a8cd5b7a5f', 'gst100': '98d516d6e51eb0f6', 'gst200': 'd9a4c5330dfeefaa', 'org200': '98d5e9d5e4366b17'}
VAN_SEC8 = '1db73b7139b0b632'          # collection_param section 8 (33 entries)
# owner -> museum/battle VOLD key (EBOOT 0x089D6CA8)
KEYS = {1: 'one100', 2: 'one200', 3: 'two100', 4: 'two200', 5: 'thr100', 6: 'thr200', 7: 'for100', 8: 'for200',
        9: 'fiv100', 10: 'fiv200', 11: 'six100', 12: 'six200', 13: 'sev100', 14: 'sev200', 15: 'eht100',
        16: 'eht200', 17: 'nin100', 18: 'nin200', 19: 'ten100', 20: 'ten200', 21: 'gst100', 22: 'gst200',
        23: 'org200', 24: 'for110', 25: 'fiv210', 26: 'sev110', 27: 'eht110', 28: 'ten110', 29: 'gst110',
        30: 'gst120', 31: 'gst130', 32: 'org210', 33: 'sev120'}
# OVL_MENU_APP (va, vanilla word, ours)
MENU_SITES = [
    (0x08A36F20, 0x2A240022, 0x2A240023, 'FUN_08a36ee8 slti s1,0x22 -> 0x23 (character list cap test)'),
    (0x08A36F2C, 0x34110021, 0x34110022, 'FUN_08a36ee8 ori s1,0x21 -> 0x22 (character list cap)'),
    (0x08A36F40, 0x34060042, 0x34060044, 'FUN_08a36ee8 memset obj+0x710 0x42 -> 0x44'),
    (0x08A37078, 0x2AC40201, 0x2AC40200, 'FUN_08a37024 slti s6,0x201 -> 0x200 (row list cap test)'),
    (0x08A37084, 0x34160200, 0x341601FF, 'FUN_08a37024 ori s6,0x200 -> 0x1FF (row list cap)'),
    (0x08A37090, 0x24840752, 0x24840754, 'FUN_08a37024 addiu obj+0x752 -> 0x754 (memset base)'),
    (0x08A37098, 0x34060400, 0x340603FE, 'FUN_08a37024 memset 0x400 -> 0x3FE'),
    (0x08A37128, 0xA4900752, 0xA4900754, 'FUN_08a37024 sh row index obj+0x752 -> 0x754'),
    (0x08A37CA0, 0x94850752, 0x94850754, 'row label lhu obj+0x752 -> 0x754'),
    (0x08A38444, 0x94850752, 0x94850754, 'FUN_08a382bc play lhu obj+0x752 -> 0x754'),
]
# neighbours that must be the vanilla code around the sites (jal targets of the list functions)
MENU_CONTEXT = [(0x08A36F14, 0x0E28F028), (0x08A36F74, 0x0E28F0C4), (0x08A3706C, 0x0E28F0D8),
                (0x08A370D0, 0x0E28F0FA), (0x08A37CA4, 0x0E28F0FA), (0x08A38448, 0x0E28F0FA),
                (0x08A36F68, 0x34170001), (0x08A37068, 0x94840710), (0x08A38424, 0x94840710),
                (0x08A37C80, 0x94840710), (0x08A386AC, 0x24840B52)]


def sha(b):
    return hashlib.sha256(b).hexdigest()[:16]


def eboot_off(va):
    return EBOOT_ISO + 0x1018 + va - 0x8804040


def menu_off(va):
    return MENU_ISO_SECTOR * SECTOR + va - MENU_VADDR + MENU_FILEOFF


def put_file(iso, path, data):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'x.bin')
        open(p, 'wb').write(data)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                           check=True, capture_output=True, text=True)
        print('   ', r.stdout.strip())


def unlock_flag(iso):
    with open(iso, 'rb') as f:
        f.seek(EBOOT_ISO)
        assert f.read(4) == b'\x7fELF', 'EBOOT is not the plain ELF'
        f.seek(eboot_off(UNLOCK_ROW_VA))
        row = struct.unpack('<5i', f.read(20))
    assert row[0] == SORA and row[1] in (-1, SORA_UNLOCK), 'unlock row 22 = %s - run spot33_catalog first' % (row,)
    return row[1]


# ---------------------------------------------------------------- PP Catalog
def ev_items():
    """both variants of our catalog item: Sora bought from the catalog / Sora free from the start (UNLOCK=0)"""
    return {SORA_UNLOCK: (EV_PRICE, EV_NAME, EV_HELP, -1, SORA_UNLOCK, SORA_UNLOCK, EV_FLAG, NEW_FLAG, -1, 1, NAME63, 1,
                          NAME63),
            -1: (EV_PRICE, EV_NAME, EV_HELP, -1, -1, -1, EV_FLAG, -1, -1, 1, NAME63, 1, NAME63)}


def is_ev_item(it):
    return it in ev_items().values()


def _catalog_items(d):
    head = struct.unpack_from('<8h', d, 0)
    assert head[0] == 4 and head[6] == 32 and head[7] == -1, head
    cnt = list(head[1:6])
    n = sum(cnt)
    assert len(d) == 16 + 28 * n + 32 * 64, (len(d), cnt)
    return cnt, [struct.unpack_from('<I12h', d, 16 + 28 * i) for i in range(n)]


def strip_ev(d):
    """-> (catalog without our item, (tab-0 position, item) | None); also used by spot33_catalog for re-runs"""
    cnt, items = _catalog_items(d)
    pos = [i for i in range(cnt[0]) if is_ev_item(items[i])]
    assert len(pos) <= 1 and not any(is_ev_item(it) for it in items[cnt[0]:]), 'catalog: our item twice / wrong tab'
    if not pos:
        return d, None
    p = pos[0]
    cnt[0] -= 1
    out = struct.pack('<8h', 4, *cnt, 32, -1) + d[16:16 + 28 * p] + d[16 + 28 * (p + 1):]
    return out, (p, items[p])


def insert_ev(d, ev):
    p, it = ev
    cnt, items = _catalog_items(d)
    assert p <= cnt[0]
    cnt[0] += 1
    return struct.pack('<8h', 4, *cnt, 32, -1) + d[16:16 + 28 * p] + struct.pack('<I12h', *it) + d[16 + 28 * p:]


def patch_catalog(d, sora_unlock):
    base, had = strip_ev(d)
    cnt, items = _catalog_items(base)
    assert cnt[0] == 117, 'catalog tab 0 has %d items (vanilla 117) - stop' % cnt[0]
    fc = [i for i in range(cnt[0]) if items[i][1] == EV_NAME and items[i][9] == 1 and items[i][10] == 62]
    assert len(fc) == 1, 'no single "Encounter Voice - Feral Chaos" item in tab 0'
    evs = [it for it in items[:cnt[0]] if it[1] == EV_NAME]
    assert len(evs) == 32 and sorted(it[6] for it in evs) == list(range(856, 888)), 'native EV items not 856..887'
    assert all(it[2] == EV_HELP for it in evs) and {it[0] for it in evs} == {180, 10}, 'native EV items differ'
    want = (fc[0] + 1, ev_items()[sora_unlock])
    out = insert_ev(base, want)
    return out, had, want


def patch_utext_check(t):
    """the item uses only existing texts: group 0 #30, group 3 #4, group 2 #63 'Sora' (spot33_catalog)"""
    g = text_groups(t)
    assert g[0][EV_NAME] == 'Encounter Voice - \x13', repr(g[0][EV_NAME])
    assert g[3][EV_HELP].startswith('Unlocks encounter voice data for \x13.'), repr(g[3][EV_HELP])
    assert len(g[2]) > NAME63 and g[2][NAME63] == 'Sora', 'update_list group 2 #63 is not "Sora" (run spot33_catalog)'


# ---------------------------------------------------------------- texts
def text_groups(d):
    assert d[:8] == b'mess pak', d[:8]
    ng, = struct.unpack_from('<H', d, 10)
    out = []
    for i in range(ng):
        go, gs = struct.unpack_from('<II', d, 0x10 + 8 * i)
        out.append([(r.decode('utf-16-le').rstrip('\0') if r is not None else None) for r in decode(d[go:go + gs])])
    return out


def patch_ctext(d):
    """collection text group 6 + entry 78 'vs Sora' (catalog-style rebuild, every other group byte-identical)"""
    assert d[:8] == b'mess pak', d[:8]
    ng, = struct.unpack_from('<H', d, 10)
    groups = [struct.unpack_from('<II', d, 0x10 + 8 * i) for i in range(ng)]
    bodies = [d[go:go + gs] for go, gs in groups]
    raws = decode(bodies[6])
    e = encode(raws)
    assert e == bodies[6][:len(e)] and not bodies[6][len(e):].strip(b'\0'), 'group 6 does not re-encode'
    new = (VS_SORA_TEXT + '\0').encode('utf-16-le')
    texts = [r.decode('utf-16-le') for r in raws]
    assert texts[11] == 'vs Warrior of Light\0' and texts[42] == 'vs Feral Chaos\0' and \
        texts[77].startswith('000 - Land of the Stolen Crown'), 'collection group 6 is not the vanilla category list'
    if len(raws) == G6_COUNT + 1:
        assert raws[G6_COUNT] == new, 'group 6 entry 78 exists but is not ours'
        return d, False
    assert len(raws) == G6_COUNT, len(raws)
    bodies[6] = encode(raws + [new])
    out = bytearray(d[:groups[0][0]])
    for i, b in enumerate(bodies):
        out += b'\0' * ((-len(out)) % 16)
        struct.pack_into('<II', out, 0x10 + 8 * i, len(out), len(b))
        out += b
    out += b'\0' * ((-len(out)) % 16)
    for i, (go, gs) in enumerate(groups):
        no, ns = struct.unpack_from('<II', out, 0x10 + 8 * i)
        if i == 6:
            assert decode(bytes(out[no:no + ns])) == raws + [new]
        else:
            assert out[no:no + ns] == d[go:go + gs], 'group %d changed' % i
    return bytes(out), True


# ---------------------------------------------------------------- collection_param section 8
def sec8_entry(sora_unlock):
    return struct.pack('<HBB', sora_unlock & 0xFFFF, SORA, 0xFF)


def patch_sec8(d, sora_unlock):
    h = list(struct.unpack_from('<20H', d, 0))
    assert h[0] == 2 and h[1] == 9, h[:2]
    off = 40 + sum(h[11:19])
    n, size = h[10], h[19]
    assert size == 4 * n and off + size + 9 * 64 == len(d), (n, size, len(d))
    ents = [d[off + 4 * i:off + 4 * i + 4] for i in range(n)]
    ours = [sec8_entry(f) for f in (SORA_UNLOCK, -1)]
    had = [e for e in ents if e in ours]
    base = [e for e in ents if e not in ours]
    assert len(had) <= 1 and len(base) == 33 and sha(b''.join(base)) == VAN_SEC8, \
        'collection_param section 8 is not vanilla (+ ours) - stop'
    owners = [e[2] for e in base]
    k = owners.index(32) + 1                          # after Feral Chaos, before the system entry (255)
    assert owners[k] == 255
    new = base[:k] + [sec8_entry(sora_unlock)] + base[k:]
    h[10], h[19] = len(new), 4 * len(new)
    out = struct.pack('<20H', *h) + d[40:off] + b''.join(new) + d[off + size:]
    return out, bool(had), out == d


# ---------------------------------------------------------------- Jukebox rows
def row(cat, flag, idx, slot, kind, name):
    return struct.pack('<6h32s', cat, flag, idx, slot, kind, -1, name.encode())


def unrow(r):
    return struct.unpack_from('<6h', r, 0) + (r[12:44].split(b'\0')[0].decode(),)


def parse_cvp(d):
    one, ng = struct.unpack_from('<HH', d, 0)
    assert one == 1, one
    gs = [struct.unpack_from('<HHHh', d, 4 + 8 * i) for i in range(ng)]
    p = 4 + 8 * ng
    groups = []
    for o, c, sz, x in gs:
        assert sz == 44 * c and x == -1, (o, c, sz, x)
        groups.append((o, [d[p + 44 * k:p + 44 * k + 44] for k in range(c)]))
        p += 44 * c
    assert p == len(d), (p, len(d))
    return groups


def build_cvp(groups):
    out = bytearray(struct.pack('<HH', 1, len(groups)))
    for o, rows in groups:
        assert 44 * len(rows) < 0x10000
        out += struct.pack('<HHHh', o, len(rows), 44 * len(rows), -1)
    for o, rows in groups:
        out += b''.join(rows)
    return bytes(out)


def vs_categories(groups, vl):
    """opponent owner -> 'vs' category, from the native groups + their VOLD lists (must agree for every fighter)"""
    cat_of = {}
    for o, rows in groups:
        if o not in KEYS or o in (23, 32, SORA):
            continue
        vs = {}
        for r in vl.rows('P_' + KEYS[o].upper()):
            if r[2] == 0x46 and r[3] == 2:
                vs.setdefault(r[0], r[4])
        for r in rows:
            u = unrow(r)
            if 11 <= u[0] <= 42:
                opp = vs[u[6]]
                assert cat_of.setdefault(opp, u[0]) == u[0], 'vs category of owner %d differs' % opp
    assert sorted(cat_of.values()) == list(range(11, 43)) and sorted(cat_of) == list(range(1, 33)), cat_of
    cat_of[SORA] = VS_SORA_CAT
    return cat_of


def ev_flag_of(rows):
    fl = {unrow(r)[1] for r in rows if unrow(r)[0] == 2 or 11 <= unrow(r)[0] <= 41}
    assert len(fl) == 1, fl
    return fl.pop()


def bank_slots(bank):
    return {i: bank[off:off + size] for i, off, size, rate in sscf.entries(bank)}


def sora_group(vl, cat_of, cloud_rows):
    rows, audio, clones = [], {}, []
    vold = vl.rows(SORA_KEY)

    def fresh(clip):
        """Sora's list has same-audio copies of a few lines (so_battle_30 = 26, 39 = 34, 40 = 35, and the generic
        vs-Chaos fallback 71 = 24); a native group never lists one line twice -> keep the first, skip the copies"""
        h = sha(vl.file('voice/EN/battle/%s.at3' % clip))
        if h in audio:
            if audio[h] != clip:
                clones.append((clip, audio[h]))
            return False
        audio[h] = clip
        return True

    # Encounter 1..N
    enc, seen = [], set()
    for r in vold:
        if r[2] == 0x46 and r[3] in (0, 5, 7, 8) and r[0] not in seen:
            seen.add(r[0])
            if fresh(r[0]):
                enc.append(r[0])
    rows += [row(2, EV_FLAG, k, 0, 0, c) for k, c in enumerate(enc, 1)]
    # vs X by category (+ vs Sora mirror after vs Feral Chaos)
    vs = {}
    for r in vold:
        if r[2] == 0x46 and r[3] == 2:
            assert vs.setdefault(r[4], r[0]) == r[0], 'Sora has two vs-%d rows' % r[4]
    assert set(vs) <= set(cat_of), sorted(vs)
    vs_rows = 0
    for opp in sorted(vs, key=lambda o: cat_of[o]):
        if fresh(vs[opp]):
            rows.append(row(cat_of[opp], FC_EV_FLAG if opp == 32 else EV_FLAG, 0, 0, 0, vs[opp]))
            vs_rows += 1
    # Victory / Loss (all rows of the moment, unique clips)
    for cat, moment in ((3, 0x146), (4, 0x246)):
        clips, seen = [], set()
        for r in vold:
            if r[2] == moment and r[0] not in seen:
                seen.add(r[0])
                if fresh(r[0]):
                    clips.append(r[0])
        rows += [row(cat, -1, k, 0, 0, c) for k, c in enumerate(clips, 1)]
    # Battle N / Loss - Battle from the voice bank, Cloud's native slot choice
    bank = bank_slots(vl.file(SORA_BANK))
    c5 = [unrow(r)[3] for r in cloud_rows if unrow(r)[0] == 5 and unrow(r)[4] == 1]
    c44 = [unrow(r)[3] for r in cloud_rows if unrow(r)[0] == 44]
    assert c5 and len(c44) == 1, (c5, c44)
    picked, hashes, skipped = [], {}, []
    for s in c5:
        data = bank.get(s, b'')
        if not data.strip(b'\0'):
            skipped.append((s, 'empty'))
            continue
        h = sha(data)
        if h in hashes:
            skipped.append((s, 'same audio as slot %d' % hashes[h]))
            continue
        hashes[h] = s
        picked.append(s)
    rows += [row(5, -1, k, s, 1, SORA_BANK_NAME) for k, s in enumerate(picked, 1)]
    ko = c44[0]
    assert bank.get(ko, b'').strip(b'\0'), 'Sora KO slot %d empty' % ko
    rows.append(row(44, -1, 0, ko, 1, SORA_BANK_NAME))
    cloud_assist = [unrow(r) for r in cloud_rows if unrow(r)[0] == 45]
    abank = bank_slots(vl.file(SORA_ABANK))
    assist = None
    if len(cloud_assist) == 1 and abank.get(cloud_assist[0][3], b'').strip(b'\0'):
        assist = cloud_assist[0][3]
        rows.append(row(45, -1, 0, assist, 1, SORA_BANK_NAME.replace('_00', '_a_00')))
    info = dict(encounter=len(enc), vs=vs_rows, clones=clones, win=sum(1 for r in rows if unrow(r)[0] == 3),
                loss=sum(1 for r in rows if unrow(r)[0] == 4), battle=len(picked), skipped=skipped, ko=ko,
                assist=assist)
    return rows, info


def patch_cvp(d, vl):
    groups = parse_cvp(d)
    owners = [o for o, _ in groups]
    assert owners in (list(range(1, 33)) + [255], list(range(1, 34)) + [255]), owners
    had33 = SORA in owners
    groups = [(o, rows) for o, rows in groups if o != SORA]
    native, added = [], []
    for o, rows in groups:
        base = [r for r in rows if unrow(r)[0] != VS_SORA_CAT]
        assert len(rows) - len(base) <= 1, 'group %d has two vs-Sora rows' % o
        assert sha(b''.join(base)) == VAN_CVP_GROUPS[o], 'jukebox group %d is not vanilla (+ ours) - stop' % o
        native.append((o, base))
    cat_of = vs_categories(native, vl)
    cloud_rows = dict(native)[CLOUD]
    out_groups = []
    for o, base in native:
        rows = list(base)
        if o in KEYS and o != SORA:
            vs33 = [r for r in vl.rows('P_' + KEYS[o].upper()) if r[2] == 0x46 and r[3] == 2 and r[4] == SORA]
            if vs33:
                assert len({r[0] for r in vs33}) == 1, (o, vs33)
                k = max(i for i, r in enumerate(rows) if 11 <= unrow(r)[0] <= 42) + 1
                rows.insert(k, row(VS_SORA_CAT, ev_flag_of(base), 0, 0, 0, vs33[0][0]))
                added.append((o, vs33[0][0]))
        out_groups.append((o, rows))
        if o == 32:
            srows, info = sora_group(vl, cat_of, cloud_rows)
            out_groups.append((SORA, srows))
    out = build_cvp(out_groups)
    assert parse_cvp(out) == out_groups
    return out, had33, added, info, out_groups


# ---------------------------------------------------------------- museum VOLD copies
def build_mpk(head, items):
    """MPK like the vanilla one: 16-B header, 16-B table, names back to back, members 16-aligned"""
    out = bytearray(head[:16])
    struct.pack_into('<I', out, 8, len(items))
    out += bytearray(16 * len(items))
    noffs = []
    for n, _ in items:
        noffs.append(len(out))
        out += n.encode() + b'\0'
    for i, (n, blob) in enumerate(items):
        out += b'\0' * ((-len(out)) % 16)
        struct.pack_into('<IIII', out, 16 + 16 * i, noffs[i], len(out), len(blob), 0)
        out += blob
    out += b'\0' * ((-len(out)) % 16)
    return bytes(out)


def patch_mpk(m, vl):
    ents = list(mpk.entries(m))
    assert build_mpk(m, [(n, m[o:o + s]) for n, o, s in ents]) == m, 'voice_load_parameter.mpk layout unknown'
    items, synced = [], []
    for n, o, s in ents:
        key = n[len('voice_load_p_'):-len('.bin')]
        assert n == 'voice_load_p_%s.bin' % key, n
        loose = vl.file('voice/EN/voice_load_P_%s.bin' % key.upper())
        mem = m[o:o + s]
        if key == KEYS[SORA]:
            assert mem[:4] == b'VOLD', 'museum member %s is not a VOLD list' % n
        else:
            assert mem == loose or sha(mem) == VAN_MPK_MEMBERS[key], \
                'museum copy %s is neither vanilla nor the loose list - stop' % n
        if mem != loose:
            synced.append(key)
        items.append((n, loose))
    names = [n for n, _ in items]
    assert set(names) - {'voice_load_p_sev120.bin'} == {'voice_load_p_%s.bin' % k for k in VAN_MPK_MEMBERS}, names
    sora = vl.file('voice/EN/voice_load_%s.bin' % SORA_KEY)
    if 'voice_load_p_sev120.bin' not in names:
        items.append(('voice_load_p_sev120.bin', sora))
        synced.append('sev120 (new)')
    out = build_mpk(m, items)
    chk = {n: out[o:o + s] for n, o, s in mpk.entries(out)}
    assert all(chk[n] == b for n, b in items)
    return out, synced


# ---------------------------------------------------------------- menu code
def patch_menu(iso, dry):
    with open(iso, 'rb') as f:
        for va, want in MENU_CONTEXT:
            f.seek(menu_off(va))
            got, = struct.unpack('<I', f.read(4))
            assert got == want, 'menu overlay 0x%08X = %08X, expected vanilla %08X - stop' % (va, got, want)
        cur = []
        for va, old, new, what in MENU_SITES:
            f.seek(menu_off(va))
            w, = struct.unpack('<I', f.read(4))
            assert w in (old, new), 'menu overlay 0x%08X = %08X (neither vanilla %08X nor ours %08X) - stop' % (
                va, w, old, new)
            cur.append(w)
    todo = [(s, w) for s, w in zip(MENU_SITES, cur) if w != s[2]]
    print('OVL_MENU_APP Jukebox list sizes: %d/%d words %s' % (
        len(MENU_SITES) - len(todo), len(MENU_SITES), 'already' if not todo else ('to write' if dry else 'written')))
    if todo and not dry:
        with open(iso, 'r+b') as f:
            for (va, old, new, what), w in todo:
                f.seek(menu_off(va))
                f.write(struct.pack('<I', new))
        with open(iso, 'rb') as f:
            for va, old, new, what in MENU_SITES:
                f.seek(menu_off(va))
                assert struct.unpack('<I', f.read(4))[0] == new


# ---------------------------------------------------------------- free-flag proof
def flag_users(iso, vl, flags):
    hits = []
    cnt, items = _catalog_items(strip_ev(vl.file(PARAM))[0])
    for i, it in enumerate(items):
        for fv in flags:
            if fv in it[3:8]:
                hits.append('catalog item %d uses %d' % (i, fv))
    with open(iso, 'rb') as f:
        for i in range(40):
            f.seek(eboot_off(0x089D7BE0 + 20 * i))
            r = struct.unpack('<5i', f.read(20))
            if r[0] == -1:
                break
            hits += ['unlock row %d uses %d' % (i, fv) for fv in flags if fv in r[1:]]
    cp = vl.file(CPARAM)
    h = struct.unpack_from('<20H', cp, 0)
    offs = [40]
    for sz in h[11:20]:
        offs.append(offs[-1] + sz)
    for i in range(h[2]):                                   # section 0 character records: unlock / viewed flags
        hits += ['Museum record %d uses %d' % (i, fv) for fv in flags
                 if fv in struct.unpack_from('<2H', cp, offs[0] + 48 * i + 8)]
    for i in range(h[8]):                                   # section 6 music records: unlock flag
        hits += ['Museum music %d uses %d' % (i, fv) for fv in flags
                 if struct.unpack_from('<H', cp, offs[6] + 8 * i + 2)[0] == fv]
    for i in range(h[10]):                                  # section 8 Jukebox characters
        e = cp[offs[8] + 4 * i:offs[8] + 4 * i + 4]
        if e[2] != SORA:
            hits += ['Jukebox character %d uses %d' % (i, fv) for fv in flags if struct.unpack('<H', e[:2])[0] == fv]
    for o, rows in parse_cvp(vl.file(CVP)):
        for r in rows:
            u = unrow(r)
            if o != SORA and u[1] in flags and not (u[0] == VS_SORA_CAT):
                hits.append('Jukebox group %d row %s' % (o, u))
    main = vl.file(MAIN)
    mem = {n: main[o:o + s] for n, o, s in mpk.entries(main)}
    _, chunks = arc_split(mem['system.bin'])
    u = next(c for c in chunks if c[1] == b'uicn')[2]
    for i in range(struct.unpack_from('<H', u, 2)[0]):
        hits += ['uicn row %d uses %d' % (i, fv) for fv in flags if fv in struct.unpack_from('<2H', u, 4 + 8 * i + 4)]
    b = mem['bgm_entry.bin']
    for i in range(struct.unpack_from('<I', b, 8)[0]):
        hits += ['bgm_entry row %d uses %d' % (i, fv) for fv in flags if fv in struct.unpack_from('<4h', b, 16 + 44 * i + 4)]
    with open(iso, 'rb') as f:
        for name, (sec, size) in CODE_FILES.items():
            f.seek(sec * SECTOR)
            code = f.read(size)
            words = struct.unpack('<%dI' % (len(code) // 4), code[:len(code) // 4 * 4])
            for k, w in enumerate(words):
                if (w >> 26) in (0x09, 0x0D) and ((w >> 21) & 31) == 0 and (w & 0xFFFF) in flags:
                    hits.append('%s +0x%X immediate %d' % (name, 4 * k, w & 0xFFFF))
    return hits


# ---------------------------------------------------------------- main
def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    assert len(args) == 1, __doc__
    iso = args[0]
    dry = '--dry' in sys.argv
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the vanilla ISO'
    if not dry:
        r = subprocess.run(['pgrep', '-a', '-x', 'PPSSPPSDL'], capture_output=True, text=True)
        assert os.path.abspath(iso) not in r.stdout and os.path.basename(iso) not in r.stdout, \
            'PPSSPP has this ISO open - stop'
    sora_unlock = unlock_flag(iso)
    vl = VoiceISO(iso)
    users = flag_users(iso, vl, (EV_FLAG, NEW_FLAG))
    assert not users, 'flags in use: %s - stop' % users
    print('flags %d (Encounter Voice - Sora) / %d (catalog "new") unused by catalog, unlock table, Museum sections '
          '0/6/8, Jukebox rows, uicn, bgm_entry, code immediates' % (EV_FLAG, NEW_FLAG))
    writes = []

    patch_utext_check(vl.file(UTEXT))
    d = vl.file(PARAM)
    nd, had, (pos, item) = patch_catalog(d, sora_unlock)
    print('%s: tab 0 #%d "Encounter Voice - Sora" %d PP, flag %d, listed %s: %s' % (
        PARAM, pos, item[0], item[6], 'after flag %d (new flag %d)' % (item[4], item[7]) if item[4] != -1 else 'always',
        'already' if nd == d else ('to write' if dry else 'written')))
    if nd != d:
        writes.append((PARAM, nd))

    cp = vl.file(CPARAM)
    ncp, had8, same = patch_sec8(cp, sora_unlock)
    print('%s section 8: Sora (owner %d, flag %d) after Feral Chaos: %s' % (
        CPARAM, SORA, sora_unlock, 'already' if same else ('to write' if dry else 'written')))
    if not same:
        writes.append((CPARAM, ncp))

    ct = vl.file(CTEXT)
    nct, ch = patch_ctext(ct)
    print('%s group 6 #%d "%s": %s' % (CTEXT, VS_SORA_CAT, VS_SORA_TEXT,
                                         ('to write' if dry else 'written') if ch else 'already'))
    if ch:
        writes.append((CTEXT, nct))

    cv = vl.file(CVP)
    ncv, had33, added, info, groups = patch_cvp(cv, vl)
    print('%s: group 33 = Encounter %d, vs %d (incl. mirror), Victory %d, Loss %d, Battle %d (bank %s), Loss - Battle '
          'slot %d, Assist %s; flags %d / vs Feral Chaos %d; %d rows: %s' % (
              CVP, info['encounter'], info['vs'], info['win'], info['loss'], info['battle'], SORA_BANK_NAME,
              info['ko'], info['assist'] if info['assist'] is not None else 'none', EV_FLAG, FC_EV_FLAG,
              len(dict(groups)[SORA]), 'already' if ncv == cv else ('to write' if dry else 'written')))
    print('  skipped same-audio clips: %s' % ' '.join('%s(=%s)' % c for c in info['clones']))
    print('  skipped bank slots: %s' % info['skipped'])
    print('  "vs Sora" rows in %d other groups: %s' % (len(added), ' '.join('%d:%s' % a for a in added)))
    for o, rows in groups:                                  # every kind-0 clip must exist and be in the VOLD copy
        for r in rows:
            u = unrow(r)
            if u[4] == 0 and o in KEYS and (o == SORA or u[0] == VS_SORA_CAT):
                vl.file('voice/EN/battle/%s.at3' % u[6])
    if ncv != cv:
        writes.append((CVP, ncv))

    m = vl.file(VMPK)
    nm, synced = patch_mpk(m, vl)
    print('%s: museum VOLD copies = loose lists (%d members changed: %s): %s' % (
        VMPK, len(synced), ' '.join(synced) or '-', 'already' if nm == m else ('to write' if dry else 'written')))
    if nm != m:
        writes.append((VMPK, nm))
    for o, rows in groups:                                  # museum lookup will find every kind-0 clip we list
        if o == SORA or any(unrow(r)[0] == VS_SORA_CAT for r in rows):
            key = KEYS[o]
            mem = {n: nm[a:a + s] for n, a, s in mpk.entries(nm)}['voice_load_p_%s.bin' % key]
            names = {mem[16 + 24 * i:32 + 24 * i].split(b'\0')[0].decode() for i in range(struct.unpack_from('<I', mem, 8)[0])}
            for r in rows:
                u = unrow(r)
                if u[4] == 0 and (o == SORA or u[0] == VS_SORA_CAT):
                    assert u[6] in names, (o, u)
    vl.f.close()

    if not dry:
        for path, data in writes:
            put_file(iso, path, data)
    patch_menu(iso, dry)
    print('dry run, nothing written' if dry else 'done')


if __name__ == '__main__':
    main()
