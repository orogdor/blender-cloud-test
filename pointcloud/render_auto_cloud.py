"""Run only in Blender background mode; GitHub Actions entrypoint."""
import bpy, bmesh, json, math, runpy, shutil
from pathlib import Path
from mathutils import Vector

source=Path(__file__).with_name('auto_punktipilv_mesh.py')
module=runpy.run_path(str(source),run_name='car_library')
out=Path('output/auto_punktipilv');out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
car=module['run_blender']()
cloud=bpy.data.objects['01_Punktipilv']
bm=bmesh.new();bm.from_mesh(car.data)
assert all(e.is_manifold for e in bm.edges), 'Nonmanifold edges'
assert all(v.is_manifold for v in bm.verts), 'Nonmanifold vertex'
bm.free()
report=module['validate_geometry']([tuple(v.co) for v in car.data.vertices],
                                 [tuple(p.vertices) for p in car.data.polygons])
(out/'kontroll.json').write_text(json.dumps(report,indent=2))
text=bpy.data.texts.new('auto_punktipilv_mesh.py');text.write(source.read_text())
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=24
scene.cycles.use_denoising=False  # Ubuntu Blender has no OpenImageDenoiser
scene.render.resolution_x=1000;scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.18,.21,.26,1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.7
def aim(ob,position): ob.rotation_euler=(Vector(position)-ob.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(-6.4,-6.2,3.7))
camera=bpy.context.object;aim(camera,(0,0,.82));camera.data.type='ORTHO';camera.data.ortho_scale=5.7;scene.camera=camera
for position,power,size in [((-3,-4,6),1100,5),((3,2,5),900,4),((1,-1,5),500,3)]:
 bpy.ops.object.light_add(type='AREA',location=position)
 light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;aim(light,(0,0,.6))
car.hide_render=False;cloud.hide_render=True
scene.render.filepath=str(out/'mesh.png');bpy.ops.render.render(write_still=True)
cloud.hide_render=False;cloud.hide_set(False);car.hide_render=True
scene.render.filepath=str(out/'punktipilv.png');bpy.ops.render.render(write_still=True)
cloud.hide_render=True;cloud.hide_set(True);car.hide_render=False;car.hide_set(False)
for ob in bpy.context.selected_objects: ob.select_set(False)
car.select_set(True);bpy.context.view_layer.objects.active=car
bpy.ops.export_scene.gltf(filepath=str(out/'auto_suletud.glb'),export_format='GLB',use_selection=True)
for area in bpy.context.screen.areas:
 if area.type=='VIEW_3D':
  area.spaces.active.region_3d.view_distance=6
  area.spaces.active.region_3d.view_location=Vector((0,0,.8))
  area.spaces.active.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
scene.render.filepath=str(out/'mesh.png')
bpy.ops.wm.save_as_mainfile(filepath=str((out/'auto_punktipilv_mesh.blend').resolve()))
shutil.copyfile(source,out/source.name)
print('FINAL_VALIDATION',json.dumps(report))
