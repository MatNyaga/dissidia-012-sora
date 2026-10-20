"""Build unbound native MDL/TEX resources from KH2 shell0. Never edits FEP, OBJX, ISO or resource reservations."""
import struct,sys,json,hashlib,math
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'tools/scripts/fep_edit.py').exists());sys.path.insert(0,str(ROOT/'tools/scripts'))
import fep_edit as E,fep as F,kh2_pax_dump as K,fep_dump as FD
from PIL import Image,ImageDraw
out=Path(__file__).parent/'prototype';out.mkdir(exist_ok=True)
iso=ROOT/'dumps/ULUS10566-test245-tumble.iso';obj=E.load_objx(str(iso),'obj/p_sev120.objx');_,eff,_,fd=E.split(obj);assert len(eff)==848640;S=F.Fep(fd)
rec,blob=S.resources('MDL')[64];template=bytes(blob.data[:F.u32(rec.data,8)]);assert F.u32(template,0x34)==1
assert struct.unpack_from('<6I',template,F.u32(template,0x38))[1:3]==(0x99,8)
source=ROOT/'kh2_export/raw/kh2_fifth/original/magic/REFLECT_3.mag';d=source.read_bytes();p=next(d[o:o+s] for t,_,_,o,s in K.bar(d) if t==18);el,_,x=K.pax_elements(p);_,ds=K.dpx_parse(p[x:]);D=ds[0];L=K.dpd_lists(D);o=L[3][0];pa,va=struct.unpack_from('<2I',D,o+20);pc,vc=struct.unpack_from('<2H',D,o+32);v=[struct.unpack_from('<3h',D,o+16+va+6*j) for j in range(vc)];q=o+16+pa;assert D[q+1]==6 and struct.unpack_from('<H',D,q+2)[0]==pc;q+=16
corners=[];uvall=[[],[]]
for j in range(pc):
 ids=struct.unpack_from('<4H',D,q+16);uv=struct.unpack_from('<8H',D,q+24)
 quad=[(*v[ids[k]],*D[q+4*k:q+4*k+4],uv[2*k],uv[2*k+1]) for k in range(4)]
 for k in (0,2,1,2,3,1):corners.append(quad[k]) # reverse winding for Y reflection
 for k in range(4):
  for a in range(2):uvall[a].append(uv[2*k+a])
 q+=40
assert D[q:q+2]==b'\xff\xff' and len(corners)==pc*6
w,h,idx,pal=E.from_kh2(str(source)+':0:0');periods=[w*16,h*16];uvbase=[min(uvall[a])//periods[a]*periods[a] for a in range(2)]
scale=1.4/342.;ymid=(min(x[1] for x in v)+max(x[1] for x in v))/2
points=[(c[0]*scale,-(c[1]-ymid)*scale,c[2]*scale) for c in corners];ext=[max(abs(x[a]) for x in points) for a in range(3)]
head=bytearray(template[:128]);struct.pack_into('<I',head,8,0);struct.pack_into('<I',head,28,0) # unbound self/texture keys
struct.pack_into('<10f',head,64,*ext,0,0,0,1,1,0,0);struct.pack_into('<6I',head,104,3,0x99,8,0,len(corners),128)
body=bytearray();decoded=[];maxerr=0
for c,pt in zip(corners,points):
 uv=[round((c[7+a]-uvbase[a])/16) for a in range(2)];assert all(0<=t<=255 for t in uv)
 rgba=[round(min(255,c[3+a]*2)/17) for a in range(4)];color=sum(x<<(4*a) for a,x in enumerate(rgba))
 xyz=[round(pt[a]/ext[a]*127) if ext[a] else 0 for a in range(3)];body+=struct.pack('<BBHbbbB',*uv,color,*xyz,0)
 dec=[xyz[a]/127*ext[a] for a in range(3)];maxerr=max(maxerr,max(abs(pt[a]-dec[a]) for a in range(3)));decoded.append(dec)
mdl=bytes(head+body);tex=E.make_tex(0,w,h,idx,pal);assert len(mdl)==128+len(corners)*8 and len(tex)==9280
# Check actual emitted fields and texture swizzle round-trip, not only intended inputs.
assert struct.unpack_from('<6I',mdl,104)==(3,0x99,8,0,768,128)
assert FD.unswizzle(tex[48:48+w*h],w,h)==idx
(out/'shell0-unbound.mdl').write_bytes(mdl);(out/'shell0-unbound.tex').write_bytes(tex)
# Mesh-only source/native comparison, no claimed native shader/runtime preview.
im=Image.new('RGB',(1000,540),(17,25,34));dr=ImageDraw.Draw(im)
for panel,pts in enumerate((points,decoded)):
 projected=[(p[0]*.866-p[2]*.5,p[1]*-.85+(p[0]*.5+p[2]*.866)*.45) for p in pts]
 for j in range(0,len(pts),3):
  pp=[(250+panel*500+a*135,285+b*135) for a,b in projected[j:j+3]];dr.line(pp+[pp[0]],fill=(100,210,230),width=1)
 dr.text((20+panel*500,20),['KH2 shell0 — transformed source','Decoded native MDL — 8-bit positions'][panel],fill='white')
dr.text((20,510),'Offline geometry comparison. No game shader, animation, attachment or runtime verification.',fill='white');im.save(out/'shell0-comparison.png')
manifest={'baseline':str(iso.relative_to(ROOT)),'objx_sha256':hashlib.sha256(obj).hexdigest(),'source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(d).hexdigest(),'model':0,'pdata':0,'texture':0,'source_PAX_element0':el[0],'triangles':256,'vertices_unindexed':768,'native_mdl_bytes':len(mdl),'native_tex_bytes':len(tex),'keys':'zero placeholders; NOT assigned to any live resource','native_template':'test245 MDL64 header; primitive changed to3 triangle list; shader flags retained provisionally','positions':{'source_units':'raw signed OMD integers','transform':'(x, -(y - ymid), z) * scale','ymid':ymid,'scale':scale,'radius_m':1.4,'extents':ext,'max_axis_quantization_error_m':maxerr,'winding':'reversed after Y reflection'},'uv':{'source':'unsigned16 fixed4 fractional bits','tile_offsets_fixed':uvbase,'converted':'round((uv - tile_offset)/16), unnormalized texels','uv_transform':[1,1,0,0],'wrapping':'preserved by removing whole tiles; V may exceed64 and requires wrap sampler, not clamp; runtime not verified'},'color':'source128→255 then RGBA4444; palette alpha expanded once by existing from_kh2','attachment_proposal':{'bone':'root','FEPA_translation':[0,0,0],'basis':'centered prototype, provisional; source PAX bind and offsets not directly transplanted','timing':'EX op19 at frame0; finite lifetime must cover existing guard0–36 script ticks and cleanly fade/cancel; not authored here'},'checks':['256 source quads-to-triangles counts checked','all source indices in range','768 native vertices within signed8-bit range','native draw offsets/count/stride checked','TEX swizzle roundtrip byte-identical','baseline read-only; no FEP mutation or ISO write'],'blockers':['shared resource reservation pending','runtime mesh/material/UV/attachment and winding need verification','no native tree or FEPA/script binding yet']}
(out/'shell0-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('MDL',len(mdl),'TEX',len(tex),'total',len(mdl)+len(tex),'max error',maxerr)
