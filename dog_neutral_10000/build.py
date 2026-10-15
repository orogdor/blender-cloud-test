"""Standing Poisson surface -> exactly 10000 quads -> canine rig -> sit-pretty.
The old recipe supplies topology/export utilities only; anatomy and motion are new.
"""
import bpy,bmesh,json,math,struct,shutil,sys,importlib.util
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).parent;OUT=Path('output/dog_neutral_10000');OUT.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('mesh_utilities',ROOT.parent/'dog_mudelitehas/build_dog.py');U=importlib.util.module_from_spec(spec);spec.loader.exec_module(U)
U.OUT=OUT;U.TARGET_BASE=2500
FPS=24;FRAMES=144;TARGET_FRAME=73

def mat(name,color,rough=.7):return U.material(name,color,rough)
def select(ob):
 for o in bpy.context.selected_objects:o.select_set(False)
 ob.select_set(True);bpy.context.view_layer.objects.active=ob
def coords(ob):
 ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();a=np.empty(len(m.vertices)*3,dtype='float32');m.vertices.foreach_get('co',a);ev.to_mesh_clear();return a.reshape(-1,3)

def rig_and_weights(body):
 arm=bpy.data.armatures.new('Canine_neutral_standing_skeleton');rig=bpy.data.objects.new('Dog_Rig',arm);bpy.context.collection.objects.link(rig);select(rig);bpy.ops.object.mode_set(mode='EDIT')
 specs={'root':((0,0,0),(0,0,.08),None),'pelvis':((0,.43,.72),(0,.22,.75),'root'),'spine':((0,.22,.75),(0,-.02,.78),'pelvis'),'chest':((0,-.02,.78),(0,-.32,.82),'spine'),'neck':((0,-.32,.82),(0,-.48,1.04),'chest'),'head':((0,-.48,1.04),(0,-.58,1.16),'neck'),'jaw':((0,-.60,1.0),(0,-.84,.975),'head')}
 for s,side in ((1,'L'),(-1,'R')):
  specs.update({'shoulder.'+side:((s*.12,-.30,.78),(s*.145,-.298,.68),'chest'),'upper_foreleg.'+side:((s*.145,-.298,.68),(s*.155,-.335,.39),'shoulder.'+side),'lower_foreleg.'+side:((s*.155,-.335,.39),(s*.161,-.405,.092),'upper_foreleg.'+side),'forepaw.'+side:((s*.161,-.405,.092),(s*.163,-.465,.035),'lower_foreleg.'+side),'thigh.'+side:((s*.143,.402,.64),(s*.165,.285,.398),'pelvis'),'hock.'+side:((s*.165,.285,.398),(s*.169,.482,.176),'thigh.'+side),'hind_ankle.'+side:((s*.169,.482,.176),(s*.169,.464,.065),'hock.'+side),'hindpaw.'+side:((s*.169,.464,.065),(s*.170,.396,.035),'hind_ankle.'+side),'ear.'+side:((s*.15,-.47,1.145),(s*.19,-.48,.97),'head')})
 tail=[(0,.526,.758),(0,.616,.64),(0,.704,.50),(0,.780,.365)]
 for i in range(3):specs['tail_'+str(i+1)]=(tail[i],tail[i+1],'pelvis' if i==0 else 'tail_'+str(i))
 for name,(a,b,parent) in specs.items():
  bone=arm.edit_bones.new(name);bone.head=a;bone.tail=b;bone.use_deform=name!='root'
  if parent:bone.parent=arm.edit_bones[parent]
 bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True
 groups={n:body.vertex_groups.new(name=n) for n in specs if n!='root'}
 for v in body.data.vertices:
  x,y,z=v.co;side='L' if x>0 else 'R'
  if z>.94 and y<-.37:
   names=['head','neck','jaw']
   if abs(x)>.14 and y>-.62:names=['head','ear.'+side]
  elif y<-.40 and z>.83:names=['head','neck','jaw']
  elif z<.59 and y<-.20 and abs(x)>.075:names=['shoulder.'+side,'upper_foreleg.'+side,'lower_foreleg.'+side,'forepaw.'+side]
  elif z<.59 and y>.17 and abs(x)>.082:names=['pelvis','thigh.'+side,'hock.'+side,'hind_ankle.'+side,'hindpaw.'+side]
  elif y>.54 and abs(x)<.11:names=['pelvis','tail_1','tail_2','tail_3']
  else:names=['pelvis','spine','chest','neck','head']
  ds=[U.bone_dist(v.co,*specs[n][:2]) for n in names];ids=sorted(range(len(names)),key=lambda i:ds[i])[:3];weights=np.array([1/(ds[i]+.025)**5 for i in ids]);weights/=weights.sum()
  # Planted feet must stay rigidly bound below the ankle for precise contact.
  if z<.095 and y>.22:ids=[names.index('hindpaw.'+side)] if 'hindpaw.'+side in names else ids;weights=np.ones(len(ids))/len(ids)
  for i,w in zip(ids,weights):groups[names[i]].add([v.index],float(w),'REPLACE')
 # Topological diffusion smooths region boundaries without bridging separate legs.
 gs=list(body.vertex_groups);w=np.zeros((len(body.data.vertices),len(gs)))
 for v in body.data.vertices:
  for g in v.groups:w[v.index,g.group]=g.weight
 edges=np.array([tuple(e.vertices) for e in body.data.edges]);degree=np.bincount(edges.ravel(),minlength=len(w));fixed=np.array([v.co.z<.088 and v.co.y>.22 for v in body.data.vertices])
 for _ in range(6):
  nw=np.zeros_like(w);np.add.at(nw,edges[:,0],w[edges[:,1]]);np.add.at(nw,edges[:,1],w[edges[:,0]]);nw=.48*w+.52*nw/np.maximum(degree[:,None],1);nw[fixed]=w[fixed];w=nw
 # Four influences export identically to glTF and the Blender linear skin.
 order=np.argsort(w,axis=1)[:,:-4];np.put_along_axis(w,order,0,axis=1);w/=np.maximum(w.sum(1)[:,None],1e-12)
 for g in gs:g.remove(list(range(len(w))))
 for i,row in enumerate(w):
  for j in np.flatnonzero(row>0):gs[int(j)].add([i],float(row[j]),'REPLACE')
 body.parent=rig;select(body)
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1519,island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
 sub=body.modifiers.new('Exact_10000_quads','SUBSURF');sub.levels=1;sub.render_levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
 # Subdivision interpolates influences; trim and renormalize again for export.
 for v in body.data.vertices:
  entries=sorted([(g.group,g.weight) for g in v.groups],key=lambda q:q[1],reverse=True)
  for gi,_ in entries[4:]:body.vertex_groups[gi].remove([v.index])
  total=sum(w for _,w in entries[:4])
  for gi,w in entries[:4]:body.vertex_groups[gi].add([v.index],w/total,'REPLACE')
 skin=body.modifiers.new('Canine_linear_skin','ARMATURE');skin.object=rig;skin.use_deform_preserve_volume=False
 return rig,specs

