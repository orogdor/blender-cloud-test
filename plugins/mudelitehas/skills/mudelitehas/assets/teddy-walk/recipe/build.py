"""T-pose teddy from saved point cloud surface; cached mesh, biped gait, PBR, GLB."""
import sys,json,time,math,hashlib,struct,importlib.util,inspect,os
from pathlib import Path
BASE=Path(__file__).resolve().parent.parent;OUT=BASE/'output';CACHE=BASE/'cache';ROOT=BASE.parents[1];sys.path.insert(0,str(ROOT/'runtime/py311'))
if os.environ.get('MUDELITEHAS_PYTHONPATH'):sys.path.insert(0,os.environ['MUDELITEHAS_PYTHONPATH'])
import bpy,numpy as np
from mathutils import Vector,Matrix
from PIL import Image,ImageDraw
spec=importlib.util.spec_from_file_location('utilities',BASE/'recipe/mesh_utilities.py');U=importlib.util.module_from_spec(spec);spec.loader.exec_module(U);U.OUT=OUT;U.TARGET_BASE=2500
MODE=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'probe';TIMES={};START=time.perf_counter();FPS=24;FRAMES=49

def stage(name,fn):
 t=time.perf_counter();r=fn();TIMES[name]=time.perf_counter()-t;print('STAGE',name,round(TIMES[name],3),flush=True);return r
def select(o):
 for a in bpy.context.selected_objects:a.select_set(False)
 o.select_set(True);bpy.context.view_layer.objects.active=o
def evaluated(body):
 ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();a=np.array([v.co[:] for v in me.vertices]);ev.to_mesh_clear();return a

def mesh_stage():
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);data=json.loads((OUT/'05_surface.json').read_text());me=bpy.data.meshes.new('Reconstructed_teddy_surface');me.from_pydata(data['points'],[],data['triangles']);me.update();body=bpy.data.objects.new('Teddy_Body_10000_Quads',me);bpy.context.collection.objects.link(body);select(body)
 rem=body.modifiers.new('Close_Poisson','REMESH');rem.mode='VOXEL';rem.voxel_size=.008;rem.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=rem.name)
 sm=body.modifiers.new('Relax','SMOOTH');sm.factor=.45;sm.iterations=2;bpy.ops.object.modifier_apply(modifier=sm.name);
 for target in [2200,1800,1400]:
  bpy.ops.object.quadriflow_remesh(target_faces=target,seed=8,use_preserve_sharp=False,use_preserve_boundary=False)
  if len(body.data.polygons)<=2500:break
 U.exact_quads(body)
 sm=body.modifiers.new('Even_quads','SMOOTH');sm.factor=.18;sm.iterations=2;bpy.ops.object.modifier_apply(modifier=sm.name)
 sub=body.modifiers.new('Exactly_10000_quads','SUBSURF');sub.levels=1;sub.render_levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
 offset=max(0,.001-min(v.co.z for v in body.data.vertices))
 for v in body.data.vertices:v.co.z+=offset
 for p in body.data.polygons:p.use_smooth=True
 assert U.validate(body,True)['quad_faces']==10000
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1519,island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT');return body

def create_rig(body):
 arm=bpy.data.armatures.new('Teddy_biped_skeleton');rig=bpy.data.objects.new('Teddy_Rig',arm);bpy.context.collection.objects.link(rig);select(rig);bpy.ops.object.mode_set(mode='EDIT')
 specs={'root':((0,0,0),(0,0,.12),None),'pelvis':((0,0,.510),(0,0,.720),'root'),'spine':((0,0,.720),(0,0,.920),'pelvis'),'chest':((0,0,.920),(0,0,1.065),'spine'),'neck':((0,0,1.065),(0,0,1.150),'chest'),'head':((0,0,1.150),(0,0,1.480),'neck'),'tail':((0,.18,.567),(0,.27,.567),'pelvis')}
 for sign,side in [(1,'L'),(-1,'R')]:
  specs.update({'shoulder.'+side:((sign*.20,0,.979),(sign*.345,0,.979),'chest'),'upper_arm.'+side:((sign*.345,0,.979),(sign*.520,0,.979),'shoulder.'+side),'forearm.'+side:((sign*.520,0,.979),(sign*.690,0,.979),'upper_arm.'+side),'hand.'+side:((sign*.690,0,.979),(sign*.790,0,.979),'forearm.'+side),'thigh.'+side:((sign*.185,0,.490),(sign*.185,0,.310),'pelvis'),'shin.'+side:((sign*.185,0,.310),(sign*.185,0,.160),'thigh.'+side),'foot.'+side:((sign*.185,0,.160),(sign*.185,-.16,.060),'shin.'+side),'ear.'+side:((sign*.25,0,1.510),(sign*.31,0,1.610),'head')})
 for n,(a,b,parent) in specs.items():
  bone=arm.edit_bones.new(n);bone.head=a;bone.tail=b;bone.use_deform=n!='root'
  if parent:bone.parent=arm.edit_bones[parent]
 bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True;rig['specs']=json.dumps(specs);body.parent=rig;return rig,specs

