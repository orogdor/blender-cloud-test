import copy
import json
from pathlib import Path
import random
import tempfile
import unittest
import urllib.error
from shared_recipes import Store, apply, choose, empty_catalog, key, pack, pool, stats

REQ=key('human','stone-age-spearman',1000,2)
def recipe(rid):
    return dict(id=rid,request=REQ,bundle_sha256=rid,bundle_path='bundles/'+rid+'.json',validation_status='accepted',parent_id=None,created_ns=1)
def delivered(c,rid,did,status='accepted'):
    return apply(c,dict(action='delivery',data=dict(id=did,recipe_id=rid,model_sha256='a'*64,validation_status=status,created_ns=1)))
def rate(c,did,score,eid,at=1):
    return apply(c,dict(action='rating',data=dict(id=eid,delivery_id=did,model_sha256='a'*64,shape_score=score,created_ns=at)))
class MemoryGitHub:
    def __init__(self):self.catalog=empty_catalog();self.sha="0";self.bundles={};self.conflict=None
    def read(self):return copy.deepcopy(self.catalog),self.sha
    def write(self,c,sha):
        if self.conflict:
            self.catalog=apply(self.catalog,self.conflict);self.conflict=None;self.sha=str(int(self.sha)+1)
        if sha!=self.sha:raise urllib.error.HTTPError('https://api.github.com',409,'Conflict',None,None)
        self.catalog=copy.deepcopy(c);self.sha=str(int(self.sha)+1)
    def put_bundle(self,m,b):self.bundles[m['id']]=b
    def bundle(self,m):return self.bundles[m['id']]
class SharedTests(unittest.TestCase):
    def test_offline_model_and_feedback_reconnect_together(self):
        class Offline(MemoryGitHub):
            def read(self):raise OSError('offline')
        with tempfile.TemporaryDirectory() as d:
            store=Store(Offline(),d);store.submit(dict(action='recipe',data=recipe('r')))
            delivery=dict(id='d',recipe_id='r',model_sha256='a'*64,validation_status='accepted',created_ns=2)
            op=dict(action='delivery',data=delivery);apply(store.known(),op);store.submit(op)
            rating=dict(id='e',delivery_id='d',model_sha256='a'*64,shape_score=5,created_ns=3)
            op=dict(action='rating',data=rating);apply(store.known(),op);store.submit(op)
            self.assertEqual(len(list(store.pending().glob('*.json'))),3)
            store.client=MemoryGitHub();store.flush();self.assertEqual(len(pool(store.sync(),REQ)),1)
    def test_accepted_gate_cannot_bless_a_different_glb(self):
        from shared_recipes import verify_delivery
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'quality-gate.json').write_text(json.dumps(dict(acceptance_status='accepted')))
            with self.assertRaises(ValueError):verify_delivery(REQ,p/'other.glb',p/'quality-gate.json')

    def seed(self,rid='r'):
        return apply(empty_catalog(),dict(action='recipe',data=recipe(rid)))
    def test_five_and_validation_both_required(self):
        c=self.seed();c=delivered(c,'r','one');c=rate(c,'one',4,'e1');self.assertEqual(pool(c,REQ),[])
        c=delivered(c,'r','two','needs_repair');c=rate(c,'two',5,'e2');self.assertEqual(pool(c,REQ),[])
        c=delivered(c,'r','three');c=rate(c,'three',5,'e3');self.assertEqual(len(pool(c,REQ)),1)
    def test_corrected_rating_removes_old_five(self):
        c=delivered(self.seed(),'r','d');c=rate(c,'d',5,'e1');c=rate(c,'d',2,'e2',at=0)
        self.assertEqual(pool(c,REQ),[]);self.assertEqual(stats(c)['r']['count'],1)
    def test_pool_keeps_ten_and_archives_all(self):
        c=empty_catalog()
        for i in range(12):
            rid=str(i);c=apply(c,dict(action='recipe',data=recipe(rid)));c=delivered(c,rid,rid);c=rate(c,rid,5,rid)
        self.assertEqual(len(pool(c,REQ)),10);self.assertEqual(len(c['recipes']),12)
        for i in range(6):
            did='extra'+str(i);c=delivered(c,'11',did);c=rate(c,did,5,did)
        self.assertEqual(pool(c,REQ)[0]['recipe']['id'],'11')
    def test_exact_budget_and_kind(self):
        c=rate(delivered(self.seed(),'r','d'),'d',5,'e')
        self.assertEqual(pool(c,key('human','archer',1000,2)),[])
        self.assertEqual(pool(c,key('human','stone-age-spearman',2000,2)),[])
    def test_rotation_avoids_last_and_samples_alternatives(self):
        c=self.seed()
        for rid in ['r','s','t']:
            if rid!='r':c=apply(c,dict(action='recipe',data=recipe(rid)))
            c=rate(delivered(c,rid,rid),rid,5,rid)
        seen={choose(c,REQ,'r',random.Random(i))['recipe']['id'] for i in range(20)}
        self.assertEqual(seen,{'s','t'})
    def test_unknown_delivery_and_bool_rating_rejected(self):
        c=self.seed()
        with self.assertRaises(ValueError):rate(c,'missing',5,'e')
        c=delivered(c,'r','d')
        with self.assertRaises(ValueError):rate(c,'d',True,'e')
        op=dict(action='rating',data=dict(id='e',delivery_id='d',model_sha256='b'*64,shape_score=5,created_ns=1))
        with self.assertRaises(ValueError):apply(c,op)
    def test_duplicate_event_idempotent(self):
        c=delivered(self.seed(),'r','d');c=rate(c,'d',5,'e');self.assertEqual(c,rate(c,'d',5,'e'))
    def test_two_devices_conflict_merges_without_loss(self):
        client=MemoryGitHub();client.conflict=dict(action='recipe',data=recipe('other-device'))
        with tempfile.TemporaryDirectory() as d:
            result=Store(client,d).submit(dict(action='recipe',data=recipe('this-device')))
            self.assertEqual(result['status'],'synced');self.assertEqual(set(client.catalog['recipes']),{'other-device','this-device'})
    def test_offline_queue_preserves_dependencies(self):
        class Offline(MemoryGitHub):
            def read(self):raise OSError('offline')
        with tempfile.TemporaryDirectory() as d:
            store=Store(Offline(),d);self.assertEqual(store.submit(dict(action='recipe',data=recipe('r')))['status'],'pending_sync')
            self.assertEqual(len(list(store.pending().glob('*.json'))),1)
            store.client=MemoryGitHub();store.flush();self.assertIn('r',store.sync()['recipes'])
    def test_network_failure_is_not_remote_recipe_absence(self):
        class Offline(MemoryGitHub):
            def read(self):raise OSError('offline')
        with tempfile.TemporaryDirectory() as d:
            store=Store(Offline(),d)
            with self.assertRaises(OSError):store.sync()
            with self.assertRaises(ValueError):store.sync(offline=True)
    def test_source_versions_content_addressed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'build.py').write_text('print(1)')
            a,b=pack(p,REQ,'needs_repair');a2,_=pack(p,REQ,'accepted');self.assertEqual(a['id'],a2['id'])
            (p/'build.py').write_text('print(2)');c,_=pack(p,REQ,'accepted',a['id']);self.assertNotEqual(a['id'],c['id'])
    def test_parent_compatibility(self):
        m=recipe('child');m['parent_id']='absent'
        with self.assertRaises(ValueError):apply(self.seed(),dict(action='recipe',data=m))
if __name__=='__main__':unittest.main()
