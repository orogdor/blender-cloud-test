#!/usr/bin/env python3
"""Create a local feedback bundle and a GitHub issue link; never send automatically."""
import argparse,json,hashlib,platform,urllib.parse,zipfile
from pathlib import Path
SKILL=Path(__file__).resolve().parents[1];VERSION=(SKILL/'VERSION').read_text().strip();REPO='https://github.com/orogdor/blender-cloud-test'
def collect(run,category,description,frame=None):
 out=run/'output';manifest=json.loads((out/'run_manifest.json').read_text()) if (out/'run_manifest.json').exists() else {};validation=json.loads((out/'validation.json').read_text()) if (out/'validation.json').exists() else {}
 report={'plugin_version':manifest.get('plugin_version',VERSION),'run_id':manifest.get('run_id','unknown'),'recipe':'teddy-walk','category':category,'description':description,'frame':frame,'fingerprints':manifest.get('fingerprints',{}),'reference_hashes':manifest.get('reference_hashes',{}),'artifact_sha256':manifest.get('artifact_sha256',{}),'runtime':{'blender':manifest.get('blender_version','unknown'),'python':manifest.get('python_version',platform.python_version())},'status':manifest.get('status','unknown'),'error':manifest.get('error'),'stages':manifest.get('stages',[]),'model_checks':{k:validation[k] for k in ['primary_quad_faces','bones','loop_seam_m','minimum_z_m','skin_stretch_p999_edges_over_3mm','gait_phase'] if k in validation}}
 return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workdir',required=True,type=Path);p.add_argument('--category',choices=['shape','rig','animation','material','export','performance'],required=True);p.add_argument('--description',required=True);p.add_argument('--frame',type=int);p.add_argument('--output',type=Path);a=p.parse_args();run=a.workdir.resolve()
 if not (run/'.mudelitehas-run.json').exists():p.error('Not a marked Mudelitehas run directory.')
 report=collect(run,a.category,a.description,a.frame);dest=a.output or run/'feedback'/('mudelitehas-'+report['run_id']+'.zip');dest.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('feedback.json',json.dumps(report,ensure_ascii=False,indent=2))
 title='[0.1 feedback] '+a.category+': '+a.description[:90];url=REPO+'/issues/new?'+urllib.parse.urlencode({'template':'mudelitehas-feedback.yml','title':title,'version':report['plugin_version'],'run_id':report['run_id'],'category':a.category,'description':a.description,'frame':str(a.frame) if a.frame is not None else ''})
 print(json.dumps({'bundle':str(dest),'issue_url':url,'sent':False},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
