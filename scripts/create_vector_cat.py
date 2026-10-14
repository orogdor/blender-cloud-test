"""An original hand-parameterized cat, built directly from connected 3D vertices.

No Blender mesh primitive operators, four-view voxels, or downloaded models.
The anatomy is modeled with smooth variable-section surface lofts and custom
triangular ear/eye meshes. Works in Blender 4.0+ headless on GitHub Actions.
"""
import bpy
import bmesh
import math
import os
import json
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'output', 'vector_cat')
os.makedirs(OUT, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

TAU = math.pi * 2
skinned = []
model = []

def material(name, rgb, roughness=.85, metallic=0.0):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*rgb,1)
    m.use_nodes=True
    bsdf=m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(*rgb,1)
    bsdf.inputs['Roughness'].default_value=roughness
    bsdf.inputs['Metallic'].default_value=metallic
    return m

FUR=material('Ginger fur',(.57,.245,.080))
FUR_LIGHT=material('Golden cream fur',(.77,.52,.29))
STRIPE=material('Rusty tabby stripes',(.22,.084,.035))
SOCK=material('Ivory white paw fur',(.88,.81,.66))
EAR=material('Ear skin dusty pink',(.48,.22,.20))
OUTLINE=material('Deep warm eyeliner',(.14,.065,.035))
IRIS=material('Emerald eyes',(.23,.58,.34),.22)
PUPIL=material('Vertical cat pupils',(.013,.026,.022),.20)
NOSE=material('Rose pink nose',(.60,.23,.23))
WHISKER=material('Whisker ivory',(.93,.90,.77),.34)


def mesh_obj(name, verts, faces, materials, face_materials=None, smooth=True):
    mesh=bpy.data.meshes.new(name+'_mesh')
    mesh.from_pydata(verts,[],faces)
    mesh.update(calc_edges=True)
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    for m in materials: mesh.materials.append(m)
    for i,p in enumerate(mesh.polygons):
        p.use_smooth=smooth
        if face_materials is not None: p.material_index=face_materials[i]
    model.append(obj)
    return obj


def cubic(a,b,c,d,t):
    return 0.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)

def interpolate(stations,t):
    t=max(0.0,min(1.0,t))*(len(stations)-1)
    i=min(len(stations)-2,int(t)); f=t-i
    p0=stations[max(0,i-1)];p1=stations[i];p2=stations[i+1];p3=stations[min(len(stations)-1,i+2)]
    return tuple(cubic(p0[k],p1[k],p2[k],p3[k],f) for k in range(len(p1)))


def loft_y(name, stations, rings=38, sides=28, materials=None, mark=None):
    # station tuple: Y, center Z, half X width, Z height radius
    verts=[];faces=[];indices=[]
    for i in range(rings+1):
        y,cz,rx,rz=interpolate(stations,i/rings)
        for j in range(sides):
            a=TAU*j/sides
            # organic local surface, not a uniform analytic spheroid
            asym=1+.018*math.sin(a*3+y*9)
            x=math.cos(a)*rx*asym
            z=cz+math.sin(a)*rz*(1-.07*math.cos(a*2))
            verts.append((x,y,z))
    for i in range(rings):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides
            c=(i+1)*sides+(j+1)%sides;d=(i+1)*sides+j
            faces.append((a,b,c,d))
            indices.append(mark(i,j,rings,sides) if mark else 0)
    # end caps with a fan, proper closed individual manifold objects
    start=len(verts);y,cz,_,_=stations[0];verts.append((0,y,cz))
    end=len(verts);y,cz,_,_=stations[-1];verts.append((0,y,cz))
    for j in range(sides):
        faces.append((start,(j+1)%sides,j));indices.append(0)
        faces.append((end,rings*sides+j,rings*sides+(j+1)%sides));indices.append(0)
    return mesh_obj(name,verts,faces,materials or [FUR],indices)


