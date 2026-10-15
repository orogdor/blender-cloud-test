"""Reviewed neutral four views -> rounded inferred volume -> cloud before Poisson."""
from pathlib import Path
import json,time,hashlib
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import binary_closing,binary_fill_holes,label,distance_transform_edt,gaussian_filter,binary_erosion,map_coordinates
BASE=Path(__file__).resolve().parent.parent;OUT=BASE/'output';REF=BASE/'references';OUT.mkdir(exist_ok=True);start=time.perf_counter()
sheet=Image.open(REF/'02_neutral_four_views.png').convert('RGB');W,H=sheet.size;print('SHEET',W,H,flush=True)
# Panel boundaries reviewed on actual image; side views have same standing T-pose.
rects={'front':(0,0,675,640),'left':(675,0,W,640),'back':(0,640,675,H),'right':(675,640,W,H)}
x=np.linspace(-.92,.92,185,dtype='float32');y=np.linspace(-.50,.44,121,dtype='float32');z=np.linspace(-.015,1.735,221,dtype='float32');HEIGHT=1.65
D={'x':x,'y':y,'z':z};registration={};tiles=[]
for name,rect in rects.items():
 rgb=np.array(sheet.crop(rect));mask=(rgb.max(2)-rgb.min(2)>20)&(rgb.min(2)<225);mask=binary_fill_holes(binary_closing(mask,iterations=2));lab,n=label(mask);counts=np.bincount(lab.ravel());counts[0]=0;mask=lab==counts.argmax();rows,cols=np.nonzero(mask);top,bottom=rows.min(),rows.max();scale=HEIGHT/(bottom-top)
 if name in ['front','back']:center=(cols.min()+cols.max())/2
 else:
  row=int(bottom-.43*(bottom-top));cc=np.flatnonzero(mask[row]);center=(cc.min()+cc.max())/2
 axis=x if name in ['front','back'] else y;uu,zz=np.meshgrid(axis,z[::-1]);pixelx=center+uu/scale if name!='right' else center-uu/scale;pixely=bottom-zz/scale;coords=np.array([pixely,pixelx]);m=map_coordinates(mask.astype(float),coords,order=0,mode='constant')>.5
 color=np.stack([map_coordinates(rgb[:,:,c],coords,order=1,mode='nearest') for c in range(3)],axis=2).astype('uint8');rgba=np.dstack([color,m.astype('uint8')*255]);D[name+'_mask']=m;D[name+'_rgba']=rgba;Image.fromarray(rgba).save(REF/('aligned_'+name+'.png'))
 registration[name]={'panel':rect,'pixel_top':int(top),'pixel_floor':int(bottom),'pixel_center':float(center),'meters_per_pixel_estimated':float(scale)}
 im=Image.fromarray(rgba).convert('RGB');im.thumbnail((360,600));tiles.append((name,im))
