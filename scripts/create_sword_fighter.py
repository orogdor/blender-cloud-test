"""Create a stylized anatomically proportioned sword fighter and animated GLB.
Run: blender -b --factory-startup --python-exit-code 1 --python scripts/create_sword_fighter.py
"""
import bpy, math, os, json
from mathutils import Vector

BASE=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
OUT=os.path.join(BASE,"fighter_output")
os.makedirs(OUT,exist_ok=True)
bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)

def material(name, rgba, metal=0, rough=.65):
    m=bpy.data.materials.new(name);m.diffuse_color=(*rgba,1);m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*rgba,1)
    p.inputs["Metallic"].default_value=metal
    p.inputs["Roughness"].default_value=rough
    return m

cloth=material("Royal blue padded tunic",(.10,.38,.82))
cloth2=material("Dark blue cloth",(.055,.13,.29))
skin=material("Warm skin",(.77,.47,.32))
hair=material("Dark brown hair",(.10,.065,.052))
plate=material("Silver armor",(.51,.59,.70),.62,.28)
trim=material("Golden armor trim",(.93,.59,.15),.63,.34)
leather=material("Leather boots gloves",(.21,.11,.065))
steel=material("Sword polished steel",(.72,.85,.93),.78,.2)
eye=material("Eyes dark",(.05,.04,.04))

meshes=[]; assignments={}
def ell(name,loc,scale,mat,bone,sub=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub,radius=1,location=loc)
    o=bpy.context.object;o.name=name;o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat);meshes.append(o);assignments[o.name]=bone
    return o

def box(name,loc,dims,mat,bone,bevel=.035):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object;o.name=name;o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    if bevel:
        mod=o.modifiers.new("Soft armor edges","BEVEL")
        mod.width=bevel;mod.segments=2
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.modifier_apply(modifier=mod.name)
        n=o.modifiers.new("Weighted normals","WEIGHTED_NORMAL")
        try: bpy.ops.object.modifier_apply(modifier=n.name)
        except Exception: o.modifiers.remove(n)
    meshes.append(o);assignments[o.name]=bone
    return o

def limb(name,a,b,r,mat,bone):
    a=Vector(a);b=Vector(b)
    o=ell(name,(a+b)/2,(r,r,(b-a).length/2+r*.20),mat,bone)
    o.rotation_euler=(b-a).to_track_quat("Z","Y").to_euler()
    return o

# Height 2.00 Blender units. Pelvis 1.00, shoulders 1.60, head ~1.84.
# Forward is -Y; rig pose is anatomical A pose; head size ~1/8 overall height.
ell("Pelvis",(0,0,1.01),(.245,.155,.18),cloth2,"pelvis")
ell("Abdomen",(0,0,1.25),(.22,.15,.27),cloth,"spine")
ell("Rib cage",(0,0,1.52),(.34,.19,.27),cloth,"chest")
box("Breastplate",(0,-.168,1.52),(.56,.11,.36),plate,"chest",.10)
box("Gold center trim",(0,-.235,1.53),(.08,.018,.30),trim,"chest",.016)
ell("Neck",(0,0,1.735),(.093,.09,.105),skin,"neck")
ell("Head",(0,-.016,1.859),(.124,.128,.159),skin,"head",3)
ell("Nose",(0,-.140,1.849),(.033,.055,.038),skin,"head")
ell("Hair cap",(0,.018,1.975),(.135,.139,.068),hair,"head")
for sign,side in [(-1,"R"),(1,"L")]:
    ell(side+" ear", (sign*.124,-.003,1.855),(.026,.027,.041),skin,"head")
    ell(side+" eye",(sign*.052,-.138,1.883),(.019,.013,.018),eye,"head")
    x=sign*.174
    ell(side+" hip",(x,0,1.004),(.16,.145,.14),cloth2,"pelvis")
    limb(side+" thigh",(x,0,.972),(x*1.09,-.013,.565),.139,cloth2,side+"_thigh")
    ell(side+" knee",(x*1.09,-.05,.565),(.142,.105,.114),plate,side+"_shin")
    limb(side+" shin",(x*1.09,0,.55),(x*1.09,-.015,.175),.107,cloth,side+"_shin")
    box(side+" boot",(x*1.09,-.095,.102),(.245,.36,.20),leather,side+"_foot",.05)
    # Arms are hanging slightly outward to allow a clean anatomical silhouette.
    sx=sign*.34; ex=sign*.45; hx=sign*.48
    ell(side+" shoulder",(sx,0,1.64),(.15,.14,.14),plate,side+"_upperarm")
    limb(side+" upper arm",(sx,0,1.61),(ex,-.012,1.36),.113,cloth,side+"_upperarm")
    ell(side+" elbow",(ex,-.02,1.34),(.095,.095,.105),skin,side+"_forearm")
    limb(side+" forearm",(ex,-.012,1.33),(hx,-.10,1.115),.091,cloth,side+"_forearm")
    ell(side+" glove",(hx,-.115,1.087),(.083,.075,.117),leather,side+"_hand")
    box(side+" bracer",(ex*1.04,-.092,1.23),(.15,.065,.16),plate,side+"_forearm",.025)

