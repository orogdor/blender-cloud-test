"""Blender 3.6+/4.x: pildist inspireeritud auto, punktipilv -> suletud mesh.

Scripting > Open > Run Script. Ei kustuta kasutaja teisi objekte.
Ei loe pildilt automaatselt ruudustikku: PROFILE on käsitsi hinnatud kuju.
Punktidel säilib ruudustiku naabrusinfo; sellest tekivad päris pinnad.
Rattad on kerega ühendatud pinnalaigud, mitte eraldi pöörlevad objektid.
"""
import math
from collections import defaultdict, deque

LONGITUDINAL = 80
PERIMETER = 64  # keep 64: wheel patch layout is calibrated to this grid
TRIANGULATE = False  # True: all faces become triangles
SHOW_POINT_CLOUD = False  # True: show loose vertices instead of the final mesh
POINT_RADIUS = 0.009
OUTPUT_BLEND = ""  # optional absolute path; empty = don't save automatically
COLLECTION_NAME = "AUTO_PUNKTID_MESH"
# x (front negative), roof z, width multiplier
PROFILE = [(-2.1, 1.02, .87), (-1.9, 1.09, .96),
           (-1.15, 1.12, 1.0), (-.95, 1.16, 1.0),
           (-.25, 1.63, 1.0), (.2, 1.68, 1.0),
           (1.35, 1.66, 1.0), (1.75, 1.50, .98),
           (2.1, 1.10, .91)]


def profile(x):
    for a, b in zip(PROFILE, PROFILE[1:]):
        if a[0] <= x <= b[0]:
            t = (x-a[0])/(b[0]-a[0])
            return tuple(a[k]*(1-t)+b[k]*t for k in (1, 2))
    return PROFILE[-1][1:]


def build_geometry():
    """Return points, indexed faces and per-face material ids. No bpy needed."""
    if LONGITUDINAL < 48 or PERIMETER != 64:
        raise ValueError("LONGITUDINAL must be >=48; PERIMETER must be 64")
    pts, faces, mats = [], [], []
    def vertex(p):
        pts.append(tuple(p))
        return len(pts)-1
    def face(ids, material=0):
        faces.append(tuple(ids)); mats.append(material)
    def idx(i, j):
        return i*PERIMETER+j % PERIMETER
    for i in range(LONGITUDINAL+1):
        x = -2.1+4.2*i/LONGITUDINAL
        roof, width = profile(x)
        corners = [(-.72,.25),(.72,.25),(.87,.42),(.89,1.00),
                   (.70,roof),(-.70,roof),(-.89,1.00),(-.87,.42)]
        for j in range(PERIMETER):
            k, t = divmod(j, 8); t /= 8
            a, b = corners[k], corners[(k+1) % 8]
            y = (a[0]*(1-t)+b[0]*t)*width
            z = a[1]*(1-t)+b[1]*t
            vertex((x,y,z))
    patches = []
    for wheel_x in (-1.32, 1.35):
        ci = round((wheel_x+2.1)/4.2*LONGITUDINAL)
        half = max(4, round(.44/4.2*LONGITUDINAL))
        for j0, j1, sign in ((12,24,1),(48,60,-1)):
            patches.append((ci-half,ci+half,j0,j1,sign))
    for i in range(LONGITUDINAL):
        for j in range(PERIMETER):
            if any(a <= i < b and c <= j < d for a,b,c,d,s in patches):
                continue
            ids = (idx(i,j),idx(i,j+1),idx(i+1,j+1),idx(i+1,j))
            x,y,z = [sum(pts[v][k] for v in ids)/4 for k in range(3)]
            mat = 1 if z > 1.13 and -.92 < x < 1.81 else 0
            if j < 8: mat = 4
            face(ids,mat)
    # Watertight nose and tail. Shared perimeter vertices, no duplicate seams.
    for i in (0,LONGITUDINAL):
        center = vertex((pts[idx(i,0)][0],0,.65))
        for j in range(PERIMETER):
            ids = (center,idx(i,j+1),idx(i,j)) if i == 0 else (center,idx(i,j),idx(i,j+1))
            y,z = sum(pts[v][1] for v in ids)/3,sum(pts[v][2] for v in ids)/3
            # Approximate lights/grille as integrated face materials.
            mat = 5 if i == 0 and abs(y) > .47 and .62 < z < .91 else 0
            if i == 0 and abs(y) < .45 and .35 < z < .61: mat = 4
            if i != 0 and .73 < z < .87: mat = 6
            face(ids,mat)
    # Remove each side patch and bridge its exact boundary to tire/rim rings.
    # This gives one connected surface, not intersecting independent wheels.
    for a,b,c,d,sign in patches:
        boundary = ([idx(i,c) for i in range(a,b)] +
                    [idx(b,j) for j in range(c,d)] +
                    [idx(i,d) for i in range(b,a,-1)] +
                    [idx(a,j) for j in range(d,c,-1)])
        cx = (pts[idx(a,c)][0]+pts[idx(b,c)][0])/2
        cz = (pts[idx(a,c)][2]+pts[idx(a,d)][2])/2
        rx = (pts[idx(b,c)][0]-pts[idx(a,c)][0])/2
        rz = (pts[idx(a,d)][2]-pts[idx(a,c)][2])/2
        angles = [math.atan2((pts[v][2]-cz)/rz,(pts[v][0]-cx)/rx) for v in boundary]
        prev = boundary
        for radius, depth, material in ((.455,.925,0),(.445,.99,2),
                                        (.42,1.035,2),(.32,1.045,2),
                                        (.29,1.048,3),(.09,1.06,3)):
            ring = [vertex((cx+radius*math.cos(t),sign*depth,
                            .46+radius*math.sin(t))) for t in angles]
            for k in range(len(prev)):
                n = (k+1) % len(prev)
                # Boundary winding is opposite to the removed body's faces.
                face((prev[k],prev[n],ring[n],ring[k]), material)
            prev = ring
        center = vertex((cx,sign*1.064,.46))
        for k in range(len(prev)):
            face((prev[k],prev[(k+1) % len(prev)],center),3)
    # Remove unused interior patch points from BOTH point cloud and final mesh.
    used = sorted({v for f in faces for v in f})
    remap = {v:i for i,v in enumerate(used)}
    pts = [pts[v] for v in used]
    faces = [tuple(remap[v] for v in f) for f in faces]
    if TRIANGULATE:
        out, outm = [], []
        for f,m in zip(faces,mats):
            for k in range(1,len(f)-1):
                out.append((f[0],f[k],f[k+1])); outm.append(m)
        faces,mats = out,outm
    # Orient all polygons consistently using shared edge directions.
    edge_faces = defaultdict(list)
    for fi,f in enumerate(faces):
        for u,v in zip(f,f[1:]+f[:1]): edge_faces[tuple(sorted((u,v)))].append((fi,u,v))
    flip = {0:False}; queue = deque([0])
    while queue:
        fi = queue.popleft(); f = faces[fi]
        for u,v in zip(f,f[1:]+f[:1]):
            for ni,nu,nv in edge_faces[tuple(sorted((u,v)))]:
                if ni == fi: continue
                expected = flip[fi] ^ (u == nu and v == nv)
                if ni in flip:
                    if flip[ni] != expected: raise ValueError("Non-orientable surface")
                else: flip[ni]=expected; queue.append(ni)
    faces = [tuple(reversed(f)) if flip.get(i,False) else f for i,f in enumerate(faces)]
    volume = signed_volume(pts,faces)
    if volume < 0: faces = [tuple(reversed(f)) for f in faces]
    validate_geometry(pts,faces)
    return pts,faces,mats


