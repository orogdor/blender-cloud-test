"""Build exact 5000-quads car from the separately saved, checked cloud reconstruction."""
from pathlib import Path
import bpy,bmesh,json,math,sys,os
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output';REF=ROOT/'references'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
source=json.loads((OUT/'05_quad_surface.json').read_text());cal=json.loads((REF/'calibration.json').read_text())
img=bpy.data.images.load(str(REF/'4319.png'));img.pack();J=cal['projection_jacobians'];B=cal['projection_offsets'];W,H=cal['source_pixels']
def project(p,k):return ((sum(p[a]*J[k][0][a] for a in range(3))+B[k][0])/W,1-(sum(p[a]*J[k][1][a] for a in range(3))+B[k][1])/H)
def material(name,color,metal,rough,texture=False):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;bs=n.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
 if texture:
  t=n.new('ShaderNodeTexImage');t.image=img;t.interpolation='Linear';m.node_tree.links.new(t.outputs['Color'],bs.inputs['Base Color'])
 return m
mats={
 'paint':material('Silver_paint_reference',(0.54,.56,.58),.15,.48,True),
 'glass':material('Smoked_glass',(.055,.075,.09),.18,.2,False),
 'solid_paint':material('Mirror_silver',(.46,.49,.53),.5,.29,False),
 'rubber':material('Rubber',(.012,.014,.017),.0,.82),
 'rim':material('Alloy_rim_reference',(.4,.42,.45),.72,.28,True),
 'chrome':material('Brushed_trim',(.30,.33,.36),.75,.25),
 'plate':material('Blank_plate',(.014,.016,.019),.05,.45),
 'front_photo':material('Grille_and_fog_reference',(.08,.09,.10),.32,.35,True),
 'underbody':material('Underbody',(.025,.027,.031),.1,.8)
}
assets=[];body_parts=[]
def np_interp(x,keys,values):
 for i in range(len(keys)-1):
  if keys[i]<=x<=keys[i+1]:
   t=(x-keys[i])/(keys[i+1]-keys[i]);return values[i]*(1-t)+values[i+1]*t
 return values[0] if x<keys[0] else values[-1]
for part in source['objects']:
 me=bpy.data.meshes.new(part['name']);me.from_pydata(part['vertices'],[],part['faces']);me.update();ob=bpy.data.objects.new(part['name'],me);bpy.context.collection.objects.link(ob);ob['point_cloud_source']='04_point_cloud.npz';ob['source_kind']=part['kind']
 for material_ in mats.values():me.materials.append(material_)
 names=list(mats)
 for poly,mat in zip(me.polygons,part['materials']):poly.material_index=names.index(mat)
 if part['kind'] in ['body','cap']:body_parts.append(ob)
 assets.append((ob,part))
# Weld shared cap/loft boundary samples, then establish coherent outward normals.
bpy.ops.object.select_all(action='DESELECT')
for ob in body_parts:ob.select_set(True)
bpy.context.view_layer.objects.active=body_parts[0];bpy.ops.object.join();body_ob=bpy.context.object;body_ob.name='Auto_kere_3400_quads'
assets=[(ob,p) for ob,p in assets if p['kind'] not in ['body','cap']]+[(body_ob,{'kind':'body'})]
for ob,p in assets:
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000005);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();ob.data.update()
 uv=ob.data.uv_layers.new(name='Reference_projection')
 for poly in ob.data.polygons:
  center=poly.center;n=poly.normal;mat=ob.data.materials[poly.material_index].name
  if p['kind']=='wheel':view=1
  elif p['kind']=='panel':view=p['view']
  elif abs(n.x)>.62 and abs(n.x)>abs(n.z)*.85:view=2 if n.x<0 else 3
  elif abs(n.z)>.58 and center.z>.85:view=0
  else:view=1
  if p['kind']=='body' and abs(center.y)>.43 and center.z>.94 and -1.12<center.x<1.82:view=1
  for loop in poly.loop_indices:
   point=ob.data.vertices[ob.data.loops[loop].vertex_index].co.copy()
   if p['kind']=='wheel':
    # Same visible wheel reference on both sides; source axle centres differ.
    wx=[(180-14)/980*4.56-2.28,(770-14)/980*4.56-2.28][p['axle']]
    source_wx=[(180-14)/980*4.56-2.28,(770-14)/980*4.56-2.28][p['axle']]
    point.x=source_wx+point.x-wx
   uv.data[loop].uv=project(point,view)
  if p['kind']=='body':
   if center.z<.31:poly.material_index=names.index('underbody')
  if p['kind']=='mirror':poly.material_index=names.index('solid_paint')
  poly.use_smooth=p['kind'] not in ['panel']
 if p['kind']=='mirror':
  bevel=ob.modifiers.new('Shading_normals','WEIGHTED_NORMAL');bevel.keep_sharp=True

