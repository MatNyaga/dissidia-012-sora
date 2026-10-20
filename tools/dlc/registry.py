"""P2.2: registry builder + validator for EXTRA.REG v1 (docs/ENGINE.md "Registry + stubs v2 (DRAFT, P2.1)").

Input: one registry-source JSON per package (tools/dlc/registry/<pkg>.json; every value is [value, source]).
Output: EXTRA.REG bytes exactly per the P2.1 layout (64-B rows, item-owner / item-fx / flag-map / aux / strings
sections, 32-bit sum). Static tool: reads JSON, tools/dlc/flag_map.json (P2.6) and, with --disc, an ISO READ-ONLY
(text/picture packs via comb_patch; a layout-A/R disc such as test352, not layout B). Writes only -o OUT.

  python3 -I tools/dlc/registry.py build SRC.json [SRC2.json ...] -o OUT [--disc ISO] [--dry]
  python3 -I tools/dlc/registry.py validate SRC.json [...] [--disc ISO]
  python3 -I tools/dlc/registry.py decode EXTRA.REG [-o OUT.json]
  python3 -I tools/dlc/registry.py selftest [--disc ISO]     (round trip + tools/dlc/registry/tests/cases.json)
Exit code 1 when a check fails (errors); warnings never fail.
"""
import copy
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
SCRIPTS = os.path.join(ROOT, 'tools', 'scripts')
REGDIR = os.path.join(HERE, 'registry')
FLAG_MAP = os.path.join(HERE, 'flag_map.json')

VERSION = 1
HEADER = 0x40
ROW = 64
MAX_ROWS = 31                                  # owners 33..63 (64-bit music mask ceiling)
MIN_ENGINE = 0x00020000
MAGIC = b'XREG'
FEATURES = {'EX_RUN': 1, 'REFLECT_GUARD': 2, 'EX_BURST_SOUND_SKIP': 3, 'ITEM_OWNER': 4, 'ITEM_EFFECTS': 5,
            'ITEM_SCALING': 6, 'BURST_MODULE': 7, 'PKG_FLAGS': 8, 'RECORD_SLOT': 9, 'OQ_FACE': 10}
FEAT_MASK = sum(1 << (i - 1) for i in FEATURES.values())
BEHAVIOUR = {'REFLECT_GUARD', 'ITEM_EFFECTS', 'ITEM_SCALING', 'BURST_MODULE', 'EX_BURST_SOUND_SKIP'}
EFFECTS = {'EX_HIT_GAIN': 1, 'EX_GUARD_GAIN': 2, 'REFLECT_POWER': 3, 'EX_DRAIN': 4}
BURST_CHRP, BURST_MODULE0 = 0xFF, 0x80
ITEM_CEILING = 683                             # owner_tables item_rows: loader + save-inventory ceiling (ids 0..682)
OBJENTRY_COSMOS = 1338                         # owner 34: own rows must sort before P_ORG800_1P (owner_tables)
OQ_EXTRA_FACES = 1                             # OQ face-handle list: room for one extra pair (P2.1 -> P2.7)
FRIEND_CARDS = 25
# Original Quest picture bases (spot33_menuart SCENES['original_quest'], owner-1 runs) and owner-icon layout
OQ_ICON, OQ_FACE_R, OQ_FACE, OQ_NAME, OQ_LAYOUT = 0x6434, 0x64B7, 0x64DA, 0x6454, 0x660E
# 64-B row: owner, row_flags, feat, panel_tex[3], panel_sprite, name_index, record_slot, museum_record, pic_slot,
# pic_slot_party, party_frame, setup_frame, oq_name, oq_face_pic, oq_face_layout, oq_banner, oq_row[3], burst_ctl,
# reserved, ex_run_mult, key_off, params[16]
ROW_FMT = '<BBH3HHHBBHHHHHHHH3HBBfI16s'
PARAMS_V1 = '<4HBBHf'                          # items[4], voice_bar, voice_reflect, shield_pct, crown_drain
assert struct.calcsize(ROW_FMT) == ROW and struct.calcsize(PARAMS_V1) == 16
HDR_FMT = '<4sHHHHIIHHIIIHHIIIIII'
assert struct.calcsize(HDR_FMT) == HEADER
U16_FIELDS = ('panel_sprite', 'name_index', 'pic_slot', 'pic_slot_party', 'party_frame', 'setup_frame', 'oq_name',
              'oq_face_pic', 'oq_face_layout', 'oq_banner')