# Sword travels with the right wrist / hand. Point rises vertically in idle.
swx=-.48
box("Sword grip",(swx,-.115,1.035),(.052,.052,.26),leather,"R_hand",.014)
box("Sword crossguard",(swx,-.115,1.165),(.33,.075,.054),trim,"R_hand",.014)
box("Sword blade",(swx,-.115,1.57),(.105,.034,.80),steel,"R_hand",.016)
box("Sword tip",(swx,-.115,1.98),(.065,.024,.08),steel,"R_hand",.01)
ell("Pommel",(swx,-.115,.89),(.06,.06,.06),trim,"R_hand")

# Deform rig. Each piece gets a stable bone weight: robust GLB animation.
bpy.ops.object.armature_add(enter_editmode=True,location=(0,0,0))
rig=bpy.context.object;rig.name="FighterRig"
rig.data.edit_bones.remove(rig.data.edit_bones[0])
def bone(name,head,tail,parent=None):
    b=rig.data.edit_bones.new(name);b.head=head;b.tail=tail
    if parent: b.parent=rig.data.edit_bones[parent]
    b.use_connect=False

bone("root",(0,0,.98),(0,0,1.09))
bone("pelvis",(0,0,1.0),(0,0,1.13),"root")
bone("spine",(0,0,1.15),(0,0,1.4),"pelvis")
bone("chest",(0,0,1.40),(0,0,1.69),"spine")
bone("neck",(0,0,1.68),(0,0,1.77),"chest")
bone("head",(0,0,1.76),(0,0,1.96),"neck")
for s in ("R","L"):
    sign=-1 if s=="R" else 1
    bone(s+"_thigh",(sign*.17,0,1.0),(sign*.19,0,.57),"pelvis")
    bone(s+"_shin",(sign*.19,0,.57),(sign*.19,0,.16),s+"_thigh")
    bone(s+"_foot",(sign*.19,0,.17),(sign*.19,-.18,.09),s+"_shin")
    bone(s+"_upperarm",(sign*.34,0,1.64),(sign*.45,0,1.34),"chest")
    bone(s+"_forearm",(sign*.45,0,1.34),(sign*.48,-.10,1.12),s+"_upperarm")
    bone(s+"_hand",(sign*.48,-.10,1.12),(sign*.48,-.12,1.02),s+"_forearm")
bpy.ops.object.mode_set(mode="OBJECT")

for o in meshes:
    group=o.vertex_groups.new(name=assignments[o.name])
    group.add(list(range(len(o.data.vertices))),1.0,"REPLACE")
    mod=o.modifiers.new("Armature deformation","ARMATURE");mod.object=rig
    o.parent=rig

# Rig test motions: idle, walk, attack, block. Stored as named NLA tracks.
def pose(name,keys,frames):
    rig.animation_data_create()
    action=bpy.data.actions.new(name)
    rig.animation_data.action=action
    for fr,rotations in keys:
        for pb in rig.pose.bones:
            pb.rotation_mode="XYZ"
            pb.rotation_euler=(0,0,0)
        for bn,angles in rotations.items():
            rig.pose.bones[bn].rotation_euler=[math.radians(a) for a in angles]
        for pb in rig.pose.bones:
            pb.keyframe_insert(data_path="rotation_euler",frame=fr,group=pb.name)
    track=rig.animation_data.nla_tracks.new();track.name=name
    track.strips.new(name,frames[0],action)
    rig.animation_data.action=None

pose("Idle",[(1,{}),(20,{"spine":(1.5,0,0),"R_forearm":(-2,0,0)}),(40,{})],(1,40))
pose("Walk",[(1,{"R_thigh":(22,0,0),"L_thigh":(-22,0,0),"R_upperarm":(-12,0,0),"L_upperarm":(12,0,0)}),
              (12,{"R_thigh":(-22,0,0),"L_thigh":(22,0,0),"R_upperarm":(12,0,0),"L_upperarm":(-12,0,0)}),
              (24,{"R_thigh":(22,0,0),"L_thigh":(-22,0,0),"R_upperarm":(-12,0,0),"L_upperarm":(12,0,0)})],(1,24))
pose("SwordSlash",[(1,{"R_upperarm":(-40,10,-35),"R_forearm":(-30,0,-10),"chest":(0,0,25)}),
                   (10,{"R_upperarm":(-90,-20,45),"R_forearm":(-40,0,12),"chest":(0,0,-27)}),
                   (18,{"R_upperarm":(-20,0,-12),"R_forearm":(0,0,0),"chest":(0,0,0)})],(1,18))
pose("Block",[(1,{}),(8,{"R_upperarm":(-65,10,45),"R_forearm":(-65,0,-24),"L_upperarm":(-33,0,-35)}),
              (19,{"R_upperarm":(-65,10,45),"R_forearm":(-65,0,-24),"L_upperarm":(-33,0,-35)}),
              (28,{})],(1,28))

scene=bpy.context.scene
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,"sword_fighter.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,"sword_fighter.glb"),export_format="GLB",
                           export_animations=True,export_nla_strips=True)
triangles=sum(len(p.vertices)-2 for o in meshes for p in o.data.polygons)
with open(os.path.join(OUT,"report.json"),"w") as f:
    json.dump({"model":"Stylized human sword fighter","height_m":2.0,"mesh_parts":len(meshes),
               "bones":len(rig.data.bones),"triangles_estimate":triangles,
               "animations":["Idle","Walk","SwordSlash","Block"],
               "output":["sword_fighter.blend","sword_fighter.glb"]},f,indent=2)
print("FIGHTER_BUILD_FINISHED")
