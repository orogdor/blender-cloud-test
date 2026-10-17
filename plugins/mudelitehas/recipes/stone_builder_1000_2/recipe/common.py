"""Common, independently testable input and calibration logic for stone-builder 1000/2."""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
import numpy as np
from PIL import Image

RECIPE="stone-builder-1000-2"
AXES=('front','right','top')
BUDGET=1000

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_json(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def resolve(base,name):
    p=(Path(base)/name).resolve()
    if not p.is_file():raise ValueError('Missing input: '+str(p))
    return p

def calibrate(view):
    direction=view['direction'];ppm=float(view['pixels_per_meter']);u,v=map(float,view['origin_pixels'])
    if ppm<40 or ppm>3000:raise ValueError('Implausible pixels_per_meter')
    # x=left/right, y=ground-to-head, z=front-to-back. Positive image V goes down.
    jac={
      'front':[[ppm,0,0],[0,-ppm,0]],
      'right':[[0,0,-ppm],[0,-ppm,0]],
      'top':[[ppm,0,0],[0,0,ppm]],
      'back':[[-ppm,0,0],[0,-ppm,0]],
    }
    if direction not in jac:raise ValueError('Unsupported camera direction: '+str(direction))
    return np.asarray(jac[direction],float),np.asarray([u,v],float)

def read_inputs(manifest_path,allow_synthetic=False):
    path=Path(manifest_path).resolve();m=load_json(path)
    if m.get('recipe')!=RECIPE or m.get('quad_budget')!=BUDGET or m.get('level')!=2:
        raise ValueError('Wrong recipe, budget or level')
    if m.get('rest_pose')!='T-pose' or m.get('character')!='stone_age_builder':
        raise ValueError('Require same neutral T-pose Stone Age builder')
    review=m.get('visual_review') or {}
    if not isinstance(review.get('reviewer'),str) or not review['reviewer'].strip():
        raise ValueError('Visual reviewer missing')
    if review.get('status')!='approved' or not review.get('reviewed_at') or not review.get('notes'):
        raise ValueError('Actual visual review must be approved, timestamped and explained')
    if not all(m.get(k) is True for k in ['same_identity','same_pose','registered_scale','limbs_separated']):
        raise ValueError('Identity/T-pose/scale/limb registration has not been confirmed')
    if m.get('synthetic_test') and not allow_synthetic:
        raise ValueError('Synthetic test references cannot be used for a production build')
    views=m.get('views') or []
    if len(views)<3:raise ValueError('Need >= 3 genuine independent image directions')
    if len({v.get('direction') for v in views})!=len(views):
        raise ValueError('Duplicate projection direction; do not count mirrored views')
    if not set(AXES).issubset(v['direction'] for v in views):
        raise ValueError('Must provide front, right, top independent directions')
    if sum(bool(v.get('source_type') in ('observed','reviewed_generated')) for v in views)<3:
        raise ValueError('Unverified/procedural inputs cannot be treated as image evidence')
    jj=[];bb=[];imgs=[];masks=[];hashes={};view_order=[]
    for v in views:
        name=v['direction'];view_order.append(name)
        if v.get('is_mirror_copy'):raise ValueError('Mirrored copy is not a new view: '+name)
        image=resolve(path.parent,v['image']);maskfile=resolve(path.parent,v['mask'])
        for label,p in [('image',image),('mask',maskfile)]:
            digest=sha256(p);expected=v.get(label+'_sha256')
            if not expected or digest!=expected:
                raise ValueError('Image/mask hash absent or mismatched: '+name+'/'+label)
            hashes[name+'/'+label]=digest
        im=Image.open(image).convert('RGB');mk=Image.open(maskfile).convert('L')
        if im.size!=mk.size:raise ValueError('Mask/image dimensions differ: '+name)
        mask=np.asarray(mk)>=128
        if mask.mean()<.005 or mask.mean()>.75:raise ValueError('Invalid mask occupancy: '+name)
        J,b=calibrate(v)
        if len(v.get('landmark_notes',[]))<3:
            raise ValueError('Requires at least three reviewed registration landmarks per view: '+name)
        if not (0<=b[0]<im.width and 0<=b[1]<im.height):
            raise ValueError('Origin outside image: '+name)
        jj.append(J);bb.append(b);imgs.append(im);masks.append(mask)
    jac=np.stack(jj);offset=np.stack(bb)
    dirs=np.cross(jac[:,0],jac[:,1]);dirs/=np.linalg.norm(dirs,axis=1)[:,None]
    if np.linalg.matrix_rank(dirs,tol=.15)!=3:
        raise ValueError('Independent viewing direction rank must equal 3')
    # This checks declared registration, not visual consistency of the images.
    scale=[float(v['pixels_per_meter']) for v in views]
    if max(scale)/min(scale)>1.12:raise ValueError('View scale disagreement >12%')
    return {'manifest':m,'masks':masks,'images':imgs,'J':jac,'offset':offset,'views':view_order,
            'hashes':hashes,'manifest_file':path,'synthetic_test':bool(m.get('synthetic_test'))}

def project(xyz,jac,offset):
    xyz=np.asarray(xyz,float)
    return np.einsum('nd,vkd->nvk',xyz,jac)+offset[None,:,:]
