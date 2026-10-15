"""One-off test: traced three-axis constraints -> saved cloud -> structured quad reconstruction.
Not feature triangulation: hidden surfaces and depth are inferred and disclosed.
"""
from pathlib import Path
import json,math,hashlib,time
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt,map_coordinates
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output';REF=ROOT/'references';OUT.mkdir(exist_ok=True)
IM=Image.open(REF/'4319.png').convert('RGB');W,H=IM.size
SIDE=[(14,839),(60,806),(150,782),(250,768),(291,759),(365,712),(442,680),(534,670),(650,676),(737,700),(808,730),(875,753),(973,750),(987,778),(995,899),(980,939),(843,952),(838,974),(794,995),(744,995),(704,972),(691,953),(260,953),(246,979),(209,996),(159,996),(119,975),(103,951),(20,946),(9,920)]
TOP=[(18,272),(30,204),(64,164),(126,138),(220,128),(315,130),(326,104),(364,101),(355,125),(429,125),(600,124),(730,127),(838,136),(898,158),(932,210),(946,290),(939,383),(923,436),(885,470),(820,489),(710,499),(520,497),(367,491),(353,519),(315,516),(321,483),(230,491),(135,490),(60,465),(31,416),(17,351)]
FRONT=[(984,246),(1024,238),(1043,264),(1067,237),(1105,160),(1137,147),(1364,146),(1396,159),(1437,244),(1457,266),(1471,238),(1517,244),(1515,264),(1474,275),(1493,321),(1498,471),(1485,490),(1483,527),(1401,534),(1394,487),(1100,487),(1096,534),(1008,531),(997,484),(999,333),(1016,280),(985,271)]
BACK=[(1050,741),(1077,732),(1091,744),(1128,672),(1154,649),(1390,646),(1417,660),(1457,742),(1474,732),(1504,740),(1498,762),(1471,771),(1496,822),(1500,960),(1486,994),(1410,995),(1405,953),(1151,953),(1144,993),(1067,994),(1058,949),(1062,821),(1081,771),(1055,760)]
POLYS=[TOP,SIDE,FRONT,BACK];NAMES=['top','side','front','rear']
# Affine orthographic registration; scale is inferred, no camera calibration supplied.
J=np.array([[[926/4.56,0,0],[0,-204,0]],[[980/4.56,0,0],[0,0,-320/1.47]],[[0,495/1.82,0],[0,0,-384/1.47]],[[0,-440/1.82,0],[0,0,-346/1.47]]])
B=np.array([[16+926/2,312],[14+980/2,990],[1250,531],[1278,992]])
MASK=[];SDF=[];GRAD=[]
for name,poly in zip(NAMES,POLYS):
 im=Image.new('L',(W,H));ImageDraw.Draw(im).polygon(poly,fill=255);im.save(REF/f'mask_{name}.png');m=np.asarray(im)>0
 sdf=distance_transform_edt(m)-distance_transform_edt(~m);MASK.append(m);SDF.append(sdf);GRAD.append(np.gradient(sdf))
def project(p,k):return p@J[k].T+B[k]
def sample(a,uv):return map_coordinates(a,[uv[:,1],uv[:,0]],order=1,mode='nearest')
def fit(p):
 original=p.copy();p=p.copy()
 for iteration in range(10):
  for k in range(4):
   uv=project(p,k);d=sample(SDF[k],uv);bad=d< -2
   if not bad.any():continue
   gradient=np.column_stack([sample(GRAD[k][1],uv[bad]),sample(GRAD[k][0],uv[bad])])@J[k]
   p[bad]+=(-1.8-d[bad])[:,None]*gradient/np.maximum((gradient*gradient).sum(1)[:,None],1e-6)
 # Regularise the depth prior rather than collapsing the cloud onto contradictory
 # silhouettes. Every remaining failed projection stays explicitly reported.
 delta=p-original;length=np.linalg.norm(delta,axis=1);scale=np.minimum(.15,.025/np.maximum(length,1e-12))
 return original+delta*scale[:,None]

