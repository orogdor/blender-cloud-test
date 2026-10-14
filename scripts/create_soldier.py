"""Headless Blender test: procedural sci-fi soldier + GLB + two PNGs.
Run: blender -b --factory-startup --python-exit-code 1 --python scripts/create_soldier.py
"""
import bpy, math, json, os
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "output")
os.makedirs(OUT, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
parts = []

def mat(name, rgb, metal=0, rough=.7):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*rgb,1)
    m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*rgb,1)
    p.inputs["Metallic"].default_value=metal
    p.inputs["Roughness"].default_value=rough
    return m

uniform=mat("Olive textile",(.21,.27,.18))
armor=mat("Armor graphite",(.20,.25,.27),.48)
accent=mat("Armor sage",(.40,.44,.35),.25)
dark=mat("Black rubber",(.065,.075,.075))
steel=mat("Gun steel",(.12,.14,.16),.78,.32)
skin=mat("Human skin",(.55,.39,.29))
strap=mat("Canvas straps",(.33,.29,.19))
glass=mat("Visor glass",(.045,.22,.28),.6,.24)

def tag(o,name,m):
    o.name=name
    o.data.materials.append(m)
    parts.append(o)
    return o
def cube(name, pos, dims, m, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pos)
    o=tag(bpy.context.object,name,m)
    o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=o.modifiers.new("Edge bevel","BEVEL")
        mod.width=bevel
        mod.segments=2
        # Omit weighted normal modifier for compatibility with stock Ubuntu Blender.
    return o
def ellipsoid(name,pos,scale,m,detail=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=detail,radius=1,location=pos)
    o=tag(bpy.context.object,name,m)
    o.scale=scale
    return o
def segment(name,a,b,width,depth,m):
    a,b=Vector(a),Vector(b)
    o=cube(name,(a+b)*.5,(width,depth,(b-a).length),m,.016)
    o.rotation_euler=(b-a).to_track_quat("Z","Y").to_euler()
    return o
def barrel(name,pos,radius,length,m):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=radius,depth=length,location=pos)
    o=tag(bpy.context.object,name,m)
    o.rotation_euler=(math.pi/2,0,0)
    return o

# Up is +Z in Blender, forward is -Y. Blender GLB export converts this for Three.js.
cube("Torso jacket",(0,0,1.71),(.69,.37,.78),uniform,.10)
cube("Chest armor",(0,-.223,1.86),(.61,.13,.53),armor,.045)
cube("Center plate",(0,-.305,1.86),(.20,.024,.43),accent,.012)
cube("Abdomen armor",(0,-.22,1.48),(.48,.12,.21),armor,.025)
cube("Combat pants waist",(0,0,1.31),(.55,.33,.35),uniform,.055)
cube("Utility belt",(0,-.04,1.38),(.65,.37,.085),dark,.012)
cube("Neck",(0,-.005,2.27),(.19,.20,.17),skin,.025)
cube("Collar",(0,-.01,2.24),(.42,.33,.105),dark,.024)
ellipsoid("Head",(0,-.025,2.48),(.215,.21,.26),skin,2)
ellipsoid("Helmet",(0,.025,2.62),(.265,.25,.19),armor,2)
cube("Helmet visor",(0,-.227,2.53),(.36,.06,.10),glass,.017)
cube("Helmet face guard",(0,-.233,2.45),(.092,.06,.14),armor,.012)
for sign, side in [(-1,"right"),(1,"left")]:
    x=sign*.19
    ellipsoid(side+" hip",(x,0,1.23),(.18,.18,.16),dark,1)
    segment(side+" thigh",(x,0,1.22),(x*1.08,-.025,.82),.285,.29,uniform)
    cube(side+" knee pad",(x*1.08,-.18,.79),(.27,.11,.23),armor,.022)
    segment(side+" shin",(x*1.08,-.01,.76),(x*1.10,-.015,.28),.235,.25,uniform)
    cube(side+" boot collar",(x*1.1,0,.265),(.27,.29,.18),dark,.018)
    cube(side+" boot",(x*1.1,-.13,.115),(.30,.47,.21),dark,.030)
    cube(side+" shoulder plate",(sign*.42,-.02,2.05),(.35,.42,.23),armor,.045)
    cube(side+" ear protection",(sign*.26,0,2.54),(.065,.18,.16),dark,.015)

