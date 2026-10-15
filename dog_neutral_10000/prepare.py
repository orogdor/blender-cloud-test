"""Register the actually reviewed standing-dog sheet; images precede any geometry."""
from pathlib import Path
import base64,hashlib,io,json,sys
import numpy as np
from PIL import Image
from scipy.ndimage import label,binary_closing,binary_fill_holes,map_coordinates,distance_transform_edt
ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT.parent))
from mudelitehas.command import parse_command
sheet=Image.open(ROOT/'02_rest_four_views.jpg').convert('RGB');W,H=sheet.size
x=np.linspace(-.43,.43,145);y=np.linspace(-.99,1.02,337);z=np.linspace(-.035,1.285,221)
arrays={'x':x,'y':y,'z':z};cal={}
for name,cell,axis,flip,anchor_fraction in [('front',(0,0),x,False,.5),('left',(1,0),y,False,.49),('back',(0,1),x,True,.5),('right',(1,1),y,True,.49)]:
 cx,cy=cell;rect={'front':(0,0,470,590),'left':(480,0,W,590),'back':(0,590,460,H),'right':(470,590,W,H)}[name];im=sheet.crop(rect)
 if flip:im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 a=np.asarray(im);mask=(a.min(2)<232)&((a.max(2)-a.min(2)>12)|(a.mean(2)<160))
 lab,n=label(mask);counts=np.bincount(lab.ravel());counts[0]=0;mask=binary_fill_holes(binary_closing(lab==counts.argmax(),iterations=2))
 rows,cols=np.where(mask);top,bottom=int(rows.min()),int(rows.max()+1);left,right=int(cols.min()),int(cols.max()+1)
 scale=1.22/(bottom-top)
 # Profile trunk center is inferred from the shoulders and pelvis, excluding tail.
 anchor=(left+right)/2 if name in ('front','back') else left+(right-left)*anchor_fraction
 # Longitudinal zero is about 15 cm behind the profile bounding-box midpoint.
 if name in ('left','right'):anchor+=.07/scale
 def sample(ax,zs):
  u=anchor+ax/scale;v=bottom-zs[::-1]/scale;vv,uu=np.meshgrid(v,u,indexing='ij')
  rgb=np.stack([map_coordinates(a[:,:,k].astype(float),[vv,uu],order=1,mode='constant',cval=255) for k in range(3)],2).astype('uint8')
  alpha=map_coordinates(mask.astype(float),[vv,uu],order=1,mode='constant',cval=0)
  return np.dstack([rgb,(alpha*255).astype('uint8')]),alpha>.5
 rgba,m=sample(axis,z);arrays[name+'_rgba']=rgba;arrays[name+'_mask']=m
 # Higher resolution camera-projected material photographs, with edge color dilation.
 axtex=np.linspace(axis[0],axis[-1],512 if name in ('front','back') else 1024);ztex=np.linspace(z[0],z[-1],768)
 tex,tm=sample(axtex,ztex);indices=distance_transform_edt(~tm,return_distances=False,return_indices=True);tex[:,:,:3]=tex[indices[0],indices[1],:3]
 Image.fromarray(tex).save(ROOT/('source_'+name+'.png'));Image.fromarray(rgba).save(ROOT/('aligned_'+name+'.png'))
 cal[name]={'cell':cell,'flip':flip,'meters_per_pixel':scale,'anchor_pixel':anchor,'ground_pixel':bottom,'height_m':1.22,'camera':'estimated orthographic; generated profile has mild perspective'}
buf=io.BytesIO();np.savez_compressed(buf,**arrays);p=ROOT/'rest_inputs.b85';p.write_text(base64.b85encode(buf.getvalue()).decode())
(ROOT/'calibration.json').write_text(json.dumps(cal,indent=2))
# Visual inspection performed on the actual generated sheet, not inferred from flags.
manifest={'schema_version':2,'reference_role':'rest_pose','body_plan':'quadruped','rest_pose':'quadruped_stand','views':['front','left','back','right'],'same_identity':True,'same_pose':True,'registered_scale':True,'limbs_separated':True,'source_input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'requested_pose_reference':'01_requested_pose.jpg','visual_review':{'status':'approved','reviewer':'Codex visual inspection of generated concept and four-view sheet','notes':['All four panels show standing quadruped, golden short coat, cream muzzle and chest, floppy ears.','Profile far-side feet are staggered by mild perspective; use symmetric anatomical estimates for hidden depth.','Front view occludes hind legs; side and rear identify their separate chains.','Tail and back are partially hidden in the front view; do not treat absent silhouette as absent anatomy.']}}
(ROOT/'reference_manifest.json').write_text(json.dumps(manifest,indent=2))
request=parse_command('Mudelitehas 10000 3 sitsiv koer animatsiooniga');(ROOT/'request.json').write_text(json.dumps(request,indent=2,ensure_ascii=False))
print(json.dumps(cal,indent=2));print('source bytes',len(buf.getvalue()))
