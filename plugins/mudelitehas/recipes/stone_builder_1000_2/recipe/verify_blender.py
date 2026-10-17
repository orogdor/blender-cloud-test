"""Reimport the exported GLB into fresh Blender scene and independently audit export."""
import bpy,json,sys
from pathlib import Path
assert bpy.app.version==(4,5,3)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if len(args)!=2 or args[0]!='--workdir':raise ValueError('Expected -- --workdir PATH')
work=Path(args[1]);blender_check=json.loads((work/'blender_validation.json').read_text())
if blender_check['source_quads_total']>1000 or not blender_check['all_source_faces_are_quads'] or blender_check['body_connected_components']!=1:
    raise RuntimeError('Authoring quad budget or connected topology check failed')
file=work/'StoneBuilder_1000_2.glb'
if not file.is_file():raise FileNotFoundError(file)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for x in list(bpy.data.actions):bpy.data.actions.remove(x)
bpy.ops.import_scene.gltf(filepath=str(file))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
if not meshes or not rigs:raise RuntimeError('GLB lacks mesh or skeleton')
if len(rigs)!=1 or len(rigs[0].data.bones)<14:raise RuntimeError('GLB skeleton invalid')
tris=sum(sum(len(p.vertices)-2 for p in mesh.data.polygons) for mesh in meshes)
if tris>2000:raise RuntimeError('Whole GLB is over 2000 triangles (1000 source quads)')
if not any(len(m.vertex_groups)>=12 for m in meshes):raise RuntimeError('Skinning weights absent')
anims=[a.name for a in bpy.data.actions]
for n in ['Idle_Loop','Walk_Loop','Build_Loop']:
    if not any(n in a for a in anims):raise RuntimeError('GLB is missing animation '+n)
# Actual deformed geometry and gameplay-view renders need separate in-engine inspection.
report={'status':'passed','blender_version':'.'.join(map(str,bpy.app.version)),
        'source_quads':blender_check['source_quads_total'],'glb_triangles':tris,
        'rig_bones':len(rigs[0].data.bones),'mesh_nodes':len(meshes),'reimported_action_names':anims,
        'visual_review':'PENDING','animations_playback_in_browser':'NOT_TESTED',
        'method_limitations':['Depth is silhouette-derived plus anatomy priors; no camera calibration from real photogrammetry',
                              'The reconstruction is NOT a per-feature 3D triangulation',
                              'Blender source is all-quads, but exported GLB is triangles']}
(work/'export_reimport_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('Reimport validated',report)