# Both arms bend around rifle so it faces forwards (-Y).
for name, shoulder, elbow, hand in [
    ("right",(-.42,-.04,2.0),(-.57,-.33,1.75),(-.40,-.69,1.56)),
    ("left",(.42,-.04,2.0),(.57,-.36,1.73),(.11,-.78,1.59)),
]:
    segment(name+" upper arm",shoulder,elbow,.24,.23,uniform)
    ellipsoid(name+" elbow armor",elbow,(.15,.15,.15),armor,1)
    segment(name+" lower arm",elbow,hand,.18,.18,uniform)
    ellipsoid(name+" glove",hand,(.11,.12,.12),dark,1)

cube("Rifle receiver",(-.33,-.78,1.59),(.20,.49,.17),steel,.015)
cube("Rifle rail",(-.33,-.78,1.695),(.11,.43,.045),dark,.007)
cube("Rifle stock",(-.33,-.44,1.58),(.17,.27,.15),dark,.014)
cube("Foregrip",(-.26,-1.04,1.49),(.12,.22,.09),strap,.010)
barrel("Rifle barrel",(-.33,-1.19,1.60),.043,.47,steel)
barrel("Rifle muzzle",(-.33,-1.44,1.60),.060,.07,dark)
cube("Rifle pistol grip",(-.36,-.71,1.43),(.11,.12,.27),dark,.013)
cube("Rifle magazine",(-.32,-.90,1.35),(.13,.15,.25),steel,.019)
cube("Reflex sight",(-.33,-.79,1.77),(.11,.14,.09),dark,.015)

cube("Backpack",(0,.28,1.81),(.52,.30,.61),strap,.05)
cube("Backpack roll",(0,.43,2.06),(.45,.15,.15),uniform,.035)
for i,x in enumerate((-.26,-.09,.09,.26)):
    cube("Belt pouch "+str(i+1),(x,-.245,1.34),(.14,.10,.20),strap,.019)
for x in (-.25,.25):
    segment("Harness strap",(x,-.14,2.12),(x*.9,-.27,1.56),.075,.048,strap)

scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.samples=12
# Ubuntu Blender may be built without OpenImageDenoise; disable denoising.
for layer in scene.view_layers:
    layer.cycles.use_denoising = False
scene.render.resolution_x=640
scene.render.resolution_y=640
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.film_transparent=True
scene.view_settings.view_transform="Standard"

world=bpy.data.worlds.new("Studio")
scene.world=world
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(.16,.19,.22,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.8

def area(name, location, power, size):
    bpy.ops.object.light_add(type="AREA",location=location)
    ob=bpy.context.object; ob.name=name
    ob.data.energy=power; ob.data.shape="DISK"; ob.data.size=size
    ob.rotation_euler=(Vector((0,0,1.5))-ob.location).to_track_quat("-Z","Y").to_euler()

area("Key",(2,-4,4),520,5)
area("Fill",(-3,-2,3),320,4)
area("Rim",(0,3,4),560,3)

bpy.ops.object.camera_add(location=(4,-7,3.2))
cam=bpy.context.object;cam.name="Preview camera";scene.camera=cam
cam.data.type="ORTHO";cam.data.ortho_scale=3.5

def aim(x):
    cam.location=x
    cam.rotation_euler=(Vector((0,-.2,1.40))-cam.location).to_track_quat("-Z","Y").to_euler()

aim((4,-7,3.2))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,"soldier.blend"))

# Export only geometry, excluding the scene lights/camera.
bpy.ops.object.select_all(action="DESELECT")
for ob in parts: ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,"soldier.glb"),
                           export_format="GLB",use_selection=True)
for filename,position in [
    ("preview_front.png",(4,-7,3.2)),
    ("preview_side.png",(7,-1.4,3.1))
]:
    aim(position)
    scene.render.filepath=os.path.join(OUT,filename)
    bpy.ops.render.render(write_still=True)

report={"blender_version":bpy.app.version_string,
        "parts":len(parts),"base_triangles":sum(len(o.data.polygons) for o in parts),
        "files":["soldier.glb","soldier.blend","preview_front.png","preview_side.png"],
        "note":"Technical procedural prototype, no skeleton or animations"}
with open(os.path.join(OUT,"report.json"),"w",encoding="utf-8") as f:
    json.dump(report,f,indent=2)
print("CLOUD_BLENDER_SUCCESS",report)