def skin(body,rig,specs):
 body.vertex_groups.clear();co=np.array([v.co[:] for v in body.data.vertices]);names=[n for n in specs if n!='root'];groups=[body.vertex_groups.new(name=n) for n in names];radii={'pelvis':.20,'spine':.205,'chest':.19,'neck':.12,'head':.255,'tail':.07,'shoulder':.105,'upper_arm':.105,'forearm':.105,'hand':.105,'thigh':.115,'shin':.118,'foot':.14,'ear':.09};aff=[]
 for n in names:
  a,b=[np.array(p) for p in specs[n][:2]];ab=b-a;t=np.clip(((co-a)@ab)/(ab@ab),0,1);d=np.sum((co-a-t[:,None]*ab)**2,axis=1);r=radii[n.split('.')[0]];v=np.exp(-2.0*d/(r*r))
  if n.endswith('.L'):v*=1/(1+np.exp(-65*co[:,0]))
  if n.endswith('.R'):v*=1/(1+np.exp(65*co[:,0]))
  aff.append(v)
 w=np.array(aff).T;w/=np.maximum(w.sum(1)[:,None],1e-12);lookup={n:i for i,n in enumerate(names)};fixed=co[:,2]<.175
 for i in np.flatnonzero(co[:,2]<.24):
  pin=np.clip((.24-co[i,2])/.065,0,1);j=lookup['foot.L' if co[i,0]>0 else 'foot.R'];w[i]*=1-pin;w[i,j]+=pin
 e=np.array([ed.vertices[:] for ed in body.data.edges]);degree=np.bincount(e.ravel(),minlength=len(w))
 for _ in range(8):
  n=np.zeros_like(w);np.add.at(n,e[:,0],w[e[:,1]]);np.add.at(n,e[:,1],w[e[:,0]]);n=.72*w+.28*n/np.maximum(degree[:,None],1);n[fixed]=w[fixed];w=n
 order=np.argsort(w,axis=1)[:,:-4];np.put_along_axis(w,order,0,axis=1);w/=w.sum(1)[:,None]
 for i,row in enumerate(w):
  for j in np.flatnonzero(row>1e-9):groups[int(j)].add([i],float(row[j]),'REPLACE')
 mod=body.modifiers.new('Teddy_linear_skin','ARMATURE');mod.object=rig;return rig

def set_pose(rig,specs,phase):
 bob=.008*(1-math.cos(phase*2));P=Vector((.012*math.sin(phase),0,.475+bob));R=Matrix.Rotation(.035*math.sin(phase),3,'Z');targets={}
 def put(n,a,b):targets[n]=(Vector(a),Vector(b))
 put('root',*specs['root'][:2]);a=P.copy()
 for n in ['pelvis','spine','chest','neck','head']:
  rotation=R
  if n in ['chest','neck','head']:rotation=Matrix.Rotation(-.025*math.sin(phase),3,'Z')@R
  vec=Vector(specs[n][1])-Vector(specs[n][0]);b=a+rotation@vec;put(n,a,b);a=b
 for sign,side in [(1,'L'),(-1,'R')]:
  q=(phase+(0 if side=='L' else math.pi))%(2*math.pi);swing=math.cos(phase+(0 if side=='L' else math.pi))*.32
  n='shoulder.'+side;a=targets['chest'][0]+R@(Vector(specs[n][0])-Vector(specs['chest'][0]));b=a+R@(Vector(specs[n][1])-Vector(specs[n][0]));put(n,a,b);a=b
  for part,bend in [('upper_arm',0),('forearm',.10),('hand',.05)]:
   n=part+'.'+side;rr=Matrix.Rotation(swing+bend,3,'X')@Matrix.Rotation(sign*math.radians(73),3,'Y');b=a+rr@(Vector(specs[n][1])-Vector(specs[n][0]));put(n,a,b);a=b
  hip=P+R@(Vector(specs['thigh.'+side][0])-Vector(specs['pelvis'][0]));lift=.055*max(0,math.sin(q-math.pi));ankle=Vector((sign*.185,-.12*math.cos(q),.160+lift));ex=(ankle-hip).normalized();d=(ankle-hip).length;l1=.180;l2=.150;along=(l1*l1-l2*l2+d*d)/(2*d);height=math.sqrt(max(0,l1*l1-along*along));forward=Vector((0,ex.z,-ex.y)).normalized();knee=hip+ex*along+forward*height;put('thigh.'+side,hip,knee);put('shin.'+side,knee,ankle)
  vec=Vector(specs['foot.'+side][1])-Vector(specs['foot.'+side][0]);pitch=math.radians(-10)*max(0,math.sin(q-math.pi));toe=ankle+Matrix.Rotation(pitch,3,'X')@vec;put('foot.'+side,ankle,toe)
  n='ear.'+side;hr=Matrix.Rotation(-.025*math.sin(phase),3,'Z')@R;a=targets['head'][0]+hr@(Vector(specs[n][0])-Vector(specs['head'][0]));b=a+hr@(Vector(specs[n][1])-Vector(specs[n][0]));put(n,a,b)
 a=P+R@(Vector(specs['tail'][0])-Vector(specs['pelvis'][0]));put('tail',a,a+R@(Vector(specs['tail'][1])-Vector(specs['tail'][0])))
 for n,(a,b) in targets.items():
  pb=rig.pose.bones[n];v=Vector(specs[n][1])-Vector(specs[n][0]);m=(v.rotation_difference(b-a).to_matrix()@pb.bone.matrix_local.to_3x3()).to_4x4();m.translation=a;pb.matrix=m;bpy.context.view_layer.update()
 return targets

