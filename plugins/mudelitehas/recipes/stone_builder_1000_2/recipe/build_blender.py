"""Blender 4.5.3 only. Cloud-guided quad retopology of a neutral Stone Age builder.
Real cloud MUST have been created and verified first; no standalone model fabrication.
"""
import bpy,bmesh,json,sys,math,os
from pathlib import Path
from mathutils import Vector
import numpy as np

argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if len(argv)!=2 or argv[0]!='--workdir':raise ValueError('Expected -- --workdir <previously validated workdir>')
W=Path(argv[1]);cloud=W/'cloud_before_mesh.npz';gate=W/'three_direction_gate.json';review=W/'preflight.json'
if not all(x.is_file() for x in [cloud,gate,review]):raise RuntimeError('Pre-mesh evidence and independent gate required')
assert bpy.app.version==(4,5,3),'Expected Blender 4.5.3'
g=json.loads(gate.read_text());pre=json.loads(review.read_text())
if g['independent_direction_rank']!=3 or g['point_count']<300:raise ValueError('Multiview gate failed')
if pre['synthetic_test']:raise ValueError('Synthetic test input cannot produce a production model')
with np.load(cloud,allow_pickle=False) as npz:points=np.asarray(npz['points'])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)

# Ring priors are T-POSE ANATOMICAL estimates, then fitted to recorded pre-mesh cloud.
# Proportions MUST be visually reviewed against actual images; depth is not measured.
sections={
 'torso':dict(axis='y',steps=12,a=.79,b=1.47,center=[0,0,0],base=(.22,.165)),
 'head':dict(axis='y',steps=8,a=1.43,b=1.81,center=[0,0,0],base=(.135,.118)),
 'left_arm':dict(axis='x',steps=11,a=-1.08,b=-.19,center=[0,1.345,0],base=(.078,.090)),
 'right_arm':dict(axis='x',steps=11,a=.19,b=1.08,center=[0,1.345,0],base=(.078,.090)),
 'left_leg':dict(axis='y',steps=11,a=.06,b=.87,center=[-.17,0,.015],base=(.103,.10)),
 'right_leg':dict(axis='y',steps=11,a=.06,b=.87,center=[.17,0,.015],base=(.103,.10)),
}
FIT_LOG={}; objects=[]

def ring_fit(name,axis,center,v,rx,rz):
    # Axis-specific physical dimensions; filter cloud in local slice AND body region.
    sample=points[np.abs(points[:,{'x':0,'y':1}[axis]]-v)<.075]
    cx,cy,cz=center
    if name=='torso':sample=sample[(np.abs(sample[:,0])<.36)&(np.abs(sample[:,2])<.36)]
    elif name=='head':sample=sample[(np.abs(sample[:,0])<.21)&(np.abs(sample[:,2])<.21)]
    elif name.endswith('leg'):
        sample=sample[(np.abs(sample[:,0]-cx)<.20)&(np.abs(sample[:,2]-cz)<.28)]
    else:sample=sample[(np.abs(sample[:,1]-cy)<.17)&(np.abs(sample[:,2]-cz)<.22)]
    inferred=len(sample)<24
    if not inferred:
        if axis=='y':f=np.percentile(np.abs(sample[:,0]-cx),85);h=np.percentile(np.abs(sample[:,2]-cz),85)
        else:f=np.percentile(np.abs(sample[:,1]-cy),85);h=np.percentile(np.abs(sample[:,2]-cz),85)
        # Strong prior avoids flattening when only silhouette rays are available.
        rx=max(rx*.70,min(rx*1.30,rx*.45+float(f)*.55))
        rz=max(rz*.70,min(rz*1.30,rz*.45+float(h)*.55))
    FIT_LOG.setdefault(name,[]).append({'position_m':round(float(v),4),'sample_count':len(sample),'prior_only':inferred,'radius_a':round(rx,4),'radius_b':round(rz,4)})
    return rx,rz

