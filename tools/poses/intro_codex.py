"""Codex isolated intro alternatives. 80 frames @30fps, existing 54-bone rig.
VARIANT=arc (default) or spin. Whole-body anticipation, continuous rotation
splines, sequential planted-foot adjustment and shared KH2 idle endpoint.
"""
import os, math
import numpy as np
from scipy.spatial.transform import Rotation, RotationSpline
from scipy.interpolate import CubicSpline
END=80
LOOP=6

def smooth(x):
 x=np.clip(x,0,1);return x*x*x*(10+x*(-15+6*x))

def mix(P,a,b,w):
 return P.Pose({n:P.trs((1-w)*a.loc[n][:3,3]+w*b.loc[n][:3,3],P.quat_to_mat(P.slerp(P.mat_to_quat(a.loc[n][:3,:3]),P.mat_to_quat(b.loc[n][:3,:3]),w))) for n in a.loc})

def arm_pose(P, upper, fore, blade):
 p=P.kh2(2,0);p.aim('r_uparm',upper);p.aim('r_foarm',fore);p.aim_keyblade(blade)
 p.aim('l_uparm',(.25,-.95,.04));p.aim('l_foarm',(.12,-.85,.35));return p

def ik(P,p,side,target,rotation):
 a,b,c=[side+'_'+n for n in ('femur','tibia','foot')]
 w=p.world();h,k,e=[w[n][:3,3] for n in (a,b,c)]
 l1=np.linalg.norm(k-h);l2=np.linalg.norm(e-k);v=target-h;d=np.linalg.norm(v);u=v/d
 d=min(d,l1+l2-.00001);proj=(l1*l1-l2*l2+d*d)/(2*d)
 bend=k-h-u*np.dot(k-h,u)
 if np.linalg.norm(bend)<1e-6:bend=np.cross(u,[1,0,0])
 knee=h+u*proj+P.unit(bend)*math.sqrt(max(0,l1*l1-proj*proj))
 p.aim(a,knee-h);w=p.world();p.aim(b,target-w[b][:3,3]);p._set_world_rot(c,rotation)

def build(P):
 variant=os.environ.get('VARIANT','arc'); spin=variant=='spin'
 field=P.kh2_clip(2);idle=P.kh2_clip(0)
 rest=arm_pose(P,(-.75,-.45,.45),(.15,.95,-.1),(-.3,.3,-.9))
 lift=arm_pose(P,(-.85,.05,.25),(-.15,.9,.32),(-.35,.55,-.75))
 low=arm_pose(P,(-.8,-.5,.3),(-.65,-.05,.75),(-.65,.12,.75))
 across=arm_pose(P,(-.55,-.5,.65),(-.3,.12,.95),(-.45,.6,.65))
 times=[0,10,20,32,50,70,80] if not spin else [0,9,18,25,52,70,80]
 poses=[rest,rest,lift,low,across,idle[140],idle[150]]
 names=['r_clavicle','r_uparm_c','r_uparm','r_arm_help','r_foarm','r_hand','r_fing1a','r_fing3b','r_wep','wep0','wep1']
 curves={n:RotationSpline(times,Rotation.from_matrix([p.loc[n][:3,:3] for p in poses])) for n in names}
 trans={n:CubicSpline(times,np.array([p.loc[n][:3,3] for p in poses]),bc_type='clamped') for n in names}
 out=[]
 for f in range(81):
  if f>=74:out.append((f,idle[150-(80-f)].copy()));continue
  w=smooth((f-(43 if spin else 30))/(31 if spin else 44))
  p=mix(P,field[f%len(field)],idle[150-(80-f)],w)
  env=math.sin(math.pi*f/74)**2
  # Hips initiate, chest follows with a delayed counter-rotation; feet solved below.
  yaw=np.interp(f,[0,10,22,36,51,64,74],[0,5,-8,9,4,-2,0])
  p.turn('hip',(0,1,0),yaw*.45*env)
  p.turn('waist',(0,1,0),yaw*.55*env)
  p.turn('chest',(0,1,0),np.interp(f,[0,14,26,42,58,74],[0,3,-7,8,-3,0])*env)
  p.turn('chest',(1,0,0),3*env)
  p.turn('head',(0,1,0),-yaw*.45*env)
  p.move_root(dx=-.025*env,dy=-.018*env,dz=.012*env)
  for n in names:
   p.loc[n][:3,:3]=curves[n](f).as_matrix();p.loc[n][:3,3]=trans[n](f)
  if spin and 25<=f<=52:
   # one continuous turn, velocity eased only at entry/exit, not at quadrant keys
   u=(f-25)/27;angle=-360*smooth(u)
   wld=p.world();axis=wld['r_hand'][:3,3]-wld['r_foarm'][:3,3]
   p.turn('r_hand',axis,angle)
  # Keep the rigid chain and blade clear of the torso during the inward recovery.
  clearance=28*math.sin(math.pi*f/74)**2
  p.turn('r_uparm',(0,0,1),-clearance)
  # Relaxed free arm lags the torso, then joins the ready pose over the longer settle.
  left=field[f%len(field)].copy()
  swing=math.sin((f-12)*math.pi/43)*env
  left.aim('l_uparm',(.25,-.95,.07+.16*swing));left.aim('l_foarm',(.12,-.85,.32+.15*swing))
  lw=smooth((f-47)/27)
  for n in ['l_uparm','l_foarm','l_hand']:
   p.loc[n][:3,:3]=P.quat_to_mat(P.slerp(P.mat_to_quat(left.loc[n][:3,:3]),P.mat_to_quat(idle[150-(80-f)].loc[n][:3,:3]),lw))
  # Short sequential adjustments: a supporting foot stays planted as the other repositions.
  for side,start,stop in [('l',34,51),('r',50,70)]:
   u=smooth((f-start)/(stop-start));a=field[0].world()[side+'_foot'];b=idle[150-(80-f)].world()[side+'_foot']
   target=(1-u)*a[:3,3]+u*b[:3,3];target[1]+=.035*math.sin(math.pi*u)
   rot=P.quat_to_mat(P.slerp(P.mat_to_quat(a[:3,:3]),P.mat_to_quat(b[:3,:3]),u))
   ik(P,p,side,target,rot)
  out.append((f,p))
 return out