def bind_correction(body,rig):
 bpy.context.scene.frame_set(0)
 for pb in rig.pose.bones:pb.matrix_basis.identity()
 select(body);mod=body.modifiers.new('JointCorrection','CORRECTIVE_SMOOTH');mod.factor=.70;mod.iterations=8;mod.smooth_type='LENGTH_WEIGHTED';mod.rest_source='BIND';group=body.vertex_groups.new(name='CorrectionMask')
 for v in body.data.vertices:
  x,y,z=v.co;weight=min(1,max(0,(z-.23)/.10))*min(1,max(0,(1.15-z)/.12));group.add([v.index],weight,'REPLACE')
 mod.vertex_group=group.name;bpy.ops.object.correctivesmooth_bind(modifier=mod.name)

def animate(rig,specs):
 rig.animation_data_clear();scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=FRAMES;scene.render.fps=FPS
 for pb in rig.pose.bones:pb.rotation_mode='QUATERNION';pb.matrix_basis.identity();pb.keyframe_insert('location',frame=0);pb.keyframe_insert('rotation_quaternion',frame=0);pb.keyframe_insert('scale',frame=0)
 for f in range(1,FRAMES+1):
  scene.frame_set(f);set_pose(rig,specs,2*math.pi*(f-1)/(FRAMES-1))
  for pb in rig.pose.bones:pb.keyframe_insert('location',frame=f);pb.keyframe_insert('rotation_quaternion',frame=f);pb.keyframe_insert('scale',frame=f)
 rig.animation_data.action.name='Walk_Loop'
 for fc in rig.animation_data.action.fcurves:
  for k in fc.keyframe_points:k.interpolation='LINEAR'
 scene.frame_set(1)

def check(body,rig):
 rest=np.array([v.co[:] for v in body.data.vertices]);edges=np.array([e.vertices[:] for e in body.data.edges]);length=np.linalg.norm(rest[edges[:,0]]-rest[edges[:,1]],axis=1);poses=[];ratios=[];absolute=[];bone=[];contact=[]
 frames=list(range(1,50,4))
 for f in frames:
  bpy.context.scene.frame_set(f);p=evaluated(body);poses.append(p);le=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1);valid=length>.003;ratios.append(float(np.quantile(le[valid]/length[valid],.999)));absolute.append(float(abs(le-length).max()));bone.extend(abs((b.tail-b.head).length-b.bone.length) for b in rig.pose.bones)
  phase=2*math.pi*(f-1)/48
  for sign,side in [(1,'L'),(-1,'R')]:
   q=(phase+(0 if sign==1 else math.pi))%(2*math.pi)
   if q<=math.pi+1e-6:
    ids=(rest[:,2]<.175)&(rest[:,0]*sign>0);contact.append(float(p[ids,2].min()))
 a=np.array(poses);result={'frames_checked':frames,'finite':bool(np.isfinite(a).all()),'loop_seam_m':float(abs(a[-1]-a[0]).max()),'max_skin_motion_m':float(np.linalg.norm(a-a[0],axis=2).max()),'minimum_z_m':float(a[:,:,2].min()),'stance_sole_min_z_range_m':[min(contact),max(contact)],'skin_stretch_p999_edges_over_3mm':max(ratios),'max_edge_length_change_m':max(absolute),'bone_length_error_m':float(max(bone)),'root_motion':'in-place gait; stance feet move backward relative to stationary root','collision_check':'multi-view visual review, not exhaustive collision proof'}
 np.savez_compressed(OUT/'deformation_samples.npz',rest=rest,poses=a,frames=frames);(OUT/'deformation_validation.json').write_text(json.dumps(result,indent=2));print('DEFORMATION',result,flush=True);return result

def studio(quality=False):
 for o in list(bpy.data.objects):
  if o.type in ['CAMERA','LIGHT'] or o.name=='Preview_floor':bpy.data.objects.remove(o,do_unlink=True)
 sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=20 if quality else 8;sc.cycles.use_denoising=True;sc.render.resolution_x=480 if quality else 360;sc.render.resolution_y=560 if quality else 420;sc.render.resolution_percentage=100;sc.view_settings.view_transform='AgX';sc.world.use_nodes=True;sc.world.node_tree.nodes.get('Background').inputs[0].default_value=(.28,.31,.36,1);sc.world.node_tree.nodes.get('Background').inputs[1].default_value=.45
 bpy.ops.object.camera_add(location=(2.8,-5,2.0));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=1.95;U.aim(cam,(0,0,.82));sc.camera=cam
 for pos,power,size in [((2,-3,4),400,3),((-3,-1,3),230,3),((1,3,3),450,3)]:
  bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;U.aim(o,(0,0,.8))
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0));floor=bpy.context.object;floor.name='Preview_floor';floor.data.materials.append(U.material('Studio_gray',(.13,.16,.20),.85));return cam

