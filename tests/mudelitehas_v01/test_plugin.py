import importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];PKG=ROOT/'plugins/mudelitehas'
spec=importlib.util.spec_from_file_location('package_plugin',PKG/'tools/package_plugin.py');package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)

class PluginTests(unittest.TestCase):
 def test_marketplace_resolves_actual_plugin(self):
  m=json.loads((ROOT/'.agents/plugins/marketplace.json').read_text());entry=m['plugins'][0]
  target=ROOT/entry['source']['path'];self.assertEqual(target.resolve(),PKG.resolve());self.assertEqual(entry['name'],package.validate()['name']);self.assertEqual(entry['policy']['installation'],'AVAILABLE')
 def test_submission_zip_has_root_manifest_and_no_generated_runtime(self):
  with tempfile.TemporaryDirectory() as d:
   path=package.build(Path(d))
   with zipfile.ZipFile(path) as z:
    names=z.namelist();self.assertIn('plugin.json',names);self.assertIn('skills/mudelitehas/SKILL.md',names);self.assertIn('assets/walking-teddy.png',names)
    self.assertFalse(any('..' in Path(n).parts or n.startswith('/') or '__pycache__' in n or n.endswith(('.pyc','.blend','.glb')) for n in names));self.assertFalse(any(n.startswith('examples/') for n in names))
    self.assertEqual(json.loads(z.read('plugin.json'))['version'],'0.1.2')
 def test_engine_updated_and_historical_canonical_model_remains_original(self):
  self.assertEqual((PKG/'skills/mudelitehas/VERSION').read_text().strip(),'0.1.2')
  self.assertEqual(json.loads((PKG/'examples/teddy-walk/canonical-manifest.json').read_text())['version'],'0.1.0')

if __name__=='__main__':unittest.main()
