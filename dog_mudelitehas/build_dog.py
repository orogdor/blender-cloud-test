"""Blender stage: reconstructed surface -> 100000 quads -> skin -> run GIF.
Requires reconstruct_dog.py to have produced output/dog_mudelitehas.
"""
import bpy,bmesh,json,math,struct,shutil
from pathlib import Path
from mathutils import Vector,Quaternion
import numpy as np
from PIL import Image,ImageDraw,ImageFont
OUT=Path('output/dog_mudelitehas');OUT.mkdir(parents=True,exist_ok=True)
TARGET_BASE=6250
FRAMES=48
FPS=24

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
 mesh=bpy.data.meshes.new('Dog_exact_quad_topology')
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

def bone_dist(p,a,b):
 a,b=Vector(a),Vector(b);d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));return(p-(a+d*t)).length

def rig_dog(ob):
 arm=bpy.data.armatures.new('Canine_sitting_skeleton');rig=bpy.data.objects.new('Dog_Rig',arm);bpy.context.collection.objects.link(rig)
 bpy.context.view_layer.objects.active=rig;rig.select_set(True);ob.select_set(False);bpy.ops.object.mode_set(mode='EDIT')
 specs={'root':((0,0,0),(0,0,.15),None),'pelvis':((0,.08,.20),(0,.02,.46),'root'),
 'spine':((0,.02,.46),(0,-.04,.81),'pelvis'),'chest':((0,-.04,.81),(0,-.08,1.14),'spine'),
 'neck':((0,-.08,1.14),(0,-.09,1.43),'chest'),'head':((0,-.09,1.43),(0,-.14,1.70),'neck'),
 'jaw':((0,-.16,1.46),(0,-.46,1.43),'head')}
 for sign,side in ((1,'L'),(-1,'R')):
  specs.update({'shoulder.'+side:((sign*.19,-.08,1.16),(sign*.26,-.20,1.09),'chest'),
   'upper_foreleg.'+side:((sign*.26,-.20,1.09),(sign*.28,-.42,1.02),'shoulder.'+side),
   'lower_foreleg.'+side:((sign*.28,-.42,1.02),(sign*.28,-.50,.88),'upper_foreleg.'+side),
   'forepaw.'+side:((sign*.28,-.50,.88),(sign*.28,-.48,.80),'lower_foreleg.'+side),
   'thigh.'+side:((sign*.13,.07,.36),(sign*.27,-.08,.37),'pelvis'),
   'hock.'+side:((sign*.27,-.08,.37),(sign*.27,-.06,.11),'thigh.'+side),
   'hindpaw.'+side:((sign*.27,-.06,.11),(sign*.28,-.26,.055),'hock.'+side),
   'ear.'+side:((sign*.19,.015,1.68),(sign*.28,-.01,1.48),'head')})
 tail=[(0,.22,.15),(.11,.33,.09),(.28,.44,.095),(.44,.52,.12),(.57,.58,.17)]
 for i in range(4):specs['tail_'+str(i+1)]=(tail[i],tail[i+1],'pelvis' if i==0 else 'tail_'+str(i))
 for name,(head,tail,parent) in specs.items():
  bone=arm.edit_bones.new(name);bone.head=head;bone.tail=tail
  if parent:bone.parent=arm.edit_bones[parent]
  bone.use_deform=name!='root'
 bpy.ops.object.mode_set(mode='OBJECT');groups={name:ob.vertex_groups.new(name=name) for name in specs if name!='root'}
 for v in ob.data.vertices:
  p=v.co;x,y,z=p;side='L' if x>=0 else 'R'
  if z>1.40:
   names=['head','neck']
   if abs(x)>.18 and y>-.15:names+=['ear.'+side]
  elif z>1.23:names=['neck','head','chest']
  elif .67<z<1.23 and abs(x)>.195 and y<-.22:
   names=['shoulder.'+side,'upper_foreleg.'+side,'lower_foreleg.'+side,'forepaw.'+side]
  elif z<.29 and y>.19 and (x>.14 or y>.28):names=['tail_1','tail_2','tail_3','tail_4','pelvis']
  elif z<.47 and abs(x)>.14:names=['thigh.'+side,'hock.'+side,'hindpaw.'+side,'pelvis']
  else:names=['pelvis','spine','chest','neck']
  ds=[bone_dist(p,*specs[n][:2]) for n in names];nearest=sorted(range(len(names)),key=lambda i:ds[i])[:3]
  weights=[1/(ds[i]+.035)**5 for i in nearest];total=sum(weights)
  for i,w in zip(nearest,weights):groups[names[i]].add([v.index],w/total,'REPLACE')
 ob.parent=rig;bpy.context.view_layer.objects.active=ob;ob.select_set(True);rig.select_set(False)
 # Smooth anatomical region transitions before subdivision to prevent skin spurs.
 bpy.ops.object.vertex_group_smooth(group_select_mode='ALL',factor=.65,repeat=8,expand=0)
 bpy.ops.object.vertex_group_normalize_all(lock_active=False)
 # UVs and low-resolution skin are built before the detail subdivision.
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1519,island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
 sub=ob.modifiers.new('100000_body_quads','SUBSURF');sub.levels=2;sub.render_levels=2;bpy.ops.object.modifier_apply(modifier=sub.name)
 mod=ob.modifiers.new('Canine_skin','ARMATURE');mod.object=rig
 rig.show_in_front=True;return rig,specs

