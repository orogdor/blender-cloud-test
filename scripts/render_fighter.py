"""Render reference images for the generated sword fighter (.blend)."""
import bpy,os
from mathutils import Vector
BASE=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
OUT=os.path.join(BASE,"fighter_output")
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT,"sword_fighter.blend"))
scene=bpy.context.scene
rig=bpy.data.objects.get("FighterRig")
if rig is None:raise RuntimeError("Missing FighterRig")
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=14
scene.render.threads_mode="FIXED"
scene.render.threads=2
for vl in scene.view_layers:
    vl.cycles.use_denoising=False
world=scene.world or bpy.data.worlds.new("Preview world")
scene.world=world
world.use_nodes=True
world.node_tree.nodes.get("Background").inputs["Color"].default_value=(0.42,0.46,0.54,1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value=0.9
def add_light(name,pos,power,size):
    bpy.ops.object.light_add(type="AREA",location=pos)
    light=bpy.context.object;light.name=name;light.data.energy=power
    light.data.shape="DISK";light.data.size=size
    light.rotation_euler=(Vector((0,0,1.1))-light.location).to_track_quat("-Z","Y").to_euler()
add_light("Key",(2,-4,4),470,4)
add_light("Fill",(-3,-2,3),300,4)
add_light("Rim",(0,3,4),580,3)
scene.render.image_settings.file_format="PNG"
scene.render.resolution_x=560
scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.view_settings.view_transform="Standard"
bpy.ops.object.camera_add(location=(3.7,-6.4,2.6))
cam=bpy.context.object;cam.name="Reference preview camera";cam.data.type="ORTHO";cam.data.ortho_scale=2.9;scene.camera=cam
def render(name,point,frame=1):
    cam.location=point
    cam.rotation_euler=(Vector((0,0,1.11))-cam.location).to_track_quat("-Z","Y").to_euler()
    scene.frame_set(frame)
    scene.render.filepath=os.path.join(OUT,name)
    bpy.ops.render.render(write_still=True)
if rig.animation_data:
    for track in rig.animation_data.nla_tracks:track.mute=True
rig.data.pose_position="REST"
render("preview_front.png",(3.1,-6.8,2.3))
render("preview_side.png",(6.5,-2.0,2.2))
rig.data.pose_position="POSE"
if rig.animation_data:
    for track in rig.animation_data.nla_tracks:track.mute=(track.name!="SwordSlash")
render("preview_sword_slash.png",(3.1,-6.8,2.3),10)
for name in ("preview_front.png","preview_side.png","preview_sword_slash.png"):
    assert os.path.getsize(os.path.join(OUT,name))>5000,name
print("BLENDER_PREVIEW_SUCCESS")
