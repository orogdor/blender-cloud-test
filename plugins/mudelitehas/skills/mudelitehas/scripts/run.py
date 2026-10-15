#!/usr/bin/env python3
"""Portable, resumable runner for the validated Mudelitehas 0.1 teddy recipe."""
import argparse,ast,hashlib,json,os,platform,shutil,subprocess,sys,time,uuid
from pathlib import Path
SKILL=Path(__file__).resolve().parents[1];ASSET=SKILL/'assets/teddy-walk';VERSION=(SKILL/'VERSION').read_text().strip()
def digest(*parts):
 h=hashlib.sha256()
 for p in parts:h.update(p if isinstance(p,bytes) else str(p).encode());h.update(b'\0')
 return h.hexdigest()
def filehash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def function_hash(path,names):
 tree=ast.parse(Path(path).read_text());found={n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};return digest(*(found[n] for n in names))
def fingerprints():
 p=ASSET/'recipe/build.py';refs=json.loads((ASSET/'reference-checksums.json').read_text());reconstruction=digest((ASSET/'recipe/reconstruct.py').read_bytes(),(ASSET/'request.json').read_bytes(),json.dumps(refs,sort_keys=True));mesh=digest(reconstruction,function_hash(p,['mesh_stage','create_rig']),(ASSET/'recipe/mesh_utilities.py').read_bytes());skin=digest(mesh,function_hash(p,['skin','bind_correction']));pose=digest(skin,function_hash(p,['set_pose','animate','check']));finish=digest(function_hash(p,['bake_joint_shapes','coat','face','short_fibers','make_lod','export_glb']));render=digest(function_hash(p,['studio','controls','preview']));return dict(reconstruction=reconstruction,mesh=mesh,skin=skin,pose=pose,finish=finish,render=render,version=VERSION)
