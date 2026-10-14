"""Four source silhouettes -> confidence-weighted oriented cloud -> Poisson mesh.
The saved cloud is created before any mesh; anatomical depth priors are explicit.
"""
from pathlib import Path
import numpy as np,base64,io,json,sys
from scipy.ndimage import distance_transform_edt,gaussian_filter,binary_erosion,label
from PIL import Image,ImageDraw
ROOT=Path(__file__).parent
OUT=Path('output/dog_mudelitehas');OUT.mkdir(parents=True,exist_ok=True)
D=np.load(io.BytesIO(base64.b85decode((ROOT/'dog_inputs.b85').read_text())))
x,y,z=[D[k] for k in ('x','y','z')];dx,dy,dz=x[1]-x[0],y[1]-y[0],z[1]-z[0]
def sdf(mask,spacing):return distance_transform_edt(mask,sampling=spacing)-distance_transform_edt(~mask,sampling=spacing)
F=sdf(D['front_mask'],(dz,dx)).T[:,None,::-1]
B=sdf(D['back_mask'],(dz,dx)).T[:,None,::-1]
L=sdf(D['left_mask'],(dz,dy)).T[None,:,::-1]
R=sdf(D['right_mask'],(dz,dy)).T[None,:,::-1]
tau=.010
def smoothmin(a,b,t=tau):return -t*np.logaddexp(-a/t,-b/t)
def smoothmax(a,b,t=tau):return t*np.logaddexp(a/t,b/t)
raw=smoothmin(smoothmin(F,B),smoothmin(L,R))+.010
xx=x[:,None,None];yy=y[None,:,None];zz=z[None,None,:]
def ellipsoid(cx,cy,cz,rx,ry,rz):
 return (1-np.sqrt(((xx-cx)/rx)**2+((yy-cy)/ry)**2+((zz-cz)/rz)**2))*min(rx,ry,rz)
# These priors regularize ambiguous DEPTH only; no existing 3D model is sampled.
# The source masks retain responsibility for the visible contours.
head=ellipsoid(0,-.09,1.595,.207,.255,.235)
muzzle=ellipsoid(0,-.36,1.470,.151,.254,.132)
head=smoothmax(head,muzzle,.035)
for s in (-1,1):
 head=smoothmax(head,ellipsoid(s*.235,-.008,1.555,.112,.116,.173),.018)
head_phi=smoothmin(raw,head,.008)
initial=np.where(zz>1.34,head_phi,raw)
# Cross-section rounding of trunk and haunches using the actual silhouette
# widths at each row. Raised forelegs use separate inferred depth bands.
fm=(D['front_mask']|D['back_mask'])[::-1]
sm=(D['left_mask']&D['right_mask'])[::-1]
for k,zk in enumerate(z):
 if not .12<zk<1.34:continue
 ids=np.flatnonzero(fm[k]& (np.abs(x)<(.32 if zk<.80 else .245)))
 js=np.flatnonzero(sm[k])
 if len(ids)<3 or len(js)<3:continue
 # In the forelimb band the front-most side interval belongs to lifted paws.
 if .72<zk<1.13:js=js[y[js]>-.25]
 if len(js)<3:continue
 rx=max(abs(x[ids[0]]),abs(x[ids[-1]]))+.025
 cy=(y[js[0]]+y[js[-1]])/2;ry=(y[js[-1]]-y[js[0]])/2+.018
 ellipse=(1-np.sqrt((x[:,None]/rx)**2+((y[None,:]-cy)/ry)**2))*min(rx,ry)
 trunk=ellipse
 if .67<zk<1.19:
  # Shared silhouette tells us vertical width; rounded limb thickness is inferred.
  a=.13-np.abs(y+.38)
  for s in (-1,1):
   limb=np.minimum(.145-np.abs(x[:,None]-s*.265),a[None,:])
   trunk=smoothmax(trunk,limb,.022)
 initial[:,:,k]=smoothmin(initial[:,:,k],trunk,.009)

def largest(mask):
 lab,n=label(mask);counts=np.bincount(lab.ravel());counts[0]=0
 return lab==counts.argmax()
def projections(mask):return {'front':mask.any(1).T[::-1],'back':mask.any(1).T[::-1],'left':mask.any(0).T[::-1],'right':mask.any(0).T[::-1]}
def scores(mask):
 p=projections(mask);return {n:float((p[n]&D[n+'_mask']).sum()/max(1,(p[n]|D[n+'_mask']).sum())) for n in p}
# Small regularization search with quantitative silhouette comparison. Retain
# shape priors unless they substantially contradict the four source images.
candidates=[]
for mix in (1.,.8,.6):
 field=gaussian_filter(initial*mix+raw*(1-mix),.75)
 mask=largest(field>0);s=scores(mask);score=float(np.mean(list(s.values())))
 candidates.append((score-.065*(1-mix),mix,field,mask,s))