def setup_coat(body):
 """Bake continuous four-camera photo projection, preserving coat detail."""
 m=mat('Golden_dog_photo_PBR',(.52,.26,.09),.78);nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes.get('Principled BSDF');out=nodes.get('Material Output')
 if 'Sheen Weight' in bs.inputs:bs.inputs['Sheen Weight'].default_value=.20
 geo=nodes.new('ShaderNodeNewGeometry');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(geo.outputs['Position'],sep.inputs[0]);ns=nodes.new('ShaderNodeSeparateXYZ');links.new(geo.outputs['Normal'],ns.inputs[0])
 def mathnode(op,a,b=None):
  n=nodes.new('ShaderNodeMath');n.operation=op
  for i,v in enumerate([a,b]):
   if v is None:continue
   if isinstance(v,(int,float)):n.inputs[i].default_value=v
   else:links.new(v,n.inputs[i])
  return n.outputs[0]
 def combine(a,b,c):
  n=nodes.new('ShaderNodeCombineXYZ')
  for v,s in zip([a,b,c],n.inputs):
   if isinstance(v,(int,float)):s.default_value=v
   else:links.new(v,s)
  return n.outputs[0]
 colors=[];weights=[];d=np.load(OUT/'aligned_images.npz')
 for name,axis,normal,sign in [('front','X','Y',-1),('back','X','Y',1),('left','Y','X',-1),('right','Y','X',1)]:
  ar=d['x' if axis=='X' else 'y'];zs=d['z'];u=mathnode('DIVIDE',mathnode('SUBTRACT',sep.outputs[axis],float(ar[0])),float(ar[-1]-ar[0]));v=mathnode('DIVIDE',mathnode('SUBTRACT',sep.outputs['Z'],float(zs[0])),float(zs[-1]-zs[0]))
  tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str((ROOT/('source_'+name+'.png')).resolve()));tex.image.pack();tex.extension='EXTEND';links.new(combine(u,v,0),tex.inputs['Vector'])
  facing=mathnode('POWER',mathnode('MAXIMUM',mathnode('MULTIPLY',ns.outputs[normal],sign),0),4)
  # Dilation avoids white fringes; source alpha marks actual silhouette coverage.
  weight=mathnode('MULTIPLY',facing,mathnode('GREATER_THAN',tex.outputs['Alpha'],.4));weights.append(weight)
  scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';links.new(tex.outputs['Color'],scale.inputs[0]);links.new(weight,scale.inputs[3]);colors.append(scale.outputs[0])
 total=weights[0];color=colors[0]
 for w,c in zip(weights[1:],colors[1:]):
  total=mathnode('ADD',total,w);add=nodes.new('ShaderNodeVectorMath');add.operation='ADD';links.new(color,add.inputs[0]);links.new(c,add.inputs[1]);color=add.outputs[0]
 scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';links.new(color,scale.inputs[0]);links.new(mathnode('DIVIDE',1,mathnode('MAXIMUM',total,.001)),scale.inputs[3]);color=scale.outputs[0]
 mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';links.new(mathnode('GREATER_THAN',total,.005),mix.inputs[0]);mix.inputs[1].default_value=(.42,.21,.075,1);links.new(color,mix.inputs[2]);links.new(mix.outputs[0],bs.inputs['Base Color'])
 noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=380;noise.inputs['Detail'].default_value=3
 texco=nodes.new('ShaderNodeTexCoord');mult=nodes.new('ShaderNodeVectorMath');mult.operation='MULTIPLY';mult.inputs[1].default_value=(1,1,.13);links.new(texco.outputs['Generated'],mult.inputs[0]);links.new(mult.outputs[0],noise.inputs['Vector'])
 bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.0012;links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs[0],bs.inputs['Normal'])
 body.data.materials.clear();body.data.materials.append(m)
 for p in body.data.polygons:p.use_smooth=True
 select(body);skin=body.modifiers.get('Canine_linear_skin');skin.show_render=False;skin.show_viewport=False
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.cycles.use_denoising=False
 td=OUT/'textures';td.mkdir(exist_ok=True);target=nodes.new('ShaderNodeTexImage')
 def bake(name,kind):
  image=bpy.data.images.new(name,width=2048,height=2048,alpha=False)
  if kind=='NORMAL':image.colorspace_settings.name='Non-Color'
  target.image=image;nodes.active=target;bpy.ops.object.bake(type=kind,margin=12,use_clear=True);image.filepath_raw=str((td/(name+'.png')).resolve());image.file_format='PNG';image.save();image.pack();print('BAKED',name,flush=True);return image
 emit=nodes.new('ShaderNodeEmission');links.new(mix.outputs[0],emit.inputs['Color']);links.new(emit.outputs[0],out.inputs['Surface']);base=bake('Dog_BaseColor','EMIT');links.new(bs.outputs[0],out.inputs['Surface']);normal=bake('Dog_Normal','NORMAL')
 btex=nodes.new('ShaderNodeTexImage');btex.image=base;links.new(btex.outputs['Color'],bs.inputs['Base Color']);ntex=nodes.new('ShaderNodeTexImage');ntex.image=normal;norm=nodes.new('ShaderNodeNormalMap');links.new(ntex.outputs['Color'],norm.inputs['Color']);links.new(norm.outputs[0],bs.inputs['Normal'])
 rng=np.random.default_rng(42);rough=np.clip(.79+rng.normal(0,.015,(1024,1024)),.72,.86);Image.fromarray((rough*255).astype('uint8')).save(td/'Dog_Roughness.png');ri=bpy.data.images.load(str((td/'Dog_Roughness.png').resolve()));ri.colorspace_settings.name='Non-Color';ri.pack();rt=nodes.new('ShaderNodeTexImage');rt.image=ri;links.new(rt.outputs['Color'],bs.inputs['Roughness'])
 skin.show_render=True;skin.show_viewport=True

