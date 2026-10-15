import importlib.util,json,tempfile,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];SKILL=ROOT/'plugins/mudelitehas/skills/mudelitehas'
spec=importlib.util.spec_from_file_location('multiview',SKILL/'scripts/check_multiview.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class MultiviewTests(unittest.TestCase):
 def fixture(self,path,change=None):
  j=np.array([[[1,0,0],[0,1,0]],[[1,0,0],[0,0,1]],[[0,1,0],[0,0,1]]],float);b=np.zeros((3,2));p=np.array([[0,0,0],[1,1,1]],float);r=np.array([[1,1,1],[1,-5,1]],float)
  c={'view_order':['top','side','front'],'projection_jacobians':j.tolist(),'projection_offsets':b.tolist()};d={'points':p,'reference_pixels':np.einsum('nd,vkd->nvk',p,j),'signed_silhouette_distance_px':r,'view_support':r>=-3,'axis_support':r>=-3}
  if change:change(c,d)
  np.savez(path/'cloud.npz',**d);(path/'calibration.json').write_text(json.dumps(c));return path/'cloud.npz',path/'calibration.json'
 def test_conflicts_remain_reported_and_do_not_become_feature_matches(self):
  with tempfile.TemporaryDirectory() as d:
   r=m.validate_cloud(*self.fixture(Path(d)));self.assertEqual(r['unresolved_points'],1);self.assertFalse(r['geometry_support_complete']);self.assertFalse(r['feature_triangulation_proven'])
 def test_front_back_do_not_add_a_third_direction(self):
  def change(c,d):c['projection_jacobians'][2]=c['projection_jacobians'][1]
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'independent'):m.validate_cloud(*self.fixture(Path(d),change))
 def test_fabricated_witness_pixel_is_rejected(self):
  def change(c,d):d['reference_pixels'][0,0,0]=100
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'witnesses'):m.validate_cloud(*self.fixture(Path(d),change))
 def test_inflated_support_is_rejected(self):
  def change(c,d):d['axis_support'][:]=True
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'Axis support'):m.validate_cloud(*self.fixture(Path(d),change))
 def test_every_level_and_subject_gets_new_point_policy(self):
  import sys
  sys.path.insert(0,str(ROOT));from mudelitehas.command import parse_command
  for level in [1,2,3]:
   for subject in ['auto','koer','inimene']:
    r=parse_command(f'Mudelitehas 5000 {level} {subject}');self.assertEqual(r['workflow_version'],'0.1.2');self.assertEqual(r['point_placement_policy']['minimum_independent_directions'],3)
 def test_reviewed_car_preserves_its_reported_conflicts(self):
  cloud=ROOT/'plugins/mudelitehas/examples/car-5000/04_point_cloud.npz';cal=ROOT/'plugins/mudelitehas/examples/car-5000/calibration.json'
  r=m.validate_cloud(cloud,cal);self.assertEqual(r['point_count'],83747);self.assertEqual(r['unresolved_points'],17399)

if __name__=='__main__':unittest.main()