roof_pixels=np.array([(14,839),(60,806),(150,782),(250,768),(291,759),(365,712),(442,680),(534,670),(650,676),(737,700),(808,730),(875,753),(973,750),(994,786)],float)
roof_x=(roof_pixels[:,0]-14)/980*4.56-2.28;roof_z=(990-roof_pixels[:,1])/320*1.47
width_x=np.array([-2.28,-2.12,-1.8,-1.1,-.4,.4,1.1,1.8,2.28]);width_v=np.array([.69,.83,.90,.91,.905,.91,.91,.89,.75])
WHEEL_X=[(180-14)/980*4.56-2.28,(770-14)/980*4.56-2.28]
def body(x,theta):
 x,theta=np.broadcast_arrays(x,theta);w=np.interp(x,width_x,width_v);r=np.interp(x,roof_x,roof_z)
 # Rounded cross-section prior fitted to the front/rear and top cabin widths.
 a=np.abs((theta+np.pi)%(2*np.pi)-np.pi);rw=w*np.where(r>1.1,.66,.87)
 keys=np.array([0,.34,.78,1.15,1.57,1.98,2.36,2.75,np.pi])
 yy=np.stack([np.zeros_like(x),rw*.48,rw,w*.86,w,w*.985,w*.89,w*.47,np.zeros_like(x)],-1)
 zz=np.stack([r,r-.008,r-.035,np.minimum(r-.065,.97+(r-.97)*.31),np.minimum(r-.12,.79),np.full_like(x,.44),np.full_like(x,.25),np.full_like(x,.235),np.full_like(x,.235)],-1)
 index=np.clip(np.searchsorted(keys,a)-1,0,len(keys)-2);t=(a-keys[index])/(keys[index+1]-keys[index])
 y=np.take_along_axis(yy,index[...,None],-1)[...,0]*(1-t)+np.take_along_axis(yy,(index+1)[...,None],-1)[...,0]*t
 z=np.take_along_axis(zz,index[...,None],-1)[...,0]*(1-t)+np.take_along_axis(zz,(index+1)[...,None],-1)[...,0]*t
 for wx in WHEEL_X:
  d=x-wx;arch=.327+np.sqrt(np.maximum(.365**2-d*d,0));weight=np.clip((y/w-.62)/.22,0,1)
  z=np.where(np.abs(d)<.365,np.maximum(z,.235+(arch-.235)*weight),z)
 return np.stack([x,np.sign(np.sin(theta))*y,z],-1)

def perimeter(n):
 # n points on square perimeter -> matching structured cap boundaries.
 pts=[];q=n//4
 for a,b in [((-1,1),(1,1)),((1,1),(1,-1)),((1,-1),(-1,-1)),((-1,-1),(-1,1))]:
  for t in np.arange(q)/q:pts.append(np.array(a)*(1-t)+np.array(b)*t)
 return np.arctan2(np.array(pts)[:,0],np.array(pts)[:,1])

cloud=[];components=[]
def register(name,points,meta):
 p=np.asarray(points,float);start=sum(len(a) for a in cloud);fitted=fit(p.reshape(-1,3));cloud.append(fitted)
 components.append({'name':name,'start':start,'count':len(fitted),'shape':list(p.shape[:-1]),**meta})

xs=np.linspace(-2.28,2.28,321);th=perimeter(160)
register('body',body(xs[:,None],th[None,:]),{'kind':'body','stride':[4,4]})
for end in [0,1]:
 a=np.linspace(-1,1,41);u,v=np.meshgrid(a,a,indexing='ij');angle=np.arctan2(u,v);rad=np.maximum(abs(u),abs(v));x=-2.28 if end==0 else 2.28
 boundary=body(np.full_like(angle,x),angle);centre=np.array([x,0,(np.interp(x,roof_x,roof_z)+.235)/2]);p=centre+(boundary-centre)*rad[...,None]
 register('cap_'+str(end),p,{'kind':'cap','end':end,'stride':[4,4]})

wheelprofile=np.array([[.025,-.125],[.18,-.125],[.24,-.115],[.318,-.095],[.327,0],[.318,.095],[.24,.115],[.18,.125],[.025,.125]])
for axle,wx in enumerate(WHEEL_X):
 for sign in [-1,1]:
  angle=np.arange(160)/160*2*np.pi;t=np.arange(36)/4;ii=t.astype(int);f=t-ii;prof=wheelprofile[ii]*(1-f[:,None])+wheelprofile[(ii+1)%9]*f[:,None]
  rr=prof[:,0][None,:];y=sign*.785+prof[:,1][None,:]+np.zeros((160,1));x=wx+np.cos(angle)[:,None]*rr;z=.327+np.sin(angle)[:,None]*rr
  register(f'wheel_{axle}_{sign}',np.stack([x,y,z],-1),{'kind':'wheel','stride':[4,4],'axle':axle,'side':sign})

