"""Visibility v2: isolated OBJX output only. Apply after v1, preserve combat scripts/magi."""
import sys,struct,math,json,hashlib,argparse
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_candidates as B
F,E,T=B.F,B.E,B.N.T

def tree(f,fd,i):return T.tree_slot(f,T.leaf_tree_index(fd,i))[2]
def prune(f,old,root):
 dead={id(b) for b in old}-{id(b) for b in T.subgraph(f,root)}
 f.ptrs=[p for p in f.ptrs if id(p[0]) not in dead]
 assert not any(id(p[2]) in dead for p in f.ptrs)
 f.blobs=[b for b in f.blobs if id(b) not in dead]
def keys(f,n):
 l=f.target(n,36);return l,[f.target(l,i*4) for i in range(n.data[19])]
def setkeys(f,n,ks):
 l=f.target(n,36);f.ptrs=[p for p in f.ptrs if p[0] is not l];l.data[:]=bytes(4*len(ks));n.data[19]=len(ks)
 for i,k in enumerate(ks):f.add_ptr(l,i*4,k)
def params(f,k):
 e=f.target(k,8)
 return [(F.u16(e.data,i*8),F.u16(e.data,i*8+2)-12,i*8) for i in range(F.u32(k.data,4))],e

def fire(f,fd):
 t=tree(f,fd,16)
 if F.u32(t.data,4)==100:return
 assert F.u32(t.data,4)==50
 old=T.subgraph(f,t);nl=f.target(t,32)
 for ni in (1,2):
  n=f.target(nl,ni*4);assert F.u16(n.data,4)==34 and n.data[19]==19
  struct.pack_into('<H',n.data,4,68);n.data[17]=68
  _,ks=keys(f,n);native=[k for k in ks if F.u32(k.data,4)>1]
  assert len(native)==3
  for k in native:
   age,span=struct.unpack_from('<hh',k.data);struct.pack_into('<hh',k.data,0,age*2,span*2)
   entries,e=params(f,k)
   for track,o,j in entries:
    start,dur=struct.unpack_from('<hh',e.data,j+4);struct.pack_into('<hh',e.data,j+4,start*2,dur*2)
    if track in (2,3):
     # Native polynomial coefficients: value + velocity*t + quadratic*t*t.
     dims=3 if track==2 else 4
     for power in (1,2):
      for axis in range(dims):
       v=struct.unpack_from('<f',e.data,o+power*16+axis*4)[0]
       struct.pack_into('<f',e.data,o+power*16+axis*4,v/(2**power))
     if track==2:
      for power in range(3):
       for axis in range(3):
        off=o+power*16+axis*4;v=struct.unpack_from('<f',e.data,off)[0];struct.pack_into('<f',e.data,off,v*1.15)
   # First event position remains overridden by exact same-frame update below.
  new=[]
  for tick in range(0,68,2):
   u=min(1,max(0,(tick-48)/16));r=1+1.2*u*u*(3-2*u);a=tick*math.pi/16
   k=F.Blob(None,struct.pack('<hhII',tick,2,1,0));p=F.Blob(None,struct.pack('<HHhh3fI',0,20,tick,2,r*math.cos(a),0,r*math.sin(a)-.2,0xcdcdcdcd))
   f.blobs.extend([k,p]);f.add_ptr(k,8,p);new.append(k)
  setkeys(f,n,sorted(native+new,key=lambda k:F.u16(k.data,0)))
 struct.pack_into('<I',t.data,4,100);prune(f,old,t)

def thunder(f,fd):
 t=tree(f,fd,23);nl=f.target(t,32);oldnode=f.target(nl,8*4)
 if F.u16(oldnode.data,4)==36 and oldnode.data[19]==2:return
 assert F.u16(oldnode.data,4)==23 and oldnode.data[8]==7, 'Impact tree drift; review new baseline'
 assert hashlib.sha256(f.resources('MDL')[30][1].data).hexdigest()=='156e38daaa2cbb15fa9fc898d36d77205e9d61c51355e1ace5f4af6e273d7e38', 'Rebuilt bolt mesh changed; review orientation/scale first'
 old=T.subgraph(f,oldnode)
 src=f.target(f.target(tree(f,fd,22),32),5*4)
 blobs=T.subgraph(f,src);copy={id(b):F.Blob(None,bytes(b.data),b.align) for b in blobs}
 for p in list(f.ptrs):
  if id(p[0]) in copy:f.ptrs.append([copy[id(p[0])],p[1],copy[id(p[2])],p[3]])
 f.blobs.extend(copy.values());n=copy[id(src)]
 for p in f.ptrs:
  if p[0] is nl and p[1]==32:p[2]=n
 n.data[:4]=f.target(nl,5*4).data[:4];struct.pack_into('<HH',n.data,4,36,8);n.data[17]=36
 _,ks=keys(f,n);first,fade=ks[0],ks[2]
 struct.pack_into('<hh',first.data,0,0,28);struct.pack_into('<hh',fade.data,0,28,8)
 for key,isinit in ((f.target(n,32),True),(first,False)):
  entries,e=params(f,key)
  for tr,o,j in entries:
   if not isinit:struct.pack_into('<hh',e.data,j+4,0,36)
   if tr==0:
    for p in range(3):struct.pack_into('<3f',e.data,o+p*16,0,0,0)
   if tr==1:struct.pack_into('<3f',e.data,o,-90,0,0)
   if tr==2:
    struct.pack_into('<3f',e.data,o,20,37,100)
    for p in (1,2):struct.pack_into('<3f',e.data,o+p*16,0,0,0)
   if tr==3:
    struct.pack_into('<4f',e.data,o,150,190,255,128)
    for p in (1,2):struct.pack_into('<4f',e.data,o+p*16,0,0,0,0)
 entries,e=params(f,fade);assert len(entries)==1 and entries[0][0]==3
 _,o,j=entries[0];struct.pack_into('<hh',e.data,j+4,28,8);struct.pack_into('<4f',e.data,o,150,190,255,128);struct.pack_into('<4f',e.data,o+16,0,0,0,-16);struct.pack_into('<4f',e.data,o+32,0,0,0,0)
 setkeys(f,n,[first,fade]);prune(f,blobs and list(copy.values()),n)
 dead={id(b) for b in old};f.ptrs=[p for p in f.ptrs if id(p[0]) not in dead];assert not any(id(p[2]) in dead for p in f.ptrs);f.blobs=[b for b in f.blobs if id(b) not in dead]

def apply(src,kind):
 ei,eff,name,fd=E.split(src);f=F.Fep(fd)
 if kind in ('fire','combined'):fire(f,fd)
 if kind in ('thunder','combined'):thunder(f,fd)
 # Reclaim only unreferenced trailing zero padding, never another tree/resource.
 while f.blobs and not any(f.blobs[-1].data) and not any(p[2] is f.blobs[-1] or p[0] is f.blobs[-1] for p in f.ptrs):f.blobs.pop()
 T.pad_to(f,len(fd));out=f.write();assert F.Fep(out).write()==out
 return E.join(src,ei,eff,name,out)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--kind',choices=['fire','thunder','combined'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert a.source.suffix=='.objx' and not a.out.exists()
 d=a.source.read_bytes();o=apply(d,a.kind);assert apply(o,a.kind)==o;assert apply(d,a.kind)==o;B.audit(d,o,a.kind);a.out.write_bytes(o);print(a.out,hashlib.sha256(o).hexdigest())