# ---------------------------------------------------------------- source JSON
def val(x):
    """[value, source] -> value; anything else as is"""
    return x[0] if isinstance(x, list) and len(x) == 2 and isinstance(x[1], str) else x


def load_source(path_or_dict):
    s = json.load(open(path_or_dict)) if isinstance(path_or_dict, str) else copy.deepcopy(path_or_dict)
    r = {k: val(v) for k, v in s['row'].items() if k != 'params'}
    p = s['row'].get('params', {'layout': 'none'})
    r['params'] = {k: val(v) for k, v in p.items()}
    return dict(package=s['package'], placeholder=bool(s.get('placeholder')), row=r,
                items=val(s.get('items', {}).get('owned', [[], ''])), fx=s.get('items', {}).get('fx', []),
                flags=s.get('flags', []), install={k: val(v) for k, v in s.get('install', {}).items()})


def feat_bits(names):
    return sum(1 << (FEATURES[n] - 1) for n in names)


def feat_names(bits):
    return [n for n, i in sorted(FEATURES.items(), key=lambda kv: kv[1]) if bits >> (i - 1) & 1]


def pack_params(p):
    if p.get('layout') == 'behaviours-v1':
        it = list(p['items']) + [0] * (4 - len(p['items']))
        return struct.pack(PARAMS_V1, *it, p['voice_bar'], p['voice_reflect'], p['shield_pct'], p['crown_drain'])
    return bytes(16)


def unpack_params(b):
    if not any(b):
        return {'layout': 'none'}
    v = struct.unpack(PARAMS_V1, b)
    return {'layout': 'behaviours-v1', 'items': [x for x in v[:4]], 'voice_bar': v[4], 'voice_reflect': v[5],
            'shield_pct': v[6], 'crown_drain': v[7]}


# ---------------------------------------------------------------- build / decode
def pad4(b):
    return b + bytes(-len(b) % 4)


