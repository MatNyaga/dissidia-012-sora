import sys,struct,json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'20261016-trinity-ready-voice'))
import patch_events as V
from spot33_combos import rebuild_arc
def patch(d):
 n=struct.unpack_from('<I',d,4)[0];ch=[struct.unpack_from('<I4sII',d,16+i*16) for i in range(n)]
 c7=next(d[o:o+z] for t,k,o,z in ch if t==7 and k==b'p_se')
 rows7=[struct.unpack_from('<HH',c7,8+i*8) for i in range(struct.unpack_from('<I',c7,4)[0])]
 for motion,block in [(8501,78),(8500,80)]:
  assert [b for m,b in rows7 if m==motion]==[block] and [m for m,b in rows7 if b==block]==[motion]
 k=next(i for i,c in enumerate(ch) if c[0]==8 and c[1]==b'p_se')
 c=bytearray(d[ch[k][2]:sum(ch[k][2:])]);count=struct.unpack_from('<I',c,4)[0];offs=struct.unpack_from('<%dI'%count,c,8)
 for idx,full in [(78,False),(80,True)]:
  o=offs[idx];size=struct.unpack_from('<H',c,o+6)[0];b=bytes(c[o:o+size]);main,one=V.parse(b);rows=V.hitrows(main)
  assert any(e[2]==0x15 and struct.unpack_from('<i',e,8)[0]==V.T.VOICE_A for e in one),'Sora voice guard'
  spec=V.T.FULL if full else V.T.INCOMPLETE
  def expected(shift):return [(a+shift,z+shift,V.T.HP if full and i==len(spec['hits'])-1 else V.T.BRV,33) for i,(a,z) in enumerate(spec['hits'])]
  if rows==expected(120):continue
  assert rows==expected(180),'requires approved 180-tick events from test273/274 or fresh equivalent'
  for e in main:
   a,z=struct.unpack_from('<HH',e)
   if a>0:a-=60
   if z!=65535:z-=60
   struct.pack_into('<HH',e,0,a,z)
  for e in one:
   t=struct.unpack_from('<H',e)[0]
   if t>0:struct.pack_into('<H',e,0,t-60)
  out=V.pack(b[:2],main,one);assert len(out)==size and V.hitrows(main)==expected(120)
  c[o:o+size]=out
 return rebuild_arc(d,{k:bytes(c)})
if __name__=='__main__':
 src,dst=map(Path,sys.argv[1:3]);assert src.resolve()!=dst.resolve()
 d=src.read_bytes();out=patch(d);assert patch(out)==out;dst.write_bytes(out)