def face_details(body,rig):
 details=[];eye=mat('Moist_dark_brown_eyes',(.022,.010,.004),.15);nosemat=mat('Textured_black_nose',(.012,.010,.008),.38);mouthmat=mat('Fine_mouth_line',(.019,.011,.008),.65)
 def hit(x,z):
  ok,p,n,fi=body.ray_cast(Vector((x,-2,z)),Vector((0,1,0)));return p if ok else Vector((x,-.75,z))
 def sphere(name,p,scale,material):
  bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=p);ob=bpy.context.object;ob.name=name;ob.scale=scale;bpy.ops.object.transform_apply(location=True,rotation=False,scale=True);ob.data.materials.append(material);U.attach_detail(ob,rig,'head');details.append(ob)
 for s in (-1,1):
  p=hit(s*.085,1.145);p.y-=.005;sphere('Eye_L' if s>0 else 'Eye_R',p,(.016,.009,.015),eye)
 p=hit(0,1.023);p.y-=.008;sphere('Nose',p,(.043,.025,.029),nosemat)
 # Muzzle line wraps across the actual reconstructed surface.
 curve=bpy.data.curves.new('Closed_mouth','CURVE');curve.dimensions='3D';curve.bevel_depth=.0012;curve.bevel_resolution=1;sp=curve.splines.new('BEZIER');sp.bezier_points.add(4)
 for b,(x,z) in zip(sp.bezier_points,[(-.08,.971),(-.045,.956),(0,.952),(.045,.956),(.08,.971)]):
  p=hit(x,z);p.y-=.002;b.co=p;b.handle_left_type='AUTO';b.handle_right_type='AUTO'
 ob=bpy.data.objects.new('Mouth_line',curve);bpy.context.collection.objects.link(ob);select(ob);bpy.ops.object.convert(target='MESH');ob.data.materials.append(mouthmat);U.attach_detail(ob,rig,'head');details.append(ob)
 return details