def create_section(name,s):
    pts=[];faces=[];a=s['a'];b=s['b'];count=s['steps'];axis=s['axis'];base=s['base'];center=s['center']
    for j in range(count):
        t=j/(count-1);v=a+(b-a)*t
        if name=='torso':r1=base[0]*(.86+.2*math.sin(math.pi*t)+.09*t);r2=base[1]*(.9+.12*math.sin(math.pi*t))
        elif name=='head':r1=base[0]*(.38+.7*math.sin(math.pi*t)**.65);r2=base[1]*(.55+.54*math.sin(math.pi*t)**.65)
        elif name.endswith('leg'):r1=base[0]*(1.05-.12*t);r2=base[1]*(1.14-.12*t)
        else:r1=base[0]*(.8+.25*math.sin(math.pi*t));r2=base[1]*(.8+.2*math.sin(math.pi*t))
        r1,r2=ring_fit(name,axis,center,v,r1,r2)
        for k in range(8):
            theta=math.tau*k/8;u=math.cos(theta);w=math.sin(theta)
            if axis=='y':pt=(center[0]+u*r1,v,center[2]+w*r2)
            else:pt=(v,center[1]+u*r1,center[2]+w*r2)
            pts.append(pt)
    for j in range(count-1):
        for k in range(8):
            kn=(k+1)%8;faces.append((8*j+k,8*j+kn,8*(j+1)+kn,8*(j+1)+k))
    # Eight-sided flat cap tessellated with three TRUE quads, no degenerate quads.
    caps=[(0,1,2,3),(0,3,4,7),(4,5,6,7)]
    faces.extend(tuple(reversed(f)) for f in caps)
    faces.extend(tuple(8*(count-1)+q for q in f) for f in caps)
    me=bpy.data.meshes.new(name+'-cloud-fitted-quads');me.from_pydata(pts,[],faces);me.update()
    obj=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(obj)
    for poly in me.polygons:poly.use_smooth=True
    return obj

for name,recipe in sections.items():objects.append(create_section(name,recipe))
# Join the CLOSED fitted parts and remove overlaps using a voxel union, then TRUE all-quad retopology.
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
body=bpy.context.object;body.name='StoneBuilder_Body_1000quads'
# Recalculate each shell's outward normals before the volume union.
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free();body.data.update()
body.data.remesh_voxel_size=.025
bpy.ops.object.voxel_remesh()
# Blender native Quadriflow reconstructs a connected, deformation-friendly quad surface.
# If unavailable / non-quad / >988 budget, STOP rather than ship a fraudulent model.
bpy.ops.object.quadriflow_remesh(mode='FACES',target_faces=880,seed=2,use_preserve_sharp=False,use_preserve_boundary=False)
if not 150<=len(body.data.polygons)<=988:raise RuntimeError('Quad retopo out of budget: '+str(len(body.data.polygons)))
if any(len(p.vertices)!=4 for p in body.data.polygons):raise RuntimeError('Non-quad face in source .blend')

bm=bmesh.new();bm.from_mesh(body.data)
if any(not edge.is_manifold for edge in bm.edges):raise RuntimeError('Body is not closed 2-manifold')
seen=set();parts=0
for vert in bm.verts:
    if vert in seen:continue
    parts+=1;stack=[vert];seen.add(vert)
    while stack:
        for edge in stack.pop().link_edges:
            other=edge.other_vert(vert)
            if other not in seen:seen.add(other);stack.append(other)
bm.free()
if parts!=1:raise RuntimeError('Main body disconnected: '+str(parts)+' islands')
for p in body.data.polygons:p.use_smooth=True
# Level 2: vertex color sampled from ACTUAL registered reference images, not arbitrary paint.
# Back-facing and occluded colors are assumptions, flagged in the report.
tex=W/'texture_sources.npz'
if not tex.exists():raise RuntimeError('No verified reference-color data')
cal=json.loads((W/'calibration.json').read_text())
with np.load(tex,allow_pickle=False) as imgs:
    arrays={name:imgs[name].copy() for name in cal['view_order']}
