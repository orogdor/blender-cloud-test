#!/usr/bin/env python3
"""Kuningriigid Stone Age watchtower V2: local Qwen art direction, native ModelFactory GLB mesh."""
from pathlib import Path
import json, math, random, subprocess, os, sys
B=Path(__file__).resolve().parent
OUT=B/"work"/"test-models"/"Kuningriigid_Kiviaja_Vahitorn_V2"
design=json.loads((OUT/"design-qwen-v2.json").read_text(encoding="utf-8"))
rng=random.Random(271027)
def cl(x,a,b):return max(a,min(b,float(x)))
R=cl(design["tower_width_m"],3.8,4.6)/2
P=cl(design["platform_z_m"],3.2,3.9)
E=cl(design["roof_eave_z_m"],5,5.9)
A=cl(design["roof_apex_z_m"],max(E+1.3,6.8),7.7)
N=int(cl(design["palisade_log_count_per_octagon_side"],5,9))
LAY=int(cl(design["roof_reed_layers"],7,12))
def rgba(key):return [cl(x,.04,.94) for x in design[key]]+[1]
def shade(c,k):return [cl(x*k,.025,.97) for x in c[:3]]+[1]
wood=rgba("timber_main_rgb");dark=rgba("timber_shadow_rgb")
thatch=rgba("thatch_rgb");stone=rgba("stone_rgb");rope=rgba("rope_rgb")
M={
"wood":{"color":wood,"roughness":.94},
"wood_light":{"color":shade(wood,1.19),"roughness":.94},
"bark":{"color":dark,"roughness":.98},
"bark_mid":{"color":shade(dark,1.39),"roughness":.97},
"endgrain":{"color":shade(wood,1.38),"roughness":.91},
"thatch":{"color":thatch,"roughness":.99,"double_sided":True},
"thatch_light":{"color":shade(thatch,1.13),"roughness":1,"double_sided":True},
"thatch_dark":{"color":shade(thatch,.72),"roughness":1,"double_sided":True},
"rope":{"color":rope,"roughness":1},
"stone":{"color":stone,"roughness":.98},
"stone_dark":{"color":shade(stone,.82),"roughness":.98},
"moss":{"color":[.21,.27,.13,1],"roughness":1,"double_sided":True},
"recess":{"color":[.050,.035,.018,1],"roughness":1,"double_sided":True}
}
meshes={k:{"vertices":[],"faces":[]} for k in M}
def add(mat,vs,fs):
    if not fs:return
    g=meshes[mat];offset=len(g["vertices"])
    g["vertices"].extend([[round(float(x),6) for x in v] for v in vs])
    g["faces"].extend([[offset+i for i in f] for f in fs])
def vsum(a,b):return [a[i]+b[i] for i in range(3)]
def diff(a,b):return [a[i]-b[i] for i in range(3)]
def mul(a,t):return [v*t for v in a]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(a):
    s=math.sqrt(sum(x*x for x in a))
    if s<1e-10:raise ValueError("zero vector")
    return [x/s for x in a]
def lerp(a,b,t):return [a[i]*(1-t)+b[i]*t for i in range(3)]
# octagonal log 8 sides, diameter shape changes along length, natural organic silhouette.
def rounded_log(a,b,r,material="wood",rings=3,pointed=False):
    axis=norm(diff(b,a))
    u=cross(axis,[0,0,1])
    if sum(x*x for x in u)<.015:u=cross(axis,[0,1,0])
    u=norm(u);v=norm(cross(axis,u))
    phase=rng.uniform(-math.pi,math.pi)
    verts=[]
    for j in range(rings+1):
        t=j/rings
        center=lerp(a,b,t)
        center=vsum(center,mul(u,.028*math.sin(phase+1.4)*math.sin(t*math.pi)))
        scale=(1-.15*t)*(.38 if pointed and j==rings else 1)
        for k in range(6):
            an=2*math.pi*k/6+.025*math.sin(t*2+phase)
            radius=r*scale*(1+.08*math.sin(k*1.74+j*.88+phase))
            verts.append(vsum(center,vsum(mul(u,math.cos(an)*radius),mul(v,math.sin(an)*radius))))
    faces=[]
    for j in range(rings):
        for k in range(6):
            nk=(k+1)%6
            faces.append([j*6+k,j*6+nk,(j+1)*6+nk,(j+1)*6+k])
    # 6-sided wood cap is two real quads, not fake duplicated polygons
    quadcaps=((0,1,2,5),(2,3,4,5))
    for quad in quadcaps:
        faces.append(list(reversed(quad)))
        faces.append([rings*6+i for i in quad])
    add(material,verts,faces)
