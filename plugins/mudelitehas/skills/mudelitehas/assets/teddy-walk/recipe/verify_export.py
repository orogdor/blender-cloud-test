"""Verify exported skeletal + corrective animation after GLB reimport."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
OUT=Path(__file__).resolve().parent.parent/'output';s=np.load(OUT/'deformation_samples.npz');report={}
for name in ['Jalutav_Mangukaru_10000.glb','Jalutav_Mangukaru_LOD.glb']:
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.context.scene.render.fps=24;bpy.ops.import_scene.gltf(filepath=str(OUT/name));meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];body=max(meshes,key=lambda o:len(o.data.polygons));rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1
 poses=[];errors=[];frames=[1,13,25,37,49]
 for f in frames:
  bpy.context.scene.frame_set(f);ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();a=np.array([tuple(ev.matrix_world@v.co) for v in me.vertices]);ev.to_mesh_clear();assert np.isfinite(a).all();poses.append(a);idx=list(s['frames']).index(f);ref=s['poses'][idx];tree=KDTree(len(ref))
  for i,p in enumerate(ref):tree.insert(Vector(p),i)
  tree.balance();errors.append(max(tree.find(Vector(p))[2] for p in a))
 a=np.array(poses);r={'armatures':len(rigs),'bones':len(rigs[0].data.bones),'morph_targets':len(body.data.shape_keys.key_blocks)-1,'frames_checked':frames,'loop_seam_m':float(abs(a[-1]-a[0]).max()),'max_skin_motion_m':float(np.linalg.norm(a-a[0],axis=2).max()),'minimum_z_m':float(a[:,:,2].min()),'distance_to_source_vertices_m':errors};assert r['loop_seam_m']<.0001 and r['max_skin_motion_m']>.1 and r['minimum_z_m']>-.003,r
 if '10000' in name:assert max(errors)<.001,r
 report[name]=r;print(name,r,flush=True)
(OUT/'export_reimport_validation.json').write_text(json.dumps(report,indent=2))
