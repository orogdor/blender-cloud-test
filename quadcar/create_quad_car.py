"""Build a single Blender mesh object of a compact retro hatchback, ~1000 all-quad faces.
No mesh primitives. Entire geometry authored as vertices/quad index lists.
Inspired by the user's multi-view white hatchback drawing, but not a literal vertex extractor.
Runs headless with Blender 4.0+ on GitHub Actions.
"""
import bpy, bmesh, math, os, json
from mathutils import Vector

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT=os.path.join(ROOT,'output','quad_car')
os.makedirs(OUT,exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

vertices=[]
faces=[]
face_types=[]
face_uvs=[]

def v_add(co):
    vertices.append(tuple(map(float, co)))
    return len(vertices)-1

def quad(indices, kind='body', uv=None):
    assert len(indices)==4
    faces.append(tuple(indices))
    face_types.append(kind)
    face_uvs.append(uv)

# Body: 24 longitudinal sections, 28 around each ring, quad-filled end caps.
N_LENGTH=23
N_EDGE=8  # 7 faces along each edge of rounded-rectangle body cross-section
FRONT=-1.82
REAR=1.82
WHEEL_Y=(-.99,1.02)

keys=[
    (-1.82,.84),(-1.67,.91),(-1.22,.96),(-.82,.99),
    (-.66,1.04),(-.07,1.46),(.93,1.47),(1.18,1.43),
    (1.60,1.11),(1.82,.94)
]

def interp(y, keys):
    if y<=keys[0][0]:return keys[0][1]
    for a,b in zip(keys[:-1],keys[1:]):
        if y<=b[0]:
            t=(y-a[0])/(b[0]-a[0]);t=t*t*(3-2*t)
            return a[1]*(1-t)+b[1]*t
    return keys[-1][1]

def wd(y):
    # Wide cabin, a slightly narrower rounded front / rear.
    u=(y-FRONT)/(REAR-FRONT)
    return .806 + .035*math.sin(math.pi*u)-.04*(abs(2*u-1)**4)

def arch(y):
    return .42*max(math.exp(-((y-a)/.255)**4) for a in WHEEL_Y)

def ring_at(y):
    w=wd(y)
    roof=interp(y,keys)
    # bottom corner rises around the wheel openings; narrower across underside
    def bottom_z(x):
        return .145 + arch(y)*(abs(x)/w)**9
    pts=[]
    # bottom: left -> right
    for i in range(N_EDGE):
        x=w*(-1+2*i/(N_EDGE-1))
        pts.append((x,y,bottom_z(x)))
    # right: bottom -> roof edge (omit first corner)
    for i in range(1,N_EDGE):
        t=i/(N_EDGE-1)
        x=w*(1-.23*t**2)
        z=bottom_z(w)*(1-t) + (roof-.075)*t
        pts.append((x,y,z))
    # top: right -> left (omit first corner)
    for i in range(1,N_EDGE):
        t=i/(N_EDGE-1)
        x=w*.77*(1-2*t)
        z=roof-.075 + .075*(1-(abs(1-2*t))**2)
        pts.append((x,y,z))
    # left: top -> bottom (omit both corners)
    for i in range(1,N_EDGE-1):
        t=i/(N_EDGE-1)
        x=-w*(1-.23*(1-t)**2)
        z=(roof-.075)*(1-t)+bottom_z(-w)*t
        pts.append((x,y,z))
    assert len(pts)==28, len(pts)
    return pts

rings=[]
for j in range(N_LENGTH+1):
    y=FRONT+(REAR-FRONT)*j/N_LENGTH
    rings.append([v_add(v) for v in ring_at(y)])

for j in range(N_LENGTH):
    ymid=FRONT+(REAR-FRONT)*(j+.5)/N_LENGTH
    for k in range(28):
        mid=(k+.5)%28
        if 7<=mid<14 or 21<=mid<28: side=True
        else: side=False
        kind='body'
        if 14<=mid<21: # roof/hood
            if -.69<ymid<-.06 or 1.14<ymid<1.61:
                kind='window'
            elif -.06<=ymid<=1.14:
                kind='roof'
        elif side and -.45<ymid<1.48 and (k%7>=4):
            kind='window'
        elif side and k%7<=1 and -1.65<ymid<1.65:
            kind='dark_trim' if k%7==0 else 'body'
        quad((rings[j][k], rings[j+1][k], rings[j+1][(k+1)%28], rings[j][(k+1)%28]), kind)

# An 8x8 quad-filled end cap. Edges reuse boundary-ring vertex IDs.
def cap_boundary(ring,s,t):
    if t==0:return ring[s]
    if s==7:return ring[7+t]
    if t==7:return ring[14+7-s]
    if s==0:return ring[21+7-t]
    return None

def cap(y,ring,kind):
    outline=ring_at(y)
    grid=[]
    for t in range(8):
        row=[]
        for s in range(8):
            old=cap_boundary(ring,s,t)
            if old is not None:row.append(old);continue
            a=s/7;b=t/7
            # bilinear/rectangular interpolation, backface follows the actual corner widths.
            left_bot=Vector(outline[0]);right_bot=Vector(outline[7])
            right_top=Vector(outline[14]);left_top=Vector(outline[21])
            coord=(1-b)*((1-a)*left_bot+a*right_bot)+b*((1-a)*left_top+a*right_top)
            coord.y=y+(.011 if kind=='front' else -.011)*math.sin(math.pi*a)*math.sin(math.pi*b)
            row.append(v_add(coord))
        grid.append(row)
    for t in range(7):
        for s in range(7):
            pts=[grid[t][s],grid[t][s+1],grid[t+1][s+1],grid[t+1][s]]
            uv=[(s/7,t/7),((s+1)/7,t/7),((s+1)/7,(t+1)/7),(s/7,(t+1)/7)]
            quad(pts,kind,uv)

cap(FRONT,rings[0],'front')
cap(REAR,rings[-1],'rear')

# Each wheel is a manually indexed, closed quad torus with 4 profile segments.
# Wheels are separate topological islands, but belong to the SAME mesh object.
for xside in (-1,1):
    for ycenter in WHEEL_Y:
        cx=xside*.79
        cz=.335
        wheel=[]
        profile=[(-.115,.245),(-.09,.323),(.09,.323),(.115,.245)]
        for ax,radius in profile:
            wheel.append([v_add((cx+xside*ax,
                    ycenter + radius*math.sin(2*math.pi*i/16),
                    cz + radius*math.cos(2*math.pi*i/16)))
                    for i in range(16)])
        for p in range(4):
            for i in range(16):
                quad([wheel[p][i],wheel[(p+1)%4][i],
                     wheel[(p+1)%4][(i+1)%16],wheel[p][(i+1)%16]],
                     'rim' if p==3 else 'tire')

assert len(faces)==998,(len(faces),'must be exactly 998 quads')
mesh=bpy.data.meshes.new('Compact Hatchback 998 quads')
mesh.from_pydata(vertices,[],faces)
mesh.update()
obj=bpy.data.objects.new('QuadCar_998_OneMesh',mesh)
bpy.context.collection.objects.link(obj)

# Materials. The front and rear bumper graphics are textures on the same quad cap.
def plain_mat(name,color,metal=.0,rough=.48):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough
    bs.inputs['Metallic'].default_value=metal
    return m

# Create embedded-cap decals as generated PNG textures: keeps total quad count fixed.
from PIL import Image,ImageDraw
size=1024

def make_cap_png(side):
    im=Image.new('RGB',(size,size),(236,237,235))
    d=ImageDraw.Draw(im)
    def xy(x,y):return (int(x*size),int((1-y)*size))
    def rect(x0,y0,x1,y1,fill):
        a=xy(x0,y0);b=xy(x1,y1)
        d.rounded_rectangle((a[0],b[1],b[0],a[1]),radius=20,fill=fill)
    def circle(cx,cy,r,fill,outline=None,stroke=0):
        a=xy(cx-r,cy+r);b=xy(cx+r,cy-r)
        d.ellipse((*a,*b),fill=fill,outline=outline,width=stroke)
    if side=='front':
        rect(.15,.23,.85,.37,(17,20,24))
        rect(.17,.40,.83,.43,(135,139,137))
        for x in (.16,.84):
            circle(x,.72,.105,(29,35,39),(140,160,170),15)
            circle(x,.72,.072,(47,58,67),(237,246,249),12)
        for x in (.32,.68):
            circle(x,.65,.055,(27,33,36),(195,212,216),11)
        for x in (.20,.80):circle(x,.23,.029,(180,188,191),(32,38,40),8)
        rect(.33,.245,.67,.31,(235,235,232))
    else:
        rect(.08,.57,.92,.63,(205,21,20))
        rect(.10,.59,.90,.612,(240,94,58))
        rect(.36,.27,.64,.36,(226,226,225))
        rect(.02,.10,.98,.20,(35,40,43))
        for x in (.16,.84):circle(x,.155,.044,(36,38,41),(178,187,190),9)
    path=os.path.join(OUT,side+'_graphic.png')
    im.save(path)
    return path

def textured_mat(side):
    path=make_cap_png(side)
    m=bpy.data.materials.new(side.capitalize()+' graphic')
    m.use_nodes=True
    nodes=m.node_tree.nodes
    p=nodes.get('Principled BSDF')
    tex=nodes.new('ShaderNodeTexImage')
    tex.image=bpy.data.images.load(path)
    tex.interpolation='Linear'
    m.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
    p.inputs['Roughness'].default_value=.48
    return m

materials=[plain_mat('Pearl White',(.88,.90,.90)),
           plain_mat('Black Roof',(.085,.09,.10),.13,.32),
           plain_mat('Dark Glass',(.095,.15,.18),.1,.24),
           plain_mat('Tire Black',(.045,.05,.052)),
           plain_mat('Alloy Rim',(.44,.49,.50),.65,.32),
           textured_mat('front'),textured_mat('rear'),
           plain_mat('Lower black side trim',(.075,.075,.08))]
for m in materials:mesh.materials.append(m)
material_map={'body':0,'roof':1,'window':2,'tire':3,'rim':4,
              'front':5,'rear':6,'dark_trim':7}
uv_layer=mesh.uv_layers.new(name='Cap UV')
for i,poly in enumerate(mesh.polygons):
    poly.material_index=material_map[face_types[i]]
    # For all non-face-cap surfaces, assign nonzero basic UV to avoid glTF warnings.
    uv=face_uvs[i]
    for j,li in enumerate(poly.loop_indices):
        uv_layer.data[li].uv=uv[j] if uv else ((j in (1,2))*1.,(j in (2,3))*1.)
    poly.use_smooth=True

# Check topology: one object, quads, 5 connected components (body + four wheels).
bm=bmesh.new();bm.from_mesh(mesh)
bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
nonmanifold=sum(1 for e in bm.edges if not e.is_manifold)
remaining=set(bm.verts);components=0
while remaining:
    components+=1
    stack=[remaining.pop()]
    while stack:
        vv=stack.pop()
        for edge in vv.link_edges:
            other=edge.other_vert(vv)
            if other in remaining:
                remaining.remove(other);stack.append(other)
bm.to_mesh(mesh);bm.free();mesh.update()
assert len(bpy.data.objects)==1,'Unexpected extra object before scene setup'
assert all(len(p.vertices)==4 for p in mesh.polygons)
assert nonmanifold==0,('non-manifold edges',nonmanifold)

# Scene and exports, only select model for GLB.
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,'quad_car.glb'),
                           export_format='GLB',use_selection=True)
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=9
for layer in scene.view_layers:
    layer.cycles.use_denoising=False
