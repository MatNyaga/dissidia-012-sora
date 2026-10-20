"""P1.2 extractor: reference build R0 - clean dump -> a fighter package (docs/PACKAGE-FORMAT.md v1.0).

  python3 -I tools/pkg/extract.py CLEAN.iso R0.iso OUT_DIR [--report REPORT.json] [--dry]

READ-ONLY on both discs (opened 'rb'). Writes only OUT_DIR (must not be under dumps/; an existing OUT_DIR must be a
previous package - its manifest/files/rows/patches/order.json are replaced) and the report (default
tools/pkg/ref/sora-extract-report.json). --dry = compute + self-check, write nothing.

What it does
  1 PACKAGE paths (PACKAGE_INFO rows): hash only on R0 -> files/package/<path> (add); same hash, other bytes ->
    shared container (MPK / ARC / mess pak / menu pak / VOLD / param table / text file, tools/pkg/containers.py)
    -> rows/<owner_tables id>.json, row-level; a fighter-own file (sev120) -> files/ (replace).
  2 ISO files: new loose files -> files/iso/...; EBOOT.BIN -> files entry `produce: eboot_plain` (decrypted
    clean EBOOT, tools/scripts/eboot_plain.py) + word diffs vs the plain clean EBOOT; OVL_*_APP.ELF word diffs.
    Code words are grouped by tools/pkg/code_sites.json: code-site/iso-file ids -> patches/<id>.json, data ids
    (tables inside a code image) -> rows/<id>.json with ns img:<IMAGE>, key at = VA.
  3 SELF-CHECK (the P1.3 proof without writing an ISO): every changed container is rebuilt from the clean bytes +
    the package rows (containers.apply_file) and must equal R0 byte for byte; EBOOT / overlays = plain clean +
    rows + patches == R0; every files/ entry has R0's sha256. A container that does not round-trip is shipped
    whole (files/, listed as a stop-gap); any difference without an owner_tables id is listed as UNMATCHED.
  4 manifest (allocations derived from the rows, features, provenance), pkgformat.seal, validate --strict.
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools/scripts'))
sys.dont_write_bytecode = True
import containers as K  # noqa: E402
import equiv  # noqa: E402
import pkgformat as P  # noqa: E402
from pkgapply import apply_image  # noqa: E402
from pkghash import pkg_hash  # noqa: E402

DATA = 'PSP_GAME/USRDIR/DATA/'
EBOOT = 'PSP_GAME/SYSDIR/EBOOT.BIN'
IMAGES = {EBOOT: ('EBOOT', 0x08804040 - 0x1018),
          DATA + 'OVL_MENU_APP.ELF': ('OVL_MENU_APP', 0x089DD4C0 - 0x54),
          DATA + 'OVL_BATTLE_APP.ELF': ('OVL_BATTLE_APP', 0x089DD4C0 - 0x54)}
IMG_PATH = {v[0]: k for k, v in IMAGES.items()}
LAYOUT_FILES = {DATA + 'PACKAGE.BIN', DATA + 'PACKAGE_INFO.BIN'}
OWNER, KEY = 33, 'sev120'
DEFAULT_REPORT = os.path.join(HERE, 'ref', 'sora-extract-report.json')

# ---------------------------------------------------------------- owner_tables ids for rows (ns regex, lower case)
TABLE_RULES = [
    (r'main\.bin!objentry\.bin$', 'objentry'),
    (r'main\.bin!bgm_entry\.bin$', 'bgm_entry'),
    (r'main\.bin!manual_param\.bin$', 'battle_tips'),
    (r'main\.bin!assist\.bin$', 'assist_bin'),
    (r'system\.bin!chrp$', 'chrp'),
    (r'system\.bin!ablt$', 'ablt_rows'),
    (r'system\.bin!item$', 'item_rows'),
    (r'system\.bin!eqpm$', 'eqpm_presets'),
    (r'system\.bin!chrl$', 'chrl'),
    (r'system\.bin!amas$', 'amas'),
    (r'system\.bin!jobp$', 'jobp_stance'),
    (r'system\.bin!acab$', 'acab'),
    (r'system\.bin!uicn$', 'uicn'),
    (r'system\.bin!eqaa$', 'eqaa'),
    (r'system\.bin!grwp$', 'grwp'),                                     # RC3: owner-33 Max CP growth row (Vita crash fix)
    (r'^pkg:battle_non_residing\.bin', 'brai_seco'),
    (r'^pkg:voice/[a-z]+/voice_load_p_', 'vold_lists'),
    (r'^pkg:voice/[a-z]+/voice_load_parameter\.mpk', 'vold_lists'),      # Museum copies (members + member add)
    (r'^pkg:collection_param\.bin!sec4$', 'museum_icons'),
    (r'^pkg:collection_param\.bin!sec6$', 'museum_music'),
    (r'^pkg:collection_param\.bin', 'museum_char_files'),
    (r'^pkg:command_list_param\.bin', 'cmd_list'),
    (r'^pkg:update_list_param\.bin', 'pp_catalog'),
    (r'main_lang\.bin!bgm_name\.bin$', 'bgm_names'),
    (r'main_lang\.bin!ability\.bin$', 'ability_text'),
    (r'main_lang\.bin!item(_help)?\.bin$', 'item_texts'),
    (r'field_lang\.bin!battle_voice_name\.bin$', 'voice_subtitles'),
    (r'^pkg:general_archive/menu/user_icon[0-9]+\.bin', 'museum_icons'),
    (r'mess_pk_customize_ability_0\.bin#1$', 'cmd_list'),
    (r'mess_pk_customize_ability_0\.bin', 'customize_desc_text'),
    (r'mess_pk_exmode_0\.bin', 'exmode_texts'),
    (r'mess_pk_customize_common_0\.bin', 'tips_texts'),
    (r'mess_pk_chara_select_0\.bin#2$', 'char_blurbs'),                  # RR-17 blurb groups (id 33 = Sora)
    (r'mess_pk_(creation_room|party_setting)_0\.bin#5$', 'char_blurbs'),
    (r'mess_pk_story_mode_0\.bin#1$', 'char_blurbs'),
    (r'mess_pk_update_list_0\.bin#7$', 'char_blurbs'),
    (r'mess_pk_creation_room_0\.bin#4$', 'oq_full_names'),              # RR-18 full-name groups (entry 122 = Sora)
    (r'mess_pk_chara_select_0\.bin#0$', 'oq_full_names'),
    (r'mess_pk_party_setting_0\.bin#6$', 'oq_full_names'),
    (r'mess_pk_story_mode_0\.bin#10$', 'oq_full_names'),
    (r'mess_pk_(chara_select|story_mode)_0\.bin$', 'char_blurbs'),       # whole-pack layout pin (R2: only the blurb group changes)
    (r'mess_pk_collection_0\.bin#3$', 'char_name_lists'),
    (r'mess_pk_collection_0\.bin', 'museum_texts'),
    (r'mess_pk_update_list_0\.bin#2$', 'char_name_lists'),
    (r'mess_pk_update_list_0\.bin', 'catalog_texts'),
    (r'mess_pk_(dungeon|network|md_list|worldmap|loading|colosseum|creation_room)_0\.bin', 'char_name_lists'),
    (r'menu_pk_free_battle_gim_3\.bin', 'qb_pictures'),
    (r'menu_pk_collection_gim_0\.bin', 'records_icons'),
    (r'menu_pk_dungeon_gim_0\.bin', 'labyrinth_face'),
    (r'^pkg:menu/(en/)?menu_l?pk_[a-z_]+_gim_[0-9]+\.bin', 'menu_scene_packs'),
]
FIGHTER_OWN = re.compile(r'(^|/)[^/]*%s[^/]*$' % KEY, re.I)     # sev120 files = Sora's own (whole files)
GRID_PATCH_MAX = 16                                          # changed span <= this -> patch op, else replace


def table_for_ns(ns):
    low = ns.lower()
    for rx, t in TABLE_RULES:
        if re.search(rx, low):
            return t
    return None


def table_for_file(target, path):
    low = path.lower()
    if target == 'iso':
        return 'bgm_files' if '/bgm/' in low else None
    if re.match(r'obj/p_[a-z]{3}[0-9]{3}(_a)?\.objx$', low):
        return 'own_battle_file'
    if 'user_icon' in low:
        return 'museum_icons'
    if FIGHTER_OWN.search(low) or low.startswith('voice/') or low.startswith('menu/'):
        return 'fighter_files'
    return None


# ---------------------------------------------------------------- names
def extra_names(discs):
    """candidate paths beyond equiv.load_names: other fighters' voice lists, user icons + archives, title calls"""
    cand = set()
    keys = set()
    for p in ('tools/scripts', 'notes'):
        for d, _, fs in os.walk(os.path.join(ROOT, p)):
            for fn in fs:
                if fn.endswith(('.py', '.md')):
                    with open(os.path.join(d, fn), errors='replace') as f:
                        keys.update(k.upper() for k in re.findall(r'[pP]_([A-Za-z]{3}\d{3})', f.read()))
    for k in keys:
        cand.add('voice/EN/voice_load_P_%s.bin' % k)
    for i in range(1000):
        cand.add('menu/JP/Collection/user_icon/user_icon%03d.gim' % i)
    for i in range(40):
        cand.add('general_archive/menu/user_icon%02d.bin' % i)
    for n in 'wo ga fn em on cd ce gb ca bu ed gi ti cf cl sf tf la sq am zi kj td yu je pr sh va gs li co ch na ae so'.split():
        for half in ('SQE', 'DDD'):
            cand.add('voice/EN/event/title_call/title_%s_%s.at3' % (n, half))
    return {pkg_hash(c): c for c in cand}


