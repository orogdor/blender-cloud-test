"""Blender: reference-shaped seated rabbit, connected mesh and point cloud.

Scripting > Open > Run Script. Or Blender --background --python this_file.py.
Shape is modelled from the five-view picture, not an exact image-grid extraction.
QuadriFlow creates the final topology; point cloud retains exactly its vertices.
Output: output/rabbit_reference/ (BLEND, GLB, PLY, PNG, checks).
"""
import bpy,bmesh,math,json,shutil
from pathlib import Path
from mathutils import Vector

OUT=Path('output/rabbit_reference');OUT.mkdir(parents=True,exist_ok=True)
TARGET_FACES=2400
VOXEL_SIZE=.025
parts=[]

def ellipsoid(name,location,scale,axis=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=24,location=location)
    ob=bpy.context.object;ob.name=name;ob.scale=scale
    if axis:ob.rotation_euler=Vector(axis).to_track_quat('Z','Y').to_euler()
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    parts.append(ob);return ob


def check(ob):
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bad_edges=sum(not e.is_manifold for e in bm.edges)
    bad_vertices=sum(not v.is_manifold for v in bm.verts)
    loose=sum(not v.link_faces for v in bm.verts)
    boundary=sum(e.is_boundary for e in bm.edges)
    todo=set(bm.verts);components=0
    while todo:
        stack=[todo.pop()];components+=1
        while stack:
            for edge in stack.pop().link_edges:
                for v in edge.verts:
                    if v in todo:todo.remove(v);stack.append(v)
    report={'vertices':len(bm.verts),'faces':len(bm.faces),'edges':len(bm.edges),
            'quads':sum(len(f.verts)==4 for f in bm.faces),
            'triangles':sum(len(f.verts)==3 for f in bm.faces),
            'other_polygons':sum(len(f.verts)>4 for f in bm.faces),
            'components':components,'boundary_edges':boundary,'nonmanifold_edges':bad_edges,
            'nonmanifold_vertices':bad_vertices,'loose_vertices':loose,
            'volume':round(bm.calc_volume(),6)}
    assert components==1 and not(bad_edges or bad_vertices or loose or boundary),report
    assert report['volume']>0,report
    bm.to_mesh(ob.data);bm.free();return report


def material(name,color,roughness=.6):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=color
    bsdf=m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=color
    bsdf.inputs['Roughness'].default_value=roughness
    return m


def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()


