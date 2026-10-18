# Mudelitehas World Atlas 1000 — 5 päris 3D objekti

Valmis geomeetrilised **GLB mudelid** + **nelinurkse topoloogiaga OBJ lähtefailid**, igaühel retsept, paigutusreeglid ja validatsioon.

| Objekt | Retsept | Quadid | GLB kolmnurgad |
| --- | --- | ---: | ---: |
| Küla | `world_village_1000` | 356 | 712 |
| Iidne vare / altar | `ancient_ruin_1000` | 402 | 804 |
| Kaljupaljand | `rock_outcrop_1000` | 360 | 720 |
| Puidust jõesild | `river_bridge_1000` | 294 | 588 |
| Metsagrupp | `forest_cluster_1000` | 622 | 1244 |

## Kasutamine

- Failid `models/<id>/<id>.glb` — mängu/importimiseks glTF 2.0 GLB.
- Failid `.obj` + `.mtl` — **quads-only** Blenderis muudetavad mudelid.
- Kaust `recipes/<id>/` — retsept, mängu paigutus ja kontrollnõuded.
- `viewer.html` — kõigi 5 mudeli lokaalne 3D-vaatur (serverist avades, nt `python -m http.server 8000`).
- `scripts/build_world_objects.py` — korduvgenereerimise lähtekood (Python `trimesh`, `numpy`).
- `python -m unittest discover -s tests -v` — GLB ja OBJ automaatkontroll.

## Mudelitehas 0.1.2 vastavus

**Quad-arvu ja ekspordi kontrollid on tehtud.** Need on teadlikult modelleeritud **protseduurilised lähteobjektid**, mitte 3 sõltumatu referentssuuna point-cloud rekonstruktsioonid. Piltide, enne meshi kontrollitud punktitunnistuste ja Blenderi auditi puudumise tõttu **ei ole neid märgitud sertifitseeritud Mudelitehas 0.1.2 mudeliteks**. Retseptides on puuduvate tõendite väljad nähtaval, mitte võltsandmetega täidetud.

## Mänguga sidumine

Sild suunatakse jõe ületuskohale; külad ja varemed näidatakse ainult pärast avastamist ja annavad preemia üks kord. Kaljud ja metsagrupid on madalal LOD-tasemel korratavad dekoratsioonid. Täpsed tingimused vt `placement_rules.json`. GLB ei muuda mängu reegleid iseenesest.
