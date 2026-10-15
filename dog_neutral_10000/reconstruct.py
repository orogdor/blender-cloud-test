"""Registered standing references -> inferred rounded volume -> oriented cloud -> Poisson.
No mesh is created or sampled before the point cloud is written.
"""
from pathlib import Path
import base64,io,json,sys
import numpy as np
from scipy.ndimage import distance_transform_edt,gaussian_filter,binary_erosion,label
from PIL import Image,ImageDraw
ROOT=Path(__file__).parent;sys.path.insert(0,str(ROOT.parent))
from mudelitehas.pose_plan import validate_reference_manifest
OUT=Path('output/dog_neutral_10000');OUT.mkdir(parents=True,exist_ok=True)
request=json.loads((ROOT/'request.json').read_text());review=validate_reference_manifest(request,json.loads((ROOT/'reference_manifest.json').read_text()),ROOT/'rest_inputs.b85')
D=np.load(io.BytesIO(base64.b85decode((ROOT/'rest_inputs.b85').read_text())))
x,y,z=[D[k].astype('float32') for k in ('x','y','z')];dx,dy,dz=float(x[1]-x[0]),float(y[1]-y[0]),float(z[1]-z[0])
xx=x[:,None,None];yy=y[None,:,None];zz=z[None,None,:]
def sdf(m,spacing):return (distance_transform_edt(m,sampling=spacing)-distance_transform_edt(~m,sampling=spacing)).astype('float32')
front=sdf(D['front_mask']|D['back_mask'],(dz,dx)).T[:,None,::-1]
left=sdf(D['left_mask'],(dz,dy)).T[None,:,::-1];right=sdf(D['right_mask'],(dz,dy)).T[None,:,::-1]
side=(left+right)*.5
def smax(a,b,k=.014):return k*np.logaddexp(a/k,b/k)
def smin(a,b,k=.007):return -k*np.logaddexp(-a/k,-b/k)
def ell(c,r):
 return (1-np.sqrt(((xx-c[0])/r[0])**2+((yy-c[1])/r[1])**2+((zz-c[2])/r[2])**2))*min(r)
def cap(a,b,r):
 a=np.array(a,dtype='float32')/r;b=np.array(b,dtype='float32')/r;ab=b-a
 qx=xx/r[0]-a[0];qy=yy/r[1]-a[1];qz=zz/r[2]-a[2]
 t=np.clip((qx*ab[0]+qy*ab[1]+qz*ab[2])/(ab@ab),0,1)
 return (1-np.sqrt((qx-t*ab[0])**2+(qy-t*ab[1])**2+(qz-t*ab[2])**2))*min(r)
# Metric centers are reviewed estimates from registered shoulders, rump, head,
# knees, wrists and hocks. Radii are rounded depth estimates constrained by masks.
phi=ell((0,.045,.676),(.194,.505,.229))
phi=smax(phi,cap((0,-.16,.68),(0,.31,.68),(.184,.21,.223)),.020)
phi=smax(phi,ell((0,-.28,.691),(.185,.270,.263)),.027)
phi=smax(phi,cap((0,-.32,.72),(0,-.49,1.04),(.147,.157,.157)),.024)
phi=smax(phi,ell((0,-.535,1.075),(.161,.184,.157)),.018)
phi=smax(phi,ell((0,-.735,1.015),(.114,.185,.092)),.019)
phi=smax(phi,ell((0,-.678,.967),(.111,.167,.067)),.013)
for s in (-1,1):
 phi=smax(phi,ell((s*.176,-.485,1.064),(.062,.092,.148)),.010)
 # Foreleg chains are independent from chest below elbow level.
 phi=smax(phi,cap((s*.145,-.298,.68),(s*.155,-.335,.39),(.074,.085,.082)),.020)
 phi=smax(phi,cap((s*.155,-.335,.39),(s*.161,-.405,.092),(.046,.052,.055)),.012)
 phi=smax(phi,ell((s*.163,-.449,.048),(.058,.092,.047)),.010)
 # Haunch -> forward knee -> rear hock -> planted foot.
 phi=smax(phi,ell((s*.143,.402,.626),(.116,.172,.211)),.022)
 phi=smax(phi,cap((s*.153,.393,.57),(s*.165,.285,.398),(.079,.083,.083)),.017)
 phi=smax(phi,cap((s*.165,.285,.398),(s*.169,.482,.176),(.049,.057,.058)),.012)
 phi=smax(phi,cap((s*.169,.482,.176),(s*.169,.464,.065),(.037,.040,.044)),.009)
 phi=smax(phi,ell((s*.170,.419,.041),(.055,.083,.040)),.009)
