"""Mudelitehas 8000 level 2, GitHub Blender stage.
Uses ONLY the surface previously made by Poisson reconstruction of saved 4-view cloud.
"""
import bpy,bmesh,json,math,struct
from pathlib import Path
from mathutils import Vector
OUT=Path("output/viking_mudelitehas");OUT.mkdir(parents=True,exist_ok=True)
TARGET_BASE=8000

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
 mesh=bpy.data.meshes.new('Viking_exact_quad_topology')
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
  fi=max(range(len(F)),key=lambda i:sum((Vector(V[F[i][k]])-Vector(V[F[i][(k+1)%4]])).length_squared for k in range(4)))
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



bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
source=json.loads((OUT/"05_reconstructed_surface.json").read_text())
mesh=bpy.data.meshes.new("Viking_from_oriented_cloud_Poisson")
mesh.from_pydata(source["points"],[],source["triangles"]);mesh.update()
ob=bpy.data.objects.new("VikingBody_8000_TRUE_QUADS",mesh)
bpy.context.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob;ob.select_set(True)
# Voxel close tiny Poisson openings and relax. No primitive body is introduced.
rem=ob.modifiers.new("Repair_surface","REMESH");rem.mode='VOXEL';rem.voxel_size=.014
bpy.ops.object.modifier_apply(modifier=rem.name)
sm=ob.modifiers.new("Relax_image_based_surface","SMOOTH");sm.factor=.65;sm.iterations=3
bpy.ops.object.modifier_apply(modifier=sm.name)
print("RECONSTRUCTION_VALID",validate(ob),flush=True)
# Target slightly low and adjust to exactly 8000 by surface-preserving quad patches.
bpy.ops.object.quadriflow_remesh(target_faces=7750,seed=0,use_preserve_sharp=False,use_preserve_boundary=False)
print("QUADRIFLOW_VALID",validate(ob,True),flush=True)
report=exact_quads(ob)
assert report["faces"]==8000 and report["quad_faces"]==8000,report
print("EXACT_TRUE_8000_BODY_QUADS",report,flush=True)
def material(name,color,metal=0.,rough=.72):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 bs=m.node_tree.nodes.get("Principled BSDF")
 bs.inputs["Base Color"].default_value=(*color,1);bs.inputs["Metallic"].default_value=metal;bs.inputs["Roughness"].default_value=rough
 return m
mats=[
 material("Worn steel helmet",(.23,.27,.29),.8,.45),
 material("Rough natural fur",(.27,.19,.13),.0,.94),
 material("Weathered leather armor",(.19,.105,.057),.08,.83),
 material("Dark blue quilted textile",(.072,.11,.135),0,.89),
 material("Bearded skin",(.49,.28,.17),0,.82),
 material("Thick leather boots",(.16,.09,.045),0,.9),
 material("Dark iron chainmail",(.135,.15,.16),.65,.52),
 material("Ash wood shield",(.29,.16,.075),0,.86),
 material("Dark steel edge",(.17,.20,.21),.85,.38)
]
for m in mats:ob.data.materials.append(m)
# Face classification creates colour regions without taking colour from an old mesh.
# The reference sketches provide silhouette; estimated surface material zones
# are labelled by anatomical height/depth, e.g. torso armour vs beard and fur.
for poly in ob.data.polygons:
 x,y,z=poly.center
 if z>1.765: mat=0
 elif z>1.54 and abs(x)<.23:mat=4
 elif z>1.30 and (abs(x)>.26 or y>.12):mat=1
 elif z>1.33 and y<-.15 and abs(x)<.19:mat=2
 elif z>1.06 and abs(x)<.34:mat=6 if abs(x)<.245 and y<-.16 else 2
 elif z>.84 and abs(x)<.37:mat=2
 elif z<.35:mat=5
 elif z>.90 and abs(x)>.35:mat=2
 else:mat=3
 poly.material_index=mat;poly.use_smooth=True
def new_quads(name,verts,faces,mat_ids=None,material_indices=None):
 m=bpy.data.meshes.new(name+"_mesh");m.from_pydata(verts,[],faces);m.update()
 o=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(o)
 for k in (material_indices if material_indices is not None else range(len(mats))):
  m.materials.append(mats[k])
 if mat_ids:
  for f,k in zip(m.polygons,mat_ids):f.material_index=k
 for p in m.polygons:p.use_smooth=True
 return o
# Shield as an equipment mesh, independent of the reconstructed 8000-quad body.
# Ring vertices & face indices (no Blender primitive construction).
V=[];F=[];M=[]
N=48;cx=.57;cy=-.265;cz=1.025;rad=.315
for y,r in [(-.345,.065),(-.37,.13),(-.32,.29),(-.29,rad),(-.26,rad),(-.245,.29),(-.237,.12),(-.242,.065)]:
 for i in range(N):
  a=2*math.pi*i/N
  V.append((cx+r*math.cos(a),y,cz+r*math.sin(a)))