scene.render.resolution_x=1000
scene.render.resolution_y=700
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False
world=bpy.data.worlds.new('Studio World');world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.32,.36,.39,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
scene.world=world
for name,location,power,size_l in [('Softbox',(3,-4,5),900,5),('Fill',(-4,2,3.5),540,4)]:
    bpy.ops.object.light_add(type='AREA',location=location)
    light=bpy.context.object;light.name=name;light.data.energy=power;light.data.size=size_l
    light.rotation_euler=(Vector((0,0,.65))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(4,-5,2.9))
camera=bpy.context.object;scene.camera=camera

def render(name,position,target=(0,0,.74),ortho=4.5):
    camera.location=position
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=ortho
    scene.render.filepath=os.path.join(OUT,name+'.png')
    bpy.ops.render.render(write_still=True)

render('preview',(4,-5,3.0),ortho=4.6)
render('front',(0,-7,1.0),ortho=2.55)
render('side',(7,0,1.0),ortho=4.5)
render('rear',(0,7,1.0),ortho=2.55)
render('top',(0,0,7),ortho=4.3)
# Only one mesh object even though lights/camera are Blender objects.
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'quad_car.blend'))
stats={'blender_version':bpy.app.version_string,'mesh_objects':sum(o.type=='MESH' for o in scene.objects),
       'quad_faces':len(mesh.polygons),'triangles':sum(len(p.vertices)-2 for p in mesh.polygons),
       'vertices':len(mesh.vertices),'edges':len(mesh.edges),'nonmanifold_edges':nonmanifold,
       'connected_components':components,'dimensions_m':{'length':3.64,'width':1.68,'height':1.47},
       'method':'Manually defined vertex cross-sections, one mesh, no primitive operators',
       'reference_method':'Approximation of user hatchback image, not automatic grid digitization'}
with open(os.path.join(OUT,'stats.json'),'w') as f:json.dump(stats,f,indent=2)
print('QUAD_CAR_SUCCESS',json.dumps(stats))