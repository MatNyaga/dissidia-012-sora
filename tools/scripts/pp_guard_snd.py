"""Guard sound check: log every call of the play-sound function 0x088a24d4 (a1 = absolute sound id) while Sora guards
3x outside EX Mode and 3x in EX Mode. No memory reads while the breakpoint is on (log flood). python3 -I tools/scripts/pp_guard_snd.py FIGHTER_HEX  (player fighter address, e.g. from ppexburst candidates)"""
import base64, json, struct, sys, threading, time
import websocket
fs = int(sys.argv[1], 16)
ws = websocket.create_connection('ws://127.0.0.1:41335/debugger', timeout=30, suppress_origin=True)
lock = threading.Lock(); logs = []; replies = {}; t0 = time.time(); stop = []
def rx():
    while not stop:
        try: r = json.loads(ws.recv())
        except Exception: continue
        if r.get('event') == 'log': logs.append((time.time() - t0, r.get('message', '').strip()))
        else: replies.setdefault(r.get('event'), []).append(r)
def call(ev, **a):
    replies.pop(ev, None); ws.send(json.dumps(dict(event=ev, **a)))
    for _ in range(300):
        if replies.get(ev): return replies[ev].pop(0)
        time.sleep(0.02)
threading.Thread(target=rx, daemon=True).start()
st = struct.unpack('<I', base64.b64decode(call('memory.read', address=fs + 0x52C, size=4)['base64']))[0]
ex = st + 0x18
print('ex gauge', struct.unpack('<f', base64.b64decode(call('memory.read', address=ex, size=4)['base64']))[0])
call('cpu.breakpoint.add', address=0x088a24d4, enabled=False, log=True, logFormat='SND a1={a1} ra={ra}')
marks = []
def press(b, fr):
    call('input.buttons.send', buttons={x: True for x in b}); time.sleep(fr / 60); call('input.buttons.send', buttons={x: False for x in b})
try:
    time.sleep(1)
    for k in range(3):
        marks.append((time.time() - t0, 'G_noex')); press(['rtrigger'], 30); time.sleep(1.5)
    call('memory.write', address=ex, base64=base64.b64encode(struct.pack('<f', 10000.0)).decode()); time.sleep(1.5)
    marks.append((time.time() - t0, 'EXMODE')); press(['rtrigger', 'square'], 24); time.sleep(3)
    for k in range(3):
        marks.append((time.time() - t0, 'G_ex')); press(['rtrigger'], 30); time.sleep(1.5)
finally:
    ws.send(json.dumps({'event': 'cpu.breakpoint.remove', 'address': 0x088a24d4})); time.sleep(1); stop.append(1)
ev = sorted(marks + logs)
import collections
print('log lines', len(logs))
for t, m in ev:
    print('%.2f %s' % (t, m))