# ---------------------------------------------------------------- diff -> rows
def span(a, b):
    """first and last+1 differing byte of equal-length a, b"""
    i = next(k for k in range(len(a)) if a[k] != b[k])
    j = next(k for k in range(len(a) - 1, -1, -1) if a[k] != b[k]) + 1
    return i, j


def printable(raw):
    parts = [p for p in raw.split(b'\0') if p]
    if not parts:
        return None
    txt = b' | '.join(parts)
    try:
        s = txt.decode('utf-8')
    except UnicodeDecodeError:
        return None
    if sum(c.isprintable() for c in s) < 0.9 * len(s):
        return None
    return s if len(s) <= 400 else s[:400] + '…'


def decode_fields(ns, raw):
    low = ns.lower()
    try:
        if 'voice_load_p_' in low and len(raw) == 24:
            line, moment, cond, value = struct.unpack_from('<HHhh', raw, 16)
            return {'clip': raw[:16].split(b'\0')[0].decode('latin-1'), 'line': line, 'moment': moment, 'cond': cond,
                    'value': value}
        if low.endswith('!objentry.bin') and len(raw) == 68:
            return {'id': struct.unpack_from('<H', raw, 0)[0], 'name': raw[0x24:0x34].split(b'\0')[0].decode('latin-1'),
                    'model': raw[0x34:0x44].split(b'\0')[0].decode('latin-1')}
        if low.endswith('!item') and len(raw) == 104:
            i, n, h = struct.unpack_from('<HHH', raw, 0)
            return {'id': i, 'name_idx': n, 'help_idx': h, 'mask': '0x%08x' % struct.unpack_from('<I', raw, 0x18)[0]}
        if low.endswith('!uicn') and len(raw) == 8:
            a, b, c, d = struct.unpack('<HHhH', raw)
            return {'index': a, 'icon': b, 'unlock_flag': c, 'viewed_flag': d}
        if low.endswith('!ablt') and len(raw) == 40:
            return {'owner': raw[1], 'action': struct.unpack_from('<H', raw, 12)[0]}
    except (struct.error, UnicodeDecodeError):
        return None
    return None


