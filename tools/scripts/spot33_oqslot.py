"""Original Quest menus: Sora (owner 33) gets his own face, name and party pictures (RR-18 runtime, 2026-10-19,
notes/dlc-phase1.md "RR-18 Original Quest runtime"; screens dumps/screens/rr18/25, 28, 34, 36, 57).

Slips seen on the RC2 disc (vanilla fighters fine on the same screens):
  1. Battle & Event Settings slot: black face square + "Play as this character?" instead of face + name.
  2. Quest party picker "1st" slot: a dark red banner instead of Sora's.
  3. Quest party screen header: "Lv 42 Warrior of Light".
Causes (OVL_MENU_APP, all owner-indexed data with a reserved, never-filled owner-33 entry):
  a. Slot NAME, FUN_08a5417c: text group 4 entry = u32 table 0x08A544E0[owner] (full names: Cloud 13 -> 19 "Cloud
     Strife"); owner 33's word 0x08A54564 = 0 = entry 0 "Play as this character?". The full-name list (creation_room
     group 4, same list in chara_select 0 / party_setting 6 / story_mode 10) has 122 entries and no Sora.
  b. Slot FACE, FUN_08a53f58: sprite from handle list[idx], idx = u32 table 0x08A54638[owner] (owner o -> o + 2);
     owner 33 -> 0 -> list[0] = a panel part (black square). The list (scene + 0x30, 38 handles) is built by
     FUN_08a62530 from (layout, picture) pairs 0x08A63724 (owner icons = layout 0x660E, pictures 25652 + owner - 1);
     every one of the 38 handles is in use and the scene object has no room for a 39th.
  c. Party PICTURES, FUN_08a6bed0 (party slots 1st..5th, row +2) and FUN_08a6c03c (current member, row +4): 6-byte
     rows 0x08A6CAD0[owner] = (face_r, face, name) pictures (owner o: 25783/25818/25684 + o - 1); owner 33's row
     0x08A6CB96 = (-1, -1, -1) -> header name picture -1 ("Warrior of Light"), no face_r strip.
  d. Party PICKER banner, 0x08A6AB10 (Test -> Quest Info -> member picker, slots 1st..5th): u16 0x08A6B394[owner] =
     face_r picture (owner o: 25783 + o - 1); owners 33 and 34 = 25814 = Feral Chaos's (the dark red banner).
Fix:
  a. "Sora" appended as entry 122 of the four full-name groups; 0x08A54564 = 122.
  b. FUN_08a62530 (38 words, same function): builds one more handle, pair 39 = (0x660E, 25897) = Sora's OQ icon
     (spot33_menuart put it at 25652 + 245 in menu_pk_original_quest_gim_3) read from the unused -1 word 0x08A637BC
     right after the 38 pairs, and stores that handle in face-table word 0x08A546BC (owner 33, unused) instead of the
     scene. The base-class call it starts with is made direct (its vtable 0x08A63680 is the only one holding
     FUN_08a62530; slot 0x44 = FUN_08a52034, adjust 0). FUN_08a53f58 (21 words 0x08A54044..): the face-table memcpy
     is replaced by a direct load; an entry >= 64 is a handle (only owner 33's, written at run time), else list[entry]
     exactly as before. The word is rewritten every time the list is built, so it never outlives the scene.
  c. Row 0x08A6CB96 = (26028, 26063, 25929) = Sora's face_r / face / name pictures from spot33_menuart (base + 245).
  d. 0x08A6B3D6 (owner 33) = 26028 (Sora's face_r); owner 34 left as it is.
Guards: every code / data word is the clean value or ours (all checked before anything is written); the clean words
also match dumps/extracted/OVL_MENU_APP.ELF; Sora's four pictures must exist (non-empty) in
menu_pk_original_quest_gim_3; text groups: the other entries / groups byte-identical after the rebuild. Refuses the
clean dump and an ISO PPSSPP has open. --dry writes nothing, --rollback restores the clean words and drops entry 122.
Re-runnable ("already").

  python3 -I spot33_oqslot.py ISO [--dry] [--rollback]
"""
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mips_asm import asm  # noqa: E402
from roster_patch import MENU_FILEOFF, MENU_ISO_SECTOR, MENU_VADDR  # noqa: E402
from spot33_museum import decode, encode, get, put_file  # noqa: E402

SECTOR = 0x800
CLEAN_MENU = os.path.join(HERE, '../../dumps/extracted/OVL_MENU_APP.ELF')
SORA_FULL = 122                               # full-name entry for Sora (groups have 0..121)
FACE33 = 0x08A546BC                           # face-table word of owner 33 (0x08A54638 + 4 * 33)
PAIR39 = 0x08A637BC                           # unused -1 word right after the 38 (layout, picture) pairs
ICON, LAYOUT = 25897, 0x660E                  # Sora's OQ icon (25652 + 245), owner-icon layout
ROW33 = (26028, 26063, 25929)                 # face_r / face / name (25783 / 25818 / 25684 + 245)
PICS = {25897: 'icon', 26028: 'face_r', 26063: 'face', 25929: 'name'}