def controls(cam):
 if os.environ.get('MUDELITEHAS_PREVIEW')=='none':return
 if os.environ.get('MUDELITEHAS_PREVIEW')=='quick':
  bpy.context.scene.render.resolution_x=256;bpy.context.scene.render.resolution_y=300;bpy.context.scene.cycles.samples=4
 sc=bpy.context.scene;images=[]
 for name,pos,frame in [('Rest',(2.8,-5,2),0),('Left_contact',(2.8,-5,2),1),('Passing',(2.8,-5,2),13),('Right_contact',(2.8,-5,2),25),('Side',(-5,0,1.1),13),('Back',(0,5,1.1),25)]:
  sc.frame_set(frame);cam.location=pos;U.aim(cam,(0,0,.82));cam.data.ortho_scale=2.05 if frame==0 else 1.95;sc.render.filepath=str(OUT/('control_'+name+'.png'));bpy.ops.render.render(write_still=True);im=Image.open(sc.render.filepath).convert('RGB');ImageDraw.Draw(im).text((10,10),name,fill='white');images.append(im)
 sheet=Image.new('RGB',(images[0].width*3,images[0].height*2))
 for i,im in enumerate(images):sheet.paste(im,((i%3)*im.width,(i//3)*im.height))
 sheet.save(OUT/'Control_views.jpg',quality=92)

if MODE=='probe':
 cache=CACHE/'Neutral_10000.blend';finger=hashlib.sha256((OUT/'05_surface.json').read_bytes()+b'area_balanced_teddy_v1'+str(bpy.app.version).encode()).hexdigest()
 if cache.exists() and (CACHE/'mesh_fingerprint.sha256').read_text()==finger:
  bpy.ops.wm.open_mainfile(filepath=str(cache));body=bpy.data.objects['Teddy_Body_10000_Quads'];rig=bpy.data.objects['Teddy_Rig'];specs=json.loads(rig['specs'])
 else:
  body=stage('mesh_10000',mesh_stage);rig,specs=stage('skeleton',lambda:create_rig(body));bpy.ops.wm.save_as_mainfile(filepath=str(cache));(CACHE/'mesh_fingerprint.sha256').write_text(finger)
 stage('continuous_skin',lambda:skin(body,rig,specs));stage('bind_joint_correction',lambda:bind_correction(body,rig));stage('walk_animation',lambda:animate(rig,specs));result=stage('deformation_gate',lambda:check(body,rig));result['topology']=U.validate(body,True)
 body.data.materials.clear();body.data.materials.append(U.material('Clay',(.38,.35,.30),.8));bpy.ops.wm.save_as_mainfile(filepath=str(CACHE/'Walk_review.blend'));cam=studio();stage('review_renders',lambda:controls(cam));(OUT/'probe_validation.json').write_text(json.dumps(result,indent=2));(OUT/'probe_timings.json').write_text(json.dumps(TIMES,indent=2));print('PROBE_COMPLETE',time.perf_counter()-START,flush=True)

def bake_joint_shapes(body,rig):
 mod=body.modifiers.get('JointCorrection');base=np.array([v.co[:] for v in body.data.vertices]);samples=list(range(1,49,6));targets=[];deltas=[]
 for frame in samples:
  bpy.context.scene.frame_set(frame);mod.show_viewport=True;target=evaluated(body);mod.show_viewport=False;linear=evaluated(body);matrices={b.name:np.array(b.matrix@b.bone.matrix_local.inverted())[:3,:3] for b in rig.pose.bones};M=np.zeros((len(base),3,3))
  for v in body.data.vertices:
   for g in v.groups:
    name=body.vertex_groups[g.group].name
    if name in matrices:M[v.index]+=g.weight*matrices[name]
  a,s,v=np.linalg.svd(M);inv=(v.transpose(0,2,1)*(1/np.maximum(s,.03))[:,None,:])@a.transpose(0,2,1);deltas.append(np.einsum('nij,nj->ni',inv,target-linear));targets.append(target)
 body.modifiers.remove(mod);body.shape_key_add(name='Basis');keys=[]
 for frame,delta in zip(samples,deltas):
  key=body.shape_key_add(name=f'WalkJoint_{frame:02}');key.data.foreach_set('co',(base+delta).astype('float32').ravel());keys.append(key)
 for key in keys:key.value=0;key.keyframe_insert('value',frame=0)
 for frame in range(1,50):
  u=((frame-1)%48)/6;i=int(u);t=u-i
  for j,key in enumerate(keys):key.value=(1-t if j==i else t if j==(i+1)%8 else 0);key.keyframe_insert('value',frame=frame)
 for fc in body.data.shape_keys.animation_data.action.fcurves:
  for k in fc.keyframe_points:k.interpolation='LINEAR'
 errors=[]
 for f,target in zip(samples,targets):bpy.context.scene.frame_set(f);errors.append(float(np.linalg.norm(evaluated(body)-target,axis=1).max()))
 assert max(errors)<.003,errors
 return {'shape_keys':[k.name for k in keys],'corrective_reference_errors_m':errors,'method':'Bound corrective smooth converted to synchronized exportable morph targets'}

def coat(body):
 m=U.material('Honey_plush_PBR',(.42,.20,.065),.85);nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes.get('Principled BSDF');output=nodes.get('Material Output')
 if 'Sheen Weight' in bs.inputs:bs.inputs['Sheen Weight'].default_value=.40
 geo=nodes.new('ShaderNodeNewGeometry');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(geo.outputs['Position'],sep.inputs[0])
 def mathn(op,a,b=None):
  n=nodes.new('ShaderNodeMath');n.operation=op
  for i,v in enumerate([a,b]):
   if v is None:continue
   if isinstance(v,(int,float)):n.inputs[i].default_value=v
   else:links.new(v,n.inputs[i])
  return n.outputs[0]
 def ellipse(cx,cz,rx,rz):
  x=mathn('DIVIDE',mathn('SUBTRACT',sep.outputs['X'],cx),rx);z=mathn('DIVIDE',mathn('SUBTRACT',sep.outputs['Z'],cz),rz);return mathn('ADD',mathn('MULTIPLY',x,x),mathn('MULTIPLY',z,z))
 front=mathn('MINIMUM',mathn('MAXIMUM',mathn('MULTIPLY',mathn('SUBTRACT',-.12,sep.outputs['Y']),25),0),1);bellydist=ellipse(0,.735,.208,.279);muzzledist=ellipse(0,1.210,.172,.114)
 belly=mathn('MINIMUM',mathn('MAXIMUM',mathn('MULTIPLY',mathn('SUBTRACT',1,bellydist),12),0),1);muzzle=mathn('MINIMUM',mathn('MAXIMUM',mathn('MULTIPLY',mathn('SUBTRACT',1,muzzledist),12),0),1);cream=mathn('MULTIPLY',mathn('MAXIMUM',belly,muzzle),front)
 noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=90;noise.inputs['Detail'].default_value=4;noise.inputs['Roughness'].default_value=.7;links.new(geo.outputs['Position'],noise.inputs['Vector'])
 golden=nodes.new('ShaderNodeMixRGB');golden.inputs[1].default_value=(.32,.126,.033,1);golden.inputs[2].default_value=(.46,.222,.071,1);links.new(noise.outputs['Fac'],golden.inputs[0]);mix=nodes.new('ShaderNodeMixRGB');links.new(cream,mix.inputs[0]);links.new(golden.outputs[0],mix.inputs[1]);mix.inputs[2].default_value=(.69,.55,.36,1)
 # A narrow seam follows the tummy patch; height detail moves with the skin.
 seam=mathn('MULTIPLY',mathn('LESS_THAN',mathn('ABSOLUTE',mathn('SUBTRACT',bellydist,1)),.026),front);seamcolor=nodes.new('ShaderNodeMixRGB');links.new(mathn('MULTIPLY',seam,.40),seamcolor.inputs[0]);links.new(mix.outputs[0],seamcolor.inputs[1]);seamcolor.inputs[2].default_value=(.19,.09,.027,1);links.new(seamcolor.outputs[0],bs.inputs['Base Color'])
 fiber=nodes.new('ShaderNodeTexNoise');fiber.inputs['Scale'].default_value=1100;fiber.inputs['Detail'].default_value=2;stretch=nodes.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY';stretch.inputs[1].default_value=(1,1,.22);links.new(geo.outputs['Position'],stretch.inputs[0]);links.new(stretch.outputs[0],fiber.inputs['Vector']);bum=nodes.new('ShaderNodeBump');bum.inputs['Strength'].default_value=.32;bum.inputs['Distance'].default_value=.0009;links.new(fiber.outputs['Fac'],bum.inputs['Height']);links.new(bum.outputs[0],bs.inputs['Normal']);seambump=nodes.new('ShaderNodeBump');seambump.inputs['Strength'].default_value=.18;seambump.inputs['Distance'].default_value=.0006;seambump.invert=True;links.new(seam,seambump.inputs['Height']);links.new(bum.outputs[0],seambump.inputs['Normal']);links.new(seambump.outputs[0],bs.inputs['Normal'])
 body.data.materials.clear();body.data.materials.append(m);select(body);skin=body.modifiers.get('Teddy_linear_skin');skin.show_viewport=False;skin.show_render=False;bpy.context.scene.frame_set(0);sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=1;sc.cycles.use_denoising=False;td=OUT/'textures';td.mkdir(exist_ok=True);target=nodes.new('ShaderNodeTexImage')
 def bake(name,kind):
  im=bpy.data.images.new(name,width=2048,height=2048,alpha=False)
  if kind=='NORMAL':im.colorspace_settings.name='Non-Color'
  target.image=im;nodes.active=target;bpy.ops.object.bake(type=kind,margin=12,use_clear=True);im.filepath_raw=str(td/(name+'.png'));im.file_format='PNG';im.save();im.pack();return im
 emit=nodes.new('ShaderNodeEmission');links.new(seamcolor.outputs[0],emit.inputs['Color']);links.new(emit.outputs[0],output.inputs['Surface']);base=bake('Teddy_BaseColor','EMIT');links.new(bs.outputs[0],output.inputs['Surface']);normal=bake('Teddy_Normal','NORMAL');tex=nodes.new('ShaderNodeTexImage');tex.image=base;links.new(tex.outputs[0],bs.inputs['Base Color']);nt=nodes.new('ShaderNodeTexImage');nt.image=normal;norm=nodes.new('ShaderNodeNormalMap');links.new(nt.outputs['Color'],norm.inputs[0]);links.new(norm.outputs[0],bs.inputs['Normal'])
 rng=np.random.default_rng(39);rough=np.clip(.85+rng.normal(0,.017,(1024,1024)),.78,.92);Image.fromarray((rough*255).astype('uint8')).save(td/'Teddy_Roughness.png');ri=bpy.data.images.load(str(td/'Teddy_Roughness.png'));ri.colorspace_settings.name='Non-Color';ri.pack();rt=nodes.new('ShaderNodeTexImage');rt.image=ri;links.new(rt.outputs['Color'],bs.inputs['Roughness']);skin.show_viewport=True;skin.show_render=True

def face(body,rig):
 details=[];eye=U.material('Dark_safety_eyes',(.017,.008,.003),.10);nosemat=U.material('Black_fabric_nose',(.014,.010,.007),.43);thread=U.material('Dark_sewn_smile',(.045,.020,.006),.88);earmat=U.material('Cream_inner_ear',(.57,.38,.20),.88)
 def hit(x,z):
  ok,p,n,i=body.ray_cast(Vector((x,-2,z)),Vector((0,1,0)));return p if ok else Vector((x,-.25,z))
 def sphere(name,pos,scale,material,bone='head'):
  bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,location=pos);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=True,rotation=False,scale=True);o.data.materials.append(material);U.attach_detail(o,rig,bone);details.append(o);return o
 for sign,side in [(1,'L'),(-1,'R')]:
  p=hit(sign*.118,1.337);p.y-=.007;sphere('Safety_eye_'+side,p,(.029,.016,.031),eye)
  sphere('Inner_ear_'+side,Vector((sign*.278,-.062,1.555)),(.064,.016,.076),earmat,'ear.'+side)
 p=hit(0,1.236);p.y-=.008;o=sphere('Triangular_fabric_nose',p,(.048,.023,.032),nosemat)
 for v in o.data.vertices:
  localz=(v.co.z-p.z)/.032
  if localz<0:v.co.x*=.62+.38*(localz+1)
 def line(name,points,radius=.0018):
  cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=radius;cu.bevel_resolution=2;sp=cu.splines.new('BEZIER');sp.bezier_points.add(len(points)-1)
  for b,(x,z) in zip(sp.bezier_points,points):p=hit(x,z);p.y-=.003;b.co=p;b.handle_left_type='AUTO';b.handle_right_type='AUTO'
  ob=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(ob);select(ob);bpy.ops.object.convert(target='MESH');ob=bpy.context.object;ob.data.materials.append(thread);U.attach_detail(ob,rig,'head');details.append(ob)
 line('Sewn_smile',[(-.076,1.164),(-.042,1.142),(0,1.150),(.042,1.142),(.076,1.164)]);line('Nose_stitch',[(0,1.214),(0,1.180),(0,1.150)],.0016)
 return details

def short_fibers(body,rig,count=6500):
 bpy.context.scene.frame_set(0);body.data.calc_loop_triangles();tris=np.array([t.vertices[:] for t in body.data.loop_triangles]);coords=np.array([v.co[:] for v in body.data.vertices]);normals=np.array([v.normal[:] for v in body.data.vertices]);tri=coords[tris];areas=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)*.5;rng=np.random.default_rng(20261015);pick=rng.choice(len(tris),count,p=areas/areas.sum());indices=tris[pick];a=np.sqrt(rng.random(count));b=rng.random(count);bary=np.column_stack([1-a,a*(1-b),a*b]);roots=(coords[indices]*bary[:,:,None]).sum(1);n=(normals[indices]*bary[:,:,None]).sum(1);n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-10);keep=roots[:,2]>.08;indices=indices[keep];bary=bary[keep];roots=roots[keep];n=n[keep];count=len(roots)
 t=np.cross(n,rng.normal(size=n.shape));t/=np.maximum(np.linalg.norm(t,axis=1)[:,None],1e-10);length=rng.uniform(.002,.0045,count);width=rng.uniform(.00035,.0006,count);v=np.empty((count,3,3));v[:,0]=roots-n*.0003-t*width[:,None];v[:,1]=roots-n*.0003+t*width[:,None];v[:,2]=roots+n*length[:,None]+t*length[:,None]*.18
 me=bpy.data.meshes.new('Short_plush_fibers');me.from_pydata(v.reshape(-1,3),[],np.arange(count*3).reshape(-1,3));me.update();ob=bpy.data.objects.new('Short_plush_fibers',me);bpy.context.collection.objects.link(ob);ob.parent=rig;gold=U.material('Honey_fiber_tips',(.42,.20,.064),.95);cream=U.material('Cream_fiber_tips',(.66,.53,.34),.95);me.materials.append(gold);me.materials.append(cream)
 for poly,p in zip(me.polygons,roots):
  x,y,z=p;poly.material_index=int(y<-.12 and ((x/.208)**2+((z-.735)/.279)**2<1 or (x/.172)**2+((z-1.21)/.114)**2<1))
 names=[b.name for b in rig.data.bones if b.use_deform];groups={n:ob.vertex_groups.new(name=n) for n in names};source=np.zeros((len(coords),len(names)));lookup={n:i for i,n in enumerate(names)}
 for vert in body.data.vertices:
  for g in vert.groups:
   name=body.vertex_groups[g.group].name
   if name in lookup:source[vert.index,lookup[name]]=g.weight
 weights=(source[indices]*bary[:,:,None]).sum(1)
 for i,w in enumerate(weights):
  ids=np.argsort(w)[-4:];values=w[ids];values/=max(values.sum(),1e-9)
  for j,weight in zip(ids,values):
   if weight>1e-8:groups[names[int(j)]].add([i*3,i*3+1,i*3+2],float(weight),'REPLACE')
 skin=ob.modifiers.new('Fiber_skin','ARMATURE');skin.object=rig;ob.shape_key_add(name='Basis')
 for key in list(body.data.shape_keys.key_blocks)[1:]:
  delta=np.array([p.co[:] for p in key.data])-coords;delta=(delta[indices]*bary[:,:,None]).sum(1);new=ob.shape_key_add(name=key.name);new.data.foreach_set('co',(v+delta[:,None,:]).astype('float32').ravel())
 ob.data.shape_keys.animation_data_create();ob.data.shape_keys.animation_data.action=body.data.shape_keys.animation_data.action;return ob,count

