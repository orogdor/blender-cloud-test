"""Pose routing, reference provenance and organic surface geometry checks."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
import numpy as np
try:
    from .command import parse_command
    from .pose_plan import validate_reference_manifest
    from .organic_surface import round_organic_sections
except ImportError:
    from command import parse_command
    from pose_plan import validate_reference_manifest
    from organic_surface import round_organic_sections

class PoseWorkflowTests(unittest.TestCase):
    def test_dog_uses_standing_reconstruction_and_sitting_target(self):
        r=parse_command('Mudelitehas 100000 3 sitsiv koer animatsiooniga')
        self.assertEqual(r['pose_plan']['reconstruction_pose'],'quadruped_stand')
        self.assertEqual(r['pose_plan']['target_pose_kind'],'sit_pretty')
        self.assertTrue(r['pose_plan']['requires_rig'])
        self.assertEqual(r['pipeline'][1],'four consistent views in rig-friendly rest pose')
    def test_humanoid_uses_t_pose_even_with_underscores(self):
        r=parse_command('Mudelitehas 8000 2 vikingi_sõdalane')
        self.assertEqual(r['pose_plan']['reconstruction_pose'],'humanoid_t')
        self.assertTrue(r['pose_plan']['requires_rig'])
    def test_custom_creature_does_not_guess_skeleton(self):
        r=parse_command('Mudelitehas 20000 3 tulnukas')
        self.assertTrue(r['pose_plan']['requires_anatomy_review'])
        with self.assertRaises(ValueError):validate_reference_manifest(r,{},'unused')
    def test_rigid_object_keeps_basic_pipeline(self):
        r=parse_command('Mudelitehas 5000 1 ralliauto')
        self.assertEqual(r['pipeline'],['2D concept','four consistent views','point cloud','mesh'])
        self.assertFalse(r['pose_plan']['requires_rig'])
    def test_all_levels_preserve_neutral_pose_policy(self):
        for level in (1,2,3):
            r=parse_command(f'Mudelitehas 5000 {level} istuv koer')
            self.assertTrue(r['pose_plan']['neutral_reference_required'])
            self.assertTrue(r['pose_plan']['requires_rig'])
    def test_review_and_hash_are_required_but_not_pixel_verification(self):
        # Synthetic bytes test only provenance logic, not an actual image review.
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'synthetic-input.b85';p.write_bytes(b'synthetic test fixture')
            r=parse_command('Mudelitehas 5000 1 koer')
            manifest={'reference_role':'rest_pose','body_plan':'quadruped','rest_pose':'quadruped_stand','views':['front','left','back','right'],
                'source_input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'same_identity':True,'same_pose':True,'registered_scale':True,'limbs_separated':True,
                'visual_review':{'status':'approved','reviewer':'synthetic_unit_test_only'}}
            result=validate_reference_manifest(r,manifest,p)
            self.assertFalse(result['visual_pose_verified_by_code'])
            for field,value in [('rest_pose','sit_pretty'),('same_pose',False),('limbs_separated','true'),('source_input_sha256','bad')]:
                broken=copy.deepcopy(manifest);broken[field]=value
                with self.assertRaises(ValueError):validate_reference_manifest(r,broken,p)
            broken=copy.deepcopy(manifest);broken['visual_review']['status']='pending'
            with self.assertRaises(ValueError):validate_reference_manifest(r,broken,p)
            with self.assertRaises(ValueError):validate_reference_manifest({'schema_version':1},{},p)
    def test_rounding_removes_box_corner_without_removing_axis_extent(self):
        x=y=np.linspace(-1.4,1.4,81);z=np.linspace(-.4,.4,5)
        fm=np.tile(np.abs(x)<1,(len(z),1));sm=np.tile(np.abs(y)<1,(len(z),1))
        phi=np.broadcast_to(np.minimum(1-np.abs(x[:,None,None]),1-np.abs(y[None,:,None])),(len(x),len(y),len(z))).copy()
        result=round_organic_sections(phi,x,y,z,fm,fm,sm,sm)
        i=int(np.argmin(abs(x-.8)));mid=len(y)//2
        self.assertGreater(phi[i,i,2],0);self.assertLess(result[i,i,2],0)
        self.assertGreater(result[i,mid,2],0)
    def test_rounding_preserves_gap_between_limbs(self):
        x=y=np.linspace(-1,1,81);z=np.linspace(-.3,.3,5)
        fm=np.tile((np.abs(x-.5)<.15)|(np.abs(x+.5)<.15),(len(z),1));sm=np.tile(np.abs(y)<.2,(len(z),1))
        result=round_organic_sections(np.ones((81,81,5)),x,y,z,fm,fm,sm,sm)
        self.assertLess(result[40,40,2],0)
        self.assertGreater(result[60,40,2],0)

if __name__=='__main__':unittest.main()