def reference_integrity():
 checks=json.loads((ASSET/'reference-checksums.json').read_text())
 for relative,sha in checks.items():
  path=ASSET/relative
  if not path.is_file() or filehash(path)!=sha:raise ValueError('Bundled reference checksum mismatch: '+relative)
 return checks

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workdir',type=Path,required=True);parser.add_argument('--blender',default=shutil.which('blender'));parser.add_argument('--mode',choices=['resume','rebuild','verify'],default='resume');parser.add_argument('--preview',choices=['full','quick','none'],default='quick');parser.add_argument('--command',default=json.loads((ASSET/'request.json').read_text())['command']);args=parser.parse_args(argv)
 request=json.loads((ASSET/'request.json').read_text())
 if args.command.strip()!=request['command']:parser.error('Version 0.1 supports only the bundled 10000-quad walking teddy recipe. Do not substitute a different subject or budget.')
 if not args.blender:parser.error('Blender 4.5.3 is required; pass --blender /path/to/blender.')
 reference_integrity();work=args.workdir.resolve()
 if work==ASSET or ASSET in work.parents or work in ASSET.parents:parser.error('Work directory must be separate from the installed skill.')
 marker=work/'.mudelitehas-run.json'
 if work.exists() and any(work.iterdir()) and not marker.exists():parser.error('Use an empty directory or an existing marked Mudelitehas run; existing files will not be overwritten.')
 work.mkdir(parents=True,exist_ok=True)
 if marker.exists():
  identity=json.loads(marker.read_text())
  if identity.get('recipe')!='teddy-walk':parser.error('Run directory belongs to a different recipe.')
 else:marker.write_text(json.dumps({'recipe':'teddy-walk','created_with':VERSION}))
 for folder in ['recipe','references']:shutil.copytree(ASSET/folder,work/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 out=work/'output';cache=work/'cache';logs=work/'logs';out.mkdir(exist_ok=True);cache.mkdir(exist_ok=True);logs.mkdir(exist_ok=True);statepath=cache/'runner_state.json';old=json.loads(statepath.read_text()) if statepath.exists() else {};keys=fingerprints();run_id=uuid.uuid4().hex[:12];events=[];env=os.environ.copy();env['MUDELITEHAS_PREVIEW']=args.preview;start=time.perf_counter()
 manifest={'plugin_version':VERSION,'run_id':run_id,'recipe':'teddy-walk','command':request['command'],'quad_budget':10000,'budget_scope':'primary_body','reference_hashes':json.loads((ASSET/'reference-checksums.json').read_text()),'fingerprints':keys,'python_version':platform.python_version(),'mode':args.mode,'preview':args.preview,'status':'running','stages':events}
 def save():manifest['seconds']=time.perf_counter()-start;(out/'run_manifest.json').write_text(json.dumps(manifest,indent=2))
 def stage(name,cmd):
  print('Running '+name,flush=True);t=time.perf_counter()
  with (logs/(name+'.log')).open('w') as f:r=subprocess.run(cmd,cwd=work,env=env,stdout=f,stderr=subprocess.STDOUT)
  event={'name':name,'seconds':round(time.perf_counter()-t,3),'exit_code':r.returncode};events.append(event);save()
  if r.returncode:raise RuntimeError(name+' failed; see logs/'+name+'.log')
 def blender(mode):return [args.blender,'--background','--threads','4','--factory-startup','--python-exit-code','1','--python',str(work/'recipe/build.py'),'--',mode]
 def skip(name):events.append({'name':name,'cached':True});print('Cached '+name,flush=True)
 try:
  expr="import sys,os; sys.path.insert(0,os.environ.get('MUDELITEHAS_PYTHONPATH','')); import bpy,json,numpy,PIL; assert bpy.app.version == (4,5,3), 'Expected Blender 4.5.3'; import addon_utils; assert any(m.__name__=='io_scene_gltf2' for m in addon_utils.modules()); print('MUDELITEHAS_PREFLIGHT '+json.dumps({'blender':bpy.app.version_string,'numpy':numpy.__version__,'pillow':PIL.__version__}))"
  stage('preflight',[args.blender,'--background','--factory-startup','--python-exit-code','1','--python-expr',expr]);manifest['blender_version']='4.5.3'
  if args.mode=='rebuild':
   for folder in [out,cache]:shutil.rmtree(folder);folder.mkdir()
   old={}
  need_rec=args.mode!='verify' and (old.get('reconstruction')!=keys['reconstruction'] or not all((out/n).exists() for n in ['04_point_cloud.npz','05_surface.json','pipeline.json']))
  if need_rec:stage('reconstruction',[sys.executable,str(work/'recipe/reconstruct.py')])
  else:skip('reconstruction')
  models=['Jalutav_Mangukaru_10000.glb','Jalutav_Mangukaru_LOD.glb','Jalutav_Mangukaru_10000.blend','validation.json','deformation_samples.npz'];have_models=all((out/n).is_file() for n in models)
  changed_mesh=old.get('mesh')!=keys['mesh'];changed_skin=old.get('skin')!=keys['skin'];changed_pose=old.get('pose')!=keys['pose'];changed_finish=old.get('finish')!=keys['finish'];pose_cache=(cache/'Walk_review.blend').exists()
  if args.mode!='verify':
   if changed_mesh:
    for name in ['Neutral_10000.blend','mesh_fingerprint.sha256']:(cache/name).unlink(missing_ok=True)
   motion_only=have_models and pose_cache and changed_pose and not changed_mesh and not changed_skin and not changed_finish and not need_rec
   if motion_only:stage('pose_update',blender('motion-update'))
   else:
    if need_rec or changed_mesh or changed_skin or changed_pose or not pose_cache:stage('pose_gate',blender('probe'))
    else:skip('pose_gate')
    if need_rec or changed_pose or changed_finish or not have_models:stage('finish',blender('finish'))
    else:
     skip('finish')
     if args.preview!='none' and (old.get('render')!=keys['render'] or old.get('preview')!=args.preview or not (out/'Jalutav_Mangukaru_Uus.gif').exists()):stage('preview',blender('render-only'))
  if not all((out/n).is_file() for n in models):raise RuntimeError('Required model outputs are missing; run resume or rebuild first.')
  verifykey=digest(*(filehash(out/n) for n in [models[0],models[1],'deformation_samples.npz']),filehash(work/'recipe/verify_export.py'))
  if old.get('verify')!=verifykey or not (out/'export_reimport_validation.json').exists() or args.mode=='verify':stage('GLB_reimport',[args.blender,'--background','--threads','4','--factory-startup','--python-exit-code','1','--python',str(work/'recipe/verify_export.py')])
  else:skip('GLB_reimport')
  stage('final_checks',blender('finalize'));manifest['status']='completed';manifest['artifact_sha256']={n:filehash(out/n) for n in models[:3]};save();statepath.write_text(json.dumps({**keys,'verify':verifykey,'preview':args.preview},indent=2));print(json.dumps({'status':'completed','version':VERSION,'run_id':run_id,'output':str(out),'seconds':round(manifest['seconds'],2)},indent=2));return 0
 except Exception as e:
  manifest['status']='failed';manifest['error']=str(e).replace(str(work),'${WORKDIR}');save();print('ERROR: '+manifest['error'],file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
