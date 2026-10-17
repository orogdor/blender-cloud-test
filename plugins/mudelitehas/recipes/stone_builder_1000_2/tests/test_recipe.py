"""True unit/integration checks. They use SYNTHETIC fixtures and never certify a model."""
from __future__ import annotations
import json,sys,tempfile,unittest,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
PKG=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PKG/'recipe'))
from common import read_inputs,sha256,write_json


def make_fixture(root):
    root=Path(root);refs=root/'references';refs.mkdir(parents=True,exist_ok=True)
    views=[]
    for direction in ('front','right','top'):
        im=Image.new('RGB',(512,512),{'front':'#9a896b','right':'#819c85','top':'#776c6a'}[direction]);im.save(refs/(direction+'.png'))
        mask=Image.new('L',(512,512),0);pen=ImageDraw.Draw(mask)
        scale=215
        def py(y):return 470-round(y*scale)
        if direction=='front':
            pen.ellipse([256-30,py(1.81),256+30,py(1.45)],fill=255)
            pen.rounded_rectangle([201,py(1.46),311,py(.78)],radius=16,fill=255)
            pen.rectangle([256-round(1.1*scale),py(1.45),256+round(1.1*scale),py(1.30)],fill=255)
            pen.rounded_rectangle([214,py(.84),250,py(.03)],radius=13,fill=255)
            pen.rounded_rectangle([262,py(.84),298,py(.03)],radius=13,fill=255)
        elif direction=='right':
            pen.ellipse([225,py(1.81),287,py(1.45)],fill=255)
            pen.rounded_rectangle([210,py(1.47),302,py(.78)],radius=16,fill=255)
            pen.rounded_rectangle([230,py(.86),284,py(.03)],radius=12,fill=255)
        else:
            pen.ellipse([224,226,288,286],fill=255)
            pen.rounded_rectangle([209,211,303,300],radius=20,fill=255)
            pen.rounded_rectangle([256-round(1.1*scale),240,256+round(1.1*scale),278],radius=7,fill=255)
        mask.save(refs/(direction+'_mask.png'))
        views.append(dict(direction=direction,source_type='reviewed_generated',image='references/'+direction+'.png',mask='references/'+direction+'_mask.png',image_sha256=sha256(refs/(direction+'.png')),mask_sha256=sha256(refs/(direction+'_mask.png')),origin_pixels=[256,256 if direction=='top' else 470],pixels_per_meter=215,is_mirror_copy=False,landmark_notes=['ankle: synthetic', 'shoulder: synthetic','head: synthetic']))
    m=dict(recipe='stone-builder-1000-2',character='stone_age_builder',quad_budget=1000,level=2,rest_pose='T-pose',same_identity=True,same_pose=True,registered_scale=True,limbs_separated=True,synthetic_test=True,visual_review={'status':'approved','reviewer':'SYNTHETIC UNIT TEST ONLY','reviewed_at':'fixture-run','notes':'Unit test data: do not use for model validation'},views=views)
    file=root/'manifest.json';write_json(file,m);return file

class StoneBuilderRecipeTest(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.manifest=make_fixture(Path(self.temp.name))
    def test_reject_synthetic_production(self):
        with self.assertRaisesRegex(ValueError,'Synthetic'):read_inputs(self.manifest)
    def test_reject_unreviewed(self):
        m=json.loads(self.manifest.read_text());m['visual_review']['status']='pending';write_json(self.manifest,m)
        with self.assertRaisesRegex(ValueError,'visual review'):read_inputs(self.manifest,allow_synthetic=True)
    def test_reject_wrong_hash(self):
        m=json.loads(self.manifest.read_text());m['views'][0]['image_sha256']='bad';write_json(self.manifest,m)
        with self.assertRaisesRegex(ValueError,'hash'):read_inputs(self.manifest,allow_synthetic=True)
    def test_reject_missing_third_axis(self):
        m=json.loads(self.manifest.read_text());m['views']=m['views'][:2];write_json(self.manifest,m)
        with self.assertRaisesRegex(ValueError,'independent image'):read_inputs(self.manifest,allow_synthetic=True)
    def test_pre_mesh_witness_checker_and_no_unreviewed_glb(self):
        out=Path(self.temp.name)/'output'
        subprocess.run([sys.executable,str(PKG/'recipe/run.py'),'--manifest',str(self.manifest),'--workdir',str(out),'--synthetic-test-only'],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
        gate=json.loads((out/'three_direction_gate.json').read_text())
        m=json.loads((out/'run_manifest.json').read_text())
        self.assertEqual(gate['independent_direction_rank'],3)
        self.assertGreater(gate['point_count'],300)
        self.assertEqual(gate['attempted_views_per_point'],3)
        self.assertFalse(gate['feature_triangulation_proven'])
        self.assertEqual(m['status'],'synthetic_test_only')
        self.assertFalse(list(out.glob('*.glb')))
        self.assertFalse(list(out.glob('*.blend')))

if __name__=='__main__':unittest.main(verbosity=2)