def make_lod(body,rig):
 from mathutils.kdtree import KDTree
 ob=body.copy();ob.data=body.data.copy();bpy.context.collection.objects.link(ob);ob.name='Teddy_Game_LOD';ob.shape_key_clear()
 for m in list(ob.modifiers):ob.modifiers.remove(m)
 select(ob);dec=ob.modifiers.new('Game_reduction','DECIMATE');dec.ratio=.4;bpy.ops.object.modifier_apply(modifier=dec.name);skin=ob.modifiers.new('Skin','ARMATURE');skin.object=rig;tree=KDTree(len(body.data.vertices))
 for v in body.data.vertices:tree.insert(v.co,v.index)
 tree.balance();nearest=[]
 for v in ob.data.vertices:
  ns=tree.find_n(v.co,4);w=np.array([1/(n[2]+.002)**2 for n in ns]);w/=w.sum();nearest.append(([n[1] for n in ns],w))
 base=np.array([v.co[:] for v in body.data.vertices]);newbase=np.array([v.co[:] for v in ob.data.vertices]);ob.shape_key_add(name='Basis')
 for old in list(body.data.shape_keys.key_blocks)[1:]:
  delta=np.array([v.co[:] for v in old.data])-base;d=np.array([(delta[i]*w[:,None]).sum(0) for i,w in nearest]);key=ob.shape_key_add(name=old.name);key.data.foreach_set('co',(newbase+d).astype('float32').ravel())
 ob.data.shape_keys.animation_data_create();ob.data.shape_keys.animation_data.action=body.data.shape_keys.animation_data.action;return ob

