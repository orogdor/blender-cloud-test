"""Vector-surface compact hatchback based on user-supplied four-view vehicle reference.
Everything is authored as explicit custom vertices and polygon faces; no mesh primitives.
Blender 4.0+, headless GitHub Actions compatible. Dimensions in metres.
"""
import bpy, math, os, json
from mathutils import Vector
from collections import Counter

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
OUT=os.path.join(ROOT,'output','vector_car')
os.makedirs(OUT,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
geo=[]

def material(name, color, metal=0, rough=.5):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metal
    bs.inputs['Roughness'].default_value=rough
    m.use_backface_culling=False
    return m
PAINT=material('Pearl white lacquer',(0.79,.83,.84),.32,.26)
ROOF=material('Gloss black roof',(.025,.031,.039),.42,.22)
GLASS=material('Tinted blue-grey glass',(.065,.115,.144),.48,.15)
GLASS2=material('Windshield reflection',(.125,.21,.25),.29,.18)
TRIM=material('Charcoal rubber trim',(.021,.026,.028),.04,.65)
TIRE=material('Black tire rubber',(.014,.017,.018),.01,.82)
CHROME=material('Machined aluminium',(.51,.60,.65),.78,.24)
RIM=material('Gloss anthracite spokes',(.11,.13,.15),.68,.28)
RED=material('Rear light red',(.84,.055,.028),.1,.27)
AMBER=material('Rear amber bar',(.93,.32,.025),.1,.27)
LIGHT=material('White LED lens',(.69,.82,.91),.14,.18)
DARKGLASS=material('Lamp internal dark glass',(.044,.066,.079),.23,.24)
SEAM=material('Fine panel seam',(.105,.13,.15),.16,.52)
FLOOR=material('Studio grey',(0.10,.135,.16),.03,.8)

def mesh(name, vertices, faces, mat, smooth=False, objgroup=True):
    datab=bpy.data.meshes.new(name+'_data')
    datab.from_pydata(vertices,[],faces)
    datab.update()
    ob=bpy.data.objects.new(name,datab)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    if smooth:
        for p in ob.data.polygons:p.use_smooth=True
    if objgroup:geo.append(ob)
    return ob

def quad(name, pts, mat):
    return mesh(name,pts,[(0,1,2,3)],mat)

def polygon(name, pts, mat):
    return mesh(name,pts,[tuple(range(len(pts)))],mat)

def segment(name, a, b, radius, mat, sides=9):
    A,B=Vector(a),Vector(b);dr=(B-A).normalized()
    ref=Vector((0,0,1)) if abs(dr.z)<.9 else Vector((0,1,0))
    u=dr.cross(ref).normalized();v=dr.cross(u).normalized()
    verts=[]
    for p in (A,B):
        for i in range(sides):
            an=2*math.pi*i/sides
            verts.append(tuple(p+radius*(u*math.cos(an)+v*math.sin(an))))
    faces=[(0,)+(tuple(range(sides-1,0,-1))), tuple(sides+i for i in range(sides))]
    faces += [(i,(i+1)%sides,sides+(i+1)%sides,sides+i) for i in range(sides)]
    return mesh(name,verts,faces,mat,True)

def polyline(name, points, radius, mat, sides=7):
    # One coherent vertex mesh, not one separate Blender object per edge.
    if len(points)<2:return None
    pts=[Vector(p) for p in points]
    vv=[];ff=[]
    for j,p in enumerate(pts):
        dr=((pts[min(j+1,len(pts)-1)]-pts[max(0,j-1)])).normalized()
        ref=Vector((0,0,1)) if abs(dr.z)<.90 else Vector((0,1,0))
        u=dr.cross(ref).normalized();v=dr.cross(u).normalized()
        for i in range(sides):
            an=2*math.pi*i/sides
            vv.append(tuple(p+radius*(u*math.cos(an)+v*math.sin(an))))
    ff.append(tuple(range(sides-1,-1,-1)))
    for j in range(len(pts)-1):
        for i in range(sides):
            a=j*sides+i;b=j*sides+(i+1)%sides
            ff.append((a,b,b+sides,a+sides))
    ff.append(tuple((len(pts)-1)*sides+i for i in range(sides)))
    return mesh(name,vv,ff,mat,True)


def interp(st,x):
    if x<=st[0][0]:return st[0][1:]
    if x>=st[-1][0]:return st[-1][1:]
    for a,b in zip(st,st[1:]):
        if a[0]<=x<=b[0]:
            t=(x-a[0])/(b[0]-a[0]);return tuple(u+(v-u)*t for u,v in zip(a[1:],b[1:]))
    return st[-1][1:]

# X runs front(-) to back(+); Y is width; Z is up.
# Main body shell: artist-directed station cross sections (not cubes/ellipsoids).
BODY_STATIONS=[
(-2.14,.73,1.11),(-1.97,.82,1.20),(-1.62,.86,1.29),(-1.19,.87,1.34),
(-.94,.86,1.31),(-.70,.86,1.27),(0,.87,1.25),(.75,.86,1.25),
(1.41,.85,1.26),(1.79,.83,1.24),(2.12,.76,1.18)]
counts=99;xs=[-2.14+i*(4.26/counts) for i in range(counts+1)]
verts=[];ringn=9
for x in xs:
    w,top=interp(BODY_STATIONS,x)
    # Cross-section clockwise on YZ, bonnet surface has gentle transverse crown.
    verts.extend([
        (x,-w*.96,.90),(x,-w,top-.105),(x,-w*.88,top-.025),
        (x,-w*.40,top+.028),(x,0,top+.052),(x,w*.40,top+.028),
        (x,w*.88,top-.025),(x,w,top-.105),(x,w*.96,.90)
    ])
faces=[]
for i in range(counts):
    for j in range(ringn-1):
        a=i*ringn+j;b=(i+1)*ringn+j
        faces.append((a,b,b+1,a+1))
mesh('Continuous hood shoulders and upper body custom loft',verts,faces,PAINT,True)

# Side skins with actual wheel cutouts (quads around an arch, not false tire decals).
AXLES=(-1.30,1.31)
for sign,label in [(-1,'left'),(1,'right')]:
    countx=175;countz=30
    vs=[];fs=[]
    for i in range(countx+1):
        x=-2.13+4.24*i/countx
        w,t=interp(BODY_STATIONS,x)
        for j in range(countz+1):
            z=.29+(.92-.29)*j/countz
            # wheel well occupies real negative space. Surface side slightly convex
            y=sign*(w-.024*math.sin(math.pi*(z-.29)/(.92-.29)))
            vs.append((x,y,z))
    for i in range(countx):
        x=-2.13+4.24*(i+.5)/countx
        for j in range(countz):
            z=.29+(.92-.29)*(j+.5)/countz
            if any((x-cx)**2+(z-.42)**2 < .432**2 for cx in AXLES):continue
            a=i*(countz+1)+j;b=a+countz+1
            fs.append((a,a+1,b+1,b) if sign==1 else (a,b,b+1,a+1))
    mesh(f'{label} flanks with arch openings',vs,fs,PAINT,True)
    # Sculpted upper body crease and lower sill detail
    crease=[];lower=[]
    for i in range(81):
        x=-1.93+3.86*i/80;w,top=interp(BODY_STATIONS,x)
        crease.append((x,sign*(w+.005),1.034+.012*math.cos(x*1.6)))
        if all(abs(x-cx)>.48 for cx in AXLES):lower.append((x,sign*(w+.006),.345))
    polyline(label+' long shoulder crease',crease,.005,CHROME)
    # split rocker at wheel arches
    for x1,x2 in [(-.78,.81)]:
        p=[]
        for i in range(25):
            x=x1+(x2-x1)*i/24;w,t=interp(BODY_STATIONS,x)
            p.append((x,sign*(w+.010),.34))
        polyline(label+' lower rocker molding',p,.022,TRIM)
    for cx in AXLES:
        points=[]
        for j in range(47):
            th=math.pi*j/46
            x=cx+.442*math.cos(th);z=.42+.442*math.sin(th)
            w,t=interp(BODY_STATIONS,x)
            points.append((x,sign*(w+.021),z))
        polyline(label+f' wheel arch trim {cx:+.2f}',points,.013,TRIM)
        outer=[]
        for j in range(37):
            th=math.pi*j/36
            x=cx+.466*math.cos(th);z=.42+.466*math.sin(th)
            w,t=interp(BODY_STATIONS,x)
            outer.append((x,sign*(w+.014),z))
        polyline(label+f' arch chrome {cx:+.2f}',outer,.004,CHROME)

# Front and rear lower facias, handmade soft bevel ring sections.
def bumper(xfront, label, back=False):
    side=[]
    w=.73 if not back else .76
    for y,z in [(-w,.90),(-w*.99,.43),(-w*.85,.29),(-w*.54,.245),
                (w*.54,.245),(w*.85,.29),(w*.99,.43),(w,.90)]:
        side.append((xfront,y,z))
    polygon(label+' face',side,PAINT)
    polygon(label+' black air dam',[(xfront+(-.012 if not back else .012),y,z)
       for y,z in [(-.69,.39),(-.60,.285),(.60,.285),(.69,.39)]],TRIM)
bumper(-2.145,'Front bumper')
bumper(2.125,'Rear bumper',True)
# Deep lower grille with horizontal slots
def recess(name,x,y0,y1,z0,z1,mat):
    return quad(name,[(x,y0,z0),(x,y1,z0),(x,y1,z1),(x,y0,z1)],mat)
recess('Wide lower grille',-2.166,-.44,.44,.46,.665,TRIM)
for z in (.495,.542,.589):segment('Grille silver horizontal bar',(-2.174,-.41,z),(-2.174,.41,z),.008,CHROME)
for sy in (-1,1):
    recess('Corner intake',-2.17,sy*.53-.115,sy*.53+.115,.40,.68,TRIM)
    for off in (-.05,.05):segment('Intake grille slat',(-2.178,sy*.53+off,.43),(-2.178,sy*.53+off,.64),.008,RIM)
recess('Nose center badge plate',-2.17,-.24,.24,.97,1.035,PAINT)

# Roof and its supports: low, sweeping wagon-hatch proportions.
ROOF_SECTIONS=[(-1.00,.77,1.275),(-.60,.715,1.64),(-.35,.660,1.82),
               (-.15,.650,1.86),(.87,.650,1.865),(1.13,.665,1.82),
               (1.39,.710,1.65),(1.69,.80,1.29)]
vs=[];fs=[]
for x,w,z in ROOF_SECTIONS:
    vs.append((x,-w,z));vs.append((x,w,z))
for i in range(len(ROOF_SECTIONS)-1):
    a=i*2;fs.append((a,a+1,a+3,a+2))
mesh('Sweeping gloss black roof shell',vs,fs,ROOF,True)
for sign,label in [(-1,'left'),(1,'right')]:
    points=[(x,sign*w,z) for x,w,z in ROOF_SECTIONS]
    # Underlying cabin side panel black, from the roof rail to belt.
    for i in range(len(points)-1):
        p,q=points[i],points[i+1]
        w1=interp(BODY_STATIONS,p[0])[0];w2=interp(BODY_STATIONS,q[0])[0]
        quad(label+f' upper black cabin skin {i}',[(p[0],sign*w1,1.248),
        (q[0],sign*w2,1.248),q,p],ROOF)
    polyline(label+' satin roof rail',points,.012,ROOF)
    # Glass door windows. Local polygon positions approximate a flush curved glass surface.
    frontpts=[(-.85,.780,1.31),(-.445,.683,1.710),(-.20,.663,1.783),
              (.39,.670,1.781),(.47,.840,1.307)]
    rearpts=[(.49,.842,1.31),(.46,.670,1.78),(1.02,.668,1.78),
             (1.35,.727,1.59),(1.58,.804,1.315)]
    for glname,coords in [('Front side window',frontpts),('Rear side window',rearpts)]:
        ps=[(x,sign*(y+.009),z) for x,y,z in coords]
        polygon(label+' '+glname,ps,GLASS)
        polyline(label+' '+glname+' rubber surround',ps+[ps[0]],.012,TRIM)
    # black B-pillar and C-pillar
    polyline(label+' B-pillar',[(.46,sign*.687,1.775),(.48,sign*.851,1.286)],.027,ROOF)
    polyline(label+' C-pillar',[(1.30,sign*.719,1.655),(1.60,sign*.83,1.26)],.023,ROOF)
    # doors, with thin curved seams and brushed handles
    for ix in (-.66,.49,1.57):
        w,t=interp(BODY_STATIONS,ix)
        polyline(label+f' door shut-line {ix:.1f}',[(ix,sign*(w+.015),.42),
                 (ix+.02,sign*(w+.018),.88),(ix,sign*(w+.015),1.245)],.0048,SEAM)
    for ix in (.07,1.12):
        w,t=interp(BODY_STATIONS,ix)
        polyline(label+' door handle',[(ix-.065,sign*(w+.023),1.085),
                                       (ix+.07,sign*(w+.023),1.088)],.016,CHROME)
        segment(label+' handle shadow',(ix-.052,sign*(w+.026),1.064),(ix+.065,sign*(w+.026),1.064),.005,SEAM)
    # Mirror stalks and white housing
    segment(label+' mirror neck',(-.74,sign*.79,1.36),(-.72,sign*.97,1.37),.018,TRIM)
    mirror=[(-.84,sign*.97,1.35),(-.68,sign*.97,1.35),(-.68,sign*1.05,1.41),(-.84,sign*1.05,1.41)]
    polygon(label+' white door mirror',mirror,PAINT)
    polyline(label+' mirror outer border',mirror+[mirror[0]],.012,PAINT)

# Panoramic front windscreen slant and rear hatch glass; carbon black surrounds.
front_glass=[(-.945,-.698,1.297),(-.945,.698,1.297),(-.405,.617,1.754),(-.405,-.617,1.754)]
rear_glass=[(1.315,-.644,1.743),(1.315,.644,1.743),(1.638,.747,1.317),(1.638,-.747,1.317)]
for name,pts in [('Front windscreen',front_glass),('Rear hatch tinted glass',rear_glass)]:
    polygon(name,pts,GLASS2 if name.startswith('Front') else GLASS)
    polyline(name+' perimeter',pts+[pts[0]],.014,TRIM)
    # center horizontal reflection / wiper mark at windshield bottom
    if name.startswith('Front'):
        polyline('Windshield base wiper',[(-.96,-.43,1.296),(-.958,-.1,1.298),(-.958,.40,1.296)],.009,ROOF)

# Five-spoke premium wheels, sidewall tire explicitly lofted with 48 angular vertices.
def annular(name, cx, cy, cz, r0, r1, y, mat, detail=48, side=1):
    v=[]
    for r in (r0,r1):
        for i in range(detail):
            t=i*2*math.pi/detail
            v.append((cx+r*math.cos(t),y,cz+r*math.sin(t)))
    faces=[(i,(i+1)%detail,detail+(i+1)%detail,detail+i) for i in range(detail)]
    return mesh(name,v,faces,mat,True)

def disk(name,cx,cy,cz,r,y,mat,detail=48):
    v=[(cx,y,cz)]+[(cx+r*math.cos(i*2*math.pi/detail),y,cz+r*math.sin(i*2*math.pi/detail)) for i in range(detail)]
    faces=[(0,1+i,1+(i+1)%detail) for i in range(detail)]
    return mesh(name,v,faces,mat,True)

def wheel(cx,sign):
    cy=sign*.84;cz=.415
    verts=[];K=48
    # wheel section profile through the axle, near outer face, tyre tread, backwall
    profile=[(sign*.708,.288),(sign*.704,.362),(sign*.727,.394),
             (sign*.867,.394),(sign*.915,.366),(sign*.929,.293)]
    for y,r in profile:
        for i in range(K):
            th=2*math.pi*i/K
            verts.append((cx+r*math.cos(th),y,cz+r*math.sin(th)))
    faces=[]
    for k in range(len(profile)-1):
        for i in range(K):
            a=k*K+i;b=k*K+(i+1)%K
            faces.append((a,b,b+K,a+K))
    mesh(f'Tyre {cx:+.2f} {sign:+d} custom cross-section',verts,faces,TIRE,True)
    y=sign*.938
    annular('Silver outer wheel lip',cx,cy,cz,.286,.320,y,CHROME)
    annular('Wheel black inset',cx,cy,cz,.08,.286,y+sign*.001,TRIM)
    annular('Diamond cut rim outer',cx,cy,cz,.265,.280,y+sign*.003,CHROME)
    for i in range(5):
        a=i*2*math.pi/5+.18
        # double-spoke split set; polygons are actual custom 3D faces.
        for split in (-1,1):
            ang=a+split*.095
            w=.028
            y0=y+sign*.008
            r_inner=.082;r_outer=.260
            pts=[(cx+r_inner*math.cos(ang-w),y0,cz+r_inner*math.sin(ang-w)),
                 (cx+r_outer*math.cos(ang-w*.66),y0,cz+r_outer*math.sin(ang-w*.66)),
                 (cx+r_outer*math.cos(ang+w*.66),y0,cz+r_outer*math.sin(ang+w*.66)),
                 (cx+r_inner*math.cos(ang+w),y0,cz+r_inner*math.sin(ang+w))]
            polygon('Double machined wheel spoke',pts,CHROME)
        rbolt=.056
        disk('Central alloy hub',cx,cy,cz,rbolt,y+sign*.018,RIM,24)
        disk('Wheel hub badge',cx,cy,cz,.027,y+sign*.022,CHROME,18)
    for j in range(5):
        a=2*math.pi*j/5
        disk('Wheel bolt',cx+.049*math.cos(a),cy,cz+.049*math.sin(a),.010,y+sign*.025,CHROME,12)

for cx in AXLES:
    for sg in (-1,1):wheel(cx,sg)

# Front face lighting: two large and two small round clusters as in image reference.
def front_disc(name,y,z,r,x,mat,steps=52):
    vs=[(x,y,z)]
    for i in range(steps):
        t=i*2*math.pi/steps
        vs.append((x,y+r*math.cos(t),z+r*math.sin(t)))
    fs=[(0,1+i,1+(i+1)%steps) for i in range(steps)]
    return mesh(name,vs,fs,mat)

def front_ring(name,y,z,r0,r1,x,mat,steps=52):
    vs=[]
    for r in (r0,r1):
        for i in range(steps):
            t=i*2*math.pi/steps
            vs.append((x,y+r*math.cos(t),z+r*math.sin(t)))
    fs=[(i,(i+1)%steps,steps+(i+1)%steps,steps+i) for i in range(steps)]
    return mesh(name,vs,fs,mat)

for y in (-.615,.615):
    front_disc('Main headlight housing',y,1.09,.196,-2.175,TRIM)
    front_ring('Chrome headlamp outer trim',y,1.09,.166,.199,-2.181,CHROME)
    front_disc('Big LED lens',y,1.09,.150,-2.184,LIGHT)
    front_ring('Headlight inner smoked ring',y,1.09,.110,.134,-2.188,DARKGLASS)
    front_disc('Headlight lens glass',y,1.09,.098,-2.191,GLASS2)
    front_disc('Foglight steel surround',y,.520,.110,-2.189,CHROME)
    front_disc('Foglight insert',y,.520,.077,-2.194,TRIM)
    front_disc('Foglight LED',y,.520,.040,-2.198,LIGHT)
for y in (-.285,.285):
    front_disc('Inner circular running lamp outer',y,.990,.112,-2.17,CHROME)
    front_disc('Inner running lamp dark center',y,.990,.079,-2.178,DARKGLASS)
    front_ring('Running lamp LED circle',y,.990,.057,.071,-2.181,LIGHT)

# Rear chrome and red lamp bar, bumper exhausts.
recess('Full width rear red LED strip',2.151,-.718,.718,1.09,1.15,RED)
recess('Rear orange trim upper',2.155,-.715,.715,1.146,1.17,AMBER)
recess('Rear number plate',2.159,-.270,.270,.565,.72,LIGHT)
recess('Rear plate recess',2.152,-.306,.306,.54,.746,TRIM)
recess('Rear number plate white',2.160,-.270,.270,.565,.72,LIGHT)
for y in (-.52,.52):
    front_ring('Rear exhaust pipe outline',y,.31,.052,.064,2.16,CHROME,32)
    front_disc('Rear exhaust dark hole',y,.31,.044,2.161,TRIM,32)

# Underbody closing silhouette: no need for full interior in this visual prototype.
quad('Black lower underbody',[(-1.96,-.77,.29),(1.95,-.76,.29),(1.95,.76,.29),(-1.96,.77,.29)],TRIM)

# Export only generated polygon meshes, no rendering lights/camera.
bpy.ops.object.select_all(action='DESELECT')
for obj in geo:obj.select_set(True)
bpy.context.view_layer.objects.active=geo[0]
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,'vector_car.glb'),export_format='GLB',use_selection=True,
                           export_apply=True)