J=np.asarray(cal['projection_jacobians']);offset=np.asarray(cal['projection_offsets'])
attr=body.data.color_attributes.new(name='ReferenceColor',type='FLOAT_COLOR',domain='CORNER')
import collections
color_audit=collections.Counter()
for polygon in body.data.polygons:
    n=polygon.normal
    direction='top' if n.z is not None and n.y>.45 and 'top' in arrays else ('right' if n.x>.48 and 'right' in arrays else 'front')
    if n.z < -.42:color_audit['inferred_back_color']+=len(polygon.loop_indices)
    for loop_index in polygon.loop_indices:
        vi=body.data.loops[loop_index].vertex_index
        vert=body.data.vertices[vi].co
        vix=cal['view_order'].index(direction)
        px=J[vix]@np.asarray(vert)+offset[vix]
        arr=arrays[direction];u=int(round(px[0]));v=int(round(px[1]))
        if 0<=v<arr.shape[0] and 0<=u<arr.shape[1]:
            rgb=arr[v,u].astype(float)/255.;color_audit['sampled_reference_pixels']+=1
        else:
            rgb=np.asarray([.6,.47,.34]);color_audit['registration_fallback_pixels']+=1
        attr.data[loop_index].color=(float(rgb[0]),float(rgb[1]),float(rgb[2]),1.0)
mat=bpy.data.materials.new('ImageGuidedStoneAgeClothSkin');mat.use_nodes=True
bsdf=mat.node_tree.nodes.get('Principled BSDF')
node=mat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='ReferenceColor'
mat.node_tree.links.new(node.outputs['Color'],bsdf.inputs['Base Color'])
body.data.materials.clear();body.data.materials.append(mat)

# Rig in actual neutral T-pose, right-handed with +X on character right.
rigdat=bpy.data.armatures.new('Builder_Skeleton');rig=bpy.data.objects.new('StoneBuilder_Armature',rigdat)
bpy.context.collection.objects.link(rig);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
def addbone(name,head,tail,parent=None):
    bone=rigdat.edit_bones.new(name);bone.head=head;bone.tail=tail
    if parent:bone.parent=rigdat.edit_bones[parent];bone.use_connect=False
    return bone
addbone('Root',(0,.04,0),(0,.77,0))
addbone('Pelvis',(0,.77,0),(0,.93,0),'Root')
addbone('Spine',(0,.93,0),(0,1.20,0),'Pelvis')
addbone('Chest',(0,1.20,0),(0,1.45,0),'Spine')
addbone('Neck',(0,1.45,0),(0,1.54,0),'Chest')
addbone('Head',(0,1.54,0),(0,1.78,0),'Neck')
for side,prefix in [(-1,'L'),(1,'R')]:
    addbone(prefix+'_UpperArm',(side*.24,1.37,0),(side*.59,1.37,0),'Chest')
    addbone(prefix+'_ForeArm',(side*.59,1.37,0),(side*.92,1.37,0),prefix+'_UpperArm')
    addbone(prefix+'_Hand',(side*.92,1.37,0),(side*1.04,1.37,0),prefix+'_ForeArm')
    addbone(prefix+'_Thigh',(side*.17,.77,0),(side*.17,.43,0),'Pelvis')
    addbone(prefix+'_Shin',(side*.17,.43,0),(side*.17,.14,0),prefix+'_Thigh')
    addbone(prefix+'_Foot',(side*.17,.14,0),(side*.17,.09,.16),prefix+'_Shin')
bpy.ops.object.mode_set(mode='OBJECT')
for b in rig.pose.bones:b.rotation_mode='XYZ'

