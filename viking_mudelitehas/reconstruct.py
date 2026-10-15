"""Mudelitehas 8000 level 2: generated 2D four-view Viking silhouettes -> oriented cloud -> Poisson.
No existing 3D geometry is sampled or reused. 2D silhouette depth is estimated.
"""
from pathlib import Path
import json, numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, binary_erosion, label
import open3d as o3d
OUT=Path("output/viking_mudelitehas");OUT.mkdir(parents=True,exist_ok=True)
W,H=264,384
# Coordinate system in metres: X left/right, Y front(-)/back(+), Z up.
X=np.linspace(-.79,.79,115);Y=np.linspace(-.57,.57,93);Z=np.linspace(.006,1.88,185)
def point(u,z,kind):
    lo,hi=(-.79,.79) if kind in ("front","back") else (-.57,.57)
    return (int((u-lo)/(hi-lo)*(W-1)),int((1-z/1.88)*(H-1)))
def make_view(kind):
    im=Image.new("RGBA",(W,H),(245,244,240,0));d=ImageDraw.Draw(im)
    def poly(points,c):
        d.polygon([point(u,z,kind) for u,z in points],fill=(*c,255))
    def oval(cx,cz,rx,rz,c):
        a=point(cx-rx,cz+rz,kind);b=point(cx+rx,cz-rz,kind)
        d.ellipse((a[0],a[1],b[0],b[1]),fill=(*c,255))
    leather=(83,59,43);iron=(81,88,92);fur=(102,83,65)
    cloth=(47,62,69);skin=(149,107,78);boots=(72,51,37)
    if kind in ("front","back"):
        # Legs and boots are intentionally two anatomically distinct lobes.
        for s in (-1,1):
            poly([(s*.075,.83),(s*.305,.81),(s*.28,.60),(s*.257,.39),
                  (s*.245,.23),(s*.25,.105),(s*.29,.035),(s*.23,.008),
                  (s*.072,.008),(s*.095,.20),(s*.09,.43)],cloth)
            poly([(s*.09,.32),(s*.263,.32),(s*.255,.08),(s*.305,.025),
                  (s*.28,.008),(s*.07,.008)],boots)
        poly([(-.35,.78),(-.345,1.06),(-.41,1.31),(-.32,1.54),
              (.32,1.54),(.41,1.31),(.345,1.06),(.35,.78),
              (.25,.69),(-.25,.69)],cloth)
        for s in (-1,1):
            poly([(s*.34,1.51),(s*.475,1.44),(s*.525,1.21),
                  (s*.54,1.06),(s*.56,.96),(s*.515,.91),
                  (s*.45,.95),(s*.41,1.14),(s*.29,1.37)],leather)
            oval(s*.532,.95,.062,.078,skin)
        # Broad fur shoulders taper into armor.
        poly([(-.49,1.46),(-.32,1.59),(-.20,1.56),(0,1.50),
              (.20,1.56),(.49,1.46),(.43,1.28),(.27,1.33),
              (0,1.34),(-.27,1.33),(-.43,1.28)],fur)
        oval(0,1.622,.162,.162,skin)
        # Beard projects below cheeks, separate color patch.
        if kind=="front":
            poly([(-.13,1.61),(-.14,1.47),(-.092,1.39),(0,1.33),
                  (.092,1.39),(.14,1.47),(.13,1.61)],(91,66,48))
        poly([(-.17,1.69),(-.17,1.79),(-.12,1.855),(.12,1.855),
              (.17,1.79),(.17,1.69)],iron)
    else:
        # Profile uses real sagittal silhouette, not a copy of the frontal silhouette.
        poly([(-.17,.81),(.13,.81),(.20,.53),(.185,.30),(.15,.065),
              (-.34,.025),(-.35,.005),(.19,.005),(.27,.07),
              (.23,.81)],boots)
        poly([(-.19,1.51),(.27,1.52),(.36,1.29),(.30,1.06),
              (.32,.81),(.20,.71),(-.23,.72),(-.30,1.15)],cloth)
        poly([(-.30,1.48),(-.22,1.58),(.27,1.56),(.43,1.45),
              (.40,1.32),(.29,1.29),(-.31,1.34)],fur)
        # Arm in profile hangs slightly forward of trunk.
        poly([(-.28,1.43),(-.13,1.41),(-.15,1.12),(-.11,1.01),
              (-.15,.89),(-.27,.89),(-.34,1.08)],leather)
        oval(-.23,.918,.076,.08,skin)
        oval(-.04,1.63,.166,.169,skin)
        # Profile beard hangs forward (negative Y).
        if kind=="left":
            poly([(-.22,1.61),(-.30,1.51),(-.255,1.36),(-.13,1.37),
                  (-.10,1.58)],(93,65,44))
        else:
            poly([(-.20,1.61),(-.27,1.50),(-.23,1.37),(-.08,1.40),
                  (-.09,1.60)],(93,65,44))
        poly([(-.21,1.70),(-.20,1.80),(-.14,1.858),
              (.06,1.858),(.14,1.76),(.13,1.70)],iron)
    # Lightly smooth the 2D alpha contour to preserve a workable reconstruction.
    return im
