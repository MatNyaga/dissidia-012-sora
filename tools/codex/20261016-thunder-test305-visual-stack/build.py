"""Exact-byte visual patches. Never serializes/rebuilds FEP or writes ISO."""
import sys,struct,hashlib,json,argparse,importlib.util
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('./tools/codex')
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
C=module('core_candidate',ROOT/'20261016-fire-core-readability/build.py')
T=module('thunder_candidate',ROOT/'20261016-thunder-canonical-readability/build.py');R=C.R
KINDS=('fire','thunder-body','thunder-flashes','combined')
def unique(data,part):
 o=data.find(part);assert o>=0 and data.find(part,o+1)<0,'Ambiguous container';return o
def apply(data,kind):
 assert kind in KINDS
 fd=R.E.split(data)[3];f=R.F.Fep(fd);fo=unique(data,fd);out=bytearray(data);allowed=set()
 def put(o,b):out[o:o+len(b)]=b;allowed.update(range(o,o+len(b)))
 if kind in ('fire','combined'):
  assert len(f.resources('TEX'))==21 and R.F.u32(R.tree(f,fd,16).data,4)==100
  for idx,h in ((15,'725a4a83ffd869b5b62f086105e68e754775c5181b871f81a03f381a6853c5c9'),(21,'3ef97c2680cb833101c0defd012a0bffd5764bb0824f367b15f458334c04b1f0')):
   assert hashlib.sha256(f.resources('MDL')[idx][1].data).hexdigest()==h,'Fire geometry/material drift'
  b=next(b for r,b in f.resources('TEX') if R.F.u32(r.data,4)==(f.key_base()|15));new=C.option('core');assert bytes(b.data) in (C.SOURCE,new),'Fire texture drift'
  put(fo+b.off+48,new[48:16432])
 if kind in ('thunder-body','thunder-flashes','combined'):
  a=R.B.chunks(data);ref=T.REF.read_bytes();rc=R.B.chunks(ref)
  # Exact Claude-confirmed test305 v2 MAGI only; never edit behavior bytes.
  assert hashlib.sha256(a[(1,b'magi')]).hexdigest()=='3260398da1f3acb96caa56fccf2ac4de83a0f62351438e9d932c0edd0a41d2a2', 'Exact confirmed test305 Thundaga v2 movement required'
  assert a[(1,b'atkp')]==rc[(1,b'atkp')], 'Canonical hit table required'
  feb=R.E.mpk_member(data,1)
  assert all(R.F.u32(feb,16+row*260+40)==leaf for row,leaf in ((31,22),(32,23),(33,23))), 'Thunder effect binding drift'
  n=f.target(f.target(R.tree(f,fd,23),32),32);assert R.F.u16(n.data,2)==272 and R.F.u16(n.data,4)==23
 if kind in ('thunder-body','combined'):
  current=T.scale_edits(data);reference=T.scale_edits(ref);assert len(current)==len(reference)
  for (o,_,_),(_,old,new) in zip(current,reference):
   assert bytes(out[fo+o:fo+o+4]) in (old,new),'Thunder scale drift';put(fo+o,new)
 if kind in ('thunder-flashes','combined'):
  feb=R.E.mpk_member(data,1);base=unique(data,feb)
  for row,v in ((32,.7),(33,.35)):
   o=16+row*260;assert R.F.u32(feb,o+40)==23
   for axis in range(3):
    off=o+24+axis*4;old=struct.unpack_from('<f',feb,off)[0];assert abs(old-1.4)<1e-5 or abs(old-v)<1e-5;put(base+off,struct.pack('<f',v))
 out=bytes(out);diff={i for i,(a,b) in enumerate(zip(data,out)) if a!=b};assert len(out)==len(data) and diff<=allowed
 newfd=R.E.split(out)[3];nf=R.F.Fep(newfd)
 # Full pointer graph offsets and addends exact => every allocation/serial/init address retains alignment.
 def pointers(f):return [(s.off,o,t.off,a) for s,o,t,a in f.ptrs]
 assert pointers(f)==pointers(nf)
 assert [b.off for b in f.blobs]==[b.off for b in nf.blobs]
 assert len(R.E.split(out)[1])==848640 and len(nf.resources('TEX'))==21
 assert R.E.mpk_member(data,2)==R.E.mpk_member(out,2)
 assert all(v==R.B.chunks(out)[k] for k,v in R.B.chunks(data).items() if k[1]!=b'effe')
 return out,{'kind':kind,'changed_bytes':len(diff),'source_sha256':hashlib.sha256(data).hexdigest(),'output_sha256':hashlib.sha256(out).hexdigest(),'effe_bytes':848640,'TEX_count':21,'checks':['exact-offset byte patch','all pointer records and blob offsets exact','no FEP serialization','all non-effect chunks and FXSE exact','no allocation/lifetime/serial/header edits'],'input_alignment_warnings':sum(1 for b in f.blobs if b.kinds & {'n20_data','n24_data'} and b.off%16!=12),'runtime':'UNTESTED'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--kind',choices=KINDS,required=True);p.add_argument('--out',type=Path);p.add_argument('--dry',action='store_true');a=p.parse_args();assert a.dry or (a.out and not a.out.exists());d=a.source.read_bytes();o,r=apply(d,a.kind);assert apply(o,a.kind)[0]==o and apply(d,a.kind)[0]==o
 if not a.dry:a.out.write_bytes(o)
 print(json.dumps(r,indent=2))