def body_stripes(i,j,n,ns):
    # Bands across shoulders/rump, taper on ventral belly
    a=TAU*(j+.5)/ns
    dorsal=max(0.,math.sin(a))
    t=(i+.5)/n
    bands=math.sin(t*TAU*6.5 + .2*math.cos(a*4))
    if dorsal>.12 and bands>.62+(1-dorsal)*.28 and .09<t<.93: return 1
    if dorsal<-.56 and .22<t<.55: return 2
    return 0

# Anatomical trunk, shaped along spine, +Y goes toward the tail.
body=loft_y('CAT_BODY_HAND_MESH',[
 (-.48,.55,.035,.055),(-.42,.53,.145,.175),(-.29,.525,.198,.225),
 (-.12,.55,.218,.245),(.06,.565,.211,.252),(.24,.55,.211,.247),
 (.40,.55,.225,.258),(.52,.55,.204,.215),(.61,.57,.095,.12),(.64,.59,.016,.028)
],rings=50,sides=32,materials=[FUR,STRIPE,FUR_LIGHT],mark=body_stripes)

# Thick feline neck, anatomically flowing forward into head.
neck=loft_y('Neck and throat vertices',[
 (-.58,.67,.07,.08),(-.53,.66,.130,.135),(-.45,.62,.145,.17),
 (-.36,.57,.135,.19),(-.30,.53,.10,.105)
],rings=20,sides=24,materials=[FUR_LIGHT])

# Skull, cheeks and tapered chin: intentional sections rather than a sphere.
head=loft_y('Feline skull and cheeks',[
 (-.81,.72,.015,.025),(-.77,.738,.080,.065),(-.735,.758,.132,.112),
 (-.675,.777,.175,.164),(-.585,.787,.187,.181),(-.49,.80,.176,.174),
 (-.43,.795,.122,.12),(-.40,.78,.036,.037)
],rings=36,sides=32,materials=[FUR,FUR_LIGHT,STRIPE],mark=lambda i,j,n,ns: 1 if math.sin(TAU*j/ns)<-.62 and i<11 else (2 if (math.sin(TAU*j/ns)>.24 and i in (16,17,20,21)) else 0))

# Legs: tubular surface swept over a cat-specific bent joint path.
def path_mesh(name, joints, radius_pairs, mats, color_fn=None, sides=16, rings=27):
    verts=[];faces=[];face_mats=[]
    for i in range(rings+1):
        t=i/rings
        x,y,z,rx,ry=interpolate([(*p,*r) for p,r in zip(joints,radius_pairs)],t)
        p=Vector((x,y,z))
        ta=max(0.,t-.006);tb=min(1.,t+.006)
        a=Vector(interpolate(joints,ta)); b=Vector(interpolate(joints,tb))
        tangent=(b-a).normalized()
        if tangent.length<1e-6:tangent=Vector((0,0,-1))
        right=Vector((1,0,0))
        if abs(right.dot(tangent))>.85:right=Vector((0,1,0))
        right=(right-tangent*right.dot(tangent)).normalized()
        forward=tangent.cross(right).normalized()
        for j in range(sides):
            q=TAU*j/sides
            v=p+right*(rx*math.cos(q))+forward*(ry*math.sin(q))
            verts.append(tuple(v))
    for i in range(rings):
        for j in range(sides):
            faces.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
            face_mats.append(color_fn(i,j,rings,sides) if color_fn else 0)
    # actual closed mesh: cap triangles
    a0=len(verts);verts.append(joints[0]);a1=len(verts);verts.append(joints[-1])
    for j in range(sides):
        faces.append((a0,j,(j+1)%sides));face_mats.append(0)
        faces.append((a1,rings*sides+(j+1)%sides,rings*sides+j));face_mats.append(0)
    return mesh_obj(name,verts,faces,mats,face_mats)