images={n:make_view(n) for n in ("front","back","left","right")}
for n,im in images.items():im.save(OUT/("03_"+n+"_aligned.png"))
# Keep separate, genuinely image-derived projected alpha silhouettes.
masks={n:(np.asarray(im)[:,:,3]>128) for n,im in images.items()}
def mask_sample(n,coords,world,zcoords):
    a=masks[n];u=np.clip(np.rint((coords-world[0])/(world[-1]-world[0])*(W-1)).astype(int),0,W-1)
    v=np.clip(np.rint((1-zcoords/1.88)*(H-1)).astype(int),0,H-1)
    return a[v[:,None],u[None,:]].T[:,:,::-1] # (coord,z ascending) - actual rows reversed
# Direct array index with top-down image coordinates.
def project(n,world,zaxis,flip=False):
    c=world[::-1] if flip else world
    iu=np.clip(np.rint((c-world[0])/(world[-1]-world[0])*(W-1)).astype(int),0,W-1)
    iv=np.clip(np.rint((1-zaxis/1.88)*(H-1)).astype(int),0,H-1)
    return masks[n][iv[None,:],iu[:,None]]
f=project("front",X,Z);b=project("back",X,Z,True)
l=project("left",Y,Z);r=project("right",Y,Z,True)
occ=f[:,None,:]&b[:,None,:]&l[None,:,:]&r[None,:,:]
# Depth and roundness priors: cross-section regularisation in point-cloud stage.
xx=X[:,None,None]; yy=Y[None,:,None]; zz=Z[None,None,:]
# Rounded torso cross sections reconstructed from image row widths.
for k,z in enumerate(Z):
    if .76<z<1.53:
        inside_x=np.flatnonzero(f[:,k]&b[:,k]);inside_y=np.flatnonzero(l[:,k]&r[:,k])
        if len(inside_x)>5 and len(inside_y)>5:
            rx=max(abs(X[inside_x[0]]),abs(X[inside_x[-1]]))
            ry=max(abs(Y[inside_y[0]]),abs(Y[inside_y[-1]]))
            torso=(xx[:,:,0]/max(rx,.15))**2+(yy[:,:,0]/max(ry,.12))**2<1.23
            if z>1.37:
                # Shoulder fur can keep a wider oval.
                torso=(xx[:,:,0]/max(rx,.15))**2+(yy[:,:,0]/max(ry,.12))**2<1.75
            # Restrict front/profile visual-hull slabs to rounded depth sections.
            occ[:,:,k]&=np.where(abs(xx[:,:,0])<.365,torso,abs(yy[:,:,0])<.18)
    if 1.53<=z<1.865:
        occ[:,:,k]&=((xx[:,:,0]/.19)**2+((yy[:,:,0]+.035)/.19)**2<1.05)
    if z<.77:
        legL=((xx[:,:,0]+.171)/.154)**2+((yy[:,:,0]-.010)/.18)**2<1.1
        legR=((xx[:,:,0]-.171)/.154)**2+((yy[:,:,0]-.010)/.18)**2<1.1
        occ[:,:,k]&=(legL|legR)
