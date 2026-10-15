import importlib.util,json,subprocess,sys,tempfile,unittest,zipfile,urllib.parse,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];PKG=ROOT/'plugins/mudelitehas';SKILL=PKG/'skills/mudelitehas'
def module(name):
 spec=importlib.util.spec_from_file_location('test_'+name,SKILL/'scripts'/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class PackageTests(unittest.TestCase):
 def test_exact_canonical_files(self):
  root=PKG/'examples/teddy-walk';manifest=json.loads((root/'canonical-manifest.json').read_text());self.assertEqual(manifest['version'],'0.1.0')
  for name,item in manifest['files'].items():
   p=root/name;self.assertEqual(p.stat().st_size,item['bytes'],name);self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),item['sha256'],name)
 def test_references_and_scope(self):
  run=module('run');run.reference_integrity();self.assertEqual((SKILL/'VERSION').read_text().strip(),'0.1.0');request=json.loads((run.ASSET/'request.json').read_text());self.assertEqual(request['quad_faces'],10000);self.assertEqual(request['rest_pose'],'biped T-pose')
 def test_wrong_subject_is_rejected_before_writing(self):
  with tempfile.TemporaryDirectory() as d:
   work=Path(d)/'run';p=subprocess.run([sys.executable,str(SKILL/'scripts/run.py'),'--workdir',str(work),'--command','Mudelitehas 10000 3 sitsiv koer animatsiooniga'],capture_output=True,text=True);self.assertEqual(p.returncode,2);self.assertFalse(work.exists());self.assertIn('supports only',p.stderr)
 def test_feedback_preserves_frame_zero_and_omits_private_inputs(self):
  with tempfile.TemporaryDirectory() as d:
   run=Path(d);(run/'output').mkdir();(run/'.mudelitehas-run.json').write_text('{"recipe":"teddy-walk"}');(run/'output/run_manifest.json').write_text(json.dumps({'plugin_version':'0.1.0','run_id':'test-run','status':'failed','environment':{'SECRET':'not-for-feedback'},'error':'pose failed','fingerprints':{'pose':'abc'}}));(run/'private-model.glb').write_bytes(b'private model');(run/'logs').mkdir();(run/'logs/raw.log').write_text('private log')
   p=subprocess.run([sys.executable,str(SKILL/'scripts/feedback.py'),'--workdir',str(run),'--category','rig','--description','T-poosi käpa volt','--frame','0'],check=True,capture_output=True,text=True);r=json.loads(p.stdout);self.assertFalse(r['sent']);self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlparse(r['issue_url']).query)['frame'],['0'])
   with zipfile.ZipFile(r['bundle']) as z:
    self.assertEqual(z.namelist(),['feedback.json']);data=z.read('feedback.json').decode();self.assertNotIn('not-for-feedback',data);self.assertNotIn('private log',data);self.assertNotIn('private model',data);self.assertEqual(json.loads(data)['frame'],0)
 def test_cache_fingerprints_cover_stages(self):
  f=module('run').fingerprints();self.assertEqual(set(f),{'reconstruction','mesh','skin','pose','finish','render','version'});self.assertTrue(all(len(v)==64 for k,v in f.items() if k!='version'))
 def test_pinned_runtime_digest(self):
  m=module('install_runtime');self.assertEqual(len(m.SHA256),64);self.assertEqual(m.SHA256,'975c58fcb244273838534bba771e64ad87739216b0f9b39a888531a49a72d845')
if __name__=='__main__':unittest.main()
