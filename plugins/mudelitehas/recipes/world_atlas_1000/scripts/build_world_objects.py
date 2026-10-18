#!/usr/bin/env python3
"""Generate editable all-quad OBJ sources and preview-ready GLB world props.
Procedural authoring, *not* a v0.1.2 multi-view-certified reconstruction.
Coordinate system: X/Z horizontal, Y up; game atlas cell nominally 50 units.
No input scans or fake witness records are generated.
"""
import math, random, json, argparse
from pathlib import Path
from collections import defaultdict
import numpy as np
import trimesh

PAL={
 'wood': (119,82,50,255),'darkwood':(75,52,38,255),'roof':(159,126,77,255),
 'straw':(187,158,93,255),'stone':(140,142,129,255),'lightstone':(182,180,154,255),
 'moss':(82,111,75,255),'grass':(103,128,73,255),'earth':(130,103,72,255),
 'rock':(101,105,101,255),'rocklight':(155,155,143,255),'rockdark':(77,79,79,255),
 'leaves':(63,111,69,255),'needles':(49,89,61,255),'leaves2':(83,131,74,255),
 'iron':(73,83,86,255),'water':(67,130,145,255),'brick':(150,112,93,255),
 'gold':(174,147,75,255)
}

class Model:
 def __init__(self,name):
  self.name=name;self.parts=[];self.vertices=[];self.quads=[];self.groups=[];self.mat=[]
 def mesh(self,verts,faces,material,name='mesh'):
  base=len(self.vertices);self.vertices.extend(tuple(float(x) for x in v) for v in verts)
  for face in faces:
   assert len(face)==4
   self.quads.append(tuple(base+i for i in face));self.mat.append(material);self.groups.append(name)
 def box(self,x,y,z,sx,sy,sz,mat='stone',name='box',yaw=0):
  verts=[(-.5,-.5,-.5),(.5,-.5,-.5),(.5,.5,-.5),(-.5,.5,-.5),(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)]
  c,s=math.cos(yaw),math.sin(yaw)
  verts=[(x+sx*a*c+sz*d*s,y+sy*b,z-sx*a*s+sz*d*c) for a,b,d in verts]
  faces=[(0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(3,7,6,2),(0,1,5,4)]
  self.mesh(verts,faces,mat,name)
 def beam(self,a,b,width,height,mat,name='beam'):
  x=(a[0]+b[0])/2;z=(a[1]+b[1])/2
  yaw=math.atan2(a[1]-b[1],b[0]-a[0]);length=math.dist(a,b)
  self.box(x,height/2,z,length,height,width,mat,name,yaw)
 def ringed(self,x,y,z,rings,n=8,mat='stone',name='ringed',seed=0,cap=True):
  # Perimeter vertices, horizontal levels. n even for quad-only cap strips.
  rng=random.Random(seed);jitter=[(.85+.3*rng.random()) for _ in range(n)]
  vertices=[]
  for h,rx,rz in rings:
   for j in range(n):
    ang=2*math.pi*j/n
    vertices.append((x+rx*math.cos(ang)*jitter[j],y+h,z+rz*math.sin(ang)*jitter[j]))
  faces=[]
  for k in range(len(rings)-1):
   for j in range(n): faces.append((k*n+j,(k+1)*n+j,(k+1)*n+(j+1)%n,k*n+(j+1)%n))
  if cap:
   def close(ring,reverse):
    ids=[ring*n+j for j in range(n)]
    while len(ids)>4:
     quad=[ids[-1],ids[0],ids[1],ids[2]]
     faces.append(tuple(quad) if reverse else tuple(reversed(quad)));ids=[ids[2]]+ids[3:]
    faces.append(tuple(ids) if reverse else tuple(reversed(ids)))
   close(0,True);close(len(rings)-1,False)
  self.mesh(vertices,faces,mat,name)
 def roof(self,x,y,z,sx,sy,sz,mat='straw',name='roof'):
  # Two thick quadrilateral roof facets, no triangular faces.
  ridge=y+sy
  self.mesh([
   (x-sx/2,y,z-sz/2),(x-sx/2,ridge,z),(x+sx/2,ridge,z),(x+sx/2,y,z-sz/2),
   (x-sx/2,y-.13,z-sz/2),(x-sx/2,ridge-.13,z),(x+sx/2,ridge-.13,z),(x+sx/2,y-.13,z-sz/2)
  ],[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],mat,name+'_left')
  self.mesh([
   (x-sx/2,ridge,z),(x-sx/2,y,z+sz/2),(x+sx/2,y,z+sz/2),(x+sx/2,ridge,z),
   (x-sx/2,ridge-.13,z),(x-sx/2,y-.13,z+sz/2),(x+sx/2,y-.13,z+sz/2),(x+sx/2,ridge-.13,z)
  ],[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],mat,name+'_right')
 def write(self,folder):
  assert 0 < len(self.quads) <= 1000,(self.name,len(self.quads))
  folder.mkdir(parents=True,exist_ok=True)
  obj=folder/(self.name+'.obj');mtl=folder/(self.name+'.mtl');glb=folder/(self.name+'.glb')
  with mtl.open('w') as f:
   for mat,rgba in PAL.items():
    r,g,b,a=rgba;f.write(f'newmtl {mat}\nKd {r/255:.6f} {g/255:.6f} {b/255:.6f}\nKa 0.0 0.0 0.0\nd 1\nillum 1\n\n')
  with obj.open('w') as f:
   f.write('# QUAD SOURCE. GLB indices triangulated by glTF specification.\n')
   f.write(f'mtllib {self.name}.mtl\no {self.name}\n')
   for v in self.vertices:f.write('v '+ ' '.join(f'{a:.6f}' for a in v)+'\n')
   prev=(None,None)
   for group,mat,face in zip(self.groups,self.mat,self.quads):
    if prev!=(group,mat): f.write(f'g {group}\nusemtl {mat}\n');prev=(group,mat)
    f.write('f '+' '.join(str(k+1) for k in face)+'\n')
  scene=trimesh.Scene()
  for mat in sorted(set(self.mat)):
   idxs=[i for i,m in enumerate(self.mat) if m==mat];mapv={};vert=[];faces=[]
   for i in idxs:
    face=self.quads[i]
    v=[]
    for k in face:
     if k not in mapv:mapv[k]=len(vert);vert.append(self.vertices[k])
     v.append(mapv[k])
    faces.extend([(v[0],v[1],v[2]),(v[0],v[2],v[3])])
   mesh=trimesh.Trimesh(vertices=np.asarray(vert),faces=np.asarray(faces,dtype=int),process=False)
   mesh.visual.vertex_colors=np.tile(PAL[mat],(len(mesh.vertices),1))
   scene.add_geometry(mesh,geom_name=mat,node_name=f'{self.name}_{mat}')
  glb.write_bytes(scene.export(file_type='glb'))
  re=trimesh.load(glb,force='scene');tri=sum(len(m.faces) for m in re.geometry.values())
  assert tri == len(self.quads)*2,(tri,len(self.quads))
  bounds=scene.bounds.tolist()
  report={'id':self.name,'quad_source':str(obj.name),'quad_count':len(self.quads),'triangles_glb':tri,'under_1000_quads':True,'bounds_xyz':bounds,'materials':sorted(set(self.mat)),'source_views':'none / procedural original','multiview_certified':False,'glb_bytes':glb.stat().st_size}
  (folder/(self.name+'_validation.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
  return report


def village():
 m=Model('world_village_1000');r=random.Random(17)
 m.box(0,.05,0,15,.10,13,'earth','village_ground')
 buildings=[(-4,-3,3.6,2.7),(.3,-3.5,4.2,3), (4.2,-1.5,3.2,2.4),(-3.2,2.4,2.8,2.2),(1.3,2.4,3.7,3.1)]
 for i,(x,z,w,d) in enumerate(buildings):
  hh=2.5+(i%3)*.3;m.box(x,.15+hh/2,z,w,hh,d,'lightstone' if i%3==0 else 'wood',f'house{i}')
  m.roof(x,hh+.24,z,w+.5,1.4,d+.7,'straw' if i%2 else 'roof',f'roof{i}')
  m.box(x,1.4,z+d/2+.03,.7,1.45,.09,'darkwood',f'door{i}')
  for ww in [-w*.28,w*.28]:m.box(x+ww,2,z-d/2-.06,.42,.34,.09,'darkwood',f'window{i}')
 # village well
 m.ringed(-.7,.1,.15,[(0,.85,.85),(.8,.9,.9)],8,'stone','well')
 for xx in [-.6,.6]:m.box(-.7+xx,1.55,.15,.12,1.5,.12,'wood','well_pillar')
 m.roof(-.7,2.4,.15,2.0,.65,1.7,'roof','well_roof')
 # short wooden palisade, pathways
 for n in range(9):
  x=-6.5+n*1.6
  if -2.3<x<.2:continue
  m.box(x,.75,6.5,.13,1.5,.17,'wood','fence_post')
  if n: m.box(x-.8,.7,6.5,1.55,.12,.12,'darkwood','fence_rail')
 for i in range(9):m.box(r.uniform(-6,6),.12,r.uniform(-5,5),.5,.08,.3,'rocklight','path_stone',yaw=r.random()*4)
 return m

def ruins():
 m=Model('ancient_ruin_1000');r=random.Random(23)
 m.box(0,.08,0,12,.15,12,'earth','ruin_ground')
 m.box(0,.24,0,7,.3,6,'stone','temple_base')
 for x,z,h in [(-3,-2.4,4.9),(-3,2.4,2.9),(3,-2.4,5.8),(3,2.4,1.7),(-.5,-2.4,1.6)]:
  m.ringed(x,.4,z,[(0,.5,.5),(h*.24,.56,.56),(h*.72,.43,.43),(h,.5,.5)],8,'lightstone','broken_column',seed=int((x+5)*11+(z+4)*7))
  m.box(x,.35+h+.12,z,1.3,.24,1.3,'stone','capital')
 m.box(0,6.15,-2.4,7,.7,.85,'lightstone','lintel')
 m.box(-4,1.1,0,.8,2.0,7.8,'stone','ruin_wall')
 m.box(4,.7,0,.7,1.3,7,'stone','ruin_wall')
 m.box(0,.72,.9,2.3,1.4,1.6,'rock','altar')
 m.box(0,1.5,.9,1.0,.18,.8,'gold','relic')
 for i in range(30):
  x=r.uniform(-5.5,5.5);z=r.uniform(-5.5,5.5);w=r.uniform(.35,.9)
  m.box(x,.16+w*.2,z,w,.32+w*.2,w*.75,'rocklight' if i%3 else 'moss',f'rubble{i}',yaw=r.uniform(0,math.pi))
 return m

def rocks():
 m=Model('rock_outcrop_1000');r=random.Random(11)
 peaks=[(-3,-1,4.0,3.8),(1,1,6.7,3.4),(3.8,-2.3,3.3,2.7),(-.2,-3.8,2.8,2.6),(-4.8,2,2.3,2.0)]
 for i,(x,z,h,radius) in enumerate(peaks):
  m.ringed(x,0,z,[(0,radius*1.20,radius*.95),(.2*h,radius*1.1,radius*.87),(.6*h,radius*.87,radius*.68),(h,radius*.25,radius*.25)],8,['rock','rocklight','rockdark'][i%3],f'crag_{i}',seed=29+i)
 for i in range(15):
  x=r.uniform(-6.5,6.5);z=r.uniform(-5,5);w=r.uniform(.3,1)
  m.ringed(x,.03,z,[(0,w,w*.8),(.6*w,w*.6,w*.7)],8,'rocklight' if i%4==0 else 'rock',f'debris{i}',seed=i+18)
 return m

def bridge():
 m=Model('river_bridge_1000');
 # Bridge deck crosses Z-direction, river along X-direction.
 for i in range(17):
  z=-7.2+i*.9
  deck_y=1.7+.58*(1-(z/7.8)**2)
  m.box(0,deck_y,z,6,.26,.85,'roof' if i%3 else 'wood',f'deck_plank_{i}')
 for side in [-2.65,2.65]:
  for z in [-6,-3,0,3,6]:
   m.box(side,2.5+.5*(1-(z/7.8)**2),z,.18,1.7,.22,'wood','support_post')
   m.box(side,3.7+.5*(1-(z/7.8)**2),z,.29,.25,.35,'darkwood','post_cap')
  m.box(side,3.45,0,.21,.17,14.5,'wood','handrail')
  m.box(side,2.45,0,.19,.15,14.5,'darkwood','side_reinforcement')
 for z in [-6.5,0,6.5]:
  for side in [-2.5,2.5]:
   m.box(side,.85,z,.55,1.6,.6,'stone','bridge_stone_pier')
 for z in [-7.5,7.5]:m.box(0,1.0,z,7,.2,1.25,'earth','approach')
 return m

def forest():
 m=Model('forest_cluster_1000');r=random.Random(12)
 points=[(-4.4,-2.4),(-1,-3.6),(2.9,-3.2),(4.6,.3),(1.4,2.4),(-3.4,2.9),(.1,-.6),(-5,1.1),(4,3.6)]
 for i,(x,z) in enumerate(points):
  h=5.4+(i%4)*1.4;rad=1.5+(i%3)*.18
  m.ringed(x,0,z,[(0,.38,.38),(h*.50,.3,.3),(h*.9,.22,.22)],8,'darkwood',f'trunk_{i}',seed=i)
  if i%3:
   m.ringed(x,2.8,z,[(0,rad*.9,rad*.9),(2.2,rad,rad),(4.3,rad*.7,rad*.7),(5.7,rad*.17,rad*.17)],8,'needles' if i%2 else 'leaves',f'conifer_{i}',seed=3+i)
  else:
   m.ringed(x,3.8,z,[(0,rad*.6,rad*.6),(1.8,rad*1.45,rad*1.45),(3.9,rad*1.25,rad*1.25),(5.1,rad*.3,rad*.3)],8,'leaves2',f'broadleaf_{i}',seed=3+i)
 for i in range(7):
  x=r.uniform(-5,5);z=r.uniform(-5,5)
  m.ringed(x,0,z,[(0,.55,.55),(.8,.9,.9),(1.35,.22,.22)],8,'moss',f'bush_{i}',seed=i+66)
 return m

SPECS={
 'world_village_1000':(village,'Küla','village', 'avastatav','plains, forest_edge, river_near'),
 'ancient_ruin_1000':(ruins,'Iidne vare','ancient','avastatav ja boonus','plains, hills'),
 'rock_outcrop_1000':(rocks,'Kaljupaljand','rock','maastik','hills, mountain'),
 'river_bridge_1000':(bridge,'Jõesild','bridge','jõe ületamine','river, ford'),
 'forest_cluster_1000':(forest,'Metsagrupp','forest','maastik','forest, taiga')
}

def build_all(out):
 reports=[]
 for key,(func,et,kind,role,biome) in SPECS.items():
  print('Building',key,flush=True)
  model=func();reports.append(model.write(out/'models'/key))
  rec=out/'recipes'/key;rec.mkdir(parents=True,exist_ok=True)
  (rec/'recipe.json').write_text(json.dumps({'recipe_id':key,'title_et':et,'version':'1.0.0','kind':kind,'role':role,'max_quads':1000,'target_quads':[350,950],'coordinate_system':'Y up, pivot ground center','materials':'vertex colors + MTL','output':f'models/{key}/{key}.glb','quad_source':f'models/{key}/{key}.obj','builder': 'python scripts/build_world_objects.py','source_method':'procedural authoring','multiview_certificate':False,'three_direction_reference_required_for_certification':True,'pre_mesh_witness_status':'not supplied, must not be fabricated','geometry_constraints':['quads-only OBJ','GLB triangles <= 2000','single pivot','no degenerate quads']},ensure_ascii=False,indent=2),encoding='utf-8')
  (rec/'placement_rules.json').write_text(json.dumps({'kind':kind,'allowed_biomes':biome.split(', '),'max_slope_degrees':25 if kind!='rock' else 75,'minimum_spacing_tiles':{'village':8,'ancient':12,'rock':1,'bridge':2,'forest':1}[kind],'rotation': 'river-normal aligned to Z' if kind=='bridge' else 'random Y-angle','instancing':kind in ('rock','forest'),'game_hook':{'village':'discovery village reward once','ancient':'discovery relic reward once','rock':'mountain decoration','bridge':'ford/bridge crossing','forest':'biome forest decoration'}[kind],'visible_only_if_discovered':kind in ('village','ancient'),'notes_et':'Mängus kasutamiseks lisa instancing või GLBLoader; olemasolevat mängureeglistikku automaatselt ei muudeta.'},ensure_ascii=False,indent=2),encoding='utf-8')
  (rec/'validation.md').write_text(f'''# {et} – valideerimine\n\n- [x] Päris geomeetria olemas OBJ ja GLB failis.\n- [x] OBJ koosneb ainult nelinurksetest tahkudest.\n- [x] {len(model.quads)} quadi, piir <=1000.\n- [x] GLB avatud uuesti trimesh abil; {len(model.quads)*2} trianguleeritud kolmnurka.\n- [x] Pivot maapinna keskosas, Y-up.\n- [ ] **Mudelitehas 0.1.2 sertifikaat**: 3 sõltumatut referentssuunda ja punktide witness enne meshi (puudub).\n- [ ] Blender .blend eksport / Blenderi enda reimport (siinses keskkonnas Blender puudub).\n- [ ] Mängus päriselt üle vaadatud (GLB paigutuse visuaaltest mängus).\n\nSee on **protseduuriline quad-algmudel**, mitte punktipilvest rekonstrueeritud sertifitseeritud Mudelitehas 0.1.2 mudel.\n''',encoding='utf-8')
  (rec/'README.md').write_text(f'''# {et} / {key}\n\nRetsept Kuningriikide maailmakaardi jaoks.\n\n- Ruudupiir: 1000; loodud: **{len(model.quads)}**.\n- Pärismudel: `models/{key}/{key}.glb` (kolmnurkne glTF representatsioon).\n- Redigeeritav nelinurkne lähteobjekt: `.obj`, koos materjalifailiga `.mtl`.\n- Retsept ja paigutusreeglid: siinsamas kaustas.\n- Mudelitehas 0.1.2 kolme sõltumatu suuna kinnitamine ootab läbivaadatud referentsfotosid.\n\nUuesti genereerimiseks: `python scripts/build_world_objects.py --output .`.\n''',encoding='utf-8')
  # strict manifest for future multiview certification, not synthetic
  (rec/'references_manifest.template.json').write_text(json.dumps({'model_id':key,'status':'references_missing','independent_directions':['front','side','top'],'views':[],'witness_per_point':[],'pre_mesh_gate':'blocked until reviewed'},ensure_ascii=False,indent=2),encoding='utf-8')
 (out/'validation_report.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({x['id']:x['quad_count'] for x in reports},ensure_ascii=False))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--output',default=str(Path(__file__).resolve().parents[1]));args=ap.parse_args();build_all(Path(args.output))