from scipy.ndimage import binary_closing,binary_opening,generate_binary_structure
occ=binary_closing(occ,iterations=1)
lab,n=label(occ);counts=np.bincount(lab.ravel());counts[0]=0
occ=lab==counts.argmax()
# Positive implicit field inside, negative outside, smooth and derive normals.
from scipy.ndimage import distance_transform_edt
dx,dy,dz=X[1]-X[0],Y[1]-Y[0],Z[1]-Z[0]
phi=distance_transform_edt(occ,sampling=(dx,dy,dz))-distance_transform_edt(~occ,sampling=(dx,dy,dz))
phi=gaussian_filter(phi,.85)
inside=phi>0
boundary=inside&~binary_erosion(inside)
ids=np.argwhere(boundary)[::2]
points=np.column_stack([X[ids[:,0]],Y[ids[:,1]],Z[ids[:,2]]])
grad=np.gradient(phi,dx,dy,dz)
normals=-np.column_stack([g[tuple(ids.T)] for g in grad])
normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
with (OUT/"04_oriented_point_cloud.ply").open("w") as fp:
    fp.write("ply\nformat ascii 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\nproperty float nx\nproperty float ny\nproperty float nz\nend_header\n"%len(points))
    for p,n in zip(points,normals):fp.write(" ".join(map(str,list(p)+list(n)))+"\n")
np.savez_compressed(OUT/"04_oriented_cloud.npz",points=points,normals=normals)
print("POINT_CLOUD_SAVED_BEFORE_MESH",len(points),flush=True)
cloud=o3d.geometry.PointCloud()
cloud.points=o3d.utility.Vector3dVector(points);cloud.normals=o3d.utility.Vector3dVector(normals)
mesh,dens=o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(cloud,depth=8,n_threads=2)
mesh.remove_degenerate_triangles();mesh.remove_duplicated_triangles()
mesh.remove_duplicated_vertices();mesh.remove_non_manifold_edges()
tri_comp,counts,_=mesh.cluster_connected_triangles()
mesh.remove_triangles_by_mask(np.array(tri_comp)!=int(np.argmax(counts)))
mesh.remove_unreferenced_vertices();mesh.compute_vertex_normals()
o3d.io.write_triangle_mesh(str(OUT/"05_poisson_from_cloud.ply"),mesh)
# Blender consumes this surface, not the input drawing and not a previous model.
(OUT/"05_reconstructed_surface.json").write_text(json.dumps({"points":np.asarray(mesh.vertices).round(6).tolist(),"triangles":np.asarray(mesh.triangles).tolist()},separators=(",",":")))
report={"command":"Mudelitehas 8000 2 vikingi_sõdalane",
        "stages":["2D design","four separately generated orthographic alpha masks","image intersection + estimated anatomical depth","oriented point cloud PLY SAVED FIRST","Poisson surface reconstructed from point cloud","Blender quad retopology","8000 quad body","GLB and web viewer"],
        "point_cloud_count":len(points),"grid":[len(X),len(Y),len(Z)],
        "source":"Illustrated 2D silhouettes traced from Viking reference design, no old 3D model reused",
        "limits":["Illustrated silhouettes are approximations rather than measured scan","Invisible depth is an estimate","Axe and shield are independently modeled equipment, outside base body quad count"]}
(OUT/"pipeline.json").write_text(json.dumps(report,indent=2))
print("POISSON_SURFACE_FROM_ORIENTED_CLOUD",len(mesh.vertices),len(mesh.triangles),flush=True)