tail=[((0,.526,.758),(0,.616,.64),(.072,.077,.077)),((0,.616,.64),(0,.704,.50),(.064,.069,.068)),((0,.704,.50),(0,.780,.365),(.059,.065,.066))]
for a,b,r in tail:phi=smax(phi,cap(a,b,r),.011)
# Softly respect source contours without making flat rectangular intersections.
phi=smin(phi,front+.026);phi=smin(phi,side+.018)
phi=gaussian_filter(phi,.70)
inside=phi>0;lab,n=label(inside);ct=np.bincount(lab.ravel());ct[0]=0;inside=lab==ct.argmax()
idx=np.argwhere(inside&~binary_erosion(inside));grad=np.gradient(phi,dx,dy,dz)
normals=-np.column_stack([g[tuple(idx.T)] for g in grad]);normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-10)
points=np.column_stack([x[idx[:,0]],y[idx[:,1]],z[idx[:,2]]]);points+=normals*np.clip(phi[tuple(idx.T)],0,min(dx,dy,dz))[:,None]
confidence=np.full(len(points),.65,dtype='float32')
np.savez_compressed(OUT/'04_point_cloud.npz',points=points,normals=normals,confidence=confidence)
np.savez_compressed(OUT/'aligned_images.npz',**{k:D[k] for k in D.files})
with (OUT/'04_point_cloud.ply').open('w') as f:
 f.write('ply\nformat ascii 1.0\nelement vertex '+str(len(points))+'\nproperty float x\nproperty float y\nproperty float z\nproperty float nx\nproperty float ny\nproperty float nz\nend_header\n')
 np.savetxt(f,np.column_stack([points,normals]),fmt='%.7f')
print('POINT_CLOUD_SAVED_BEFORE_ANY_MESH',len(points),flush=True)
pred={'front':inside.any(1).T[::-1],'back':inside.any(1).T[::-1],'left':inside.any(0).T[::-1],'right':inside.any(0).T[::-1]}
scores={name:float((mask&D[name+'_mask']).sum()/max(1,(mask|D[name+'_mask']).sum())) for name,mask in pred.items()}
panel=Image.new('RGB',(1600,600),(25,31,40));draw=ImageDraw.Draw(panel)
for i,(name,m) in enumerate(pred.items()):
 target=D[name+'_mask'];rgb=np.zeros((*m.shape,3),dtype='uint8');rgb[target]=[60,135,240];rgb[m]=[230,145,50];rgb[m&target]=[120,200,155]
 im=Image.fromarray(rgb);im.thumbnail((380,520));panel.paste(im,(i*400+(400-im.width)//2,45));draw.text((i*400+10,15),name+' IoU '+str(round(scores[name],3)),fill='white')
panel.save(OUT/'04_cloud_silhouette_comparison.png')
report={'pipeline':['requested-pose 2D concept','same dog standing four-view references','registered masks + reviewed round anatomical depth','oriented point cloud SAVED BEFORE MESH','Poisson reconstruction','exact 10000 primary quads','UV PBR','standing-rest canine skeleton','armature animation into SitPretty','deformation and silhouette checks'],
'cloud_created_before_mesh':True,'cloud_points':len(points),'source_silhouette_iou':scores,'reference_review':review,'reconstruction_pose':'quadruped_stand','target_pose':'sit_pretty','depth_is_estimated':True,'inferred_parts':['hidden side width','joint centers','cross-section roundness','tail and far limb depth'],'limitations':['Generated views contain mild perspective and inconsistent far-side paw offsets.','Metric scale and hidden anatomy are estimates, not a scan.','Rounded anatomical fields are regularized by image masks, not an existing mesh.']}
(OUT/'pipeline.json').write_text(json.dumps(report,indent=2));print('CLOUD_SILHOUETTES',scores,flush=True)
if '--cloud-only' not in sys.argv:
 import open3d as o3d
 cloud=o3d.geometry.PointCloud();cloud.points=o3d.utility.Vector3dVector(points);cloud.normals=o3d.utility.Vector3dVector(normals)
 mesh,density=o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(cloud,depth=8,n_threads=2)
 mesh.remove_degenerate_triangles();mesh.remove_duplicated_triangles();mesh.remove_duplicated_vertices()
 comp,counts,areas=mesh.cluster_connected_triangles();mesh.remove_triangles_by_mask(np.asarray(comp)!=int(np.argmax(counts)));mesh.remove_unreferenced_vertices();mesh.compute_vertex_normals()
 o3d.io.write_triangle_mesh(str(OUT/'05_poisson.ply'),mesh)
 (OUT/'05_surface.json').write_text(json.dumps({'points':np.asarray(mesh.vertices).tolist(),'triangles':np.asarray(mesh.triangles).tolist()},separators=(',',':')))
 print('POISSON_CREATED_FROM_SAVED_CLOUD',len(mesh.vertices),len(mesh.triangles),flush=True)