def grid_rows(ns, spec, a, b, rs=None):
    ha, ra, ta, row, _ = K.grid_parts(spec, a, rs)
    hb, rb, tb, _, _ = K.grid_parts(spec, b, rs)
    out = []
    if ha != hb:
        if len(ha) != len(hb):
            raise ValueError('%s: header size changed' % ns)
        i, j = span(ha, hb)
        out.append({'ns': ns, 'key': {'at': 'hdr'}, 'op': 'patch', 'offset': i, 'old': ha[i:j].hex(), 'new': hb[i:j].hex()})
    if ta != tb:
        out.append({'ns': ns, 'key': {'at': 'tail'}, 'op': 'replace', 'raw': tb.hex(), 'old_raw': ta.hex()})
    sm = difflib.SequenceMatcher(None, ra, rb, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        n = min(i2 - i1, j2 - j1)
        for k in range(n):
            x, y = ra[i1 + k], rb[j1 + k]
            s, e = span(x, y)
            if e - s <= GRID_PATCH_MAX:
                r = {'ns': ns, 'key': {'at': i1 + k}, 'op': 'patch', 'offset': s, 'old': x[s:e].hex(), 'new': y[s:e].hex()}
            else:
                r = {'ns': ns, 'key': {'at': i1 + k}, 'op': 'replace', 'raw': y.hex(), 'old_raw': x.hex()}
            f = decode_fields(ns, y)
            if f:
                r['fields'] = f
            out.append(r)
        for k in range(i1 + n, i2):
            out.append({'ns': ns, 'key': {'at': k}, 'op': 'delete', 'old_raw': ra[k].hex()})
        for k in range(j1 + n, j2):
            r = {'ns': ns, 'key': {'at': k}, 'op': 'add', 'raw': rb[k].hex()}
            f = decode_fields(ns, rb[k])
            if f:
                r['fields'] = f
            out.append(r)
    return out


def tokens(d):
    out, s = [], 0
    for m in re.finditer(b'\0+', d):
        out.append(d[s:m.end()])
        s = m.end()
    if s < len(d):
        out.append(d[s:])
    return out


def bytes_rows(ns, a, b):
    if a == b:
        return []
    p = 0
    n = min(len(a), len(b))
    while p < n and a[p] == b[p]:
        p += 1
    q = 0
    while q < n - p and a[len(a) - 1 - q] == b[len(b) - 1 - q]:
        q += 1
    ma, mb = a[p:len(a) - q], b[p:len(b) - q]
    out = []

    def emit(off, old, new):
        if old == new:
            return
        if old and new and len(old) == len(new):
            s, e = span(old, new)
            old, new, off = old[s:e], new[s:e], off + s
        if not old:
            r = {'ns': ns, 'key': {'at': off}, 'op': 'add', 'raw': new.hex()}
        elif not new:
            r = {'ns': ns, 'key': {'at': off}, 'op': 'delete', 'old_raw': old.hex()}
        else:
            r = {'ns': ns, 'key': {'at': off}, 'op': 'replace', 'raw': new.hex(), 'old_raw': old.hex()}
        t = printable(new)
        if t:
            r['text'] = t
        out.append(r)
    if len(ma) == len(mb) and len(ma) <= 64:
        emit(p, ma, mb)
        return out
    ta, tb = tokens(ma), tokens(mb)
    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=len(ta) > 2000)
    oa = [0]
    for t in ta:
        oa.append(oa[-1] + len(t))
    ob = [0]
    for t in tb:
        ob.append(ob[-1] + len(t))
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        emit(p + oa[i1], ma[oa[i1]:oa[i2]], mb[ob[j1]:ob[j2]])
    return out