def build():
    # The script resets its working scene; keep another project in a separate file.
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    ellipsoid('Haunch_body',(0,.25,.77),(.50,.69,.66))
    ellipsoid('Chest',(0,-.28,1.03),(.36,.40,.61))
    ellipsoid('Neck',(0,-.46,1.47),(.27,.29,.40))
    ellipsoid('Head',(0,-.58,1.82),(.35,.36,.34))
    for sign in (-1,1):
        ellipsoid('Cheek',(sign*.12,-.87,1.69),(.19,.23,.17))
        ellipsoid('Foreleg',(sign*.18,-.52,.50),(.115,.17,.43),axis=(0,.10,1))
        ellipsoid('Front_paw',(sign*.18,-.70,.105),(.145,.25,.12))
        ellipsoid('Hind_haunch',(sign*.42,.29,.48),(.29,.39,.45))
        ellipsoid('Hind_paw',(sign*.42,-.02,.115),(.225,.49,.13))
        # Tiny connected toe contours help paws read like the reference.
        for offset in (-.07,0,.07):
            ellipsoid('Front_toe',(sign*.18+offset,-.875,.095),(.052,.077,.065))
        # Ears form a gentle V in the front view and share their roots with head.
        root=Vector((sign*.205,-.47,2.055))
        tip=Vector((sign*.40,-.36,3.04))
        middle=(root+tip)/2
        ellipsoid('Ear',middle,(.125,.072,.575),axis=tip-root)
        ellipsoid('Ear_root',root,(.15,.13,.17))
    ellipsoid('Nose',(0,-1.056,1.745),(.066,.068,.052))
    ellipsoid('Tail',(0,.93,.43),(.225,.235,.27),axis=(0,.25,1))
    bpy.ops.object.select_all(action='DESELECT')
    for ob in parts:ob.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
    rabbit=bpy.context.object;rabbit.name='02_Rabbit_Connected_Mesh'
    bpy.ops.object.transform_apply(location=True,rotation=False,scale=False)
    rem=rabbit.modifiers.new('Fuse_to_closed_surface','REMESH');rem.mode='VOXEL';rem.voxel_size=VOXEL_SIZE
    rem.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=rem.name)
    smooth=rabbit.modifiers.new('Relax_surface','SMOOTH');smooth.factor=.7;smooth.iterations=5
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    print('VOXEL_UNION_CHECK',check(rabbit),flush=True)
    # QuadriFlow is a retopology step, not a claim of exact photo grid recovery.
    print('QUADRIFLOW_START',TARGET_FACES,flush=True)
    bpy.ops.object.quadriflow_remesh(target_faces=TARGET_FACES,seed=0,
                                  use_preserve_sharp=False,use_preserve_boundary=False)
    report=check(rabbit);print('QUADRIFLOW_CHECK',report,flush=True)
    white=material('Ivory_mesh',(.76,.73,.67,1),.58)
    eyes=material('Eyes',(.025,.022,.018,1),.15)
    nose=material('Nose',(.16,.12,.11,1),.5)
    ear=material('Inner_ears',(.59,.56,.52,1),.7)
    wiremat=material('Topology_edges',(.022,.026,.03,1),.9)
    for m in (white,eyes,nose,ear,wiremat):rabbit.data.materials.append(m)
    for p in rabbit.data.polygons:
        x,y,z=p.center;p.use_smooth=True
        if ((abs(x)-.285)/.105)**2+((y+.795)/.095)**2+((z-1.92)/.105)**2<1:p.material_index=1
        elif abs(x)<.075 and y<-1.045 and 1.69<z<1.81:p.material_index=2
        elif z>2.2 and y<-.425+(z-2.2)*.12 and abs(abs(x)-(.23+(z-2.2)*.18))<.075:p.material_index=3
    # Exact vertex copy; point cloud is a separate preview object without faces.
    coordinates=[tuple(v.co) for v in rabbit.data.vertices]
    pcmesh=bpy.data.meshes.new('Rabbit_point_coordinates');pcmesh.from_pydata(coordinates,[],[]);pcmesh.update()
    cloud=bpy.data.objects.new('01_Rabbit_Point_Cloud',pcmesh);bpy.context.collection.objects.link(cloud)
    pointmat=material('Point_cloud_dots',(.15,.48,.76,1),.5)
    group=bpy.data.node_groups.new('Rabbit_point_preview','GeometryNodeTree')
    if hasattr(group,'interface'):
        group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
        group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    else:
        group.inputs.new('NodeSocketGeometry','Geometry');group.outputs.new('NodeSocketGeometry','Geometry')
    inp=group.nodes.new('NodeGroupInput');out=group.nodes.new('NodeGroupOutput')
    convert=group.nodes.new('GeometryNodeMeshToPoints');convert.mode='VERTICES'
    sphere=group.nodes.new('GeometryNodeMeshIcoSphere');sphere.inputs['Radius'].default_value=.007
    sphere.inputs['Subdivisions'].default_value=1
    setmat=group.nodes.new('GeometryNodeSetMaterial');setmat.inputs['Material'].default_value=pointmat
    inst=group.nodes.new('GeometryNodeInstanceOnPoints')
    group.links.new(inp.outputs['Geometry'],convert.inputs['Mesh'])
    group.links.new(sphere.outputs['Mesh'],setmat.inputs['Geometry'])
    group.links.new(setmat.outputs['Geometry'],inst.inputs['Instance'])
    group.links.new(convert.outputs['Points'],inst.inputs['Points'])
    group.links.new(inst.outputs['Instances'],out.inputs['Geometry'])
    mod=cloud.modifiers.new('Point_display','NODES');mod.node_group=group
    cloud.hide_render=True;cloud.hide_set(True)
    rabbit['validation']=json.dumps(report)
    rabbit['source']='Modelled from generated five-view rabbit image; retopology is inferred'
    cloud['source']='Exactly the same vertices as Rabbit_Connected_Mesh; no faces'
    (OUT/'kontroll.json').write_text(json.dumps(report,indent=2))
    with (OUT/'rabbit_point_cloud.ply').open('w') as f:
        f.write('ply\nformat ascii 1.0\nelement vertex '+str(len(coordinates))+'\nproperty float x\nproperty float y\nproperty float z\nend_header\n')
        for p in coordinates:f.write(' '.join(str(v) for v in p)+'\n')
    return rabbit,cloud


