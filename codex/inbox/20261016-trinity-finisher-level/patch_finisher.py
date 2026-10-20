import sys,struct,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2]
sys.path[:0]=[str(R/'tools/scripts'),str(P.parent/'20261016-trinity-ready-voice')]
import patch_events as E,sscf
from spot33_combos import rebuild_arc
from spot33_soundids import bank_base
def patch(d,slot):
 ch=[struct.unpack_from('<I4sII',d,16+i*16) for i in range(struct.unpack_from('<I',d,4)[0])]
 def idx(t=None,k=None):return next(i for i,c in enumerate(ch) if (t is None or c[0]==t) and (k is None or c[1]==k))
 def chunk(i):return d[ch[i][2]:sum(ch[i][2:])]
 ib=idx(k=b'snd_');it=idx(8,b'p_se');i7=idx(7,b'p_se');bank=bytearray(chunk(ib));base=bank_base(bank);assert base==21900000
 t7=chunk(i7);rows=[struct.unpack_from('<HH',t7,8+i*8) for i in range(struct.unpack_from('<I',t7,4)[0])]
 assert [b for m,b in rows if m==8500]==[80] and [m for m,b in rows if b==80]==[8500]
 c=bytearray(chunk(it));o=struct.unpack_from('<I',c,8+80*4)[0];z=struct.unpack_from('<H',c,o+6)[0];blk=bytes(c[o:o+z]);main,one=E.parse(blk)
 last=E.hitrows(main)[-1];assert last[0] in (237,393) and last[2:]==(1801,33)
 cues=[e for e in one if e[2]==3 and struct.unpack_from('<H',e)[0]==last[0] and struct.unpack_from('<i',e,8)[0] in (base+91,base+slot)]
 assert len(cues)==1
 count=struct.unpack_from('<I',bank,12)[0];blob=(P/'finisher-only.vag').read_bytes();oldentries=list(sscf.entries(bank))
 if count==slot+1:
  _,pos,size,rate=oldentries[slot];assert bytes(bank[pos:pos+size])==blob
  assert struct.unpack_from('<i',cues[0],8)[0]==base+slot
  return d
 assert slot==count and slot>=96,'requires confirmed next-free append slot'
 assert struct.unpack_from('<i',cues[0],8)[0]==base+91
 row=bytearray(bank[32+91*32:64+91*32]);end=32+count*32
 oldpayload=[bytes(bank[a:a+n]) for i,a,n,r in oldentries]
 for i,a,n,r in oldentries:
  if a:struct.pack_into('<I',bank,32+i*32+4,a+32)
 bank[end:end]=row;struct.pack_into('<II',bank,end+4,len(bank),len(blob));bank+=blob
 struct.pack_into('<II',bank,8,len(bank),count+1);assert len(bank)<=540000
 for (i,a,n,r),payload in zip(list(sscf.entries(bank))[:count],oldpayload):assert bytes(bank[a:a+n])==payload
 struct.pack_into('<i',cues[0],8,base+slot);c[o:o+z]=E.pack(blk[:2],main,one)
 out=rebuild_arc(d,{ib:bytes(bank),it:bytes(c)})
 for i in range(len(ch)):
  if i not in (ib,it):
   _,_,a,n=struct.unpack_from('<I4sII',out,16+i*16);assert out[a:a+n]==chunk(i)
 return out
if __name__=='__main__':
 src,dst=map(Path,sys.argv[1:3]);slot=int(sys.argv[3]);assert src.resolve()!=dst.resolve()
 d=src.read_bytes();out=patch(d,slot);assert patch(out,slot)==out;dst.write_bytes(out)
 print('Finisher-only staging patch; shared91 preserved; slot',slot)