BUILDER_VA = 0x08A62530
BUILDER_CLEAN = ('27bdffe0 afb00000 00808025 8e040024 24840040 84850000 8c860004 afb10004 afb20008 afb3000c '
                 'afbf0010 00c0f809 02052021 3c1208a6 34130000 26523724 3c11089d 96460000 96470002 8e247830 '
                 '0e2341c0 3405001a ae020030 8e247830 0e233e5c 00402825 26730001 26520004 2a640026 1480fff3 '
                 '26100004 8fb00000 8fb10004 8fb20008 8fb3000c 8fbf0010 03e00008 27bd0020')
BUILDER = """
    addiu sp,sp,-0x10
    sw s0,0x0(sp)
    sw s1,0x4(sp)
    sw ra,0x8(sp)
    jal 0x08a52034
    or s0,a0,zero
    lui s1,0x8a6
    addiu s1,s1,0x3724
L:
    lhu a2,0x0(s1)
    lhu a3,0x2(s1)
    lui a0,0x89d
    lw a0,0x7830(a0)
    jal 0x088d0700
    ori a1,zero,0x1a
    sw v0,0x30(s0)
    lui a0,0x89d
    lw a0,0x7830(a0)
    jal 0x088cf970
    or a1,v0,zero
    addiu s1,s1,0x4
    andi t0,s1,0xffff
    addiu s0,s0,0x4
    xori t1,t0,0x37bc
    bne t1,zero,SKIP
    xori t1,t0,0x37c0
    lui s0,0x8a5
    addiu s0,s0,0x468c
SKIP:
    bne t1,zero,L
    nop
    lw s0,0x0(sp)
    lw s1,0x4(sp)
    lw ra,0x8(sp)
    jr ra
    addiu sp,sp,0x10
    nop
    nop
    nop
    nop
"""
FACE_VA = 0x08A54044
FACE_CLEAN = ('3c0508a5 27a40094 34060090 0e24d549 24a54638 00112080 03a42021 8c910094 8e040018 10800004 '
              '00000000 0e236818 00000000 ae000018 8e040078 00112880 00852021 8c840000 00002825 0e236a90 '
              '00003025')
FACE = """
    lw a0,0x18(s0)
    beq a0,zero,L1
    nop
    jal 0x088da060
    nop
    sw zero,0x18(s0)
L1:
    sll a1,s1,2
    lui a3,0x8a5
    addu a3,a3,a1
    lw a1,0x4638(a3)
    addiu a3,a3,0x4638
    lw a0,0x78(s0)
    sll t1,a1,2
    addu t1,a0,t1
    sltiu t0,a1,0x40
    movz t1,a3,t0
    lw a0,0x0(t1)
    or a1,zero,zero
    jal 0x088daa40
    or a2,zero,zero
    nop
"""
# data: (VA, clean bytes, ours)
DATA = [
    (0x08A54564, struct.pack('<I', 0), struct.pack('<I', SORA_FULL), 'slot name: full-name entry of owner 33'),
    (PAIR39, struct.pack('<I', 0xFFFFFFFF), struct.pack('<HH', LAYOUT, ICON), 'pair 39 = Sora OQ icon'),
    (0x08A6CB96, struct.pack('<3h', -1, -1, -1), struct.pack('<3H', *ROW33), 'party row of owner 33'),
    (0x08A6B3D6, struct.pack('<H', 25814), struct.pack('<H', ROW33[0]), 'party picker banner of owner 33'),
]
TEXTS = {'text/EN/mess_pk_creation_room_0.bin': 4, 'text/EN/mess_pk_chara_select_0.bin': 0,
         'text/EN/mess_pk_party_setting_0.bin': 6, 'text/EN/mess_pk_story_mode_0.bin': 10}
SORA = 'Sora\0'.encode('utf-16-le')
OQ_PACK = 'menu/menu_pk_original_quest_gim_3.bin'


def menu_off(va):
    return MENU_ISO_SECTOR * SECTOR + va - MENU_VADDR + MENU_FILEOFF


def hexwords(s):
    return [int(x, 16) for x in s.split()]


def code_plan(f, clean_menu, rollback):
    plan = []
    for va, clean, src in ((BUILDER_VA, BUILDER_CLEAN, BUILDER), (FACE_VA, FACE_CLEAN, FACE)):
        clean = hexwords(clean)
        ours = asm(src.strip().splitlines(), va)
        assert len(ours) == len(clean), (hex(va), len(ours), len(clean))
        o = va - MENU_VADDR + MENU_FILEOFF
        assert list(struct.unpack_from('<%dI' % len(clean), clean_menu, o)) == clean, \
            'clean OVL_MENU_APP.ELF differs at %08x' % va
        f.seek(menu_off(va))
        cur = list(struct.unpack('<%dI' % len(clean), f.read(4 * len(clean))))
        assert cur in (clean, ours), 'code at %08x is neither clean nor ours - stop' % va
        want = clean if rollback else ours
        plan.append((va, struct.pack('<%dI' % len(want), *want), cur == want, '%d words' % len(want)))
    for va, clean, ours, what in DATA:
        o = va - MENU_VADDR + MENU_FILEOFF
        assert clean_menu[o:o + len(clean)] == clean, 'clean OVL_MENU_APP.ELF differs at %08x' % va
        f.seek(menu_off(va))
        cur = f.read(len(clean))
        assert cur in (clean, ours), 'data at %08x = %s, neither clean nor ours - stop' % (va, cur.hex())
        want = clean if rollback else ours
        plan.append((va, want, cur == want, what))
    o = FACE33 - MENU_VADDR + MENU_FILEOFF
    assert clean_menu[o:o + 4] == b'\0' * 4, 'face-table word of owner 33 is not 0 in the clean overlay'
    return plan


