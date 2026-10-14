"""Render reference images for the generated sword fighter (.blend)."""
import bpy,os
from mathutils import Vector
BASE=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
OUT=os.path.join(BASE,"fighter_output")
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT,"sword_fighter.blend"))
scene=bpy.context.scene
rig=bpy.data.objects.get("FighterRig")
if rig is None:raise RuntimeError("Missing FighterRig")
scene.render.engine="BLENDER_WORKBENCH"
scene.display.shading.color_type="MATERIAL"
scene.display.shading.light="STUDIO"
scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True
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