def diff_node(ns, a, b, notes):
    """rows that turn node bytes a (clean) into b (R0). Raises ValueError when the node cannot be expressed."""
    kind = K.kind_of(ns, a)
    if K.kind_of(ns, b) != kind:
        raise ValueError('%s: container kind changed' % ns)
    if kind == 'sections':
        ua, ub = K.sec_split(a), K.sec_split(b)
        if [k for k, _ in ua] != [k for k, _ in ub]:
            raise ValueError('%s: section list changed' % ns)
        out = []
        for (k, x), (_, y) in zip(ua, ub):
            if x != y:
                cns = '%s!%s' % (ns, k)
                spec = K.leaf_codec(cns)
                if spec[0] == 'grid-sec':
                    out += grid_rows(cns, spec, x, y, rs=K.sec_rowsize(a, k))
                else:
                    out += bytes_rows(cns, x, y)
        return out
    if kind in K.SPLIT:
        ua, kids_a = K.node_children(kind, ns, a)
        ub, kids_b = K.node_children(kind, ns, b)
        da, db = dict(ua), dict(ub)
        keys_a, keys_b = [k for k, _ in ua], [k for k, _ in ub]
        out = []
        for k in keys_a:
            if k not in db:
                out.append({'ns': ns, 'key': {'at': k}, 'op': 'delete', 'old_raw': da[k].hex()})
        for k in keys_b:
            if k not in da:
                out.append({'ns': ns, 'key': {'at': k}, 'op': 'add', 'raw': db[k].hex()})
                continue
            if da[k] == db[k]:
                continue
            cns = {v: c for c, v in kids_a.items()}.get(k)
            sub = None
            if cns is not None and (K.kind_of(cns, da[k]) in K.SPLIT or K.leaf_codec(cns)):
                try:
                    sub = diff_node(cns, da[k], db[k], notes)
                except ValueError as ex:
                    notes.append('%s: member replaced whole (%s)' % (cns, ex))
            if sub is None:
                out.append({'ns': ns, 'key': {'at': k}, 'op': 'replace', 'raw': db[k].hex(), 'old_raw': da[k].hex()})
            else:
                out += sub
        # order of members: kept members keep their order, adds appended (mpk) / by id (pak)
        kept = [k for k in keys_a if k in db]
        added = [k for k in keys_b if k not in da]
        want = sorted(kept + added) if kind == 'pak' else kept + sorted(added, key=str)
        if want != keys_b:
            raise ValueError('%s: member order cannot be expressed (adds not at the end)' % ns)
        try:
            canon = K.join(kind, ns, a, ub)
        except ValueError:
            canon = None
        if canon != b:
            if canon is None:
                raise ValueError('%s: canonical %s re-encode impossible' % (ns, kind))
            skb, ska = K.skeleton(kind, b), K.skeleton(kind, canon)
            out.append({'ns': ns, 'key': {'at': 'layout'}, 'op': 'replace', 'raw': skb.hex(), 'old_raw': ska.hex(),
                        'note': 'layout pin: R0 skeleton (raw) instead of the canonical %s re-encode (old_raw = its '
                                'skeleton, the guard); %d B' % (kind, len(skb))})
            notes.append('%s: layout pin (%s, skeleton %d B)' % (ns, kind, len(skb)))
        return out
    spec = K.leaf_codec(ns)
    if spec is None:
        raise ValueError('%s: no codec' % ns)
    if spec[0] == 'grid':
        if len(a) < spec[1] or len(b) < spec[1]:
            raise ValueError('%s: shorter than its header' % ns)
        return grid_rows(ns, spec, a, b)
    if spec[0] == 'bytes':
        return bytes_rows(ns, a, b)
    raise ValueError('%s: codec %s needs its parent' % (ns, spec[0]))


# ---------------------------------------------------------------- code images
def load_sites():
    with open(os.path.join(HERE, 'code_sites.json'), encoding='utf-8') as f:
        d = json.load(f)
    return [(img, int(lo, 16), int(hi, 16), sid, script, note) for img, lo, hi, sid, script, note in d['ranges']]


def site_for(sites, img, va):
    for s in sites:
        if s[0] == img and s[1] <= va < s[2]:
            return s
    return None


def plain_eboot(enc):
    import eboot_plain as E
    if enc[:4] == b'\x7fELF':
        raise ValueError('clean EBOOT is already plain - not the clean dump?')
    if len(enc) != E.ENC_SIZE or hashlib.sha256(enc).hexdigest() != E.ENC_SHA:
        raise ValueError('clean EBOOT is not the known encrypted ULUS10566 EBOOT')
    elf, how = E.decrypt(enc)
    return elf, how


def code_diffs(img, base, a, b, sites, tables, unmatched):
    """-> {site id: [edits]} for patches, {table id: [rows]} for data in images"""
    patches, rows = {}, {}
    words = [o for o in range(0, min(len(a), len(b)) - 3, 4) if a[o:o + 4] != b[o:o + 4]]
    for o in words:
        va = o + base
        s = site_for(sites, img, va)
        if s is None:
            unmatched.append({'where': '%s 0x%08x' % (img, va), 'what': 'word 0x%08x -> 0x%08x' % (
                struct.unpack_from('<I', a, o)[0], struct.unpack_from('<I', b, o)[0]), 'reason': 'no code_sites.json range'})
            continue
        sid = s[3]
        if tables[sid]['kind'] in ('code-site', 'iso-file'):
            patches.setdefault(sid, []).append({'image': img, 'va': '0x%08x' % va,
                                                'old': '0x%08x' % struct.unpack_from('<I', a, o)[0],
                                                'new': '0x%08x' % struct.unpack_from('<I', b, o)[0]})
        else:
            lst = rows.setdefault(sid, [])
            if lst and lst[-1]['_end'] == va:
                lst[-1]['_old'] += a[o:o + 4]
                lst[-1]['_new'] += b[o:o + 4]
                lst[-1]['_end'] = va + 4
            else:
                lst.append({'ns': 'img:' + img, 'key': {'at': va}, 'op': 'replace', '_old': a[o:o + 4], '_new': b[o:o + 4],
                            '_end': va + 4, 'fields': {'va': '0x%08x' % va}, 'note': s[5] or s[4]})
    if len(b) > len(a):
        if (len(a) - len(a) % 4) != len(a):
            raise ValueError('%s: clean size not word aligned' % img)
        va = len(a) + base
        s = site_for(sites, img, va)
        if s is None:
            unmatched.append({'where': '%s 0x%08x' % (img, va), 'what': '%d appended bytes' % (len(b) - len(a)),
                              'reason': 'no code_sites.json range'})
        else:
            patches.setdefault(s[3], []).append({'image': img, 'va': '0x%08x' % va, 'old_bytes': None,
                                                 'new_bytes': b[len(a):].hex(), 'append': True})
    elif len(b) < len(a):
        unmatched.append({'where': img, 'what': 'image shrinks %d -> %d' % (len(a), len(b)), 'reason': 'not expressible'})
    for lst in rows.values():
        for r in lst:
            r['raw'], r['old_raw'] = r.pop('_new').hex(), r.pop('_old').hex()
            r.pop('_end')
    return patches, rows


