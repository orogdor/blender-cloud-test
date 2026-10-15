#!/usr/bin/env python3
"""Verify complete per-point witnesses in >=3 independent viewing directions."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np

def validate_cloud(cloud_path,calibration_path):
    cloud_path=Path(cloud_path);calibration_path=Path(calibration_path)
    with np.load(cloud_path,allow_pickle=False) as data:
        required=['points','reference_pixels','signed_silhouette_distance_px','view_support','axis_support']
        if any(k not in data for k in required):raise ValueError('Missing per-point witness arrays')
        d={k:data[k] for k in required}
    c=json.loads(calibration_path.read_text());p=d['points'];uv=d['reference_pixels'];res=d['signed_silhouette_distance_px'];j=np.asarray(c['projection_jacobians'],float);b=np.asarray(c['projection_offsets'],float)
    n=len(p);v=len(c['view_order'])
    if not n or v<3 or p.shape!=(n,3) or uv.shape!=(n,v,2) or res.shape!=(n,v) or d['view_support'].shape!=(n,v) or d['axis_support'].shape!=(n,3):raise ValueError('Invalid or incomplete per-point witness shape')
    if j.shape!=(v,2,3) or b.shape!=(v,2) or not all(np.isfinite(x).all() for x in [p,uv,res,j,b]):raise ValueError('Missing/invalid camera or point evidence')
    directions=np.cross(j[:,0],j[:,1]);length=np.linalg.norm(directions,axis=1)
    if (length<1e-10).any():raise ValueError('Degenerate view projection')
    directions/=length[:,None]
    if np.linalg.matrix_rank(directions,tol=.15)<3:raise ValueError('Three independent directions required; opposite/mirrored sides do not add an axis')
    predicted=np.einsum('nd,vkd->nvk',p,j)+b[None,:,:]
    if np.max(np.abs(predicted-uv))>.02:raise ValueError('Saved image witnesses do not match the saved cloud and cameras')
    tolerance=float(c.get('support_tolerance_px',3))
    if not np.array_equal(d['view_support'].astype(bool),res>=-tolerance):raise ValueError('Support flags disagree with residuals')
    basis=[]
    for direction in directions:
        if np.linalg.matrix_rank(np.asarray(basis+[direction]),tol=.15)>len(basis):basis.append(direction)
        if len(basis)==3:break
    groups=np.abs(directions@np.asarray(basis).T).argmax(1)
    computed=np.column_stack([d['view_support'][:,groups==k].astype(bool).any(1) for k in range(3)])
    if not np.array_equal(computed,d['axis_support'].astype(bool)):raise ValueError('Axis support flags disagree with independent view groups')
    # Every point has finite witnesses in all declared views, including failed ones.
    supported=d['axis_support'].astype(bool).all(1);bad=int((~supported).sum())
    return {'workflow_version':'0.1.2','method_compliance':True,'status':'checked_with_conflicts' if bad else 'checked','point_count':n,'attempted_views_per_point':v,'independent_direction_rank':3,'points_with_three_axis_support':int(supported.sum()),'unresolved_points':bad,'three_axis_support_percent':round(float(supported.mean()*100),2),'geometry_support_complete':bad==0,'tolerance_px':tolerance,'feature_triangulation_proven':False,'cloud_sha256':hashlib.sha256(cloud_path.read_bytes()).hexdigest(),'calibration_sha256':hashlib.sha256(calibration_path.read_bytes()).hexdigest(),'scope':'Checks witness consistency and direction coverage, not truth of unseen depth or correctness of traced masks'}

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--cloud',type=Path,required=True);a.add_argument('--calibration',type=Path,required=True);a.add_argument('--output',type=Path,required=True);p=a.parse_args();r=validate_cloud(p.cloud,p.calibration);p.output.parent.mkdir(parents=True,exist_ok=True);p.output.write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':main()