def rock(cx,cy,k=1):
    rot=rng.uniform(0,math.tau)
    vs=[]
    for j,(z,rad) in enumerate(((.03,.48*k),(.18,.60*k),(.39,.43*k))):
        for i in range(8):
            an=i*math.tau/8+rot
            rr=rad*(1+.13*math.sin(i*2.7+rot))
            vs.append([cx+rr*math.cos(an),cy+rr*math.sin(an),z+.027*math.cos(i*3.1+rot)])
    faces=[[j*8+i,j*8+(i+1)%8,(j+1)*8+(i+1)%8,(j+1)*8+i] for j in range(2) for i in range(8)]
    for q in ((0,1,2,7),(2,3,4,7),(4,5,6,7)):
        faces.append(list(reversed(q)))
        faces.append([16+i for i in q])
    add("stone" if rng.random()<.75 else "stone_dark",vs,faces)
def winding(point,axis,radius=.18,turns=2):
    axis=norm(axis)
    u=cross(axis,[0,0,1])
    if sum(x*x for x in u)<.04:u=cross(axis,[0,1,0])
    u=norm(u);v=norm(cross(axis,u))
    # Closed ribbon, 2 coils, 6 segments each.
    for coil in range(turns):
        r=radius+coil*.015
        n=12
        vs=[]
        for j in range(2):
            for i in range(n):
                an=math.tau*i/n+.15*coil
                pos=vsum(point,vsum(mul(u,r*math.cos(an)),mul(v,r*math.sin(an))))
                vs.append(vsum(pos,mul(axis,(j-.5)*.026+(coil-.5)*.06)))
        faces=[[i,(i+1)%n,n+(i+1)%n,n+i] for i in range(n)]
        add("rope",vs,faces)
def octo(r,z,rot=math.pi/8):
    return [[r*math.cos(rot+k*math.pi/4),r*math.sin(rot+k*math.pi/4),z] for k in range(8)]
# timber legs staggered on irregular boulder footings
leg=1.43
for x in (-leg,leg):
    for y in (-leg,leg):
        rock(x,y,1)
        aa=[x+rng.uniform(-.025,.025),y+rng.uniform(-.025,.025),.3]
        bb=[x+rng.uniform(-.13,.13),y+rng.uniform(-.13,.13),P+.13]
        rounded_log(aa,bb,.24,"bark",rings=4)
        winding([x,y,P-.19],[0,0,1],.26,1)
        rounded_log([x,y,P-.10],[x,y,P+.34],.28,"wood",rings=2)
# four faces of variable solid-log X bracing
for sgn in (-1,1):
    x=sgn*leg
    rounded_log([x,-leg,.83],[x,leg,P-.26],.123,"wood_light")
    rounded_log([x,leg,.83],[x,-leg,P-.26],.109,"bark_mid")
    y=sgn*leg
    rounded_log([-leg,y,.83],[leg,y,P-.26],.119,"wood")
    rounded_log([leg,y,.83],[-leg,y,P-.26],.114,"bark_mid")
# uneven lower cross-bars and lashings
for height in (P-.21,):
    for a,b in zip(octo(leg,height),octo(leg,height)[1:]+octo(leg,height)[:1]):
        rounded_log(a,b,.105,"bark_mid",rings=2)
# elevated polygonal platform with notched logs
lowerRing=octo(R-.24,P+.04)
for i in range(8):
    rounded_log(lowerRing[i],lowerRing[(i+1)%8],.18,"bark",rings=2)
