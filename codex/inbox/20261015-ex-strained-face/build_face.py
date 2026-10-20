"""Read-only current GMO/OBJX -> isolated, structurally guarded charge face candidate."""
import argparse,sys,struct,json,hashlib
from pathlib import Path
from PIL import Image
R=Path('.');sys.path.insert(0,str(R/'tools/scripts'))
import gmo,gim
from gltf2gmo import chunk,arg,png_to_gim
from gmo_motion import motions
P=Path(__file__).resolve().parent
H=lambda d:hashlib.sha256(d).hexdigest()
def items(d):
 a=[];gmo.walk(d,16,len(d),0,a);return a
def build(d,od,out):
 a=items(d);eye=next(x for x in a if x[2]==15 and x[5]=='0_EYE');_,eo,_,eh,ez,_=eye
 face=next(x for x in a if x[2]==10 and x[5]=='sora_tex1');_,to,_,th,tz,_=face
 fg=d[d.index(b'MIG.00.1PSP',to,to+tz):to+tz];im=gim.decode(fg).convert('RGB');assert im.size==(256,256)
 # Refuse unknown native face artwork; new motion/keychain/effect changes are allowed.
 assert H(fg)==json.loads((P/'assets/pins.json').read_text())['face_gim_sha256'],'face texture changed; rebase artwork'
 patched=any(x[5]=='codex_strain_face' for x in a)
 if patched:
  assert b'6_EX_STRAIN' in d[eo:eo+ez];result=d
 else:
  assert b'target:p_sev100_01.tm2' in d[eo:eo+ez] and b'6_' not in d[eo:eo+ez],'eye channel already customized; merge manually'
  pb=next(x for x in gim.blocks(fg,16,len(fg),[]) if x[0]==5);ph=gim.header(fg,pb[1]+pb[3]);pal=fg[ph['px']:ph['px']+1024]
  palim=Image.new('P',(1,1));palim.putpalette([pal[i+j] for i in range(0,1024,4) for j in range(3)])
  neutral=im.crop((4,24,100,104));strain=neutral.copy()
  eyes=Image.open(P/'assets/eyes.png').convert('RGB');mouth=Image.open(P/'assets/mouth.png').convert('RGB')
  strain.paste(eyes,(0,0));strain.paste(mouth,(20,56))
  atlas=Image.new('RGB',(128,256));atlas.paste(neutral,(0,0));atlas.paste(strain,(0,96));idx=atlas.quantize(palette=palim,dither=Image.Dither.NONE);idx.save(out/'atlas.png')
  gb=bytearray(png_to_gim(str(out/'atlas.png')));bb=gim.blocks(gb,16,len(gb),[]);ib=next(x for x in bb if x[0]==4);ih=gim.header(gb,ib[1]+ib[3]);pb=next(x for x in bb if x[0]==5);ph=gim.header(gb,pb[1]+pb[3]);gb[ih['px']:ih['px']+128*256]=idx.tobytes();gb[ph['px']:ph['px']+1024]=pal
  # Exact native neutral indices prevent any ordinary Sora face pixel change.
  origib=next(x for x in gim.blocks(fg,16,len(fg),[]) if x[0]==4);origih=gim.header(fg,origib[1]+origib[3]);assert origih['fmt']==5 and origih['order']==0
  for y in range(80):gb[ih['px']+y*128:ih['px']+y*128+96]=fg[origih['px']+(24+y)*256+4:origih['px']+(24+y)*256+100]
  newtex=chunk(10,'codex_strain_face',arg(0x8012,b'codex_strain_face.tm2\0')+arg(0x8013,struct.pack('<I',len(gb))+gb))
  children=[]
  for o,t,h,z in gmo.chunks(d,eo+eh,eo+ez):
   raw=d[o+8:o+z];label=raw.split(b'\0')[0];payload=(len(label)+4)//4*4
   if label.startswith(b'target:'):
    lab=b'target:p_sev120_sora1.tm2\0';lab+=b'\0'*((-len(lab))%4);children.append(arg(t,lab+struct.pack('<4I',4,24,96,80)))
   elif label.startswith(b'source:'):children.append(arg(t,b'source:codex_strain_face.tm2\0'))
   elif label.startswith(b'default:'):children.append(d[o:o+z])
   else:
    b=bytearray(raw)
    for k in range(payload,len(b),4):
     w=struct.unpack_from('<I',b,k)[0]
     if not w&3:struct.pack_into('<I',b,k,w&~0xffc) # Same waits/jumps; every ordinary state restores exact neutral.
    children.append(arg(t,b))
  lab=b'6_EX_STRAIN\0';lab+=b'\0'*((-len(lab))%4);children.append(arg(0x80f1,lab+struct.pack('<II',(6<<7)|(2<<12)|(2<<22),5)))
  neweye=chunk(15,'0_EYE',b''.join(children));_,bo,_,bh,bz,_=next(x for x in a if x[2]==15 and x[5]=='TexAnm');blind=chunk(15,'TexAnm',b''.join(neweye if o==eo else d[o:o+z] for o,t,h,z in gmo.chunks(d,bo+bh,bo+bz)))
  _,mo,_,mh,mz,_=next(x for x in a if x[2]==3 and x[5]=='model-0');model=chunk(3,'model-0',b''.join(newtex+blind if o==bo else d[o:o+z] for o,t,h,z in gmo.chunks(d,mo+mh,mo+mz)))
  _,fh,fz=struct.unpack_from('<HHI',d,16);result=d[:16]+chunk(2,'file-0',d[16+fh:mo]+model+d[mo+mz:16+fz])
 # Resolve _801B by current motion ordering and verify type7 maps motion ID8101 to that block.
 idx=next(i for i,(n,o,z) in enumerate(motions(d)[0]) if n=='_801B')
 ent=[struct.unpack_from('<I4sII',od,16+i*16) for i in range(struct.unpack_from('<I',od,4)[0])]
 t7=next(e for e in ent if e[:2]==(7,b'p_se'));b=od[t7[2]:t7[2]+t7[3]]
 rows=[struct.unpack_from('<4H',b,8+i*8) for i in range(struct.unpack_from('<I',b,4)[0])]
 assert any(row[0]==8101 and row[1]==idx for row in rows),('unexpected charge route',idx,[r for r in rows if r[0]==8101])
 e=next(e for e in ent if e[:2]==(8,b'p_se'));base=e[2];off=base+struct.unpack_from('<I',od,base+8+idx*4)[0];assert struct.unpack_from('<H',od,off)[0]==idx
 cur=off+8;matches=[];ob=bytearray(od)
 for _ in range(od[off+2]):
  lo,hi,op,n=struct.unpack_from('<HHBB',od,cur);params=struct.unpack_from('<%dI'%n,od,cur+12)
  if op==0x14 and params in [(0,2),(0,6)]:matches.append(cur+16);struct.pack_into('<I',ob,cur+16,6)
  cur+=12+n*4
 assert len(matches)==1
 assert all(i in matches for i,(a,b) in enumerate(zip(od,ob)) if a!=b)
 for n,o,z in motions(d)[0]:
  no,nz=next((a,b) for nn,a,b in motions(result)[0] if nn==n);assert d[o:o+z]==result[no:no+nz]
 newitems=items(result)
 for dep,o,t,h,z,n in a:
  if t in [4,5,7,8,9,10] or (t==15 and n in ['1_LIP','2_WEP']):assert any(result[oo:oo+zz]==d[o:o+z] for _,oo,tt,hh,zz,nn in newitems if t==tt and n==nn),(t,n)
 tex=next(x for x in items(result) if x[5]=='codex_strain_face');o,z=tex[1],tex[4];at=gim.decode(result[result.index(b'MIG.00.1PSP',o,o+z):o+z]).convert('RGB');assert at.crop((0,0,96,80)).tobytes()==im.crop((4,24,100,104)).tobytes()
 im.save(out/'before.png');im.paste(at.crop((0,96,96,176)),(4,24));im.save(out/'after.png')
 (out/'charge-face.gmo').write_bytes(result);(out/'charge-face.objx').write_bytes(ob)
 report={'input_gmo_sha256':H(d),'output_gmo_sha256':H(result),'input_objx_sha256':H(od),'output_objx_sha256':H(ob),'all_motions_byte_identical':True,'existing_geometry_materials_textures_lip_weapon_unchanged':True,'ordinary_face_exact_neutral_restoration':True,'charge_block':idx,'changed_objx_byte_offsets':[i for i,(a,b) in enumerate(zip(od,ob)) if a!=b],'target_xywh':[4,24,96,80],'source_xy':[0,96],'runtime_verified':False}
 (out/'validation.json').write_text(json.dumps(report,indent=2));return result,bytes(ob),report
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('gmo');ap.add_argument('objx');ap.add_argument('--out',required=True);args=ap.parse_args();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
 d=Path(args.gmo).read_bytes();o=Path(args.objx).read_bytes();r,b,report=build(d,o,out)
 print(json.dumps(report,indent=2))