def rx(angle):return Matrix.Rotation(angle,3,'X')
def two_bone(a,b,l1,l2):
 d=(b-a).length;ex=(b-a)/d;along=(l1*l1-l2*l2+d*d)/(2*d);along=max(-l1,min(l1,along));height=math.sqrt(max(0,l1*l1-along*along));perp=Vector((0,-ex.z,ex.y)).normalized()
 if perp.y>0:perp=-perp
 return a+ex*along+perp*height

def apply_pose(rig,specs,t,idle=0):
 """Solve world-space bone directions with fixed hind feet and fixed lengths."""
 restP=Vector(specs['pelvis'][0]);P=restP.lerp(Vector((0,.58,.23)),t);R=rx(math.radians(-75)*t);targets={}
 def put(name,a,b):targets[name]=(Vector(a),Vector(b))
 put('root',*specs['root'][:2])
 a=P.copy()
 for n in ['pelvis','spine','chest']:
  vec=Vector(specs[n][1])-Vector(specs[n][0]);b=a+R@vec;put(n,a,b);a=b
 neckR=rx(math.radians(-30)*t+idle*.005);b=a+neckR@(Vector(specs['neck'][1])-Vector(specs['neck'][0]));put('neck',a,b)
 headR=Matrix.Rotation(idle*.018,3,'Z')@rx(math.radians(-3)*t);a=b;b=a+headR@(Vector(specs['head'][1])-Vector(specs['head'][0]));put('head',a,b)
 headA=a.copy()
 for n in ['jaw','ear.L','ear.R']:
  a=headA+headR@(Vector(specs[n][0])-Vector(specs['head'][0]));b=a+headR@(Vector(specs[n][1])-Vector(specs[n][0]));put(n,a,b)
 for s,side in ((1,'L'),(-1,'R')):
  n='shoulder.'+side;a=targets['chest'][0]+R@(Vector(specs[n][0])-Vector(specs['chest'][0]));b=a+R@(Vector(specs[n][1])-Vector(specs[n][0]));put(n,a,b);a=b
  for part,ang in [('upper_foreleg',-53),('lower_foreleg',10),('forepaw',63)]:
   n=part+'.'+side;rr=rx(math.radians(ang)*t+idle*.012*t);b=a+rr@(Vector(specs[n][1])-Vector(specs[n][0]));put(n,a,b);a=b
  n='thigh.'+side;hip=P+R@(Vector(specs[n][0])-restP);ankle=Vector(specs['hock.'+side][1]);l1=(Vector(specs[n][1])-Vector(specs[n][0])).length;l2=(Vector(specs['hock.'+side][1])-Vector(specs['hock.'+side][0])).length
  knee=two_bone(hip,ankle,l1,l2);put(n,hip,knee);put('hock.'+side,knee,ankle)
  for part in ['hind_ankle','hindpaw']:put(part+'.'+side,*specs[part+'.'+side][:2])
 a=P+R@(Vector(specs['tail_1'][0])-restP)
 for i in range(1,4):
  n='tail_'+str(i);rr=Matrix.Rotation(t*idle*.10*i,3,'Z')@rx(math.radians(46)*t);b=a+rr@(Vector(specs[n][1])-Vector(specs[n][0]));put(n,a,b);a=b
 # Set ancestors first; a quaternion rotates the bone's original frame to its target.
 for name,(a,b) in targets.items():
  pb=rig.pose.bones[name];rest=pb.bone.matrix_local.copy();restvec=Vector(specs[name][1])-Vector(specs[name][0]);rotation=restvec.rotation_difference(b-a).to_matrix();matrix=(rotation@rest.to_3x3()).to_4x4();matrix.translation=a;pb.matrix=matrix;bpy.context.view_layer.update()
 return targets