for side in (-1,1):
    x=side*.165
    path_mesh(('Left' if side>0 else 'Right')+' foreleg',[
      (x,-.275,.605),(x*1.05,-.28,.48),(x*1.1,-.325,.35),(x*1.08,-.315,.20),
      (x*1.05,-.31,.074)
    ],[(.091,.088),(.075,.070),(.054,.059),(.048,.052),(.042,.047)],[FUR,SOCK],
      lambda i,j,n,ns: 1 if i>n*.81 else 0)
    x=side*.176
    path_mesh(('Left' if side>0 else 'Right')+' rear leg',[
      (x,.42,.59),(x*1.09,.51,.455),(x*1.05,.59,.315),(x*1.1,.48,.205),
      (x*1.06,.48,.074)
    ],[(.14,.125),(.135,.113),(.082,.079),(.052,.056),(.046,.049)],[FUR,STRIPE,SOCK],
      lambda i,j,n,ns: 2 if i>n*.82 else (1 if n*.23<i<n*.31 else 0))

# Paw topology made from rings running along Y, with wide toe end cap.
def paw(name,x,y):
    verts=[];faces=[]
    sides=16
    for k,(dy,rx,rz,cz) in enumerate([(-.115,.033,.024,.061),(-.070,.065,.037,.054),(-.018,.074,.042,.058),(.053,.054,.045,.064),(.082,.013,.018,.061)]):
        for j in range(sides):
            a=TAU*j/sides
            verts.append((x+math.cos(a)*rx,y+dy,cz+math.sin(a)*rz))
    for k in range(4):
        for j in range(sides):
            faces.append((k*sides+j,k*sides+(j+1)%sides,(k+1)*sides+(j+1)%sides,(k+1)*sides+j))
    verts.extend(((x,y-.115,.061),(x,y+.082,.061)))
    for j in range(sides):
        faces.append((5*sides,(j+1)%sides,j))
        faces.append((5*sides+1,4*sides+j,4*sides+(j+1)%sides))
    mesh_obj(name,verts,faces,[SOCK])
for s in (-1,1):
    paw(('L' if s>0 else 'R')+' front toes',s*.173,-.35)
    paw(('L' if s>0 else 'R')+' back toes',s*.186,.47)

# Curled tail with a tapered tube and exact polygon vertices.
tail_joints=[(.015,.56,.67),(.03,.67,.68),(.07,.78,.70),(.09,.89,.79),
             (.10,.95,.93),(.095,.91,1.065),(.04,.80,1.14)]
tail_r=[(.081,.081),(.073,.072),(.064,.065),(.052,.052),(.047,.047),(.039,.039),(.007,.008)]
path_mesh('Curving tabby tail - vertex spline',tail_joints,tail_r,[FUR,STRIPE],
          lambda i,j,n,ns: 1 if (int(i/4)%2) else 0,sides=18,rings=54)

# Pinna triangle mesh, anatomically swept, not a cube/cone.
def ear_mesh(name,x):
    s=1 if x>0 else -1
    outer=[(x-s*.071,-.53,.875),(x+s*.069,-.53,.872),
           (x+s*.031,-.48,1.115),(x,-.585,.927),(x-s*.035,-.57,.998)]
    # back surface offset towards rear of head
    back=[(xx,yy+.052,zz-.005) for xx,yy,zz in outer]
    verts=outer+back
    faces=[(0,3,4),(4,3,2),(3,1,2),
           (5,9,8),(9,7,8),(8,7,6),
           (0,4,9,5),(4,2,7,9),(2,1,6,7),(1,3,8,6),(3,0,5,8)]
    # Ear is sculpted using 5 face vertices + inner triangle facing front.
    ob=mesh_obj(name,verts,faces,[FUR])
    inner=[(x-s*.036,-.590,.907),(x+s*.033,-.584,.912),
           (x+s*.023,-.510,1.053),(x,-.606,.935)]
    back=[(vx,vy+.003,vz) for vx,vy,vz in inner]
    ear_vertices=inner+back
    ear_faces=[(0,3,2),(3,1,2),(4,6,7),(7,6,5),
               (0,2,6,4),(2,1,5,6),(1,3,7,5),(3,0,4,7)]
    mesh_obj(name+' salmon inner ear',ear_vertices,ear_faces,[EAR],smooth=False)
    return ob
