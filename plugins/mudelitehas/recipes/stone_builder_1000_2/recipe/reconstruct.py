#!/usr/bin/env python3
"""Form a genuine, pre-mesh 3D visual hull cloud from THREE registered masks.
This is silhouette reconstruction and prior-based depth, not photogrammetric feature triangulation.
"""
import argparse,sys,hashlib,json
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_erosion,distance_transform_edt
from common import read_inputs,write_json,project,sha256


def inside_samples(uv,mask):
    h,w=mask.shape
    col=np.rint(uv[:,0]).astype(int);row=np.rint(uv[:,1]).astype(int)
    valid=(col>=0)&(col<w)&(row>=0)&(row<h)
    result=np.zeros(len(col),dtype=bool)
    result[valid]=mask[row[valid],col[valid]]
    return result


def signed_silhouette_distance(uv,mask):
    # Positive inside silhouette, negative outside; pixels from REAL mask.
    edt_inside=distance_transform_edt(mask)
    edt_outside=distance_transform_edt(~mask)
    h,w=mask.shape
    col=np.rint(uv[:,0]).astype(int);row=np.rint(uv[:,1]).astype(int)
    valid=(col>=0)&(col<w)&(row>=0)&(row<h)
    values=np.full(len(col),-100000.,dtype=float)
    values[valid]=edt_inside[row[valid],col[valid]]-edt_outside[row[valid],col[valid]]
    return values


def generate(manifest,workdir,resolution=.035,maxpoints=25000,allow_synthetic=False):
    data=read_inputs(manifest,allow_synthetic=allow_synthetic)
    root=Path(workdir);root.mkdir(parents=True,exist_ok=True)
    if not .018<=resolution<=.085:raise ValueError('Voxel resolution must be 0.018–0.085 m')
    # T-pose bounds, meters. Uses independent silhouette intersection, not a sampled mesh.
    x=np.arange(-1.16,1.1601,resolution,dtype=np.float32)
    y=np.arange(0,1.951,resolution,dtype=np.float32)
    z=np.arange(-.58,.581,resolution,dtype=np.float32)
    xx,yy,zz=np.meshgrid(x,y,z,indexing='ij')
    volume_xyz=np.column_stack((xx.ravel(),yy.ravel(),zz.ravel())).astype(np.float32)
    uv=project(volume_xyz,data['J'],data['offset'])
    inside=np.ones(len(volume_xyz),dtype=bool)
    for i,mask in enumerate(data['masks']):inside&=inside_samples(uv[:,i,:],mask)
    volume=inside.reshape((len(x),len(y),len(z)))
    if volume.sum()<600:raise ValueError('Visual hull empty or tiny: check camera registration')
    border=volume & ~binary_erosion(volume,iterations=1,border_value=0)
    points=volume_xyz[border.ravel()]
    if len(points)>maxpoints:
        # Stable sampling without inventing points. Uniformly distributed over voxel surface.
        ids=np.random.default_rng(1002).choice(len(points),size=maxpoints,replace=False)
        points=points[np.sort(ids)]
    if len(points)<300:raise ValueError('Insufficient cloud surface points')
    # EXACT three-view witness data BEFORE ANY MESH is built.
    witnesses=project(points,data['J'],data['offset'])
    distance=np.column_stack([signed_silhouette_distance(witnesses[:,i,:],m) for i,m in enumerate(data['masks'])]);tol=3.
    support=distance>=-tol
    # Independent basis is fixed front/right/top, extra back groups with front.
    groups=[['front','back'],['right'],['top']]
    axis=np.column_stack([support[:,[i for i,n in enumerate(data['views']) if n in g]].any(axis=1) for g in groups]);assert axis.shape==(len(points),3)
    cloud=root/'cloud_before_mesh.npz';np.savez_compressed(cloud,points=points.astype(np.float32),reference_pixels=witnesses.astype(np.float32),signed_silhouette_distance_px=distance.astype(np.float32),view_support=support.astype(np.uint8),axis_support=axis.astype(np.uint8))
    calibration={'view_order':data['views'],'projection_jacobians':data['J'].tolist(),'projection_offsets':data['offset'].tolist(),'support_tolerance_px':tol,'coordinate_system':'X right, Y up, Z backward; 1 unit=1 meter','source_hashes':data['hashes'],'interpretation':'SILHOUETTE occupancy only; per-feature triangulation NOT verified'}
    cal=root/'calibration.json';write_json(cal,calibration)
    # Actual pixel colors from the reviewed images for level-2 image-guided surface color.
    np.savez_compressed(root/'texture_sources.npz', **{name:np.asarray(im.convert('RGB'),dtype=np.uint8) for name,im in zip(data['views'],data['images'])})
    report={'recipe':'stone-builder-1000-2','workflow_version':'0.1.2','stage':'PRE_MESH_POINT_CLOUD',
            'reference_manifest_sha256':sha256(manifest),'cloud_sha256':sha256(cloud),
            'count':len(points),'interior_voxels':int(volume.sum()),'resolution_m':resolution,
            'attempted_view_witnesses_per_point':len(data['views']),
            'siluette_three_axis_support_percent':float(axis.all(axis=1).mean()*100),
            'unresolved_silhouette_points':int((~axis.all(axis=1)).sum()),
            'independent_feature_correspondence_verified':0,
            'depth_status':'estimated from visual hull and anatomy priors, not measured',
            'synthetic_test':data['synthetic_test']}
    write_json(root/'cloud_report.json',report)
    # Needed for reproducible trace from cloud back to signed silhouette source distances.
    np.savez_compressed(root/'occupied_volume.npz',origin=np.asarray([x[0],y[0],z[0]],np.float32),resolution=np.float32(resolution),occupied=volume.astype(np.uint8))
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--workdir',type=Path,required=True)
    p.add_argument('--resolution',type=float,default=.035)
    p.add_argument('--allow-synthetic-test',action='store_true');args=p.parse_args()
    result=generate(args.manifest,args.workdir,args.resolution,allow_synthetic=args.allow_synthetic_test)
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
