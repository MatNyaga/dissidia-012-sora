"""Sora's own equipment (Codex Q-20261016-CODEX-004): weapon 678 "Kingdom Key" and armor 679 "Protect Belt".
notes/ex-equipment.md §3. Their EX effects are battle code in spot33_reflect.py (EXITEMS, needs TRINITY_CTL on).

DATA (main.bin → system.bin chunk `item`, main_lang.bin EN → item.bin / item_help.bin):
  item rows 678 = clone of Broadsword (0), 679 = clone of Leather Armor (101): same stats/slot/price, only id, name,
  help and equip mask (bit 0 = owner 1 / owner 33) differ. Appended after id 677 (table stays sorted; 679 rows <= 683
  = loader + save-inventory ceiling). Names = new item.bin entries 762/763, help = new item_help.bin entries 784/785
  (tables grown by 2 entries each; every other entry re-checked byte for byte after the rebuild; the game copies the
  exact file size to the heap, main_lang buffer 0x80000 has room).
CODE (EBOOT dead function, sub-range 0x089a8b94-0x089a8de4 owned by THIS script; hooks are single words or pairs):
  ENSURE   0x088b8fd0 (FUN_088b8fd0 = every item-inventory lookup) `addiu sp,-16 / lw a2,0x15f4(a0)` →
           `j ENSURE / addiu sp,-16`: only for the real save inventory (*(0x089d712c)+0xf6e0): if its sorted list ends
           below 678/679 (a save made before this patch), append 678 and/or 679 with count 1, flags 0x0b (owned,
           seen) = owned from the start, once (later saves contain them). Then the original code continues.
  NEWGAME  0x088b8778 (end of the new-game inventory init FUN_088b8634, `jal 0x088b87ac` = an empty stub) →
           `jal NEWGAME_GIVE`: the fresh inventory already lists 678/679 (count 0) → count 1 (only if 0).
  ELIG     0x088c1afc (FUN_088c1ae8 "may character c keep/equip this item", jal FUN_088c1998) → jal ELIG_MASK:
           for 678/679 the mask is all bits for c == 33, none for anybody else (owner 33 shares bit 0 with owner 1).
  ROWMASK  0x088c132c / 0x088c1364 (FUN_088c1234 item list search, `lw a1,0x18(s0)` = row mask) → jal ROWMASK
           (same rule, char = s2; uses t8/t9 only).
  MENU     menu overlay 0x08af9004 (FUN_08af8f84 equip status) and 0x08af8ed8 (FUN_08af8ea8), both
           `jal 0x08af8e14` (effective item mask) → jal MENU_FIX (same rule, char = **(ctx+0x140)).
Every site is checked (original or ours) before anything is written; re-run = no change.
EX MODE PAGE (Phase 3; Customization → EX Mode, menu overlay FUN_08b22ec0): per-character table at menu overlay
  0x08b23f28, 0x20-B rows (int character, 2 × 7 u16 = burst, burst 2, Regen 23, Critical Boost 68, effects ×3; -1 =
  none), -1 ends it. Owner 33 had no row (empty page). The unused Chaos row (character 23, not playable; burst 0, no
  effects) becomes Sora's: Trinity Limit + Ultima Weapon (ATK) + Reflect (GUARD) + Haste (RUN), names/descriptions =
  new entries 82-85 of text/EN/mess_pk_exmode_0.bin groups 2 (names) / 3 (descriptions), grown 82 → 86 (every old
  entry and group re-checked). Wording: Codex CUSTOMIZATION-TEXT.txt, notes/ex-damage.md, measured +10 % run.
  python3 -I spot33_exitems.py ISO [--dry]       env EXITEMS=0 → exact rollback (rows, texts, code, sites)
"""
import hashlib
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

KK_ID, PB_ID, SK_ID, CP_ID = 678, 679, 680, 681   # also used by spot33_reflect.py (battle effects)
ITEMS = (KK_ID, PB_ID, SK_ID, CP_ID)
SHIELD_MULT = float(os.environ.get('SHIELD_MULT', '1.5'))   # Save the King: reflected-hit power x (hit +0x2a)
CROWN_DRAIN = float(os.environ.get('CROWN_DRAIN', str(1 / 1.3)))  # Crown Pendant: EX drain x (1/1.3 = EX lasts x1.30; spot33_reflect HELM)

from mips_asm import asm  # noqa: E402

SECTOR = 2048
EBOOT_ISO = 560 * SECTOR
MENU_SECTOR, OVL_BASE, OVL_DATA = 185056, 0x089DD4C0, 0x54
CLEAN_EBOOT = os.path.join(HERE, '../../dumps/extracted/EBOOT.elf')
CLEAN_MENU = os.path.join(HERE, '../../dumps/extracted/OVL_MENU_APP.ELF')
CLEAN_ISO = os.path.realpath(os.path.join(HERE, '../../dumps/ULUS10566.iso'))
MAIN = 'general_archive/main/main.bin'
LANG = 'general_archive/main/EN/main_lang.bin'