for a in (-.126,.126):ear_mesh(('Left' if a>0 else 'Right')+' triangular ear',a)

# Cat almond eyes, irises, pupils. Polygon vertex fans on curved face.
def ellipse_patch(name,cx,cy,cz,radx,radz,mat,n=20,angle=0):
    verts=[(cx,cy-.003,cz)]
    for k in range(n):
        a=TAU*k/n
        dx=radx*math.cos(a); dz=radz*math.sin(a)
        verts.append((cx+dx*math.cos(angle)-dz*math.sin(angle),cy,cz+dx*math.sin(angle)+dz*math.cos(angle)))
    # Closed, paper-thin polygon volume instead of a non-manifold disc.
    backcenter=len(verts)
    verts.append((cx,cy+.004,cz))
    for k in range(n):
        vx,vy,vz=verts[k+1]
        verts.append((vx,vy+.004,vz))
    faces=[]
    for k in range(n):
        nxt=(k+1)%n
        faces.append((0,k+1,nxt+1))
        faces.append((backcenter,backcenter+nxt+1,backcenter+k+1))
        faces.append((k+1,backcenter+k+1,backcenter+nxt+1,nxt+1))
    return mesh_obj(name,verts,faces,[mat],smooth=False)
for side in (-1,1):
    x=side*.09
    ellipse_patch(('L' if side>0 else 'R')+' almond eye outline',x,-.749,.803,.058,.048,OUTLINE,28)
    ellipse_patch(('L' if side>0 else 'R')+' iris',x,-.754,.805,.040,.037,IRIS,28)
    ellipse_patch(('L' if side>0 else 'R')+' slit pupil',x,-.760,.807,.010,.033,PUPIL,20)
    ellipse_patch(('L' if side>0 else 'R')+' eye glint',x-side*.011,-.763,.819,.008,.009,WHISKER,12)

# Swept feline muzzle and jowls on face; ears and nose give recognizable profile.
for s in (-1,1):
    x=s*.053
    loft_y(('L' if s>0 else 'R')+' muzzle cheek',[
      (-.835,.709,.006,.012),(-.815,.702,.040,.037),(-.780,.707,.055,.046),
      (-.743,.708,.046,.045),(-.725,.717,.004,.008)
    ],rings=14,sides=16,materials=[SOCK]).location.x=x

nose_verts=[(-.036,-.847,.742),(.036,-.847,.742),(0,-.862,.708),
            (-.026,-.826,.745),(.026,-.826,.745),(0,-.834,.710)]
nose_faces=[(0,1,2),(3,5,4),(0,3,4,1),(1,4,5,2),(2,5,3,0)]
mesh_obj('Hand-shaped triangular nose',nose_verts,nose_faces,[NOSE],smooth=False)

# Smooth whisker and mouth curves as short tubes with 6 sides, not Blender curves primitives.
def filament(name,pts,rad,mat):
    vertices=[];faces=[];segments=6
    for i,p in enumerate(pts):
        p=Vector(p)
        prev=Vector(pts[max(i-1,0)]);nxt=Vector(pts[min(i+1,len(pts)-1)])
        t=(nxt-prev).normalized()
        tangent=Vector((0,0,1))
        if abs(t.dot(tangent))>.95:tangent=Vector((0,1,0))
        u=t.cross(tangent).normalized();v=t.cross(u).normalized()
        for j in range(segments):
            a=TAU*j/segments
            k=max(.25,1-(i/max(1,len(pts)-1))*.66)
            r=rad*k
            q=p+(u*math.cos(a)+v*math.sin(a))*r
            vertices.append(tuple(q))
    for i in range(len(pts)-1):
        for j in range(segments):
            faces.append((i*segments+j,i*segments+(j+1)%segments,
                        (i+1)*segments+(j+1)%segments,(i+1)*segments+j))
    vertices.append(pts[0]);vertices.append(pts[-1]);a0=len(vertices)-2;a1=len(vertices)-1
    for j in range(segments):
        faces.append((a0,(j+1)%segments,j))
        faces.append((a1,(len(pts)-1)*segments+j,(len(pts)-1)*segments+(j+1)%segments))
    return mesh_obj(name,vertices,faces,[mat])