for i in range(9):
    x=(i-4)*.42
    extent=math.sqrt(max(.15,(R-.36)**2-x*x))
    rounded_log([x,-extent,P+.05],[x,extent,P+.05],.175,("wood" if i%3 else "wood_light"),rings=2)
# raised enclosure's wall: raw upright sharply tapered logs, 7 per each of 8 sides
base=P+.22
ring=octo(R-.18,base)
for side in range(8):
    a=ring[side]
    b=ring[(side+1)%8]
    for i in range(N):
        t=(i+.52+rng.uniform(-.085,.085))/N
        center=lerp(a,b,t)
        h=E+rng.uniform(-.16,.20)
        radius=.118+rng.uniform(-.009,.016)
        c=[center[0],center[1]]
        mat=("bark" if (side+i)%4==0 else "wood" if (side+i)%3 else "wood_light")
        # 2 short arrow-slits placed in the upper course, dark intentional hole across breaks
        if i==N//2 and side in (0,3,6):
            rounded_log([*c,base],[*c,P+1.06],radius,mat,rings=2)
            rounded_log([*c,P+1.43],[*c,h],radius,mat,rings=2,pointed=True)
        else:
            rounded_log([*c,base+rng.uniform(-.07,.02)],[*c,h],radius,mat,rings=2,pointed=True)
    # pegged horizontal ties, high and low: fastened with hemp wrappings
    rounded_log([a[0],a[1],P+.69],[b[0],b[1],P+.69],.09,"bark_mid",rings=2)
    rounded_log([a[0],a[1],E-.32],[b[0],b[1],E-.32],.077,"bark",rings=2)
# simple primitive climb up the side using split-log ladder
ladderSide=-R-.40
aa=[-.45,ladderSide-.77,.18]; bb=[-.45,ladderSide+.48,P+.25]
cc=[.45,ladderSide-.77,.18];dd=[.45,ladderSide+.48,P+.25]
rounded_log(aa,bb,.108,"bark",rings=4)
rounded_log(cc,dd,.10,"bark",rings=4)
rungs=int(cl(design["ladder_rungs"],10,14))
for j in range(rungs):
    t=(j+.95)/(rungs+1)
    pl=lerp(aa,bb,t);pr=lerp(cc,dd,t)
    rounded_log(pl,pr,.080,"wood_light" if j%3==0 else "wood",rings=2)
    if j%4==0:
        winding(pl,[1,0,0],.095,1)
        winding(pr,[1,0,0],.095,1)
# irregular woven conical roof, not a pyramid or modern shingled cap
outer=R+.42
rot=math.pi/8
roofV=[]
faces=[]
radial_count=20;ring_count=5
for ri in range(ring_count):
    t=ri/(ring_count-1)*.94
    rr=outer*(1-t)
    z=E+(A-E)*t**.93
    for k in range(radial_count):
        th=math.tau*k/radial_count+rot
        small=.034*math.sin(k*2.4+ri*1.1)
        roofV.append([(rr+small)*math.cos(th),(rr+small)*math.sin(th),z+(.027*math.sin(th*5+ri))])
for i in range(ring_count-1):
    for j in range(radial_count):
        faces.append([i*radial_count+j,i*radial_count+(j+1)%radial_count,(i+1)*radial_count+(j+1)%radial_count,(i+1)*radial_count+j])
# top joined naturally, no degenerate roof points, use triangle fan
topidx=len(roofV)
roofV.append([0,0,A+.02])
for j in range(radial_count):
    faces.append([(ring_count-1)*radial_count+j,(ring_count-1)*radial_count+(j+1)%radial_count,topidx])