for k in range(7):
 for i in range(N):
  F.append((k*N+i,k*N+(i+1)%N,(k+1)*N+(i+1)%N,(k+1)*N+i))
  M.append(1 if k in (2,3,4) else (0 if k in (0,6) else 2))
# Back-to-front center bosses, fan triangles confined to accessory only.
V.append((cx,-.412,cz));V.append((cx,-.22,cz))
for i in range(N):
 F.append((N*8, (i+1)%N, i));M.append(0)
 F.append((N*8+1,7*N+i,7*N+(i+1)%N));M.append(0)
shield=new_quads("Shield_detachable",V,F,M,[8,7,2])
# Axe handle by indexed cross-sections and quads.
V=[];F=[]
S=12
for j in range(18):
 z=.46+j*.051;x=-.56-.050*(z-.46);y=-.25
 for i in range(S):
  a=2*math.pi*i/S
  V.append((x+.020*math.cos(a),y+.020*math.sin(a),z))
for j in range(17):
 for i in range(S):F.append((j*S+i,j*S+(i+1)%S,(j+1)*S+(i+1)%S,(j+1)*S+i))
for i in range(S):F.append((i,(i+1)%S,0)) if False else None
handle=new_quads("Axe_wooden_handle",V,F,material_indices=[7])
# Etched broad single-bladed head, planar outline extruded in Y.
outline=[(-.606,1.225),(-.80,1.31),(-.88,1.31),(-.855,1.19),(-.91,1.10),(-.79,1.085),(-.59,1.13)]
v=[(x,y,z) for y in (-.276,-.311) for x,z in outline]
f=[]
for i in range(len(outline)):f.append((i,(i+1)%len(outline),len(outline)+(i+1)%len(outline),len(outline)+i))
# closed cap triangles; small and intentionally NOT counted as body quads
for i in range(1,len(outline)-1):
 f.append((0,i+1,i));f.append((len(outline),len(outline)+i,len(outline)+i+1))
axe=new_quads("Axe_iron_head",v,f,material_indices=[8])
gear=[shield,handle,axe]
# Save exact body (without scene) to GLB and OBJ.
bpy.ops.object.select_all(action='DESELECT')
for item in [ob,*gear]:item.select_set(True)
bpy.context.view_layer.objects.active=ob
bpy.ops.export_scene.gltf(filepath=str((OUT/"Viking_Mudelitehas_8000_Level2.glb").resolve()),export_format='GLB',use_selection=True,export_apply=True)
bpy.ops.wm.obj_export(filepath=str((OUT/"Viking_Mudelitehas_8000_Level2.obj").resolve()),export_selected_objects=True)
with (OUT/"Viking_Mudelitehas_8000_Level2.glb").open("rb") as fp:
 fp.read(12);ln,kind=struct.unpack("<II",fp.read(8));gltf=json.loads(fp.read(ln))
triangles=sum(gltf["accessors"][p["indices"]]["count"]//3 for m in gltf["meshes"] for p in m["primitives"])
stats={"pipeline":"2D four views -> saved cloud -> Poisson mesh -> exact Blender QuadriFlow retopo",
 "body_quads":report["quad_faces"],"body_connected_components":report["components"],
 "body_nonmanifold_edges":report["nonmanifold_edges"],"body_boundary_edges":report["boundary_edges"],
 "body_vertices":report["vertices"],"equipment_meshes":[o.name for o in gear],
 "total_glb_triangles_including_gear":triangles,"blender":bpy.app.version_string,
 "limitations":["4 ortho views are design silhouettes, not measured scans","Unseen surface depth is inferred",
 "Axe, shield and fasteners are independent equipment meshes and not part of the 8000 body quads"]}
(OUT/"validation.json").write_text(json.dumps(stats,indent=2))
# Studio, render true model from 4 sides (not AI preview images).
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=700;scene.render.resolution_y=790;scene.render.resolution_percentage=100
scene.world.color=(.15,.17,.2)
def aim(o,pos):o.rotation_euler=(Vector(pos)-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(2.8,-4,2.15))
cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=2.32
aim(cam,(0,0,.96))
for pos,pow,size in [((3,-4,5),750,4),((-3,-1,3),420,4),((1,3,4),560,3)]:
 bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=pow;o.data.size=size;aim(o,(0,0,.9))
for nm,xyz in [('preview',(2.7,-4,2.1)),('front',(0,-5,1.15)),('left',(-5,0,1.15)),('back',(0,5,1.15)),('right',(5,0,1.15))]:
 cam.location=xyz;aim(cam,(0,0,.96));scene.render.filepath=str((OUT/(nm+".png")).resolve())
 bpy.ops.render.render(write_still=True)
# Web presenter bundled in the workflow artifact (also deployed to site/viking).
bpy.ops.wm.save_as_mainfile(filepath=str((OUT/"Viking_Mudelitehas_8000_Level2.blend").resolve()))
print("MUD ELITEHAS_8000_LEVEL2_COMPLETE",json.dumps(stats),flush=True)
