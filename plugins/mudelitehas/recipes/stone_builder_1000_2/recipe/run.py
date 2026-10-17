#!/usr/bin/env python3
"""Fail-closed Stone Builder recipe orchestrator, for Blender 4.5.3.
Synthetic fixture mode only goes through cloud verification; it never makes an approved GLB.
"""
import argparse,subprocess,sys,json,shutil,os
from pathlib import Path
from common import write_json,read_inputs
ROOT=Path(__file__).resolve().parent
SKILL_CHECK=ROOT.parents[2]/'skills/mudelitehas/scripts/check_multiview.py'
if not SKILL_CHECK.is_file():SKILL_CHECK=ROOT.parent/'vendor/check_multiview.py'

def run(cmd):
    print('RUN:',' '.join(map(str,cmd)),flush=True)
    subprocess.run([str(x) for x in cmd],check=True)

def main():
    a=argparse.ArgumentParser();a.add_argument('--manifest',type=Path,required=True)
    a.add_argument('--workdir',type=Path,required=True)
    a.add_argument('--blender',default=shutil.which('blender'))
    a.add_argument('--cloud-only',action='store_true');a.add_argument('--synthetic-test-only',action='store_true')
    opt=a.parse_args();work=opt.workdir.resolve();work.mkdir(parents=True,exist_ok=True)
    manifest=opt.manifest.resolve()
    report={'recipe':'stone-builder-1000-2','status':'running','stages':[], 'synthetic_test':opt.synthetic_test_only}
    def step(label,command):
        try:run(command);report['stages'].append({'name':label,'status':'passed'})
        except Exception as e:
            report['stages'].append({'name':label,'status':'failed','message':str(e)})
            report['status']='failed';write_json(work/'run_manifest.json',report);raise
    read_inputs(manifest,allow_synthetic=opt.synthetic_test_only)
    step('preflight',[sys.executable,ROOT/'preflight.py','--manifest',manifest,'--output',work/'preflight.json']+(['--allow-synthetic-test'] if opt.synthetic_test_only else []))
    step('registered_cloud',[sys.executable,ROOT/'reconstruct.py','--manifest',manifest,'--workdir',work]+(['--allow-synthetic-test'] if opt.synthetic_test_only else []))
    if not SKILL_CHECK.is_file():raise RuntimeError('Install the real Mudelitehas skill next to this recipe. Missing: '+str(SKILL_CHECK))
    step('three_direction_gate',[sys.executable,SKILL_CHECK,'--cloud',work/'cloud_before_mesh.npz','--calibration',work/'calibration.json','--output',work/'three_direction_gate.json'])
    gate=json.loads((work/'three_direction_gate.json').read_text());report['three_direction_gate']=gate
    # Gate checks source AND witness consistency, but cannot prove a particular surface feature is matched.
    if opt.synthetic_test_only or opt.cloud_only:
        report['status']='synthetic_test_only' if opt.synthetic_test_only else 'cloud_checked_mesh_not_built'
        write_json(work/'run_manifest.json',report)
        print(report['status']);return
    if not opt.blender:raise ValueError('Need Blender 4.5.3, pass --blender path')
    step('blender_version',[opt.blender,'--background','--factory-startup','--python-exit-code','1','--python-expr',"import bpy;assert bpy.app.version==(4,5,3),'Need Blender 4.5.3'"])
    step('retopology_rig_animation_export',[opt.blender,'--background','--factory-startup','--python-exit-code','1','--python',ROOT/'build_blender.py','--','--workdir',work])
    step('glb_reimport_validation',[opt.blender,'--background','--factory-startup','--python-exit-code','1','--python',ROOT/'verify_blender.py','--','--workdir',work])
    check=json.loads((work/'export_reimport_validation.json').read_text());report['export_check']=check
    if check['status']!='passed':raise RuntimeError('GLB export verification failed')
    report['status']='geometry_export_verified_visual_review_pending';write_json(work/'run_manifest.json',report)
    print('Blender pipeline completed. HUMAN VISUAL QA STILL REQUIRED: front/side/top/oblique and animation clips.')
if __name__=='__main__':
    try:main()
    except Exception as e:print(str(e),file=sys.stderr);raise SystemExit(1)