# Mirror cubes are surface samples, not faces; surface topology is built only after cloud save.
for sign in [-1,1]:
 center=np.array([-.80,sign*.965,1.005]);dims=np.array([.23,.24,.13]);patch=[]
 for axis in range(3):
  others=[i for i in range(3) if i!=axis]
  for side in [-1,1]:
   a,b=np.meshgrid(np.linspace(-.5,.5,9),np.linspace(-.5,.5,9),indexing='ij');p=np.zeros(a.shape+(3,));p[...,axis]=side*.5;p[...,others[0]]=a;p[...,others[1]]=b
   # Mildly rounded box shape prior.
   p=p*.88+(.12*p/np.maximum(np.linalg.norm(p,axis=-1,keepdims=True),1e-9)*.5)
   patch.append(center+p*dims)
 register('mirror_'+str(sign),patch,{'kind':'mirror','side':sign,'stride':[4,4]})

for x0 in [-.08,.91]:
 for sign in [-1,1]:
  t=np.arange(40)/40*2*np.pi;s=np.arange(24)/24*2*np.pi
  # Small elongated door-handle loop, sampled densely before 4x3 quad reconstruction.
  x=x0+(.096+.011*np.cos(s)[None,:])*np.cos(t)[:,None];z=.862+(.018+.007*np.cos(s)[None,:])*np.sin(t)[:,None];y=sign*(.906+.009*np.sin(s)[None,:])+np.zeros((40,1))
  register(f'handle_{x0}_{sign}',np.stack([x,y,z],-1),{'kind':'handle','side':sign,'stride':[10,8]})

def panel(name,axis,constant,urange,vrange,nu,nv,material):
 u,v=np.meshgrid(np.linspace(*urange,nu*4+1),np.linspace(*vrange,nv*4+1),indexing='ij');p=np.zeros(u.shape+(3,));p[...,axis]=constant;others=[i for i in range(3) if i!=axis];p[...,others[0]]=u;p[...,others[1]]=v
 register(name,p,{'kind':'panel','stride':[4,4],'material':material,'view':2 if constant<0 else 3})
panel('front_plate',0,-2.285,(-.28,.28),(.30,.43),4,2,'plate')
panel('rear_plate',0,2.285,(-.27,.27),(.59,.75),4,2,'plate')
panel('grille',0,-2.287,(-.59,.59),(.45,.64),8,4,'front_photo')
for sign in [-1,1]:panel('fog_'+str(sign),0,-2.288,(sign*.50-.08,sign*.50+.08),(.31,.41),4,2,'front_photo')

points=np.concatenate(cloud);uv=np.stack([project(points,k) for k in range(4)],1);residual=np.stack([sample(SDF[k],uv[:,k]) for k in range(4)],1)
support=residual>=-3;axes_support=np.column_stack([support[:,0],support[:,1],support[:,2]|support[:,3]])
assert np.isfinite(points).all()
np.savez_compressed(OUT/'04_point_cloud.npz',points=points.astype('f4'),reference_pixels=uv.astype('f4'),signed_silhouette_distance_px=residual.astype('f4'),view_support=support,axis_support=axes_support)
with (OUT/'04_point_cloud.ply').open('w') as f:
 f.write(f'ply\nformat ascii 1.0\nelement vertex {len(points)}\nproperty float x\nproperty float y\nproperty float z\nend_header\n');np.savetxt(f,points,fmt='%.6f')
(OUT/'cloud_components.json').write_text(json.dumps(components,indent=2))
calibration={'source_sha256':hashlib.sha256((REF/'4319.png').read_bytes()).hexdigest(),'source_pixels':[W,H],'assumed_dimensions_m':[4.56,1.82,1.47],'axes':['X longitudinal front negative','Y lateral','Z up'],'view_order':NAMES,'projection_jacobians':J.tolist(),'projection_offsets':B.tolist(),'traced_polygons':dict(zip(NAMES,POLYS)),'roof_trace_side_pixels':roof_pixels.tolist(),'depth':'orthographic affine estimate; not measured photogrammetry','feature_correspondence':'not identifiable for every surface point in these four views; silhouette support is distinct from visible feature matches'}
(REF/'calibration.json').write_text(json.dumps(calibration,indent=2))
report={'test':'Mudelitehas 5000 - three-axis per-point support experiment','status':'cloud_saved_before_mesh','cloud_points':len(points),'points_checked_in_all_four_views':len(points),'points_supported_in_3_axes':int(axes_support.all(1).sum()),'points_supported_in_all_4_silhouettes':int(support.all(1).sum()),'minimum_searched_directions':3,'points_with_unresolved_projection_conflicts':int((~axes_support.all(1)).sum()),'support_tolerance_px':3,'support_counts':{n:int(support[:,k].sum()) for k,n in enumerate(NAMES)},'minimum_silhouette_distance_px':residual.min(0).tolist(),'per_point_visible_feature_match_claim':False,'unique_three_view_triangulation_claim':False,'assumptions':['affine orthographic registration and left/right symmetry','manually traced silhouette/roof profiles','rounded body section, wheel and mirror depth priors','occluded surfaces only constrained by projections; not observed in three photographs','materials use source image projections and include original lighting','remaining projection conflicts are reported instead of crushing geometry onto masks'],'cloud_sha256':hashlib.sha256((OUT/'04_point_cloud.npz').read_bytes()).hexdigest()}
(OUT/'three_view_test.json').write_text(json.dumps(report,indent=2));print('CLOUD_SAVED_BEFORE_ANY_FACES',len(points),flush=True)