ON = os.environ.get('EXITEMS', '1') == '1'
# PANEL (RR-12, Mat's runtime find on p16 2026-10-18): the □ "Can be equipped by" panel (menu FUN_08aff218, shared
# by Customization / Shop / Artifacts) lit EVERY portrait for 678..681: in Customization its mask comes from
# FUN_08af8ea8 -> MENU_FIX, which returns all bits while Sora is the edited fighter (that is what lets him equip them;
# the real equip lists of other fighters were already correct). Owner 33 shares bit 0 with Warrior of Light, so no
# 32-bit mask can light Sora alone -> PANEL_LIT replaces the panel's lit test (0x08aff32c `and a0,s2,a0`; s1 = panel,
# *(s1+0) = item id, s4 = sprite owner after spot33_charpanel = 32 only for Sora, Feral Chaos is not in that list):
# items 678..681 -> lit only for Sora's portrait, whatever the mask; every other item = the original `and`.
# 8 words in the last free words of this script's range; the jal's delay slot is the native next word (sll a2,a1,2).
PANEL_FIX = os.environ.get('PANEL_FIX', '1') == '1'
DONOR = {KK_ID: 0, PB_ID: 101, SK_ID: 57, CP_ID: 81}       # Broadsword, Leather Armor, Buckler, Bronze Helm
SLOT = {KK_ID: 0, PB_ID: 3, SK_ID: 1, CP_ID: 2}
NAME_IDX = {KK_ID: 762, PB_ID: 763, SK_ID: 764, CP_ID: 765}
HELP_IDX = {KK_ID: 784, PB_ID: 785, SK_ID: 786, CP_ID: 787}
MASK = 0x1                                    # bit 0 (owners 1 and 33); the code below makes it Sora-only
NAMES = {KK_ID: 'Kingdom Key', PB_ID: 'Protect Belt', SK_ID: 'Save the King', CP_ID: 'Crown Pendant'}
HELP = {  # Customization help box: max 2 lines of ~28 visible chars (vanilla max 2 lines / 31 chars; Mat test331: 3 lines overflowed)
    KK_ID: "Sora only. Combos build EX.\nATK grows with Sora's level.",
    PB_ID: "Sora only. Blocks: EX +10%.\nHP grows with Sora's level.",
    SK_ID: "Sora only. Reflect dmg +50%.\nDEF grows with Sora's level.",
    CP_ID: "Sora only. Longer EX (+30%).\nBRV grows with Sora's level."}
FLAGS = 0x0B                                  # inventory flags of an owned, seen item (1 | 2 seen | 8 owned)

EXMODE_TEXT = 'text/EN/mess_pk_exmode_0.bin'
EXMODE_N0 = 82                                # entries in groups 2 / 3 before ours
EXMODE_ROW_VA, EXMODE_ROW_NO = 0x08B23F28, 22 # row 22 = character 23 (Chaos)
CIRCLE = '\x1e\u2f01'                        # the game's circle-button glyph (Cloud's Omnislash text)
EXMODE_NEW = [  # (name, description) -> entries 82, 83, 84, 85
    ('Trinity Limit',
     'Sora calls on the light of his\nfriends for a storm of Keyblade\nstrikes.\nRepeatedly press %s to raise the\n'
     'gauge.' % CIRCLE),
    ('Ultima Weapon \x11P(ATK)\x11d',
     "[Always active while in EX Mode]\nThe higher the user's HP, the\nstronger the Keyblade. Bravery\n"
     'attacks also gain a 50% bonus.'),
    ('Reflect \x11P(GUARD)\x11d',
     '[Always active while in EX Mode]\nBlocking casts Reflect: attacks,\nspells, even HP attacks go back.\n'
     'Reflecting an HP attack refills\nthe EX gauge.'),
    ('Haste \x11P(RUN)\x11d',
     '[Always active while in EX Mode]\nRuns 40% faster on the ground.')]
EXMODE_ORIG_ROW = struct.pack('<i14h', 23, 0, -1, 23, 68, -1, -1, -1, 0, -1, 23, 68, -1, 0, 0)
_b, _e = EXMODE_N0, EXMODE_N0
EXMODE_ROW = struct.pack('<i14h', 33, _b, -1, 23, 68, _e + 1, _e + 2, _e + 3, _b, -1, 23, 68, _e + 1, _e + 2, _e + 3)
# EX Mode page header (FUN_08af37a4 -> FUN_08af3824 -> EBOOT FUN_088d5638, shared with the main Customization
# header): face = bases[0] + owner - 1, name = bases[1] + owner - 1, assist face = bases[0] + assist - 1. The EX
# scene's bases 0x08b23f22 = (15395, 15363) -> owner 33 asked for 15427 (an EN lpk label) and 15395 (= Warrior of
# Light's face: the "blue armour" picture). PICID3/PICID0 (sites 0x088d56a4 / 0x088d56d8 owner s3, 0x088d5714
# assist s0; `addu a0,a1,sX / addiu a0,a0,-1` -> `jal PICIDx / nop`): only owner 33 with base 15395 -> 15434 and
# base 15363 -> 15435, everything else the original sum (main Customization header 3114/3081 unchanged).
# 15434 = new main-pack entry = Sora's customize face (menu_pk_customize_gim_0 entry 74; the 32 EX-page faces are
# byte-identical to the customize ones), 15435 = new EN lpk entry = Sora's name plate (menu_lpk_customize_gim_0 41).
EX_FACE_ID, EX_NAME_ID = 15434, 15435
EX_PACK, EX_LPK = 'menu/menu_pk_exmode_gim_0.bin', 'menu/EN/menu_lpk_exmode_gim_0.bin'
CUST_PACK, CUST_LPK = 'menu/menu_pk_customize_gim_0.bin', 'menu/EN/menu_lpk_customize_gim_0.bin'
EX_PACK_N0 = 74                               # entries in both EX packs before ours
EX_SCENE_BUFFER = 0xB6800                     # FUN_088d00fc(.., 0xb6800, group 0x10, list 0x08b24368): 4 packs