_,mix,phi,inside,ious=max(candidates,key=lambda c:c[0])
boundary=inside&~binary_erosion(inside);idx=np.argwhere(boundary)
gradient=np.gradient(phi,dx,dy,dz)
normals=-np.column_stack([g[tuple(idx.T)] for g in gradient]);normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
points=np.column_stack([x[idx[:,0]],y[idx[:,1]],z[idx[:,2]]])
# Subvoxel projection onto the zero crossing, capped to avoid unstable normals.
dist=phi[tuple(idx.T)];points+=normals*np.clip(dist,0,min(dx,dy,dz))[:,None]
agreement=np.minimum.reduce([np.broadcast_to(F,phi.shape)[tuple(idx.T)],np.broadcast_to(B,phi.shape)[tuple(idx.T)],np.broadcast_to(L,phi.shape)[tuple(idx.T)],np.broadcast_to(R,phi.shape)[tuple(idx.T)]])
confidence=np.clip(.65+agreement/.10,.25,1.)
np.savez_compressed(OUT/'04_point_cloud.npz',points=points,normals=normals,confidence=confidence)
np.savez_compressed(OUT/'aligned_images.npz',**{k:D[k] for k in D.files})
with (OUT/'04_point_cloud.ply').open('w') as f:
 f.write('ply\nformat ascii 1.0\nelement vertex '+str(len(points))+'\nproperty float x\nproperty float y\nproperty float z\nproperty float nx\nproperty float ny\nproperty float nz\nproperty float confidence\nend_header\n')
 for p,n,c in zip(points,normals,confidence):f.write(' '.join(map(str,np.r_[p,n,c]))+'\n')
print('POINT_CLOUD_SAVED_BEFORE_ANY_MESH',len(points),flush=True)
for name in ('front','left','back','right'):Image.fromarray(D[name+'_rgba']).save(OUT/('03_'+name+'_aligned.png'))
pred=projections(inside);panel=Image.new('RGB',(600*4,720),(25,31,40));draw=ImageDraw.Draw(panel)
for i,name in enumerate(('front','left','back','right')):
 target=D[name+'_mask'];a=np.zeros((*target.shape,3),dtype='uint8');a[target]=[65,150,235];a[pred[name]]=[235,135,45];a[target&pred[name]]=[160,207,165]
 im=Image.fromarray(a).resize((560,640));panel.paste(im,(i*600+20,45));draw.text((i*600+20,12),name+' silhouette IoU '+str(round(ious[name],3)),fill='white')
draw.text((20,697),'green=overlap  blue=source only  orange=cloud only; estimated orthographic calibration',fill='white');panel.save(OUT/'04_silhouette_comparison.png')
report={'pipeline':['2D concept','4 orthographic reference views','estimated camera alignment','oriented confidence-weighted point cloud','Poisson surface reconstruction','quad retopology','PBR UV material maps','canine rig','SitPretty animation','multi-view validation'],
 'cloud_points':len(points),'grid_shape':list(phi.shape),'cloud_created_before_mesh':True,'cloud_source':'Four image masks and explicit inferred anatomical depth; NOT points sampled from a model',
 'source_silhouette_iou':ious,'regularization_mix':mix,'regularization_candidates':[{'mix':c[1],'iou':c[4]} for c in candidates],'calibration':'Estimated orthographic scale from common body height and torso centers, not measured cameras',
 'inferred_parts':['skull and muzzle cross section','floppy ear depth','foreleg thickness','unseen surface'],
 'limitations':['AI views may disagree','Silhouettes do not measure true depth or hidden cavities','Shape priors are estimates; generated image depth would also be estimated'],
 'recommendations_applied':['four-view consistency alignment','normal and confidence on cloud points','anatomical depth regularization','quantitative silhouette feedback','UV and separate PBR maps','separate optical eye and nose details','canine-specific skeleton','skin deformation and ground-contact checks','editable high detail model and lower detail export']}
(OUT/'pipeline.json').write_text(json.dumps(report,indent=2))
if '--cloud-only' not in sys.argv:
 import open3d as o3d
 cloud=o3d.geometry.PointCloud();cloud.points=o3d.utility.Vector3dVector(points);cloud.normals=o3d.utility.Vector3dVector(normals)
 mesh,d=o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(cloud,depth=8,n_threads=2)
 mesh.remove_degenerate_triangles();mesh.remove_duplicated_triangles();mesh.remove_duplicated_vertices();mesh.remove_non_manifold_edges()
 comp,counts,areas=mesh.cluster_connected_triangles();mesh.remove_triangles_by_mask(np.asarray(comp)!=int(np.argmax(counts)));mesh.remove_unreferenced_vertices();mesh.compute_vertex_normals()
 o3d.io.write_triangle_mesh(str(OUT/'05_poisson_mesh.ply'),mesh)
 (OUT/'05_surface.json').write_text(json.dumps({'points':np.asarray(mesh.vertices).tolist(),'triangles':np.asarray(mesh.triangles).tolist()},separators=(',',':')))
 print('POISSON_MESH_CREATED_FROM_CLOUD',len(mesh.vertices),len(mesh.triangles),flush=True)
