#!/usr/bin/env python3
"""Rebuild the reviewed 5000-total-quad sedan with the 0.1.2 per-point gate."""
import argparse,hashlib,json,os,shutil,subprocess,sys,time,uuid
from pathlib import Path
SKILL=Path(__file__).resolve().parents[1];ASSET=SKILL/'assets/car-5000';VERSION=(SKILL/'VERSION').read_text().strip()
def main(argv=None):
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--workdir',type=Path,required=True);a.add_argument('--blender',default=shutil.which('blender'));a.add_argument('--rebuild',action='store_true');a.add_argument('--command',default='Mudelitehas 5000 3 auto 4319');p=a.parse_args(argv)
 if p.command!='Mudelitehas 5000 3 auto 4319':a.error('Only the reviewed 4319 sedan and 5000-total-quad budget are implemented; prepare a new recipe for other subjects.')
 if not p.blender:a.error('Blender 4.5.3 is required')
 work=p.workdir.resolve()
 if work==SKILL or SKILL in work.parents or work in SKILL.parents:a.error('Work directory must be separate from installed skill')
 marker=work/'.mudelitehas-run.json'
 if work.exists() and any(work.iterdir()):
  if not marker.exists() or json.loads(marker.read_text()).get('recipe')!='car-5000':a.error('Refusing an unrelated work directory')
  if not p.rebuild:a.error('This car runner supports explicit --rebuild for an existing marked car run; it does not claim stage caching')
 checks=json.loads((ASSET/'reference-checksums.json').read_text())
 for relative,expected in checks.items():
  if hashlib.sha256((ASSET/relative).read_bytes()).hexdigest()!=expected:raise ValueError('Car reference checksum mismatch: '+relative)
 work.mkdir(parents=True,exist_ok=True);marker.write_text(json.dumps({'recipe':'car-5000','created_with':VERSION}))
 for folder in ['recipe','references']:shutil.copytree(ASSET/folder,work/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 shutil.copy2(SKILL/'scripts/check_multiview.py',work/'recipe/multiview.py')
 out=work/'output';out.mkdir(exist_ok=True);logs=work/'logs';logs.mkdir(exist_ok=True);start=time.perf_counter();env=os.environ.copy();env['OMP_NUM_THREADS']='4'
 manifest={'plugin_version':VERSION,'recipe':'car-5000','command':p.command,'run_id':uuid.uuid4().hex[:12],'quad_budget':5000,'budget_scope':'whole_model','status':'running','stages':[],'reference_hashes':checks}
 def save():manifest['seconds']=round(time.perf_counter()-start,3);(out/'run_manifest.json').write_text(json.dumps(manifest,indent=2))
 def stage(name,cmd):
  print('Running '+name,flush=True);t=time.perf_counter()
  with (logs/(name+'.log')).open('w') as f:r=subprocess.run(cmd,cwd=work,env=env,stdout=f,stderr=subprocess.STDOUT)
  manifest['stages'].append({'name':name,'exit_code':r.returncode,'seconds':round(time.perf_counter()-t,3)});save()
  if r.returncode:raise RuntimeError(name+' failed; see logs/'+name+'.log')
 def blender(script):return [p.blender,'--background','--threads','4','--factory-startup','--python-exit-code','1','--python',str(work/'recipe'/script)]
 try:
  save();stage('preflight',[p.blender,'--background','--factory-startup','--python-exit-code','1','--python-expr',"import bpy; assert bpy.app.version==(4,5,3),'Expected Blender 4.5.3'"])
  stage('reconstruction_and_pre_mesh_gate',[sys.executable,str(work/'recipe/reconstruct.py')])
  gate=json.loads((out/'three_direction_gate.json').read_text());manifest['three_direction_gate']=gate;save()
  stage('build_export_render',blender('build.py'));stage('GLB_reimport',blender('verify_export.py'))
  manifest['status']='completed';save();stage('reports_and_package',[sys.executable,str(work/'recipe/finish.py')]);manifest['status']='completed';save();print(json.dumps({'status':'completed','version':VERSION,'output':str(out),'three_axis_support_percent':gate['three_axis_support_percent']}));return 0
 except Exception as error:
  manifest['status']='failed';manifest['error']=str(error);save();print(str(error),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