LO, HI = 0x089A8B94, 0x089A8DE4               # THIS script's EBOOT sub-range (148 words; 132 until test311)
DEAD_LO, DEAD_HI = 0x089A8B14, 0x089A8F0C
DEAD_SHA = '1345b9e14727260640786f74c5a0da3f87f96bc420433447e145e240f01dd10e'
# ---- Level scaling (Mat 2026-10-17: "have the attack be based on your level ... the same with Protect Belt") ----
# Item stats are added per queried effect id by FUN_088be63c(out, max, effect, RECORD, provider) (EBOOT; battle
# fighter setup and every menu stat build): for each equipped slot FUN_088bdb2c(.., row + 0x1c, ..) reads the 4 fixed
# slots through the pointers the item loader sets (row+0x20+8i -> row+0x3c+2i). STASH (entry 0x088be63c) keeps a3 =
# record in SCR; SCALE (call 0x088be96c, a3 = row + 0x1c; t0 = 5th argument from the delay slot, kept) rewrites our row's stat value in the RAM item table from
# the record's level (byte +1) before the native read. Piecewise linear over 32-level segments: V0 at Lv1, V1 Lv33,
# V2 Lv65, V3 Lv97, V4 = slope point so Lv100 = top tier; points = best vanilla gear of that tier (swords type 0 /
# light armor type 21, the categories of the template rows). Code lives in the DEAD jump table of the dead function
# 0x089a8b14 (0x089d1fb4, 52 words; its only reference is that dead function's own `jr`).
SCALE_TAB = {KK_ID: (0, (4, 40, 58, 63, 106)),         # slot 0 ATK: Lv1 4 (Broadsword) .. Lv100 67 (Excalibur tier)
             PB_ID: (2, (428, 1882, 2610, 2610, 6482)),  # slot 2 HP: Lv1 428 (Leather Armor) .. Lv100 2973
             SK_ID: (1, (3, 39, 61, 67, 131)),           # slot 1 DEF: Lv1 3 (Buckler) .. Lv100 73 (shields type 12)
             CP_ID: (3, (38, 167, 255, 255, 629))}       # slot 3 BRV: Lv1 38 (Bronze Helm) .. Lv100 290 (helms type 17)
JT_LO, JT_HI = 0x089D1FB4, 0x089D1FB4 + 52 * 4


def scale_value(item, level):
    slot, v = SCALE_TAB[item]
    k, frac = (level - 1) >> 5, (level - 1) & 31
    return v[k] + (((v[k + 1] - v[k]) * frac) >> 5)


TEXT_KEY_VA = 0x089D68AA                      # 16 u16 XOR keys for 'UTF8' text tables (FUN_0887a6a0)

SRC = """
ENSURE:
    lui t0,0x89d
    lw t0,0x712c(t0)
    ori t1,zero,0xf6e0
    addu t0,t0,t1
    bne t0,a0,EN_OUT
    lw t1,0x15f4(a0)
    addiu t2,t1,-0x1
    sltiu t2,t2,%(lim)d
    beq t2,zero,EN_OUT
    addu t3,t1,t1
    addu t3,t3,t3
    addu t3,t3,a0
    lh t4,-0x4(t3)
    bltz t4,EN_OUT
    li t6,%(first1)d
EN_LOOP:
    slt t5,t4,t6
    movn t4,t6,t5
    addiu t4,t4,0x1
    slti t5,t4,%(end)d
    beq t5,zero,EN_SAVE
    li t5,%(cf)d
    sh t4,0x0(t3)
    sh t5,0x2(t3)
    addiu t3,t3,0x4
    b EN_LOOP
    addiu t1,t1,0x1
EN_SAVE:
    sw t1,0x15f4(a0)
EN_OUT:
    lw a2,0x15f4(a0)
    j 0x088b8fd8
    nop
NEWGAME_GIVE:
    lw t1,0x15f4(a0)
    li t7,%(n)d
    li t5,%(cf)d
NG_LOOP:
    blez t1,NG_OUT
    addiu t1,t1,-0x1
    addu t3,t1,t1
    addu t3,t3,t3
    addu t3,t3,a0
    lh t4,0x0(t3)
    addiu t4,t4,-%(first)d
    sltiu t4,t4,%(n)d
    beq t4,zero,NG_NEXT
    addiu t7,t7,-0x1
    sh t5,0x2(t3)
NG_NEXT:
    bgtz t7,NG_LOOP
    nop
NG_OUT:
    jr ra
    nop
ELIG_MASK:
    addiu sp,sp,-0x10
    sw ra,0x0(sp)
    jal 0x088c1998
    sw a0,0x4(sp)
    lw a0,0x4(sp)
    lw ra,0x0(sp)
    lw t0,0x0(a0)
    beq t0,zero,EM_RET
    addiu sp,sp,0x10
    lh t1,0x0(t0)
    addiu t1,t1,-%(first)d
    sltiu t1,t1,%(n)d
    beq t1,zero,EM_RET
    xori t2,s0,0x21
    sltiu t2,t2,0x1
    subu v0,zero,t2
EM_RET:
    jr ra
    nop
ROWMASK:
    lh t8,0x0(s0)
    addiu t8,t8,-%(first)d
    sltiu t8,t8,%(n)d
    bne t8,zero,RM_OURS
    xori t9,s2,0x21
    jr ra
    lw a1,0x18(s0)
RM_OURS:
    sltiu t9,t9,0x1
    jr ra
    subu a1,zero,t9
MENU_FIX:
    addiu sp,sp,-0x10
    sw ra,0x0(sp)
    sw a0,0x4(sp)
    jal 0x08af8e14
    sw a1,0x8(sp)
    lw a0,0x4(sp)
    lw a1,0x8(sp)
    lw ra,0x0(sp)
    lw t0,0x0(a1)
    beq t0,zero,MF_RET
    addiu sp,sp,0x10
    lh t1,0x0(t0)
    addiu t1,t1,-%(first)d
    sltiu t1,t1,%(n)d
    beq t1,zero,MF_RET
    lw t0,0x140(a0)
    beq t0,zero,MF_RET
    li v0,0x0
    lw t0,0x0(t0)
    xori t0,t0,0x21
    sltiu t0,t0,0x1
    subu v0,zero,t0
MF_RET:
    jr ra
    nop
SHIELD:
    lw t3,0x18(a0)
    lw t4,0x20(a0)
    beq t4,t3,SH_GO
    nop
    beq t4,zero,SH_GO
    nop
    beq t3,zero,SH_GO
    move t7,ra
    move t6,a0
    move a0,t3
    jal %(has)s
    li a1,%(sk)d
    move a0,t6
    beq v0,zero,SH_GO
    move ra,t7
    lh t5,0x2a(a0)
    li t6,%(pct)d
    mult t5,t6
    mflo t5
    .word %(sra7)s
    sh t5,0x2a(a0)
SH_GO:
    j 0x089a3890
    nop
PICID0:
    b PI_C
    move t9,s0
PICID3:
    move t9,s3
PI_C:
    addu a0,a1,t9
    addiu a0,a0,-0x1
    xori t8,t9,0x21
    bne t8,zero,PI_RET
    li t8,%(fb)d
    beq a1,t8,PI_F
    li t8,%(nb)d
    bne a1,t8,PI_RET
    nop
    jr ra
    li a0,%(nid)d
PI_F:
    li a0,%(fid)d
PI_RET:
    jr ra
    nop
PANEL_LIT:
    lw t7,0x0(s1)
    addiu t7,t7,-%(first)d
    sltiu t7,t7,%(n)d
    and a0,s2,a0
    xori t8,s4,0x20
    sltiu t8,t8,0x1
    jr ra
    movn a0,t8,t7
"""
SRC_ARGS = dict(first=KK_ID, first1=KK_ID - 1, n=len(ITEMS), end=KK_ID + len(ITEMS), lim=683 - len(ITEMS),
                cf=FLAGS << 8 | 1, sk=SK_ID, pct=int(round(SHIELD_MULT * 128)), sra7='0x%08x' % (13 << 16 | 13 << 11 | 7 << 6 | 3),
                fb=15395, nb=15363, fid=15434, nid=15435)