filament('Nose philtrum',[(0,-.866,.709),(0,-.865,.683),(0,-.863,.674)],.0035,OUTLINE)
for s in (-1,1):
    filament('Mouth arc '+str(s),[(0,-.864,.673),(s*.018,-.857,.660),(s*.044,-.828,.670)],.003,OUTLINE)
    for k in range(3):
        dz=.030-k*.026
        filament('Whisker '+str(s)+'-'+str(k),[(s*.087,-.802,.705+dz),
                 (s*.18,-.825,.705+dz+.01),(s*.27,-.844,.702+dz+.045)],.002,WHISKER)

# Fur eyebrow tufts (not simulated hair): cat tabby stripes as small arched surface strips.
for s in (-1,1):
    x=s*.09
    filament('Eyebrow stripe '+str(s),[(x-s*.06,-.701,.872),(x,-.702,.88),(x+s*.053,-.689,.871)],.009,STRIPE)

scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=20
for layer in scene.view_layers: layer.cycles.use_denoising=False
scene.render.resolution_x=840
scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=True
world=bpy.data.worlds.new('Neutral editorial studio')
world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.20,.26,.32,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
scene.world=world

def light(name,pos,energy,size,color):
    bpy.ops.object.light_add(type='AREA',location=pos)
    ob=bpy.context.object;ob.name=name;ob.data.energy=energy;ob.data.shape='DISK';ob.data.size=size
    ob.data.color=color
    ob.rotation_euler=(Vector((0,0,.57))-ob.location).to_track_quat('-Z','Y').to_euler()
light('Softbox left',(2,-3,3.1),480,3.8,(1,.91,.83))
light('Softbox fill',(-2,-2,2.2),270,3.0,(.75,.85,1))
light('Rim light',(-1.5,2.7,2.3),460,3.0,(.94,1,.93))

bpy.ops.object.camera_add(location=(2.00,-2.90,1.65))
cam=bpy.context.object
scene.camera=cam
cam.data.type='ORTHO';cam.data.ortho_scale=1.96

def render_at(path,pos):
    cam.location=pos
    cam.rotation_euler=(Vector((0,.04,.56))-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=os.path.join(OUT,path)
    bpy.ops.render.render(write_still=True)

render_at('preview.png',(2.25,-3.20,1.66))
render_at('side.png',(3.8,-.15,1.35))
render_at('front.png',(0,-3.7,1.28))

# Export *only* original editable vertex meshes, no studio lighting/camera.
bpy.ops.object.select_all(action='DESELECT')
for obj in model:obj.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,'vector_cat.glb'),export_format='GLB',use_selection=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'vector_cat.blend'))

count_v=sum(len(o.data.vertices) for o in model)
count_f=sum(len(o.data.polygons) for o in model)
count_t=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in model)
nonmanifold=0
for obj in model:
    bm=bmesh.new();bm.from_mesh(obj.data)
    nonmanifold+=sum(not e.is_manifold for e in bm.edges)
    bm.free()
report={'generator':'Surface lofts and custom polygon vertices; NO primitive mesh operators',
        'blender':bpy.app.version_string,'mesh_objects':len(model),
        'vertices':count_v,'polygons':count_f,'triangles':count_t,
        'nonmanifold_edges':nonmanifold,
        'files':['vector_cat.glb','vector_cat.blend','preview.png','side.png','front.png']}
with open(os.path.join(OUT,'stats.json'),'w',encoding='utf-8') as f:json.dump(report,f,indent=2)
print('VECTOR_CAT_DONE',json.dumps(report))