def animate(rig,specs):
 scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=FRAMES+1;scene.render.fps=FPS
 for pb in rig.pose.bones:pb.rotation_mode='QUATERNION'
 for f in range(1,FRAMES+2):
  scene.frame_set(f)
  if f<=49:u=(f-1)/48;t=u*u*(3-2*u)
  elif f<=97:t=1.
  else:u=(f-97)/48;t=1-u*u*(3-2*u)
  idle=math.sin(2*math.pi*(f-49)/48)*t
  apply_pose(rig,specs,t,idle)
  for pb in rig.pose.bones:
   pb.keyframe_insert('location',frame=f);pb.keyframe_insert('rotation_quaternion',frame=f);pb.keyframe_insert('scale',frame=f)
 rig.animation_data.action.name='Stand_to_SitPretty_and_Back'
 for fc in rig.animation_data.action.fcurves:
  for k in fc.keyframe_points:k.interpolation='LINEAR'
 scene.frame_set(TARGET_FRAME)

def deformation_checks(body,rig,specs):
 scene=bpy.context.scene;rest=np.array([tuple(v.co) for v in body.data.vertices]);edges=np.array([tuple(e.vertices) for e in body.data.edges]);length=np.linalg.norm(rest[edges[:,0]]-rest[edges[:,1]],axis=1);poses=[];ratios=[];grounds=[];feet=[];bone_errors=[]
 fixed=(rest[:,2]<.07)&(rest[:,1]>.26)
 for f in [1,13,25,37,49,61,73,85,97,109,121,133,145]:
  scene.frame_set(f);a=coords(body);poses.append(a);grounds.append(float(a[:,2].min()));feet.append(a[fixed]);pl=np.linalg.norm(a[edges[:,0]]-a[edges[:,1]],axis=1);valid=length>.001;ratios.append(float(np.quantile(pl[valid]/length[valid],.999)))
  for n,pb in rig.pose.bones.items():bone_errors.append(abs((pb.tail-pb.head).length-pb.bone.length))
 assert np.isfinite(poses).all()
 move=float(np.linalg.norm(poses[6]-poses[0],axis=1).max());seam=float(np.abs(poses[-1]-poses[0]).max());footmotion=float(np.linalg.norm(np.array(feet)-feet[0],axis=2).max())
 report={'max_vertex_motion':move,'skin_stretch_ratio_99_9_percent':max(ratios),'ground_minimum_z_by_pose':grounds,'planted_hindfoot_max_motion':footmotion,'bone_length_error_max':max(bone_errors),'animation_loop_seam':seam,'poses_checked':len(poses),'rest_pose_frame':1,'requested_pose_frame':TARGET_FRAME,'self_intersection_check':'visual multi-angle review plus ground and deformation metrics; not an exhaustive collision proof'}
 np.savez_compressed(OUT/'deformation_samples.npz',rest=rest,poses=np.array(poses),edges=edges)
 (OUT/'deformation_validation.json').write_text(json.dumps(report,indent=2));print('DEFORMATION',report,flush=True)
 assert move>.3 and seam<1e-5 and footmotion<.025 and max(bone_errors)<.002,report
 assert min(grounds)>-.045,report
 scene.frame_set(TARGET_FRAME);return report