def ee_has_addr():
    """EE_HAS lives in spot33_reflect's EE_B (it must be installed: checked in main)"""
    import spot33_reflect as R
    return R.EE_B_LABELS['EE_HAS'], R.EE_B_LO, R.EE_B_WORDS


def plan():
    assert 1.0 <= SHIELD_MULT <= 3.0 and 0.1 <= CROWN_DRAIN <= 1.0
    src = (SRC % dict(SRC_ARGS, has='0x%08x' % ee_has_addr()[0])).strip().split('\n')
    words = asm(src, LO)
    labels, pc = {}, LO
    for line in src:
        line = line.strip()
        if line.endswith(':'):
            labels[line[:-1]] = pc
        elif line:
            pc += 4
    assert LO + 4 * len(words) <= HI, 'exitems code (%d words) does not fit' % len(words)
    code = b''.join(struct.pack('<I', w) for w in words)

    def j(op, t, va):
        return asm(['%s 0x%08x' % (op, t)], va)[0]
    # (area, va, original words, new words)
    sites = [('eboot', 0x088B8FD0, (0x27BDFFF0, 0x8C8615F4), (j('j', labels['ENSURE'], 0x088B8FD0), 0x27BDFFF0)),
             ('eboot', 0x088B8778, (0x0E22E1EB,), (j('jal', labels['NEWGAME_GIVE'], 0x088B8778),)),
             ('eboot', 0x088C1AFC, (0x0E230666,), (j('jal', labels['ELIG_MASK'], 0x088C1AFC),)),
             ('eboot', 0x088C132C, (0x8E050018,), (j('jal', labels['ROWMASK'], 0x088C132C),)),
             ('eboot', 0x088C1364, (0x8E050018,), (j('jal', labels['ROWMASK'], 0x088C1364),)),
             ('menu', 0x08AF9004, (0x0E2BE385,), (j('jal', labels['MENU_FIX'], 0x08AF9004),)),
             ('menu', 0x08AF8ED8, (0x0E2BE385,), (j('jal', labels['MENU_FIX'], 0x08AF8ED8),)),
             ('eboot', 0x088D56A4, (0x00B32021, 0x2484FFFF), (j('jal', labels['PICID3'], 0x088D56A4), 0)),
             ('eboot', 0x088D56D8, (0x00B32021, 0x2484FFFF), (j('jal', labels['PICID3'], 0x088D56D8), 0)),
             ('eboot', 0x088D5714, (0x00B02021, 0x2484FFFF), (j('jal', labels['PICID0'], 0x088D5714), 0)),
             ('eboot', 0x088079AC, (0x0E268E24,), (j('jal', labels['SHIELD'], 0x088079AC),))]
    # □ "Can be equipped by" panel (RR-12, 2026-10-18): PANEL_FIX=0 puts the vanilla word back
    sites.append(('menu', 0x08AFF32C, (0x02442024,),
                  (j('jal', labels['PANEL_LIT'], 0x08AFF32C),) if PANEL_FIX else (0x02442024,)))
    _, jl = jt_plan()
    sites += [('eboot', 0x088BE63C, (0x27BDFDD0, 0xAFB50214), (j('j', jl['STASH'], 0x088BE63C), 0x27BDFDD0)),
              ('eboot', 0x088BE96C, (0x0E22F6CB,), (j('jal', jl['SCALE'], 0x088BE96C),))]
    return code, sites, labels, len(words)


def _shift(op, rd, rt, sa):
    return '.word 0x%08x' % (R_[rt] << 16 | R_[rd] << 11 | sa << 6 | {'sll': 0, 'srl': 2, 'sra': 3}[op])


