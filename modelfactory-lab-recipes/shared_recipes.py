#!/usr/bin/env python3
"""Shared, immutable recipe versions and model-bound shape ratings. No mesh execution."""
import argparse
import base64
import copy
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import random
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from lab_isolation import require_lab_path

CONFIG = Path(__file__).parents[1] / 'recipes/shared-store.json'
ACCEPTED = {'accepted', 'accepted_with_limitations'}

def encoded(data):
    return (json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'))+'\n').encode()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def now():
    return time.time_ns()

def key(family, kind, quads, level):
    if not family.strip() or not kind.strip() or type(quads) is not int or quads < 1 or type(level) is not int or level not in (1, 2, 3):
        raise ValueError('Require family, canonical kind, positive quad budget and level 1-3')
    return dict(family=family.strip().casefold(), kind=kind.strip().casefold(), quads=quads, level=level)

def empty_catalog():
    return dict(schema=1, recipes={}, deliveries={}, ratings={})

def validate(c):
    if c.get('schema') != 1 or any(not isinstance(c.get(n), dict) for n in ('recipes','deliveries','ratings')):
        raise ValueError('Unsupported shared catalog')
    return c

def pack(directory, request, validation_status, parent_id=None):
    root = Path(directory).resolve()
    files = {}
    for p in sorted(root.rglob('*')):
        if any(n in {'.git','__pycache__','.venv','node_modules'} for n in p.relative_to(root).parts):
            continue
        if p.is_symlink():
            raise ValueError('Recipe symlinks are unsupported')
        if p.is_file():
            raw=p.read_bytes()
            files[p.relative_to(root).as_posix()] = dict(sha256=digest(raw), base64=base64.b64encode(raw).decode())
    if not files or not any(n.endswith('.py') for n in files):
        raise ValueError('Reproducible recipe implementation is required')
    bundle = dict(schema=1, request=request, files=files)
    raw=encoded(bundle)
    if len(raw)>32*1024*1024:
        raise ValueError('Recipe bundle exceeds 32 MiB; keep generated model outputs outside recipe source')
    rid=digest(raw)
    manifest=dict(id=rid, request=request, bundle_path=f'bundles/{rid}.json',
                  bundle_sha256=digest(raw), validation_status=validation_status,
                  parent_id=parent_id, created_ns=now())
    return manifest, bundle

def apply(catalog, op):
    """Pure, idempotent operations; replay after a compare-and-swap conflict."""
    c=copy.deepcopy(validate(catalog));action=op['action'];data=op['data'];rid=data.get('recipe_id')
    if action=='recipe':
        rid=data['id'];old=c['recipes'].get(rid)
        if old:
            # Source identity is immutable, including request; validation is per delivery.
            if old['bundle_sha256'] != data['bundle_sha256'] or old['request'] != data['request']:
                raise ValueError('Immutable recipe identity conflict')
            return c
        parent=data.get('parent_id')
        if parent and (parent not in c['recipes'] or c['recipes'][parent]['request'] != data['request']):
            raise ValueError('Parent must be a known version of the same recipe kind/budget')
        c['recipes'][rid]=data
    elif action=='delivery':
        if rid not in c['recipes'] or len(data['model_sha256'])!=64:
            raise ValueError('Delivery needs a known recipe and exact exported model hash')
        old=c['deliveries'].get(data['id'])
        if old and old!=data:raise ValueError('Delivery identity conflict')
        c['deliveries'][data['id']]=data
    elif action=='rating':
        if type(data['shape_score']) is not int or not 1<=data['shape_score']<=5:
            raise ValueError('Shape score must be the explicit integer 1-5')
        delivery=c['deliveries'].get(data['delivery_id'])
        if not delivery or delivery['model_sha256']!=data['model_sha256']:
            raise ValueError('Rating must identify the delivered model, not just a recipe name')
        old=c['ratings'].get(data['id'])
        if old:
            original={k:v for k,v in old.items() if k!='sequence'}
            if original!=data:raise ValueError('Rating event identity conflict')
            return c
        data=copy.deepcopy(data)
        data['sequence']=1+max((v.get('sequence',0) for v in c['ratings'].values()),default=0)
        c['ratings'][data['id']]=data
    else:raise ValueError('Unknown operation')
    return c

def stats(c):
    # A corrected rating replaces the previous score for that delivery, not another vote.
    latest={}
    for e in c['ratings'].values():
        d=e['delivery_id'];old=latest.get(d)
        if old is None or (e.get('sequence',0),e['created_ns'],e['id'])>(old.get('sequence',0),old['created_ns'],old['id']):latest[d]=e
    result={}
    for did,e in latest.items():
        d=c['deliveries'][did]
        if d['validation_status'] not in ACCEPTED:continue
        result.setdefault(d['recipe_id'],[]).append(e['shape_score'])
    out={}
    for rid,scores in result.items():
        n=len(scores);five=scores.count(5);p=five/n;z=1.96
        lower=(p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)
        out[rid]=dict(count=n,fives=five,mean=sum(scores)/n,confidence=lower)
    return out

def pool(c, request):
    s=stats(c);items=[]
    for rid,m in c['recipes'].items():
        if m['request']==request and rid in s and s[rid]['fives']:
            items.append(dict(recipe=m, statistics=s[rid]))
    items.sort(key=lambda x:(-x['statistics']['confidence'],-x['statistics']['mean'],
                             -x['statistics']['fives'],x['recipe']['id']))
    return items[:10]

def choose(c, request, previous=None, rng=None):
    items=pool(c,request)
    if len(items)>1:items=[x for x in items if x['recipe']['id']!=previous]
    if not items:return None
    weights=[.1+x['statistics']['confidence']+x['statistics']['mean']/5 for x in items]
    return (rng or random.SystemRandom()).choices(items,weights=weights,k=1)[0]

def verify_delivery(request, model_path, gate_path):
    gate=json.loads(Path(gate_path).read_text())
    status=gate.get('acceptance_status')
    if status not in ACCEPTED|{'needs_repair'}:raise ValueError('Actual final acceptance gate required')
    if status not in ACCEPTED:return status
    root=Path(gate_path).resolve().parent
    if Path(model_path).resolve()!=root/'output/model.glb':
        raise ValueError('Accepted delivery must be the actual checked output/model.glb')
    from check_acceptance import evaluate
    from glb_io import verify_export
    from lab_model import project_audit
    actual=evaluate(root,request['quads'],gate.get('minimum_view_iou',.90),
                    organic=request['family'] in ('human','quadruped'),
                    static=gate.get('motion_required') is False,human=request['family']=='human')
    if actual['failed_gates'] or actual['acceptance_status']!=status:
        raise ValueError('Fresh acceptance checks do not agree with the saved passing gate')
    project=json.loads((root/'output/model.mflab.json').read_text())
    if project_audit(project)['quad_faces_total']!=request['quads'] or any(len(f)!=4 for o in project['objects'] for f in o['faces']):
        raise ValueError('Actual project exceeds requested whole-model quad budget')
    verify_export(project,model_path)
    return status

class GitHub:
    def __init__(self, config, token=None):
        self.repo=config['repository'];self.branch=config['branch'];self.prefix=config['directory']
        self.token=token or os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        if not self.token:
            try:self.token=subprocess.run(['gh','auth','token'],capture_output=True,text=True,check=True).stdout.strip()
            except (OSError,subprocess.CalledProcessError):pass
    def request(self, method, path, data=None, raw=False):
        headers={'Accept':'application/vnd.github.raw+json' if raw else 'application/vnd.github+json',
                 'Content-Type':'application/json','User-Agent':'ModelFactory-Lab-shared-recipes','X-GitHub-Api-Version':'2022-11-28'}
        if self.token:headers['Authorization']='Bearer '+self.token
        req=urllib.request.Request('https://api.github.com/repos/'+self.repo+path,
              data=None if data is None else encoded(data),headers=headers,method=method)
        with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read())
    def path(self,name):
        if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or '\\' in name:
            raise ValueError('Unsafe shared store path')
        return '/contents/'+urllib.parse.quote(self.prefix+'/'+name,safe='/')
    def read(self):
        d=self.request('GET',self.path('catalog.json')+'?ref='+urllib.parse.quote(self.branch,safe=''))
        value=json.loads(base64.b64decode(d['content'])) if d.get('content') else self.request('GET',self.path('catalog.json')+'?ref='+urllib.parse.quote(self.branch,safe=''),raw=True)
        return validate(value),d['sha']
    def write(self,c,sha):
        if not self.token:raise PermissionError('GitHub write access unavailable; operation remains queued')
        self.request('PUT',self.path('catalog.json'),dict(message='Update ModelFactory Lab shared recipe catalog',
                     branch=self.branch,sha=sha,content=base64.b64encode(encoded(c)).decode()))
    def put_bundle(self,m,bundle):
        name=m['bundle_path']
        try:
            old=self.bundle(m)
        except urllib.error.HTTPError as e:
            if e.code!=404:raise
        else:
            if encoded(old)!=encoded(bundle):raise ValueError('Immutable remote bundle changed')
            return
        if not self.token:raise PermissionError('GitHub write access unavailable')
        self.request('PUT',self.path(name),dict(message='Add immutable ModelFactory Lab recipe '+m['id'][:12],
                     branch=self.branch,content=base64.b64encode(encoded(bundle)).decode()))
    def bundle(self,m):
        value=self.request('GET',self.path(m['bundle_path'])+'?ref='+urllib.parse.quote(self.branch,safe=''),raw=True)
        if digest(encoded(value))!=m['bundle_sha256'] or value.get('request')!=m['request']:
            raise ValueError('Bundle hash or request mismatch')
        return value