# Analytic mesh report (decorative single-face decals intentionally non-manifold).
verts=sum(len(o.data.vertices) for o in geo)
polygons=sum(len(o.data.polygons) for o in geo)
triangles=sum(sum(max(1,len(p.vertices)-2) for p in ob.data.polygons) for ob in geo)
degenerate=sum(1 for ob in geo for p in ob.data.polygons if p.area<1e-10)
assert verts>10000 and triangles>15000
assert degenerate==0,('Degenerate polygon count',degenerate)
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=20
for layer in scene.view_layers:layer.cycles.use_denoising=False
scene.render.resolution_x=900;scene.render.resolution_y=680;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=True
scene.view_settings.view_transform='Standard'
scene.view_settings.look='Medium High Contrast'
scene.view_settings.exposure=0;scene.view_settings.gamma=1
scene.render.image_settings.color_mode='RGBA'
world=bpy.data.worlds.new('Studio sky')
world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.2,.24,.28,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
scene.world=world

floor=quad('Non-exported floor',[(-10,-10,.017),(-10,10,.017),(10,10,.017),(10,-10,.017)],FLOOR)
geo.remove(floor);floor.hide_render=False

for name,loc,power,size in [('Front softbox',(-5,-6,7),1200,7),('Side stripbox',(1,5,6),1450,8),('White key',(5,-3,5),700,5)]:
    bpy.ops.object.light_add(type='AREA',location=loc)
    o=bpy.context.object;o.name=name;o.data.energy=power;o.data.size=size
    o.rotation_euler=(Vector((0,0,.88))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(-5,-7,3.6))
cam=bpy.context.object;scene.camera=cam
cam.data.type='ORTHO';cam.data.ortho_scale=5.75

for name,loc in [('preview',(-5.0,-7,3.6)),('side',(0,-7.2,2.0)),('front',(-7.3,0,2.0)),
                 ('rear',(7.3,0,2.0)),('top',(0.01,-.01,8))]:
    cam.location=loc
    cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=os.path.join(OUT,name+'.png')
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'vector_car.blend'))
report={'model':'Vector hatchback from uploaded front-side-rear-top reference',
        'generator':'Custom polygon vertices/loft cross sections; no Blender mesh primitives',
        'blender_version':bpy.app.version_string,'mesh_objects':len(geo),
        'vertices':verts,'polygons':polygons,'triangles':triangles,'degenerate_faces':degenerate,
        'dimensions_m':{'length':4.3,'width_approx':2.1,'height_approx':1.87},
        'limitations':'Stylized visual approximation; no automotive CAD or interior; separate trim/wheel meshes'}
with open(os.path.join(OUT,'stats.json'),'w') as f:json.dump(report,f,indent=2)
print('VECTOR_CAR_SUCCESS',json.dumps(report))