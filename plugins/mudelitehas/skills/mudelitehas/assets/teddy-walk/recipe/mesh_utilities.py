"""Shared mesh, topology and export-view helpers; no animal-specific generator."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
import numpy as np
from PIL import Image,ImageDraw
OUT=Path("output")
TARGET_BASE=2500

def validate(ob,require_quads=False):
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 report={'vertices':len(bm.verts),'faces':len(bm.faces),'quad_faces':sum(len(f.verts)==4 for f in bm.faces),
 'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
 'nonmanifold_vertices':sum(not v.is_manifold for v in bm.verts),'loose_vertices':sum(not v.link_faces for v in bm.verts)}
 todo=set(bm.verts);components=0
 while todo:
  stack=[todo.pop()];components+=1
  while stack:
   for e in stack.pop().link_edges:
    for v in e.verts:
     if v in todo:todo.remove(v);stack.append(v)
 report['components']=components;report['volume']=round(bm.calc_volume(),6)
 assert components==1 and not any(report[k] for k in ('boundary_edges','nonmanifold_edges','nonmanifold_vertices','loose_vertices')),report
 if require_quads:assert report['quad_faces']==report['faces'],report
 assert report['volume']>0,report
 bm.to_mesh(ob.data);bm.free();return report

def replace_geometry(ob,V,F):
 used=sorted({v for f in F for v in f});remap={v:i for i,v in enumerate(used)}
 mesh=bpy.data.meshes.new('Mudelitehas_quad_topology')
 mesh.from_pydata([V[v] for v in used],[],[tuple(remap[v] for v in f) for f in F]);mesh.update()
 old=ob.data;ob.data=mesh;bpy.data.meshes.remove(old)

def exact_quads(ob):
 V=[tuple(v.co) for v in ob.data.vertices];F=[tuple(p.vertices) for p in ob.data.polygons]
 assert all(len(f)==4 for f in F)
 assert len(F)<=TARGET_BASE,(len(F),TARGET_BASE)
 # If the count is odd, collapse one tiny quad diagonal. Neighbor quads retain
 # four vertices; shared-edge incidence is checked afterwards. No spare faces.
 if len(F)%2:
  neighbors={i:set() for i in range(len(V))}
  for f in F:
   for k in range(4):neighbors[f[k]].add(f[(k+1)%4]);neighbors[f[(k+1)%4]].add(f[k])
  options=[]
  for fi,f in enumerate(F):
   for k in (0,1):
    u,v=f[k],f[k+2]
    if len(neighbors[u]&neighbors[v])==2:
     options.append(((Vector(V[u])-Vector(V[v])).length_squared,fi,u,v))
  assert options,'No safe quad diagonal collapse'
  _,fi,u,v=min(options);V[u]=tuple((Vector(V[u])+Vector(V[v]))/2)
  mapped=[tuple(u if q==v else q for q in f) for f in F]
  F=[f for f in mapped if len(set(f))==4]
  replace_geometry(ob,V,F);validate(ob,True)
  V=[tuple(v.co) for v in ob.data.vertices];F=[tuple(p.vertices) for p in ob.data.polygons]
 # Insetting one face adds four quads without changing any shared boundary edge.
 delta=TARGET_BASE-len(F)
 while delta>=4:
  fi=max(range(len(F)),key=lambda i:((Vector(V[F[i][1]])-Vector(V[F[i][0]])).cross(Vector(V[F[i][2]])-Vector(V[F[i][0]]))).length + ((Vector(V[F[i][2]])-Vector(V[F[i][0]])).cross(Vector(V[F[i][3]])-Vector(V[F[i][0]]))).length)
  outer=F.pop(fi);center=sum((Vector(V[v]) for v in outer),Vector())/4;inner=[]
  for v in outer:inner.append(len(V));V.append(tuple(Vector(V[v])*.67+center*.33))
  F.append(tuple(inner))
  for k in range(4):F.append((outer[k],outer[(k+1)%4],inner[(k+1)%4],inner[k]))
  delta-=4
 # A six-edge patch containing two quads can be replaced by four quads (+2)
 # while retaining every exterior edge. This avoids T-junctions.
 if delta==2:
  edges={}
  for fi,f in enumerate(F):
   for k in range(4):edges.setdefault(tuple(sorted((f[k],f[(k+1)%4]))),[]).append(fi)
  for (a,b),items in edges.items():
   if len(items)!=2:continue
   i,j=items
   if len(set(F[i]+F[j]))!=6:continue
   adj={}
   for f in (F[i],F[j]):
    for k in range(4):
     u,v=f[k],f[(k+1)%4]
     if {u,v}=={a,b}:continue
     adj.setdefault(u,[]).append(v);adj.setdefault(v,[]).append(u)
   loop=[a];prev=None;current=a
   while len(loop)<6:
    nxt=next(v for v in adj[current] if v!=prev);loop.append(nxt);prev,current=current,nxt
   loop=loop[-1:]+loop[:-1]
   if loop[4]!=b:continue
   g=len(V);V.append(tuple(sum((Vector(V[loop[k]]) for k in (0,1,4,5)),Vector())/4))
   h=len(V);V.append(tuple(sum((Vector(V[loop[k]]) for k in (1,2,3,4)),Vector())/4))
   for fi in sorted((i,j),reverse=True):F.pop(fi)
   p=loop;F.extend([(p[0],p[1],g,p[5]),(p[2],p[3],p[4],h),(p[1],p[2],h,g),(p[4],p[5],g,h)])
   break
  else:raise RuntimeError('Cannot add final two quads')
 assert len(F)==TARGET_BASE,len(F)
 replace_geometry(ob,V,F);return validate(ob,True)

def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()

def material(name,color,rough=.6):
 mat=bpy.data.materials.new(name);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;return mat

def attach_detail(ob,rig,bone):
 ob.parent=rig;vg=ob.vertex_groups.new(name=bone);vg.add(list(range(len(ob.data.vertices))),1,'REPLACE');mod=ob.modifiers.new('Detail_skin','ARMATURE');mod.object=rig
 for p in ob.data.polygons:p.use_smooth=True
 return ob

def mesh_silhouette_check(body):
 from mathutils.bvhtree import BVHTree
 rig=body.parent;old=rig.data.pose_position;rig.data.pose_position='REST';bpy.context.view_layer.update()
 tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get());d=np.load(OUT/'aligned_images.npz');scores={};panel=Image.new('RGB',(600*4,720),(25,31,40));draw=ImageDraw.Draw(panel)
 for ci,name in enumerate(('front','left','back','right')):
  ax=d['x'] if name in ('front','back') else d['y'];zs=d['z'][::-1];mask=np.zeros((len(zs),len(ax)),bool)
  for j,z in enumerate(zs):
   for i,u in enumerate(ax):
    origin=Vector((u,-3,z)) if name in ('front','back') else Vector((-3,u,z));direction=Vector((0,1,0)) if name in ('front','back') else Vector((1,0,0))
    mask[j,i]=tree.ray_cast(origin,direction,6)[0] is not None
  target=d[name+'_mask'];iou=float((mask&target).sum()/max(1,(mask|target).sum()));scores[name]=iou
  rgb=np.zeros((*mask.shape,3),dtype='uint8');rgb[target]=[65,150,235];rgb[mask]=[235,135,45];rgb[target&mask]=[160,207,165]
  im=Image.fromarray(rgb).resize((560,640));panel.paste(im,(ci*600+20,45));draw.text((ci*600+20,12),name+' FINAL MESH IoU '+str(round(iou,3)),fill='white')
 draw.text((20,697),'green=overlap  blue=source only  orange=mesh only; REST pose, estimated orthographic cameras',fill='white');panel.save(OUT/'08_final_mesh_silhouette_comparison.png')
 rig.data.pose_position=old;bpy.context.view_layer.update();return scores
