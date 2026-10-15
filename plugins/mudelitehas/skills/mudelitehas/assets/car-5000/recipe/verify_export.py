from pathlib import Path
import bpy,bmesh,json
from mathutils import Vector
from mathutils.kdtree import KDTree
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output'
cloud=np.load(OUT/'04_point_cloud.npz')['points'];tree=KDTree(len(cloud))
for i,p in enumerate(cloud):tree.insert(Vector(p),i)
tree.balance()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(OUT/'Auto_5000_3vaate_test.glb'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];tris=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objects)
distances=[];zero=0
for ob in objects:
 for v in ob.data.vertices:distances.append(tree.find(ob.matrix_world@v.co)[2])
 zero+=sum(p.area<1e-12 for p in ob.data.polygons)
assert tris==10000,tris
assert max(distances)<.00002,max(distances)
assert zero==0,zero
r={'status':'passed','actual_export_triangles':tris,'expected_triangles':10000,'zero_area_export_faces':zero,'mesh_objects':len(objects),'maximum_distance_to_pre_mesh_cloud_m':max(distances),'mean_distance_to_pre_mesh_cloud_m':float(np.mean(distances)),'all_vertices_match_saved_pre_mesh_cloud':True,'texture_images':len([i for i in bpy.data.images if i.size[0]>0])}
(OUT/'export_reimport_validation.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