def source_colors(ob):
 """Four-view diffuse color classification removes most baked lighting.
 The color map is inferred intrinsic albedo, not copied photograph shading.
 """
 d=np.load(OUT/'aligned_images.npz');n=len(ob.data.vertices)
 co=np.empty(n*3,dtype='float32');no=np.empty(n*3,dtype='float32')
 ob.data.vertices.foreach_get('co',co);ob.data.vertices.foreach_get('normal',no);co=co.reshape(-1,3);no=no.reshape(-1,3)
 x,y,z=co.T;nx,ny,nz=no.T;color=np.zeros((n,3));weight=np.zeros(n)
 for name,axis,normal in [('front',x,-ny),('back',x,ny),('left',y,-nx),('right',y,nx)]:
  ax=d['x'] if name in ('front','back') else d['y'];rgba=d[name+'_rgba'];h,w=rgba.shape[:2]
  u=np.clip(np.rint((axis-ax[0])/(ax[-1]-ax[0])*(w-1)),0,w-1).astype(int)
  v=np.clip(np.rint((d['z'][-1]-z)/(d['z'][-1]-d['z'][0])*(h-1)),0,h-1).astype(int)
  pixels=rgba[v,u]/255.;ww=np.maximum(normal,0)**4*(pixels[:,3]>.5)
  color+=pixels[:,:3]*ww[:,None];weight+=ww
 color/=np.maximum(weight[:,None],1e-6);color[weight<1e-4]=[.75,.53,.32]
 sat=color.max(1)-color.min(1);brightness=color.mean(1)
 cream=np.clip((.22-sat)/.09,0,1)*np.clip((brightness-.38)/.2,0,1)
 cream=np.maximum(cream,np.clip((.20-np.abs(x))/.05,0,1)*np.clip((-y-.19)/.06,0,1)*((z>.64)&(z<1.38)))
 cream=np.maximum(cream,np.clip((.15-np.abs(x))/.045,0,1)*np.clip((-y-.28)/.05,0,1)*((z>1.39)&(z<1.52)))
 cream*=np.where(z>1.53,0,1)
 # Palette compression removes directional light/dark patches from source views.
 variation=np.clip((color[:,0]-color[:,2]-.30)*.08,-.025,.025)
 tan=np.array([.72,.49,.29])[None,:]+variation[:,None]
 rgb=tan*(1-cream[:,None])+np.array([.83,.80,.72])[None,:]*cream[:,None]
 linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
 rgba=np.column_stack([linear,np.ones(n)]).astype('float32')
 attr=ob.data.color_attributes.new(name='intrinsic_albedo',type='FLOAT_COLOR',domain='POINT');attr.data.foreach_set('color',rgba.ravel())