# Assign gradual skin blending from anatomical regions, not Blender's heuristic 'automatic weights'.
for bone in rig.data.bones:body.vertex_groups.new(name=bone.name)
for v in body.data.vertices:
    x,y,z=v.co;ax=abs(x);side='L' if x<0 else 'R';w={}
    if y>1.48 and ax<.26:w={'Head':.92,'Neck':.08}
    elif 1.16<y<1.61 and ax>.31:
        if ax>.88:w={side+'_Hand':.9,side+'_ForeArm':.1}
        elif ax>.6:
            share=min(1,max(0,(ax-.58)/.12));w={side+'_UpperArm':1-share*.7,side+'_ForeArm':share*.7}
        else:w={side+'_UpperArm':.87,'Chest':.13}
    elif y<.81 and ax>.07:
        if y<.17:w={side+'_Foot':.85,side+'_Shin':.15}
        elif y<.42:w={side+'_Shin':.9,side+'_Thigh':.1}
        else:w={side+'_Thigh':.88,'Pelvis':.12}
    elif y>1.22:w={'Chest':.88,'Spine':.12}
    elif y>.94:w={'Spine':.88,'Pelvis':.12}
    else:w={'Pelvis':1.}
    total=sum(w.values())
    for name,val in w.items():body.vertex_groups[name].add([v.index],val/total,'REPLACE')
mod=body.modifiers.new('Armature_Skin','ARMATURE');mod.object=rig;body.parent=rig

