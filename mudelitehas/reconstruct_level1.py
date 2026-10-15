"""Fast level 1: four image masks -> oriented cloud -> Poisson surface."""
from pathlib import Path
import argparse,base64,io,json
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt,gaussian_filter,binary_erosion,label
try:
    from .pose_plan import validate_reference_manifest
    from .organic_surface import round_organic_sections
except ImportError:
    from pose_plan import validate_reference_manifest
    from organic_surface import round_organic_sections

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--request',type=Path,required=True)
    ap.add_argument('--output',type=Path,default=Path('output/mudelitehas_level1'))
    ap.add_argument('--cloud-only',action='store_true')
    ap.add_argument('--reference-manifest',default=None,help='Visuaalselt üle vaadatud ehituspoosi manifest JSON')
    args=ap.parse_args();request=json.loads(args.request.read_text())
    if request['level']!=1:ap.error('See rekonstruktsioon on taseme 1 jaoks.')
    manifest=json.loads(Path(args.reference_manifest).read_text()) if args.reference_manifest else {}
    review=validate_reference_manifest(request,manifest,args.input)
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    with np.load(io.BytesIO(base64.b85decode(args.input.read_text()))) as data:
        axes=[np.linspace(data[k][0],data[k][-1],min(len(data[k]),limit)) for k,limit in zip(('x','y','z'),request['profile']['grid_limit'])]
        x,y,z=axes;dx,dy,dz=x[1]-x[0],y[1]-y[0],z[1]-z[0]
        fields={};masks={}
        for name,width,spacing in [('front',len(x),(dz,dx)),('back',len(x),(dz,dx)),('left',len(y),(dz,dy)),('right',len(y),(dz,dy))]:
            mask=np.asarray(Image.fromarray(data[name+'_mask']).resize((width,len(z)),Image.Resampling.NEAREST),dtype=bool)
            masks[name]=mask
            sdf=distance_transform_edt(mask,sampling=spacing)-distance_transform_edt(~mask,sampling=spacing)
            a=sdf.T[...,::-1]
            fields[name]=a[:,None,:] if name in ('front','back') else a[None,:,:]
    tau=.014
    smoothmin=lambda a,b:-tau*np.logaddexp(-a/tau,-b/tau)
    phi=gaussian_filter(smoothmin(smoothmin(fields['front'],fields['back']),smoothmin(fields['left'],fields['right']))+.006,.6)
    organic=request.get('pose_plan',{}).get('subject_kind')=='living'
    if organic:
        phi=round_organic_sections(phi,x,y,z,**{name+'_mask':masks[name] for name in ('front','back','left','right')})
        phi=gaussian_filter(phi,.45)
    lab,count=label(phi>0);counts=np.bincount(lab.ravel());counts[0]=0
    if not counts[1:].any():raise ValueError('Neli vaadet ei anna ühise ruumalaga kujundit; kontrolli joondust.')
    inside=lab==counts.argmax();idx=np.argwhere(inside&~binary_erosion(inside))
    points=np.column_stack([x[idx[:,0]],y[idx[:,1]],z[idx[:,2]]])
    gradient=np.gradient(phi,dx,dy,dz);normals=-np.column_stack([g[tuple(idx.T)] for g in gradient]);normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
    np.savez_compressed(out/'04_point_cloud.npz',points=points,normals=normals)
    with (out/'04_point_cloud.ply').open('w') as f:
        f.write('ply\nformat ascii 1.0\nelement vertex '+str(len(points))+'\nproperty float x\nproperty float y\nproperty float z\nproperty float nx\nproperty float ny\nproperty float nz\nend_header\n')
        for p,n in zip(points,normals):f.write(' '.join(map(str,np.r_[p,n]))+'\n')
    report={'level':1,'pipeline':request['pipeline'],'cloud_points':len(points),'cloud_created_before_mesh':True,'input_views':str(args.input),'reference_review':review,'organic_rounding_applied':organic,'depth':'estimated from four registered silhouette masks; organic cross sections rounded when applicable','limitations':['silhouettes do not determine unseen surface detail','rounded cross sections are a prior, not measured depth; detailed joints need local anatomy profiles']}
    (out/'pipeline.json').write_text(json.dumps(report,indent=2));print('POINT_CLOUD_SAVED_BEFORE_MESH',len(points),flush=True)
    if args.cloud_only:return
    import open3d as o3d
    cloud=o3d.geometry.PointCloud();cloud.points=o3d.utility.Vector3dVector(points);cloud.normals=o3d.utility.Vector3dVector(normals)
    mesh,d=o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(cloud,depth=request['profile']['poisson_depth'],n_threads=2)
    mesh.remove_degenerate_triangles();mesh.remove_duplicated_triangles();mesh.remove_duplicated_vertices();mesh.remove_non_manifold_edges()
    comp,counts,areas=mesh.cluster_connected_triangles();mesh.remove_triangles_by_mask(np.asarray(comp)!=int(np.argmax(counts)));mesh.remove_unreferenced_vertices()
    o3d.io.write_triangle_mesh(str(out/'05_poisson_mesh.ply'),mesh)
    (out/'05_surface.json').write_text(json.dumps({'points':np.asarray(mesh.vertices).tolist(),'triangles':np.asarray(mesh.triangles).tolist()},separators=(',',':')))

if __name__=='__main__':main()