def render(rabbit,cloud):
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=False
    scene.render.resolution_x=960;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.world.use_nodes=True
    scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.15,.18,.22,1)
    scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.6
    bpy.ops.object.camera_add(location=(4,-6,3.2));camera=bpy.context.object
    aim(camera,(0,0,1.45));camera.data.type='ORTHO';camera.data.ortho_scale=3.85;scene.camera=camera
    for location,energy,size in [((3,-4,6),900,5),((-4,-1,4),650,4),((0,4,5),800,3)]:
        bpy.ops.object.light_add(type='AREA',location=location);ob=bpy.context.object
        ob.data.energy=energy;ob.data.shape='DISK';ob.data.size=size;aim(ob,(0,0,1.3))
    for kind in ('mesh','mesh_grid','point_cloud'):
        rabbit.hide_render=kind=='point_cloud';cloud.hide_render=kind!='point_cloud';cloud.hide_set(kind!='point_cloud')
        wire=None
        if kind=='mesh_grid':
            wire=rabbit.modifiers.new('Visible_topology','WIREFRAME');wire.thickness=.002
            wire.use_replace=False;wire.material_offset=4
        scene.render.filepath=str(OUT/(kind+'.png'));bpy.ops.render.render(write_still=True)
        if wire:rabbit.modifiers.remove(wire)
    # Four consistent orthographic checks from the same actual 3D mesh.
    rabbit.hide_render=False;cloud.hide_render=True;cloud.hide_set(True)
    wire=rabbit.modifiers.new('Topology_preview','WIREFRAME');wire.thickness=.0016;wire.use_replace=False;wire.material_offset=4
    for name,loc,target in [('front',(0,-7,1.5),(0,0,1.5)),('side',(7,0,1.5),(0,0,1.5)),
                            ('rear',(0,7,1.5),(0,0,1.5)),('top',(0,0,7),(0,0,0))]:
        camera.location=loc;aim(camera,target);camera.data.ortho_scale=3.7
        scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    rabbit.modifiers.remove(wire)
    camera.location=(4,-6,3.2);aim(camera,(0,0,1.45));camera.data.ortho_scale=3.85
    for ob in bpy.context.selected_objects:ob.select_set(False)
    rabbit.select_set(True);bpy.context.view_layer.objects.active=rabbit
    bpy.ops.export_scene.gltf(filepath=str(OUT/'rabbit.glb'),export_format='GLB',use_selection=True)
    source=Path(__file__)
    text=bpy.data.texts.new('create_rabbit.py');text.write(source.read_text());shutil.copyfile(source,OUT/source.name)
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=4.5
            area.spaces.active.region_3d.view_location=Vector((0,0,1.45))
            area.spaces.active.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
    bpy.ops.wm.save_as_mainfile(filepath=str((OUT/'rabbit_point_cloud_mesh.blend').resolve()))
    # Composite uses actual Blender renders, never generated decorative geometry.
    from PIL import Image,ImageDraw,ImageFont
    canvas=Image.new('RGB',(1920,860),(65,72,82));canvas.paste(Image.open(OUT/'point_cloud.png').convert('RGB'),(0,60))
    canvas.paste(Image.open(OUT/'mesh_grid.png').convert('RGB'),(960,60))
    draw=ImageDraw.Draw(canvas)
    try:font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',30)
    except OSError:font=ImageFont.load_default()
    draw.text((320,15),'PUNKTIPILV',font=font,fill='white');draw.text((1180,15),'ÜHENDATUD MESH',font=font,fill='white')
    canvas.save(OUT/'rabbit_point_cloud_and_mesh.png')


if __name__=='__main__':
    rabbit,cloud=build();render(rabbit,cloud)
