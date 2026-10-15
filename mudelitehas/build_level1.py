"""Blender basic level 1: closed surface -> exact quad budget -> GLB and BLEND."""
import argparse,json,math,runpy,sys
from pathlib import Path
import bpy
from mathutils import Vector

def main():
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--request',type=Path,required=True);ap.add_argument('--output',type=Path,default=Path('output/mudelitehas_level1'));args=ap.parse_args(argv)
    request=json.loads(args.request.read_text());out=args.output;out.mkdir(parents=True,exist_ok=True)
    if request['level']!=1:ap.error('See Blenderi retsept on taseme 1 jaoks.')
    if request['animation_requested']:ap.error('Taseme 1 põhiretsept loob staatilise meshi. Animatsiooniga mudelile koosta eraldi lihtne luustik või kasuta taset 2/3.')
    if request.get('pose_plan',{}).get('requires_rig'):ap.error('Tellitud poos vajab luustikuga poseerimist ehituspoosist; staatiline põhiretsept seda ei asenda.')
    target=request['quad_faces']
    if target<256 or target%2:ap.error('Praegune täpse nelinurkade arvu retsept toetab paarisarvu alates 256-st.')
    # Reuse validated geometry helpers; run_path does not run the character build.
    helper=Path(__file__).resolve().parents[1]/'teddy_mudelitehas'/'build_teddy.py'
    env=runpy.run_path(str(helper),run_name='mudelitehas_quad_helpers')
    env['exact_quads'].__globals__['TARGET_BASE']=target
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    source=json.loads((out/'05_surface.json').read_text());mesh=bpy.data.meshes.new('Level1_surface');mesh.from_pydata(source['points'],[],source['triangles']);mesh.update()
    ob=bpy.data.objects.new(request['description'],mesh);bpy.context.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    height=max(v.co.z for v in mesh.vertices)-min(v.co.z for v in mesh.vertices)
    rem=ob.modifiers.new('Close_surface','REMESH');rem.mode='VOXEL';rem.voxel_size=height/110;rem.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=rem.name)
    bpy.ops.object.quadriflow_remesh(target_faces=int(target*.85),seed=0,use_preserve_sharp=False,use_preserve_boundary=False)
    env['exact_quads'](ob)
    smooth=ob.modifiers.new('Smooth_shape','SMOOTH');smooth.factor=.25;smooth.iterations=2;bpy.ops.object.modifier_apply(modifier=smooth.name)
    report=env['validate'](ob,True);assert report['faces']==target,report
    report.update({'level':1,'quad_budget':target,'description':request['description'],'rig':False,'materials':'one basic surface material'})
    mat=bpy.data.materials.new('Level1_basic_color');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.35,.19,.08,1);bs.inputs['Roughness'].default_value=.8;ob.data.materials.append(mat)
    for p in ob.data.polygons:p.use_smooth=True
    bpy.ops.export_scene.gltf(filepath=str(out/'Model_Tase1.glb'),export_format='GLB',use_selection=True,export_animations=False)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=False;scene.render.resolution_x=512;scene.render.resolution_y=640;scene.render.resolution_percentage=100
    mesh=ob.data
    low=Vector(tuple(min(v.co[i] for v in mesh.vertices) for i in range(3)));high=Vector(tuple(max(v.co[i] for v in mesh.vertices) for i in range(3)));center=(low+high)/2
    def aim(o):o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add(location=center+Vector((height*1.8,-height*3,height*.8)));cam=bpy.context.object;aim(cam);cam.data.type='ORTHO';cam.data.ortho_scale=max((high-low).length,height)*1.3;scene.camera=cam
    for offset,energy in [((2,-3,4),500),((-3,-1,2),300)]:
        bpy.ops.object.light_add(type='AREA',location=center+Vector(offset));light=bpy.context.object;light.data.energy=energy;light.data.size=3;aim(light)
    scene.world.color=(.16,.16,.16);scene.render.filepath=str(out/'Preview_Tase1.png');bpy.ops.render.render(write_still=True)
    (out/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));ob['validation']=json.dumps(report)
    for selected in bpy.context.selected_objects:selected.select_set(False)
    ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.wm.save_as_mainfile(filepath=str((out/'Model_Tase1.blend').resolve()));print(report,flush=True)

if __name__=='__main__':main()