def jt_plan():
    """STASH + SCALE + SCR + TAB in the dead jump table; -> (bytes, labels)"""
    from mips_asm import R as R
    global R_
    R_ = R
    items = sorted(SCALE_TAB)
    assert items == list(range(KK_ID, KK_ID + len(items)))
    for _ in range(2):
        n_code = 0 if _ == 0 else n_code
        scr = JT_LO + 4 * n_code
        tab = scr + 4
        hs = lambda a: '0x%x' % ((a + 0x8000) >> 16)
        ls = lambda a: (lambda lo: ('-0x%x' % -lo) if lo < 0 else '0x%x' % lo)(((a & 0xFFFF) ^ 0x8000) - 0x8000)
        src = """
STASH:
    lui t9,%(sh)s
    sw a3,%(sl)s(t9)
    j 0x088be644
    sw s5,0x214(sp)
SCALE:
    lh t7,-0x1c(a3)
    addiu t7,t7,-%(kk)d
    sltiu t1,t7,%(n)d
    beq t1,zero,SC_GO
    lui t9,%(sh)s
    lw t1,%(sl)s(t9)
    lbu t1,0x1(t1)
    addiu t1,t1,-0x1
    %(srl)s
    andi t1,t1,0x1f
    %(sll3)s
    %(sll2)s
    addu t3,t3,t7
    lui t4,%(th)s
    addiu t4,t4,%(tl)s
    addu t3,t3,t4
    lhu t4,0x0(t3)
    addu t2,t2,t2
    addu t2,t2,t3
    lhu t5,0x2(t2)
    lhu t6,0x4(t2)
    subu t6,t6,t5
    mult t6,t1
    mflo t6
    %(sra)s
    addu t5,t5,t6
    addu t4,t4,a3
    j 0x088bdb2c
    sh t5,0x0(t4)
SC_GO:
    j 0x088bdb2c
    nop
""" % dict(sh=hs(scr), sl=ls(scr), th=hs(tab), tl=ls(tab), kk=KK_ID, n=len(items),
           srl=_shift('srl', 't2', 't1', 5), sll3=_shift('sll', 't3', 't7', 3), sll2=_shift('sll', 't7', 't7', 2),
           sra=_shift('sra', 't6', 't6', 5))
        lines = src.strip().split('\n')
        words = asm(lines, JT_LO)
        n_code = len(words)
    labels, pc = {}, JT_LO
    for line in lines:
        line = line.strip()
        if line.endswith(':'):
            labels[line[:-1]] = pc
        elif line:
            pc += 4
    data = b''.join(struct.pack('<I', w) for w in words) + bytes(4)        # SCR
    for it in items:
        slot, v = SCALE_TAB[it]
        assert all(0 <= x < 0x10000 for x in v) and len(v) == 5
        data += struct.pack('<6H', 0x20 + 2 * slot, *v)
    data += bytes((-len(data)) % 4)
    assert JT_LO + len(data) <= JT_HI, 'scaling code + table (%d B) does not fit the dead jump table' % len(data)
    labels['SCR'], labels['TAB'] = scr, tab
    return data, labels


# ------------------------------------------------------------------------------------------------- text tables
def text_key():
    eb = open(CLEAN_EBOOT, 'rb').read()
    return struct.unpack_from('<16H', eb, 0x1018 + TEXT_KEY_VA - 0x8804040)