from multiview import validate_cloud
gate=validate_cloud(OUT/'04_point_cloud.npz',REF/'calibration.json')
(OUT/'three_direction_gate.json').write_text(json.dumps(gate,indent=2))
print('THREE_DIRECTION_GATE',json.dumps(gate),flush=True)

# Reopen the saved independent cloud; all final vertices are selected from it.
points=np.load(OUT/'04_point_cloud.npz')['points'];objects=[]
def item(name,vertices,faces,materials,meta):
 assert all(len(f)==4 for f in faces)
 objects.append({'name':name,'vertices':np.asarray(vertices).tolist(),'faces':faces,'materials':materials,**meta})
for c in components:
 p=points[c['start']:c['start']+c['count']].reshape(c['shape']+[3]);kind=c['kind'];faces=[];mats=[]
 if kind=='body':
  a=p[::4,::4];n,m=a.shape[:2]
  for i in range(n-1):
   for j in range(m):faces.append([i*m+j,(i+1)*m+j,(i+1)*m+(j+1)%m,i*m+(j+1)%m]);mats.append('paint')
  item('Body_shell',a.reshape(-1,3),faces,mats,{'kind':kind})
 elif kind=='cap':
  a=p[::4,::4];n,m=a.shape[:2]
  for i in range(n-1):
   for j in range(m-1):faces.append([i*m+j,(i+1)*m+j,(i+1)*m+j+1,i*m+j+1]);mats.append('paint')
  item(c['name'],a.reshape(-1,3),faces,mats,{'kind':kind})
 elif kind in ['wheel','handle']:
  a=p[::c['stride'][0],::c['stride'][1]];n,m=a.shape[:2]
  for i in range(n):
   for j in range(m):
    faces.append([i*m+j,((i+1)%n)*m+j,((i+1)%n)*m+(j+1)%m,i*m+(j+1)%m]);mats.append('rubber' if kind=='wheel' and j in [2,3,4,5] else ('rim' if kind=='wheel' else 'chrome'))
  item(c['name'],a.reshape(-1,3),faces,mats,{'kind':kind,'axle':c.get('axle'),'side':c.get('side')})
 elif kind=='mirror':
  verts=[]
  for patch in p:
   a=patch[::4,::4];offset=len(verts);verts.extend(a.reshape(-1,3))
   for i in range(2):
    for j in range(2):faces.append([offset+i*3+j,offset+(i+1)*3+j,offset+(i+1)*3+j+1,offset+i*3+j+1]);mats.append('paint')
  item(c['name'],verts,faces,mats,{'kind':kind})
 else:
  a=p[::4,::4];n,m=a.shape[:2]
  for i in range(n-1):
   for j in range(m-1):faces.append([i*m+j,(i+1)*m+j,(i+1)*m+j+1,i*m+j+1]);mats.append(c['material'])
  item(c['name'],a.reshape(-1,3),faces,mats,{'kind':kind,'view':c['view']})
assert sum(len(o['faces']) for o in objects)==5000
(OUT/'05_quad_surface.json').write_text(json.dumps({'objects':objects,'quad_faces':5000,'cloud_sha256':report['cloud_sha256']},separators=(',',':')))
report['status']='cloud_then_quad_mesh_created';report['mesh_quads_total']=5000;report['body_quads_including_caps']=3400;report['all_mesh_vertices_from_saved_cloud']=True
(OUT/'three_view_test.json').write_text(json.dumps(report,indent=2))
# Diagnostic reprojection: same sampled cloud points in each of the four source regions.
overlay=IM.copy();draw=ImageDraw.Draw(overlay)
for k in range(4):
 draw.line(POLYS[k]+[POLYS[k][0]],fill=(220,75,40),width=2)
 for idx in range(0,len(points),max(1,len(points)//1700)):
  u,v=uv[idx,k];color=(25,170,85) if axes_support[idx].all() else (255,0,0);draw.ellipse((u-1,v-1,u+1,v+1),fill=color)
overlay.save(OUT/'Punktide_kontroll_4_vaates.png')
print(json.dumps(report),flush=True)
