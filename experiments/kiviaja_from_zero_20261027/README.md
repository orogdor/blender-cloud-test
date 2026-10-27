# ModelFactory — kiviaja inimene: nullist uuesti (27.10.2026)

**Seis: NEEDS_REPAIR**. See haru ei sisalda kasutusvalmis 3000-quad kiviaja inimest.

Varasemad 3000-quad mudelid jäeti kõrvale. Uueks alusmudeliks kasutati MakeHumani CC0 allikat (base.obj, caucasian-male-young.target ning 18% lihasmorfi). Lokaalses Blender 4.5.15 keskkonnas loodi uus 13 378-quad anatoomiline mees ja kontrolliti selle GLB uuesti importimist (26 756 eksportkolmnurka). Kohalik Qwen 3.5 9B koostas ka uue 3000-quad tehnilise retopoloogia juhise.

Erinevate parandustega riide- ja juukseproov oli 17 048 tahku, kuid ei läbinud visuaalset ülevaatust. Käelabad jäävad T-poosis kõveraks, habe ja juuksed on liigselt geomeetrilistest ribadest ning nahkriided on ebaveenva siluetiga. Need probleemid vajavad päriselt parandamist; katset ei tohi nimetada lõpetatud kiviaja inimese mudeliks.

**Failid**
- `MakeHuman_CC0_male_clean_baseline.glb`: uus puhas anatoomiline mehe lähtevõrk.
- `Clean_Male_Baseline_Starter.zip`: puhas GLB ja redigeeritav Blenderi .blend, manifest ja audit.
- `Kiviaja_uus_alustamine_AUDIT.jpg`: võrdlus mehe puhtast baasvõrgust ja visuaalselt ebaõnnestunud rõivastuse proovist.

**Järgmine tehniline samm:** kasutada sobivat luustikku ja usaldusväärseid nahakaale T-poosi saavutamiseks, mitte pöörata käsi koordinaadilahendusega; pärast geomeetria tõendamist modelleerida riided kehaga sobivaks, teha UV/PBR bake ja alles siis 3000-quad retopoloogia.

CC0 allikas: https://github.com/makehumancommunity/makehuman.
