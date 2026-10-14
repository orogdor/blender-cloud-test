"""Stage 4: four image silhouettes -> surface points -> Poisson mesh.
No pre-existing mesh is sampled. Uses estimated orthographic calibration.
"""
from pathlib import Path
import numpy as np,base64,io,json
from scipy.ndimage import distance_transform_edt,gaussian_filter,binary_erosion,label
from PIL import Image
ROOT=Path(__file__).parent
OUT=Path('output/teddy_mudelitehas');OUT.mkdir(parents=True,exist_ok=True)
data=np.load(io.BytesIO(base64.b85decode((ROOT/'teddy_inputs.b85').read_text())))
x,y,z=[data[k] for k in ('x','y','z')]
def sdf(mask,spacing):
 return distance_transform_edt(mask,sampling=spacing)-distance_transform_edt(~mask,sampling=spacing)
front=sdf(data['front_mask'],(z[1]-z[0],x[1]-x[0])).T[:,None,:]
back=sdf(data['back_mask'],(z[1]-z[0],x[1]-x[0])).T[:,None,:]
left=sdf(data['left_mask'],(z[1]-z[0],y[1]-y[0])).T[None,:,:]
right=sdf(data['right_mask'],(z[1]-z[0],y[1]-y[0])).T[None,:,:]
# Image rows run top to bottom; density uses ascending world z.
front,back,left,right=[a[...,::-1] for a in (front,back,left,right)]
tau=.021
phi=-tau*np.logaddexp(np.logaddexp(-front/tau,-back/tau),np.logaddexp(-left/tau,-right/tau))
# Four silhouettes cannot determine local appendage thickness: use explicit
# depth priors at the CLOUD stage, before creating any mesh. These are labelled
# estimates rather than claiming measured depths from a four-view image sheet.
xx=x[:,None,None];yy=y[None,:,None];zz=z[None,None,:]
arm_region=(np.abs(xx)>.32)&(zz>.48)&(zz<1.115)
arm_depth=.145-np.abs(yy+.005)
rounded_arm=-tau*np.logaddexp(-phi/tau,-arm_depth/tau)
phi=np.where(arm_region,rounded_arm,phi)
# Round head cross sections using per-row widths/depths from the source masks.
fm=(data['front_mask']&data['back_mask'])[::-1]
sm=(data['left_mask']&data['right_mask'])[::-1]
for k,zk in enumerate(z):
 if zk<1.115:continue
 xs=np.flatnonzero(fm[k]);ys=np.flatnonzero(sm[k])
 if len(xs)<3 or len(ys)<3:continue
 rx=max(abs(x[xs[0]]),abs(x[xs[-1]]));cy=(y[ys[0]]+y[ys[-1]])/2;ry=(y[ys[-1]]-y[ys[0]])/2
 if rx<.015 or ry<.015:continue
 ellipse=(1-np.sqrt((x[:,None]/rx)**2+((y[None,:]-cy)/ry)**2))*min(rx,ry)
 phi[:,:,k]=np.minimum(phi[:,:,k],ellipse)
phi=gaussian_filter(phi,.9)
inside=phi>0
labels,n=label(inside);count=np.bincount(labels.ravel());count[0]=0;inside=labels==count.argmax()
boundary=inside&~binary_erosion(inside)
indices=np.argwhere(boundary)
points=np.column_stack([x[indices[:,0]],y[indices[:,1]],z[indices[:,2]]])
gx,gy,gz=np.gradient(phi,x[1]-x[0],y[1]-y[0],z[1]-z[0])
normals=-np.column_stack([g[tuple(indices.T)] for g in (gx,gy,gz)])
normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
np.savez_compressed(OUT/'04_point_cloud.npz',points=points,normals=normals)
np.savez_compressed(OUT/'aligned_images.npz',**{k:data[k] for k in data.files})
with (OUT/'04_point_cloud.ply').open('w') as f:
 f.write('ply\nformat ascii 1.0\nelement vertex '+str(len(points))+'\nproperty float x\nproperty float y\nproperty float z\nproperty float nx\nproperty float ny\nproperty float nz\nend_header\n')
 for p,n in zip(points,normals):f.write(' '.join(str(v) for v in np.r_[p,n])+'\n')
print('POINT_CLOUD_SAVED_BEFORE_MESH',len(points),flush=True)
report={'pipeline':['2D concept','4 AI orthographic views','alpha silhouette alignment','visual-hull surface points','Poisson surface reconstruction','quad retopology','rig','running animation'],
 'cloud_points':len(points),'grid_shape':list(phi.shape),'point_cloud_source':'Boundary of softened four-view silhouette intersection; NOT sampled from mesh',
 'calibration':'estimated orthographic scale, aligned by image height and bounding-box center; arm thickness and rounded head depth inferred at point-cloud stage',
 'limitation':'AI views can disagree; silhouettes do not recover hidden cavities or exact plush details'}
(OUT/'pipeline.json').write_text(json.dumps(report,indent=2))
for name in ('front','back','left','right'):
 Image.fromarray(data[name+'_rgba']).save(OUT/('03_'+name+'_aligned.png'))
if '--cloud-only' not in __import__('sys').argv:
 import open3d as o3d
 cloud=o3d.geometry.PointCloud();cloud.points=o3d.utility.Vector3dVector(points);cloud.normals=o3d.utility.Vector3dVector(normals)
 mesh,densities=o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(cloud,depth=8,n_threads=2)
 mesh.remove_degenerate_triangles();mesh.remove_duplicated_triangles();mesh.remove_duplicated_vertices();mesh.remove_non_manifold_edges()
 components,counts,areas=mesh.cluster_connected_triangles()
 mesh.remove_triangles_by_mask(np.asarray(components)!=int(np.argmax(counts)));mesh.remove_unreferenced_vertices()
 mesh.compute_vertex_normals();o3d.io.write_triangle_mesh(str(OUT/'05_poisson_mesh.ply'),mesh)
 (OUT/'05_surface.json').write_text(json.dumps({'points':np.asarray(mesh.vertices).tolist(),'triangles':np.asarray(mesh.triangles).tolist()},separators=(',',':')))
 print('POISSON_MESH_SAVED',len(mesh.vertices),len(mesh.triangles),flush=True)