def build(pkgs):
    """list of loaded sources -> EXTRA.REG bytes (rows sorted by owner)"""
    pkgs = sorted(pkgs, key=lambda p: p['row']['owner'])
    strings = b''
    key_off = {}
    for p in pkgs:
        key_off[p['package']] = len(strings)
        strings += p['row']['key'].encode('ascii') + b'\0'
    strings = pad4(strings)
    rows = b''
    for p in pkgs:
        r = p['row']
        rows += struct.pack(ROW_FMT, r['owner'], 1, feat_bits(r['features']), *r['panel_tex'], r['panel_sprite'],
                            r['name_index'], r['record_slot'], r['museum_record'], r['pic_slot'], r['pic_slot_party'],
                            r['party_frame'], r['setup_frame'], r['oq_name'], r['oq_face_pic'], r['oq_face_layout'],
                            r['oq_banner'], *r['oq_row'], r['burst_ctl'], 0, r['ex_run_mult'], key_off[p['package']],
                            pack_params(r['params']))
    owned = {i: p['row']['owner'] for p in pkgs for i in p['items']}
    item_lo = min(owned) if owned else 0
    item_count = (max(owned) - item_lo + 1) if owned else 0
    item_owner = pad4(bytes(owned.get(item_lo + k, 0) for k in range(item_count)))
    fx = b''.join(struct.pack('<HBBf', f['item'], EFFECTS[f['effect']], 0, f['value'])
                  for p in pkgs for f in sorted(p['fx'], key=lambda f: f['item']))
    gate = sorted({f['flag'] for p in pkgs for f in p['flags'] if f.get('gate')})
    flag_lo = gate[0] if gate else 0
    flag_bits = (gate[-1] - flag_lo + 1) if gate else 0
    fm = bytearray((flag_bits + 7) // 8)
    for g in gate:
        fm[(g - flag_lo) >> 3] |= 1 << ((g - flag_lo) & 7)
    flagmap = pad4(bytes(fm))
    aux = b''                                   # per-behaviour tables (SCALE TAB, combo caps): P2.4
    off = HEADER
    rows_off = off; off += len(rows)
    io_off = off; off += len(item_owner)
    fx_off = off; off += len(fx)
    fm_off = off; off += len(flagmap)
    aux_off = off; off += len(aux)
    st_off = off; off += len(strings)
    body = rows + item_owner + fx + flagmap + aux + strings
    assert len(body) % 4 == 0
    total = sum(struct.unpack('<%dI' % (len(body) // 4), body)) & 0xFFFFFFFF
    hdr = struct.pack(HDR_FMT, MAGIC, VERSION, HEADER, ROW, len(pkgs), rows_off, io_off, item_lo, item_count,
                      fx_off, len(fx) // 8, fm_off, flag_lo, flag_bits, aux_off, len(aux), st_off, len(strings),
                      total, MIN_ENGINE)
    return hdr + body


def decode(b):
    """EXTRA.REG -> dict (raises AssertionError on anything the module's load rules would refuse)"""
    errs = file_checks(b)
    assert not errs, '; '.join(errs)
    h = dict(zip(('magic', 'version', 'header_size', 'row_size', 'row_count', 'rows_off', 'item_owner_off',
                  'item_lo', 'item_count', 'item_fx_off', 'item_fx_count', 'flagmap_off', 'flag_lo', 'flag_bits',
                  'aux_off', 'aux_size', 'strings_off', 'strings_size', 'sum', 'min_engine_version'),
                 struct.unpack_from(HDR_FMT, b, 0)))
    strings = b[h['strings_off']:h['strings_off'] + h['strings_size']]
    rows = []
    for i in range(h['row_count']):
        v = struct.unpack_from(ROW_FMT, b, h['rows_off'] + i * h['row_size'])
        ko = v[24]
        rows.append(dict(owner=v[0], row_flags=v[1], features=feat_names(v[2]), panel_tex=list(v[3:6]),
                         panel_sprite=v[6], name_index=v[7], record_slot=v[8], museum_record=v[9], pic_slot=v[10],
                         pic_slot_party=v[11], party_frame=v[12], setup_frame=v[13], oq_name=v[14],
                         oq_face_pic=v[15], oq_face_layout=v[16], oq_banner=v[17], oq_row=list(v[18:21]),
                         burst_ctl=v[21], ex_run_mult=v[23], key=strings[ko:strings.index(b'\0', ko)].decode('ascii'),
                         params=unpack_params(v[25])))
    io = b[h['item_owner_off']:h['item_owner_off'] + h['item_count']]
    items = {h['item_lo'] + k: o for k, o in enumerate(io) if o}
    fx = []
    for k in range(h['item_fx_count']):
        it, ef, _, value = struct.unpack_from('<HBBf', b, h['item_fx_off'] + 8 * k)
        fx.append(dict(item=it, effect={v: n for n, v in EFFECTS.items()}[ef], value=value))
    fm = b[h['flagmap_off']:h['flagmap_off'] + (h['flag_bits'] + 7) // 8]
    flags = [h['flag_lo'] + i for i in range(h['flag_bits']) if fm[i >> 3] >> (i & 7) & 1]
    h['magic'] = h['magic'].decode('ascii')
    return dict(header=h, rows=rows, item_owner=items, item_fx=fx, gate_flags=flags)


def file_checks(b):
    """the module's load rules (ENGINE.md P2.1 section 6) on raw bytes -> list of errors"""
    e = []
    if len(b) < HEADER:
        return ['file shorter than the header']
    h = struct.unpack_from(HDR_FMT, b, 0)
    (magic, ver, hsz, rsz, rcnt, rows_off, io_off, item_lo, item_cnt, fx_off, fx_cnt, fm_off, flag_lo, flag_bits,
     aux_off, aux_sz, st_off, st_sz, total, min_eng) = h
    if magic != MAGIC:
        e.append('bad magic %r' % magic)
    if ver != VERSION:
        e.append('version %d != %d' % (ver, VERSION))
    if hsz < HEADER or rsz < ROW or rcnt > MAX_ROWS:
        e.append('header/row size or row count out of range (%d, %d, %d)' % (hsz, rsz, rcnt))
    for name, o, n in (('rows', rows_off, rsz * rcnt), ('item_owner', io_off, item_cnt), ('item_fx', fx_off, 8 * fx_cnt),
                       ('flagmap', fm_off, (flag_bits + 7) // 8), ('aux', aux_off, aux_sz), ('strings', st_off, st_sz)):
        if o < hsz or o + n > len(b):
            e.append('section %s outside the file (0x%x + %d)' % (name, o, n))
    if len(b) % 4:
        e.append('file size not a multiple of 4')
    else:
        body = b[hsz:]
        s = sum(struct.unpack('<%dI' % (len(body) // 4), body)) & 0xFFFFFFFF
        if s != total:
            e.append('sum 0x%08x != header 0x%08x' % (s, total))
    if min_eng > MIN_ENGINE:
        e.append('needs engine 0x%08x' % min_eng)
    if e:
        return e
    last = 0
    for i in range(rcnt):
        v = struct.unpack_from(ROW_FMT, b, rows_off + i * rsz)
        own, rflags, feat, bctl, ko = v[0], v[1], v[2], v[21], v[24]
        if not 33 <= own <= 63 or own <= last:
            e.append('row %d: owner %d not ascending/unique in 33..63' % (i, own))
        last = own
        if not rflags & 1:
            e.append('row %d: valid bit clear' % i)
        if feat & ~FEAT_MASK:
            e.append('row %d: unknown feature bits 0x%x' % (i, feat & ~FEAT_MASK))
        if bctl not in (BURST_CHRP, BURST_MODULE0):
            e.append('row %d: burst_ctl 0x%x' % (i, bctl))
        if ko >= st_sz or b'\0' not in b[st_off + ko:st_off + st_sz]:
            e.append('row %d: key string outside the strings section' % i)
    return e


# ---------------------------------------------------------------- validator (sources)
def load_flag_map():
    if not os.path.exists(FLAG_MAP):
        return None
    d = json.load(open(FLAG_MAP))
    return d


def is_free(fmap, n):
    return any(a <= n <= b for a, b in fmap['free_ranges'])


def code_writers(fmap, n):
    return [u for u in fmap['flags'].get(str(n)) or [] if 'W' in u['kind'] and u['site'].startswith('code')]


def validate(pkgs, disc=None):
    """-> (errors, warnings); checks list in notes/dlc-phase2.md 'P2.2 registry builder'"""
    E, W = [], []
    rows = [p['row'] for p in pkgs]
    # V1 owners
    owners = [r['owner'] for r in rows]
    for p in pkgs:
        o = p['row']['owner']
        if not isinstance(o, int) or not 33 <= o <= 63:
            E.append('%s: owner %r outside 33..63' % (p['package'], o))
        elif o > 35:
            W.append('%s: owner %d > 35 needs the save-format work of P2.5' % (p['package'], o))
    if len(set(owners)) != len(owners):
        E.append('duplicate owners %s' % owners)
    if len(pkgs) > MAX_ROWS:
        E.append('%d packages > %d rows' % (len(pkgs), MAX_ROWS))
    for p in pkgs:
        r, n = p['row'], p['package']
        # V2 field ranges
        for f in U16_FIELDS:
            if not isinstance(r[f], int) or not 0 <= r[f] <= 0xFFFF:
                E.append('%s: %s %r not u16' % (n, f, r[f]))
        for f in ('panel_tex', 'oq_row'):
            if len(r[f]) != 3 or not all(isinstance(x, int) and 0 <= x <= 0xFFFF for x in r[f]):
                E.append('%s: %s %r not 3 x u16' % (n, f, r[f]))
        for f in ('record_slot', 'museum_record'):
            if not isinstance(r[f], int) or not 0 <= r[f] <= 0xFF:
                E.append('%s: %s %r not u8' % (n, f, r[f]))
        # V3 features vs fields
        unknown = [f for f in r['features'] if f not in FEATURES]
        if unknown:
            E.append('%s: unknown features %s' % (n, unknown))
        fs = set(r['features'])
        if ('EX_RUN' in fs) != (r['ex_run_mult'] != 0):
            E.append('%s: EX_RUN feature and ex_run_mult %r disagree' % (n, r['ex_run_mult']))
        if r['ex_run_mult'] and not 1.0 <= r['ex_run_mult'] <= 3.0:
            E.append('%s: ex_run_mult %r outside 1.0..3.0' % (n, r['ex_run_mult']))
        if r['burst_ctl'] not in (BURST_CHRP, BURST_MODULE0):
            E.append('%s: burst_ctl %r not 0xFF (chrp) / 0x80 (module TRI)' % (n, r['burst_ctl']))
        if ('BURST_MODULE' in fs) != (r['burst_ctl'] == BURST_MODULE0):
            E.append('%s: BURST_MODULE feature and burst_ctl 0x%x disagree' % (n, r['burst_ctl']))
        if ('RECORD_SLOT' in fs) != (r['record_slot'] != 0):
            E.append('%s: RECORD_SLOT feature and record_slot %r disagree' % (n, r['record_slot']))
        if ('ITEM_OWNER' in fs) != bool(p['items']):
            E.append('%s: ITEM_OWNER feature and owned items %s disagree' % (n, p['items']))
        if ('ITEM_EFFECTS' in fs) != bool(p['fx']):
            E.append('%s: ITEM_EFFECTS feature and item effects disagree' % n)
        if fs & BEHAVIOUR and r['params'].get('layout') != 'behaviours-v1':
            E.append('%s: behaviour features %s need params layout behaviours-v1' % (n, sorted(fs & BEHAVIOUR)))
        if r['params'].get('layout') == 'behaviours-v1':
            pr = r['params']
            if len(pr['items']) > 4 or not set(pr['items']) <= set(p['items']):
                E.append('%s: params items %s not among owned items' % (n, pr['items']))
            if not (0 <= pr['voice_bar'] <= 255 and 0 <= pr['voice_reflect'] <= 255 and 0 < pr['shield_pct'] <= 0xFFFF
                    and 0.1 <= pr['crown_drain'] <= 1.0):
                E.append('%s: params out of range %s' % (n, pr))
        # V4 key
        if not re.fullmatch(r'[a-z0-9]{6}', r['key']):
            E.append('%s: key %r is not 6 x [a-z0-9]' % (n, r['key']))
        # V5 Original Quest consistency (pictures derive from pic_slot)
        ps = r['pic_slot']
        if r['pic_slot_party'] != ps + 1:
            E.append('%s: pic_slot_party %d != pic_slot + 1 (%d)' % (n, r['pic_slot_party'], ps + 1))
        if r['oq_face_pic'] != OQ_ICON + ps:
            E.append('%s: oq_face_pic %d != OQ icon base + pic_slot (%d)' % (n, r['oq_face_pic'], OQ_ICON + ps))
        if list(r['oq_row']) != [OQ_FACE_R + ps, OQ_FACE + ps, OQ_NAME + ps]:
            E.append('%s: oq_row %s != OQ bases + pic_slot %s' % (n, r['oq_row'], [OQ_FACE_R + ps, OQ_FACE + ps, OQ_NAME + ps]))
        if r['oq_banner'] != r['oq_row'][0]:
            E.append('%s: oq_banner %d != oq_row face_r %d' % (n, r['oq_banner'], r['oq_row'][0]))
        if r['oq_face_layout'] != OQ_LAYOUT:
            E.append('%s: oq_face_layout 0x%x != owner-icon layout 0x%x' % (n, r['oq_face_layout'], OQ_LAYOUT))
        # V6 install-time id rules
        ids = p['install'].get('objentry_ids', [])
        if r['owner'] == 34 and any(i >= OBJENTRY_COSMOS for i in ids):
            E.append('%s: owner 34 objentry ids %s must be < %d (Cosmos rows)' % (n, ids, OBJENTRY_COSMOS))
        for it in p['items']:
            if not 0 <= it < ITEM_CEILING:
                E.append('%s: item %d >= item ceiling %d (P2.7 must raise it first)' % (n, it, ITEM_CEILING))
        for f in p['fx']:
            if f['effect'] not in EFFECTS:
                E.append('%s: unknown item effect %r' % (n, f['effect']))
            if f['item'] not in p['items']:
                E.append('%s: effect on item %d that the package does not own' % (n, f['item']))
    # V7 uniqueness across packages
    for f, lo in (('name_index', 63), ('oq_name', 122), ('museum_record', 34), ('pic_slot', 245)):
        vs = [r[f] for r in rows]
        if len(set(vs)) != len(vs):
            E.append('duplicate %s %s' % (f, vs))
        for r in rows:
            if r[f] < lo:
                E.append('owner %d: %s %d < %d (vanilla range)' % (r['owner'], f, r[f], lo))
    keys = [r['key'] for r in rows]
    if len(set(keys)) != len(keys):
        E.append('duplicate keys %s' % keys)
    tci = [p['install'].get('title_call_index') for p in pkgs if p['install'].get('title_call_index') is not None]
    if len(set(tci)) != len(tci):
        E.append('duplicate title_call_index %s' % tci)
    for what, getter in (('item', lambda p: p['items']), ('objentry id', lambda p: p['install'].get('objentry_ids', []))):
        seen = {}
        for p in pkgs:
            for x in getter(p):
                if x in seen:
                    E.append('%s %d used by %s and %s' % (what, x, seen[x], p['package']))
                seen[x] = p['package']
    # V8 record slots: 24, 23, ... contiguous; friend-card limit = 25 - slots
    slots = sorted((r['record_slot'] for r in rows if r['record_slot']), reverse=True)
    if len(set(slots)) != len(slots):
        E.append('duplicate record_slot %s' % slots)
    elif slots and slots != list(range(FRIEND_CARDS - 1, FRIEND_CARDS - 1 - len(slots), -1)):
        E.append('record slots %s must be 24, 23, ... (contiguous from the top friend card)' % slots)
    if FRIEND_CARDS - len(slots) < 1:
        E.append('no friend cards left')
    # V9 OQ face-handle capacity
    oqf = [r['owner'] for r in rows if 'OQ_FACE' in r['features']]
    if len(oqf) > OQ_EXTRA_FACES:
        E.append('OQ_FACE on owners %s: the OQ face-handle list has room for %d extra pair (P2.7)' % (oqf, OQ_EXTRA_FACES))
    # V10 flags (P2.6 map)
    fmap = load_flag_map()
    seen = {}
    for p in pkgs:
        for f in p['flags']:
            fl = f['flag']
            if fl in seen:
                E.append('flag %d used by %s and %s' % (fl, seen[fl], p['package']))
            seen[fl] = p['package']
            if not 0 <= fl <= 5119:
                E.append('%s: flag %d outside the save flag space 0..5119' % (p['package'], fl))
                continue
            if fmap is None:
                continue
            if is_free(fmap, fl):
                continue
            cw = code_writers(fmap, fl)
            users = fmap['flags'].get(str(fl)) or []
            if f.get('reuse_vanilla') and not cw:
                W.append('%s: flag %d reuses a vanilla flag (%s); vanilla users: %s' % (
                    p['package'], fl, f['reuse_vanilla'], ', '.join(u['site'] for u in users[:3])))
            else:
                E.append('%s: flag %d is not free%s; users: %s' % (
                    p['package'], fl, ' and the game CODE writes it' if cw else '',
                    ', '.join('%s %s' % (u['kind'], u['site']) for u in users[:4])))
    if fmap is None:
        W.append('no tools/dlc/flag_map.json (P2.6): flags not checked against vanilla users')
    # V11 disc checks (read-only)
    if disc:
        de, dw = disc_checks(pkgs, disc)
        E += de
        W += dw
    return E, W


def disc_checks(pkgs, disc):
    """names and pictures must exist in the packs of a layout-A/R disc (placeholder packages: warnings only)"""
    sys.path.insert(0, SCRIPTS)
    sys.dont_write_bytecode = True
    from comb_patch import use_iso, pkg_offset, read_at  # noqa: E402
    from voice_text import KEY  # noqa: E402
    import spot33_menuart as MA  # noqa: E402  (scene picture runs)
    import spot33_oqslot as OQ  # noqa: E402  (full-name groups)
    import spot33_ownername as ON  # noqa: E402  (name-list groups)
    use_iso(disc)
    cache = {}

    def get(path):
        if path not in cache:
            try:
                st, sz = pkg_offset(path)
                with open(disc, 'rb') as f:
                    cache[path] = read_at(f, st, sz)
            except Exception as ex:                   # missing from this disc's index
                cache[path] = ex
        return cache[path]

    def group(path, gi):
        d = get(path)
        if isinstance(d, Exception) or d[:8] != b'mess pak':
            return None
        go, gs = struct.unpack_from('<II', d, 0x10 + 8 * gi)
        g = d[go:go + gs]
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

    def pic_ok(packs, pid):
        for path in packs:
            b = get(path)
            if isinstance(b, Exception):
                continue
            cnt, base = struct.unpack_from('<HH', b, 0x0A)
            if base <= pid < base + cnt and struct.unpack_from('<II', b, 0x10 + 8 * (pid - base))[1] > 0:
                return True
        return False

    E, W = [], []
    for p in pkgs:
        r, n = p['row'], p['package']
        out = W if p['placeholder'] else E
        for texts, idx, what in ((ON.TEXTS, r['name_index'], 'name_index'), (OQ.TEXTS, r['oq_name'], 'oq_name')):
            for path, gi in texts.items():
                raws = group(path, gi)
                if raws is None:
                    W.append('%s: %s group %d unreadable on this disc' % (n, path, gi))
                elif idx >= len(raws) or raws[idx] is None:
                    out.append('%s: %s %d missing in %s group %d (%d entries)' % (n, what, idx, path, gi, len(raws)))
        for scene, (_, packs, _, bases) in MA.SCENES.items():
            for tag, base in bases.items():
                if tag in ('logo', 'art'):             # logo = base + 148, art = portrait: not registry fields
                    continue
                if not pic_ok(packs, base + r['pic_slot']):
                    out.append('%s: picture %s/%s %d (base 0x%x + %d) missing on the disc' % (
                        n, scene, tag, base + r['pic_slot'], base, r['pic_slot']))
    return E, W


# ---------------------------------------------------------------- CLI
def report(E, W):
    for w in W:
        print('  WARN  %s' % w)
    for e in E:
        print('  ERROR %s' % e)
    print('  %d error(s), %d warning(s)' % (len(E), len(W)))


def selftest(disc=None):
    ok = True
    sora = load_source(os.path.join(REGDIR, 'sora.json'))
    t34 = load_source(os.path.join(REGDIR, 'test34.json'))
    for name, pk in (('sora', [sora]), ('sora+test34', [sora, t34])):
        E, W = validate(pk, disc)
        b = build(pk)
        d = decode(b)
        # round trip: decoded rows -> sources -> bytes again
        back = []
        for row in d['rows']:
            src = next(p for p in pk if p['row']['owner'] == row['owner'])
            r2 = dict(row)
            for k in ('row_flags',):
                r2.pop(k)
            back.append(dict(src, row=r2, items=[i for i, o in d['item_owner'].items() if o == row['owner']],
                             fx=[f for f in d['item_fx'] if d['item_owner'].get(f['item']) == row['owner']]))
        same = build(back) == b
        print('%-12s EXTRA.REG %d B, rows %d, errors %d, warnings %d, round trip %s' % (
            name, len(b), len(d['rows']), len(E), len(W), 'OK' if same else 'MISMATCH'))
        ok &= same and not E
        for e in E:
            print('   ERROR', e)
    cases = json.load(open(os.path.join(REGDIR, 'tests', 'cases.json')))
    for c in cases['cases']:
        srcs = {'sora': json.load(open(os.path.join(REGDIR, 'sora.json'))),
                'test34': json.load(open(os.path.join(REGDIR, 'test34.json')))}
        for pkg, path, value in c['set']:
            node = srcs[pkg]
            keys = path.split('.')
            for k in keys[:-1]:
                node = node[int(k)] if isinstance(node, list) else node[k]
            last = keys[-1]
            if isinstance(node, list):
                node[int(last)] = value
            elif isinstance(node.get(last), list) and len(node[last]) == 2 and isinstance(node[last][1], str):
                node[last] = [value, 'test case']      # sourced pair: replace the value, keep the shape
            else:
                node[last] = value
        pk = [load_source(srcs[x]) for x in c['packages']]
        E, _ = validate(pk)
        hit = any(c['expect'] in e for e in E)
        print('case %-34s %s' % (c['name'], 'caught' if hit else 'MISSED (errors: %s)' % E))
        ok &= hit
    # file-level rules on a corrupted file
    b = bytearray(build([sora, t34]))
    b[-1] ^= 1
    ferr = file_checks(bytes(b))
    print('case %-34s %s' % ('file: corrupted byte -> sum', 'caught' if any('sum' in e for e in ferr) else 'MISSED'))
    ok &= any('sum' in e for e in ferr)
    print('SELFTEST', 'PASS' if ok else 'FAIL')
    return ok


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a.pop(0)
    disc = None
    if '--disc' in a:
        i = a.index('--disc')
        disc = a[i + 1]
        del a[i:i + 2]
    dry = '--dry' in a
    a = [x for x in a if x != '--dry']
    out = None
    if '-o' in a:
        i = a.index('-o')
        out = a[i + 1]
        del a[i:i + 2]
    if cmd == 'selftest':
        sys.exit(0 if selftest(disc) else 1)
    if cmd == 'decode':
        d = decode(open(a[0], 'rb').read())
        s = json.dumps(d, indent=1)
        if out and not dry:
            open(out, 'w').write(s + '\n')
            print('wrote', out)
        else:
            print(s)
        return
    pkgs = [load_source(x) for x in a]
    E, W = validate(pkgs, disc)
    print('validate %s%s' % (' + '.join(p['package'] for p in pkgs), ' (disc %s)' % os.path.basename(disc) if disc else ''))
    report(E, W)
    if cmd == 'validate':
        sys.exit(1 if E else 0)
    if cmd != 'build':
        sys.exit('unknown command %s' % cmd)
    if E:
        sys.exit('not building: %d error(s)' % len(E))
    b = build(pkgs)
    decode(b)                                   # must pass the module's load rules
    print('EXTRA.REG %d bytes (%d rows)' % (len(b), len(pkgs)))
    if dry or not out:
        print('(dry: nothing written)' if dry else '(no -o: nothing written)')
        return
    open(out, 'wb').write(b)
    print('wrote', out)


if __name__ == '__main__':
    main()
