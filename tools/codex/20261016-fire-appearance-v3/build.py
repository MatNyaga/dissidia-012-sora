"""Deterministic native CLUT8 resampling. Existing TEX only, no resource/animation growth."""
import sys,struct,json,hashlib,argparse
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'./tools/codex/20261016-fire-thunder-visibility-v2')
import revise as R
import fep_dump as D
import numpy as np
P=Path(__file__).resolve().parent

def encode_smooth(tex):
 assert tex[:4]==b'TEX\0';w,h=struct.unpack_from('<II',tex,28);assert (w,h)==(128,128)
 px=np.frombuffer(D.unswizzle(tex[48:48+w*h],w,h),np.uint8).reshape(h,w)
 assert np.array_equal(px[::2],px[1::2]),'Expected duplicate-row source; review new texture'
 pal=np.frombuffer(tex[48+w*h+16:48+w*h+16+1024],np.uint8).reshape(256,4)
 assert np.all(pal[:,3]==255),'Expected native additive premultiplied palette'
 rgb=pal[px[::2],:3].astype(np.int32)
 # Keep two KH2 atlas halves separate; never sample across their seam.
 out=np.empty((h,w,3),np.int32)
 for y in range(h):
  i=y//2;j=max(0,i-1) if y%2==0 else min(63,i+1)
  row=3*rgb[i]+rgb[j]
  for lo,hi in ((0,64),(64,128)):
   v=row[lo:hi];left=np.concatenate([v[:1],v[:-1]]);right=np.concatenate([v[1:],v[-1:]])
   out[y,lo:hi]=(6*v+left+right+16)//32
 # Quantize ONLY to original palette; all palette bytes and alpha remain exact.
 q=[];palette=pal[:,:3].astype(np.int32)
 for row in out:
  dist=((row[:,None,:]-palette[None,:,:])**2).sum(2);q.append(dist.argmin(1).astype(np.uint8))
 idx=np.stack(q).tobytes();new=bytearray(tex);new[48:48+w*h]=R.E.swizzle8(idx,w,h)
 assert new[:48]==tex[:48] and new[48+w*h:]==tex[48+w*h:]
 return bytes(new)

def apply(data):
 ei,eff,name,fd=R.E.split(data);f=R.F.Fep(fd);key=f.key_base()|15
 resources=f.resources('TEX');assert len(resources)==21
 rec,blob=next((r,b) for r,b in resources if R.F.u32(r.data,4)==key)
 expected=(P/'source-fire-o0f.tex').read_bytes();new=(P/'smooth-fire-o0f.tex').read_bytes()
 assert bytes(blob.data) in (expected,new),'Fire texture drift; inspect current source first'
 # This candidate accepts only the already-approved Fire timing; never installs motion.
 assert R.F.u32(R.tree(f,fd,16).data,4)==100
 blob.data[:]=new;outfd=f.write();assert len(outfd)==len(fd) and R.F.Fep(outfd).write()==outfd
 out=R.E.join(data,ei,eff,name,outfd);assert len(R.E.split(out)[1])==848640
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists();d=a.source.read_bytes();o=apply(d);assert apply(o)==o and apply(d)==o;a.out.write_bytes(o);print(hashlib.sha256(o).hexdigest())
if __name__=='__main__':main()