# ---------------------------------------------------------------- allocations / features
def ranges(ids):
    ids = sorted(set(ids))
    out = []
    for i in ids:
        if out and out[-1][1] == i - 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return [x[0] if x[0] == x[1] else x for x in out]


def derive_allocations(rows_by_table, files, vold_clean_lines, vold_r0_lines):
    al = {}

    def add(space, ids, **kw):
        if ids:
            al.setdefault(space, []).append(dict(ids=ranges(ids), **kw))
    pics = {}
    for r in rows_by_table.get('qb_pictures', []) + rows_by_table.get('menu_scene_packs', []) + \
            rows_by_table.get('records_icons', []) + rows_by_table.get('labyrinth_face', []):
        if r['op'] == 'add' and r['ns'].startswith('pkg:menu/') and isinstance(r['key']['at'], int) and '!' not in r['ns']:
            pics.setdefault(r['ns'][4:], []).append(r['key']['at'])
    for ns in sorted(pics):
        add('picture_number', pics[ns], ns=ns, note='new menu pak entries (empty fillers included: pak ids are positional)')
    obj = [r['fields']['id'] for r in rows_by_table.get('objentry', []) if r.get('fields') and r['op'] == 'add']
    add('objentry_id', obj, role='new_rows', note='objentry rows added (u16 id at +0)')
    reuse = [r['fields']['id'] for r in rows_by_table.get('objentry', []) if r.get('fields') and r['op'] in ('patch', 'replace')]
    add('objentry_id', reuse, role='reused_rows', note='existing owner-33 / P_SEV120 placeholder rows edited in place')
    items = [r['fields']['id'] for r in rows_by_table.get('item_rows', []) if r.get('fields') and r['op'] == 'add']
    add('item_id', items, role='equipment')
    ui = [r['fields'] for r in rows_by_table.get('uicn', []) if r.get('fields') and r['op'] == 'add']
    add('museum_icon', [f['icon'] for f in ui], note='uicn rows added (icon numbers)')
    flags = [f['viewed_flag'] for f in ui if f['viewed_flag'] not in (0, 0xFFFF)]
    add('save_flag', flags, role='icon_viewed', note='uicn viewed flags')
    bgm = [r['key']['at'] for r in rows_by_table.get('bgm_entry', []) if r['op'] == 'add']
    add('bgm_id', bgm, note='bgm_entry rows added (row index = BGM id)')
    lines = sorted(vold_r0_lines - vold_clean_lines)
    add('voice_line', lines, note='line ids in R0 voice lists (Sora list + rows added to other lists) unused on the clean disc')
    return al


FEATURES = [  # (name, kind, table, transitional patch ids, params, note)
    ('reflect_guard', 'behaviour', 'reflect_guard', ['reflect_guard', 'battle_overlay_cave'], None, 'EX Mode Reflect guard (notes/reflect.md)'),
    ('ex_run_speed', 'behaviour', 'exrun_hook', ['exrun_hook'], {'mult': 1.4}, 'EX Mode ground run x1.40 (lui 0x3fb3)'),
    ('ex_damage', 'behaviour', 'chrp', [], {'flag_word': '0x0c03'}, 'chrp row 33 +0x0C (rows/chrp.json)'),
    ('burst_controller', 'behaviour', 'burst_controller', ['burst_controller'], {'controller': 'trinity'}, 'Trinity Limit controller (TRI)'),
    ('item_effects', 'behaviour', 'item_battle_effects', ['item_battle_effects'], None, 'Kingdom Key / Protect Belt / Crown Pendant battle effects'),
    ('item_owner', 'lookup', 'item_code_hooks', ['item_code_hooks'], {'items': [678, 679, 680, 681]}, 'items only owner 33 may equip'),
    ('title_call', 'lookup', 'title_call', ['title_call'], {'index': 34}, 'title-screen voice index 34'),
    ('assist_drop', 'lookup', 'assist_drop_words', ['assist_drop_words'], None, None),
    ('name_index', 'lookup', 'name_index_eboot', ['name_index_eboot'], {'index': 63}, None),
    ('record_slot', 'lookup', 'save_record_slot', ['save_record_hooks'], {'slot': 24}, None),
    ('start_preset', 'lookup', 'start_preset_table', [], {'preset': 250}, 'rows/start_preset_table.json (img:EBOOT)'),
    ('picture_remap', 'lookup', 'menu_picture_remaps', ['menu_picture_remaps', 'setup_banner_remap'], {'picture': 245}, None),
    ('labyrinth_face', 'lookup', 'labyrinth_face', [], None, 'rows/labyrinth_face.json (img:OVL_MENU_APP)'),
    ('records_icon', 'lookup', 'records_icons', ['records_list'], {'texture': 16480}, None),
    ('network_name', 'lookup', 'network_names', ['network_name_hook'], {'index': 63}, None),
    ('jukebox_voice', 'lookup', 'jukebox_voice', ['jukebox_list_code'], {'group': 33}, 'Museum Jukebox group 33; menu list caps 33 -> 34'),
]