np.savez_compressed(OUT/'aligned_images.npz',**D)
panel=Image.new('RGB',(1440,650),'#343d48');draw=ImageDraw.Draw(panel)
for i,(name,im) in enumerate(tiles):panel.paste(im,(i*360+(360-im.width)//2,35));draw.text((i*360+10,10),name,fill='white')
panel.save(OUT/'Registration_check.png');(REF/'calibration.json').write_text(json.dumps(registration,indent=2))
xx=x[:,None,None];yy=y[None,:,None];zz=z[None,None,:];spacing=[float(a[1]-a[0]) for a in [x,y,z]]
def sdf(mask,sp):return (distance_transform_edt(mask,sampling=sp)-distance_transform_edt(~mask,sampling=sp)).astype('float32')
front=sdf(D['front_mask']|D['back_mask'],(spacing[2],spacing[0])).T[:,None,::-1];side=(sdf(D['left_mask'],(spacing[2],spacing[1]))+sdf(D['right_mask'],(spacing[2],spacing[1]))).T[None,:,::-1]*.5
def smax(a,b,k=.018):return k*np.logaddexp(a/k,b/k)
def smin(a,b,k=.008):return -k*np.logaddexp(-a/k,-b/k)
def ell(c,r):return (1-np.sqrt(((xx-c[0])/r[0])**2+((yy-c[1])/r[1])**2+((zz-c[2])/r[2])**2))*min(r)
def cap(a,b,r):
 a=np.array(a)/r;b=np.array(b)/r;ab=b-a;qx=xx/r[0]-a[0];qy=yy/r[1]-a[1];qz=zz/r[2]-a[2];t=np.clip((qx*ab[0]+qy*ab[1]+qz*ab[2])/(ab@ab),0,1);return (1-np.sqrt((qx-t*ab[0])**2+(qy-t*ab[1])**2+(qz-t*ab[2])**2))*min(r)
# Metric sizes are anatomical depth estimates constrained by the actual masks.
phi=ell((0,0,.735),(.315,.220,.365));phi=smax(phi,ell((0,0,.985),(.262,.185,.19)))
phi=smax(phi,ell((0,-.004,1.340),(.335,.255,.300)));phi=smax(phi,ell((0,-.246,1.210),(.178,.105,.118)),.016)
for sign in [-1,1]:
 phi=smax(phi,ell((sign*.278,.004,1.555),(.108,.065,.112)),.012)
 phi=smax(phi,cap((sign*.247,0,.979),(sign*.703,0,.979),(.112,.115,.112)),.024)
 phi=smax(phi,ell((sign*.727,-.005,.977),(.103,.119,.112)),.018)
 phi=smax(phi,cap((sign*.185,.012,.467),(sign*.185,.003,.133),(.116,.133,.135)),.022)
 phi=smax(phi,ell((sign*.185,-.055,.087),(.137,.184,.089)),.019)
phi=smax(phi,ell((0,.205,.567),(.075,.075,.076)),.012)
phi=smin(phi,front+.018);phi=smin(phi,side+.02);phi=gaussian_filter(phi,.65);inside=phi>0;lab,n=label(inside);ct=np.bincount(lab.ravel());ct[0]=0;inside=lab==ct.argmax()
idx=np.argwhere(inside&~binary_erosion(inside));grad=np.gradient(phi,*spacing);normals=-np.column_stack([g[tuple(idx.T)] for g in grad]);normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-10);points=np.column_stack([x[idx[:,0]],y[idx[:,1]],z[idx[:,2]]]);points+=normals*np.clip(phi[tuple(idx.T)],0,min(spacing))[:,None]
np.savez_compressed(OUT/'04_point_cloud.npz',points=points,normals=normals,confidence=np.full(len(points),.65))
with (OUT/'04_point_cloud.ply').open('w') as f:
 f.write('ply\nformat ascii 1.0\nelement vertex '+str(len(points))+'\nproperty float x\nproperty float y\nproperty float z\nproperty float nx\nproperty float ny\nproperty float nz\nend_header\n');np.savetxt(f,np.column_stack([points,normals]),fmt='%.7f')
print('POINT_CLOUD_SAVED_BEFORE_MESH',len(points),flush=True)
pred={'front':inside.any(1).T[::-1],'back':inside.any(1).T[::-1],'left':inside.any(0).T[::-1],'right':inside.any(0).T[::-1]};scores={name:float((m&D[name+'_mask']).sum()/max(1,(m|D[name+'_mask']).sum())) for name,m in pred.items()}
report={'command':'Mudelitehas 10000 3 jalutav mängukaru animatsiooniga','rest_pose':'biped T-pose','requested_pose':'upright walking','cloud_created_before_mesh':True,'cloud_points':len(points),'source_silhouette_iou':scores,'depth_estimated_not_measured':True,'reference_review':{'status':'visually_reviewed','same_identity':True,'arms_separated_in_front_and_back':True,'legs_separated':True,'side_limbs_occluded_as_expected':True,'sha256':hashlib.sha256((REF/'02_neutral_four_views.png').read_bytes()).hexdigest()},'inferred_parts':['cross-section depth','far limb thickness','joint centers','plush volume'],'limitations':['Generated views have minor proportion inconsistencies.','Shape is silhouette-constrained anatomical estimation, not a scan.']}
(OUT/'pipeline.json').write_text(json.dumps(report,indent=2));print('CLOUD_IOU',scores,flush=True)
import open3d as o3d
cloud=o3d.geometry.PointCloud();cloud.points=o3d.utility.Vector3dVector(points);cloud.normals=o3d.utility.Vector3dVector(normals);mesh,density=o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(cloud,depth=8,n_threads=2);mesh.remove_degenerate_triangles();mesh.remove_duplicated_triangles();mesh.remove_duplicated_vertices();comp,counts,areas=mesh.cluster_connected_triangles();mesh.remove_triangles_by_mask(np.asarray(comp)!=int(np.argmax(counts)));mesh.remove_unreferenced_vertices();mesh.compute_vertex_normals();o3d.io.write_triangle_mesh(str(OUT/'05_poisson.ply'),mesh);(OUT/'05_surface.json').write_text(json.dumps({'points':np.asarray(mesh.vertices).tolist(),'triangles':np.asarray(mesh.triangles).tolist()},separators=(',',':')));report['reconstruction_seconds']=time.perf_counter()-start;(OUT/'pipeline.json').write_text(json.dumps(report,indent=2));print('SURFACE_COMPLETE',len(mesh.vertices),len(mesh.triangles),report['reconstruction_seconds'],flush=True)
