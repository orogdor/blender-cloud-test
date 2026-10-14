"""Align four AI orthographic views; record estimated camera calibration."""
from pathlib import Path
from PIL import Image
from scipy.ndimage import label,binary_closing
import numpy as np,base64,io,json
ROOT=Path(__file__).parent
sheet=Image.open(ROOT/'02_dog_four_views.png').convert('RGBA')
W,H=sheet.size
x=np.linspace(-.80,.80,176);y=np.linspace(-.90,.90,196);z=np.linspace(-.045,1.845,240)
arrays={'x':x,'y':y,'z':z};report={}
for name,cell,axis,flip in [('front',(0,0),x,False),('left',(1,0),y,False),('back',(0,1),x,False),('right',(1,1),y,True)]:
 cx,cy=cell;im=sheet.crop((cx*W//2,cy*H//2,(cx+1)*W//2,(cy+1)*H//2))
 if flip:im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 a=np.asarray(im);mask=a[:,:,3]>128;lab,n=label(mask);ct=np.bincount(lab.ravel());ct[0]=0;mask=lab==ct.argmax()
 yy,xx=np.where(mask);top,bottom=yy.min(),yy.max()+1;scale=1.8/(bottom-top)
 # Anchor the torso center instead of the total bounding box: the tail is asymmetric.
 row0=round(bottom-(bottom-top)*.34);row1=round(bottom-(bottom-top)*.28)
 centers=[]
 for row in range(row0,row1):
  ids=np.flatnonzero(mask[row]);
  if len(ids):centers.append((ids[0]+ids[-1])/2)
 anchor=float(np.median(centers))
 u=anchor+axis/scale;v=bottom-(z[::-1]/scale)
 uu,vv=np.meshgrid(u,v)
 # Vectorized bilinear resampling retains source alpha and avoids background color leakage.
 i=np.floor(uu).astype(int);j=np.floor(vv).astype(int);tx=uu-i;ty=vv-j
 valid=(i>=0)&(j>=0)&(i+1<im.width)&(j+1<im.height)
 i=np.clip(i,0,im.width-2);j=np.clip(j,0,im.height-2)
 out=(a[j,i]*(1-tx[...,None])*(1-ty[...,None])+a[j,i+1]*tx[...,None]*(1-ty[...,None])+a[j+1,i]*(1-tx[...,None])*ty[...,None]+a[j+1,i+1]*tx[...,None]*ty[...,None])
 out=np.clip(out,0,255).astype('uint8');out[~valid]=0
 m=binary_closing(out[:,:,3]>128,iterations=1)
 arrays[name+'_rgba']=out;arrays[name+'_mask']=m
 Image.fromarray(out).save(ROOT/(name+'_aligned.png'));im.save(ROOT/(name+'.png'))
 report[name]={'source_cell':cell,'horizontal_flip':flip,'meters_per_pixel':scale,'torso_center_pixel':anchor,'top_pixel':int(top),'ground_pixel':int(bottom),'camera':'estimated orthographic','back_tail_orientation_correction':name=='back'}
 buff=io.BytesIO()
np.savez_compressed(buff,**arrays)
(ROOT/'dog_inputs.b85').write_text(base64.b85encode(buff.getvalue()).decode())
(ROOT/'calibration.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2));print('PACKED_INPUT_BYTES',len(buff.getvalue()))