# 12 accessory QUADS: haft and flint adze head, separate rigid mesh, bound to the right hand.
# Kept separate as a prop and explicitly counted in WHOLE-MODEL budget.
def cube(v,f,center,half):
    base=len(v);x,y,z=center;hx,hy,hz=half
    v.extend([(x-hx,y-hy,z-hz),(x+hx,y-hy,z-hz),(x+hx,y+hy,z-hz),(x-hx,y+hy,z-hz),
              (x-hx,y-hy,z+hz),(x+hx,y-hy,z+hz),(x+hx,y+hy,z+hz),(x-hx,y+hy,z+hz)])
    f.extend([tuple(base+i for i in q) for q in [(0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(0,1,5,4),(3,7,6,2)]])
v=[];f=[];cube(v,f,(1.02,1.29,.045),(.025,.26,.032));cube(v,f,(1.02,1.47,.045),(.15,.055,.055))
me=bpy.data.meshes.new('Adze_12quads');me.from_pydata(v,[],f);me.update()
tool=bpy.data.objects.new('StoneFlintAdze',me);bpy.context.collection.objects.link(tool)
tool.vertex_groups.new(name='R_Hand').add(list(range(len(v))),1,'REPLACE')
tool.modifiers.new('Tool_Skin','ARMATURE').object=rig;tool.parent=rig
for matname,shade in [('ToolWood',(.39,.26,.14,1)),('ToolFlint',(.43,.46,.42,1))]:
    material=bpy.data.materials.new(matname);material.diffuse_color=shade
    tool.data.materials.append(material)
for poly in tool.data.polygons:poly.material_index=0 if poly.index<6 else 1
source_quads=sum(len(o.data.polygons) for o in [body,tool]);assert source_quads<=1000,source_quads
if any(len(p.vertices)!=4 for o in [body,tool] for p in o.data.polygons):raise RuntimeError('Nonquad in scene')

# Three distinct looping animations. Bake actions to NLA for glTF.
sc=bpy.context.scene;sc.render.fps=24;sc.frame_start=1;sc.frame_end=49

def animate_action(name,poses):
    action=bpy.data.actions.new(name);rig.animation_data_create();rig.animation_data.action=action
    for fr,values in poses:
        sc.frame_set(fr)
        for bone in rig.pose.bones:bone.rotation_euler=(0,0,0)
        for bone,xyz in values.items():rig.pose.bones[bone].rotation_euler=xyz
        for bone in rig.pose.bones:bone.keyframe_insert(data_path='rotation_euler',frame=fr,group=bone.name)
    rig.animation_data.action=None
    track=rig.animation_data.nla_tracks.new();track.name=name
    strip=track.strips.new(name,1,action);strip.action_frame_start=1;strip.action_frame_end=49
    track.mute=False
    return action

animate_action('Idle_Loop',[(1,{}),(25,{'Chest':(.025,0,.017),'Head':(-.01,0,0)}),(49,{})])
walk=[]
for fr in [1,7,13,19,25,31,37,43,49]:
    phase=(fr-1)/48*math.tau*2
    swing=.52*math.sin(phase)
    walk.append((fr,{'L_Thigh':(swing,0,0),'R_Thigh':(-swing,0,0),'L_Shin':(max(0,-swing)*.45,0,0),
                     'R_Shin':(max(0,swing)*.45,0,0),'L_UpperArm':(-.25*swing,0,0),'R_UpperArm':(.25*swing,0,0)}))
animate_action('Walk_Loop',walk)
build=[]
for fr in [1,7,13,19,25,31,37,43,49]:
    stroke=(1-math.cos((fr-1)/48*math.tau*2))/2
    build.append((fr,{'R_UpperArm':(-.2-1.3*stroke,0,.08),'R_ForeArm':(-.12-.35*stroke,0,0),
                      'L_UpperArm':(-.4,0,0),'Chest':(.08*stroke,0,0)}))
animate_action('Build_Loop',build)

# Save exact all-quad authoring source; GLB will triangulate by design.
sc.frame_set(1)
for b in rig.pose.bones:b.rotation_euler=(0,0,0)
bpy.ops.wm.save_as_mainfile(filepath=str(W/'StoneBuilder_1000_2.blend'))

# Illuminated previews from the ACTUAL mesh (not reference pictures).
world=bpy.data.worlds.new('PreviewWorld') if not sc.world else sc.world
sc.world=world;sc.world.color=(.22,.24,.27)
for i,(pos,power) in enumerate([((3,5,4),600),((-4,3,-2),400)]):
    ld=bpy.data.lights.new('PreviewLight'+str(i),'AREA');ld.energy=power
    lamp=bpy.data.objects.new('PreviewLight'+str(i),ld);bpy.context.collection.objects.link(lamp);lamp.location=pos
    lamp.rotation_euler=(Vector((0,1,0))-lamp.location).to_track_quat('-Z','Y').to_euler()
# Rendered controls from the ACTUAL mesh (not reference pictures).
def make_preview(label,eye):
    camdat=bpy.data.cameras.new('preview_'+label);cam=bpy.data.objects.new('Camera_'+label,camdat)
    bpy.context.collection.objects.link(cam);cam.location=eye
    direction=Vector((0,1,0))-cam.location;cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
    camdat.type='ORTHO';camdat.ortho_scale=2.95;sc.camera=cam
    sc.render.engine='BLENDER_WORKBENCH'
    try:sc.display.shading.color_type='VERTEX'
    except (ValueError,TypeError):sc.display.shading.color_type='MATERIAL';sc.render.resolution_x=480;sc.render.resolution_y=480;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.render.filepath=str(W/('preview_'+label+'.png'))
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam,do_unlink=True)
# Visual inspection still must be performed by reviewer.
for label,eye in [('front',(0,1.17,4.0)),('side',(4.0,1.17,0)),('top',(0,4.3,0)),('oblique',(2.6,2.5,3.2))]:make_preview(label,eye)

bpy.ops.object.select_all(action='DESELECT')
for obj in (body,tool,rig):obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(W/'StoneBuilder_1000_2.glb'),export_format='GLB',use_selection=True,
    export_animations=True,export_nla_strips=True,export_skins=True)
(W/'blender_validation.json').write_text(json.dumps({'source_quads_total':source_quads,'body_quads':len(body.data.polygons),
    'prop_quads':len(tool.data.polygons),'body_connected_components':parts,'all_source_faces_are_quads':True,
    'rig_bones':len(rig.data.bones),'animation_names':['Idle_Loop','Walk_Loop','Build_Loop'],
    'cloud_fitting':FIT_LOG,'reference_color_audit':dict(color_audit),'visual_review':'PENDING'},indent=2))
print('Finished export',source_quads,'quads; visual review still pending')