def setup_material(ob):
 source_colors(ob)
 mat=bpy.data.materials.new('Dog_short_coat_PBR');mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF');out=nodes.get('Material Output')
 bs.inputs['Roughness'].default_value=.78
 if 'Sheen Weight' in bs.inputs:bs.inputs['Sheen Weight'].default_value=.24
 elif 'Sheen' in bs.inputs:bs.inputs['Sheen'].default_value=.24
 vertex=nodes.new('ShaderNodeVertexColor');vertex.layer_name='intrinsic_albedo';links.new(vertex.outputs['Color'],bs.inputs['Base Color'])
 coords=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(1,1,.18)
 links.new(coords.outputs['Generated'],mapping.inputs[0]);noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=280;noise.inputs['Detail'].default_value=2
 links.new(mapping.outputs[0],noise.inputs['Vector']);bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.25;bump.inputs['Distance'].default_value=.0018
 links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
 ob.data.materials.clear();ob.data.materials.append(mat)
 for p in ob.data.polygons:p.use_smooth=True
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.cycles.use_denoising=False
 bpy.context.view_layer.objects.active=ob
 for o in bpy.context.selected_objects:o.select_set(False)
 ob.select_set(True);texdir=OUT/'textures';texdir.mkdir(exist_ok=True)
 texnode=nodes.new('ShaderNodeTexImage')
 def bake(name,kind):
  im=bpy.data.images.new(name,width=2048,height=2048,alpha=False)
  if kind=='NORMAL':im.colorspace_settings.name='Non-Color'
  texnode.image=im;nodes.active=texnode
  bpy.ops.object.bake(type=kind,margin=12,use_clear=True)
  im.filepath_raw=str((texdir/(name+'.png')).resolve());im.file_format='PNG';im.save();im.pack();return im
 emission=nodes.new('ShaderNodeEmission');links.new(vertex.outputs['Color'],emission.inputs['Color']);links.new(emission.outputs[0],out.inputs['Surface'])
 albedo=bake('Dog_BaseColor','EMIT');links.new(bs.outputs['BSDF'],out.inputs['Surface'])
 normal=bake('Dog_Normal','NORMAL')
 # Reconnect the baked maps for a portable glTF material, without procedural-only nodes.
 base=nodes.new('ShaderNodeTexImage');base.image=albedo;links.new(base.outputs['Color'],bs.inputs['Base Color'])
 normtex=nodes.new('ShaderNodeTexImage');normtex.image=normal;normalnode=nodes.new('ShaderNodeNormalMap');normalnode.inputs['Strength'].default_value=.6
 links.new(normtex.outputs['Color'],normalnode.inputs['Color']);links.new(normalnode.outputs[0],bs.inputs['Normal'])
 rng=np.random.default_rng(41);rough=np.clip(.78+rng.normal(0,.018,(1024,1024)),.70,.85)
 Image.fromarray((rough*255).astype('uint8')).save(texdir/'Dog_Roughness.png')
 ri=bpy.data.images.load(str((texdir/'Dog_Roughness.png').resolve()));ri.colorspace_settings.name='Non-Color';ri.pack();rn=nodes.new('ShaderNodeTexImage');rn.image=ri;links.new(rn.outputs['Color'],bs.inputs['Roughness'])
 return mat

def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()

def material(name,color,rough=.6):
 mat=bpy.data.materials.new(name);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;return mat

def attach_detail(ob,rig,bone):
 ob.parent=rig;vg=ob.vertex_groups.new(name=bone);vg.add(list(range(len(ob.data.vertices))),1,'REPLACE');mod=ob.modifiers.new('Detail_skin','ARMATURE');mod.object=rig
 for p in ob.data.polygons:p.use_smooth=True
 return ob

