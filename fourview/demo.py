"""Run in Blender background to generate four synthetic orthographic masks and mesh.
No external AI images needed for this test; in real use images come from prompts.
"""
import os, sys, math, json
import bpy
import bmesh
from mathutils import Vector
from array import array

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
OUT=os.path.join(ROOT,'output','fourview')
os.makedirs(OUT,exist_ok=True)
sys.path.insert(0,os.path.join(ROOT,'fourview'))
import four_view_mesh as fvm

N=192

def make_silhouette(name, view):
    image=bpy.data.images.new(name,width=N,height=N,alpha=True,float_buffer=False)
    pixels=array('f')
    for row in range(N):
        z=(row+.5)/N
        # Test shape: sci-fi helmet/robot upper body, tapering shoulder silhouette.
        if z < .10: half=.13
        elif z < .44: half=.32
        elif z < .65: half=.40
        elif z < .76: half=.30
        elif z < .96: half=.20*math.sqrt(max(0,1-((z-.86)/.13)**2))
        else: half=0
        for col in range(N):
            u=(col+.5)/N-.5
            factor=1.0 if view in ('front','back') else .77
            inside=(abs(u) < half*factor) and .06 < z < .98
            pixels.extend((.1,.12,.16,1. if inside else 0.))
    image.pixels.foreach_set(pixels)
    path=os.path.join(OUT,view+'.png')
    image.filepath_raw=path
    image.file_format='PNG'
    image.save()
    bpy.data.images.remove(image)
    return path

paths={k:make_silhouette('mask_'+k,k) for k in ('front','back','left','right')}
obj=fvm.build_mesh(paths,resolution=48,width=1.45,depth=.85,height=2.0,smooth=True,name='FourView_HelmetBody')
# Exact editable quad surface + smooth modifier.
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active=obj
mat=bpy.data.materials.new('Brushed grey metal')
mat.diffuse_color=(.32,.44,.46,1)
mat.use_nodes=True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.32,.44,.46,1)
obj.data.materials.append(mat)
verts=len(obj.data.vertices);faces=len(obj.data.polygons)
assert verts > 100 and faces > 100,(verts,faces)
assert all(len(poly.vertices)==4 for poly in obj.data.polygons)
bm=bmesh.new()
bm.from_mesh(obj.data)
nonmanifold=sum(not edge.is_manifold for edge in bm.edges)
bm.free()
assert nonmanifold==0, 'Non-manifold edge count: %d' % nonmanifold


# Export while the mesh is selected.
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,'four_view_mesh.glb'),export_format='GLB',use_selection=True)
# A real rendered preview, to inspect model form before importing into a game.
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=12
for layer in scene.view_layers:
    layer.cycles.use_denoising=False
scene.render.resolution_x=540
scene.render.resolution_y=540
scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG'
world=bpy.data.worlds.new('Four-view world')
world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
scene.world=world
bpy.ops.object.camera_add(location=(3.2,-4,2.7))
cam=bpy.context.object
cam.rotation_euler=(Vector((0,0,1.1))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO'
cam.data.ortho_scale=3.1
scene.camera=cam
bpy.ops.object.light_add(type='AREA',location=(2,-3,4))
lamp=bpy.context.object
lamp.data.energy=600
lamp.data.size=4
lamp.rotation_euler=(Vector((0,0,1.0))-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=os.path.join(OUT,'preview.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'four_view_mesh.blend'))
with open(os.path.join(OUT,'stats.json'),'w') as fp:
    json.dump({'blender_version':bpy.app.version_string,'vertices':verts,'quads':faces,
               'silhouettes':list(paths.keys()),'volume_voxels':int(obj['occupied_voxels']), 'nonmanifold_edges':nonmanifold},fp,indent=2)
print('FOUR_VIEW_MESH_SUCCESS',verts,faces)