add("thatch_dark",roofV,faces)
# each layered reed cluster is separate curvilinear strip; its lower edge bends and spills
# roof 9 concentric strata * 24 strips gives ~430 non-box quads
for lay in range(LAY):
    t0=.018+lay*.099
    t1=min(.982,t0+.17)
    for k in range(radial_count):
        center=math.tau*(k+.5)/radial_count+rot
        half=.5*math.tau/radial_count*.94
        segment=[]
        for j,t in enumerate((t0,t1)):
            r=outer*(1-t)
            z=E+(A-E)*t**.93
            for pos in (-1,0,1):
                th=center+pos*half
                wob=(.045 if j==0 else .018)*math.sin(k*2.31+lay*1.93+pos)
                pr=r*(1+.015*math.sin(k*.77+lay+pos))
                segment.append([pr*math.cos(th),pr*math.sin(th),z+.035+wob])
        ms=("thatch_light" if (k*3+lay)%7==0 else "thatch_dark" if (k+lay)%5==0 else "thatch")
        add(ms,segment,[[0,1,4,3],[1,2,5,4]])
# dark radial ribs under the eaves; bent fir poles, attached to center 
for k in range(8):
    a=math.tau*k/8+rot
    xx,yy=math.cos(a),math.sin(a)
    rounded_log([outer*xx,outer*yy,E-.04],[.12*xx,.12*yy,A-.18],.080,
                "bark",rings=4)
# Knots and lashings at roof brackets
for k in range(8):
    a=math.tau*k/8+rot
    winding([(R-.13)*math.cos(a),(R-.13)*math.sin(a),E-.16],
            [math.cos(a),math.sin(a),.3],.13,1)
# carved primitive fork at peak: two gently parted branch stubs, no medieval banner
rounded_log([0,0,A-.10],[0,0,A+.28],.075,"bark_mid",rings=2)
rounded_log([0,0,A+.23],[.23,.07,A+.48],.046,"wood_light",rings=2,pointed=True)
rounded_log([0,0,A+.23],[-.18,.17,A+.51],.044,"wood_light",rings=2,pointed=True)
# Root-scale genuine GLB plan: repeated organic meshes grouped by material.
parts=[]
for mat,m in meshes.items():
    if m["faces"]:
        parts.append({"name":mat+"_organic_mesh","operation":"mesh","kind":"tower_organic",
                      "material":mat,"vertices":m["vertices"],"faces":m["faces"]})
total=sum(len(p["faces"]) for p in parts)
plan={"name":"Kuningriigid Kiviaja Vahitorn V2 / Local Qwen + Organic Native Mesh",
      "materials":M,"parts":parts,"user_scope":"Static historical RTS prop",
      "design_source":"local qwen3.5-9b, previously rated 2/5 and redesigned",
      "source_recipe_id":"f49d5f218c3ca100"}
(OUT/"native-plan-v2.json").write_text(json.dumps(plan,ensure_ascii=False),encoding="utf-8")
print("QWEN DESIGN",design["design_name"],flush=True)
print("NATIVE QUADS+TRIANGLES",total,"parts",len(parts),flush=True)
runtime=B/"work"/"runtime"/"python"
env=dict(os.environ,MODELFACTORY_LAB_ROOT=str(B/"work"))
env["PYTHONPATH"]=str(runtime)+os.pathsep+env.get("PYTHONPATH","")
script=B/"lab"/"skills"/"modelfactory-lab"/"scripts"/"lab_model.py"
output=OUT/"build"
c=[sys.executable,str(script),"build","--plan",str(OUT/"native-plan-v2.json"),"--out",str(output)]
print("RUNNING_NATIVE_GLTF",flush=True)
p=subprocess.run(c,env=env,text=True,capture_output=True,timeout=240)
(OUT/"build-stdout.txt").write_text(p.stdout,encoding="utf-8")
(OUT/"build-stderr.txt").write_text(p.stderr,encoding="utf-8")
print("BUILD EXIT",p.returncode,flush=True)
print(p.stdout[-4000:],p.stderr[-4000:],flush=True)
if p.returncode:sys.exit(p.returncode)
report=json.loads((output/"mesh-audit.json").read_text(encoding="utf-8"))
export=json.loads((output/"export-validation.json").read_text(encoding="utf-8"))
print("QUADS",report["quad_faces_total"],"TRIANGLES",report["triangles_total"],
      "GEOMETRY_AUDIT",report["status"],"REIMPORT",export["status"],flush=True)
print("GLB",str(output/"model.glb"),flush=True)