def add_face_details(body,rig):
 details=[];black=material('Moist_black_nose',(.018,.014,.012),.34);eye=material('Wet_dark_brown_eyes',(.035,.017,.006),.12)
 iris=material('Amber_iris',(.12,.053,.010),.22);pupil=material('Black_pupil',(.002,.002,.001),.08);line=material('Mouth_and_nostrils',(.012,.008,.006),.72)
 nodes=black.node_tree.nodes;links=black.node_tree.links;noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=75;noise.inputs['Detail'].default_value=2
 bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.001;links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],nodes.get('Principled BSDF').inputs['Normal'])
 def front_hit(x,z):
  hit,p,n,face=body.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
  return p if hit else Vector((x,-.28,z))
 def sphere(name,pos,scale,mat):
  bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=pos);ob=bpy.context.object;ob.name=name;ob.scale=scale
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  # Apply locations to mesh so all detail skin matrices share body's coordinates.
  bpy.ops.object.transform_apply(location=True,rotation=False,scale=False);ob.data.materials.append(mat);attach_detail(ob,rig,'head');details.append(ob);return ob
 for s,side in ((1,'L'),(-1,'R')):
  p=front_hit(s*.108,1.655);p.y-=.012
  sphere('Eye.'+side,p,(.034,.018,.031),eye)
  sphere('Iris.'+side,p+Vector((0,-.015,0)),(.023,.006,.023),iris)
  sphere('Pupil.'+side,p+Vector((0,-.020,0)),(.009,.004,.014),pupil)
 nose=front_hit(0,1.544);nose.y-=.017;sphere('Nose',nose,(.056,.034,.039),black)
 for s in (-1,1):sphere('Nostril',nose+Vector((s*.028,-.027,.003)),(.012,.008,.007),line)
 # A thin curve conforms to the reconstructed muzzle instead of painting a shadow.
 path=[]
 for x,z in [(-.10,1.444),(-.065,1.427),(0,1.431),(.065,1.427),(.10,1.444)]:
  p=front_hit(x,z);p.y-=.003;path.append(p)
 curve=bpy.data.curves.new('Closed_mouth_curve','CURVE');curve.dimensions='3D';curve.bevel_depth=.0018;curve.bevel_resolution=2;sp=curve.splines.new('BEZIER');sp.bezier_points.add(len(path)-1)
 for b,p in zip(sp.bezier_points,path):b.co=p;b.handle_left_type='AUTO';b.handle_right_type='AUTO'
 ob=bpy.data.objects.new('Closed_mouth',curve);bpy.context.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.convert(target='MESH');ob.data.materials.append(line);attach_detail(ob,rig,'head');details.append(ob)
 return details

def animate(rig):
 scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=FRAMES+1;scene.render.fps=FPS
 for pb in rig.pose.bones:pb.rotation_mode='QUATERNION'
 def turn(name,angle,axis=(1,0,0)):
  pb=rig.pose.bones[name];local=pb.bone.matrix_local.to_3x3().inverted()@Vector(axis);pb.rotation_quaternion=pb.rotation_quaternion@Quaternion(local.normalized(),angle)
 for f in range(1,FRAMES+2):
  scene.frame_set(f);t=2*math.pi*(f-1)/FRAMES
  for pb in rig.pose.bones:pb.rotation_quaternion=Quaternion();pb.scale=(1,1,1)
  # Pelvis and planted hindpaws stay fixed; breathing belongs to the upper torso.
  turn('spine',.010*math.sin(t));turn('chest',-.012*math.sin(t));rig.pose.bones['chest'].scale=(1+.010*math.sin(t),1+.006*math.sin(t),1+.010*math.sin(t))
  turn('neck',.018*math.sin(t));turn('head',.055*math.sin(t),(0,0,1));turn('head',.030*math.sin(t+.4),(0,1,0))
  for s,side in ((1,'L'),(-1,'R')):
   turn('shoulder.'+side,s*.014*math.sin(t),(0,0,1));turn('upper_foreleg.'+side,.025*math.sin(t+s*.35));turn('lower_foreleg.'+side,.040*math.sin(t+s*.35));turn('forepaw.'+side,.07*math.sin(t+s*.35))
   turn('ear.'+side,s*.018*math.sin(t-.3),(0,1,0))
  for i in range(1,5):turn('tail_'+str(i),.12*math.sin(2*t-i*.28),(0,0,1))
  for pb in rig.pose.bones:
   pb.keyframe_insert('rotation_quaternion',frame=f);pb.keyframe_insert('scale',frame=f)
 rig.animation_data.action.name='SitPretty'
 for fc in rig.animation_data.action.fcurves:
  for key in fc.keyframe_points:key.interpolation='LINEAR'
 scene.frame_set(1)

