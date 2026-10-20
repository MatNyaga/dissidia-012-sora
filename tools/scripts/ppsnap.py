"""Save all PSP user RAM (0x08800000-0x0A000000) from PPSSPP's remote debugger to a file.
Usage: python3 -I ppsnap.py PORT OUTFILE
"""
import json
import sys

import websocket

sys.path.insert(0, __import__('os').path.dirname(__file__))
from ppdbg import read  # noqa: E402


def main():
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % sys.argv[1], timeout=60, suppress_origin=True)
    ws.send(json.dumps({'event': 'cpu.breakpoint.list'}))
    while True:
        r = json.loads(ws.recv())
        if r.get('event') == 'cpu.breakpoint.list':
            break
    for b in r.get('breakpoints', []):
        ws.send(json.dumps({'event': 'cpu.breakpoint.remove', 'address': b['address']}))
    with open(sys.argv[2], 'wb') as out:
        for a in range(0x08800000, 0x0A000000, 0x100000):
            out.write(read(ws, a, 0x100000))
    print('saved', sys.argv[2])


if __name__ == '__main__':
    main()
