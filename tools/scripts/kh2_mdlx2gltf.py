"""KH2 .mdlx -> glTF (no Blender): bones, skinned meshes, UVs, HD texture. For weapons/props to feed add_keyblade.py.

  python3 -I kh2_mdlx2gltf.py MODEL.mdlx TEXTURE.(dds|png) OUT_DIR NAME

Decoder adapted from OpenKH (Apache-2.0, commit 7a3b945: OpenKh.Ps2 VifUnpacker/VpuPacket, OpenKh.Kh2 ModelSkeletal),
via kh2_export/logs/decode_mdlx.py. Output units = KH2 cm x 0.01 (m), Y up, like kingdom_key.glb. Joint world
matrices = decoded bone matrices; inverseBindMatrices = their inverses; vertices are in bind pose.
"""
import json
import math
import os
import struct
import sys

import numpy as np
from PIL import Image

def unpack_vif(code):
 mem=bytearray(16384);pc=0;mask=0
 def read(fmt):
  nonlocal pc
  v=struct.unpack_from('<'+fmt,code,pc)[0];pc+=struct.calcsize(fmt);return v & 0xffffffff
 while pc<len(code):
  op=read('I');cmd=(op>>24)&127;num=(op>>16)&255
  if cmd&0x60==0x60:
   dest=(op&0x1ff)*16;vn=(op>>26)&3;vl=(op>>24)&3;enabled=(op>>28)&1
   fmt=(['I','H','B','H'] if op&0x400==0 else ['I','h','b','h'])[vl]
   for n in range(num):
    m=(mask>>((n&3)*8))&255 if enabled else 0
    if vn in [0,1]:
     vals=[read(fmt)] if vn==0 else [read(fmt),read(fmt)]
     vals=vals*4 if vn==0 else vals*2
     for j in range(4):
      if (m>>(2*j))&3==0:struct.pack_into('<I',mem,dest,vals[j])
      dest+=4
    else:
     for j in range(4):
      if (m>>(2*j))&3==0:
       saved=pc;value=read(fmt)
       if vn==2 and j==3:pc=saved
       struct.pack_into('<I',mem,dest,value)
      dest+=4
   pc=(pc+3)&~3
  elif cmd in [0,1]:pass
  elif cmd in [0x14,0x17]:break
  elif cmd==0x20:mask=read('I')
  elif cmd in [0x30,0x31]:
   for _ in range(4):read('I')
  else:raise ValueError(f'Unsupported VIF command {cmd:x} at {pc:x}')
 return mem

def vpu(mem,boneids,matrices):
 h=struct.unpack_from('<16i',mem,0)
 ranges=struct.unpack_from('<'+'i'*h[15],mem,h[6]*16)
 idx=[struct.unpack_from('<4i',mem,h[5]*16+i*16) for i in range(h[4])]
 coords=[struct.unpack_from('<4f',mem,h[13]*16+i*16) for i in range(h[12])]
 assert sum(ranges)==len(coords),(ranges,len(coords))
 positions=[];v=0
 for k,count in enumerate(ranges):
  for j in range(count):positions.append((boneids[k],coords[v]));v+=1
 groups=[]
 if h[10]>0:
  counts=struct.unpack_from('<'+'i'*h[10],mem,h[11]*16);p=h[11]*16+4*h[10]
  for amount,count in enumerate(counts):
   p=(p+15)&~15
   for _ in range(count):
    ids=struct.unpack_from('<'+'i'*(amount+1),mem,p);p+=4*(amount+1);groups.append([positions[i] for i in ids])
 else:groups=[[p] for p in positions]
 vertices=[];uv=[];weights=[];faces=[]
 for i,(u,v,ind,func) in enumerate(idx):
  assert 0<=ind<len(groups)
  pos=np.zeros(4);w=[]
  for bone,coord in groups[ind]:
   c=np.array(coord);c[3]=1 if c[3]==0 else c[3];pos+=matrices[bone]@c;w.append([bone,float(c[3])])
  assert abs(sum(x[1] for x in w)-1)<0.002,(ind,w)
  vertices.append(pos[:3].tolist());uv.append([u/4096,1-v/4096]);weights.append(w)
  if func in [0,0x20]:faces.append([i,i-2,i-1])
  if func in [0,0x30]:faces.append([i,i-1,i-2])
  assert func in [0,0x10,0x20,0x30],func
 # Strip triangles may carry the previous packet's last two indices, as in OpenKH.
 assert all(min(f)>=-2 for f in faces)
 return vertices,uv,weights,faces

