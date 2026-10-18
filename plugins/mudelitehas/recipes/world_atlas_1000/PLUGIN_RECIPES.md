# Mudelitehase lisaretseptid Kuningriikide maailma jaoks

Automaatselt lisatavad retseptid (mudelitehas v0.1.2 täissertifitseerimise staatus: **puuduvad 3-suunalised referentsid**):

- world_village_1000
- ancient_ruin_1000
- rock_outcrop_1000
- river_bridge_1000
- forest_cluster_1000

Käsk: `python scripts/build_world_objects.py --output .`

Retsepte võib kasutada varasemate GLB mudelite alusgeomeetriana. Kui lisanduvad front/side/top kontrollitud referentsid, tuleb kolme vaate witness-andmed salvestada **enne** asendava meshi tegemist ja käivitada SKILL.md valideerimistee. Protseduurilise mudeli valideerimine OBJ quadide ja GLB triangulatsiooni alusel ei asenda seda nõuet.
