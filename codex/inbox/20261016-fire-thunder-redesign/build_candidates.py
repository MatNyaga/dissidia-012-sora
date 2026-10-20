"""Build isolated spell OBJX candidates from an ISO or OBJX; never writes the source."""
import argparse, hashlib, json, struct, sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import native_orbit as N
import thunder_base as TB
F,E=N.F,TB.E
from spot33_fx import patch_member
import spot33_firefx as FF

def sha(b):return hashlib.sha256(b).hexdigest()
def fire(d):
 ei,eff,name,fd=E.split(d)
 out,path=N.build(fd)
 d=E.join(d,ei,eff,name,out)
 feb=bytearray(E.mpk_member(d,1))
 for ri,phase in ((10,0.),(14,180.)):
  o=16+ri*0x104
  assert F.u32(feb,o+0x24)==9100+(0 if ri==10 else 4)
  assert F.u32(feb,o+0x28)==16
  struct.pack_into('<3f',feb,o,0.,.5,0.)
  struct.pack_into('<3f',feb,o+0xc,0.,phase,0.)
  struct.pack_into('<3f',feb,o+0x18,1.,1.,1.)
  struct.pack_into('<I',feb,o+0x30,0) # countdown, never seek
 d=patch_member(d,1,bytes(feb))
 old=FF.swirl_schedule
 try:
  FF.swirl_schedule=lambda:[(16,9100),(16,9104)]
  d=FF.edit_scripts(d) or d
 finally:FF.swirl_schedule=old
 return d

def thunder(d,bolt,flash):
 d,_=TB.patch(d,thunder='vertical' if bolt else 'none',flashes=flash)
 if bolt:
  # Change the actual visible ground body, not the instant 0x7C5 helper.
  es=E.arc_entries(d);mi=next(i for i,e in enumerate(es) if e[1]==b'magi');e=es[mi]
  m=bytearray(d[e[2]:e[2]+e[3]]);n,nf=struct.unpack_from('<II',m,8);ft=struct.unpack_from('<%df'%nf,m,16+n*204)
  o=next(16+i*204 for i in range(n) if F.u16(m,16+i*204)==0x7c4)
  for p,v in ((18,3.),(19,3.),(57,9.),(58,9.)):
   m[o+0x40+p]=next(i for i,x in enumerate(ft) if abs(x-v)<1e-5)
  d=TB.rebuild_arc(d,{mi:bytes(m)})
 return d

def chunks(d):return {(e[0],e[1]):d[e[2]:e[2]+e[3]] for e in E.arc_entries(d)}
def blocks(d):
 c=chunks(d)[(8,b'p_se')];n=F.u32(c,4)
 return [c[o:o+F.u16(c,o+6)] for o in struct.unpack_from('<%dI'%n,c,8)]
def audit(src,out,kind):
 a,b=chunks(src),chunks(out);assert a.keys()==b.keys()
 changed=[str(k) for k in a if a[k]!=b[k]]
 allowed={(6,b'effe'),(8,b'p_se'),(0,b'magi')}
 # Archive type varies; identify effect and magi by name, script by exact pair.
 assert all(k[1] in (b'effe',b'magi') or k==(8,b'p_se') for k in a if a[k]!=b[k])
 assert len(E.split(out)[1])==848640
 assert E.mpk_member(src,2)==E.mpk_member(out,2),'FXSE sound mapping changed'
 f0,f1=F.Fep(E.split(src)[3]),F.Fep(E.split(out)[3]);assert f1.write()==E.split(out)[3]
 for typ in ('MDL','TEX','ANM'):
  assert [bytes(x.data) for _,x in f0.resources(typ)]==[bytes(x.data) for _,x in f1.resources(typ)],typ
 ba,bb=blocks(src),blocks(out);delta=[i for i,(x,y) in enumerate(zip(ba,bb)) if x!=y]
 t7=a[(7,b'p_se')];r={F.u16(t7,8+i*8):F.u16(t7,10+i*8) for i in range(F.u32(t7,4))}
 assert set(delta)<= {r[10310],r[10313]}
 # Every unrelated FEPA row is identical. Existing sound mappings retained even on reduced flash layers.
 fa,fb=E.mpk_member(src,1),E.mpk_member(out,1)
 rows=[i for i in range(F.u32(fa,12)) if fa[16+i*260:16+(i+1)*260]!=fb[16+i*260:16+(i+1)*260]]
 assert set(rows)<={10,14,32,33}
 if 'fire' in kind or kind=='combined':
  for bi in (r[10310],r[10313]):
   bl=bb[bi];q=F.u16(bl,4);events=[]
   for _ in range(bl[3]):
    size=8+bl[q+3]*4
    if bl[q+2]==0x19 and F.u32(bl,q+8) in set(range(9100,9114))|{53,54}:events.append((F.u16(bl,q),F.u32(bl,q+8)))
    q+=size
   assert events==[(16,9100),(16,9104)],events
 return dict(source_sha256=sha(src),candidate_sha256=sha(out),objx_bytes=len(out),effe_bytes=848640,changed_chunks=changed,changed_script_blocks=delta,changed_fepa_rows=rows,checks=['FEP exact roundtrip','FXSE byte identity','all MDL/TEX/ANM bytes identical','non-target archive chunks identical','only Firaga script blocks changed','only allowed FEPA rows changed','two Fire spawns, no static release spawns'] if delta else ['FEP exact roundtrip','FXSE byte identity','all MDL/TEX/ANM bytes identical','non-target archive chunks identical','scripts byte-identical','only allowed FEPA rows changed'])
def apply(d,kind):
 if kind in ('fire','combined'):d=fire(d)
 if kind!='fire':d=thunder(d,kind in ('thunder-bolt','thunder','combined'),kind in ('thunder-flashes','thunder','combined'))
 return d

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('--out',type=Path,required=True);p.add_argument('--kind',choices=['fire','thunder-bolt','thunder-flashes','thunder','combined'],default='combined');p.add_argument('--dry',action='store_true');args=p.parse_args()
 d=Path(args.source).read_bytes() if args.source.endswith('.objx') else E.load_objx(args.source,'obj/p_sev120.objx')
 out=apply(d,args.kind);report=audit(d,out,args.kind)
 assert apply(out,args.kind)==out,'idempotence';assert apply(d,args.kind)==out,'determinism'
 report.update(kind=args.kind,baseline=args.source,status='STATIC PASS; runtime acceptance pending',checks=report['checks']+['second application byte-identical','repeat build byte-identical'])
 print(json.dumps(report,indent=2))
 if not args.dry:
  assert not args.out.exists(),'refuse overwrite';args.out.write_bytes(out);args.out.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