class Store:
    def __init__(self, client, root):
        self.client=client;self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
    def pending(self):
        p=self.root/'pending';p.mkdir(exist_ok=True);return p
    def queue(self,op,bundle=None):
        uid=digest(encoded(op));p=self.pending()/(uid+'.json')
        p.write_bytes(encoded(dict(operation=op,bundle=bundle)));return uid
    def mutate(self,op,bundle=None):
        for attempt in range(5):
            c,sha=self.client.read()
            updated=apply(c,op)
            if bundle is not None:self.client.put_bundle(op['data'],bundle)
            if updated==c:
                (self.root/'catalog.json').write_bytes(encoded(c));return c
            try:
                self.client.write(updated,sha)
                (self.root/'catalog.json').write_bytes(encoded(updated))
                return updated
            except urllib.error.HTTPError as e:
                if e.code not in (409,422):raise
        raise RuntimeError('Concurrent updates continue; queued operation preserved, retry later')
    def flush(self):
        sent=[]
        # Dependency order preserves recipe -> delivery -> rating even across offline sessions.
        records=[(p,json.loads(p.read_text())) for p in self.pending().glob('*.json')]
        order={'recipe':0,'delivery':1,'rating':2}
        records.sort(key=lambda x:(order[x[1]['operation']['action']],x[1]['operation']['data'].get('created_ns',0)))
        for p,item in records:
            self.mutate(item['operation'],item['bundle']);p.unlink();sent.append(p.stem)
        return sent
    def sync(self,offline=False):
        cache=self.root/'catalog.json'
        if offline:
            if not cache.exists():raise ValueError('No offline catalog; remote absence cannot be inferred')
            return validate(json.loads(cache.read_text()))
        c,sha=self.client.read();cache.write_bytes(encoded(c));(self.root/'catalog-revision.txt').write_text(sha)
        return c
    def known(self):
        # For queuing mutations only: preserve pending dependencies without inventing remote absence.
        try:c=self.sync()
        except (OSError,urllib.error.URLError):
            cache=self.root/'catalog.json'
            c=validate(json.loads(cache.read_text())) if cache.exists() else empty_catalog()
        ops=[json.loads(p.read_text())['operation'] for p in self.pending().glob('*.json')]
        for action in ('recipe','delivery','rating'):
            for op in sorted(ops,key=lambda x:x['data'].get('created_ns',0)):
                if op['action']==action:c=apply(c,op)
        return c
    def submit(self,op,bundle=None):
        uid=self.queue(op,bundle)
        try:self.flush();return dict(status='synced',operation_id=uid)
        except (OSError,ValueError,urllib.error.URLError,PermissionError,RuntimeError) as e:
            return dict(status='pending_sync',operation_id=uid,reason=str(e))
    def extract(self,m,dest):
        bundle=self.client.bundle(m);dest=require_lab_path(dest);dest.mkdir(parents=True,exist_ok=False)
        entries=[]
        for name,v in bundle['files'].items():
            p=PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:raise ValueError('Unsafe recipe path')
            raw=base64.b64decode(v['base64'],validate=True)
            if digest(raw)!=v['sha256']:raise ValueError('Source hash mismatch: '+name)
            entries.append((dest.joinpath(*p.parts),raw))
        for p,raw in entries:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        return dict(directory=str(dest),recipe_id=m['id'],executed=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',required=True,type=Path);p.add_argument('--config',type=Path,default=CONFIG)
    s=p.add_subparsers(dest='command',required=True)
    for cmd in ('sync','flush'):s.add_parser(cmd)
    f=s.add_parser('find')
    for n in ('family','kind'):f.add_argument('--'+n,required=True)
    f.add_argument('--quads',type=int,required=True);f.add_argument('--level',type=int,default=2);f.add_argument('--offline',action='store_true');f.add_argument('--out',type=Path)
    a=s.add_parser('add');a.add_argument('--source',type=Path,required=True);a.add_argument('--request',type=Path,required=True);a.add_argument('--validation-status',choices=sorted(ACCEPTED|{'needs_repair'}),required=True);a.add_argument('--parent-id')
    d=s.add_parser('delivered');d.add_argument('--recipe-id',required=True);d.add_argument('--run-id',required=True);d.add_argument('--model',type=Path,required=True);d.add_argument('--gate',type=Path,required=True)
    r=s.add_parser('rate');r.add_argument('--delivery-id',required=True);r.add_argument('--score',type=int,required=True);r.add_argument('--model-sha256',required=True)
    args=p.parse_args();root=require_lab_path(args.cache);store=Store(GitHub(json.loads(args.config.read_text())),root)
    if args.command=='sync':result=store.sync()
    elif args.command=='flush':result=store.flush()
    elif args.command=='find':
        c=store.sync(args.offline);req=key(args.family,args.kind,args.quads,args.level);history=root/'last-choice.json';last=json.loads(history.read_text()) if history.exists() else {};k=digest(encoded(req));picked=choose(c,req,last.get(k))
        result=dict(status='found' if picked else 'no_five_star_recipe',request=req,active_count=len(pool(c,req)),selection=picked,offline=args.offline)
        if picked:
            last[k]=picked['recipe']['id'];history.write_bytes(encoded(last))
            if args.out:
                if args.offline:raise ValueError('Materialization needs online bundle verification')
                result['source']=store.extract(picked['recipe'],args.out)
    elif args.command=='add':
        request=json.loads(args.request.read_text());req=key(request['family'],request['kind'],request['quads'],request['level']);m,b=pack(args.source,req,args.validation_status,args.parent_id)
        result=store.submit(dict(action='recipe',data=m),b);result['recipe_id']=m['id']
    elif args.command=='delivered':
        c=store.known()
        request=c['recipes'][args.recipe_id]['request']
        status=verify_delivery(request,args.model,args.gate)
        d=dict(id=uuid.uuid4().hex,recipe_id=args.recipe_id,run_id=args.run_id,model_sha256=digest(args.model.read_bytes()),validation_status=status,gate_sha256=digest(args.gate.read_bytes()),created_ns=now())
        result=store.submit(dict(action='delivery',data=d));result.update(delivery_id=d['id'],model_sha256=d['model_sha256'],rating_prompt='Hinda selle mudeli kuju 1–5. Mis vajab parandamist?')
        (root/('feedback-'+d['id']+'.json')).write_bytes(encoded(result))
    else:
        c=store.known()
        e=dict(id=uuid.uuid4().hex,delivery_id=args.delivery_id,model_sha256=args.model_sha256,shape_score=args.score,created_ns=now());op=dict(action='rating',data=e);apply(c,op);result=store.submit(op)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
