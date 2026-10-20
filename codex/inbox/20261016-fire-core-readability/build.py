"""Native Fire index-only options; offline references, no ISO writer."""
import sys,struct,hashlib,argparse
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'./codex/inbox/20261016-fire-thunder-visibility-v2');import revise as R
import fep_dump as D
import numpy as np
P=Path(__file__).resolve().parent
SOURCE=Path('./codex/inbox/20261016-fire-appearance-v3/smooth-fire-o0f.tex').read_bytes()
def decode(t):
 pal=np.frombuffer(t[16448:17472],np.uint8).reshape(256,4);idx=np.frombuffer(D.unswizzle(t[48:16432],128,128),np.uint8).reshape(128,128)
 return pal,idx,pal[idx,:3]
def option(kind):
 pal,idx,rgb=decode(SOURCE);v=rgb.astype(float)
 if kind=='core':
  # Fill hollow atlas lobe with existing flame content; retain original ring outline.
  v[:,64:]=np.maximum(v[:,64:],v[:,:64])
 if kind=='softer':
  for lo,hi in ((0,64),(64,128)):
   a=v[:,lo:hi].copy();pad=np.pad(a,((1,1),(1,1),(0,0)),mode='edge');b=np.zeros_like(a)
   for y,w1 in enumerate((1,2,1)):
    for x,w2 in enumerate((1,2,1)):b+=pad[y:y+128,x:x+64]*w1*w2/16
   v[:,lo:hi]=b
 # Lift midtones while keeping exact black and maximum; quantize to existing palette.
 v=255*np.power(v/255,1.0 if kind=='core' else (.72 if kind=='brighter' else .8))
 q=[];palette=pal[:,:3].astype(float)
 for row in v:q.append(((row[:,None,:]-palette[None,:,:])**2).sum(2).argmin(1).astype(np.uint8))
 out=bytearray(SOURCE);out[48:16432]=R.E.swizzle8(np.stack(q).tobytes(),128,128)
 assert out[:48]==SOURCE[:48] and out[16432:]==SOURCE[16432:]
 return bytes(out)
def apply(d,kind):
 ei,eff,n,fd=R.E.split(d);f=R.F.Fep(fd);assert len(f.resources('TEX'))==21
 for idx,expected in ((15,'725a4a83ffd869b5b62f086105e68e754775c5181b871f81a03f381a6853c5c9'),(21,'3ef97c2680cb833101c0defd012a0bffd5764bb0824f367b15f458334c04b1f0')):
  assert hashlib.sha256(f.resources('MDL')[idx][1].data).hexdigest()==expected,'Fire mesh/material drift: review before applying texture'
 blob=next(b for r,b in f.resources('TEX') if R.F.u32(r.data,4)==f.key_base()|15);new=option(kind)
 assert bytes(blob.data) in (SOURCE,new),'Fire texture changed; review current base'
 assert R.F.u32(R.tree(f,fd,16).data,4)==100
 blob.data[:]=new;nf=f.write();assert R.F.Fep(nf).write()==nf
 assert len(nf)==len(fd) and all(blob.off+48<=i<blob.off+16432 for i,(a,b) in enumerate(zip(fd,nf)) if a!=b)
 out=R.E.join(d,ei,eff,n,nf);assert len(R.E.split(out)[1])==848640
 assert R.E.mpk_member(out,1)==R.E.mpk_member(d,1) and R.E.mpk_member(out,2)==R.E.mpk_member(d,2)
 assert all(v==R.B.chunks(out)[k] for k,v in R.B.chunks(d).items() if k[1]!=b'effe')
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--kind',choices=['brighter','softer','core'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists();d=a.source.read_bytes();o=apply(d,a.kind);assert apply(o,a.kind)==o;a.out.write_bytes(o);print(hashlib.sha256(o).hexdigest())
