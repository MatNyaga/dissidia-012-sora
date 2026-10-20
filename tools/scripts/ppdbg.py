"""Tiny client for PPSSPP's remote debugger (Settings > Tools > Developer tools > Allow remote debugger).

Usage: python3 -I ppdbg.py PORT read ADDR SIZE        hex dump of game memory
       python3 -I ppdbg.py PORT u32 ADDR [COUNT]       signed 32-bit values
       python3 -I ppdbg.py PORT status
"""
import base64
import json
import struct
import sys

import websocket


def call(ws, event, **args):
    ws.send(json.dumps(dict(event=event, **args)))
    while True:
        r = json.loads(ws.recv())
        if r.get('event') == event or r.get('event') == 'error':
            return r


def read(ws, addr, size):
    r = call(ws, 'memory.read', address=addr, size=size)
    if 'base64' not in r:
        sys.exit(str(r))
    return base64.b64decode(r['base64'])


def main():
    port, cmd = sys.argv[1], sys.argv[2]
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=90, suppress_origin=True)
    if cmd == 'status':
        print(call(ws, 'game.status'))
    elif cmd == 'read':
        addr, size = int(sys.argv[3], 0), int(sys.argv[4], 0)
        b = read(ws, addr, size)
        for k in range(0, len(b), 16):
            print('%08x  %s' % (addr + k, b[k:k + 16].hex(' ')))
    elif cmd == 'u32':
        addr = int(sys.argv[3], 0)
        n = int(sys.argv[4], 0) if len(sys.argv) > 4 else 1
        print(list(struct.unpack('<%di' % n, read(ws, addr, 4 * n))))


if __name__ == '__main__':
    main()
