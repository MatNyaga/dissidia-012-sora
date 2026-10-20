"""Log every battle-end win scene (FUN_08b0a090): the side flag (task +0xC) that picks motion 1200 (_910A) or
1210 (_911A), and the owner of both fighters. Pauses the game for a split second per hit.
Usage: python3 -I ppwinwatch.py PORT SECONDS
"""
import base64
import json
import struct
import sys
import time

import websocket

ADDR = 0x08B0A090


def wait(ws, ev):
    while True:
        r = json.loads(ws.recv())
        if r.get('event') in (ev, 'error'):
            return r


def read(ws, addr, size):
    ws.send(json.dumps({'event': 'memory.read', 'address': addr, 'size': size}))
    m = wait(ws, 'memory.read')
    return base64.b64decode(m.get('base64', ''))


def owner(ws, fighter):
    if not 0x08800000 <= fighter < 0x0A000000:
        return -1
    obj = struct.unpack('<I', read(ws, fighter + 0x2F8, 4))[0]
    return read(ws, obj + 6, 1)[0] if 0x08800000 <= obj < 0x0A000000 else -1


def main():
    port, secs = sys.argv[1], float(sys.argv[2])
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=5, suppress_origin=True)
    ws.send(json.dumps({'event': 'cpu.breakpoint.add', 'address': ADDR, 'enabled': True}))
    end = time.time() + secs
    print('watching win scenes for %d s' % secs, flush=True)
    try:
        while time.time() < end:
            try:
                r = json.loads(ws.recv())
            except websocket.WebSocketTimeoutException:
                continue
            if r.get('event') != 'cpu.stepping':
                continue
            ws.send(json.dumps({'event': 'cpu.getAllRegs'}))
            g = wait(ws, 'cpu.getAllRegs')
            reg = dict(zip(g['categories'][0]['registerNames'], g['categories'][0]['uintValues']))
            task = read(ws, reg['a0'], 0x40)
            w = struct.unpack('<16I', task)
            flag = task[0xC]
            f8, f9 = w[8], w[9]
            print('%s win scene: flag=%d -> motion %s; fighter[8] owner %d, fighter[9] owner %d; task %s' % (
                time.strftime('%H:%M:%S'), flag, '1200 (_910A)' if flag == 1 else '1210 (_911A)',
                owner(ws, f8), owner(ws, f9), task.hex()), flush=True)
            ws.send(json.dumps({'event': 'cpu.resume'}))
    finally:
        ws.send(json.dumps({'event': 'cpu.breakpoint.remove', 'address': ADDR}))
        ws.send(json.dumps({'event': 'cpu.resume'}))
        time.sleep(0.5)


if __name__ == '__main__':
    main()