def u8_decode(r, K):
    assert r[:4] == b'UTF8'
    n, = struct.unpack_from('<I', r, 4)
    offs = struct.unpack_from('<%dH' % n, r, 8)
    out = []
    for i in range(n):
        p = offs[i] * 2
        ln, = struct.unpack_from('<H', r, p)
        w = struct.unpack_from('<%dH' % (ln // 2), r, p + 2)
        out.append(b''.join(struct.pack('<H', x ^ K[(i + k) & 15]) for k, x in enumerate(w)))
    return out


def u8_encode(raws, K):
    n = len(raws)
    out = bytearray(b'UTF8' + struct.pack('<I', n) + bytes(2 * n))
    for i, raw in enumerate(raws):
        out += b'\0' * (len(out) % 2)
        struct.pack_into('<H', out, 8 + 2 * i, len(out) // 2)
        assert len(raw) % 2 == 0
        w = struct.unpack('<%dH' % (len(raw) // 2), raw)
        out += struct.pack('<H', len(raw)) + b''.join(struct.pack('<H', x ^ K[(i + k) & 15]) for k, x in enumerate(w))
    out += b'\0' * ((-len(out)) % 4)
    return bytes(out)


def u16_raw(s):
    return s.encode('utf-16-le') + b'\0\0'


def u8_raw(s):
    b = s.encode('utf-8') + b'\0'
    return b + b'\0' * (len(b) % 2)


def patch_texts(lang):
    """-> (new main_lang.bin or None if already as wanted, report)"""
    from mpk import entries, replace
    from spot33_desc import decode, encode
    K = text_key()
    mem = {n: lang[o:o + s] for n, o, s in entries(lang)}
    names, helps = mem['item.bin'], mem['item_help.bin']
    tn, th = decode(names), u8_decode(helps, K)
    assert encode(tn) == names and u8_encode(th, K) == helps, 'text tables do not round-trip: format changed?'
    want_n = [u16_raw(NAMES[i]) for i in ITEMS]
    want_h = [u8_raw(HELP[i]) for i in ITEMS]
    base_n, base_h = NAME_IDX[KK_ID], HELP_IDX[KK_ID]
    if len(tn) == base_n:
        cur_n = 'original'
    else:
        assert len(tn) in (base_n + 2, base_n + len(ITEMS)), 'item.bin has %d entries' % len(tn)   # 2 = test310-323
        cur_n = 'ours'
    if len(th) == base_h:
        cur_h = 'original'
    else:
        assert len(th) in (base_h + 2, base_h + len(ITEMS)), 'item_help.bin has %d entries' % len(th)
        cur_h = 'ours'
    tn0, th0 = tn[:base_n], th[:base_h]
    new_tn = tn0 + want_n if ON else tn0
    new_th = th0 + want_h if ON else th0
    nb, hb = encode(new_tn), u8_encode(new_th, K)
    assert decode(nb)[:base_n] == tn0 and u8_decode(hb, K)[:base_h] == th0      # every other entry unchanged
    rep = 'item.bin %d -> %d entries, item_help.bin %d -> %d entries' % (len(tn), len(new_tn), len(th), len(new_th))
    if nb == names and hb == helps:
        return None, rep + ' (no change)'
    out = replace(replace(lang, 'item.bin', nb), 'item_help.bin', hb)
    new_mem = {n: out[o:o + s] for n, o, s in entries(out)}
    assert all(new_mem[k] == v for k, v in mem.items() if k not in ('item.bin', 'item_help.bin'))
    assert len(out) <= 0x80000, 'main_lang.bin would exceed its 0x80000 load buffer'
    return out, rep + ' (%s/%s before), main_lang %d -> %d B' % (cur_n, cur_h, len(lang), len(out))


def patch_exmode(d):
    """mess_pk_exmode_0.bin: groups 2/3 82 -> 86 entries (EXITEMS=0: back to 82). -> (new file or None, report)"""
    from spot33_museum import decode as mdec, encode as menc
    assert d[:8] == b'mess pak', d[:8]
    ng, = struct.unpack_from('<H', d, 10)
    groups = [struct.unpack_from('<II', d, 0x10 + 8 * i) for i in range(ng)]
    bodies = [d[go:go + gs] for go, gs in groups]
    want = {2: [u16_raw(n) for n, _ in EXMODE_NEW], 3: [u16_raw(t) for _, t in EXMODE_NEW]}
    states = []
    for gi, new in want.items():
        raws = mdec(bodies[gi])
        e = menc(raws)
        assert e == bodies[gi][:len(e)] and not bodies[gi][len(e):].strip(b'\0'), 'group %d does not round-trip' % gi
        if len(raws) == EXMODE_N0 + len(new):
            # entries 82.. are only ever written by this script: a difference = our own older wording (e.g. the Haste
            # line 10% -> 40%, Mat 2026-10-17), rewritten below
            states.append('ours' if raws[EXMODE_N0:] == new else 'ours (older text)')
        else:
            assert len(raws) == EXMODE_N0, 'exmode group %d: %d entries' % (gi, len(raws))
            states.append('original')
        target = raws[:EXMODE_N0] + (new if ON else [])
        if target != raws:
            bodies[gi] = menc(target)
    if bodies == [d[go:go + gs] for go, gs in groups]:
        return None, 'exmode text groups 2/3: %s (no change)' % '/'.join(states)
    fill = b'\x77'                            # vanilla gap / tail filler of this mess pak
    out = bytearray(d[:groups[0][0]])
    for i, b in enumerate(bodies):
        out += fill * ((-len(out)) % 16)
        struct.pack_into('<II', out, 0x10 + 8 * i, len(out), len(b))
        out += b
    out += fill * ((-len(out)) % 16)
    for i, (go, gs) in enumerate(groups):
        no, ns = struct.unpack_from('<II', out, 0x10 + 8 * i)
        old = d[go:go + gs]
        if i in want:
            assert mdec(bytes(out[no:no + ns]))[:EXMODE_N0] == mdec(old)[:EXMODE_N0], 'group %d check' % i
        else:
            assert out[no:no + ns] == old, 'group %d changed' % i
    return bytes(out), 'exmode text groups 2/3: %s -> %s, %d -> %d B' % (
        '/'.join(states), 'ours' if ON else 'original', len(d), len(out))


def pak_append(d, n0, extra):
    """menu pak d with n0 entries + `extra` blobs appended as entries n0.. (b'' = empty). Original bytes are kept:
    the table grows, every non-zero offset moves by the same 16-aligned delta, new blobs go after the old end."""
    cnt, base = struct.unpack_from('<HH', d, 0x0A)
    assert cnt == n0 and len(d) % 16 == 0
    start = 0x10 + 8 * cnt
    ds = start + (-start) % 16
    ne = 0x10 + 8 * (cnt + len(extra))
    delta = ne + (-ne) % 16 - ds
    head = bytearray(d[:0x10])
    struct.pack_into('<H', head, 0x0A, cnt + len(extra))
    table = bytearray()
    for i in range(cnt):
        o, z = struct.unpack_from('<II', d, 0x10 + 8 * i)
        table += struct.pack('<II', o + delta if o else 0, z)
    tail, pos = bytearray(), len(d) + delta
    for blob in extra:
        if blob:
            table += struct.pack('<II', pos + len(tail), len(blob))
            tail += blob + b'\0' * ((-len(blob)) % 16)
        else:
            table += struct.pack('<II', 0, 0)
    out = bytes(head + table)
    out += b'\0' * (ds + delta - len(out))
    return out + d[ds:] + bytes(tail)


def pak_strip(d, n0):
    """inverse of pak_append: drop entries n0.. and move everything back (exact original bytes)"""
    cnt, base = struct.unpack_from('<HH', d, 0x0A)
    ds0 = 0x10 + 8 * n0
    ds0 += (-ds0) % 16
    ne = 0x10 + 8 * cnt
    delta = ne + (-ne) % 16 - ds0
    news = [struct.unpack_from('<II', d, 0x10 + 8 * i) for i in range(n0, cnt)]
    end = min([o for o, z in news if z] + [len(d)]) - delta
    head = bytearray(d[:0x10])
    struct.pack_into('<H', head, 0x0A, n0)
    table = bytearray()
    for i in range(n0):
        o, z = struct.unpack_from('<II', d, 0x10 + 8 * i)
        table += struct.pack('<II', o - delta if o else 0, z)
    out = bytes(head + table)
    out += b'\0' * (ds0 - len(out))
    return out + d[ds0 + delta:end + delta]


def patch_ex_pictures(iso):
    """-> {pack path: new bytes} for the EX page header face/name (only changed packs), report"""
    from spot33_qbpics import read_pack
    _, cust = read_pack(get(iso, CUST_PACK))
    _, clpk = read_pack(get(iso, CUST_LPK))
    face, name = cust[74], clpk[41]
    assert len(face) == 5416 and len(name) == 5408, 'Sora customize face/name pictures missing'
    out, rep = {}, []
    sizes = 0
    for path, gid, pic in ((EX_PACK, EX_FACE_ID, face), (EX_LPK, EX_NAME_ID, name)):
        raw = get(iso, path)
        base, blobs = read_pack(raw)
        assert base == 15360, path
        idx = gid - base
        extra = [b''] * (idx - EX_PACK_N0) + [pic]
        if len(blobs) == EX_PACK_N0:
            state, orig = 'original', raw
        else:
            assert len(blobs) == idx + 1 and blobs[EX_PACK_N0:] == extra, '%s: %d entries, not original/ours' % (
                path, len(blobs))
            state, orig = 'ours', pak_strip(raw, EX_PACK_N0)
        _, ob = read_pack(orig)
        assert len(ob) == EX_PACK_N0 and ob == blobs[:EX_PACK_N0]
        mine = pak_append(orig, EX_PACK_N0, extra)
        assert pak_strip(mine, EX_PACK_N0) == orig and read_pack(mine)[1] == ob + extra
        want = mine if ON else orig
        if want != raw:
            out[path] = want
        sizes += len(want)
        rep.append('%s %s -> %s (%d -> %d B)' % (os.path.basename(path), state, 'ours' if ON else 'original',
                                                 len(raw), len(want)))
    for p in ('menu/menu_pk_exmode_seq_0.bin', 'menu/EN/menu_lpk_exmode_seq_0.bin'):
        sizes += len(get(iso, p))
    assert sizes <= EX_SCENE_BUFFER, 'EX Mode scene packs %d > load buffer %d' % (sizes, EX_SCENE_BUFFER)
    return out, '; '.join(rep) + ' (scene packs %d of %d B)' % (sizes, EX_SCENE_BUFFER)


# ------------------------------------------------------------------------------------------------- item rows
def item_rows(item):
    n, sets = struct.unpack_from('<II', item, 8)
    rows = [item[16 + i * 104:16 + (i + 1) * 104] for i in range(n)]
    return n, sets, rows, item[16 + n * 104:]


def patch_items(item):
    n, sets, rows, tail = item_rows(item)
    assert len(item) == 16 + n * 104 + sets * 52 + 16, 'unexpected item layout'
    ids = [struct.unpack_from('<H', r)[0] for r in rows]
    by = dict(zip(ids, rows))
    want = {}
    for new in ITEMS:
        r = bytearray(by[DONOR[new]])
        assert r[12] == SLOT[new], 'donor %d slot changed' % DONOR[new]
        struct.pack_into('<HHH', r, 0, new, NAME_IDX[new], HELP_IDX[new])
        struct.pack_into('<I', r, 0x18, MASK)
        want[new] = bytes(r)
    vanilla = [i for i in range(678) if i != 673]
    if ids == vanilla:
        state = 'original'
    else:
        k = len(ids) - len(vanilla)
        assert ids[:len(vanilla)] == vanilla and k in (2, len(ITEMS)) and ids[len(vanilla):] == list(ITEMS[:k]) and \
            all(by[i] == want[i] for i in ITEMS[:k]), 'item table ids/rows are neither vanilla nor ours'
        state = 'ours (%d items)' % k
    base_rows = rows[:len(vanilla)]
    new_rows = base_rows + ([want[i] for i in ITEMS] if ON else [])
    assert len(new_rows) <= 0x2AB
    head = bytearray(item[:16])
    struct.pack_into('<I', head, 8, len(new_rows))
    out = bytes(head) + b''.join(new_rows) + tail
    return (None if out == item else out), 'item rows %d (%s) -> %d' % (n, state, len(new_rows))


def patch_main(main_bin):
    from mpk import entries as mpk_entries
    from spot33_save import arc_join, arc_split
    ents = list(mpk_entries(main_bin))
    _, sys_off, sys_size = next(e for e in ents if e[0] == 'system.bin')
    head, chunks = arc_split(main_bin[sys_off:sys_off + sys_size])
    c = next(c for c in chunks if c[1] == b'item')
    new_item, rep = patch_items(c[2])
    if new_item is None:
        return None, rep + ' (no change)'
    old_chunks = [bytes(x[2]) for x in chunks]
    c[2] = new_item
    sysbin = arc_join(head, chunks)
    h2, ch2 = arc_split(sysbin)
    assert h2 == head and all(a == b[2] for a, b in zip(old_chunks, ch2) if b[1] != b'item')
    delta = -(-(len(sysbin) - sys_size) // 16) * 16
    count, = struct.unpack_from('<I', main_bin, 8)
    out = bytearray(main_bin[:sys_off]) + sysbin + b'\0' * (delta - (len(sysbin) - sys_size))
    out += main_bin[sys_off + sys_size:]
    for i in range(count):
        noff, doff, msize, z = struct.unpack_from('<IIII', out, 16 + i * 16)
        if doff == sys_off:
            struct.pack_into('<I', out, 16 + i * 16 + 8, len(sysbin))
        elif doff > sys_off:
            struct.pack_into('<I', out, 16 + i * 16 + 4, doff + delta)
    old = {n: main_bin[o:o + s] for n, o, s in ents}
    new = {n: bytes(out[o:o + s]) for n, o, s in mpk_entries(bytes(out))}
    assert all(new[k] == v for k, v in old.items() if k != 'system.bin')
    assert len(out) <= 0x180000, 'main.bin would exceed its 0x180000 load buffer'
    return bytes(out), rep + '; system.bin %d -> %d, main.bin %d -> %d B' % (sys_size, len(sysbin), len(main_bin),
                                                                           len(out))


# ------------------------------------------------------------------------------------------------- disc i/o
def get(iso, path):
    from comb_patch import pkg_offset, read_at, use_iso
    use_iso(iso)
    st, sz = pkg_offset(path)
    with open(iso, 'rb') as f:
        return read_at(f, st, sz)


def put(iso, path, data):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'x.bin')
        open(p, 'wb').write(data)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                           check=True, capture_output=True, text=True)
        print('   ', r.stdout.strip())


def elf_off(va):
    return 0x1018 + va - 0x8804040


def site_off(area, va):
    return EBOOT_ISO + elf_off(va) if area == 'eboot' else MENU_SECTOR * SECTOR + OVL_DATA + va - OVL_BASE


def main():
    iso = sys.argv[1]
    dry = '--dry' in sys.argv
    if os.path.realpath(iso) == CLEAN_ISO:
        sys.exit('refusing to write the clean dump')
    print('EXITEMS %s: items %s (Kingdom Key, Protect Belt, Save the King x%.2f reflected, Crown Pendant drain x%.2f)' % (
        'ON' if ON else 'off (rollback)', ITEMS, SHIELD_MULT, CROWN_DRAIN))
    has, ee_lo, ee_words = ee_has_addr()
    if ON:
        with open(iso, 'rb') as f:
            f.seek(EBOOT_ISO + elf_off(ee_lo))
            assert f.read(16) == b''.join(struct.pack('<I', w) for w in ee_words[:4]), \
                'spot33_reflect EE_B (EE_HAS 0x%08x) not installed: run spot33_reflect.py --apply-code first' % has
    clean_eb = open(CLEAN_EBOOT, 'rb').read()
    assert hashlib.sha256(clean_eb[elf_off(DEAD_LO):elf_off(DEAD_HI)]).hexdigest() == DEAD_SHA
    clean_menu = open(CLEAN_MENU, 'rb').read()
    clean = clean_eb[elf_off(LO):elf_off(HI)]
    code, sites, labels, n = plan()
    mine = code + clean[len(code):]
    print('code: %d words at 0x%08x (room %d)' % (n, LO, (HI - LO) // 4))
    for k in ('ENSURE', 'NEWGAME_GIVE', 'ELIG_MASK', 'ROWMASK', 'MENU_FIX', 'SHIELD', 'PICID0', 'PICID3'):
        print('  %-12s 0x%08x' % (k, labels[k]))
    # --- data (computed first: all checks before any write)
    new_main, rep_m = patch_main(get(iso, MAIN))
    print(rep_m)
    new_lang, rep_l = patch_texts(get(iso, LANG))
    print(rep_l)
    new_exm, rep_x = patch_exmode(get(iso, EXMODE_TEXT))
    print(rep_x)
    new_pics, rep_p = patch_ex_pictures(iso)
    print('EX page header pictures:', rep_p)
    with open(iso, 'rb' if dry else 'r+b') as f:
        f.seek(EBOOT_ISO + elf_off(LO))
        cur = f.read(HI - LO)
        assert cur == clean or cur[:8] == mine[:8], 'EBOOT 0x%08x-0x%08x is neither original nor ours' % (LO, HI)
        # (signature = ENSURE's first 2 words, unchanged since test310; older layouts are rewritten whole)
        want_r = mine if ON else clean
        todo = []
        for area, va, orig, new in sites:
            if area == 'menu':
                assert struct.unpack_from('<%dI' % len(orig), clean_menu, OVL_DATA + va - OVL_BASE) == orig
            else:
                assert struct.unpack_from('<%dI' % len(orig), clean_eb, elf_off(va)) == orig
            f.seek(site_off(area, va))
            c = struct.unpack('<%dI' % len(orig), f.read(4 * len(orig)))
            def ours_w(w, nw):                      # an older build's j/jal into our code (labels move)
                t = ((w & 0x3FFFFFF) << 2) | 0x08000000
                return w == nw or (w >> 26 in (2, 3) and (LO <= t < HI or JT_LO <= t < JT_HI))
            older = c != orig and all(ours_w(x, y) for x, y in zip(c, new))
            assert c in (orig, new) or older, 'site %s 0x%08x: unexpected %s' % (area, va, ' '.join('%08x' % x for x in c))
            w = new if ON else orig
            print('site %-5s 0x%08x: %s -> %s' % (area, va, 'ours' if c == new else ('older ours' if older else 'original'),
                                                  'ours' if w == new else 'original'))
            if c != w:
                todo.append((site_off(area, va), w))
        ro = MENU_SECTOR * SECTOR + OVL_DATA + EXMODE_ROW_VA + 0x20 * EXMODE_ROW_NO - OVL_BASE
        co = OVL_DATA + EXMODE_ROW_VA + 0x20 * EXMODE_ROW_NO - OVL_BASE
        assert clean_menu[co:co + 0x20] == EXMODE_ORIG_ROW
        keys = [struct.unpack_from('<i', clean_menu, OVL_DATA + EXMODE_ROW_VA + 0x20 * k - OVL_BASE)[0] for k in range(33)]
        assert keys[-1] == -1 and 33 not in keys, 'EX Mode table layout changed'
        f.seek(ro)
        crow = f.read(0x20)
        assert crow in (EXMODE_ORIG_ROW, EXMODE_ROW), 'EX Mode table row 22 is neither Chaos nor Sora: not ours'
        wrow = EXMODE_ROW if ON else EXMODE_ORIG_ROW
        print('menu EX Mode row 22: %s -> %s' % ('Sora' if crow == EXMODE_ROW else 'Chaos (original)',
                                                 'Sora' if ON else 'Chaos (original)'))
        if crow != wrow:
            todo.append((ro, struct.unpack('<8I', wrow)))
        print('EBOOT sub-range: %s -> %s' % ('original' if cur == clean else 'ours', 'ours' if ON else 'original'))
        jt_data, jl = jt_plan()
        jt_clean = clean_eb[elf_off(JT_LO):elf_off(JT_HI)]
        jt_mine = jt_data + jt_clean[len(jt_data):]
        f.seek(EBOOT_ISO + elf_off(JT_LO))
        jt_cur = f.read(JT_HI - JT_LO)
        assert jt_cur == jt_clean or jt_cur[:16] == jt_mine[:16], 'dead jump table 0x%08x is neither original nor ours' % JT_LO
        print('level scaling: %d of %d B in the dead jump table 0x%08x (%s -> %s); STASH 0x%08x SCALE 0x%08x' % (
            len(jt_data), JT_HI - JT_LO, JT_LO, 'original' if jt_cur == jt_clean else 'ours', 'ours' if ON else 'original',
            jl['STASH'], jl['SCALE']))
        for it in sorted(SCALE_TAB):
            print('  item %d: Lv1 %d, Lv38 %d, Lv60 %d, Lv100 %d' % (it, *(scale_value(it, L) for L in (1, 38, 60, 100))))
        jt_want = jt_mine if ON else jt_clean
        if jt_cur != jt_want:
            todo.append((EBOOT_ISO + elf_off(JT_LO), struct.unpack('<%dI' % ((JT_HI - JT_LO) // 4), jt_want)))
        if dry:
            print('--dry: nothing written')
            return
        if cur != want_r:
            f.seek(EBOOT_ISO + elf_off(LO))
            f.write(want_r)
        for o, w in todo:
            f.seek(o)
            f.write(struct.pack('<%dI' % len(w), *w))
    if new_main is not None:
        put(iso, MAIN, new_main)
    if new_lang is not None:
        put(iso, LANG, new_lang)
    if new_exm is not None:
        put(iso, EXMODE_TEXT, new_exm)
    for path, data in new_pics.items():
        put(iso, path, data)
    print('done')


if __name__ == '__main__':
    main()