def decode(path,ident):
 raw=open(path,'rb').read();entries=[struct.unpack_from('<HH4sII',raw,16+16*i) for i in range(struct.unpack_from('<I',raw,4)[0])];entry=next(x for x in entries if x[0]==4);data=raw[entry[3]:entry[3]+entry[4]];base=0x90
 typ,sub,attr,shadow,bonecount,texcount,boneoff,bonedata,ng=struct.unpack_from('<4IHHIII',data,base)
 bones=[];mats=[]
 for i in range(bonecount):
  b=struct.unpack_from('<4h2i12f',data,base+boneoff+64*i);sx,sy,sz=b[6:9];rx,ry,rz=b[10:13];tx,ty,tz=b[14:17]
  assert np.allclose([sx,sy,sz],[1,1,1]),('bone scale',i,sx,sy,sz)
  x=np.array([[1,0,0,0],[0,math.cos(rx),-math.sin(rx),0],[0,math.sin(rx),math.cos(rx),0],[0,0,0,1]])
  y=np.array([[math.cos(ry),0,math.sin(ry),0],[0,1,0,0],[-math.sin(ry),0,math.cos(ry),0],[0,0,0,1]])
  z=np.array([[math.cos(rz),-math.sin(rz),0,0],[math.sin(rz),math.cos(rz),0,0],[0,0,1,0],[0,0,0,1]])
  t=np.eye(4);t[:3,3]=[tx,ty,tz];local=t@z@y@x@np.diag([sx,sy,sz,1]);parent=b[2]
  assert parent<i
  glob=mats[parent]@local if parent>=0 else local;mats.append(glob);bones.append(dict(name=f'Bone{i}',parent=parent,matrix=glob.tolist()))
 meshes=[];cursor=base+boneoff+64*bonecount
 for gi in range(ng):
  attrs,tex,polys,buf,alt,dma,bm,plen,res=struct.unpack_from('<IIIHHIIII',data,base+32+gi*32)
  start=(cursor+15)&~15;vif=data[start:base+dma];packets=[];packet=None
  for j in range(plen):
   qwc=struct.unpack_from('<H',data,base+dma+j*16)[0]
   if packet is None:packet=qwc
   elif qwc==0:packets.append(packet);packet=None
  assert packet is None
  bmc=struct.unpack_from('<I',data,base+bm)[0];blist=struct.unpack_from('<'+'i'*bmc,data,base+bm+4);bonelists=[[]]
  for b in blist:
   if b==-1:bonelists.append([])
   else:bonelists[-1].append(b)
  assert len(bonelists)==len(packets),(gi,len(bonelists),len(packets))
  mesh=dict(group=gi,material=tex,attributes=attrs,vertices=[],uv=[],weights=[],faces=[]);vp=0
  for k,qwc in enumerate(packets):
   mem=unpack_vif(vif[vp:vp+qwc*16]);vp+=qwc*16
   vertices,uv,weights,faces=vpu(mem,bonelists[k],mats);off=len(mesh['vertices']);mesh['vertices']+=vertices;mesh['uv']+=uv;mesh['weights']+=weights;mesh['faces'] +=[[a+off for a in f] for f in faces]
  assert vp==len(vif),(gi,vp,len(vif))
  assert all(min(f)>=0 and max(f)<len(mesh['vertices']) for f in mesh['faces']), (gi,mesh['faces'][:5])
  mesh['header_polygon_count']=polys
  pass  # print(ident,'group',gi,'verts',len(mesh['vertices']),'triangles',len(mesh['faces']),'declared polygons',polys)
  meshes.append(mesh);cursor=base+bm+4+4*bmc
 return dict(identifier=ident,bones=bones,meshes=meshes,texture_count=texcount,source=str(path))


