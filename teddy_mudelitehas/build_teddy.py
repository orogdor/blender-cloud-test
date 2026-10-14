"""Blender stage: reconstructed surface -> 100000 quads -> skin -> run GIF.
Requires reconstruct_teddy.py to have produced output/teddy_mudelitehas.
"""
import bpy,bmesh,json,math,struct,shutil
from pathlib import Path
from mathutils import Vector,Quaternion
import numpy as np
from PIL import Image,ImageDraw,ImageFont
OUT=Path('output/teddy_mudelitehas');OUT.mkdir(parents=True,exist_ok=True)
TARGET_BASE=6250
FRAMES=32
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
 mesh=bpy.data.meshes.new('Teddy_exact_quad_topology')
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

def rig_teddy(ob):
 arm=bpy.data.armatures.new('Teddy_skeleton');rig=bpy.data.objects.new('Teddy_Rig',arm);bpy.context.collection.objects.link(rig)
 bpy.context.view_layer.objects.active=rig;rig.select_set(True);ob.select_set(False);bpy.ops.object.mode_set(mode='EDIT')
 specs={
 'root':((0,0,0),(0,0,.17),None),
 'hips':((0,0,.46),(0,0,.67),'root'),
 'spine':((0,0,.67),(0,0,.90),'hips'),
 'chest':((0,0,.90),(0,0,1.07),'spine'),
 'neck':((0,0,1.07),(0,0,1.21),'chest'),
 'head':((0,0,1.21),(0,0,1.67),'neck')}
 for sign,side in ((1,'L'),(-1,'R')):
  specs.update({
   'upper_arm.'+side:((sign*.29,0,1.02),(sign*.46,0,.86),'chest'),
   'forearm.'+side:((sign*.46,0,.86),(sign*.60,0,.73),'upper_arm.'+side),
   'paw.'+side:((sign*.60,0,.73),(sign*.67,0,.68),'forearm.'+side),
   'thigh.'+side:((sign*.16,0,.46),(sign*.17,0,.265),'hips'),
   'shin.'+side:((sign*.17,0,.265),(sign*.18,0,.095),'thigh.'+side),
   'foot.'+side:((sign*.18,0,.095),(sign*.18,-.21,.075),'shin.'+side)})
 for name,(head,tail,parent) in specs.items():
  bone=arm.edit_bones.new(name);bone.head=head;bone.tail=tail
  if parent:bone.parent=arm.edit_bones[parent]
  bone.use_deform=name!='root'
 bpy.ops.object.mode_set(mode='OBJECT')
 groups={name:ob.vertex_groups.new(name=name) for name in specs if name!='root'}
 for v in ob.data.vertices:
  p=v.co;x,y,z=p;side='L' if x>=0 else 'R'
  if z>1.18:names=['head','neck']
  elif abs(x)>.32 and .58<z<1.13:names=['upper_arm.'+side,'forearm.'+side,'paw.'+side,'chest']
  elif z<.48:names=['thigh.'+side,'shin.'+side,'foot.'+side,'hips']
  else:names=['hips','spine','chest','neck','head']
  distances=[bone_dist(p,*specs[name][:2]) for name in names]
  nearest=sorted(range(len(names)),key=lambda i:distances[i])[:3]
  weights=[1/(distances[i]+.045)**4 for i in nearest];total=sum(weights)
  for i,w in zip(nearest,weights):groups[names[i]].add([v.index],w/total,'REPLACE')
 ob.parent=rig
 # Densify the weighted mesh before adding the deform modifier. Subdivision
 # interpolates weights and yields exactly 6250*4*4 = 100000 true quad faces.
 bpy.context.view_layer.objects.active=ob;ob.select_set(True);rig.select_set(False)
 sub=ob.modifiers.new('100000_true_quads','SUBSURF');sub.levels=2;sub.render_levels=2
 bpy.ops.object.modifier_apply(modifier=sub.name)
 mod=ob.modifiers.new('Skeleton_deformation','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False
 rig.show_in_front=True
 return rig,specs

def color_teddy(ob):
 images=np.load(OUT/'aligned_images.npz');colors=[]
 xmin,xmax=images['x'][0],images['x'][-1];ymin,ymax=images['y'][0],images['y'][-1];zmin,zmax=images['z'][0],images['z'][-1]
 for v in ob.data.vertices:
  x,y,z=v.co;nx,ny,nz=v.normal
  if abs(ny)>=abs(nx)*.65:name='front' if ny<0 else 'back';u=(x-xmin)/(xmax-xmin)
  else:name='left' if nx>0 else 'right';u=(y-ymin)/(ymax-ymin)
  rgba=images[name+'_rgba'];h,w=rgba.shape[:2];iv=(zmax-z)/(zmax-zmin)*(h-1);iu=u*(w-1)
  iu=max(0,min(w-1,iu));iv=max(0,min(h-1,iv));i,j=int(iu),int(iv);ii,jj=min(i+1,w-1),min(j+1,h-1);tx,ty=iu-i,iv-j
  p=rgba[j,i]*(1-tx)*(1-ty)+rgba[j,ii]*tx*(1-ty)+rgba[jj,i]*(1-tx)*ty+rgba[jj,ii]*tx*ty
  rgb=p[:3]/255 if p[3]>100 else np.array([.60,.31,.13])
  # Image RGB is sRGB; color attributes store linear values.
  linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
  colors.extend([float(t) for t in linear]+[1.0])
 attr=ob.data.color_attributes.new(name='bear_color',type='FLOAT_COLOR',domain='POINT');attr.data.foreach_set('color',colors)
 mat=bpy.data.materials.new('Teddy_plush_image_colors');mat.use_nodes=True
 bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Roughness'].default_value=.86
 node=mat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='bear_color';mat.node_tree.links.new(node.outputs['Color'],bsdf.inputs['Base Color'])
 ob.data.materials.append(mat)
 for p in ob.data.polygons:p.use_smooth=True

def animate(rig):
 scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=FRAMES+1;scene.render.fps=FPS
 for bone in rig.pose.bones:bone.rotation_mode='QUATERNION'
 def turn(name,angle,axis=(1,0,0)):
  pb=rig.pose.bones[name];local_axis=pb.bone.matrix_local.to_3x3().inverted()@Vector(axis)
  pb.rotation_quaternion=Quaternion(local_axis.normalized(),angle)
 for frame in range(1,FRAMES+2):
  t=2*math.pi*(frame-1)/FRAMES
  root=rig.pose.bones['root'];root.location=(0,0,.055+.04*(1-math.cos(2*t)));root.keyframe_insert('location',frame=frame)
  turn('hips',.09);turn('spine',.08);turn('chest',.055*math.sin(t),(0,0,1));turn('neck',-.11);turn('head',.025*math.sin(t),(0,1,0))
  for sign,side in ((1,'L'),(-1,'R')):
   phase=t+(0 if sign==1 else math.pi)
   turn('thigh.'+side,.70*math.sin(phase))
   turn('shin.'+side,.12+.88*max(0,-math.sin(phase)))
   turn('foot.'+side,-.18-.24*math.sin(phase))
   turn('upper_arm.'+side,-.55*math.sin(phase))
   turn('forearm.'+side,.20+.30*max(0,math.sin(phase)))
   turn('paw.'+side,.06*math.sin(phase))
  for pb in rig.pose.bones:pb.keyframe_insert('rotation_quaternion',frame=frame)
 rig.animation_data.action.name='Run'
 for curve in rig.animation_data.action.fcurves:
  for key in curve.keyframe_points:key.interpolation='LINEAR'
 scene.frame_set(1)

def evaluate_test(ob):
 scene=bpy.context.scene;values=[]
 for f in (1,9):
  scene.frame_set(f);evaluated=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
  coords=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',coords);values.append(coords.reshape((-1,3)).copy());evaluated.to_mesh_clear()
 moved=np.linalg.norm(values[1]-values[0],axis=1)
 scene.frame_set(1)
 assert np.isfinite(values).all();assert moved.max()>.15,float(moved.max())
 return {'max_vertex_motion_between_frames':round(float(moved.max()),6),'animated_vertices_over_1cm':int((moved>.01).sum())}

def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()

def render_animation(ob,rig):
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=False
 scene.render.resolution_x=640;scene.render.resolution_y=720;scene.render.resolution_percentage=100
 scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.17,.20,.25,1)
 scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.7
 bpy.ops.object.camera_add(location=(3.0,-5.6,2.5));camera=bpy.context.object;aim(camera,(0,0,.96));camera.data.type='ORTHO';camera.data.ortho_scale=2.6;scene.camera=camera
 for pos,power,size in [((2,-4,5),500,4),((-3,-1,3),350,3),((1,3,4),450,3)]:
  bpy.ops.object.light_add(type='AREA',location=pos);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;aim(light,(0,0,.9))
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.015));floor=bpy.context.object;floor.name='Studio_floor'
 mat=bpy.data.materials.new('Studio_gray');mat.diffuse_color=(.12,.15,.20,1);mat.use_nodes=True;mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.12,.15,.20,1);mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.85;floor.data.materials.append(mat)
 frames_dir=OUT/'frames';frames_dir.mkdir(exist_ok=True)
 for frame in range(1,FRAMES+1):
  scene.frame_set(frame);scene.render.filepath=str(frames_dir/f'run_{frame:03}.png');bpy.ops.render.render(write_still=True)
  print('RENDERED_RUN_FRAME',frame,flush=True)
 pictures=[Image.open(frames_dir/f'run_{f:03}.png').convert('RGB') for f in range(1,FRAMES+1)]
 # Shared palette prevents per-frame palette flicker in the inline GIF.
 sample=Image.new('RGB',(640*4,720*2))
 for i,f in enumerate((0,4,8,12,16,20,24,28)):sample.paste(pictures[f],((i%4)*640,(i//4)*720))
 palette=sample.quantize(colors=192,method=Image.Quantize.MEDIANCUT)
 gif=[p.quantize(palette=palette,dither=Image.Dither.NONE) for p in pictures]
 gif[0].save(OUT/'Teddy_Run_100000.gif',save_all=True,append_images=gif[1:],duration=round(1000/FPS),loop=0,optimize=False,disposal=2)
 pictures[4].save(OUT/'Teddy_Run_preview.png')
 scene.frame_set(1)

def main():
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 source=json.loads((OUT/'05_surface.json').read_text());mesh=bpy.data.meshes.new('Poisson_reconstruction')
 mesh.from_pydata(source['points'],[],source['triangles']);mesh.update();ob=bpy.data.objects.new('Teddy_100000_Quads',mesh);bpy.context.collection.objects.link(ob)
 bpy.context.view_layer.objects.active=ob;ob.select_set(True)
 # Close small Poisson artifacts before retopology, retaining the image-derived shape.
 rem=ob.modifiers.new('Close_reconstructed_surface','REMESH');rem.mode='VOXEL';rem.voxel_size=.015;rem.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=rem.name)
 smooth=ob.modifiers.new('Relax_reconstruction','SMOOTH');smooth.factor=.55;smooth.iterations=3;bpy.ops.object.modifier_apply(modifier=smooth.name)
 print('RECONSTRUCTION_CHECK',validate(ob),flush=True)
 bpy.ops.object.quadriflow_remesh(target_faces=5900,seed=0,use_preserve_sharp=False,use_preserve_boundary=False)
 print('QUADRIFLOW_CHECK',validate(ob,True),flush=True)
 base_report=exact_quads(ob);print('EXACT_6250_QUADS',base_report,flush=True)
 rig,specs=rig_teddy(ob);report=validate(ob,True);assert report['quad_faces']==100000,report
 color_teddy(ob);animate(rig);report.update(evaluate_test(ob))
 report['bones']=len(rig.data.bones);report['animation']='Run';report['frames']=FRAMES;report['fps']=FPS
 report['base_quad_faces']=6250;report['subdivision_levels_applied']=2
 report['face_budget_method']='6250 connected base quads, two applied Catmull-Clark subdivisions: 6250*16=100000'
 assert all(abs(sum(g.weight for g in v.groups)-1)<1e-4 for v in ob.data.vertices),'Unnormalized skin weights'
 assert max(len(v.groups) for v in ob.data.vertices)<=len(specs),'Bad skin groups'
 (OUT/'validation.json').write_text(json.dumps(report,indent=2));ob['validation']=json.dumps(report)
 print('FINAL_100000_QUAD_CHECK',report,flush=True)
 render_animation(ob,rig)
 for obj in bpy.context.selected_objects:obj.select_set(False)
 ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
 bpy.ops.export_scene.gltf(filepath=str(OUT/'Teddy_Run_100000.glb'),export_format='GLB',use_selection=True,export_animations=True,export_skins=True,export_force_sampling=True)
 with (OUT/'Teddy_Run_100000.glb').open('rb') as f:
  f.read(12);length,kind=struct.unpack('<II',f.read(8));gltf=json.loads(f.read(length))
 assert gltf.get('skins') and gltf.get('animations'),'GLB missing skin or animation'
 report['glb_skins']=len(gltf['skins']);report['glb_animations']=[a.get('name') for a in gltf['animations']]
 report['glb_triangle_count']=sum(gltf['accessors'][p['indices']]['count']//3 for m in gltf['meshes'] for p in m['primitives'])
 assert report['glb_triangle_count']==200000,report
 (OUT/'validation.json').write_text(json.dumps(report,indent=2))
 bpy.context.scene.frame_end=FRAMES
 for name in ('build_teddy.py','reconstruct_teddy.py','teddy_inputs.b85'):
  p=Path(__file__).with_name(name);shutil.copyfile(p,OUT/name)
 for name in ('pipeline.json','validation.json'):
  t=bpy.data.texts.new(name);t.write((OUT/name).read_text())
 bpy.ops.wm.save_as_mainfile(filepath=str((OUT/'Teddy_Run_100000.blend').resolve()))
 print('TEDDY_PIPELINE_COMPLETE',report,flush=True)

if __name__=='__main__':main()
