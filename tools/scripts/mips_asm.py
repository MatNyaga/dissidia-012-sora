"""Tiny MIPS (Allegrex) assembler for the few instructions our EBOOT patches use.

asm(lines, base) -> list of u32 words. Lines look like Ghidra's listing:
  'addiu sp,sp,-0x10', 'sw s0,0x0(sp)', 'jal 0x088cb3b4', 'bne a1,t2,BLANK', 'BLANK:' (label).
A leading '_' (Ghidra's delay-slot marker) is ignored. Branch targets may be labels or addresses.
'.word X' emits a data word (X = number or label, e.g. a jump-table entry pointing at cave code).
Also lwc1/swc1/mtc1/add.s (FPU) and div/mfhi (checked against FUN_08a3a0b8's own words).
"""
import re

REGS = ('zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 '
        's0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra').split()
R = {n: i for i, n in enumerate(REGS)}

I_OPS = {'addiu': 9, 'slti': 10, 'sltiu': 11, 'andi': 12, 'ori': 13, 'xori': 14}
MEM_OPS = {'lb': 32, 'lh': 33, 'lw': 35, 'lbu': 36, 'lhu': 37, 'sb': 40, 'sh': 41, 'sw': 43}
R3_OPS = {'addu': 33, 'subu': 35, 'and': 36, 'or': 37, 'xor': 38, 'slt': 42, 'sltu': 43}


def num(s):
    return int(s, 0)


def F(s):
    assert s[0] == 'f' and 0 <= int(s[1:]) < 32, s
    return int(s[1:])


def asm(lines, base):
    items = []
    labels = {}
    for line in lines:
        line = line.split('#')[0].strip()
        if not line:
            continue
        if line.endswith(':'):
            labels[line[:-1]] = base + 4 * len(items)
            continue
        items.append(line.lstrip('_'))

    def target(s):
        return labels[s] if s in labels else num(s)

    out = []
    for i, line in enumerate(items):
        pc = base + 4 * i
        op, _, rest = line.partition(' ')
        a = [x.strip() for x in rest.split(',')] if rest else []

        def branch(opc, rs, rt, t):
            off = (target(t) - (pc + 4)) >> 2
            assert -0x8000 <= off < 0x8000, line
            return opc << 26 | R[rs] << 21 | rt << 16 | (off & 0xFFFF)

        if op == 'nop':
            w = 0
        elif op == '.word':
            w = target(a[0]) & 0xFFFFFFFF
        elif op in I_OPS:
            imm = num(a[2])
            w = I_OPS[op] << 26 | R[a[1]] << 21 | R[a[0]] << 16 | (imm & 0xFFFF)
        elif op == 'li':
            imm = num(a[1])                                   # like the game's compiler:
            assert -0x8000 <= imm < 0x10000, line             # ori for 0..0xFFFF, addiu below 0
            w = (13 if imm >= 0 else 9) << 26 | R[a[0]] << 16 | (imm & 0xFFFF)
        elif op == 'lui':
            w = 15 << 26 | R[a[0]] << 16 | (num(a[1]) & 0xFFFF)
        elif op in MEM_OPS:
            m = re.fullmatch(r'(-?0x[0-9a-fA-F]+|-?\d+)\((\w+)\)', a[1])
            w = MEM_OPS[op] << 26 | R[m.group(2)] << 21 | R[a[0]] << 16 | (num(m.group(1)) & 0xFFFF)
        elif op in R3_OPS:
            w = R[a[1]] << 21 | R[a[2]] << 16 | R[a[0]] << 11 | R3_OPS[op]
        elif op == 'move':
            w = R[a[1]] << 21 | R[a[0]] << 11 | 37          # or rd,rs,zero (the game's form)
        elif op in ('movz', 'movn'):                        # Allegrex has MIPS IV conditional moves
            w = R[a[1]] << 21 | R[a[2]] << 16 | R[a[0]] << 11 | (10 if op == 'movz' else 11)
        elif op in ('lwc1', 'swc1'):                        # FPU load/store: lwc1 f12,0x18(a0)
            m = re.fullmatch(r'(-?0x[0-9a-fA-F]+|-?\d+)\((\w+)\)', a[1])
            w = (0x31 if op == 'lwc1' else 0x39) << 26 | R[m.group(2)] << 21 | F(a[0]) << 16 | (num(m.group(1)) & 0xFFFF)
        elif op == 'mtc1':                                  # mtc1 a1,f13
            w = 0x11 << 26 | 4 << 21 | R[a[0]] << 16 | F(a[1]) << 11
        elif op == 'add.s':                                 # add.s fd,fs,ft
            w = 0x11 << 26 | 16 << 21 | F(a[2]) << 16 | F(a[1]) << 11 | F(a[0]) << 6
        elif op == 'div':
            w = R[a[0]] << 21 | R[a[1]] << 16 | 26
        elif op == 'mfhi':
            w = R[a[0]] << 11 | 16
        elif op == 'mult':
            w = R[a[0]] << 21 | R[a[1]] << 16 | 24
        elif op == 'mflo':
            w = R[a[0]] << 11 | 18
        elif op == 'jr':
            w = R[a[0]] << 21 | 8
        elif op in ('j', 'jal'):
            t = target(a[0])
            assert t >> 28 == pc >> 28 and t % 4 == 0, line
            w = (2 if op == 'j' else 3) << 26 | (t >> 2) & 0x3FFFFFF
        elif op == 'beq':
            w = branch(4, a[0], R[a[1]], a[2])
        elif op == 'bne':
            w = branch(5, a[0], R[a[1]], a[2])
        elif op == 'b':
            w = branch(4, 'zero', 0, a[0])
        elif op == 'bltz':
            w = branch(1, a[0], 0, a[1])
        elif op == 'bgez':
            w = branch(1, a[0], 1, a[1])
        elif op == 'blez':
            w = branch(6, a[0], 0, a[1])
        elif op == 'bgtz':
            w = branch(7, a[0], 0, a[1])
        else:
            raise ValueError('unknown instruction: ' + line)
        out.append(w)
    return out
