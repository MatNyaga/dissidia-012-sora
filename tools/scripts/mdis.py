"""Tiny MIPS (Allegrex) decoder for OVL_MENU_APP.ELF code inside an ISO: python3 mdis.py ISO START_VA END_VA (hex)."""
import struct,sys
R=['zero','at','v0','v1','a0','a1','a2','a3','t0','t1','t2','t3','t4','t5','t6','t7','s0','s1','s2','s3','s4','s5','s6','s7','t8','t9','k0','k1','gp','sp','fp','ra']
d=open(sys.argv[1],'rb'); base=185056*0x800
def word(va):
    d.seek(base+va-0x089DD4C0+0x54); return struct.unpack('<I',d.read(4))[0]
def dis(w,va):
    op=w>>26; rs=(w>>21)&31; rt=(w>>16)&31; rd=(w>>11)&31; sa=(w>>6)&31; imm=w&0xffff; simm=imm-0x10000 if imm&0x8000 else imm
    I={0x23:'lw',0x25:'lhu',0x21:'lh',0x29:'sh',0x2b:'sw',0x24:'lbu',0x20:'lb',0x28:'sb'}
    if op in I: return '%s %s,%d(%s)'%(I[op],R[rt],simm,R[rs])
    if op==0x0d: return 'ori %s,%s,0x%x'%(R[rt],R[rs],imm)
    if op==0x0c: return 'andi %s,%s,0x%x'%(R[rt],R[rs],imm)
    if op==0x0e: return 'xori %s,%s,0x%x'%(R[rt],R[rs],imm)
    if op==0x09: return 'addiu %s,%s,%d'%(R[rt],R[rs],simm)
    if op==0x0f: return 'lui %s,0x%x'%(R[rt],imm)
    if op==0x03: return 'jal 0x%08x'%(((w&0x3ffffff)<<2)|(va&0xf0000000))
    if op==0x02: return 'j 0x%08x'%(((w&0x3ffffff)<<2)|(va&0xf0000000))
    if op in (4,5,1,6,7): return 'b(op%d) %s,%s,%08x'%(op,R[rs],R[rt],va+4+simm*4)
    if op==0:
        f=w&63
        if f==0: return 'sll %s,%s,%d'%(R[rd],R[rt],sa) if w else 'nop'
        F={0x21:'addu',0x23:'subu',0x25:'or',0x24:'and',0x0a:'movz',0x0b:'movn',0x08:'jr',0x2a:'slt',0x2b:'sltu'}
        return '%s %s,%s,%s'%(F.get(f,'f%x'%f),R[rd],R[rs],R[rt])
    return 'op%x %08x'%(op,w)
a,b=int(sys.argv[2],16),int(sys.argv[3],16)
for va in range(a,b,4):
    w=word(va); print('%08x %08x %s'%(va,w,dis(w,va)))