# ---------------------------------------------------------------- main
def sha(b):
    return hashlib.sha256(b).hexdigest()


def write(path, data, dry):
    if dry:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)


def prepare_out(out, dry):
    real = os.path.realpath(out)
    if 'dumps' in real.split(os.sep):
        sys.exit('refusing to write under dumps/: %s' % real)
    if real.lower().endswith('.iso'):
        sys.exit('refusing an .iso output')
    if dry or not os.path.exists(out):
        return
    have = set(os.listdir(out))
    if have and 'manifest.json' not in have:
        sys.exit('%s exists and is not a package folder - refusing' % out)
    if have - {'manifest.json', 'files', 'rows', 'patches', 'order.json'}:
        sys.exit('%s holds unexpected files %s - refusing' % (out, sorted(have)))
    for n in have:
        p = os.path.join(out, n)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('clean')
    ap.add_argument('r0')
    ap.add_argument('out')
    ap.add_argument('--report', default=DEFAULT_REPORT)
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    if os.path.realpath(a.clean) == os.path.realpath(a.r0):
        sys.exit('CLEAN and R0 are the same file')
    prepare_out(a.out, True)
    with open(os.path.join(ROOT, 'tools/dlc/owner_tables.json'), encoding='utf-8') as f:
        tables = {t['id']: t for t in json.load(f)['tables']}
    print('hashing discs (read-only) ...', flush=True)
    clean_sha, r0_sha = equiv.isolib.sha256_file(a.clean), equiv.isolib.sha256_file(a.r0)
    C, R = equiv.Disc(a.clean), equiv.Disc(a.r0)
    names = equiv.load_names([C, R])
    names.update({h: n for h, n in extra_names([C, R]).items() if h not in names})
    sites = load_sites()
    for s in sites:
        if s[3] not in tables:
            sys.exit('code_sites.json names unknown owner_tables id %s' % s[3])

    files, rows, patches = [], [], {}      # files: (entry, bytes|None)
    unmatched, stopgaps, notes, checks = [], [], [], []
    file_bytes = {}

    def add_file(target, path, action, table, data, tier=None, note=None, produce=None):
        e = {'path': path, 'target': target, 'action': action, 'table': table, 'origin': 'derived',
             'sha256': sha(data), 'size': len(data)}
        if tier is not None:
            e['tier'] = tier
        if note:
            e['note'] = note
        if produce:
            e['produce'] = produce
        files.append(e)
        if not produce:
            file_bytes['files/%s/%s' % (target, path)] = data

    # ---- PACKAGE paths
    print('PACKAGE rows: clean %d, R0 %d' % (len(C.prows), len(R.prows)), flush=True)
    vold_clean, vold_r0 = set(), set()
    for h in sorted(set(C.prows) | set(R.prows)):
        rc, rr = C.prows.get(h), R.prows.get(h)
        nm = names.get(h)
        if rr is None:
            unmatched.append({'where': 'PACKAGE %08x %s' % (h, nm), 'what': 'row removed in R0', 'reason': 'removal not expressible in v1.0'})
            continue
        b = R.pkg_read(rr[1], rr[2])
        if b[:4] == b'VOLD':
            vold_r0.update(struct.unpack_from('<H', b, 16 + 24 * i + 16)[0] for i in range((len(b) - 16) // 24))
        if rc is not None:
            ca = C.pkg_read(rc[1], rc[2]) if (rc[2] != rr[2] or C.pkg_sha(rc[1], rc[2]) != R.pkg_sha(rr[1], rr[2])
                                              or (b[:4] == b'VOLD')) else None
            if ca is not None and ca[:4] == b'VOLD':
                vold_clean.update(struct.unpack_from('<H', ca, 16 + 24 * i + 16)[0] for i in range((len(ca) - 16) // 24))
            if ca is None or ca == b:
                if rc[3] != rr[3]:
                    unmatched.append({'where': 'PACKAGE %s' % (nm or '%08x' % h), 'what': 'tier %d -> %d only' % (rc[3], rr[3]),
                                      'reason': 'layout (tier) change of an unchanged file'})
                continue
        if nm is None:
            unmatched.append({'where': 'PACKAGE %08x' % h, 'what': '%s file, %d B' % ('added' if rc is None else 'changed', rr[2]),
                              'reason': 'no path name known for this hash'})
            continue
        if rc is None:
            t = table_for_file('package', nm)
            if t is None:
                unmatched.append({'where': nm, 'what': 'added file', 'reason': 'no owner_tables id for this path'})
                t = 'fighter_files'
            add_file('package', nm, 'add', t, b, tier=rr[3])
            continue
        a_ = ca
        ns = 'pkg:' + nm
        own = bool(FIGHTER_OWN.search(nm.lower()))
        if own:
            add_file('package', nm, 'replace', table_for_file('package', nm) or 'fighter_files', b, tier=rr[3])
            if rc[3] != rr[3]:
                notes.append('%s: tier %d -> %d' % (nm, rc[3], rr[3]))
            continue
        loc = []
        try:
            rws = diff_node(ns, a_, b, loc)
            got = K.apply_file(ns, a_, rws)
            if got != b:
                raise ValueError('rows do not rebuild R0 (%d vs %d B)' % (len(got), len(b)))
            for r in rws:
                t = table_for_ns(r['ns'])
                if t is None:
                    unmatched.append({'where': r['ns'], 'what': 'row %s %s' % (r['op'], r['key']['at']),
                                      'reason': 'no owner_tables id for this container'})
                r['_table'] = t
            rows += rws
            notes += loc
            checks.append((nm, 'rows', len(rws)))
            if rc[3] != rr[3]:
                unmatched.append({'where': nm, 'what': 'tier %d -> %d' % (rc[3], rr[3]), 'reason': 'tier change of a row-edited container'})
        except ValueError as ex:
            t = table_for_ns(ns) or 'fighter_files'
            add_file('package', nm, 'replace', t, b, tier=rr[3], note='stop-gap: shared container shipped whole (%s)' % ex)
            stopgaps.append({'path': nm, 'reason': str(ex)})

    # ---- ISO files
    print('ISO files ...', flush=True)
    img_bytes = {}
    for p in sorted(set(C.files) | set(R.files)):
        ec, er = C.files.get(p), R.files.get(p)
        if p in LAYOUT_FILES:
            continue
        if er is None:
            unmatched.append({'where': p, 'what': 'ISO file removed', 'reason': 'not expressible'})
            continue
        if ec is not None and ec[1] == er[1] and C.sha_extent(*ec) == R.sha_extent(*er):
            continue
        b = R.file_bytes(p)
        if p in IMAGES:
            img, base = IMAGES[p]
            a_ = C.file_bytes(p)
            if p == EBOOT:
                a_, how = plain_eboot(a_)
                add_file('iso', p, 'replace', 'eboot_plain', a_, produce='eboot_plain',
                         note='decrypted clean EBOOT (%s); patches/rows on EBOOT apply after this transform; moves to the engine package when it exists' % how)
            img_bytes[img] = (base, a_, b)
            continue
        if ec is None:
            t = table_for_file('iso', p)
            if t is None:
                unmatched.append({'where': p, 'what': 'added ISO file', 'reason': 'no owner_tables id'})
                t = 'fighter_files'
            add_file('iso', p, 'add', t, b)
        else:
            unmatched.append({'where': p, 'what': 'ISO file changed', 'reason': 'no codec for loose ISO files'})
    img_rows = []
    for img in ('EBOOT', 'OVL_MENU_APP', 'OVL_BATTLE_APP'):
        if img not in img_bytes:
            continue
        base, a_, b = img_bytes[img]
        pt, rw = code_diffs(img, base, a_, b, sites, tables, unmatched)
        for sid, eds in pt.items():
            patches.setdefault(sid, []).extend(eds)
        for tid, lst in rw.items():
            for r in lst:
                r['_table'] = tid
            img_rows += lst
        got = apply_image(img, base, a_, [e for eds in pt.values() for e in eds], [r for lst in rw.values() for r in lst])
        checks.append((img, 'image', 'OK' if got == b else 'MISMATCH'))
        if got != b:
            unmatched.append({'where': img, 'what': 'image rebuild differs from R0', 'reason': 'extractor bug'})
    rows += img_rows

    # ---- group rows by table, sort, write
    by_table = {}
    for r in rows:
        t = r.pop('_table') or 'UNMATCHED'
        by_table.setdefault(t, []).append(r)
    by_table.pop('UNMATCHED', None)
    for t, lst in by_table.items():
        lst.sort(key=lambda r: (r['ns'], P.key_tuple(r['key'], ['at'])))
        seen = set()
        for r in lst:
            k = (r['ns'], json.dumps(r['key']))
            if k in seen:
                sys.exit('duplicate row key %s %s in %s' % (k[0], k[1], t))
            seen.add(k)
    for sid in patches:
        patches[sid].sort(key=lambda e: (e['image'], int(e['va'], 16)))

    # ---- allocations, features, manifest
    al = derive_allocations(by_table, files, vold_clean, vold_r0)
    al.setdefault('record_slot', []).append({'ids': [24], 'note': 'spot33_save.py (friend card 24)'})
    al.setdefault('name_index', []).append({'ids': [63], 'note': 'spot33_ownername.py'})
    al.setdefault('sound_bank', []).extend([
        {'ids': [219000], 'role': 'snd', 'note': 'spot33_soundids.py'}, {'ids': [219100], 'role': 'voice', 'note': 'spot33_soundids.py'},
        {'ids': [219500], 'role': 'assist_snd', 'note': 'spot33_assist.py (engine +50000 for assist)'},
        {'ids': [219600], 'role': 'assist_voice', 'note': 'spot33_assist.py'}])
    al.setdefault('code_cave', []).extend([
        {'ids': [[0x089A8B24, 0x089A8F0B]], 'ns': 'EBOOT', 'note': 'dead function 0x089a8b14 (EXRUN, EXITEMS, EE_B)'},
        {'ids': [[0x089C1C8C, 0x089C250F]], 'ns': 'EBOOT', 'note': 'dead controller body (TRI)'},
        {'ids': [[0x089D1FB4, 0x089D2083]], 'ns': 'EBOOT', 'note': 'dead jump table (SCALE)'},
        {'ids': [[0x08B62F70, 0x08B6316F]], 'ns': 'OVL_BATTLE_APP', 'note': 'battle overlay cave (file grows)'}])
    for space in al:
        al[space].sort(key=lambda e: (e.get('ns', ''), json.dumps(e.get('ids', e.get('values')))))
    feats = {}
    for name, kind, table, tp, params, note in FEATURES:
        tp = [x for x in tp if x in patches]
        f = {'enabled': True, 'kind': kind, 'table': table}
        if tp:
            f['transitional_patches'] = sorted(tp)
        if params:
            f['params'] = params
        if note:
            f['note'] = note
        feats[name] = f
    files.sort(key=lambda e: (e['target'], e['path']))
    with open(os.path.abspath(__file__), 'rb') as f:
        tool_sha = sha(f.read())
    man = {
        'format': P.FORMAT, 'format_version': '%d.%d' % (P.FORMAT_MAJOR, P.FORMAT_MINOR), 'id': 'sora', 'version': '1.0.0',
        'kind': 'fighter', 'owner': OWNER, 'key': KEY,
        'display_names': {'EN': 'Sora'}, 'distribution': 'never-publish-raw',
        'base': {'serial': 'ULUS10566', 'clean_iso_sha256': clean_sha}, 'requires': [], 'layouts': ['A', 'B'],
        'allocations': al, 'files': files, 'rows': sorted(by_table), 'patches': sorted(patches), 'features': feats,
        'provenance': {'clean_iso_sha256': clean_sha, 'reference_iso_sha256': r0_sha, 'tool': 'tools/pkg/extract.py',
                       'tool_sha256': tool_sha},
        'notes': ('Extracted by P1.2 from R0 (reference build) minus the clean dump. Layouts A and B (B: install.py adds the '
                  'engine from tools/pkg/engine until it is a package of its own). Row semantics + container re-encoders: tools/pkg/containers.py. Layout pins: %d. '
                  'Stop-gap whole containers: %d.' % (sum(1 for r in rows if r['key']['at'] == 'layout'), len(stopgaps))),
        'inventory': {}, 'package_sha256': '0' * 64,
    }
    docs = {}
    for t, lst in sorted(by_table.items()):
        nss = {r['ns'] for r in lst}
        specs = {K.leaf_codec(n) for n in nss}
        rs = None
        if len(specs) == 1:
            sp = next(iter(specs))
            if sp and sp[0] == 'grid':
                rs = sp[2]
        d = {'format_version': '1.0', 'table': t, 'key_fields': ['at'], 'rows': lst, 'row_size': rs,
             'note': 'key at: see tools/pkg/containers.py (grid row index / byte offset / member name / entry id / VA for img:)'}
        if rs is not None and any(len(r.get(f, '')) not in (0, 2 * rs) for r in lst for f in ('raw', 'old_raw')):
            d['row_size'] = None
        docs['rows/%s.json' % t] = d
    for sid, eds in sorted(patches.items()):
        docs['patches/%s.json' % sid] = {'format_version': '1.0', 'site': sid, 'set': 'owner%d' % OWNER, 'layouts': ['A', 'B'],
                                         'edits': eds}

    # ---- report + write
    kinds = {}
    for r in rows:
        kinds[r['op']] = kinds.get(r['op'], 0) + 1
    summary = {
        'clean_sha256': clean_sha, 'r0_sha256': r0_sha,
        'files': {'package_add': sum(1 for f in files if f['target'] == 'package' and f['action'] == 'add'),
                  'package_replace': sum(1 for f in files if f['target'] == 'package' and f['action'] == 'replace'),
                  'iso_add': sum(1 for f in files if f['target'] == 'iso' and f['action'] == 'add'),
                  'produce': sum(1 for f in files if f.get('produce'))},
        'row_tables': len(by_table), 'rows': len(rows), 'row_ops': kinds,
        'patch_sites': len(patches), 'patch_edits': sum(len(e) for e in patches.values()),
        'layout_pins': sorted(r['ns'] for r in rows if r['key']['at'] == 'layout'),
        'stopgaps': stopgaps, 'unmatched': unmatched, 'notes': notes,
        'checks': [{'what': c[0], 'how': c[1], 'result': c[2]} for c in checks],
    }
    print(json.dumps({k: v for k, v in summary.items() if k not in ('checks', 'notes')}, indent=1)[:6000])
    if a.dry:
        print('--dry: nothing written')
        return 1 if unmatched else 0
    prepare_out(a.out, False)
    os.makedirs(a.out, exist_ok=True)
    for rel, data in file_bytes.items():
        write(os.path.join(a.out, rel), data, False)
    for rel, d in docs.items():
        write(os.path.join(a.out, rel), P.canon_bytes(d), False)
    write(os.path.join(a.out, 'manifest.json'), P.canon_bytes(man), False)
    P.seal(a.out)
    os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True)
    with open(a.report, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=1, sort_keys=True)
        f.write('\n')
    print('report %s' % a.report)
    r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'validate.py'), a.out, '--strict'], capture_output=True, text=True)
    print(r.stdout[-3000:])
    print('UNMATCHED %d, stop-gaps %d, layout pins %d' % (len(unmatched), len(stopgaps), len(summary['layout_pins'])))
    return 1 if (unmatched or r.returncode) else 0


if __name__ == '__main__':
    sys.exit(main())