def studio():
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True;scene.render.resolution_x=512;scene.render.resolution_y=640;scene.render.resolution_percentage=100
 scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.22,.25,.3,1);scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.5
 scene.view_settings.view_transform='AgX'
 bpy.ops.object.camera_add(location=(2.8,-4.8,2.0));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=1.95;U.aim(cam,(0,.13,.75));scene.camera=cam
 for pos,power,size in [((2,-3,4),450,3),((-3,-1,3),250,3),((1,3,3),500,3)]:
  bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;U.aim(o,(0,.1,.7))
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.006));floor=bpy.context.object;floor.name='Preview_floor';floor.data.materials.append(mat('Studio_matte_gray',(.13,.16,.20),.85));return cam

def render(cam):
 scene=bpy.context.scene;scene.frame_set(TARGET_FRAME);scene.render.filepath=str(OUT/'Dog_SitPretty_preview.png');bpy.ops.render.render(write_still=True)
 oldpos=cam.location.copy();oldrot=cam.rotation_euler.copy();oldscale=cam.data.ortho_scale
 views=[]
 for name,pos,frame,target in [('rest_front',(0,-5,.65),1,(0,0,.65)),('rest_left',(-5,0,.65),1,(0,0,.65)),('sit_front',(0,-5,.8),TARGET_FRAME,(0,.25,.75)),('sit_left',(-5,.25,.8),TARGET_FRAME,(0,.25,.75)),('sit_back',(0,5,.8),TARGET_FRAME,(0,.25,.75)),('sit_high',(2,-3,3),TARGET_FRAME,(0,.25,.75))]:
  scene.frame_set(frame);cam.location=pos;U.aim(cam,target);cam.data.ortho_scale=1.95;scene.render.resolution_percentage=70;scene.render.filepath=str(OUT/('view_'+name+'.png'));bpy.ops.render.render(write_still=True);im=Image.open(scene.render.filepath).convert('RGB');draw=ImageDraw.Draw(im);draw.text((10,10),name,fill='white');views.append(im)
 sheet=Image.new('RGB',(views[0].width*3,views[0].height*2))
 for i,im in enumerate(views):sheet.paste(im,((i%3)*im.width,(i//3)*im.height))
 sheet.save(OUT/'Actual_model_rest_and_sitting_views.png');cam.location=oldpos;cam.rotation_euler=oldrot;cam.data.ortho_scale=oldscale;scene.render.resolution_percentage=100
 # Save the editable model before the longer animation preview.
 scene.frame_set(TARGET_FRAME);bpy.ops.wm.save_as_mainfile(filepath=str((OUT/'Dog_SitPretty_10000.blend').resolve()))
 if '--preview-only' in sys.argv:return
 folder=OUT/'frames';folder.mkdir(exist_ok=True);pictures=[];scene.cycles.samples=12
 for f in range(1,FRAMES+1,3):
  scene.frame_set(f);scene.render.filepath=str(folder/f'dog_{f:03}.png');bpy.ops.render.render(write_still=True);pictures.append(Image.open(scene.render.filepath).convert('RGB'));print('ANIMATION_FRAME',f,flush=True)
 palette=pictures[len(pictures)//2].quantize(colors=192);gif=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in pictures];gif[0].save(OUT/'Dog_Stand_to_SitPretty.gif',save_all=True,append_images=gif[1:],duration=125,loop=0,disposal=2)
 scene.frame_set(TARGET_FRAME)

def export_lod(body,details,rig):
 lod=body.copy();lod.data=body.data.copy();bpy.context.collection.objects.link(lod);lod.name='Dog_LOD';select(lod)
 for m in list(lod.modifiers):lod.modifiers.remove(m)
 dec=lod.modifiers.new('LOD_35_percent','DECIMATE');dec.ratio=.35;bpy.ops.object.modifier_apply(modifier=dec.name);skin=lod.modifiers.new('Skin','ARMATURE');skin.object=rig
 result=U.export_glb('Dog_SitPretty_LOD.glb',[lod]+details,rig);bpy.data.objects.remove(lod,do_unlink=True);return result

def main():
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 source=json.loads((OUT/'05_surface.json').read_text());mesh=bpy.data.meshes.new('Poisson_from_standing_cloud');mesh.from_pydata(source['points'],[],source['triangles']);mesh.update();body=bpy.data.objects.new('Dog_10000_Body_Quads',mesh);bpy.context.collection.objects.link(body);select(body)
 rem=body.modifiers.new('Close_reconstruction','REMESH');rem.mode='VOXEL';rem.voxel_size=.007;rem.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=rem.name);smooth=body.modifiers.new('Relax','SMOOTH');smooth.factor=.45;smooth.iterations=2;bpy.ops.object.modifier_apply(modifier=smooth.name);print('CLOSED_POISSON',U.validate(body),flush=True)
 bpy.ops.object.quadriflow_remesh(target_faces=2300,seed=4,use_preserve_sharp=False,use_preserve_boundary=False);print('QUAD_REMESH',U.validate(body,True),flush=True);U.exact_quads(body);smooth=body.modifiers.new('Relax_quads','SMOOTH');smooth.factor=.20;smooth.iterations=2;bpy.ops.object.modifier_apply(modifier=smooth.name)
 rig,specs=rig_and_weights(body);report=U.validate(body,True);assert report['quad_faces']==10000,report
 setup_coat(body);details=face_details(body,rig);animate(rig,specs);report.update(deformation_checks(body,rig,specs));report['final_mesh_silhouette_iou']=U.mesh_silhouette_check(body)
 report.update({'body_quad_faces':10000,'level':3,'bones':len(specs),'animation':'Stand_to_SitPretty_and_Back','frames':FRAMES,'fps':FPS,'preview_fps':8,'reconstruction_pose':'standing_on_four_legs','final_pose':'sit_pretty','details_separate_by_design':[o.name for o in details],'material_maps':['Dog_BaseColor.png','Dog_Normal.png','Dog_Roughness.png'],'depth_and_hidden_joints':'anatomically estimated from four generated reference images','fur':'short coat camera-projected albedo with baked micro normal, no disconnected fur ribbons'})
 assert all(abs(sum(g.weight for g in v.groups)-1)<1e-4 for v in body.data.vertices)
 report['animated_glb']=U.export_glb('Dog_SitPretty_10000.glb',[body]+details,rig);report['lod_glb']=export_lod(body,details,rig);assert report['animated_glb']['textures']>=3
 (OUT/'validation.json').write_text(json.dumps(report,indent=2));body['validation']=json.dumps(report)
 for file in ROOT.iterdir():
  if file.suffix in ('.py','.json','.b85','.md','.png','.jpg'):shutil.copyfile(file,OUT/file.name)
 for n in ['pipeline.json','validation.json']:
  t=bpy.data.texts.new(n);t.write((OUT/n).read_text())
 cam=studio();render(cam);print('DOG_NEUTRAL_10000_COMPLETE',report,flush=True)

if __name__=='__main__':main()
