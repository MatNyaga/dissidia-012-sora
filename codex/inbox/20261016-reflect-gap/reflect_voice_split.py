"""Read-only audit or isolated OBJX output; never writes an ISO or overlay.
--voice-slot must be an existing, separately verified voice slot (NOT a snd_ slot).
"""
import argparse, hashlib, json, struct, sys
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = next(p for p in Path(__file__).resolve().parents if (p/'tools/scripts/fep_edit.py').exists())
sys.path.insert(0, str(ROOT/'tools/scripts'))
import fep_edit as E
from spot33_combos import rebuild_arc

def chunks(d):
    return E.arc_entries(d)

def patch(d, slot=None):
    es = chunks(d)
    ti = next(i for i,e in enumerate(es) if e[0]==7)
    ci = next(i for i,e in enumerate(es) if e[0]==8)
    def get(i):
        e=es[i]; return d[e[2]:e[2]+e[3]]
    t=get(ti); c=bytearray(get(ci)); n=struct.unpack_from('<I',c,4)[0]
    rows={struct.unpack_from('<H',t,8+i*8)[0]:struct.unpack_from('<H',t,10+i*8)[0] for i in range(struct.unpack_from('<I',t,4)[0])}
    report=[]
    if slot is not None:
        assert 0<=slot<=42 and slot!=37, 'Only existing voice slots 0..42, excluding 37; verify bank contents separately.'
    for motion in (470,471):
        b=rows[motion]; offs=list(struct.unpack_from('<%dI'%n,c,8)); o=offs[b]
        me,size=struct.unpack_from('<HH',c,o+4); k=o+me; evs=[]
        for _ in range(c[o+3]):
            length=8+4*c[k+3]; evs.append((k,bytes(c[k:k+length]))); k+=length
        assert k==o+size
        vs=[(p,e) for p,e in evs if e[2]==0x15]
        report.append({'motion':motion,'block':b,'one_shots':[{'frame':struct.unpack_from('<H',e)[0],'op':hex(e[2]),'conditions':list(e[4:8]),'params':list(struct.unpack_from('<%dI'%e[3],e,8))} for _,e in evs]})
        if slot is None: continue
        guards=[(p,e) for p,e in vs if struct.unpack_from('<I',e,8)[0] in (2210037,21910037)]
        assert len(guards)==1 and len(vs) in (1,2), 'Unexpected guard voice layout'
        p,e=guards[0]; assert e[:4]==struct.pack('<HBB',0,0x15,3) and e[4:8] in (bytes(4),bytes([0,1,0,0]))
        base=struct.unpack_from('<I',e,8)[0]-37
        new=bytearray(e); new[5]=2; struct.pack_into('<I',new,8,base+slot)
        if len(vs)==2:
            assert e[5]==1 and any(x==bytes(new) for _,x in vs), 'Existing EX voice differs; stop instead of stacking'
            continue
        assert e[5]==0, 'Normal-only without paired EX event; inspect first'
        c[p+5]=1
        c[o+size:o+size]=new; c[o+3]+=1; struct.pack_into('<H',c,o+6,size+len(new))
        offs=[v+len(new) if v>o else v for v in offs]; struct.pack_into('<%dI'%n,c,8,*offs)
    out=rebuild_arc(d,{ci:bytes(c)}) if bytes(c)!=get(ci) else d
    for i,e in enumerate(es):
        if i!=ci:
            ne=chunks(out)[i]; assert out[ne[2]:ne[2]+ne[3]]==get(i)
    return out,report

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__); a.add_argument('iso'); a.add_argument('--voice-slot',type=int); a.add_argument('--out',type=Path); a.add_argument('--self-test',action='store_true'); v=a.parse_args()
    assert (v.voice_slot is None)==(v.out is None), 'Supply --voice-slot and --out together, or neither for audit'
    d=E.load_objx(v.iso,'obj/p_sev120.objx'); out,r=patch(d,v.voice_slot)
    evidence={'input':v.iso,'objx_sha256':hashlib.sha256(d).hexdigest(),'guard_blocks':r}
    if v.self_test:
        # Slot 7 is ONLY a structural fixture, not a proposed Reflect voice.
        trial,_=patch(d,7); assert patch(trial,7)[0]==trial
        try: patch(trial,8)
        except AssertionError: pass
        else: raise AssertionError('Conflicting EX voice accepted')
        evidence['self_test']='PASS: in-memory fixture slot 7; idempotence, conflict rejection, all non-script chunks unchanged. No audio/runtime verification.'
    if v.out:
        assert v.out.suffix=='.objx' and not v.out.exists(), 'Only new isolated .objx output allowed'
        with v.out.open('xb') as f: f.write(out)
    print(json.dumps(evidence,indent=2))
