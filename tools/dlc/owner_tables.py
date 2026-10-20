"""Reader for tools/dlc/owner_tables.json (P0.8 registry spec). Read-only; never touches an ISO.

  python3 -I tools/dlc/owner_tables.py --owner 34        checklist: what a NEW fighter on owner 34 needs, per table
  python3 -I tools/dlc/owner_tables.py --summary         counts by kind / Phase-2 target / category / need type
  python3 -I tools/dlc/owner_tables.py --list            one line per entry (id, kind, target, where)
  python3 -I tools/dlc/owner_tables.py --show ID         every field of one entry
Filters for --owner / --list: --kind KIND, --target TEXT (substring of phase2_target), --category CAT.

Status words in --owner:
  SORA     owner 33 = already done for Sora (script named)
  CODE     the table/site serves owners only up to N with data (owner_max_data_only) -> needs code/relocation first
  FULL     no free row today (capacity.free_rows == 0) -> relocation / bigger buffer first
  ALLOC    the installer must allocate ids/flags/numbers
  DATA     a data row (or registry field) is enough
  -        nothing per fighter
"""
import argparse
import collections
import json
import os
import signal
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(HERE, 'owner_tables.json')


def load(path):
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    ids = [t['id'] for t in d['tables']]
    dup = [i for i, n in collections.Counter(ids).items() if n > 1]
    if dup:
        sys.exit('duplicate ids in %s: %s' % (path, dup))
    return d


def keep(t, a):
    if a.kind and t['kind'] != a.kind:
        return False
    if a.target and a.target.lower() not in t['phase2_target'].lower():
        return False
    if a.category and t['category'] != a.category:
        return False
    return True


def status(t, owner):
    types = t['new_fighter']['type']
    if owner == 33 and t['sora_today']['scripts']:
        return 'SORA'
    mx = t.get('owner_max_data_only')
    if mx is not None and owner > mx:
        return 'CODE'
    if t['capacity'].get('free_rows') == 0:
        return 'FULL'
    if mx is None and 'code generalisation' in types and t['category'] == 'table':
        return 'CODE'
    if 'id allocation' in types:
        return 'ALLOC'
    if types:
        return 'DATA'
    return '-'


ORDER = ['CODE', 'FULL', 'ALLOC', 'DATA', 'SORA', '-']


def checklist(d, a):
    owner = a.owner
    rows = [(status(t, owner), t) for t in d['tables'] if keep(t, a)]
    print('Checklist for a new fighter on owner %d (%d entries from %s)' % (owner, len(rows), os.path.relpath(a.json)))
    if owner > 255 or owner < 1:
        print('  !! owner is a byte everywhere (1..255)')
    if owner > 63:
        print('  !! owner > 63: no bit in the 64-bit BGM owner mask')
    if owner > 35:
        print('  !! owner > 35: save stats blocks have no room (save relocation)')
    print('  legend: CODE = code/relocation first, FULL = no free row, ALLOC = allocate ids, DATA = rows only, SORA = done for 33')
    for st in ORDER:
        grp = [t for s, t in rows if s == st]
        if not grp:
            continue
        print('\n== %s (%d)' % (st, len(grp)))
        for t in grp:
            print('  [%s] %s  <%s, %s>' % (st, t['name'], t['kind'], t['phase2_target']))
            print('        where : %s' % t['where'])
            if st == 'SORA':
                print('        today : %s  (%s)' % (t['sora_today']['what'], ', '.join(t['sora_today']['scripts'])))
            else:
                print('        needs : %s' % t['new_fighter']['needs'])
            cap = t['capacity']
            if any(v is not None for v in cap.values()):
                print('        room  : max %s, used %s, free %s' % (cap['max_rows'], cap['used_rows'], cap['free_rows']))
            if t.get('covers'):
                print('        covers: %s (data-only up to owner %s)' % (t['covers'], t.get('owner_max_data_only')))
            if owner == 34 and t.get('owner34'):
                print('        P0.4  : %s' % t['owner34'])
            if t.get('notes'):
                print('        note  : %s' % t['notes'])
    cnt = collections.Counter(s for s, _ in rows)
    print('\nTotals: ' + ', '.join('%s %d' % (s, cnt[s]) for s in ORDER if cnt[s]))


def summary(d, a):
    T = [t for t in d['tables'] if keep(t, a)]
    print('%d entries in %s' % (len(T), os.path.relpath(a.json)))
    for title, key in (('kind', lambda t: [t['kind']]), ('phase2_target', lambda t: [t['phase2_target']]),
                       ('category', lambda t: [t['category']]), ('new_fighter.type', lambda t: t['new_fighter']['type'] or ['(nothing)'])):
        c = collections.Counter(v for t in T for v in key(t))
        print('\nby %s:' % title)
        for k, n in c.most_common():
            print('  %4d  %s' % (n, k))
    m = collections.Counter((t['kind'], t['phase2_target']) for t in T)
    print('\nkind x target:')
    for (k, tg), n in sorted(m.items()):
        print('  %4d  %-10s -> %s' % (n, k, tg))
    scripts = sorted({s.split(' ')[0] for t in T for s in t['sora_today']['scripts']})
    print('\nscripts referenced: %d' % len(scripts))


def listing(d, a):
    for t in d['tables']:
        if keep(t, a):
            print('%-26s %-10s %-24s %s' % (t['id'], t['kind'], t['phase2_target'], t['where'][:90]))


def show(d, ident):
    for t in d['tables']:
        if t['id'] == ident:
            print(json.dumps(t, indent=1, ensure_ascii=False))
            return
    sys.exit('no entry %r (try --list)' % ident)


def main():
    if hasattr(signal, 'SIGPIPE'):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)   # quiet when piped into head
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--json', default=DEFAULT)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--owner', type=int)
    g.add_argument('--summary', action='store_true')
    g.add_argument('--list', action='store_true')
    g.add_argument('--show')
    ap.add_argument('--kind')
    ap.add_argument('--target')
    ap.add_argument('--category')
    a = ap.parse_args()
    d = load(a.json)
    if a.owner is not None:
        checklist(d, a)
    elif a.summary:
        summary(d, a)
    elif a.list:
        listing(d, a)
    else:
        show(d, a.show)


if __name__ == '__main__':
    main()