def mesh_report(ob):
 bm=bmesh.new();bm.from_mesh(ob.data);r={'name':ob.name,'vertices':len(bm.verts),'quads':sum(len(f.verts)==4 for f in bm.faces),'faces':len(bm.faces),'triangles':sum(len(f.verts)-2 for f in bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_nonboundary_edges':sum(not e.is_manifold and not e.is_boundary for e in bm.edges),'volume':abs(bm.calc_volume(signed=True))};bm.free();return r
reports=[mesh_report(ob) for ob,p in assets];assert sum(r['quads'] for r in reports)==5000,reports;assert all(r['quads']==r['faces'] for r in reports)
assert next(r for r in reports if r['name']==body_ob.name)['boundary_edges']==0,reports
points=[ob.matrix_world@v.co for ob,p in assets for v in ob.data.vertices];lo=[min(v[i] for v in points) for i in range(3)];hi=[max(v[i] for v in points) for i in range(3)]
report={'test':'Mudelitehas kolm suunda / 5000 nelinurka','quad_faces_total':5000,'triangles_export_expected':10000,'objects':reports,'bounds_min_m':lo,'bounds_max_m':hi,'dimensions_m':[hi[i]-lo[i] for i in range(3)],'quad_count_includes_all_details':True,'point_cloud_before_mesh':True,'source_image_texture':True,'geometry_animation':False,'limits':['depth is inferred from silhouettes and reviewed profiles','same side reference mirrored for opposite side','texture contains baked source lighting','small decorative patches intentionally have boundary edges','not a manufactured dimension-accurate CAD model']}
(OUT/'validation.json').write_text(json.dumps(report,indent=2))
bpy.ops.object.select_all(action='DESELECT')
for ob,p in assets:ob.select_set(True)
bpy.context.view_layer.objects.active=body_ob
bpy.ops.export_scene.gltf(filepath=str(OUT/'Auto_5000_3vaate_test.glb'),export_format='GLB',use_selection=True,export_animations=False,export_apply=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=1000;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.view_settings.view_transform='AgX';scene.world.color=(.18,.18,.18)
target=Vector((0,0,.65))
def aim(ob):ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(-5.8,-7.2,3.4));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=5.55;aim(cam);scene.camera=cam
for loc,power,size in [((-3,-4,6),1000,5),((3,1,5),1200,4),((0,5,3),650,3)]:
 bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;aim(light)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.012));ground=bpy.context.object;ground.name='Studio_ground_not_exported';ground.data.materials.append(material('Studio',(.105,.12,.14),0,.85))
scene.render.filepath=str(OUT/'Auto_5000_eelvaade.png');bpy.ops.render.render(write_still=True)
# Orthographic proof renders; lighting and camera are presentation only.
views=[('side',(0,-8,.73),5.2),('top',(0,0,9),5.2),('front',(-8,0,.73),2.6),('rear',(8,0,.73),2.6)]
scene.render.resolution_x=640;scene.render.resolution_y=420;scene.cycles.samples=16
for name,loc,scale in views:
 target=Vector((0,0,.73));cam.location=loc;aim(cam);cam.data.ortho_scale=scale
 if name=='top':cam.rotation_euler=(0,0,0)
 scene.render.filepath=str(OUT/f'Control_{name}.png');bpy.ops.render.render(write_still=True)
target=Vector((0,0,.65));cam.location=(-5.8,-7.2,3.4);aim(cam);cam.data.ortho_scale=5.55
scene.render.resolution_x=1000;scene.render.resolution_y=700
bpy.ops.object.select_all(action='DESELECT')
for ob,p in assets:ob.select_set(True)
bpy.context.view_layer.objects.active=body_ob
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Auto_5000_3vaate_test.blend'))
print('CAR_BUILD_COMPLETE',json.dumps(report),flush=True)

