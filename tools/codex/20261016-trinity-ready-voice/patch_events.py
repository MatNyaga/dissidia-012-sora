"""Guarded standalone OBJX event edit; no ISO/controller writer. Only blocks78/80."""
import sys,struct,json,copy,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;R=next(x for x in P.parents if (x/'tools/scripts').exists());sys.path.insert(0,str(R/'tools/scripts'))
import spot33_trinity as T
from spot33_combos import rebuild_arc
SHIFT=24;VOICE=21910042
def parse(b):
 nm,no=b[2:4];o=8;main=[];one=[]
 for i in range(nm):
  n=b[o+5];z=12+n*4;main.append(bytearray(b[o:o+z]));o+=z
 assert o==struct.unpack_from('<H',b,4)[0]
 for i in range(no):
  n=b[o+3];z=8+n*4;one.append(bytearray(b[o:o+z]));o+=z
 assert o==len(b)
 return main,one
def hitrows(main):
 return [(*struct.unpack_from('<HH',e),*struct.unpack_from('<ii',e,12)) for e in main if e[4]==0]
def pack(head,main,one):
 body=b''.join(main);tail=b''.join(one)
 return head+bytes([len(main),len(one)])+struct.pack('<HH',8+len(body),8+len(body)+len(tail))+body+tail
def patch_block(b,full):
 main,one=parse(b);spec=T.FULL if full else T.INCOMPLETE
 assert any(e[2]==0x15 and struct.unpack_from('<i',e,8)[0]==T.VOICE_A for e in one),'not owner33 Sora voice mapping'
 old=[(a,z,T.HP if full and i==len(spec['hits'])-1 else T.BRV,33) for i,(a,z) in enumerate(spec['hits'])]
 new=[(a+SHIFT,z+SHIFT,atk,g) for a,z,atk,g in old]
 rows=hitrows(main);assert rows in (old,new),'input does not match approved timing'
 if rows==old:
  for e in main:
   a,z=struct.unpack_from('<HH',e)
   if e[4]==0 or a>0:a+=SHIFT
   if z!=65535:z+=SHIFT
   struct.pack_into('<HH',e,0,a,z)
  for e in one:
   t=struct.unpack_from('<H',e)[0]
   if t>0:struct.pack_into('<H',e,0,t+SHIFT)
 if full:
  # Bar-fill callback owns selected voice42. Remove launch voices (including superseded23).
  one=[e for e in one if not(e[2]==0x15 and struct.unpack_from('<H',e)[0]==0)]
  impact=spec['hits'][-1][0]+SHIFT
  # Replace the old pre-hit heavy + impact pair with ONE stronger native impact, without stacking.
  one=[e for e in one if not(e[2]==3 and (struct.unpack_from('<H',e)[0],struct.unpack_from('<i',e,8)[0]) in ((impact-2,21900088),(impact,21900089),(impact,21900091)))]
  one.append(bytearray(T.one_ev(impact,3,(21900091,0,0))))
 out=pack(b[:2],main,one);assert hitrows(parse(out)[0])==new
 return out
def patch_objx(d):
 ch=[struct.unpack_from('<I4sII',d,16+i*16) for i in range(struct.unpack_from('<I',d,4)[0])]
 i7=next(i for i,c in enumerate(ch) if c[0]==7);i8=next(i for i,c in enumerate(ch) if c[0]==8)
 c7=d[ch[i7][2]:ch[i7][2]+ch[i7][3]];rows=[struct.unpack_from('<HH',c7,8+i*8) for i in range(struct.unpack_from('<I',c7,4)[0])]
 for motion,block in [(8501,78),(8500,80)]:assert [mid for mid,b in rows if b==block]==[motion] and [b for mid,b in rows if mid==motion]==[block]
 c=bytearray(d[ch[i8][2]:ch[i8][2]+ch[i8][3]]);count=struct.unpack_from('<I',c,4)[0];offs=list(struct.unpack_from('<%dI'%count,c,8))
 for idx,full in [(78,False),(80,True)]:
  o=offs[idx];size=struct.unpack_from('<H',c,o+6)[0];new=patch_block(bytes(c[o:o+size]),full);c[o:o+size]=new
  offs=[x+len(new)-size if x>o else x for x in offs];struct.pack_into('<%dI'%count,c,8,*offs)
 return rebuild_arc(d,{i8:bytes(c)})
def selftest():
 report={}
 for full in (False,True):
  old=T.build(T.FULL if full else T.INCOMPLETE,b'\0\0',21900000);new=patch_block(old,full);main,one=parse(new)
  speech=[struct.unpack_from('<i',e,8)[0] for e in one if e[2]==0x15 and struct.unpack_from('<H',e)[0]==0]
  assert speech==([] if full else [T.VOICE_B])
  assert patch_block(new,full)==new
  report['full' if full else 'incomplete']={'idempotent':True,'hits':hitrows(main),'start_voices':speech,'new_line_count':sum(e[2]==0x15 and struct.unpack_from('<i',e,8)[0]==VOICE for e in one)}
 # Dispatch semantics: all4incomplete grades use78, full4 uses80; no global controller code changed.
 report['motion_script_added_line_counts']=[0,0,0,0,0];report['voice_owner']='bar fill edge callback, not attack motion'
 report['runtime_repeat_charge_CPUCloud_rematch']='pending; static event count is not runtime proof'
 return report
if __name__=='__main__':
 if len(sys.argv)==1:print(json.dumps(selftest(),indent=2))
 else:
  src,dst=map(Path,sys.argv[1:3]);assert src.resolve()!=dst.resolve(),'write a staging copy, not the input'
  d=src.read_bytes();out=patch_objx(d);assert patch_objx(out)==out;dst.write_bytes(out)
