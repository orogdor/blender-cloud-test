# ModelFactory Lab — Stage 1, 27.10.2026

**Staatus: KAAMERAD LÄBISID; VISUAALNE KVALITEET EI LÄBINUD. Stage 2 blokeeritud.**

## Kinnitatud
- Viis ortograafilist vaadet FRONT, LEFT, BACK, RIGHT, TOP ühest reaalsest 3D-stseenist, mõõtkava sama (2,08 m vertikaalses vaateaknas, 512×736 px iga vaade).
- Windowsi arvutis töötab Blender 4.5.15 LTS portable; viis kaameraga renderdust töötavad protsessoril, ei vaja 8 GB GPU vabastamist.
- Kasutatud CC0 VitruvianGodot'i päris keha-, näo- ja juukse-GLB-sid, mille peale on ModelFactory retsepti alusel lisatud nahkade/rõivaste katsetused.
- Senised SDXL ebaõnnestumised ja 1115 retseptikandidaati ei ole üle kirjutatud.
- Blenderi lähtestseen, kõik viis eraldi PNG-d, kaameramanifest ja kvaliteediaruanne on kohalikus Stage1 kaustas olemas.

## Kontrollitud puudused
- Kiviaja riietus meenutab V6-versioonis endiselt liiga palju tänapäevast särki ja pükse; A-poos vajab parandamist.
- V5 uuringul eemaldati algsed rõivad ning selgus, et selle tasuta allikamudeli torso ja jalad on nende all puudulikud; V5 lükati tagasi.
- V4/V6 kasutavad päris 3D-baasi, **mitte** piltidest tuletatud punktipilve. Nende kaameratulemus ei tõenda piltidel nähtamatute pindade rekonstruktsiooni.
- Quad-retopoloogia, mängumudeli 1900/3500-quad eesmärk, PBR-bake, rig, animatsioonid ja mängukõlbuliku GLB eksport on tegemata.

## Sobiv AI suund
- Hunyuan3D-2mini 0,6B shape-only on 8GB VRAM-i jaoks uuritud kohalik image-to-3D kandidaat, kuid **ei ole veel sellesse arvutisse paigaldatud ega GPU-ga testitud**.
- Suur Hunyuan3D 2.1 ja multiview mudelid ei ole 8GB mälus kindlalt rakendatavad; esimene edukas geomeetriliselt korrektne test on Blenderi kaamera-3D töövoog.

## Kontrollid
- Jälg: `work/projects/Kiviaja_Inimene_V1/01-viited/stage1_camera_v6`
- Kõik viie suuna PNG-d 512×736, viievaateline JPG 2644×879.
- `camera_manifest.json`, `stage1_quality_report.json`, `source_geometry_audit.json` (V4).
- Kvaliteedivärav: `user_approved=false`; `Stage 2=blocked_by_stage_1`.

**Järgmine:** Stage 1 raames asendada olemasolevad rõivad tõeliselt kiviaega sobiva kehale kinnitatud disainiga ja saada kasutaja visuaalne heakskiit. Seni punktipilve ei tehta.