def deformation_checks(body,rig):
 scene=bpy.context.scene;co=[];edge_ratio=[];mins=[]
 rest=np.array([tuple(v.co) for v in body.data.vertices]);edges=np.array([tuple(e.vertices) for e in body.data.edges]);rest_len=np.linalg.norm(rest[edges[:,0]]-rest[edges[:,1]],axis=1)
 for f in (1,7,13,19,25,31,37,43,49):
  scene.frame_set(f);ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();a=np.empty(len(m.vertices)*3,dtype='float32');m.vertices.foreach_get('co',a);a=a.reshape(-1,3).copy();ev.to_mesh_clear();co.append(a);mins.append(float(a[:,2].min()))
  ratios=np.linalg.norm(a[edges[:,0]]-a[edges[:,1]],axis=1)/np.maximum(rest_len,1e-7);edge_ratio.append(float(np.quantile(ratios,.999)))
 assert np.isfinite(co).all(),'Non-finite animation';movement=np.linalg.norm(co[4]-co[0],axis=1)
 assert movement.max()>.008,'Animation is not deforming the actual skin'
 assert max(edge_ratio)<2.0,edge_ratio
 ground=(rest[:,2]<.065)&(rest[:,1]<.18);ground_motion=float(np.linalg.norm(co[4][ground]-co[0][ground],axis=1).max())
 seam=float(np.abs(co[0]-co[-1]).max());assert seam<1e-5,seam
 assert ground_motion<.04,ground_motion
 scene.frame_set(1)
 return {'max_vertex_motion':float(movement.max()),'skin_stretch_ratio_99_9_percent':max(edge_ratio),'planted_vertex_max_motion':ground_motion,'animation_loop_seam':seam,'ground_minimum_z_by_pose':mins,'poses_checked':len(co)}

def add_short_fur(body,rig,count=5000):
 """Sparse skin-bound short coat ribbons for silhouette microdetail.
 Decoration comes AFTER the point-cloud reconstruction, never substitutes for it.
 """
 rng=np.random.default_rng(71);polys=list(body.data.polygons);area=np.array([p.area for p in polys]);ids=rng.choice(len(polys),count,p=area/area.sum())
 V=[];F=[];weights=[];colors=[];attr=body.data.color_attributes['intrinsic_albedo']
 for fi in ids:
  p=polys[int(fi)];tri=list(p.vertices)[:3];r=rng.random(2)
  if r.sum()>1:r=1-r
  bary=[1-r.sum(),r[0],r[1]];pos=sum((body.data.vertices[i].co*w for i,w in zip(tri,bary)),Vector());normal=sum((body.data.vertices[i].normal*w for i,w in zip(tri,bary)),Vector()).normalized()
  if pos.z>1.39 and pos.y<-.25:continue
  tangent=Vector((0,0,-1));tangent-=normal*tangent.dot(normal)
  if tangent.length<1e-5:tangent=Vector((1,0,0))
  tangent.normalize();width=normal.cross(tangent).normalized()*.0007;length=float(rng.uniform(.004,.008));base=pos+normal*.0005;tip=base+normal*(length*.55)+tangent*(length*.8)
  k=len(V);V.extend([tuple(base-width),tuple(base+width),tuple(tip+width*.15),tuple(tip-width*.15)]);F.append((k,k+1,k+2,k+3))
  ww={}
  for i,w in zip(tri,bary):
   for g in body.data.vertices[i].groups:ww[body.vertex_groups[g.group].name]=ww.get(body.vertex_groups[g.group].name,0)+g.weight*w
  weights.append(ww);colors.append(sum((Vector(attr.data[i].color[:3])*w for i,w in zip(tri,bary)),Vector()))
 mesh=bpy.data.meshes.new('Short_coat_ribbons');mesh.from_pydata(V,[],F);mesh.update();ob=bpy.data.objects.new('Short_coat_detail',mesh);bpy.context.collection.objects.link(ob);ob.parent=rig
 groups={g.name:ob.vertex_groups.new(name=g.name) for g in body.vertex_groups}
 for fi,ww in enumerate(weights):
  for name,w in ww.items():groups[name].add(list(range(fi*4,fi*4+4)),w,'REPLACE')
 col=mesh.color_attributes.new(name='coat_color',type='FLOAT_COLOR',domain='POINT')
 for fi,c in enumerate(colors):
  for j in range(4):col.data[fi*4+j].color=(*c,1)
 mat=material('Short_fur_PBR',(.25,.15,.06),.88);node=mat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='coat_color';mat.node_tree.links.new(node.outputs[0],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color']);mesh.materials.append(mat)
 mod=ob.modifiers.new('Fur_skin','ARMATURE');mod.object=rig
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

def setup_studio():
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=False
 scene.render.resolution_x=576;scene.render.resolution_y=720;scene.render.resolution_percentage=100
 scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.14,.17,.21,1);scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.5
 bpy.ops.object.camera_add(location=(3.2,-5.8,2.5));cam=bpy.context.object;aim(cam,(0,-.02,.94));cam.data.type='ORTHO';cam.data.ortho_scale=2.5;scene.camera=cam
 for pos,power,size in [((2,-4,5),600,4),((-3,-2,3),400,3),((1,3,4),700,3)]:
  bpy.ops.object.light_add(type='AREA',location=pos);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;aim(light,(0,0,.9))
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025));floor=bpy.context.object;floor.name='Studio_floor';floor.data.materials.append(material('Neutral_studio',(.085,.11,.15),.8))
 return cam

