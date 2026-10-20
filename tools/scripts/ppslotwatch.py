"""Which sound-bank slot plays for which move: memory breakpoint (read) on an SSCF bank's entry table while
pressing moves on a timetable. Each hit: decode the load instruction at pc -> address -> slot = (addr-table)/32.

Usage: python3 -I ppslotwatch.py PORT BANK_ADDR COUNT OUT.json [PC]  (in battle, nobody touching the controls)
       PC given: CPU breakpoint there instead (one stop per sound; 0x08991A70 = "lw a0,0x8(s0)" in the play code)
       Find BANK_ADDR by searching RAM for "SSCF" (#33's fighter bank: size 0x52DB0, 70 sounds).
"""
import json
import struct
import sys
import time

import websocket

sys.path.insert(0, __import__('os').path.dirname(__file__))
from ppsound_map import MOVES  # noqa: E402

GAP = 3.5
REGS = ('zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 '
        's0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra').split()


def call(ws, event, **kw):
    ws.send(json.dumps(dict(event=event, **kw)))
    while True:
        r = json.loads(ws.recv())
        if r.get('event') in (event, 'error'):
            return r


def main():
    port, bank, count, out = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3]), sys.argv[4]
    table, size = bank + 0x20, count * 32
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=40, suppress_origin=True)
    ws.settimeout(0.05)
    bp_pc = int(sys.argv[5], 0) if len(sys.argv) > 5 else None
    if bp_pc:
        ws.send(json.dumps({'event': 'cpu.breakpoint.add', 'address': bp_pc, 'enabled': True}))
    else:
        ws.send(json.dumps({'event': 'memory.breakpoint.add', 'address': table, 'size': size,
                            'read': True, 'write': False, 'change': False, 'enabled': True}))
    plan, t = [], 1.5
    for _ in range(2):
        for label, seq in MOVES:
            plan.append((t, label, None))
            dt = 0
            for button, frames, after in seq:
                plan.append((t + dt, None, (button, frames)))
                dt += after
            t += GAP
    end = t + 1
    t0 = time.time()
    events, k = [], 0
    try:
        while time.time() - t0 < end:
            now = time.time() - t0
            while k < len(plan) and plan[k][0] <= now:
                _, label, press = plan[k]
                if label:
                    events.append({'t': round(now, 3), 'move': label})
                else:
                    ws.send(json.dumps({'event': 'input.buttons.press', 'button': press[0], 'duration': press[1]}))
                k += 1
            try:
                r = json.loads(ws.recv())
            except websocket.WebSocketTimeoutException:
                continue
            if r.get('event') != 'cpu.stepping':
                continue
            ws.settimeout(10)
            g = call(ws, 'cpu.getAllRegs')
            cat = g['categories'][0]
            reg = dict(zip(cat['registerNames'], cat['uintValues']))
            pc = r.get('pc') or reg.get('pc')
            # PPSSPP stops AFTER the access; the reading code (FUN_0899xxxx) keeps the entry pointer in s0
            s0 = reg.get('s0', 0)
            slot = (s0 - table) // 32 if table <= s0 < table + size else None
            events.append({'t': round(time.time() - t0, 3), 'pc': hex(pc), 'slot': slot})
            ws.send(json.dumps({'event': 'cpu.resume'}))
            ws.settimeout(0.05)
    finally:
        ws.settimeout(10)
        if bp_pc:
            ws.send(json.dumps({'event': 'cpu.breakpoint.remove', 'address': bp_pc}))
        else:
            ws.send(json.dumps({'event': 'memory.breakpoint.remove', 'address': table, 'size': size}))
        ws.send(json.dumps({'event': 'cpu.resume'}))
        time.sleep(0.5)
    json.dump(events, open(out, 'w'), indent=0)
    move = None
    summary = {}
    for e in events:
        if 'move' in e:
            move = '%5.1f %s' % (e['t'], e['move'])
            summary[move] = []
        elif move and e['slot'] is not None and e['slot'] not in summary[move]:
            summary[move].append(e['slot'])
    for mv, slots in summary.items():
        print(mv, slots)
    line, last = [], None
    for e in events:
        if 'move' in e:
            line.append('\n%5.1f %-28s:' % (e['t'], e['move']))
        elif e['slot'] is not None:
            line.append(' %d@%.1f' % (e['slot'], e['t']))
    print(''.join(line))
    print('hits:', sum(1 for e in events if 'pc' in e), 'pcs:', sorted({e['pc'] for e in events if 'pc' in e}))


if __name__ == '__main__':
    main()
