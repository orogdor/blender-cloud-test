from pathlib import Path
import json,hashlib,zipfile,shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output';REF=ROOT/'references'
with np.load(OUT/'04_point_cloud.npz') as data:cloud={k:data[k] for k in data.files}
test=json.loads((OUT/'three_view_test.json').read_text());cal=json.loads((REF/'calibration.json').read_text());surface=json.loads((OUT/'05_quad_surface.json').read_text())
ious={}
for k,name in enumerate(cal['view_order']):
 canvas=Image.new('L',cal['source_pixels']);d=ImageDraw.Draw(canvas);j=np.array(cal['projection_jacobians'][k]);b=np.array(cal['projection_offsets'][k])
 for ob in surface['objects']:
  uv=np.asarray(ob['vertices'])@j.T+b
  for face in ob['faces']:d.polygon([tuple(v) for v in uv[face]],fill=255)
 a=np.asarray(canvas)>0;m=np.asarray(Image.open(REF/f'mask_{name}.png'))>0;ious[name]=float((a&m).sum()/(a|m).sum())
 canvas.save(OUT/f'Silhouette_{name}.png')
test['mesh_projection_silhouette_IoU']=ious
test['supported_three_axes_percent']=round(test['points_supported_in_3_axes']/test['cloud_points']*100,2)
(OUT/'three_view_test.json').write_text(json.dumps(test,indent=2))
# Exact source witness locations for every point, easy to inspect without NumPy.
with (OUT/'Punktide_3vaate_kontroll.csv').open('w') as f:
 f.write('point_id,x_m,y_m,z_m,top_u,top_v,side_u,side_v,front_u,front_v,rear_u,rear_v,top_error_px,side_error_px,front_error_px,rear_error_px,three_axes_supported\n')
 for i,p in enumerate(cloud['points']):
  row=[i,*p,*cloud['reference_pixels'][i].ravel(),*np.maximum(-cloud['signed_silhouette_distance_px'][i],0),int(cloud['axis_support'][i].all())]
  f.write(','.join(str(round(float(x),6)) for x in row)+'\n')
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
sheet=Image.new('RGB',(1280,920),(240,242,245));d=ImageDraw.Draw(sheet)
for i,(name,title) in enumerate([('side','Külg / Y'),('top','Pealt / Z'),('front','Eest / X'),('rear','Tagant / X')]):
 im=Image.open(OUT/f'Control_{name}.png').convert('RGB');sheet.paste(im,((i%2)*640,(i//2)*460+32));d.text(((i%2)*640+18,(i//2)*460+4),title,font=font,fill=(20,25,35))
sheet.save(OUT/'Auto_5000_kontrollvaated.jpg',quality=94)
report=f'''# Mudelitehas 0.1.2: auto 5000 / kolm vaatamissuunda

Lähteks on kasutaja nelivaate pilt 4319.png. See on versiooni 0.1.2 kolme suuna meetodi kontrollretsept; algne üle vaadatud katse on säilitatud eraldi.

## Tulemus

- Kogu auto: **5000 nelinurka**, GLB-s **10 000 kolmnurka**. Kere koos otsapindadega 3400, rattad 1440, peeglid 48, käepidemed 48 ja dekoratiivsed pinnad 64 nelinurka.
- Punktipilves **{test['cloud_points']}** punkti. Fail salvestati enne meshi ning lõppvõrgu tipud valiti sellest uuesti avatud pilvest.
- Iga punkti asukohta kontrolliti külg-, pealt-, eest- ja tagantvaates: kolm ruumisuunda X/Y/Z. Punktide pildikoordinaadid ja siluetist kõrvalekalle on NPZ-s ning CSV-s.
- **{test['points_supported_in_3_axes']} punkti ehk {test['supported_three_axes_percent']}%** sobib kolme suuna siluettidega 3 piksli tolerantsi piires. **{test['points_with_unresolved_projection_conflicts']} punkti** jääb vastuoluliseks; neid pole peidetud ega eduka vastena märgitud. Graafikul rohelised on sobivad ja punased vastuolulised projektsioonid.
- Meshi silueti IoU: pealt {ious['top']:.3f}, külg {ious['side']:.3f}, eest {ious['front']:.3f}, tagant {ious['rear']:.3f}. Need arvud mõõdavad silueti kattuvust, mitte fotorealismi.

## Mida tähendab siin kolme vaate otsing?

Kontuurid ja katuseprofiil on lähtepildilt märgitud. Nende järgi koostatakse ümardatud ristlõigete ning rataste/peeglite sügavushinnanguga tihe punktipilv. Iga punkti projektsiooni võrreldakse kõigi nelja märgitud siluetiga; vastuolu korral tehakse piiratud sobitus. Seejärel taastatakse pilve struktureeritud proovipunktidest quad-võrk.

See **ei ole sama nähtava pinnatunnuse usaldusväärne tuvastamine kolmel fotol ega mõõdetud fotogrammeetriline triangulatsioon**. Auto alumine, sisemine ja vastaskülg pole neis vaadetes korraga nähtavad. Silueti sisse jäämine ei tõesta sügavuse õigsust. Säilitatud on sümmeetria, ristlõike ja varjatud osade hinnangud; neid ei esitata mõõdetud faktina. Kõigi punktide maskeeritud piiridesse surumine degenereeris esimeses katses detaile, mistõttu lõplik sobitus on regulariseeritud ja puudulikud vasted jäävad aruandesse.

Mõõtkava on hinnanguline 4.56 × 1.82 × 1.47 m. Materjalides kasutatakse lähtepildi projektsioone, mis sisaldavad algset valgust ja perspektiivierinevusi; vastaskülg on peegeldatud. Klaas on lihtsustatud ja mudelil puudub ehitatud salong. Staatiline mängumudel; animatsiooni ei tellitud. Dekoratiivsed pildipinnad on avatud quad-lapid, kere/rattad/peeglid on kinnised. See on tehniline test, mitte täpne CAD-koopia.

## Failid ja kordamine

`Auto_5000_3vaate_test.glb` on mängumudel, `.blend` redigeeritav stseen. `04_point_cloud.npz/.ply`, `Punktide_3vaate_kontroll.csv` ja `three_view_test.json` säilitavad katse andmed. `Auto_5000_kontrollvaated.jpg` ning punktide ülekattepilt on tegelikud kontrollvaated.

Käivita `python recipe/reconstruct.py`, seejärel Blender 4.5.3 taustarežiimis `--python-exit-code 1 --python recipe/build.py`, siis `recipe/verify_export.py` sama Blenderiga ning viimaks `python recipe/finish.py`. Rekonstruktsioon vajab NumPy, SciPy ja Pillow't. Uue mudeli korral tuleb kontuurid, joondus ja objektipõhised sügavushinnangud uuesti koostada.
'''
(ROOT/'KATSE_KOKKUVOTE.md').write_text(report)
manifest={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in ROOT.rglob('*') if p.is_file() and p.suffix not in ['.zip','.log','.blend1'] and '__pycache__' not in p.parts and p.name!='failide_rasid.json'}
(ROOT/'failide_rasid.json').write_text(json.dumps(manifest,indent=2))
archive=ROOT/'Mudelitehas_Auto_5000_3vaate_katse.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in ROOT.rglob('*'):
  if p.is_file() and p.suffix not in ['.log','.blend1','.zip'] and '__pycache__' not in p.parts:z.write(p,p.relative_to(ROOT))
print(json.dumps({'archive':str(archive),'cloud_points':test['cloud_points'],'three_axis_support_percent':test['supported_three_axes_percent'],'silhouette_IoU':ious}))