def export_glb(name,objects,rig):
 for o in bpy.context.selected_objects:o.select_set(False)
 for o in objects+[rig]:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.context.scene.frame_set(1)
 bpy.ops.export_scene.gltf(filepath=str(OUT/name),export_format='GLB',use_selection=True,export_skins=True,export_morph=True,export_morph_animation=True,export_animations=True,export_animation_mode='SCENE',export_force_sampling=True,export_frame_range=True,export_materials='EXPORT')
 raw=(OUT/name).read_bytes();length,kind=struct.unpack('<II',raw[12:20]);g=json.loads(raw[20:20+length]);merged={'name':'Walk_Loop','channels':[],'samplers':[]}
 for anim in g['animations']:
  offset=len(merged['samplers']);merged['samplers'].extend(anim['samplers'])
  for channel in anim['channels']:channel=dict(channel);channel['sampler']+=offset;merged['channels'].append(channel)
 g['animations']=[merged];text=json.dumps(g,separators=(',',':')).encode();text+=b' '*((-len(text))%4);tail=raw[20+length:];(OUT/name).write_bytes(struct.pack('<III',0x46546c67,2,20+len(text)+len(tail))+struct.pack('<II',len(text),0x4e4f534a)+text+tail);paths={c['target']['path'] for c in merged['channels']}
 report={'skins':len(g.get('skins',[])),'animations':['Walk_Loop'],'animation_paths':sorted(paths),'triangles':sum(g['accessors'][p['indices']]['count']//3 for m in g['meshes'] for p in m['primitives']),'textures':len(g.get('textures',[])),'bytes':(OUT/name).stat().st_size};assert report['skins'] and report['textures']>=3 and {'rotation','weights'}<=paths,report;return report

def preview(cam):
 if os.environ.get('MUDELITEHAS_PREVIEW')=='none':return
 sc=bpy.context.scene;cam.location=(2.8,-5,2);U.aim(cam,(0,0,.82));cam.data.ortho_scale=1.95;sc.cycles.samples=16;folder=OUT/'frames';folder.mkdir(exist_ok=True);images=[]
 for f in range(1,49,4 if os.environ.get('MUDELITEHAS_PREVIEW')=='quick' else 2):
  sc.frame_set(f);sc.render.filepath=str(folder/f'walk_{f:03}.png');bpy.ops.render.render(write_still=True);images.append(Image.open(sc.render.filepath).convert('RGB'));print('WALK_FRAME',f,flush=True)
 pal=images[0].quantize(colors=256);frames=[im.quantize(palette=pal,dither=Image.Dither.FLOYDSTEINBERG) for im in images];frames[0].save(OUT/'Jalutav_Mangukaru_Uus.gif',save_all=True,append_images=frames[1:],duration=167 if os.environ.get('MUDELITEHAS_PREVIEW')=='quick' else 83,loop=0,disposal=2);sc.frame_set(1);sc.render.filepath=str(OUT/'Jalutav_Mangukaru_Uus.png');bpy.ops.render.render(write_still=True)

if MODE=='finish':
 stage('load_pose_cache',lambda:bpy.ops.wm.open_mainfile(filepath=str(CACHE/'Walk_review.blend')));body=bpy.data.objects['Teddy_Body_10000_Quads'];rig=bpy.data.objects['Teddy_Rig'];specs=json.loads(rig['specs']);joint=stage('bake_joint_shapes',lambda:bake_joint_shapes(body,rig));validation=stage('final_deformation',lambda:check(body,rig));validation['topology']=U.validate(body,True)
 assert validation['topology']['quad_faces']==10000 and validation['loop_seam_m']<1e-5 and validation['minimum_z_m']>-.003 and validation['max_skin_motion_m']>.1 and validation['bone_length_error_m']<1e-4,validation
 stage('plush_PBR',lambda:coat(body));bpy.context.scene.frame_set(0);details=stage('face_details',lambda:face(body,rig));fibers,count=stage('short_plush_fibers',lambda:short_fibers(body,rig));details_fur=details+[fibers];validation['joint_correctives']=joint;validation['fiber_triangles']=count;validation['main_glb']=stage('export_main',lambda:export_glb('Jalutav_Mangukaru_10000.glb',[body]+details_fur,rig));lod=stage('game_lod',lambda:make_lod(body,rig));validation['lod_glb']=stage('export_lod',lambda:export_glb('Jalutav_Mangukaru_LOD.glb',[lod]+details,rig));bpy.data.objects.remove(lod,do_unlink=True)
 validation.update({'command':'Mudelitehas 10000 3 jalutav mängukaru animatsiooniga','bones':len(rig.data.bones),'primary_quad_faces':10000,'rest_pose':'T-pose, frame 0','animation':'Walk_Loop, frames 1-49 at 24 fps','pipeline':'requested-pose image -> neutral four views -> oriented cloud saved before Poisson mesh -> exact 10000 quads -> rig and skin -> pose gate -> joint corrective morphs -> PBR -> export and reimport validation','limitations':['Estimated plush toy shape, not a scan or exact copy of generated reference.','Short polygon fibers approximate pile; not a dense strand groom.','In-place gait requires matching movement speed in a game.'],'timings_seconds':TIMES})
 (OUT/'validation.json').write_text(json.dumps(validation,indent=2));body['validation']=json.dumps(validation);cam=studio(True);stage('final_controls',lambda:controls(cam));bpy.context.scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Jalutav_Mangukaru_10000.blend'));stage('walk_GIF',lambda:preview(cam));validation['timings_seconds']=TIMES;validation['finish_seconds']=time.perf_counter()-START;(OUT/'validation.json').write_text(json.dumps(validation,indent=2));print('FINISH_COMPLETE',json.dumps(validation),flush=True)

if MODE=='motion-update':
 bpy.ops.wm.open_mainfile(filepath=str(CACHE/'Walk_review.blend'));body=bpy.data.objects['Teddy_Body_10000_Quads'];rig=bpy.data.objects['Teddy_Rig'];specs=json.loads(rig['specs']);animate(rig,specs);bpy.ops.wm.save_as_mainfile(filepath=str(CACHE/'Walk_review.blend'));joint=bake_joint_shapes(body,rig);shape_names=[k.name for k in list(body.data.shape_keys.key_blocks)[1:]];arrays=[np.array([v.co[:] for v in k.data]) for k in list(body.data.shape_keys.key_blocks)[1:]];base=np.array([v.co[:] for v in body.data.vertices])
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Jalutav_Mangukaru_10000.blend'));body=bpy.data.objects['Teddy_Body_10000_Quads'];rig=bpy.data.objects['Teddy_Rig'];specs=json.loads(rig['specs']);assert np.max(abs(np.array([v.co[:] for v in body.data.vertices])-base))<1e-6;animate(rig,specs)
 for name,coords in zip(shape_names,arrays):body.data.shape_keys.key_blocks[name].data.foreach_set('co',coords.astype('float32').ravel())
 for ob in list(bpy.data.objects):
  if ob.name=='Short_plush_fibers':bpy.data.objects.remove(ob,do_unlink=True)
 fibers,count=short_fibers(body,rig);details=[ob for ob in bpy.data.objects if ob.type=='MESH' and ob.parent==rig and ob!=body and ob!=fibers];validation=json.loads((OUT/'validation.json').read_text());validation.update(check(body,rig));validation['joint_correctives']=joint;validation['gait_phase']='Opposite arm swings against forward foot (cosine aligned stride)';validation['main_glb']=export_glb('Jalutav_Mangukaru_10000.glb',[body]+details+[fibers],rig);lod=make_lod(body,rig);validation['lod_glb']=export_glb('Jalutav_Mangukaru_LOD.glb',[lod]+details,rig);bpy.data.objects.remove(lod,do_unlink=True);(OUT/'validation.json').write_text(json.dumps(validation,indent=2));body['validation']=json.dumps(validation);cam=studio(True);controls(cam);bpy.context.scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Jalutav_Mangukaru_10000.blend'));preview(cam);print('MOTION_UPDATE_COMPLETE',flush=True)

if MODE=='finalize':
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Jalutav_Mangukaru_10000.blend'));body=bpy.data.objects['Teddy_Body_10000_Quads'];rig=bpy.data.objects['Teddy_Rig'];d=json.loads((OUT/'validation.json').read_text());d.update(check(body,rig));bpy.context.scene.frame_set(0);d['final_mesh_silhouette_iou']=U.mesh_silhouette_check(body);d['export_reimport_validation']=json.loads((OUT/'export_reimport_validation.json').read_text());d['visual_review']={'rest_front_side_back':'reviewed','walking_phases':'reviewed','face_and_materials':'reviewed','gait_phase':'opposite arm and forward foot verified','fur':'short skinned polygon fibers with matched corrective keys'};(OUT/'validation.json').write_text(json.dumps(d,indent=2));body['validation']=json.dumps(d)
 if 'validation.json' in bpy.data.texts:bpy.data.texts.remove(bpy.data.texts['validation.json'])
 bpy.data.texts.new('validation.json').write(json.dumps(d,indent=2));bpy.context.scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Jalutav_Mangukaru_10000.blend'));print('FINALIZE_COMPLETE',flush=True)

if MODE=='render-only':
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Jalutav_Mangukaru_10000.blend'));cam=studio(True);controls(cam);preview(cam)
