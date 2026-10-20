"""Log which functions run: sets PPSSPP breakpoints, records each hit (pc, ra, a0-a3), resumes at once.
Usage: python3 -I ppwatch.py PORT SECONDS ADDR [ADDR ...]
"""
import json
import sys
import time

import websocket


def main():
    port, secs = sys.argv[1], float(sys.argv[2])
    addrs = [int(a, 0) for a in sys.argv[3:]]
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=5, suppress_origin=True)
    for a in addrs:
        ws.send(json.dumps({'event': 'cpu.breakpoint.add', 'address': a, 'enabled': True}))
    hits = {}
    end = time.time() + secs
    try:
        while time.time() < end:
            try:
                r = json.loads(ws.recv())
            except websocket.WebSocketTimeoutException:
                continue
            if r.get('event') == 'cpu.stepping':
                ws.send(json.dumps({'event': 'cpu.getAllRegs'}))
                while True:
                    g = json.loads(ws.recv())
                    if g.get('event') == 'cpu.getAllRegs':
                        break
                gpr = g['categories'][0]['uintValues']
                names = g['categories'][0]['registerNames']
                reg = dict(zip(names, gpr))
                pc = r.get('pc', reg.get('pc'))
                key = pc
                hits[key] = hits.get(key, 0) + 1
                if hits[key] <= 3:
                    print('hit %08x ra=%08x a0=%08x a1=%08x a2=%08x a3=%08x' % (
                        pc, reg['ra'], reg['a0'], reg['a1'], reg['a2'], reg['a3']), flush=True)
                ws.send(json.dumps({'event': 'cpu.resume'}))
    finally:
        for a in addrs:
            ws.send(json.dumps({'event': 'cpu.breakpoint.remove', 'address': a}))
        ws.send(json.dumps({'event': 'cpu.resume'}))
        time.sleep(0.5)
        print('totals:', {('%08x' % k): v for k, v in hits.items()}, flush=True)


if __name__ == '__main__':
    main()