def render_all(cam):
 scene=bpy.context.scene;folder=OUT/'frames';folder.mkdir(exist_ok=True)
 for f in range(1,FRAMES+1):
  scene.frame_set(f);scene.render.filepath=str(folder/f'sit_{f:03}.png');bpy.ops.render.render(write_still=True);print('RENDERED_SIT_FRAME',f,flush=True)
 pictures=[Image.open(folder/f'sit_{f:03}.png').convert('RGB') for f in range(1,FRAMES+1)]
 sample=Image.new('RGB',(576*4,720*2))
 for i,f in enumerate((0,6,12,18,24,30,36,42)):sample.paste(pictures[f],((i%4)*576,(i//4)*720))
 pal=sample.quantize(colors=192);gif=[p.quantize(palette=pal,dither=Image.Dither.NONE) for p in pictures]
 ds=[int((i+1)*1000/FPS/10)*10-int(i*1000/FPS/10)*10 for i in range(FRAMES)]
 gif[0].save(OUT/'Dog_SitPretty.gif',save_all=True,append_images=gif[1:],duration=ds,loop=0,disposal=2)
 pictures[0].save(OUT/'Dog_SitPretty_preview.png')
 # Additional inspection angles from the same actual 3D model.
 scene.frame_set(1);oldpos=cam.location.copy();oldrot=cam.rotation_euler.copy();oldscale=cam.data.ortho_scale
 views=[]
 for i,(name,pos) in enumerate([('front',(0,-6,.92)),('left',(-6,0,.92)),('back',(0,6,.92)),('right',(6,0,.92)),('front_high',(2,-4,4)),('back_high',(-2,4,4)),('front_low',(-2,-4,.65)),('back_low',(2,4,.65))]):
  cam.location=pos;aim(cam,(0,0,.92));cam.data.ortho_scale=2.45;scene.render.resolution_percentage=65;scene.render.filepath=str(OUT/f'08_view_{name}.png');bpy.ops.render.render(write_still=True);views.append(Image.open(scene.render.filepath).convert('RGB'))
 sheet=Image.new('RGB',(views[0].width*4,views[0].height*2));draw=ImageDraw.Draw(sheet)
 for i,im in enumerate(views):sheet.paste(im,((i%4)*im.width,(i//4)*im.height))
 sheet.save(OUT/'08_actual_model_eight_views.png');cam.location=oldpos;cam.rotation_euler=oldrot;cam.data.ortho_scale=oldscale;scene.render.resolution_percentage=100

def export_glb(name,objects,rig):
 for ob in bpy.context.selected_objects:ob.select_set(False)
 for ob in objects+[rig]:ob.select_set(True)
 bpy.context.view_layer.objects.active=objects[0]
 bpy.ops.export_scene.gltf(filepath=str(OUT/name),export_format='GLB',use_selection=True,export_animations=True,export_skins=True,export_force_sampling=True,export_materials='EXPORT')
 with (OUT/name).open('rb') as f:f.read(12);length,kind=struct.unpack('<II',f.read(8));g=json.loads(f.read(length))
 assert g.get('skins') and g.get('animations'),'Missing skin or action'
 return {'skins':len(g['skins']),'animations':[a.get('name') for a in g['animations']],
 'triangles':sum(g['accessors'][p['indices']]['count']//3 for m in g['meshes'] for p in m['primitives']),
 'textures':len(g.get('textures',[])),'materials':len(g.get('materials',[]))}

def export_lod(body,details,rig):
 scene=bpy.context.scene;scene.frame_set(1)
 lod=body.copy();lod.data=body.data.copy();bpy.context.collection.objects.link(lod);lod.name='Dog_LOD_game'
 for mod in list(lod.modifiers):lod.modifiers.remove(mod)
 for ob in bpy.context.selected_objects:ob.select_set(False)
 lod.select_set(True);bpy.context.view_layer.objects.active=lod
 dec=lod.modifiers.new('Game_LOD','DECIMATE');dec.ratio=.12;bpy.ops.object.modifier_apply(modifier=dec.name)
 skin=lod.modifiers.new('Canine_skin','ARMATURE');skin.object=rig
 result=export_glb('Dog_SitPretty_LOD.glb',[lod]+details,rig);result['body_faces']=len(lod.data.polygons)
 bpy.data.objects.remove(lod,do_unlink=True);return result

def main():
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 source=json.loads((OUT/'05_surface.json').read_text());mesh=bpy.data.meshes.new('Point_cloud_Poisson_surface');mesh.from_pydata(source['points'],[],source['triangles']);mesh.update()
 body=bpy.data.objects.new('Dog_100000_Body_Quads',mesh);bpy.context.collection.objects.link(body);bpy.context.view_layer.objects.active=body;body.select_set(True)
 rem=body.modifiers.new('Close_small_reconstruction_artifacts','REMESH');rem.mode='VOXEL';rem.voxel_size=.010;rem.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=rem.name)
 smooth=body.modifiers.new('Relax_surface','SMOOTH');smooth.factor=.45;smooth.iterations=2;bpy.ops.object.modifier_apply(modifier=smooth.name)
 print('RECONSTRUCTED_SURFACE_CHECK',validate(body),flush=True)
 bpy.ops.object.quadriflow_remesh(target_faces=5800,seed=4,use_preserve_sharp=False,use_preserve_boundary=False)
 print('QUAD_RETOPOLOGY_CHECK',validate(body,True),flush=True);exact_quads(body)
 rig,specs=rig_dog(body);report=validate(body,True);assert report['quad_faces']==100000,report
 setup_material(body);details=add_face_details(body,rig);fur=add_short_fur(body,rig)
 animate(rig);report.update(deformation_checks(body,rig));report['final_mesh_silhouette_iou']=mesh_silhouette_check(body)
 report.update({'body_quad_faces':100000,'bones':len(specs),'animation':'SitPretty','frames':FRAMES,'fps':FPS,'body_components':1,'details_separate_by_design':[ob.name for ob in details]+[fur.name],
 'material_maps':['Dog_BaseColor.png','Dog_Normal.png','Dog_Roughness.png'],'fur_detail_quads':len(fur.data.polygons),'albedo_method':'Diffuse palette classification and anatomical cream regions; source shading suppressed','uv_layers':len(body.data.uv_layers)})
 assert all(abs(sum(g.weight for g in v.groups)-1)<1e-4 for v in body.data.vertices),'Skin weights not normalized'
 assert min(report['final_mesh_silhouette_iou'].values())>.65,report
 (OUT/'validation.json').write_text(json.dumps(report,indent=2));print('FINAL_DOG_VALIDATION',report,flush=True)
 cam=setup_studio();render_all(cam)
 report['high_detail_glb']=export_glb('Dog_SitPretty_100000.glb',[body]+details+[fur],rig);report['game_lod_glb']=export_lod(body,details,rig)
 assert report['high_detail_glb']['textures']>=3,report
 (OUT/'validation.json').write_text(json.dumps(report,indent=2));body['validation']=json.dumps(report)
 scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=FRAMES;scene.frame_set(1)
 for ob in bpy.context.selected_objects:ob.select_set(False)
 body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=body
 for name in ('build_dog.py','reconstruct_dog.py','dog_inputs.b85','prepare_dog_inputs.py','calibration.json'):
  p=Path(__file__).with_name(name)
  if p.exists():shutil.copyfile(p,OUT/name)
 for name in ('pipeline.json','validation.json'):
  t=bpy.data.texts.new(name);t.write((OUT/name).read_text())
 bpy.ops.wm.save_as_mainfile(filepath=str((OUT/'Dog_SitPretty_100000.blend').resolve()))
 print('DOG_MUDELITEHAS_COMPLETE',report,flush=True)

if __name__=='__main__':main()