def write_gltf(dec, tex_path, out_dir, name):
    os.makedirs(out_dir, exist_ok=True)
    img = Image.open(tex_path).convert('RGBA')
    img.save(os.path.join(out_dir, name + '.png'))
    mats = []
    for b in dec['bones']:                              # cm -> m on the translation only (no bone scale)
        m = np.array(b['matrix'], float)
        m[:3, 3] *= 0.01
        mats.append(m)
    buf = bytearray()
    views, accs = [], []

    def add(arr, ctype, typ, target=None, minmax=False):
        arr = np.ascontiguousarray(arr)
        while len(buf) % 4:
            buf.append(0)
        views.append({'buffer': 0, 'byteOffset': len(buf), 'byteLength': arr.nbytes})
        buf.extend(arr.tobytes())
        a = {'bufferView': len(views) - 1, 'componentType': ctype, 'count': len(arr), 'type': typ}
        if minmax:
            a['min'], a['max'] = arr.min(0).tolist(), arr.max(0).tolist()
        accs.append(a)
        return len(accs) - 1
    nodes = []
    for i, b in enumerate(dec['bones']):
        local = mats[i] if b['parent'] < 0 else np.linalg.inv(mats[b['parent']]) @ mats[i]
        nodes.append({'name': b['name'], 'matrix': local.T.reshape(-1).tolist()})
    for i, b in enumerate(dec['bones']):
        if b['parent'] >= 0:
            nodes[b['parent']].setdefault('children', []).append(i)
    ibm = np.array([np.linalg.inv(m).T for m in mats], np.float32).reshape(-1, 16)
    skin = {'joints': list(range(len(mats))), 'inverseBindMatrices': add(ibm, 5126, 'MAT4')}
    meshes = []
    for m in dec['meshes']:
        P = np.array(m['vertices'], np.float32) * 0.01
        UV = np.array(m['uv'], np.float32)
        UV[:, 1] = 1 - UV[:, 1]
        J = np.zeros((len(P), 4), np.uint16)
        W = np.zeros((len(P), 4), np.float32)
        for v, ws in enumerate(m['weights']):
            for k, (bone, w) in enumerate(ws[:4]):
                J[v, k], W[v, k] = bone, w
        F = []
        for f in m['faces']:
            a, b2, c = (np.array(m['vertices'][i]) for i in f)
            if np.linalg.norm(np.cross(b2 - a, c - a)) > 1e-6:
                F.append(f)
        idx = np.array(F, np.uint32).reshape(-1)
        meshes.append({'name': '%s_Mesh%d' % (name, m['group']), 'primitives': [{'attributes': {
            'POSITION': add(P, 5126, 'VEC3', minmax=True), 'TEXCOORD_0': add(UV, 5126, 'VEC2'),
            'JOINTS_0': add(J, 5123, 'VEC4'), 'WEIGHTS_0': add(W, 5126, 'VEC4')},
            'indices': add(idx, 5125, 'SCALAR'), 'material': 0}]})
    roots = [i for i, b in enumerate(dec['bones']) if b['parent'] < 0]
    for k in range(len(meshes)):
        nodes.append({'name': meshes[k]['name'], 'mesh': k, 'skin': 0})
    g = {'asset': {'version': '2.0', 'generator': 'kh2_mdlx2gltf.py'}, 'scene': 0,
         'scenes': [{'nodes': roots + list(range(len(dec['bones']), len(nodes)))}], 'nodes': nodes,
         'meshes': meshes, 'skins': [skin],
         'materials': [{'name': name + '_Texture0', 'doubleSided': True,
                        'pbrMetallicRoughness': {'baseColorTexture': {'index': 0}, 'metallicFactor': 0}}],
         'textures': [{'source': 0}], 'images': [{'uri': name + '.png'}],
         'buffers': [{'byteLength': len(buf), 'uri': name + '.bin'}], 'bufferViews': views, 'accessors': accs}
    open(os.path.join(out_dir, name + '.bin'), 'wb').write(bytes(buf))
    json.dump(g, open(os.path.join(out_dir, name + '.gltf'), 'w'))
    allp = np.concatenate([np.array(m['vertices']) for m in dec['meshes']]) * 0.01
    print('%s: %d bones, %d meshes, bounds %s .. %s' % (name, len(mats), len(meshes), allp.min(0).round(3),
                                                        allp.max(0).round(3)))


if __name__ == '__main__':
    path, tex, out_dir, name = sys.argv[1:5]
    dec = decode(path, name)
    write_gltf(dec, tex, out_dir, name)