def signed_volume(points,faces):
    total = 0.0
    for f in faces:
        a = points[f[0]]
        for k in range(1,len(f)-1):
            b,c = points[f[k]],points[f[k+1]]
            total += (a[0]*(b[1]*c[2]-b[2]*c[1])+
                      a[1]*(b[2]*c[0]-b[0]*c[2])+
                      a[2]*(b[0]*c[1]-b[1]*c[0]))/6
    return total


def validate_geometry(points,faces):
    edges = defaultdict(list); neighbors = defaultdict(set)
    for f in faces:
        if len(set(f)) != len(f): raise ValueError("Repeated face vertex")
        # Check total polygon area (fan), without requiring planar quads.
        area = 0
        a = points[f[0]]
        for k in range(1,len(f)-1):
            b,c = points[f[k]],points[f[k+1]]
            u,v = [b[j]-a[j] for j in range(3)],[c[j]-a[j] for j in range(3)]
            cross = (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
            area += math.sqrt(sum(t*t for t in cross))/2
        if area < 1e-12: raise ValueError("Zero-area face")
        for u,v in zip(f,f[1:]+f[:1]):
            edges[tuple(sorted((u,v)))].append((u,v)); neighbors[u].add(v); neighbors[v].add(u)
    bad = sum(len(v)!=2 or v[0] != tuple(reversed(v[1])) for v in edges.values())
    seen = {0}; queue = deque([0])
    while queue:
        for v in neighbors[queue.popleft()]:
            if v not in seen: seen.add(v); queue.append(v)
    # Closed connected genus-0 surface; also rejects disconnected spare points.
    if bad or len(seen)!=len(points) or len(points)-len(edges)+len(faces)!=2:
        raise ValueError(f"Invalid mesh: bad edges={bad}, reached={len(seen)}/{len(points)}")
    if signed_volume(points,faces) <= 0: raise ValueError("Non-positive volume")
    return {"vertices":len(points),"faces":len(faces),"edges":len(edges),
            "components":1,"boundary_edges":0,"nonmanifold_edges":0,
            "quads":sum(len(f)==4 for f in faces),"triangles":sum(len(f)==3 for f in faces),
            "volume":round(signed_volume(points,faces),6)}


def run_blender():
    import bpy
    import json
    points,faces,materials = build_geometry()
    report = validate_geometry(points,faces)
    # Only replace our own explicitly tagged collection.
    old = bpy.data.collections.get(COLLECTION_NAME)
    if old and old.get("generated_by") != "auto_punktipilv_mesh":
        raise RuntimeError("Collection name already used by another project")
    if old:
        for ob in list(old.objects): bpy.data.objects.remove(ob,do_unlink=True)
        bpy.data.collections.remove(old)
    collection = bpy.data.collections.new(COLLECTION_NAME)
    collection["generated_by"] = "auto_punktipilv_mesh"
    bpy.context.scene.collection.children.link(collection)
    def object_mesh(name,faces_in):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(points,[],faces_in); mesh.update()
        ob = bpy.data.objects.new(name,mesh); collection.objects.link(ob)
        return ob
    cloud = object_mesh("01_Punktipilv",[])
    cloud.hide_set(not SHOW_POINT_CLOUD); cloud.hide_render = True
    cloud["info"] = "Samad 3D-punktid kui lõppvõrgus; ainult vertexid. Tab = Edit Mode."
    final = object_mesh("02_Auto_Suletud_Mesh",faces)
    final.hide_set(SHOW_POINT_CLOUD); final.hide_render = SHOW_POINT_CLOUD
    colors = [("Kere",(.72,.75,.78,1)),("Klaas",(.075,.10,.13,1)),
              ("Rehv",(.025,.029,.033,1)),("Velg",(.32,.35,.38,1)),
              ("Pohi_Grill",(.055,.065,.075,1)),("Esituli",(.9,.85,.60,1)),
              ("Tagatuli",(.55,.025,.015,1))]
    for name,color in colors:
        mat = bpy.data.materials.get("AutoPC_"+name) or bpy.data.materials.new("AutoPC_"+name)
        mat.diffuse_color = color; mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value=color
        bsdf.inputs["Roughness"].default_value=.27 if name in ("Kere","Klaas") else .65
        final.data.materials.append(mat)
    for poly,mat in zip(final.data.polygons,materials):
        poly.material_index=mat; poly.use_smooth=True
    final["validation"] = json.dumps(report)
    final["source"] = "Manual grid approximation from supplied car reference; not photogrammetry"
    # Optional point spheres are display geometry only, never part of the final mesh.
    try:
        group = bpy.data.node_groups.new("AutoPC_PointDisplay","GeometryNodeTree")
        if hasattr(group,"interface"):
            group.interface.new_socket(name="Geometry",in_out="INPUT",socket_type="NodeSocketGeometry")
            group.interface.new_socket(name="Geometry",in_out="OUTPUT",socket_type="NodeSocketGeometry")
        else:
            group.inputs.new("NodeSocketGeometry","Geometry"); group.outputs.new("NodeSocketGeometry","Geometry")
        inp=group.nodes.new("NodeGroupInput"); out=group.nodes.new("NodeGroupOutput")
        convert=group.nodes.new("GeometryNodeMeshToPoints"); convert.mode="VERTICES"
        sphere=group.nodes.new("GeometryNodeMeshIcoSphere")
        sphere.inputs["Radius"].default_value=POINT_RADIUS; sphere.inputs["Subdivisions"].default_value=1
        inst=group.nodes.new("GeometryNodeInstanceOnPoints")
        group.links.new(inp.outputs["Geometry"],convert.inputs["Mesh"])
        group.links.new(convert.outputs["Points"],inst.inputs["Points"])
        group.links.new(sphere.outputs["Mesh"],inst.inputs["Instance"])
        group.links.new(inst.outputs["Instances"],out.inputs["Geometry"])
        mod=cloud.modifiers.new("Punktide kuvamine","NODES"); mod.node_group=group
    except Exception as exc:
        print("Point preview unavailable; loose vertices remain accessible in Edit Mode:",exc)
    for ob in bpy.context.selected_objects: ob.select_set(False)
    selected=cloud if SHOW_POINT_CLOUD else final
    selected.select_set(True); bpy.context.view_layer.objects.active=selected
    text=bpy.data.texts.get("AUTO_KONTROLL.txt") or bpy.data.texts.new("AUTO_KONTROLL.txt")
    text.clear(); text.write(json.dumps(report,indent=2))
    print("AUTO MESH OK",report)
    if OUTPUT_BLEND: bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
    return final


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        import json
        p,f,m=build_geometry(); print(json.dumps(validate_geometry(p,f),indent=2))
    else:
        run_blender()