def check_pics(iso):
    b = get(iso, OQ_PACK)
    cnt, base = struct.unpack_from('<HH', b, 0x0A)
    for pid, what in PICS.items():
        assert base <= pid < base + cnt, '%s picture %d not in %s (spot33_menuart missing?)' % (what, pid, OQ_PACK)
        size = struct.unpack_from('<II', b, 0x10 + 8 * (pid - base))[1]
        assert size > 0, '%s picture %d is empty in %s (spot33_menuart missing?)' % (what, pid, OQ_PACK)
    print('  %s: Sora icon/face_r/face/name pictures present' % OQ_PACK)


def texts(iso, dry, rollback):
    for path, gi in TEXTS.items():
        d = get(iso, path)
        assert d[:8] == b'mess pak', d[:8]
        ng, = struct.unpack_from('<H', d, 10)
        groups = [struct.unpack_from('<II', d, 0x10 + 8 * i) for i in range(ng)]
        bodies = [d[go:go + gs] for go, gs in groups]
        raws = decode(bodies[gi])
        e = encode(raws)
        assert e == bodies[gi][:len(e)] and not bodies[gi][len(e):].strip(b'\0'), path
        assert raws[7] == 'Warrior of Light\0'.encode('utf-16-le') and raws[121] == 'Feral Chaos\0'.encode('utf-16-le'), \
            '%s group %d is not the full-name list' % (path, gi)
        has = len(raws) == SORA_FULL + 1
        if has:
            assert raws[SORA_FULL] == SORA, '%s group %d entry %d is not "Sora"' % (path, gi, SORA_FULL)
        else:
            assert len(raws) == SORA_FULL, (path, len(raws))
        if has != rollback:
            print('  %s group %d: already %s' % (path, gi, 'without Sora' if rollback else '"Sora" at %d' % SORA_FULL))
            continue
        new_raws = raws[:SORA_FULL] if rollback else raws + [SORA]
        bodies[gi] = encode(new_raws)
        out = bytearray(d[:groups[0][0]])
        for i, b in enumerate(bodies):
            out += b'\0' * ((-len(out)) % 16)
            struct.pack_into('<II', out, 0x10 + 8 * i, len(out), len(b))
            out += b
        out += b'\0' * ((-len(out)) % 16)
        for i, (go, gs) in enumerate(groups):
            no, ns = struct.unpack_from('<II', out, 0x10 + 8 * i)
            if i == gi:
                assert decode(bytes(out[no:no + ns])) == new_raws
            else:
                assert out[no:no + ns] == d[go:go + gs]
        print('  %s group %d: %s (%d -> %d bytes)%s' % (path, gi, '- "Sora"' if rollback else '+ "Sora" at %d' % SORA_FULL,
                                                      len(d), len(out), ' (dry)' if dry else ''))
        if not dry:
            put_file(iso, path, bytes(out))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    assert len(args) == 1, __doc__
    iso = args[0]
    dry, rollback = '--dry' in sys.argv, '--rollback' in sys.argv
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the vanilla ISO'
    if not dry:
        r = subprocess.run(['pgrep', '-a', '-x', 'PPSSPPSDL'], capture_output=True, text=True)
        assert os.path.abspath(iso) not in r.stdout and os.path.basename(iso) not in r.stdout, \
            'PPSSPP has this ISO open - stop'
    clean_menu = open(CLEAN_MENU, 'rb').read()
    with open(iso, 'rb') as f:
        f.seek(560 * SECTOR)
        assert f.read(4) == b'\x7fELF', 'EBOOT is not the plain ELF'
        plan = code_plan(f, clean_menu, rollback)
    if not rollback:
        check_pics(iso)
    for va, data, done, what in plan:
        print('  OVL_MENU_APP %08x %s: %s' % (va, what, 'already' if done else ('to write (dry)' if dry else 'write')))
    if not dry:
        with open(iso, 'r+b') as f:
            for va, data, done, what in plan:
                if not done:
                    f.seek(menu_off(va))
                    f.write(data)
        with open(iso, 'rb') as f:
            for va, data, done, what in plan:
                f.seek(menu_off(va))
                assert f.read(len(data)) == data, 'verify failed at %08x' % va
    texts(iso, dry, rollback)
    print('dry run, nothing written' if dry else 'done')


if __name__ == '__main__':
    main()
